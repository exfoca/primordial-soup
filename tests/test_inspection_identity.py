"""Testes da semantica de observacao por identidade (Fase 2).

Cobrem: setter por ID, morte -> snapshot, discovery nao muda
observacao, ENTER observa, clique guarda ID, load limpa sessao.
"""
import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import state
from primordial_soup import world
from primordial_soup.world import (
    allocate_critter_ids,
    seed_lineages,
    place_initially,
    fill_fields,
    resolve_critter_id,
    INDEX_HP,
    INDEX_X,
    INDEX_Y,
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


def test_set_selection_by_id_clears_trail(fresh_world):
    state.set_inspection_selection(_first_id())
    state.inspected_trail.append((1, 1))
    state.set_inspection_selection(_first_id(1))
    assert not state.inspected_trail


def test_set_same_id_keeps_trail(fresh_world):
    cid = _first_id()
    state.set_inspection_selection(cid)
    state.inspected_trail.append((7, 7))
    state.set_inspection_selection(cid)
    assert len(state.inspected_trail) == 1


def test_compaction_does_not_lose_observation(fresh_world):
    """ID continua observado apos morte dos anteriores no array."""
    cid = int(agents[0]["ids"][5])
    state.set_inspection_selection(cid)

    alive = np.ones(agents[0]["agents"].shape[0], dtype=bool)
    alive[:5] = False
    agents[0]["ids"] = agents[0]["ids"][alive]
    agents[0]["pool"] = agents[0]["pool"][alive]
    agents[0]["agents"] = agents[0]["agents"][alive]

    assert state.inspected_critter_id == cid
    resolved = resolve_critter_id(cid)
    assert resolved is not None
    assert resolved[0] == 0


def test_criterion_change_does_not_change_observation(fresh_world):
    cid = _first_id()
    state.set_inspection_selection(cid)
    state.discovery_criterion = cfg.CRITERION_OLDEST
    assert state.inspected_critter_id == cid


def test_lineage_filter_change_does_not_change_observation(fresh_world):
    cid = _first_id()
    state.set_inspection_selection(cid)
    state.discovery_lineage_filter = "B"
    assert state.inspected_critter_id == cid


def test_death_captures_snapshot_and_keeps_id(fresh_world):
    """Observado morre: ID permanece, snapshot e criado, trail congelado."""
    from primordial_soup.evolution import _capture_death_snapshot_if_needed

    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    state.inspected_trail.append((3, 3))
    trail_len = len(state.inspected_trail)

    agent = agents[0]
    matrix = agent["agents"]
    matrix[0, INDEX_HP] = 0.0
    alive = np.nonzero(matrix[:, INDEX_HP] > 0)[0]
    _capture_death_snapshot_if_needed(0, agent, alive, matrix)

    assert state.inspected_critter_id == cid
    assert state.inspection_death_snapshot is not None
    assert state.inspection_death_snapshot.critter_id == cid
    assert len(state.inspected_trail) == trail_len  # nao limpa


def test_death_of_other_critter_does_not_snapshot(fresh_world):
    from primordial_soup.evolution import _capture_death_snapshot_if_needed

    cid = int(agents[0]["ids"][5])
    state.set_inspection_selection(cid)

    agent = agents[0]
    matrix = agent["agents"]
    matrix[0, INDEX_HP] = 0.0  # mata o indice 0, nao o observado
    alive = np.nonzero(matrix[:, INDEX_HP] > 0)[0]
    _capture_death_snapshot_if_needed(0, agent, alive, matrix)

    assert state.inspection_death_snapshot is None


def test_new_selection_clears_snapshot(fresh_world):
    from primordial_soup.evolution import _capture_death_snapshot_if_needed

    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    agent = agents[0]
    matrix = agent["agents"]
    matrix[0, INDEX_HP] = 0.0
    alive = np.nonzero(matrix[:, INDEX_HP] > 0)[0]
    _capture_death_snapshot_if_needed(0, agent, alive, matrix)
    assert state.inspection_death_snapshot is not None

    state.set_inspection_selection(int(agents[1]["ids"][0]))
    assert state.inspection_death_snapshot is None


def test_load_clears_inspection_session(fresh_world, tmp_path):
    from primordial_soup import persistence

    state.set_inspection_selection(int(agents[0]["ids"][0]))
    state.inspected_trail.append((1, 1))

    path = tmp_path / "save.pkl"
    persistence.save(str(path))
    assert persistence.load(str(path))

    assert state.inspected_critter_id is None
    assert state.inspection_death_snapshot is None
    assert len(state.inspected_trail) == 0


def test_disable_inspection_clears_everything(fresh_world):
    state.set_inspection_selection(int(agents[0]["ids"][0]))
    state.inspected_trail.append((1, 1))
    state.set_inspection_selection(None)
    assert state.inspected_critter_id is None
    assert state.inspection_death_snapshot is None
    assert len(state.inspected_trail) == 0
