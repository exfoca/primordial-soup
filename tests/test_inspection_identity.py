"""Testes da semantica de observacao por identidade (Fase 2).

Cobrem: setter por ID, morte -> snapshot, discovery nao muda
observacao, ENTER observa, clique guarda ID, load limpa sessao.
"""
import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import layout
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


def _valid_test_nests():
    """Geometria deterministica de ninhos valida para fixtures de
    checkpoint.

    Tres centros colineares, separados por 2*radius+1, de modo que os
    discos de radius NEST_RADIUS nao compartilhem celulas.
    """
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


def _valid_test_zone_centers():
    """Centros de zona determinísticos, sem consumir RNG."""
    center = (
        layout.LAYOUT.world_width - cfg.ZONE_RADIUS - 1,
        layout.LAYOUT.world_height - cfg.ZONE_RADIUS - 1,
    )
    return tuple(center for _ in range(cfg.NUMBER_OF_ZONES))


def _install_checkpoint_geometry():
    """Instala geometria valida de checkpoint em state.

    Fixtures que preparam mundo manualmente precisam de geometria
    valida antes de qualquer save. zone_centers e a autoridade,
    zones e derivada por world.build_zone_mask().
    """
    centers = _valid_test_zone_centers()
    state.zone_centers = centers
    state.zones = world.build_zone_mask(centers)
    state.nests = _valid_test_nests()


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
    _install_checkpoint_geometry()
    yield
    state.reset_counters()
    state.zones = None
    state.zone_centers = None
    state.nests = None
    agents.clear()


def _first_id(li: int = 0) -> int:
    return int(agents[li]["ids"][0])


def _death_snapshot(li: int, ai: int) -> state.DeathSnapshot:
    lineage = agents[li]
    return state.DeathSnapshot(
        critter_id=int(lineage["ids"][ai]),
        lineage_index=li,
        lineage_id=str(lineage["id"]),
        tick=max(1, int(state.tick_count)),
        agent=lineage["agents"][ai].copy(),
        genome=lineage["pool"][ai].copy(),
    )


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
    """Observado morre: ID permanece, snapshot e trail congela."""
    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    state.inspected_trail.append((3, 3))
    trail_len = len(state.inspected_trail)
    snapshot = _death_snapshot(0, 0)

    state.record_death_snapshot(snapshot)

    assert state.inspected_critter_id == cid
    assert state.inspection_death_snapshot is snapshot
    assert state.recent_deaths[-1] is snapshot
    assert len(state.inspected_trail) == trail_len


def test_death_of_other_critter_does_not_snapshot(fresh_world):
    cid = int(agents[0]["ids"][5])
    state.set_inspection_selection(cid)
    snapshot = _death_snapshot(0, 0)

    state.record_death_snapshot(snapshot)

    assert state.inspection_death_snapshot is None
    assert state.recent_deaths[-1] is snapshot


def test_new_selection_clears_snapshot(fresh_world):
    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    snapshot = _death_snapshot(0, 0)
    state.record_death_snapshot(snapshot)
    assert state.inspection_death_snapshot is snapshot

    state.set_inspection_selection(int(agents[1]["ids"][0]))
    assert state.inspection_death_snapshot is None


def test_load_clears_inspection_session(fresh_world, tmp_path):
    from primordial_soup import persistence

    state.set_inspection_selection(int(agents[0]["ids"][0]))
    state.inspected_trail.append((1, 1))

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True
    assert persistence.load(str(path))

    assert state.inspected_critter_id is None
    assert state.inspection_death_snapshot is None
    assert len(state.inspected_trail) == 0


def test_clear_selection_clears_everything(fresh_world):
    state.set_inspection_selection(int(agents[0]["ids"][0]))
    state.inspected_trail.append((1, 1))
    state.set_inspection_selection(None)
    assert state.inspected_critter_id is None
    assert state.inspection_death_snapshot is None
    assert len(state.inspected_trail) == 0