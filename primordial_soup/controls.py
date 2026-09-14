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
from .panels import DispatchResult
from .state import agents
from .world import (
    max_generation,
    generate_zones,
    longest_lifetime,
    population_per_lineage,
    place_initially,
    fill_fields,
    format_zones_txt,
)
from .genetics import random_population


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
    # Sem draw() aqui: o redraw vem do DispatchResult do handler que
    # chamou recreate(). O loop grafico e o dono unico da
    # apresentacao.


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
    slots = cfg.SAVE_SLOTS
    try:
        i = slots.index(state.active_save_slot)
    except ValueError:
        i = 0
    state.active_save_slot = slots[(i + 1) % len(slots)]
    print(i18n.t("log.save_slot", slot=state.active_save_slot))
    return DispatchResult.continue_(redraw=True)


def action_save() -> DispatchResult:
    from . import persistence
    persistence.save()
    return DispatchResult.continue_(redraw=True)


def action_load() -> DispatchResult:
    from . import persistence
    if persistence.load():
        state.paused = True
        return DispatchResult.continue_(redraw=True)
    return DispatchResult.continue_(redraw=False)
