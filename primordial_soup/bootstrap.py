# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Autoridade unica de construcao de uma nova run.

Este modulo concentra a sequencia de operacoes que criam o mundo do
zero. GUI (recreate), bootstrap grafico e bootstrap headless devem
todos passar por aqui; nenhum deles deve duplicar a construcao.

Nao depende de simulation, controls, rendering, panels_defs nem
pygame. Se uma dependencia dessas surgir, o direction of dependency
esta errado e deve ser corrigido na origem.
"""

from __future__ import annotations

from . import config as cfg
from . import state
from .genetics import random_population
from .runtime_rules import default_runtime_rules
from .state import agents
from .world import (
    fill_fields,
    generate_nests,
    generate_zones,
    place_initially,
    seed_lineages,
)


def bootstrap_new_world() -> None:
    """Constroi uma nova run: mundo, populacao e RuntimeRules default.

    Contrato de defaults:

      - default_runtime_rules() e a autoridade dos 31 defaults HOT;
      - bootstrap NAO enumera nenhum field de RuntimeRules;
      - bootstrap fresh nao preserva regra HOT da run anterior;
      - controls.recreate() preserva a RuntimeRules ativa fora desta funcao.

    Uma construcao de mundo novo tambem restaura os defaults declarativos
    de execucao para simulation_speed e paused. A recriacao pela UI
    preserva as escolhas vigentes do operador ao redor desta chamada.
    """
    state.reset_counters()

    # Nests e centros de zonas sao geometria do mundo.
    # reset_counters() nao os possui: bootstrap descarta a geometria
    # anterior e gera novos centros depois de construir as zonas.
    # A ordem canonica e zones -> nests, porque generate_nests()
    # evita as zonas recem-geradas.
    state.nests = None
    state.zone_centers = None

    seed_lineages()

    for agent in agents:
        agent["pool"] = random_population(
            cfg.INITIAL_POPULATION_PER_LINEAGE
        )

    place_initially()
    fill_fields()

    state.zones, state.zone_centers = generate_zones()
    state.nests = generate_nests(state.zones)

    rules = default_runtime_rules()
    state.set_runtime_rules(rules)

    state.simulation_speed = (
        cfg.CONFIG_SNAPSHOT.operator.default_simulation_speed
    )
    state.paused = cfg.CONFIG_SNAPSHOT.operator.default_paused
