# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations

import random
import sys

import numpy as np

from . import config as cfg
from . import state
from . import i18n
from .state import agents
from .world import (
    max_generation,
    generate_zones,
    average_hp_per_lineage,
    longest_lifetime,
    population_per_lineage,
    fill_fields,
    average_composite_score_per_lineage,
    seed_lineages,
    place_initially,
    find_agent_at,
)
from .genetics import random_population
from .evolution import evaluate_and_move, punish_reward_and_reproduce


def _collect_metrics() -> dict[str, tuple[float, ...]]:
    """Snapshot das metricas avancadas do mundo atual.

    As CHAVES SAO OS NOMES CANONICOS EM PORTUGUES e DEVEM bater
    exatamente com cfg.ADVANCED_METRICS (ex: "populacao", "hp_medio",
    "maior_tempo_de_vida", "geracao_maxima", "score_composto_medio",
    "taxa_de_mutacao").

    Isso garante que state.metrics_history, o CSV exportado por
    persistence.py e os saves usam o mesmo formato.

    Populacao esta aqui como "populacao". Nao ha mais historico
    separado por tick: o painel de chart cicla por todas as entradas
    de state.metrics_history via M, e populacao e a primeira.
    """
    return {
        "populacao": tuple(float(p) for p in population_per_lineage()),
        "hp_medio": tuple(average_hp_per_lineage()),
        "maior_tempo_de_vida": tuple(float(t) for t in longest_lifetime()),
        "geracao_maxima": tuple(float(g) for g in max_generation()),
        "score_composto_medio": tuple(average_composite_score_per_lineage()),
        "taxa_de_mutacao": (float(state.mutation_rate),),
    }


def _update_trail() -> None:
    """Anexa a posicao atual do bicho observado ao trail.

    Chamado uma vez por tick, logo apos o fill_fields() pos-movimento
    e ANTES do punish/death, entao a posicao anexada e a que o bicho
    ocupa neste tick. Se o bicho morre no mesmo tick, o trail guarda
    esse ponto final: o handler de morte congela o trail sem limpar.

    A resolucao e por ID estavel (world.resolve_critter_id), nao por
    indice posicional: se outros bichos morreram antes no tick, o
    indice estaria errado. No-op se nenhum ID esta selecionado ou se
    o ID nao resolve mais.

    A trail pertence a Observation, nao ao painel focado: continua
    sendo atualizada mesmo com o usuario em Metrics, Configuration ou
    world. Ao voltar para Inspection, o operador ve a trajetoria
    acumulada.

    Custo: um resolve (O(N) sobre as tres linhagens) mais um append
    no deque. No maximo uma vez por tick, e so com um bicho
    selecionado.
    """
    from .world import INDEX_X, INDEX_Y, resolve_critter_id

    critter_id = state.inspected_critter_id
    if critter_id is None:
        return

    resolved = resolve_critter_id(critter_id)
    if resolved is None:
        return

    li, ai = resolved
    matrix = agents[li]["agents"]
    x = int(matrix[ai, INDEX_X])
    y = int(matrix[ai, INDEX_Y])
    state.inspected_trail.append((x, y))


def step() -> None:
    """Avanca a simulacao por exatamente 1 tick.

    Nao renderiza: o chamador decide quando desenhar. Isso permite
    rodar N ticks por frame sem pagar N renders.

    Ordem sagrada do tick:
        1. perceber    (campos atuais -> inputs neurais)
        2. decidir     (rede neural -> escolha de movimento)
        3. mover       (deslocamento toroidal)
        4. reavaliar   (reconstroi campos de densidade)
        5. punir/recompensar/matar
        6. reproduzir

    Por que a ordem importa:
        - O mundo e percebido ANTES de mover. Senao o bicho reagiria
          a um mundo que ja mudou.
        - A punicao acontece DEPOIS que todos moveram. Senao o
          primeiro a mover teria vantagem injusta.
    """
    state.tick_count += 1

    for i in range(cfg.TOTAL_LINEAGES):
        evaluate_and_move(i)

    fill_fields()

    # Registra a posicao do bicho observado neste tick. Chamado apos
    # o fill_fields() pos-movimento para a posicao registrada ser a
    # que o bicho ocupa agora. O trail e VIEW, nao parte da
    # simulacao: nao muda a semantica do tick.
    _update_trail()

    # --- Turno de reproducao --------------------------------------
    #
    # Reproducao e evento GLOBAL turn-based: a cada
    # REPRODUCTION_INTERVAL ticks, exatamente UMA linhagem reproduz.
    # O turno rotaciona R -> G -> B -> R -> ...
    #
    # O cooldown conta para baixo todo tick. Ao chegar a 0, a
    # linhagem em state.reproduction_turn recebe o turno; o turno
    # avanca (mod TOTAL_LINEAGES) e o cooldown reinicia. O check vem
    # ANTES do decremento, para o primeiro turno sair ja no tick 0
    # (cooldown comeca em 0). Se decrementasse antes, o primeiro
    # turno sairia no tick 1.
    #
    # Concretamente:
    #   tick 0  : cooldown == 0 -> R recebe turno, turn -> 1, cooldown = 10
    #   tick 1  : cooldown == 10 -> sem turno, cooldown = 9
    #   ...
    #   tick 10 : cooldown == 0 -> G recebe turno, turn -> 2, cooldown = 10
    #   ...
    #   tick 20 : cooldown == 0 -> B recebe turno, turn -> 0, cooldown = 10
    #   tick 30 : cooldown == 0 -> R de novo
    #
    # Deliberado: uma run nova tem reproducao disponivel ja no tick 0
    # em vez de depois de um intervalo morto.
    if state.reproduction_cooldown <= 0:
        reproduce_lineage = state.reproduction_turn
        state.reproduction_turn = (
            state.reproduction_turn + 1
        ) % cfg.TOTAL_LINEAGES
        state.reproduction_cooldown = cfg.REPRODUCTION_INTERVAL
    else:
        reproduce_lineage = -1
        state.reproduction_cooldown -= 1

    for i in range(cfg.TOTAL_LINEAGES):
        # punish_reward_and_reproduce agora adiciona os recem-nascidos
        # ao campo de densidade via fill_fields_incremental, logo apos
        # gerar. O segundo fill_fields() inteiro que rodava aqui
        # reconstruia o campo do zero para pegar uns poucos
        # recem-nascidos — puro desperdicio. A passada incremental
        # produz o mesmo campo com um np.add.at por linhagem.
        #
        # O flag `reproduce` e True so para a linhagem dona do turno.
        # As outras ainda sao punidas/recompensadas/mortas
        # normalmente; so nao tentam reproduzir neste tick.
        punish_reward_and_reproduce(
            i,
            state.mutation_rate,
            state.mutated_genes,
            state.local_scale_fraction,
            reproduce=(i == reproduce_lineage),
        )

    # Nota: nao ha reselecao aqui. Se o bicho observado morreu neste
    # tick, seu snapshot de morte foi capturado dentro de
    # punish_reward_and_reproduce e a observacao agora esta congelada
    # nesse snapshot. Candidatos de discovery (contornos amarelos)
    # sao recalculados da populacao atual no draw; o ID observado
    # nunca e substituido automaticamente.

    # Snapshot de metricas (inclui populacao como "populacao"). Nao
    # ha historico separado por tick: o painel le tudo de
    # state.metrics_history.
    if state.tick_count % cfg.METRICS_INTERVAL == 0:
        state.register_metrics(_collect_metrics())

    if state.tick_count - state.last_print >= cfg.PRINT_EVERY_N_TICKS:
        state.last_print = state.tick_count
        print(
            i18n.t(
                "log.tick_summary",
                t=state.tick_count,
                lt=longest_lifetime(),
                g=max_generation(),
                p=population_per_lineage(),
                m=state.mutation_rate,
                modo=cfg.MUTATION_MODE,
                l=state.local_scale_fraction,
                gg=int(cfg.GLOBAL_PROBABILITY * 100),
                gf=int(cfg.GLOBAL_SCALE_FRACTION * 100),
                genes=state.mutated_genes,
            )
        )


def bootstrap_new_world() -> None:
    """Inicializa uma run nova: contadores, linhagens, populacoes,
    zonas.

    Extraido de run() para o loop grafico e o driver headless
    compartilharem EXATAMENTE as mesmas condicoes iniciais. Sem isso,
    os dois modos divergiriam e comparar um sweep headless com uma
    run grafica seria comparar mundos diferentes.

    NAO toca preferencias do operador que sobrevivem a um recreate:
    a taxa de mutacao vai para o valor INITIAL_* (e uma run nova, nao
    um recreate), a velocidade vai para 1 tick/frame e o parametro
    ativo volta para mutacao. Inspecao, idioma, slot e gravacao NAO
    sao tocados aqui — sao preferencias tratadas em outro lugar (ver
    state.reset_counters, que bootstrap_new_world chama).
    """
    state.reset_counters()

    seed_lineages()
    for agent in agents:
        # random_population retorna uma matriz [N, GENOME_SIZE]
        # float32 (nao lista de arrays), consistente com o resto do
        # hot path (ver world.seed_lineages).
        #
        # INITIAL_POPULATION_PER_LINEAGE e o tamanho inicial. A
        # reproducao pode crescer uma linhagem ate
        # MAX_POPULATION_PER_LINEAGE.
        agent["pool"] = random_population(cfg.INITIAL_POPULATION_PER_LINEAGE)
    place_initially()
    fill_fields()

    # Gera as zonas ambientais no inicio da run.
    state.zones = generate_zones()

    state.mutation_rate = cfg.INITIAL_MUTATION_RATE
    state.mutated_genes = cfg.INITIAL_MUTATED_GENES
    state.local_scale_fraction = int(cfg.LOCAL_SCALE_FRACTION * 100)
    state.ticks_per_frame = 1
    # Comeca com mutacao selecionada, para as setas terem um alvo
    # desde o primeiro frame.
    state.active_param = cfg.PARAM_MUTATION


def run_headless(
    load_slot: str | None,
    ticks: int | None,
    save_slot: str | None,
    fresh: bool,
    quiet: bool,
    seed: int | None,
) -> int:
    """Roda a simulacao sem abrir janela.

    Retorna 0 em sucesso, nao-zero em erro recuperavel (load falhou,
    save falhou). Nunca chama sys.exit: o chamador controla o
    processo.

    Contrato:
      - fresh=True ignora load_slot.
      - fresh=False + load_slot: carrega aquele slot. Se falhar,
        aborta SEM salvar. Sobrescrever um save com um mundo novo
        quando o usuario pediu para continuar dali nunca e a resposta
        certa.
      - fresh=False + sem load_slot: bootstrap de mundo novo. E o
        caso "-d sem -l", que cli.main() rejeita antes de chegar
        aqui, mas a funcao fica permissiva para chamadores
        programaticos.
      - ticks=None e tratado como 0 (zero ticks). O CLI nunca passa
        None (exige -d), mas chamadores programaticos podem; a
        normalizacao torna o contrato explicito em vez de depender
        de uma checagem implicita no loop.
      - save_slot=None pula o save. O CLI sempre resolve um slot,
        entao pelo CLI o save sempre acontece.

    O formato de savegame e identico ao modo grafico: esta funcao
    chama persistence.save() direto. Sem serializacao exclusiva do
    headless.
    """
    from . import persistence

    # --- Semantica de --seed --------------------------------------
    #
    # A ordem depende do modo:
    #
    #   --new --seed N
    #       seed ANTES do bootstrap. Os sorteios do bootstrap
    #       (zonas, genomas, posicoes) usam a seed pedida. E o modo
    #       "run reproduzivel do zero".
    #
    #   --load SLOT (sem --seed)
    #       RNG restaurado do checkpoint. Continuacao exata.
    #
    #   --load SLOT --seed N
    #       load completo (incluindo RNG salvo), DEPOIS seed N
    #       sobrescreve deliberadamente. E o modo "branching
    #       estocastico": mesmo ponto de partida, futuro alternativo.
    #
    #   --load SLOT --seed N com load falho
    #       NENHUM seed e aplicado. O processo aborta com o RNG
    #       global intacto, preservando o invariante de que um
    #       caminho de erro nao consome aleatoriedade.
    #
    # A simulacao sorteia de duas fontes independentes: `random` da
    # stdlib (world.generate_zones) e o RNG global legado do NumPy
    # (genetics.random_population, genetics._apply_noise,
    # evolution._reproduce_one_pair). Seed em so uma tornaria um
    # sweep com --seed nao-reproduzivel de forma dificil de notar
    # (zonas mudariam, genomas nao, ou vice-versa).
    seed_applied_before_bootstrap = False
    if fresh and seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        seed_applied_before_bootstrap = True

    # --- 1. Estado inicial do mundo ---
    if fresh:
        bootstrap_new_world()
    elif load_slot is not None:
        # persistence.load() resolve o path de
        # state.active_save_slot quando path e None. Define o slot
        # ANTES de chamar load e restaura em falha, para um save
        # manual posterior nao apontar para um slot que o usuario
        # nunca escolheu.
        previous_slot = state.active_save_slot
        state.active_save_slot = load_slot
        if not persistence.load():
            state.active_save_slot = previous_slot
            print(
                f"[headless] failed to load slot {load_slot!r}; "
                f"aborting without saving.",
                file=sys.stderr,
            )
            return 1

        # Load bem-sucedido: se --seed foi passado, sobrescreve
        # deliberadamente os RNGs restaurados do checkpoint. Sem
        # --seed, os RNGs ficam exatamente como o load restaurou
        # (continuacao exata).
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
    else:
        bootstrap_new_world()

    # --- 2. Roda o numero de ticks pedido ---
    #
    # Contrato: None -> 0 ticks. A normalizacao e explicita para o
    # leitor nao precisar inferir de uma checagem negativa no loop.
    ticks_to_run = 0 if ticks is None else ticks
    if ticks_to_run > 0:
        if quiet:
            # step() imprime a cada PRINT_EVERY_N_TICKS via
            # `tick_count - last_print >= PRINT_EVERY_N_TICKS`.
            # Empurrar last_print alem do fim da run suprime todos os
            # logs periodicos sem adicionar um flag `quiet` em
            # state.py (que seria estado so para o headless). O
            # resumo final do save ainda imprime.
            state.last_print = state.tick_count + ticks_to_run + 1
        for _ in range(ticks_to_run):
            step()

    # --- 3. Save ---
    if save_slot is not None:
        state.active_save_slot = save_slot
        if not persistence.save():
            print(
                f"[headless] failed to save slot {save_slot!r}.",
                file=sys.stderr,
            )
            return 1

    return 0


def run() -> None:
    """Loop grafico principal. Importa rendering/dispatcher sob
    demanda para que o headless nao precise de Pygame."""
    from .rendering import init, tick_fps, shutdown, draw
    from . import input_dispatcher
    from . import rendering
    from .panels import DispatchResult, Flow
    from .panels_defs import register_default_panels
    from . import ui_state

    bootstrap_new_world()

    # Composicao explicita: o bootstrap grafico e o unico ponto que
    # registra os paineis. Headless nunca chama isto; importar
    # panels_defs nao altera estado global.
    ui_state.reset()
    register_default_panels()

    init()

    # Adapters globais do dispatcher. Registrados aqui, nao no
    # input_dispatcher, para o dispatcher nao importar rendering nem
    # simulation (evita import cycle e mantem o dispatcher neutro).
    def _adapter_step() -> DispatchResult:
        step()
        return DispatchResult.continue_(redraw=True)

    def _adapter_space() -> DispatchResult:
        state.paused = not state.paused
        return DispatchResult.continue_(redraw=True)

    def _adapter_fullscreen() -> DispatchResult:
        rendering.toggle_fullscreen()
        return DispatchResult.continue_(redraw=True)

    def _adapter_escape() -> DispatchResult:
        if ui_state.active_panel != ui_state.PANEL_WORLD:
            ui_state.set_active_panel(ui_state.PANEL_WORLD)
            return DispatchResult.continue_(redraw=True)
        return DispatchResult.exit_()

    def _adapter_mouse(pos: tuple[int, int]) -> DispatchResult:
        world_pos = rendering.screen_to_world(pos)
        if world_pos is None:
            return DispatchResult.continue_(redraw=False)
        hit = find_agent_at(*world_pos)
        if hit is None:
            return DispatchResult.continue_(redraw=False)
        li, ai = hit
        stable_id = int(agents[li]["ids"][ai])
        state.set_inspection_selection(stable_id)
        ui_state.set_active_panel(ui_state.PANEL_INSPECTION)
        return DispatchResult.continue_(redraw=True)

    def _adapter_resize(width: int, height: int) -> DispatchResult:
        rendering.on_resize(width, height)
        return DispatchResult.continue_(redraw=True)

    def _adapter_toggle_floating_hud() -> DispatchResult:
        ui_state.toggle_floating_hud()
        return DispatchResult.continue_(redraw=True)

    def _adapter_wheel(
        notches: int, pos: tuple[int, int]
    ) -> DispatchResult:
        screen_w, _ = _pg.display.get_surface().get_size()
        mx, _my = pos
        if mx < screen_w - cfg.INSPECTION_PANEL_WIDTH:
            return DispatchResult.continue_(redraw=False)
        panel_id = (
            ui_state.active_panel
            if ui_state.active_panel != ui_state.PANEL_WORLD
            else ui_state.last_panel
        )
        current = ui_state.panel_scroll_offsets.get(panel_id, 0)
        WHEEL_STEP = 30
        ui_state.panel_scroll_offsets[panel_id] = max(
            0, current - notches * WHEEL_STEP
        )
        return DispatchResult.continue_(redraw=True)

    input_dispatcher.register_step_handler(_adapter_step)
    input_dispatcher.register_space_handler(_adapter_space)
    input_dispatcher.register_fullscreen_handler(_adapter_fullscreen)
    input_dispatcher.register_escape_handler(_adapter_escape)
    input_dispatcher.register_mouse_handler(_adapter_mouse)
    input_dispatcher.register_resize_handler(_adapter_resize)
    input_dispatcher.register_wheel_handler(_adapter_wheel)

    # Accelerators globais. Registrados aqui para o dispatcher
    # permanecer neutro quanto a dominios de UI. pygame e importado
    # localmente para preservar o contrato headless do modulo.
    import pygame as _pg
    from . import controls

    input_dispatcher.register_global_action(_pg.K_r, controls.action_recreate)
    input_dispatcher.register_global_action(_pg.K_l, controls.action_load)
    input_dispatcher.register_global_action(_pg.K_n, controls.action_cycle_save_slot)
    input_dispatcher.register_global_action(_pg.K_p, controls.action_print_state)
    input_dispatcher.register_global_action(_pg.K_z, controls.action_toggle_zones)
    input_dispatcher.register_global_action(_pg.K_g, controls.action_toggle_recording)
    # H alterna o HUD flutuante. Heal All continua disponivel, mas
    # apenas pelo painel Configuration (item heal_all).
    input_dispatcher.register_global_action(
        _pg.K_h, _adapter_toggle_floating_hud
    )

    draw()

    while True:
        result = input_dispatcher.process_events()

        if result.flow is Flow.EXIT:
            shutdown()
            return

        needs_draw = result.redraw

        if not state.paused:
            for _ in range(state.ticks_per_frame):
                step()
            needs_draw = True

        if needs_draw:
            draw()

        tick_fps()
