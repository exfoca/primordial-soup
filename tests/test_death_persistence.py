"""Persistencia v23 do historico recente de mortes."""

from __future__ import annotations

import copy
import pickle

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import layout
from primordial_soup import persistence
from primordial_soup import simulation
from primordial_soup import state
from primordial_soup import world
from primordial_soup.state import agents
from primordial_soup.world import AGENT_COLUMNS, INDEX_X, INDEX_Y


def _valid_test_nests():
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


def _install_checkpoint_geometry():
    center = (
        layout.LAYOUT.world_width - cfg.ZONE_RADIUS - 1,
        layout.LAYOUT.world_height - cfg.ZONE_RADIUS - 1,
    )
    state.zone_centers = tuple(center for _ in range(cfg.NUMBER_OF_ZONES))
    state.zones = world.build_zone_mask(state.zone_centers)
    state.nests = _valid_test_nests()


def _snapshot(
    *,
    critter_id: int = 4,
    lineage_index: int = 0,
    tick: int = 100,
    x: int = 30,
    y: int = 30,
    marker: float = 0.0,
) -> state.DeathSnapshot:
    agent = np.zeros((AGENT_COLUMNS,), dtype=np.float32)
    agent[INDEX_X] = float(x)
    agent[INDEX_Y] = float(y)
    agent[0] = np.float32(123.0 + marker)
    genome = np.zeros((cfg.GENOME_SIZE,), dtype=np.float32)
    genome[0] = np.float32(marker)
    return state.DeathSnapshot(
        critter_id=critter_id,
        lineage_index=lineage_index,
        lineage_id=cfg.LINEAGES[lineage_index]["id"],
        tick=tick,
        agent=agent,
        genome=genome,
    )


def _record(*snapshots: state.DeathSnapshot) -> None:
    state.deaths = len(snapshots)
    for snapshot in snapshots:
        state.record_death_snapshot(snapshot)


@pytest.fixture(autouse=True)
def fresh_world():
    state.reset_counters()
    agents.clear()
    world.seed_lineages()

    for li, lineage in enumerate(agents):
        lineage["pool"] = np.zeros((1, cfg.GENOME_SIZE), dtype=np.float32)
        lineage["agents"] = np.zeros((1, AGENT_COLUMNS), dtype=np.float32)
        lineage["ids"] = np.array([li + 1], dtype=np.int64)
        lineage["agents"][0, INDEX_X] = float(10 + li)
        lineage["agents"][0, INDEX_Y] = float(20 + li)
        lineage["field"] = np.zeros(
            (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
            dtype=np.int16,
        )
    world.fill_fields()

    state.next_critter_id = 10
    state.tick_count = 100
    _install_checkpoint_geometry()
    yield

    state.reset_counters()
    state.zones = None
    state.zone_centers = None
    state.nests = None
    agents.clear()


def _read(path):
    with open(path, "rb") as handle:
        return pickle.load(handle)


def _write(path, data):
    with open(path, "wb") as handle:
        pickle.dump(data, handle)


def _valid_save_with_one_death(tmp_path):
    snapshot = _snapshot()
    _record(snapshot)
    path = tmp_path / "world.pkl"
    assert persistence.save(str(path)) is True
    return path, snapshot


def test_save_empty_archive_writes_required_v23_field(tmp_path):
    path = tmp_path / "world.pkl"
    assert persistence.save(str(path)) is True

    data = _read(path)
    assert data["versao"] == 23
    assert data["mortes_recentes"] == []


def test_save_snapshot_payload_is_canonical_float32_ndarray(tmp_path):
    path, snapshot = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    record = data["mortes_recentes"][0]

    assert set(record) == {"id", "linhagem", "tick", "agente", "genoma"}
    assert type(record["id"]) is int
    assert type(record["linhagem"]) is str
    assert type(record["tick"]) is int
    assert isinstance(record["agente"], np.ndarray)
    assert record["agente"].dtype == np.float32
    assert record["agente"].shape == (AGENT_COLUMNS,)
    assert isinstance(record["genoma"], np.ndarray)
    assert record["genoma"].dtype == np.float32
    assert record["genoma"].shape == (cfg.GENOME_SIZE,)
    assert "lineage_index" not in record
    assert "x" not in record
    assert "y" not in record
    assert np.array_equal(record["agente"], snapshot.agent)
    assert np.array_equal(record["genoma"], snapshot.genome)


def test_save_payload_represents_moment_of_save(tmp_path):
    path, snapshot = _valid_save_with_one_death(tmp_path)
    expected_agent = snapshot.agent.copy()
    expected_genome = snapshot.genome.copy()

    snapshot.agent[:] = 777.0
    snapshot.genome[:] = 888.0

    data = _read(path)
    record = data["mortes_recentes"][0]
    assert np.array_equal(record["agente"], expected_agent)
    assert np.array_equal(record["genoma"], expected_genome)


def test_round_trip_restores_complete_archive_in_order(tmp_path):
    first = _snapshot(critter_id=4, lineage_index=0, tick=90, marker=1.0)
    second = _snapshot(
        critter_id=5,
        lineage_index=2,
        tick=100,
        x=40,
        y=41,
        marker=2.0,
    )
    _record(first, second)
    path = tmp_path / "world.pkl"
    assert persistence.save(str(path)) is True

    expected = tuple(state.recent_deaths)
    state.recent_deaths.clear()
    assert persistence.load(str(path)) is True

    restored = state.get_recent_deaths()
    assert len(restored) == 2
    for got, want in zip(restored, expected):
        assert got.critter_id == want.critter_id
        assert got.lineage_id == want.lineage_id
        assert got.lineage_index == want.lineage_index
        assert got.tick == want.tick
        assert np.array_equal(got.agent, want.agent)
        assert np.array_equal(got.genome, want.genome)


def test_selection_is_not_persisted_but_history_is(tmp_path):
    snapshot = _snapshot()
    _record(snapshot)
    state.set_inspection_death_selection(snapshot)
    state.inspected_trail.extend(((1, 1), (2, 2)))
    path = tmp_path / "world.pkl"
    assert persistence.save(str(path)) is True

    assert persistence.load(str(path)) is True

    assert len(state.recent_deaths) == 1
    assert state.inspected_critter_id is None
    assert state.inspection_death_snapshot is None
    assert tuple(state.inspected_trail) == ()


def test_ttl_continues_after_round_trip_and_expires_on_next_step(
    tmp_path, monkeypatch
):
    state.tick_count = 2099
    snapshot = _snapshot(tick=100)
    _record(snapshot)
    path = tmp_path / "world.pkl"
    assert persistence.save(str(path)) is True
    state.recent_deaths.clear()
    assert persistence.load(str(path)) is True
    assert len(state.recent_deaths) == 1

    monkeypatch.setattr(simulation, "evaluate_and_move", lambda _li: None)
    monkeypatch.setattr(simulation, "fill_fields", lambda: None)
    monkeypatch.setattr(simulation, "_update_trail", lambda: None)
    monkeypatch.setattr(simulation, "compute_ecology_resolution", lambda: object())
    monkeypatch.setattr(simulation, "apply_ecology_resolution", lambda _r: None)
    monkeypatch.setattr(simulation, "_take_reproduction_turn", lambda: None)

    simulation.step()

    assert state.tick_count == 2100
    assert state.get_recent_deaths() == ()


def test_load_rejects_expired_snapshot(tmp_path):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    data["tick"] = 2100
    data["mortes_recentes"][0]["tick"] = 100
    _write(path, data)
    assert persistence.load(str(path)) is False


def test_load_rejects_future_death_tick(tmp_path):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    data["mortes_recentes"][0]["tick"] = data["tick"] + 1
    _write(path, data)
    assert persistence.load(str(path)) is False


def test_load_rejects_death_ticks_out_of_order(tmp_path):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    first = data["mortes_recentes"][0]
    first["tick"] = 90
    middle = copy.deepcopy(first)
    middle["id"] = 5
    middle["tick"] = 100
    last = copy.deepcopy(first)
    last["id"] = 6
    last["tick"] = 95
    data["mortes"] = 3
    data["mortes_recentes"] = [first, middle, last]
    _write(path, data)
    assert persistence.load(str(path)) is False


def test_load_rejects_duplicate_death_id(tmp_path):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    duplicate = copy.deepcopy(data["mortes_recentes"][0])
    data["mortes"] = 2
    data["mortes_recentes"].append(duplicate)
    _write(path, data)
    assert persistence.load(str(path)) is False


def test_load_rejects_living_dead_id_collision(tmp_path):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    data["mortes_recentes"][0]["id"] = data["linhagens"][0]["ids"][0]
    _write(path, data)
    assert persistence.load(str(path)) is False


def test_load_rejects_future_death_id(tmp_path):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    data["mortes_recentes"][0]["id"] = data["proximo_id"]
    _write(path, data)
    assert persistence.load(str(path)) is False


@pytest.mark.parametrize("bad", ["X", "Red", "", None])
def test_load_rejects_invalid_death_lineage(tmp_path, bad):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    data["mortes_recentes"][0]["linhagem"] = bad
    _write(path, data)
    assert persistence.load(str(path)) is False


@pytest.mark.parametrize(
    "case",
    ["list", "float64", "shape", "x_nan", "y_nan", "x_fraction", "y_oob"],
)
def test_load_rejects_invalid_death_agent(tmp_path, case):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    record = data["mortes_recentes"][0]
    agent = record["agente"]

    if case == "list":
        record["agente"] = agent.tolist()
    elif case == "float64":
        record["agente"] = agent.astype(np.float64)
    elif case == "shape":
        record["agente"] = np.zeros((AGENT_COLUMNS + 1,), dtype=np.float32)
    elif case == "x_nan":
        agent[INDEX_X] = np.nan
    elif case == "y_nan":
        agent[INDEX_Y] = np.nan
    elif case == "x_fraction":
        agent[INDEX_X] = 3.7
    elif case == "y_oob":
        agent[INDEX_Y] = float(layout.LAYOUT.world_height)

    _write(path, data)
    assert persistence.load(str(path)) is False


@pytest.mark.parametrize("case", ["list", "float64", "shape"])
def test_load_rejects_invalid_death_genome(tmp_path, case):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    record = data["mortes_recentes"][0]
    genome = record["genoma"]

    if case == "list":
        record["genoma"] = genome.tolist()
    elif case == "float64":
        record["genoma"] = genome.astype(np.float64)
    elif case == "shape":
        record["genoma"] = np.zeros((cfg.GENOME_SIZE + 1,), dtype=np.float32)

    _write(path, data)
    assert persistence.load(str(path)) is False


def test_load_rejects_missing_recent_deaths_key(tmp_path):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    del data["mortes_recentes"]
    _write(path, data)
    assert persistence.load(str(path)) is False


def test_v22_is_rejected_without_migration(tmp_path):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    data["versao"] = 22
    _write(path, data)
    assert persistence.load(str(path)) is False


def test_failed_load_preserves_archive_and_dead_inspection_atomically(tmp_path):
    path, _ = _valid_save_with_one_death(tmp_path)
    data = _read(path)
    data["mortes_recentes"][0]["genoma"] = np.zeros(
        (cfg.GENOME_SIZE + 1,), dtype=np.float32
    )
    _write(path, data)

    sentinel = _snapshot(
        critter_id=8,
        lineage_index=1,
        tick=99,
        x=50,
        y=51,
        marker=9.0,
    )
    state.recent_deaths.clear()
    state.deaths = 1
    state.record_death_snapshot(sentinel)
    state.set_inspection_death_selection(sentinel)
    state.inspected_trail.extend(((50, 51), (51, 51)))
    archive_ref = state.recent_deaths
    before = tuple(state.recent_deaths)
    trail_before = tuple(state.inspected_trail)

    assert persistence.load(str(path)) is False

    assert state.recent_deaths is archive_ref
    assert tuple(state.recent_deaths) == before
    assert state.recent_deaths[0] is sentinel
    assert state.inspected_critter_id == sentinel.critter_id
    assert state.inspection_death_snapshot is sentinel
    assert tuple(state.inspected_trail) == trail_before


def test_save_rejects_expired_runtime_snapshot_without_gc(tmp_path):
    state.tick_count = 2100
    snapshot = _snapshot(tick=100)
    _record(snapshot)
    archive_ref = state.recent_deaths

    assert persistence.save(str(tmp_path / "world.pkl")) is False
    assert state.recent_deaths is archive_ref
    assert state.get_recent_deaths() == (snapshot,)
