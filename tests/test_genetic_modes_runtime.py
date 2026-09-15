"""Patch 7: genetic operator modes are hot RuntimeRules."""

from __future__ import annotations

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import evolution
from primordial_soup import genetics
from primordial_soup import state
from primordial_soup import world
from primordial_soup.runtime_rules import default_runtime_rules, updated_runtime_rules
from primordial_soup.state import agents
from primordial_soup.world import AGENT_COLUMNS, INDEX_HP, INDEX_TIME, INDEX_X, INDEX_Y


@pytest.fixture(autouse=True)
def _restore_runtime():
    state.set_runtime_rules(default_runtime_rules())
    yield
    state.set_runtime_rules(default_runtime_rules())
    agents.clear()


@pytest.mark.parametrize("mode", cfg.CROSSOVER_MODES)
def test_crossover_mode_accepts_canonical_values(mode):
    rules = updated_runtime_rules(default_runtime_rules(), crossover_mode=mode)
    assert rules.crossover_mode == mode
    assert type(rules.crossover_mode) is str


@pytest.mark.parametrize("mode", cfg.MUTATION_MODES)
def test_mutation_mode_accepts_canonical_values(mode):
    rules = updated_runtime_rules(default_runtime_rules(), mutation_mode=mode)
    assert rules.mutation_mode == mode
    assert type(rules.mutation_mode) is str


@pytest.mark.parametrize(
    "field,bad",
    [
        ("crossover_mode", "Blocks"),
        ("crossover_mode", " blocks "),
        ("crossover_mode", "two points"),
        ("crossover_mode", "two-points"),
        ("crossover_mode", ""),
        ("crossover_mode", None),
        ("crossover_mode", True),
        ("crossover_mode", 1),
        ("crossover_mode", b"blocks"),
        ("mutation_mode", "Two_Scales"),
        ("mutation_mode", "two scales"),
        ("mutation_mode", " surgical "),
        ("mutation_mode", "cirurgica"),
        ("mutation_mode", ""),
        ("mutation_mode", None),
        ("mutation_mode", False),
        ("mutation_mode", 0),
        ("mutation_mode", b"surgical"),
    ],
)
def test_genetic_modes_reject_invalid_without_normalization(field, bad):
    before = state.runtime_rules
    with pytest.raises(ValueError):
        state.update_runtime_rules(**{field: bad})
    assert state.runtime_rules is before


def test_genetic_mode_noop_preserves_identity_and_change_replaces():
    before = state.runtime_rules
    state.update_runtime_rules(crossover_mode=before.crossover_mode)
    state.update_runtime_rules(mutation_mode=before.mutation_mode)
    assert state.runtime_rules is before

    state.update_runtime_rules(crossover_mode="two_points", mutation_mode="surgical")
    assert state.runtime_rules is not before
    assert state.runtime_rules.crossover_mode == "two_points"
    assert state.runtime_rules.mutation_mode == "surgical"


def test_build_mask_dispatches_explicit_crossover_mode(monkeypatch):
    calls: list[tuple[str, float | int | None]] = []

    def fake_uniform(n, g, crossover_probability):
        calls.append(("uniform", crossover_probability))
        return np.zeros((n, g), dtype=bool)

    def fake_blocks(n, g, block_size):
        calls.append(("blocks", block_size))
        return np.ones((n, g), dtype=bool)

    def fake_two_points(n, g):
        calls.append(("two_points", None))
        return np.ones((n, g), dtype=bool)

    monkeypatch.setattr(genetics, "_uniform_mask", fake_uniform)
    monkeypatch.setattr(genetics, "_blocks_mask", fake_blocks)
    monkeypatch.setattr(genetics, "_two_points_mask", fake_two_points)

    for mode in cfg.CROSSOVER_MODES:
        genetics._build_mask(
            2,
            3,
            mode,
            crossover_probability=0.73,
            block_size=17,
        )
    assert calls == [
        ("blocks", 17),
        ("uniform", 0.73),
        ("two_points", None),
    ]

    with pytest.raises(ValueError, match="Unknown crossover_mode"):
        genetics._build_mask(
            2,
            3,
            "unknown",
            crossover_probability=0.73,
            block_size=17,
        )


def test_mutate_batch_dispatches_explicit_mutation_mode(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        genetics,
        "_mutate_surgical",
        lambda *args: calls.append("surgical"),
    )
    monkeypatch.setattr(
        genetics,
        "_mutate_two_scales",
        lambda *args, **kwargs: calls.append("two_scales"),
    )
    brood = np.zeros((1, 4), dtype=np.float32)

    genetics._mutate_batch(
        brood,
        1.0,
        1,
        5,
        mutation_mode="surgical",
        local_scale_sigma=0.1,
        global_probability=10,
        global_scale_fraction=20,
        global_scale_sigma=1.0,
    )
    assert calls == ["surgical"]

    calls.clear()
    genetics._mutate_batch(
        brood,
        1.0,
        1,
        5,
        mutation_mode="two_scales",
        local_scale_sigma=0.1,
        global_probability=10,
        global_scale_fraction=20,
        global_scale_sigma=1.0,
    )
    assert calls == ["two_scales"]

    with pytest.raises(ValueError, match="Unknown mutation_mode"):
        genetics._mutate_batch(
            brood,
            1.0,
            1,
            5,
            mutation_mode="unknown",
            local_scale_sigma=0.1,
            global_probability=10,
            global_scale_fraction=20,
            global_scale_sigma=1.0,
        )


def test_crossover_and_mutate_propagates_both_modes_and_ignores_cfg(monkeypatch):
    seen_masks: list[tuple[str, float, int]] = []
    seen_mutations: list[str] = []

    def fake_mask(
        n,
        g,
        crossover_mode,
        *,
        crossover_probability,
        block_size,
    ):
        seen_masks.append(
            (crossover_mode, crossover_probability, block_size)
        )
        return np.ones((n, g), dtype=bool)

    def fake_mutate(
        brood,
        probability,
        mutated_genes,
        local_scale_fraction,
        *,
        mutation_mode,
        local_scale_sigma,
        global_probability,
        global_scale_fraction,
        global_scale_sigma,
    ):
        seen_mutations.append(mutation_mode)

    monkeypatch.setattr(genetics, "_build_mask", fake_mask)
    monkeypatch.setattr(genetics, "_mutate_batch", fake_mutate)
    monkeypatch.setattr(cfg, "CROSSOVER_MODE", "blocks")
    monkeypatch.setattr(cfg, "CROSSOVER_PROBABILITY", 0.01)
    monkeypatch.setattr(cfg, "BLOCK_SIZE", 999)
    monkeypatch.setattr(cfg, "MUTATION_MODE", "two_scales")

    parent1 = np.zeros(cfg.GENOME_SIZE, dtype=np.float32)
    parent2 = np.ones(cfg.GENOME_SIZE, dtype=np.float32)
    genetics.crossover_and_mutate(
        parent1,
        parent2,
        1,
        mutation_rate=100,
        mutated_genes=1,
        local_scale_fraction=5,
        crossover_mode="two_points",
        crossover_probability=0.73,
        block_size=17,
        mutation_mode="surgical",
        local_scale_sigma=0.1,
        global_probability=10,
        global_scale_fraction=20,
        global_scale_sigma=1.0,
    )

    assert seen_masks == [("two_points", 0.73, 17)]
    assert seen_mutations == ["surgical", "surgical"]


def _valid_test_nests():
    """Geometria deterministica de ninhos valida para o contrato v21.

    Tres centros na mesma linha, separados por 2*radius+1, de modo
    que os discos de radius NEST_RADIUS nao compartilhem celulas.
    """
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


def _prepare_hot_switch_world() -> None:
    world.seed_lineages()
    matrix = np.zeros((2, AGENT_COLUMNS), dtype=np.float32)
    matrix[:, INDEX_HP] = 5000.0
    matrix[:, INDEX_TIME] = 1.0
    matrix[:, INDEX_X] = 0.0
    matrix[:, INDEX_Y] = 0.0
    agents[0]["agents"] = matrix
    agents[0]["pool"] = np.zeros((2, cfg.GENOME_SIZE), dtype=np.float32)
    agents[0]["ids"] = np.array([1, 2], dtype=np.int64)
    state.zones = None
    state.nests = _valid_test_nests()
    state.update_runtime_rules(
        base_decay_per_tick=0,
        reproduction_min_age=0,
        reproduction_hp_gate=cfg.MAX_REPRODUCTION_HP_GATE,
        reproduction_min_encounters=0,
        reproduction_min_score=0.0,
        reproduction_attempts_divisor=cfg.MAX_REPRODUCTION_ATTEMPTS_DIVISOR,
    )


def test_hot_switch_reaches_next_reproductive_event(monkeypatch):
    _prepare_hot_switch_world()
    seen: list[tuple[str, str, int]] = []

    def fake_reproduce_one_pair(
        *args,
        crossover_mode,
        mutation_mode,
        lineage_index,
        **kwargs,
    ):
        seen.append((crossover_mode, mutation_mode, lineage_index))
        return []

    monkeypatch.setattr(
        evolution, "_reproduce_one_pair", fake_reproduce_one_pair
    )
    monkeypatch.setattr(cfg, "CROSSOVER_MODE", "uniform")
    monkeypatch.setattr(cfg, "MUTATION_MODE", "two_scales")

    state.update_runtime_rules(
        crossover_mode="blocks", mutation_mode="two_scales"
    )
    evolution.reproduce_lineage(0)

    state.update_runtime_rules(
        crossover_mode="two_points", mutation_mode="surgical"
    )
    evolution.reproduce_lineage(0)

    assert seen == [
        ("blocks", "two_scales", 0),
        ("two_points", "surgical", 0),
    ]
# ---------------------------------------------------------------------------
# Patch 9: two_scales hot tuning
# ---------------------------------------------------------------------------


def _run_two_scales_with_spy(monkeypatch, *, global_probability, global_fraction=20,
                              local_sigma=0.25, global_sigma=2.0):
    calls = []

    def fake_rand(size):
        return np.zeros(size, dtype=float)

    def fake_apply_noise(brood, idx_mut, fraction, sigma):
        calls.append((idx_mut.copy(), fraction, sigma))

    monkeypatch.setattr(np.random, "rand", fake_rand)
    monkeypatch.setattr(genetics, "_apply_noise", fake_apply_noise)

    brood = np.zeros((3, 8), dtype=np.float32)
    genetics._mutate_two_scales(
        brood,
        1.0,
        5,
        local_scale_sigma=local_sigma,
        global_probability=global_probability,
        global_scale_fraction=global_fraction,
        global_scale_sigma=global_sigma,
    )
    return calls


def test_two_scales_global_probability_zero_is_local_only(monkeypatch):
    calls = _run_two_scales_with_spy(monkeypatch, global_probability=0)
    global_call, local_call = calls
    assert global_call[0].size == 0
    assert local_call[0].tolist() == [0, 1, 2]
    assert local_call[1:] == (0.05, 0.25)


def test_two_scales_global_probability_hundred_is_global_only(monkeypatch):
    calls = _run_two_scales_with_spy(
        monkeypatch,
        global_probability=100,
        global_fraction=75,
        global_sigma=2.0,
    )
    global_call, local_call = calls
    assert global_call[0].tolist() == [0, 1, 2]
    assert global_call[1:] == (0.75, 2.0)
    assert local_call[0].size == 0


def test_two_scales_runtime_values_ignore_cfg(monkeypatch):
    monkeypatch.setattr(cfg, "LOCAL_SCALE_SIGMA", 3.75)
    monkeypatch.setattr(cfg, "GLOBAL_PROBABILITY", 0.0)
    monkeypatch.setattr(cfg, "GLOBAL_SCALE_FRACTION", 0.01)
    monkeypatch.setattr(cfg, "GLOBAL_SCALE_SIGMA", 0.02)

    calls = _run_two_scales_with_spy(
        monkeypatch,
        global_probability=100,
        global_fraction=75,
        local_sigma=0.25,
        global_sigma=2.0,
    )
    global_call, local_call = calls
    assert global_call[0].tolist() == [0, 1, 2]
    assert global_call[1:] == (0.75, 2.0)
    assert local_call[1:] == (0.05, 0.25)


def test_crossover_and_mutate_propagates_two_scale_tuning(monkeypatch):
    seen = []

    monkeypatch.setattr(
        genetics,
        "_build_mask",
        lambda n, g, mode, **kwargs: np.ones((n, g), dtype=bool),
    )

    def fake_mutate(brood, probability, mutated_genes, local_scale_fraction, **kwargs):
        seen.append((probability, mutated_genes, local_scale_fraction, kwargs))

    monkeypatch.setattr(genetics, "_mutate_batch", fake_mutate)
    parent1 = np.zeros(cfg.GENOME_SIZE, dtype=np.float32)
    parent2 = np.ones(cfg.GENOME_SIZE, dtype=np.float32)

    genetics.crossover_and_mutate(
        parent1,
        parent2,
        1,
        mutation_rate=100,
        mutated_genes=3,
        local_scale_fraction=5,
        crossover_mode="blocks",
        crossover_probability=0.5,
        block_size=64,
        mutation_mode="two_scales",
        local_scale_sigma=0.25,
        global_probability=75,
        global_scale_fraction=40,
        global_scale_sigma=2.0,
    )

    assert len(seen) == 2
    for probability, mutated_genes, local_scale_fraction, kwargs in seen:
        assert probability == 1.0
        assert mutated_genes == 3
        assert local_scale_fraction == 5
        assert kwargs == {
            "mutation_mode": "two_scales",
            "local_scale_sigma": 0.25,
            "global_probability": 75,
            "global_scale_fraction": 40,
            "global_scale_sigma": 2.0,
        }