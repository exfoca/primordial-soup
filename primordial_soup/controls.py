# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Acoes de UI reutilizaveis.

Este modulo centraliza as operacoes invocadas tanto pelos handlers
de painel (panels_defs.py) quanto pelos accelerators globais
registrados em simulation.run(). A forma e sempre:

    action_xxx() -> DispatchResult

encapsulando (1) a operacao de dominio, (2) o log de console
correspondente e (3) o DispatchResult apropriado. Isso evita que
panels_defs e simulation.run dupliquem orquestracao.

recreate() e print_state() continuam existindo como operacoes
publicas (nao-DispatchResult); action_recreate() e
action_print_state() sao wrappers finos.
"""

from __future__ import annotations

from . import config as cfg
from . import state
from . import i18n
from . import prefs
from . import feedback
from .panels import DispatchResult
from .world import (
    max_generation,
    longest_lifetime,
    population_per_lineage,
    format_zones_txt,
)
from .bootstrap import bootstrap_new_world


def recreate() -> None:
    # Wrapper fino sobre a autoridade unica de bootstrap. Sem
    # draw() aqui: o redraw vem do DispatchResult do handler que
    # chamou recreate(). O loop grafico e o dono unico da
    # apresentacao.
    #
    # Contrato HOT de recreate(): recriar a populacao/mundo NAO pode
    # destruir a instancia vigente de RuntimeRules nem o tuning
    # configurado pelo operador. O bootstrap fresh (chamado no boot e
    # no headless) continua reconstruindo as rules a partir dos
    # defaults; esta distincao e o ponto do contrato.
    #
    # Capturar a instancia ANTES e restaura-la DEPOIS preserva tanto a
    # identidade quanto todos os campos HOT (lifecycle, two_scales,
    # reproducao, selecao, pesos). set_runtime_rules valida e apenas
    # rebinda a referencia global, sem reconstruir.
    #
    # O bootstrap de um mundo novo reaplica os defaults declarativos de
    # velocidade e pausa; recreate restaura as escolhas vigentes na
    # sessao grafica.
    preserved_rules = state.runtime_rules
    preserved_speed = state.simulation_speed
    preserved_paused = state.paused

    bootstrap_new_world()

    state.set_runtime_rules(preserved_rules)
    state.simulation_speed = preserved_speed
    state.paused = preserved_paused
    print(i18n.t("log.recreate"))


def print_state() -> None:
    zones_txt = format_zones_txt()
    print(
        i18n.t(
            "log.print_state",
            t=state.tick_count,
            lt=longest_lifetime(),
            g=max_generation(),
            p=population_per_lineage(),
            s=f"{state.simulation_speed:g}",
            m=state.runtime_rules.mutation_rate,
            modo=state.runtime_rules.mutation_mode,
            l=state.runtime_rules.local_scale_fraction,
            gg=state.runtime_rules.global_probability,
            gf=state.runtime_rules.global_scale_fraction,
            genes=state.runtime_rules.mutated_genes,
            a=i18n.t("hud.value.environment.zonas"),
            z=zones_txt,
            slot=state.active_save_slot,
        )
    )


# --- Acoes de UI -----------------------------------------------------
#
# Wrappers finos que combinam operacao de dominio + log + DispatchResult.
# Painel handlers e accelerators chamam a MESMA action_*, para nao
# duplicar orquestracao.


def action_recreate() -> DispatchResult:
    recreate()
    # Waves referenciam o ninho da run anterior; recriar o mundo
    # invalida-as. Nao chamamos ui_state.reset() para preservar
    # painel, cursor, scroll, HUD e preferencias do operador.
    from . import ui_state
    ui_state.clear_birth_waves()
    feedback.emit(feedback.FeedbackEvent.WORLD_GENERATED)
    return DispatchResult.continue_(redraw=True)


def action_print_state() -> DispatchResult:
    print_state()
    return DispatchResult.continue_(redraw=False)


def action_heal_all() -> DispatchResult:
    healed = __import__("primordial_soup.world", fromlist=["heal_all"]).heal_all()
    print(i18n.t("log.heal_all", n=healed))
    return DispatchResult.continue_(redraw=True)


def action_toggle_zones() -> DispatchResult:
    state.zones_active = not state.zones_active
    return DispatchResult.continue_(redraw=True)


def action_toggle_recording() -> DispatchResult:
    from . import recording
    recording.toggle()
    return DispatchResult.continue_(redraw=True)


def action_cycle_save_slot() -> DispatchResult:
    before = state.active_save_slot
    slots = cfg.SAVE_SLOTS
    try:
        i = slots.index(state.active_save_slot)
    except ValueError:
        i = 0
    state.active_save_slot = slots[(i + 1) % len(slots)]
    if state.active_save_slot != before:
        prefs.mark_dirty()
    print(i18n.t("log.save_slot", slot=state.active_save_slot))
    return DispatchResult.continue_(redraw=True)


def action_save() -> DispatchResult:
    """Salva no slot ativo e emite notice de sucesso/falha.

    persistence.save() retorna bool. O retorno e a autoridade do
    resultado; nao inferimos sucesso pelo simples fato de a funcao
    ter retornado.

    Em ambos os casos o redraw e True: mesmo no erro a notice precisa
    aparecer no proximo frame. O log de console continua sendo emitido
    por persistence.save() com o detalhe tecnico.
    """
    from . import persistence
    from . import ui_state
    slot = state.active_save_slot
    ok = persistence.save()
    if ok:
        ui_state.show_notice(
            i18n.t("notice.save_ok", slot=slot),
            kind=ui_state.NOTICE_SUCCESS,
        )
        feedback.emit(feedback.FeedbackEvent.SAVE_OK)
    else:
        ui_state.show_notice(
            i18n.t("notice.save_fail", slot=slot),
            kind=ui_state.NOTICE_ERROR,
        )
    return DispatchResult.continue_(redraw=True)


def action_load() -> DispatchResult:
    """Carrega do slot ativo e emite notice de sucesso/falha.

    Em sucesso, pausa a simulacao (comportamento historico). Em falha,
    NAO altera paused: o estado atual do operador e preservado, e a
    notice informa o erro.
    """
    from . import persistence
    from . import ui_state
    slot = state.active_save_slot
    ok = persistence.load()
    if ok:
        state.paused = True
        # A geometria de ninhos mudou junto com o mundo; waves da
        # run anterior nao se aplicam mais. Em load falho o mundo
        # atual continua valido e as waves permanecem (atomicidade).
        ui_state.clear_birth_waves()
        ui_state.show_notice(
            i18n.t("notice.load_ok", slot=slot),
            kind=ui_state.NOTICE_SUCCESS,
        )
        feedback.emit(feedback.FeedbackEvent.LOAD_OK)
    else:
        ui_state.show_notice(
            i18n.t("notice.load_fail", slot=slot),
            kind=ui_state.NOTICE_ERROR,
        )
    return DispatchResult.continue_(redraw=True)