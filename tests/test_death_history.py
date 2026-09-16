"""Contratos do historico recente de mortes do Patch 4."""

from __future__ import annotations

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import layout
from primordial_soup import simulation
from primordial_soup import state
from primordial_soup import world
from primordial_soup.state import agents
from primordial_soup.world import AGENT_COLUMNS, INDEX_X, INDEX_Y


def _snapshot(
    *,
    critter_id: int = 1,
    lineage_index: int = 0,
    tick: int = 1,
    x: int = 10,
    y: int = 10,
) -> state.DeathSnapshot:
    agent = np.zeros((AGENT_COLUMNS,), dtype=np.float32)
    agent[INDEX_X] = float(x)
    agent[INDEX_Y] = float(y)
    genome = np.zeros((cfg.GENOME_SIZE,), dtype=np.float32)
    return state.DeathSnapshot(
        critter_id=critter_id,
        lineage_index=lineage_index,
        lineage_id=cfg.LINEAGES[lineage_index]["id"],
        tick=tick,
        agent=agent,
        genome=genome,
    )


@pytest.fixture(autouse=True)
def _clean_state():
    state.reset_counters()
    agents.clear()
    yield
    state.reset_counters()
    agents.clear()


def test_record_death_snapshot_preserves_order_identity_and_tuple_view():
    first = _snapshot(critter_id=1, tick=10)
    second = _snapshot(critter_id=2, tick=10)

    state.record_death_snapshot(first)
    state.record_death_snapshot(second)

    view = state.get_recent_deaths()
    assert isinstance(view, tuple)
    assert view == (first, second)
    assert view[0] is first
    assert view[1] is second
    assert state.recent_deaths.maxlen is None


def test_record_death_snapshot_rejects_regressive_tick_without_mutation():
    first = _snapshot(critter_id=1, tick=100)
    state.record_death_snapshot(first)

    with pytest.raises(ValueError):
        state.record_death_snapshot(_snapshot(critter_id=2, tick=99))

    assert state.get_recent_deaths() == (first,)


def test_observed_death_installs_same_snapshot_and_preserves_trail():
    snapshot = _snapshot(critter_id=7, tick=25)
    state.set_inspection_selection(7)
    state.inspected_trail.extend(((1, 2), (3, 4)))

    state.record_death_snapshot(snapshot)

    assert state.recent_deaths[-1] is snapshot
    assert state.inspection_death_snapshot is snapshot
    assert tuple(state.inspected_trail) == ((1, 2), (3, 4))


def test_other_death_does_not_replace_inspection_snapshot():
    observed = _snapshot(critter_id=7, tick=20)
    other = _snapshot(critter_id=8, tick=21)
    state.set_inspection_death_selection(observed)

    state.record_death_snapshot(other)

    assert state.recent_deaths[-1] is other
    assert state.inspection_death_snapshot is observed


def test_set_inspection_death_selection_is_atomic_and_trail_semantics_hold():
    first = _snapshot(critter_id=11, tick=20)
    second = _snapshot(critter_id=12, tick=20)

    state.set_inspection_selection(99)
    state.inspected_trail.extend(((5, 5), (6, 6)))
    state.set_inspection_death_selection(first)
    assert state.inspected_critter_id == 11
    assert state.inspection_death_snapshot is first
    assert tuple(state.inspected_trail) == ()

    state.inspected_trail.append((7, 7))
    state.set_inspection_death_selection(first)
    assert tuple(state.inspected_trail) == ((7, 7),)
    assert state.inspection_death_snapshot is first

    state.set_inspection_death_selection(second)
    assert state.inspected_critter_id == 12
    assert state.inspection_death_snapshot is second
    assert tuple(state.inspected_trail) == ()


def test_expiration_boundary_and_return_count():
    snapshot = _snapshot(critter_id=1, tick=100)
    state.record_death_snapshot(snapshot)

    assert state.expire_recent_deaths(current_tick=2099) == 0
    assert state.get_recent_deaths() == (snapshot,)
    assert state.expire_recent_deaths(current_tick=2100) == 1
    assert state.get_recent_deaths() == ()


def test_expiration_preserves_active_dead_inspection():
    snapshot = _snapshot(critter_id=1, tick=100)
    state.record_death_snapshot(snapshot)
    state.set_inspection_death_selection(snapshot)

    assert state.expire_recent_deaths(current_tick=2100) == 1
    assert snapshot not in state.get_recent_deaths()
    assert state.inspection_death_snapshot is snapshot
    assert state.inspected_critter_id == snapshot.critter_id


def test_find_recent_death_exact_radius_hit_and_miss():
    exact = _snapshot(critter_id=1, tick=10, x=20, y=20)
    adjacent = _snapshot(critter_id=2, tick=10, x=21, y=20)
    state.record_death_snapshot(exact)
    state.record_death_snapshot(adjacent)

    assert world.find_recent_death_at(20, 20, radius=0) is exact
    assert world.find_recent_death_at(19, 20, radius=0) is None
    assert world.find_recent_death_at(20, 20, radius=1) is exact


def test_find_recent_death_uses_toroidal_distance():
    snapshot = _snapshot(
        critter_id=1,
        tick=10,
        x=0,
        y=10,
    )
    state.record_death_snapshot(snapshot)

    assert world.find_recent_death_at(
        layout.LAYOUT.world_width - 1,
        10,
        radius=1,
    ) is snapshot


def test_find_recent_death_nearest_wins_over_recency():
    nearest = _snapshot(critter_id=1, tick=10, x=50, y=50)
    newer = _snapshot(critter_id=2, tick=11, x=53, y=50)
    state.record_death_snapshot(nearest)
    state.record_death_snapshot(newer)

    assert world.find_recent_death_at(50, 50, radius=4) is nearest


def test_find_recent_death_newest_append_wins_distance_tie_same_tick():
    older_append = _snapshot(critter_id=1, tick=10, x=49, y=50)
    newer_append = _snapshot(critter_id=2, tick=10, x=51, y=50)
    state.record_death_snapshot(older_append)
    state.record_death_snapshot(newer_append)

    assert world.find_recent_death_at(50, 50, radius=2) is newer_append


def test_reset_counters_clears_archive_in_place():
    archive = state.recent_deaths
    state.record_death_snapshot(_snapshot(critter_id=1, tick=1))

    state.reset_counters()

    assert state.recent_deaths is archive
    assert state.get_recent_deaths() == ()


def test_recreate_clears_archive_through_bootstrap(monkeypatch):
    from primordial_soup import controls

    state.record_death_snapshot(_snapshot(critter_id=1, tick=1))
    calls = []

    def fake_bootstrap():
        calls.append("bootstrap")
        state.reset_counters()

    monkeypatch.setattr(controls, "bootstrap_new_world", fake_bootstrap)
    controls.recreate()

    assert calls == ["bootstrap"]
    assert state.get_recent_deaths() == ()


def test_step_expires_after_tick_increment_before_movement(monkeypatch):
    events = []

    def fake_expire(*, current_tick=None):
        events.append(("expire", state.tick_count, current_tick))
        return 0

    def fake_move(lineage_index):
        events.append(("move", state.tick_count, lineage_index))

    monkeypatch.setattr(state, "expire_recent_deaths", fake_expire)
    monkeypatch.setattr(simulation, "evaluate_and_move", fake_move)
    monkeypatch.setattr(simulation, "fill_fields", lambda: None)
    monkeypatch.setattr(simulation, "_update_trail", lambda: None)
    monkeypatch.setattr(simulation, "compute_ecology_resolution", lambda: object())
    monkeypatch.setattr(simulation, "apply_ecology_resolution", lambda _r: None)
    monkeypatch.setattr(simulation, "_take_reproduction_turn", lambda: None)

    state.tick_count = 0
    result = simulation.step()

    assert events[0] == ("expire", 1, None)
    assert events[1] == ("move", 1, 0)
    assert [event[0] for event in events].count("expire") == 1
    assert result.birth_lineage is None
    assert result.birth_count == 0
