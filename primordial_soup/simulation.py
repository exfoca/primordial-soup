# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations

import random
import sys
from dataclasses import dataclass

import numpy as np

from . import config as cfg
from . import state
from . import i18n
from .state import agents
from .world import (
    max_generation,
    average_hp_per_lineage,
    longest_lifetime,
    population_per_lineage,
    average_composite_score_per_lineage,
    fill_fields,
    find_agent_at,
    find_recent_death_at,
)
from .evolution import evaluate_and_move, reproduce_lineage
from .ecology import compute_ecology_resolution, apply_ecology_resolution
from .bootstrap import bootstrap_new_world
from . import prefs


@dataclass(frozen=True, slots=True)
class StepResult:
    """Fatos observaveis de UM tick.

    Retorno sincrono de simulation.step(). Nao e evento, nao e
    fila, nao e persistido. O unico consumidor hoje e o composition
    root grafico (simulation.run), que transforma birth_lineage em
    BirthWave e mantem o contrato de BIRTH_ACTIVITY agregado por
    batch.

    Contrato estrito:
        nenhum nascimento -> birth_lineage is None, birth_count == 0
        nascimento        -> birth_lineage is int, birth_count > 0
    """
    birth_lineage: int | None
    birth_count: int


def _advance_tick_credit(
    tick_credit: float,
    simulation_speed: float,
) -> tuple[int, float]:
    """Converte credito + velocidade em (steps_due, remainder).

    tick_credit acumula velocidade fracionaria entre frames graficos.
    A parte inteira do credito vira ticks a executar neste frame; a
    parte fracionaria permanece para o proximo.

    Implementacao deliberadamente simples: 0.25 e 0.5 tem
    representacao binaria exata, entao nao ha erro de arredondamento
    a corrigir. Nao adicionar epsilon nem math.floor.
    """
    total_credit = tick_credit + simulation_speed
    steps_due = int(total_credit)
    remaining_credit = total_credit - steps_due
    return steps_due, remaining_credit


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
        "taxa_de_mutacao": (float(state.runtime_rules.mutation_rate),),
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


def _take_reproduction_turn() -> int | None:
    """Resolve o turno reprodutivo deste tick.

    Retorna:
        None   -- nenhuma linhagem reproduz neste tick
        0/1/2  -- linhagem dona do turno

    Preserva a semantica original: cooldown <= 0 consome o turno
    atual, avanca o ponteiro R->G->B e recarrega o cooldown com
    rules.reproduction_interval. Caso contrario, apenas decrementa.
    """
    if state.reproduction_cooldown <= 0:
        lineage = state.reproduction_turn
        state.reproduction_turn = (
            state.reproduction_turn + 1
        ) % cfg.TOTAL_LINEAGES
        state.reproduction_cooldown = (
            state.runtime_rules.reproduction_interval
        )
        return lineage

    state.reproduction_cooldown -= 1
    return None


def step() -> StepResult:
    """Avanca a simulacao por exatamente 1 tick.

    Lifecycle canonico:

        0. incrementar tick e expirar recent_deaths vencidos
        1. perceber / decidir / mover (todas as linhagens)
        2. fill_fields() -- snapshot espacial pos-movimento
        3. compute_ecology_resolution()  -- sem mutacao
        4. apply_ecology_resolution()    -- HP/age/encounter/morte/
                                            compactacao/score
        5. scheduler reprodutivo + reproduce_lineage() se houver
           turno
        6. fill_fields() -- snapshot espacial final (inclui newborns,
                            remove mortos)
        7. metricas

    Newborns nao participam da ecologia do proprio birth tick: eles
    so aparecem apos o fill_fields() final.

    Retorna StepResult com os fatos observaveis do tick. StepResult
    nao controla apresentacao: nao renderiza, nao emite audio, nao
    importa UI. O composition root grafico decide o que fazer com
    o fato.
    """
    state.tick_count += 1
    state.expire_recent_deaths()

    for i in range(cfg.TOTAL_LINEAGES):
        evaluate_and_move(i)

    fill_fields()
    _update_trail()

    resolution = compute_ecology_resolution()
    apply_ecology_resolution(resolution)

    birth_lineage: int | None = None
    birth_count = 0

    reproduction_lineage = _take_reproduction_turn()
    if reproduction_lineage is not None:
        newborn_count = reproduce_lineage(reproduction_lineage)
        if newborn_count > 0:
            birth_lineage = reproduction_lineage
            birth_count = newborn_count

    fill_fields()

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
                m=state.runtime_rules.mutation_rate,
                modo=state.runtime_rules.mutation_mode,
                l=state.runtime_rules.local_scale_fraction,
                gg=state.runtime_rules.global_probability,
                gf=state.runtime_rules.global_scale_fraction,
                genes=state.runtime_rules.mutated_genes,
            )
        )

    return StepResult(
        birth_lineage=birth_lineage,
        birth_count=birth_count,
    )


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
    from . import audio
    from . import feedback

    bootstrap_new_world()

    # Composicao explicita: o bootstrap grafico e o unico ponto que
    # registra os paineis. Headless nunca chama isto; importar
    # panels_defs nao altera estado global.
    ui_state.reset()

    # Prefs do operador, apos os defaults de UI. Ordem importa:
    # ui_state.reset() restaura floating_hud_visible=True; se
    # prefs.load() viesse antes, o reset sobrescreveria o valor
    # carregado. Headless nao chama prefs.load() (invariante 3).
    prefs.load()

    register_default_panels()

    init()

    audio.init()
    audio.set_music_enabled(prefs.music_enabled)
    audio.set_sfx_enabled(prefs.sfx_enabled)
    feedback.register_sink(audio.handle_feedback)
    feedback.emit(feedback.FeedbackEvent.WORLD_GENERATED)

    # Adapters globais do dispatcher. Registrados aqui, nao no
    # input_dispatcher, para o dispatcher nao importar rendering nem
    # simulation (evita import cycle e mantem o dispatcher neutro).
    def _run_steps_with_feedback(count: int) -> None:
        births_before = state.births
        birth_lineages: set[int] = set()

        for _ in range(count):
            result = step()
            if result.birth_count > 0:
                # Contrato StepResult: birth_count > 0 implica
                # birth_lineage != None. Falhar alto se violado,
                # em vez de registrar wave com linhagem None.
                assert result.birth_lineage is not None, (
                    "StepResult.birth_count > 0 sem birth_lineage"
                )
                birth_lineages.add(result.birth_lineage)

        # Coalescing por batch grafico: 20 nascimentos de Red em
        # ticks que rodam no mesmo frame sao apresentados como UMA
        # onda Red neste frame. Ordem determinista para leitura e
        # para testes futuros.
        for lineage_index in sorted(birth_lineages):
            ui_state.add_birth_wave(lineage_index)

        if state.births > births_before:
            feedback.emit(feedback.FeedbackEvent.BIRTH_ACTIVITY)

    def _adapter_step() -> DispatchResult:
        _run_steps_with_feedback(1)
        return DispatchResult.continue_(redraw=True)

    def _adapter_space() -> DispatchResult:
        state.paused = not state.paused
        return DispatchResult.continue_(redraw=True)

    def _adapter_fullscreen() -> DispatchResult:
        rendering.toggle_fullscreen()
        return DispatchResult.continue_(redraw=True)

    # ESC nao possui adapter: a politica (voltar ao world / abrir
    # confirm_exit) e estrutural do dispatcher, em
    # input_dispatcher._handle_escape. Registrar um adapter externo
    # reabriria a possibilidade de ignorar o modal, que foi
    # exatamente a regressao corrigida.

    def _adapter_mouse(pos: tuple[int, int]) -> DispatchResult:
        world_pos = rendering.screen_to_world(pos)
        if world_pos is None:
            return DispatchResult.continue_(redraw=False)
        death = find_recent_death_at(*world_pos)
        if death is not None:
            state.set_inspection_death_selection(death)
            ui_state.set_active_panel(ui_state.PANEL_INSPECTION)
            return DispatchResult.continue_(redraw=True)

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
        before = ui_state.floating_hud_visible
        ui_state.toggle_floating_hud()
        if ui_state.floating_hud_visible != before:
            prefs.mark_dirty()
        return DispatchResult.continue_(redraw=True)

    def _adapter_reset_camera() -> DispatchResult:
        """Ctrl+0: retorna a camera ao estado canonico (1x, origem).

        Delega a rendering.reset_camera(), que devolve True somente
        quando a camera estava fora do estado canonico. Redraw
        reflete essa mudanca: se ja estava em 1x/origem, e no-op.
        """
        changed = rendering.reset_camera()
        return DispatchResult.continue_(redraw=changed)

    def _adapter_wheel(
        notches: int,
        pos: tuple[int, int],
        modifiers: int,
    ) -> DispatchResult:
        """Politica de wheel: sidebar vs zoom vs no-op.

        Prioridade (nesta ordem):

          1. Mouse sobre a sidebar -> scroll do painel. Ctrl NAO muda
             essa prioridade: Ctrl+wheel sobre a sidebar continua
             rolando o painel. A sidebar e uma regiao fisica de UI e
             o zoom nao invade esse dominio.

          2. Mouse fora da sidebar + Ctrl pressionado -> zoom ancorado
             no cursor via rendering.apply_zoom_at. O rendering decide
             se o ponto e valido (dentro do viewport do mundo) e se o
             zoom mudou; o adapter apenas converte a resposta em
             redraw.

          3. Mouse fora da sidebar sem Ctrl -> no-op. Pan nao existe
             nesta etapa.
        """
        screen_w, _ = _pg.display.get_surface().get_size()
        mx, _my = pos

        # Caso A: sidebar tem precedencia absoluta. Ctrl nao muda
        # isso.
        if mx >= screen_w - cfg.INSPECTION_PANEL_WIDTH:
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

        # Caso B: Ctrl+wheel sobre o mundo -> zoom.
        if modifiers & _pg.KMOD_CTRL:
            changed = rendering.apply_zoom_at(pos, notches)
            return DispatchResult.continue_(redraw=changed)

        # Caso C: wheel puro sobre o mundo -> no-op.
        return DispatchResult.continue_(redraw=False)

    input_dispatcher.register_step_handler(_adapter_step)
    input_dispatcher.register_space_handler(_adapter_space)
    input_dispatcher.register_fullscreen_handler(_adapter_fullscreen)
    input_dispatcher.register_mouse_handler(_adapter_mouse)
    input_dispatcher.register_resize_handler(_adapter_resize)
    input_dispatcher.register_wheel_handler(_adapter_wheel)
    # Autoridade geometrica das tabs e rendering.panel_tab_at(). O
    # dispatcher so consulta; nao conhece coordenadas.
    input_dispatcher.register_tab_hit_test_handler(rendering.panel_tab_at)

    # Accelerators globais. Registrados aqui para o dispatcher
    # permanecer neutro quanto a dominios de UI. pygame e importado
    # localmente para preservar o contrato headless do modulo.
    import pygame as _pg
    from . import controls

    input_dispatcher.register_global_action(_pg.K_r, controls.action_recreate)
    input_dispatcher.register_global_action(_pg.K_n, controls.action_cycle_save_slot)
    input_dispatcher.register_global_action(_pg.K_p, controls.action_print_state)
    input_dispatcher.register_global_action(_pg.K_z, controls.action_toggle_zones)
    input_dispatcher.register_global_action(_pg.K_g, controls.action_toggle_recording)
    # H alterna o HUD flutuante. Heal All continua disponivel, mas
    # apenas pelo painel Configuration (item heal_all).
    input_dispatcher.register_global_action(
        _pg.K_h, _adapter_toggle_floating_hud
    )
    # Save / Load com modificador. Ctrl+S substitui o antigo L->load
    # global. L sem Ctrl nao executa nada (nao ha registro).
    input_dispatcher.register_global_action(
        _pg.K_s, controls.action_save, modifiers=_pg.KMOD_CTRL
    )
    input_dispatcher.register_global_action(
        _pg.K_l, controls.action_load, modifiers=_pg.KMOD_CTRL
    )
    # Ctrl+0: reset da camera. Tecla nao estrutural: o accelerator
    # generico cuida do roteamento. Nao ha alias (KP0, HOME, R
    # continuam com seus significados atuais).
    input_dispatcher.register_global_action(
        _pg.K_0, _adapter_reset_camera, modifiers=_pg.KMOD_CTRL
    )

    draw()

    # Acumulador de credito fracionario do scheduler de velocidade.
    # Estado interno do loop grafico: nao vai para state.py, nao e
    # checkpoint, nao e RuntimeRules. Persiste entre iteracoes da
    # mesma execucao; pausa e resume preservam o remainder.
    tick_credit = 0.0

    while True:
        result = input_dispatcher.process_events()

        if result.flow is Flow.EXIT:
            # Flush final: ignora _save_failure_suppressed (retry
            # unico no shutdown), mas nunca _write_allowed.
            prefs.save_if_dirty(force=True)
            feedback.clear_sink()
            audio.play_shutdown_sound()
            audio.shutdown()
            shutdown()
            return

        audio.sync_music(running=not state.paused)

        needs_draw = result.redraw

        # Expira a notice em tempo de interface, nao em tempo de
        # simulacao: roda incondicionalmente a cada iteracao para a
        # notice sumir no prazo mesmo com a simulacao pausada.
        if ui_state.expire_notice_if_needed():
            needs_draw = True

        # Expira waves pelo mesmo motivo. Remocao da ultima wave
        # precisa de um redraw final para limpar o ultimo frame que
        # ainda a continha.
        if ui_state.expire_birth_waves_if_needed():
            needs_draw = True

        # Enquanto houver wave, cada frame grafico avanca a animacao.
        # FORA do gate de pausa: waves animam mesmo com a simulacao
        # parada, porque medem wall-clock, nao ticks.
        if ui_state.has_birth_waves():
            needs_draw = True

        if not state.paused:
            steps_due, tick_credit = _advance_tick_credit(
                tick_credit,
                state.simulation_speed,
            )

            _run_steps_with_feedback(steps_due)

            needs_draw = True

        if needs_draw:
            draw()

        # Flush por frame. Barato enquanto clean; falha nao dispara
        # retry em loop (ver _save_failure_suppressed em prefs.py).
        prefs.save_if_dirty()

        tick_fps()