# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Traducao de eventos de teclado e handling de mouse.

I alterna o modo de inspecao; clique esquerdo seleciona o bicho sob o
cursor. O clique e aceito com o jogo pausado OU com inspecao ja
ligada; o primeiro clique liga o modo automaticamente. A busca usa
tolerancia toroidal (CLICK_RADIUS_IN_CELLS) porque bichos ocupam
1 celula.

M cicla a metrica exibida no chart (populacao, hp medio, maior tempo
de vida, geracao maxima, score composto, taxa de mutacao).

T cicla o idioma de exibicao. Preferencia puramente de exibicao:
nunca toca o savegame, o CSV nem config. Funciona pausado, rodando e
com o painel aberto.

G alterna a gravacao de tela. Gravando, cada draw() captura um frame
(mundo + HUD + charts + painel) num buffer; parar escreve o buffer
num GIF via Pillow. Gravacao funciona pausado e rodando: pausado,
cada step manual (seta direita) produz exatamente um frame capturado.
O estado autoritativo do gravador vive em recording.py;
state.recording e espelho para o rendering fazer um check barato por
frame.

Z alterna as zonas ambientais ON/OFF em runtime. E MECANICA, nao
preferencia de exibicao: com OFF, as zonas somem da imagem E o bonus
de HP e suprimido. A mascara (state.zones) nunca e modificada, entao
reativar restaura ambos sem regenerar. O toggle e persistido em
"zonas_ativas"; R (recreate) reseta para o default (True).

Ao ligar o modo de inspecao (I), sem bicho selecionado, o mais
evoluido e auto-selecionado. Criterio "mais evoluido": maior score
composto; empate por geracao; depois tempo de vida. Ver
world.most_evolved_agent().
"""

from __future__ import annotations
import pygame

from . import config as cfg
from . import layout
from . import state
from . import i18n
from . import persistence
from . import recording
from .state import agents
from . import world
from .world import (
    INDEX_GENERATION,
    INDEX_COMPOSITE_SCORE,
    INDEX_TIME,
    INDEX_X,
    INDEX_Y,
    find_agent_at,
    max_generation,
    generate_zones,
    longest_lifetime,
    population_per_lineage,
    place_initially,
    fill_fields,
    heal_all,
    format_zones_txt,
)
from .genetics import random_population
from . import rendering
from .rendering import draw


def recreate() -> None:
    # reset_counters() vem PRIMEIRO: e a fronteira de inicio da nova
    # run. Tudo da execucao anterior (contadores, telemetria, sessao
    # de inspecao, next_critter_id) e descartado antes da nova
    # identidade/populacao ser construida.
    #
    # A ordem importa por causa de next_critter_id: place_initially()
    # chama allocate_critter_ids(), que le e avanca o contador. Se o
    # reset viesse depois, o runtime ficaria com IDs 1..N
    # recem-alocados mas next_critter_id=1, e save() gravaria um
    # payload inconsistente (proximo_id <= max(ids)) que o loader
    # rejeita corretamente. Ver tests/test_identity.py.
    state.reset_counters()

    for agent in agents:
        # random_population now returns a single [N, GENOME_SIZE]
        # float32 matrix (see genetics.random_population).
        agent["pool"] = random_population(cfg.INITIAL_POPULATION_PER_LINEAGE)
    place_initially()
    fill_fields()
    state.zones = generate_zones()
    print(i18n.t("log.recreate"))
    draw()


def print_state() -> None:
    zones_txt = format_zones_txt()
    print(
        i18n.t(
            "log.print_state",
            t=state.tick_count,
            lt=longest_lifetime(),
            g=max_generation(),
            p=population_per_lineage(),
            s=state.ticks_per_frame,
            m=state.mutation_rate,
            modo=cfg.MUTATION_MODE,
            l=state.local_scale_fraction,
            gg=int(cfg.GLOBAL_PROBABILITY * 100),
            gf=int(cfg.GLOBAL_SCALE_FRACTION * 100),
            genes=state.mutated_genes,
            a=cfg.ENVIRONMENTAL_MODIFIERS,
            z=zones_txt,
            met=state.selected_metric,
            i="on" if state.inspection_mode else "off",
            slot=state.active_save_slot,
        )
    )


def _selection_to_critter_id(
    selection: tuple[int, int] | None,
) -> int | None:
    """Converte (lineage_index, agent_index) posicional em ID estavel.

    Fronteira unica onde a API posicional (discovery) cruza com a API
    de identidade (observation). `world.discovery_candidate` e
    `world.find_agent_at` devolvem (li, ai); esta funcao vira isso em
    ID.

    Retorna None se a selecao for None ou se os indices estao
    obsoletos.
    """
    if selection is None:
        return None
    li, ai = selection
    if li >= len(agents) or ai >= agents[li]["agents"].shape[0]:
        return None
    return int(agents[li]["ids"][ai])


def _describe_selection_by_id(critter_id: int | None) -> str:
    """Formata uma linha de log descrevendo o bicho observado por ID.

    Usa resolve_critter_id para bichos vivos. Se o bicho estiver morto
    (snapshot presente) ou o ID for desconhecido, diz isso em vez de
    cair numa leitura posicional obsoleta.
    """
    if critter_id is None:
        return i18n.t("log.stale_selection")
    resolved = world.resolve_critter_id(critter_id)
    if resolved is None:
        return i18n.t("log.selection_desc_dead", id=critter_id)
    li, ai = resolved
    a = agents[li]["agents"][ai]
    return i18n.t(
        "log.selection_desc",
        id=agents[li]["id"],
        i=critter_id,
        s=f"{a[INDEX_COMPOSITE_SCORE]:.2f}",
        g=int(a[INDEX_GENERATION]),
        t=int(a[INDEX_TIME]),
        x=int(a[INDEX_X]),
        y=int(a[INDEX_Y]),
    )


def _cycle_criterion(delta: int) -> None:
    """Avanca (delta=+1) ou retrocede (delta=-1) o criterio de
    inspecao.

    Discovery puro: muda quais bichos ficam destacados em amarelo e
    qual bicho o ENTER vai observar. NUNCA troca o bicho observado.
    Observacao e acao explicita (I no start, clique, ENTER);
    discovery nao e.

    O criterio e preferencia de UI em state.discovery_criterion; NAO
    e persistido no savegame e NAO e resetado por reset_counters().
    """
    order = cfg.CRITERIA_ORDER
    try:
        i = order.index(state.discovery_criterion)
    except ValueError:
        i = 0
    state.discovery_criterion = order[(i + delta) % len(order)]


def _cycle_lineage_filter() -> None:
    """Avanca o filtro de linhagem (tecla Tab).

    Ordem de ciclo: cfg.LINEAGE_FILTER_ORDER, i.e.
    all -> R -> G -> B -> all.

    Discovery puro, mesma regra de _cycle_criterion: muda o conjunto
    de candidatos amarelos, nunca o bicho observado. Mesma politica
    de persistencia: preferencia de UI, nao persistida, nao resetada
    por reset_counters().
    """
    order = cfg.LINEAGE_FILTER_ORDER
    try:
        i = order.index(state.discovery_lineage_filter)
    except ValueError:
        i = 0
    state.discovery_lineage_filter = order[(i + 1) % len(order)]


def _enable_inspection_with_auto_selection() -> None:
    """Liga o modo de inspecao e, sem selecao ativa, escolhe o bicho
    mais evoluido automaticamente.

    De qualquer forma, o trail e (re)inicializado via
    state.set_inspection_selection(): ligar a inspecao sempre comeca
    com trail novo, porque uma sessao de analise nova nao deve herdar
    trail da anterior. Por isso passamos pelo setter mesmo quando a
    selecao nao muda: primeiro zeramos a selecao para None, depois
    selecionamos (ou nao) pelo setter.

    Em resumo: esta funcao SEMPRE comeca sem selecao e sem trail,
    depois seleciona (ou nao) pelo setter.
    """
    state.inspection_mode = True

    # Forca sessao nova: descarta selecao e snapshot primeiro, para o
    # setter abaixo sempre ver MUDANCA (None -> id) e limpar o trail.
    # Reabrir o painel no mesmo bicho nao deve herdar trail anterior.
    state.set_inspection_selection(None)

    # A observacao inicial e acao explicita do I, entao auto-selecionar
    # o candidato atual e permitido aqui. O candidato e escolhido
    # posicionalmente e convertido para ID estavel.
    chosen_pos = world.discovery_candidate(
        state.discovery_criterion, state.discovery_lineage_filter
    )
    chosen_id = _selection_to_critter_id(chosen_pos)
    state.set_inspection_selection(chosen_id)

    if chosen_id is None:
        print(i18n.t("log.inspection_on_empty"))
    else:
        print(
            i18n.t(
                "log.inspection_on_auto",
                desc=_describe_selection_by_id(chosen_id),
            )
        )


def _disable_inspection() -> None:
    state.inspection_mode = False
    # set_inspection_selection(None) limpa selecao e trail juntos,
    # mantendo os dois em sincronia. Atribuir
    # state.inspected_critter_id direto deixaria um trail orfao.
    state.set_inspection_selection(None)
    print(i18n.t("log.inspection_off"))


def _observe_discovery_candidate() -> int | None:
    """Unidade semantica de "Enter observa".

    Le state.discovery_criterion e state.discovery_lineage_filter,
    resolve o candidato via world.discovery_candidate(), converte
    para ID estavel e, com candidato, atualiza a observacao via
    state.set_inspection_selection().

    Retorna o ID observado, ou None sem candidato.

    NAO loga e NAO redesenha: isso fica no ramo K_RETURN de
    handle_events().
    """
    candidate = world.discovery_candidate(
        state.discovery_criterion,
        state.discovery_lineage_filter,
    )
    new_id = _selection_to_critter_id(candidate)
    if new_id is None:
        return None
    state.set_inspection_selection(new_id)
    return new_id


def _select_critter_at_click(pos: tuple[int, int]) -> None:
    """Converte clique de tela em coordenada do mundo e seleciona o
    bicho.

    A janela e renderizada escalada por PIXEL_SCALE, entao dividimos
    as coordenadas do mouse pela escala. HUD e painel sao desenhados
    por cima da imagem; cliques sobre eles ainda mapeiam para alguma
    celula, o que e aceitavel.

    A busca usa cfg.CLICK_RADIUS_IN_CELLS para tolerar o fato de
    bichos ocuparem 1 celula (PIXEL_SCALE px). Sem isso, acertar um
    bicho de 3x3 px seria hostil.

    Semantica: o clique e acao EXPLICITA de observacao. Clique que
    acerta observa o individuo; clique que erra NAO adota candidato
    nenhum, so registra o miss. Se a sessao ainda nao esta aberta, o
    primeiro clique a abre (via I automatico), e essa abertura pode
    auto-selecionar o candidato; a partir dai, clique vazio nao muda
    mais a observacao.
    """
    if not state.inspection_mode:
        _enable_inspection_with_auto_selection()

    px, py = pos

    # Em tela cheia o mundo e esticado e centrado (letterbox). Em
    # modo janela, _offset_* = 0 e _scale = 1.0, entao este calculo
    # se reduz a px // PIXEL_SCALE. Desfazer o offset ANTES de
    # dividir pela escala.
    px = (px - rendering._offset_x) / rendering._scale
    py = (py - rendering._offset_y) / rendering._scale
    x = int(px) // layout.LAYOUT.pixel_scale
    y = int(py) // layout.LAYOUT.pixel_scale

    if not (0 <= x < layout.LAYOUT.world_width and 0 <= y < layout.LAYOUT.world_height):
        print(
            i18n.t(
                "log.inspection_miss",
                x=x,
                y=y,
                r=cfg.CLICK_RADIUS_IN_CELLS,
            )
        )
        return

    found = find_agent_at(x, y)
    found_id = _selection_to_critter_id(found)

    if found_id is not None:
        # O setter limpa o trail SO quando o ID observado muda.
        # Clicar no mesmo bicho duas vezes preserva o trail.
        state.set_inspection_selection(found_id)
        print(
            i18n.t(
                "log.inspection_select",
                desc=_describe_selection_by_id(found_id),
            )
        )
        return

    print(
        i18n.t(
            "log.inspection_miss",
            x=x,
            y=y,
            r=cfg.CLICK_RADIUS_IN_CELLS,
        )
    )


def handle_events() -> bool:
    """Processa a fila de eventos. Retorna False se o jogo deve fechar.

    Mapa de teclas:
        SPACE  pausa/resume
        right  step (1 tick), sempre
        r      recria
        s      salva
        l      carrega
        p      imprime
        i      alterna modo de inspecao
               — ao ligar, auto-seleciona o mais evoluido se nada
                 estiver selecionado.
        m      cicla metrica do chart
        n      cicla save slot (S/L resolvem para o slot ativo)
        t      cicla idioma de exibicao
        g      alterna gravacao de GIF (start/stop)
               — start/stop e instantaneo; o GIF e escrito quando a
                 gravacao para (ou quando o budget de frames acaba).
        z      alterna zonas ambientais ON/OFF
               — visual + mecanica; persistido no savegame.
        ESC    sai

        u      seleciona taxa de mutacao como parametro ativo
        o      seleciona escala local como parametro ativo
        e      seleciona efeito de HP das zonas como parametro ativo

        up     +1 no parametro ativo
        down   -1 no parametro ativo
               (o parametro ativo e escolhido com u / o / e e
                destacado no HUD com marcador e cor)

        ,      velocidade /2
        .      velocidade *2

        clique esquerdo  seleciona bicho sob o cursor
                         (aceito pausado ou com inspecao ligada)
                         — o primeiro clique liga o modo e
                           auto-seleciona o mais evoluido; depois, um
                           clique que acerta observa o bicho, um que
                           erra loga o miss e nao muda nada.
        ENTER            adota o candidato atual de discovery como
                         bicho observado (acao explicita).
    """
    from .simulation import step

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False

        # Clique do mouse.
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Aceita o clique com o jogo pausado (caso natural para
            # selecionar um bicho) ou com inspecao ja ligada. O
            # primeiro clique liga o modo automaticamente (e ja deixa
            # o mais evoluido selecionado, caso o clique erre).
            if state.paused or state.inspection_mode:
                _select_critter_at_click(event.pos)
            continue

        if event.type != pygame.KEYDOWN:
            continue

        key = event.key

        if key == pygame.K_ESCAPE:
            return False

        elif key == pygame.K_F11:
            # Alterna tela cheia. A funcao ja redesenha internamente
            # (para o usuario ver mesmo pausado), sem draw() aqui.
            rendering.toggle_fullscreen()

        elif key == pygame.K_SPACE:
            state.paused = not state.paused

        elif key == pygame.K_EQUALS or key == pygame.K_PLUS:
            step()
            draw()

        elif key == pygame.K_LEFT:
            if state.inspection_mode:
                _cycle_criterion(-1)
                draw()

        elif key == pygame.K_RIGHT:
            if state.inspection_mode:
                _cycle_criterion(+1)
                draw()

        elif key == pygame.K_TAB:
            if state.inspection_mode:
                _cycle_lineage_filter()
                draw()

        elif key == pygame.K_RETURN:
            # ENTER = observar. As teclas de discovery (left/right,
            # Tab) nunca trocam o bicho observado; so esta tecla
            # troca, alem do I inicial e do clique do mouse.
            if state.inspection_mode:
                new_id = _observe_discovery_candidate()
                if new_id is None:
                    print(
                        i18n.t(
                            "log.inspection_no_match",
                            criterion=i18n.t(
                                f"criterion.{state.discovery_criterion}"
                            ),
                            lineage=i18n.t(
                                f"lineage_filter.{state.discovery_lineage_filter}"
                            ),
                        )
                    )
                else:
                    print(
                        i18n.t(
                            "log.inspection_observe",
                            desc=_describe_selection_by_id(new_id),
                        )
                    )
                    draw()

        elif key == pygame.K_r:
            recreate()

        elif key == pygame.K_s:
            persistence.save()

        elif key == pygame.K_l:
            if persistence.load():
                state.paused = True
                draw()

        elif key == pygame.K_p:
            print_state()

        # Alterna modo de inspecao.
        # Ao ligar, sem selecao, auto-seleciona o mais evoluido (maior
        # score composto; empate por geracao e tempo).
        elif key == pygame.K_i:
            if state.inspection_mode:
                _disable_inspection()
            else:
                _enable_inspection_with_auto_selection()

        # Cicla a metrica do chart.
        elif key == pygame.K_m:
            name = state.cycle_metric()
            print(i18n.t("log.metric_cycle", name=name))

        # Cicla o save slot ativo. S e L (abaixo) resolvem para o
        # slot ativo; e assim que o usuario troca para qual mundo
        # salva / de qual carrega. A lista e fixa em config.py (ver
        # cfg.SAVE_SLOTS).
        #
        # Sem redraw aqui: o slot aparece no HUD e o proximo draw()
        # (proximo tick rodando, proximo step manual ou SPACE pausado)
        # pinta. Evita draw() recursivo dentro do event loop. Pausado,
        # o log do console ja confirma o novo slot.
        elif key == pygame.K_n:
            slots = cfg.SAVE_SLOTS
            try:
                i = slots.index(state.active_save_slot)
            except ValueError:
                i = 0
            state.active_save_slot = slots[(i + 1) % len(slots)]
            print(i18n.t("log.save_slot", slot=state.active_save_slot))

        # Cicla o idioma de exibicao. Redraw imediato para a mudanca
        # ser visivel mesmo pausado.
        elif key == pygame.K_t:
            new_lang = i18n.cycle_language()
            print(i18n.t("log.lang", v=new_lang))
            draw()

        # Alterna gravacao de tela ON/OFF.
        #
        # recording.toggle() e idempotente dos dois lados: comeca um
        # buffer novo se ocioso, ou finaliza e escreve o GIF se ativo.
        # O caminho de stop imprime o resultado (path, frames, tamanho)
        # ou o motivo de falha (Pillow faltando, erro de save, buffer
        # vazio).
        #
        # Sem redraw aqui: o flag nao muda a aparencia do mundo, so se
        # frames sao capturados. O indicador do HUD e repintado no
        # proximo draw(). Evita draw() recursivo no event loop.
        elif key == pygame.K_g:
            recording.toggle()

        # Alterna zonas ambientais ON/OFF. E MECANICA, nao preferencia
        # de exibicao: afeta imagem E bonus de HP. Redraw imediato
        # para a mudanca ser visivel mesmo pausado.
        elif key == pygame.K_z:
            state.zones_active = not state.zones_active
            print(
                i18n.t(
                    "log.zones_toggle",
                    state="on" if state.zones_active else "off",
                )
            )
            draw()

        # Reseta o HP de todo bicho vivo para INITIAL_HP.
        # Mnemotecnica: H = Heal.
        #
        # Reset, nao soma: o HP vira EXATAMENTE INITIAL_HP. Abaixo e
        # curado, acima e reduzido. Nada mais e tocado: nem posicao,
        # nem idade, nem geracao, nem hidden state, nem contadores.
        #
        # Bichos mortos NAO sao revividos. Linhagens extintas
        # continuam extintas (reviver exigiria sintetizar genomas do
        # nada — mecanica diferente; ver notas em world.heal_all).
        #
        # Redraw imediato para a mudanca ser visivel mesmo pausado.
        elif key == pygame.K_h:
            healed = heal_all()
            print(i18n.t("log.heal_all", n=healed))
            draw()

        # --- Selecao de parametro: u / o / e ---
        #
        # As setas atuam sobre o parametro selecionado aqui. Substitui
        # as teclas antigas por parametro (a/d para escala local, [ ]
        # para efeito HP das zonas), para um unico par de teclas
        # ajustar todo parametro aditivo. Velocidade mantem as teclas
        # dedicadas , .: e um toggle de conveniencia muito mais usado
        # que os parametros de experimento.
        elif key == pygame.K_u:
            state.active_param = cfg.PARAM_MUTATION
            print(
                i18n.t(
                    "log.param_selected",
                    name=i18n.t("log.param_name.mutation"),
                )
            )
            draw()

        elif key == pygame.K_o:
            state.active_param = cfg.PARAM_LOCAL_SCALE
            print(
                i18n.t(
                    "log.param_selected",
                    name=i18n.t("log.param_name.local_scale"),
                )
            )
            draw()

        elif key == pygame.K_e:
            state.active_param = cfg.PARAM_ZONE_HP_EFFECT
            print(
                i18n.t(
                    "log.param_selected",
                    name=i18n.t("log.param_name.zone_hp_effect"),
                )
            )
            draw()

        # --- Ajusta o parametro ATIVO: up = +1, down = -1 ---
        #
        # Cada parametro tem seus limites e sua mensagem de log.
        # state.active_param e uma string canonica (ver config.py);
        # None = sem selecao e as setas sao no-op. O jogo comeca com
        # PARAM_MUTATION ativo (ver simulation.run), entao na pratica
        # as setas sempre tem alvo.
        elif key == pygame.K_UP:
            if state.active_param == cfg.PARAM_MUTATION:
                state.mutation_rate = min(
                    state.mutation_rate + 1, cfg.MAX_MUTATION_RATE
                )
                print(i18n.t("log.mut", v=state.mutation_rate))
            elif state.active_param == cfg.PARAM_LOCAL_SCALE:
                state.local_scale_fraction = min(
                    state.local_scale_fraction + 1,
                    cfg.MAX_LOCAL_SCALE_FRACTION,
                )
                print(i18n.t("log.local_scale", v=state.local_scale_fraction))
            elif state.active_param == cfg.PARAM_ZONE_HP_EFFECT:
                state.zone_hp_effect = min(
                    state.zone_hp_effect + 1, cfg.MAX_ZONE_HP_EFFECT
                )
                print(i18n.t("log.zone_hp_effect", v=state.zone_hp_effect))
            else:
                pass  # no parameter selected: no-op

        elif key == pygame.K_DOWN:
            if state.active_param == cfg.PARAM_MUTATION:
                state.mutation_rate = max(
                    state.mutation_rate - 1, cfg.MIN_MUTATION_RATE
                )
                print(i18n.t("log.mut", v=state.mutation_rate))
            elif state.active_param == cfg.PARAM_LOCAL_SCALE:
                state.local_scale_fraction = max(
                    state.local_scale_fraction - 1,
                    cfg.MIN_LOCAL_SCALE_FRACTION,
                )
                print(i18n.t("log.local_scale", v=state.local_scale_fraction))
            elif state.active_param == cfg.PARAM_ZONE_HP_EFFECT:
                state.zone_hp_effect = max(
                    state.zone_hp_effect - 1, cfg.MIN_ZONE_HP_EFFECT
                )
                print(i18n.t("log.zone_hp_effect", v=state.zone_hp_effect))
            else:
                pass  # no parameter selected: no-op

        # --- Velocidade: , diminui (/2), . aumenta (x2) ---
        elif key == pygame.K_COMMA:
            state.ticks_per_frame = max(
                cfg.MIN_TICKS_PER_FRAME, state.ticks_per_frame // 2
            )
            print(i18n.t("log.speed", v=state.ticks_per_frame))

        elif key == pygame.K_PERIOD:
            state.ticks_per_frame = min(
                cfg.MAX_TICKS_PER_FRAME, state.ticks_per_frame * 2
            )
            print(i18n.t("log.speed", v=state.ticks_per_frame))

    return True
