"""Contratos de interacao entre Discovery e Observation.

Cobrem os helpers de controls.py diretamente, sem montar fila de
eventos Pygame. O contrato de Enter e testado via
_observe_discovery_candidate().
"""

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import state
from primordial_soup import world
from primordial_soup import controls
from primordial_soup.world import (
    seed_lineages,
    place_initially,
    fill_fields,
    resolve_critter_id,
    INDEX_HP,
)
from primordial_soup.state import agents


@pytest.fixture
def fresh_world():
    """3 linhagens com pool/agents/ids em lockstep."""
    state.reset_counters()
    seed_lineages()
    for agent in agents:
        agent["pool"] = np.zeros(
            (cfg.INITIAL_POPULATION_PER_LINEAGE, cfg.GENOME_SIZE),
            dtype=np.float32,
        )
    place_initially()
    fill_fields()
    yield
    state.reset_counters()
    agents.clear()


def _first_id(li: int = 0) -> int:
    return int(agents[li]["ids"][0])


# ---------------------------------------------------------------------------
# Discovery nao muda Observation
# ---------------------------------------------------------------------------


def test_cycle_criterion_does_not_change_observation(fresh_world):
    cid = _first_id()
    state.set_inspection_selection(cid)
    before = state.discovery_criterion

    controls._cycle_criterion(+1)

    assert state.discovery_criterion != before
    assert state.inspected_critter_id == cid


def test_cycle_lineage_filter_does_not_change_observation(fresh_world):
    cid = _first_id()
    state.set_inspection_selection(cid)
    before = state.discovery_lineage_filter

    controls._cycle_lineage_filter()

    assert state.discovery_lineage_filter != before
    assert state.inspected_critter_id == cid


# ---------------------------------------------------------------------------
# discovery_candidate respeita filtro
# ---------------------------------------------------------------------------


def test_discovery_candidate_respects_lineage_filter(fresh_world):
    for target_id, li in (("R", 0), ("G", 1), ("B", 2)):
        candidate = world.discovery_candidate(
            cfg.CRITERION_MOST_EVOLVED, target_id
        )
        assert candidate is not None
        assert candidate[0] == li


def test_discovery_candidate_all_can_be_global(fresh_world):
    candidate = world.discovery_candidate(
        cfg.CRITERION_MOST_EVOLVED, cfg.LINEAGE_FILTER_ALL
    )
    assert candidate is not None
    assert 0 <= candidate[0] < cfg.TOTAL_LINEAGES


def test_discovery_candidate_none_for_empty_lineage(fresh_world):
    agents[2]["agents"] = agents[2]["agents"][:0]
    agents[2]["pool"] = agents[2]["pool"][:0]
    agents[2]["ids"] = agents[2]["ids"][:0]

    assert world.discovery_candidate(cfg.CRITERION_MOST_EVOLVED, "B") is None


def test_empty_lineage_does_not_change_observation(fresh_world):
    cid = _first_id()
    state.set_inspection_selection(cid)

    agents[2]["agents"] = agents[2]["agents"][:0]
    agents[2]["pool"] = agents[2]["pool"][:0]
    agents[2]["ids"] = agents[2]["ids"][:0]
    state.discovery_lineage_filter = "B"

    assert state.inspected_critter_id == cid


# ---------------------------------------------------------------------------
# _observe_discovery_candidate
# ---------------------------------------------------------------------------


def test_observe_sets_observed_to_candidate(fresh_world):
    state.discovery_criterion = cfg.CRITERION_MOST_EVOLVED
    state.discovery_lineage_filter = "G"

    candidate = world.discovery_candidate(
        state.discovery_criterion, state.discovery_lineage_filter
    )
    assert candidate is not None
    expected_id = int(agents[candidate[0]]["ids"][candidate[1]])

    new_id = controls._observe_discovery_candidate()

    assert new_id == expected_id
    assert state.inspected_critter_id == expected_id


def test_observe_without_candidate_keeps_observation(fresh_world):
    cid = _first_id()
    state.set_inspection_selection(cid)

    agents[2]["agents"] = agents[2]["agents"][:0]
    agents[2]["pool"] = agents[2]["pool"][:0]
    agents[2]["ids"] = agents[2]["ids"][:0]
    state.discovery_lineage_filter = "B"

    new_id = controls._observe_discovery_candidate()

    assert new_id is None
    assert state.inspected_critter_id == cid


def test_observe_clears_death_snapshot(fresh_world):
    from primordial_soup.evolution import _capture_death_snapshot_if_needed

    # Observado morre.
    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    agent = agents[0]
    matrix = agent["agents"]
    matrix[0, INDEX_HP] = 0.0
    alive = np.nonzero(matrix[:, INDEX_HP] > 0)[0]
    _capture_death_snapshot_if_needed(0, agent, alive, matrix)
    assert state.inspection_death_snapshot is not None

    # Enter observa outro candidato vivo.
    state.discovery_lineage_filter = "G"
    new_id = controls._observe_discovery_candidate()

    assert new_id is not None
    assert state.inspected_critter_id == new_id
    assert state.inspection_death_snapshot is None
    assert len(state.inspected_trail) == 0


# ---------------------------------------------------------------------------
# Snapshot morto nao e afetado por navegacao de discovery
# ---------------------------------------------------------------------------


def test_navigation_does_not_disturb_death_snapshot(fresh_world):
    from primordial_soup.evolution import _capture_death_snapshot_if_needed

    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    agent = agents[0]
    matrix = agent["agents"]
    matrix[0, INDEX_HP] = 0.0
    alive = np.nonzero(matrix[:, INDEX_HP] > 0)[0]
    _capture_death_snapshot_if_needed(0, agent, alive, matrix)
    snap = state.inspection_death_snapshot
    assert snap is not None
    trail_before = list(state.inspected_trail)

    controls._cycle_criterion(+1)
    controls._cycle_criterion(-1)
    controls._cycle_lineage_filter()

    assert state.inspected_critter_id == cid
    assert state.inspection_death_snapshot is snap
    assert list(state.inspected_trail) == trail_before


# ---------------------------------------------------------------------------
# I usa o Discovery atual (nao forca most_evolved)
# ---------------------------------------------------------------------------


def test_enable_inspection_observes_current_discovery(fresh_world):
    state.discovery_criterion = cfg.CRITERION_OLDEST
    state.discovery_lineage_filter = "B"

    candidate = world.discovery_candidate(
        state.discovery_criterion, state.discovery_lineage_filter
    )
    assert candidate is not None
    expected_id = int(agents[candidate[0]]["ids"][candidate[1]])

    controls._enable_inspection_with_auto_selection()

    assert state.inspection_mode is True
    assert state.inspected_critter_id == expected_id


# ---------------------------------------------------------------------------
# Clique direto nao altera Discovery
# ---------------------------------------------------------------------------


def test_click_does_not_change_discovery(fresh_world):
    state.inspection_mode = True
    state.discovery_criterion = cfg.CRITERION_OLDEST
    state.discovery_lineage_filter = "G"

    row = agents[0]["agents"][3]
    x = int(row[1])
    y = int(row[2])
    controls._select_critter_at_click((x * 2, y * 2))

    assert state.discovery_criterion == cfg.CRITERION_OLDEST
    assert state.discovery_lineage_filter == "G"


# ---------------------------------------------------------------------------
# Renomeacao consistente: nenhum campo antigo em uso
# ---------------------------------------------------------------------------


def test_no_legacy_field_names_referenced(fresh_world):
    assert hasattr(state, "discovery_criterion")
    assert hasattr(state, "discovery_lineage_filter")
    assert not hasattr(state, "inspected_criterion")
    assert not hasattr(state, "inspected_lineage_filter")
