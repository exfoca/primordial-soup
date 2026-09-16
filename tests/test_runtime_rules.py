"""Testes da fundacao de RuntimeRules (Patch 1).

Cobrem o contrato do dataclass, da validacao centralizada e da API
state.update_runtime_rules / state.set_runtime_rules.

Todos os docstrings deste arquivo sao intencionalmente ASCII puro.
"""

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import state
from primordial_soup.runtime_rules import (
    RuntimeRules,
    default_runtime_rules,
    updated_runtime_rules,
    validate_runtime_rules,
)
from primordial_soup.state import agents


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def test_defaults_match_config():
    rules = default_runtime_rules()
    assert rules.crossover_mode == cfg.CROSSOVER_MODE
    assert rules.mutation_mode == cfg.MUTATION_MODE
    assert rules.mutation_rate == int(cfg.INITIAL_MUTATION_RATE)
    assert rules.mutated_genes == int(cfg.INITIAL_MUTATED_GENES)
    assert rules.local_scale_fraction == int(cfg.LOCAL_SCALE_FRACTION * 100)
    assert rules.local_scale_sigma == float(cfg.LOCAL_SCALE_SIGMA)
    assert rules.global_probability == int(cfg.GLOBAL_PROBABILITY * 100)
    assert rules.global_scale_fraction == int(cfg.GLOBAL_SCALE_FRACTION * 100)
    assert rules.global_scale_sigma == float(cfg.GLOBAL_SCALE_SIGMA)
    assert rules.low_hp_threshold == int(cfg.LOW_HP_THRESHOLD)
    assert rules.stay_still_impulse == float(cfg.STAY_STILL_IMPULSE)
    assert rules.death_hp_threshold == int(cfg.DIE_WHEN_HP_LESS_OR_EQUAL)
    assert rules.zone_hp_effect == int(cfg.HP_EFFECT_IN_ZONE)
    assert rules.base_decay_per_tick == int(cfg.BASE_DECAY_PER_TICK)
    assert rules.predation_transfer == int(cfg.PREDATION_TRANSFER)
    assert (
        rules.damage_per_own_overcrowding
        == int(cfg.DAMAGE_PER_OWN_OVERCROWDING)
    )
    assert rules.reproduction_interval == int(cfg.REPRODUCTION_INTERVAL)
    assert rules.reproduction_min_age == int(cfg.REPRODUCTION_MIN_AGE)
    assert rules.reproduction_hp_gate == int(cfg.REPRODUCTION_HP_GATE)
    assert (
        rules.reproduction_min_encounters
        == int(cfg.REPRODUCTION_MIN_ENCOUNTERS)
    )
    assert (
        rules.reproduction_parent_hp_bonus
        == int(cfg.REPRODUCTION_PARENT_HP_BONUS)
    )
    assert rules.reproduction_criterion == cfg.REPRODUCTION_CRITERION
    assert rules.reproduction_pool_fraction == float(
        cfg.REPRODUCTIVE_POOL_FRACTION
    )
    assert rules.reproduction_attempts_divisor == int(
        cfg.REPRODUCTION_ATTEMPTS_DIVISOR
    )
    assert rules.reproduction_min_score == float(cfg.REPRODUCTION_MIN_SCORE)
    assert rules.longevity_weight == float(cfg.LONGEVITY_WEIGHT)
    assert rules.exploration_weight == float(cfg.EXPLORATION_WEIGHT)
    assert rules.interaction_weight == float(cfg.INTERACTION_WEIGHT)
    assert rules.reproduction_weight == float(cfg.REPRODUCTION_WEIGHT)




def test_runtime_rules_has_expected_fields():
    from dataclasses import fields

    names = {f.name for f in fields(RuntimeRules)}
    assert len(names) == 31
    assert "predation_transfer" in names
    assert "damage_per_own_overcrowding" in names


@pytest.mark.parametrize(
    "field,minimum,maximum",
    [
        ("low_hp_threshold", cfg.MIN_LOW_HP_THRESHOLD, cfg.MAX_LOW_HP_THRESHOLD),
        (
            "death_hp_threshold",
            cfg.MIN_DEATH_HP_THRESHOLD,
            cfg.MAX_DEATH_HP_THRESHOLD,
        ),
    ],
)
def test_hp_thresholds_are_strict_ints_in_closed_range(field, minimum, maximum):
    rules = default_runtime_rules()
    assert type(getattr(rules, field)) is int
    assert getattr(updated_runtime_rules(rules, **{field: minimum}), field) == minimum
    assert getattr(updated_runtime_rules(rules, **{field: maximum}), field) == maximum

    for bad in (True, False, -1, maximum + 1, 1.0, None):
        with pytest.raises(ValueError):
            updated_runtime_rules(rules, **{field: bad})


@pytest.mark.parametrize("value", [-5.0, -1.0, 0.0, 0.5, 1.0, 25.0])
def test_stay_still_impulse_accepts_any_finite_builtin_float(value):
    rules = updated_runtime_rules(
        default_runtime_rules(),
        stay_still_impulse=value,
    )
    assert type(rules.stay_still_impulse) is float
    assert rules.stay_still_impulse == value


@pytest.mark.parametrize(
    "bad",
    [1, True, False, float("nan"), float("inf"), float("-inf"), None],
)
def test_stay_still_impulse_rejects_non_float_or_non_finite(bad):
    with pytest.raises(ValueError):
        updated_runtime_rules(default_runtime_rules(), stay_still_impulse=bad)


def test_lifecycle_invalid_update_is_atomic_and_same_value_is_identity_noop():
    original = state.runtime_rules
    try:
        state.set_runtime_rules(default_runtime_rules())
        before = state.runtime_rules
        with pytest.raises(ValueError):
            state.update_runtime_rules(stay_still_impulse=float("nan"))
        assert state.runtime_rules is before

        state.update_runtime_rules(
            low_hp_threshold=before.low_hp_threshold,
            stay_still_impulse=before.stay_still_impulse,
            death_hp_threshold=before.death_hp_threshold,
        )
        assert state.runtime_rules is before
    finally:
        state.set_runtime_rules(original)


def test_reproduction_criterion_default_is_builtin_str():
    assert type(default_runtime_rules().reproduction_criterion) is str


@pytest.mark.parametrize("criterion", cfg.REPRODUCTION_CRITERIA)
def test_reproduction_criterion_accepts_only_canonical_values(criterion):
    current = default_runtime_rules()
    updated = updated_runtime_rules(
        current,
        reproduction_criterion=criterion,
    )
    assert updated.reproduction_criterion == criterion


@pytest.mark.parametrize(
    "bad",
    [
        "Composite",
        "COMPOSITE",
        " longevity ",
        "score",
        "oldest",
        "",
        None,
        True,
        False,
        0,
        1,
        0.0,
        b"composite",
        object(),
    ],
)
def test_reproduction_criterion_rejects_invalid_without_normalization(bad):
    current = default_runtime_rules()
    with pytest.raises(ValueError):
        updated_runtime_rules(current, reproduction_criterion=bad)


def test_invalid_reproduction_criterion_update_preserves_state_identity():
    before = state.runtime_rules
    with pytest.raises(ValueError):
        state.update_runtime_rules(reproduction_criterion="Composite")
    assert state.runtime_rules is before


def test_reproduction_criterion_same_value_preserves_identity():
    state.update_runtime_rules(reproduction_criterion="composite")
    before = state.runtime_rules
    state.update_runtime_rules(reproduction_criterion="composite")
    assert state.runtime_rules is before


def test_reproduction_criterion_change_creates_new_instance():
    state.update_runtime_rules(reproduction_criterion="composite")
    before = state.runtime_rules
    state.update_runtime_rules(reproduction_criterion="longevity")
    assert state.runtime_rules is not before
    assert state.runtime_rules.reproduction_criterion == "longevity"


@pytest.mark.parametrize(
    "field",
    [
        "reproduction_pool_fraction",
        "reproduction_min_score",
        "longevity_weight",
        "exploration_weight",
        "interaction_weight",
        "reproduction_weight",
    ],
)
def test_selection_float_fields_are_builtin_float(field):
    assert type(getattr(default_runtime_rules(), field)) is float


@pytest.mark.parametrize(
    "field,minimum,maximum",
    [
        (
            "reproduction_pool_fraction",
            cfg.MIN_REPRODUCTION_POOL_FRACTION,
            cfg.MAX_REPRODUCTION_POOL_FRACTION,
        ),
        (
            "reproduction_min_score",
            cfg.MIN_REPRODUCTION_MIN_SCORE,
            cfg.MAX_REPRODUCTION_MIN_SCORE,
        ),
        ("longevity_weight", cfg.MIN_SELECTION_WEIGHT, cfg.MAX_SELECTION_WEIGHT),
        ("exploration_weight", cfg.MIN_SELECTION_WEIGHT, cfg.MAX_SELECTION_WEIGHT),
        ("interaction_weight", cfg.MIN_SELECTION_WEIGHT, cfg.MAX_SELECTION_WEIGHT),
        ("reproduction_weight", cfg.MIN_SELECTION_WEIGHT, cfg.MAX_SELECTION_WEIGHT),
    ],
)
@pytest.mark.parametrize("bad_kind", ["below", "above", "bool", "int", "nan", "inf", "ninf"])
def test_selection_float_validation_is_strict(field, minimum, maximum, bad_kind):
    values = {
        "below": float(minimum - 0.1),
        "above": float(maximum + 0.1),
        "bool": True,
        "int": 1,
        "nan": float("nan"),
        "inf": float("inf"),
        "ninf": float("-inf"),
    }
    current = default_runtime_rules()
    with pytest.raises(ValueError):
        updated_runtime_rules(current, **{field: values[bad_kind]})


def test_invalid_selection_update_preserves_state_identity():
    before = state.runtime_rules
    with pytest.raises(ValueError):
        state.update_runtime_rules(longevity_weight=float("nan"))
    assert state.runtime_rules is before



def test_reproduction_pressure_runtime_types_are_strict_builtins():
    rules = default_runtime_rules()
    assert type(rules.reproduction_pool_fraction) is float
    assert type(rules.reproduction_attempts_divisor) is int


@pytest.mark.parametrize(
    "value",
    [
        cfg.MIN_REPRODUCTION_POOL_FRACTION,
        cfg.MAX_REPRODUCTION_POOL_FRACTION,
    ],
)
def test_reproduction_pool_fraction_accepts_closed_range(value):
    rules = updated_runtime_rules(
        default_runtime_rules(),
        reproduction_pool_fraction=float(value),
    )
    assert rules.reproduction_pool_fraction == float(value)


@pytest.mark.parametrize(
    "bad",
    [
        0.0,
        0.009,
        1.001,
        0,
        1,
        True,
        False,
        None,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_reproduction_pool_fraction_rejects_invalid_values(bad):
    with pytest.raises(ValueError):
        updated_runtime_rules(
            default_runtime_rules(),
            reproduction_pool_fraction=bad,
        )


@pytest.mark.parametrize(
    "value",
    [
        cfg.MIN_REPRODUCTION_ATTEMPTS_DIVISOR,
        cfg.MAX_REPRODUCTION_ATTEMPTS_DIVISOR,
    ],
)
def test_reproduction_attempts_divisor_accepts_closed_range(value):
    rules = updated_runtime_rules(
        default_runtime_rules(),
        reproduction_attempts_divisor=value,
    )
    assert rules.reproduction_attempts_divisor == value


@pytest.mark.parametrize(
    "bad",
    [
        0,
        -1,
        cfg.MAX_REPRODUCTION_ATTEMPTS_DIVISOR + 1,
        True,
        False,
        1.0,
        50.0,
        None,
    ],
)
def test_reproduction_attempts_divisor_rejects_invalid_values(bad):
    with pytest.raises(ValueError):
        updated_runtime_rules(
            default_runtime_rules(),
            reproduction_attempts_divisor=bad,
        )


def test_invalid_reproduction_pressure_update_preserves_state_identity():
    before = state.runtime_rules
    with pytest.raises(ValueError):
        state.update_runtime_rules(reproduction_pool_fraction=0.0)
    assert state.runtime_rules is before

    with pytest.raises(ValueError):
        state.update_runtime_rules(reproduction_attempts_divisor=0)
    assert state.runtime_rules is before


def test_reproduction_pressure_noop_preserves_identity():
    state.update_runtime_rules(
        reproduction_pool_fraction=0.57,
        reproduction_attempts_divisor=23,
    )
    before = state.runtime_rules
    state.update_runtime_rules(
        reproduction_pool_fraction=0.57,
        reproduction_attempts_divisor=23,
    )
    assert state.runtime_rules is before

def test_defaults_are_frozen():
    rules = default_runtime_rules()
    with pytest.raises(Exception):
        rules.mutation_rate = 99  # type: ignore[misc]


def test_defaults_are_slots():
    rules = default_runtime_rules()
    assert not hasattr(rules, "__dict__")


# ---------------------------------------------------------------------------
# updated_runtime_rules: candidate -> validate -> retorno
# ---------------------------------------------------------------------------


def test_update_returns_new_object():
    before = default_runtime_rules()
    after = updated_runtime_rules(before, mutation_rate=50)
    assert after is not before
    assert after.mutation_rate == 50
    assert before.mutation_rate == cfg.INITIAL_MUTATION_RATE


def test_update_multiple_fields():
    rules = default_runtime_rules()
    updated = updated_runtime_rules(
        rules,
        mutation_rate=7,
        mutated_genes=3,
        local_scale_fraction=42,
        zone_hp_effect=-25,
    )
    assert updated.mutation_rate == 7
    assert updated.mutated_genes == 3
    assert updated.local_scale_fraction == 42
    assert updated.zone_hp_effect == -25


# ---------------------------------------------------------------------------
# Validacao: ranges
# ---------------------------------------------------------------------------


_INVALID_CASES = [
    ("mutation_below", {"mutation_rate": cfg.MIN_MUTATION_RATE - 1}),
    ("mutation_above", {"mutation_rate": cfg.MAX_MUTATION_RATE + 1}),
    ("mutated_below", {"mutated_genes": cfg.MIN_MUTATED_GENES - 1}),
    ("mutated_above", {"mutated_genes": cfg.MAX_MUTATED_GENES + 1}),
    (
        "local_below",
        {"local_scale_fraction": cfg.MIN_LOCAL_SCALE_FRACTION - 1},
    ),
    (
        "local_above",
        {"local_scale_fraction": cfg.MAX_LOCAL_SCALE_FRACTION + 1},
    ),
    ("zone_below", {"zone_hp_effect": cfg.MIN_ZONE_HP_EFFECT - 1}),
    ("zone_above", {"zone_hp_effect": cfg.MAX_ZONE_HP_EFFECT + 1}),
    ("base_decay_below", {"base_decay_per_tick": -1}),
    (
        "base_decay_above",
        {"base_decay_per_tick": cfg.MAX_BASE_DECAY_PER_TICK + 1},
    ),
    (
        "predation_transfer_below",
        {"predation_transfer": cfg.MIN_PREDATION_TRANSFER - 1},
    ),
    (
        "predation_transfer_above",
        {"predation_transfer": cfg.MAX_PREDATION_TRANSFER + 1},
    ),
    (
        "overcrowding_below",
        {"damage_per_own_overcrowding":
            cfg.MIN_DAMAGE_PER_OWN_OVERCROWDING - 1},
    ),
    (
        "overcrowding_above",
        {"damage_per_own_overcrowding":
            cfg.MAX_DAMAGE_PER_OWN_OVERCROWDING + 1},
    ),
    (
        "repro_interval_below",
        {"reproduction_interval": cfg.MIN_REPRODUCTION_INTERVAL - 1},
    ),
    (
        "repro_interval_above",
        {"reproduction_interval": cfg.MAX_REPRODUCTION_INTERVAL + 1},
    ),
    ("repro_min_age_below", {"reproduction_min_age": -1}),
    (
        "repro_min_age_above",
        {"reproduction_min_age": cfg.MAX_REPRODUCTION_MIN_AGE + 1},
    ),
    ("repro_hp_gate_below", {"reproduction_hp_gate": 0}),
    (
        "repro_hp_gate_above",
        {"reproduction_hp_gate": cfg.MAX_REPRODUCTION_HP_GATE + 1},
    ),
    ("repro_encounters_below", {"reproduction_min_encounters": -1}),
    (
        "repro_encounters_above",
        {"reproduction_min_encounters":
            cfg.MAX_REPRODUCTION_MIN_ENCOUNTERS + 1},
    ),
    ("repro_parent_bonus_below", {"reproduction_parent_hp_bonus": -1}),
    (
        "repro_parent_bonus_above",
        {"reproduction_parent_hp_bonus":
            cfg.MAX_REPRODUCTION_PARENT_HP_BONUS + 1},
    ),
]


@pytest.mark.parametrize(
    "label, changes",
    _INVALID_CASES,
    ids=[c[0] for c in _INVALID_CASES],
)
def test_update_rejects_out_of_range(label, changes):
    rules = default_runtime_rules()
    with pytest.raises(ValueError):
        updated_runtime_rules(rules, **changes)


@pytest.mark.parametrize(
    "label, changes",
    _INVALID_CASES,
    ids=[c[0] for c in _INVALID_CASES],
)
def test_update_rejection_leaves_state_intact(label, changes):
    before = state.runtime_rules
    with pytest.raises(ValueError):
        state.update_runtime_rules(**changes)
    assert state.runtime_rules is before


# ---------------------------------------------------------------------------
# Validacao: tipo estrito (bool nao e int)
# ---------------------------------------------------------------------------


_BOOL_CASES = [
    ("mutation_bool", {"mutation_rate": True}),
    ("mutated_bool", {"mutated_genes": False}),
    ("local_bool", {"local_scale_fraction": True}),
    ("low_hp_bool", {"low_hp_threshold": True}),
    ("stay_still_bool", {"stay_still_impulse": True}),
    ("death_hp_bool", {"death_hp_threshold": True}),
    ("zone_bool", {"zone_hp_effect": True}),
    ("base_decay_bool", {"base_decay_per_tick": True}),
    ("predation_transfer_bool", {"predation_transfer": True}),
    ("overcrowding_bool", {"damage_per_own_overcrowding": True}),
    ("repro_interval_bool", {"reproduction_interval": True}),
    ("repro_min_age_bool", {"reproduction_min_age": True}),
    ("repro_hp_gate_bool", {"reproduction_hp_gate": True}),
    ("repro_encounters_bool", {"reproduction_min_encounters": True}),
    ("repro_parent_bonus_bool", {"reproduction_parent_hp_bonus": True}),
    ("repro_attempts_divisor_bool", {"reproduction_attempts_divisor": True}),
]


@pytest.mark.parametrize(
    "label, changes",
    _BOOL_CASES,
    ids=[c[0] for c in _BOOL_CASES],
)
def test_update_rejects_bool(label, changes):
    rules = default_runtime_rules()
    with pytest.raises(ValueError):
        updated_runtime_rules(rules, **changes)


# ---------------------------------------------------------------------------
# set_runtime_rules: validacao antes de escrever
# ---------------------------------------------------------------------------


def test_set_validates_before_writing():
    before = state.runtime_rules
    bad = RuntimeRules(
        crossover_mode=before.crossover_mode,
        crossover_probability=before.crossover_probability,
        block_size=before.block_size,
        mutation_mode=before.mutation_mode,
        mutation_rate=999,
        mutated_genes=before.mutated_genes,
        local_scale_fraction=before.local_scale_fraction,
        local_scale_sigma=before.local_scale_sigma,
        global_probability=before.global_probability,
        global_scale_fraction=before.global_scale_fraction,
        global_scale_sigma=before.global_scale_sigma,
        low_hp_threshold=before.low_hp_threshold,
        stay_still_impulse=before.stay_still_impulse,
        death_hp_threshold=before.death_hp_threshold,
        zone_hp_effect=before.zone_hp_effect,
        base_decay_per_tick=before.base_decay_per_tick,
        predation_transfer=before.predation_transfer,
        damage_per_own_overcrowding=before.damage_per_own_overcrowding,
        reproduction_interval=before.reproduction_interval,
        reproduction_min_age=before.reproduction_min_age,
        reproduction_hp_gate=before.reproduction_hp_gate,
        reproduction_min_encounters=before.reproduction_min_encounters,
        reproduction_parent_hp_bonus=before.reproduction_parent_hp_bonus,
        reproduction_criterion=before.reproduction_criterion,
        reproduction_pool_fraction=before.reproduction_pool_fraction,
        reproduction_attempts_divisor=before.reproduction_attempts_divisor,
        reproduction_min_score=before.reproduction_min_score,
        longevity_weight=before.longevity_weight,
        exploration_weight=before.exploration_weight,
        interaction_weight=before.interaction_weight,
        reproduction_weight=before.reproduction_weight,
    )
    with pytest.raises(ValueError):
        state.set_runtime_rules(bad)
    assert state.runtime_rules is before


# ---------------------------------------------------------------------------
# reset_counters preserva runtime_rules
# ---------------------------------------------------------------------------


def test_reset_counters_preserves_runtime_rules():
    state.update_runtime_rules(mutation_rate=77)
    before = state.runtime_rules
    state.reset_counters()
    assert state.runtime_rules is before


# ---------------------------------------------------------------------------
# Validacao direta de validate_runtime_rules
# ---------------------------------------------------------------------------


def test_validate_accepts_valid():
    rules = RuntimeRules(
        crossover_mode="two_points",
        crossover_probability=float(cfg.MAX_CROSSOVER_PROBABILITY),
        block_size=cfg.MAX_BLOCK_SIZE,
        mutation_mode="surgical",
        mutation_rate=cfg.MAX_MUTATION_RATE,
        mutated_genes=cfg.MIN_MUTATED_GENES,
        local_scale_fraction=cfg.MAX_LOCAL_SCALE_FRACTION,
        local_scale_sigma=float(cfg.MAX_MUTATION_SIGMA),
        global_probability=cfg.MAX_GLOBAL_PROBABILITY,
        global_scale_fraction=cfg.MAX_GLOBAL_SCALE_FRACTION,
        global_scale_sigma=float(cfg.MAX_MUTATION_SIGMA),
        low_hp_threshold=cfg.MAX_LOW_HP_THRESHOLD,
        stay_still_impulse=-25.0,
        death_hp_threshold=cfg.MAX_DEATH_HP_THRESHOLD,
        zone_hp_effect=cfg.MIN_ZONE_HP_EFFECT,
        base_decay_per_tick=cfg.MAX_BASE_DECAY_PER_TICK,
        predation_transfer=cfg.MAX_PREDATION_TRANSFER,
        damage_per_own_overcrowding=cfg.MAX_DAMAGE_PER_OWN_OVERCROWDING,
        reproduction_interval=cfg.MAX_REPRODUCTION_INTERVAL,
        reproduction_min_age=cfg.MAX_REPRODUCTION_MIN_AGE,
        reproduction_hp_gate=cfg.MAX_REPRODUCTION_HP_GATE,
        reproduction_min_encounters=cfg.MAX_REPRODUCTION_MIN_ENCOUNTERS,
        reproduction_parent_hp_bonus=cfg.MAX_REPRODUCTION_PARENT_HP_BONUS,
        reproduction_criterion="longevity",
        reproduction_pool_fraction=float(cfg.MAX_REPRODUCTION_POOL_FRACTION),
        reproduction_attempts_divisor=cfg.MAX_REPRODUCTION_ATTEMPTS_DIVISOR,
        reproduction_min_score=float(cfg.MAX_REPRODUCTION_MIN_SCORE),
        longevity_weight=float(cfg.MAX_SELECTION_WEIGHT),
        exploration_weight=float(cfg.MAX_SELECTION_WEIGHT),
        interaction_weight=float(cfg.MAX_SELECTION_WEIGHT),
        reproduction_weight=float(cfg.MAX_SELECTION_WEIGHT),
    )
    validate_runtime_rules(rules)  # nao levanta


def test_validate_rejects_type_confusion():
    rules = RuntimeRules(
        crossover_mode=cfg.CROSSOVER_MODE,
        crossover_probability=float(cfg.CROSSOVER_PROBABILITY),
        block_size=int(cfg.BLOCK_SIZE),
        mutation_mode=cfg.MUTATION_MODE,
        mutation_rate=5.0,  # type: ignore[arg-type]
        mutated_genes=1,
        local_scale_fraction=5,
        local_scale_sigma=float(cfg.LOCAL_SCALE_SIGMA),
        global_probability=int(cfg.GLOBAL_PROBABILITY * 100),
        global_scale_fraction=int(cfg.GLOBAL_SCALE_FRACTION * 100),
        global_scale_sigma=float(cfg.GLOBAL_SCALE_SIGMA),
        low_hp_threshold=int(cfg.LOW_HP_THRESHOLD),
        stay_still_impulse=float(cfg.STAY_STILL_IMPULSE),
        death_hp_threshold=int(cfg.DIE_WHEN_HP_LESS_OR_EQUAL),
        zone_hp_effect=5,
        base_decay_per_tick=1,
        predation_transfer=100,
        damage_per_own_overcrowding=100,
        reproduction_interval=150,
        reproduction_min_age=1000,
        reproduction_hp_gate=9000,
        reproduction_min_encounters=3,
        reproduction_parent_hp_bonus=50,
        reproduction_criterion="composite",
        reproduction_pool_fraction=float(cfg.REPRODUCTIVE_POOL_FRACTION),
        reproduction_attempts_divisor=int(cfg.REPRODUCTION_ATTEMPTS_DIVISOR),
        reproduction_min_score=0.6,
        longevity_weight=0.5,
        exploration_weight=0.3,
        interaction_weight=0.3,
        reproduction_weight=0.3,
    )
    with pytest.raises(ValueError):
        validate_runtime_rules(rules)


# ---------------------------------------------------------------------------
# No-op de identidade
# ---------------------------------------------------------------------------


def test_updated_same_value_returns_same_instance():
    """updated_runtime_rules com mudanca efetiva nula preserva identidade."""
    before = default_runtime_rules()
    after = updated_runtime_rules(
        before,
        mutation_rate=before.mutation_rate,
    )
    assert after is before


def test_updated_multiple_same_values_returns_same_instance():
    before = default_runtime_rules()
    after = updated_runtime_rules(
        before,
        mutation_rate=before.mutation_rate,
        predation_transfer=before.predation_transfer,
        damage_per_own_overcrowding=before.damage_per_own_overcrowding,
    )
    assert after is before


def test_state_update_noop_preserves_identity():
    """state.update_runtime_rules no-op preserva identidade."""
    state.update_runtime_rules(
        mutation_rate=int(cfg.INITIAL_MUTATION_RATE),
        mutated_genes=int(cfg.INITIAL_MUTATED_GENES),
        local_scale_fraction=int(cfg.LOCAL_SCALE_FRACTION * 100),
        zone_hp_effect=int(cfg.HP_EFFECT_IN_ZONE),
        base_decay_per_tick=int(cfg.BASE_DECAY_PER_TICK),
        predation_transfer=int(cfg.PREDATION_TRANSFER),
        damage_per_own_overcrowding=int(cfg.DAMAGE_PER_OWN_OVERCROWDING),
        reproduction_interval=int(cfg.REPRODUCTION_INTERVAL),
        reproduction_min_age=int(cfg.REPRODUCTION_MIN_AGE),
        reproduction_hp_gate=int(cfg.REPRODUCTION_HP_GATE),
        reproduction_min_encounters=int(cfg.REPRODUCTION_MIN_ENCOUNTERS),
        reproduction_parent_hp_bonus=int(
            cfg.REPRODUCTION_PARENT_HP_BONUS
        ),
    )
    before = state.runtime_rules
    state.update_runtime_rules(
        predation_transfer=before.predation_transfer,
        damage_per_own_overcrowding=before.damage_per_own_overcrowding,
    )
    assert state.runtime_rules is before
# ---------------------------------------------------------------------------
# Patch 9: two_scales tuning runtime
# ---------------------------------------------------------------------------


def test_two_scale_runtime_defaults_and_types():
    rules = default_runtime_rules()
    assert type(rules.local_scale_sigma) is float
    assert type(rules.global_probability) is int
    assert type(rules.global_scale_fraction) is int
    assert type(rules.global_scale_sigma) is float
    assert rules.local_scale_sigma == float(cfg.LOCAL_SCALE_SIGMA)
    assert rules.global_probability == int(cfg.GLOBAL_PROBABILITY * 100)
    assert rules.global_scale_fraction == int(cfg.GLOBAL_SCALE_FRACTION * 100)
    assert rules.global_scale_sigma == float(cfg.GLOBAL_SCALE_SIGMA)


@pytest.mark.parametrize(
    "field,minimum,maximum",
    [
        ("global_probability", cfg.MIN_GLOBAL_PROBABILITY, cfg.MAX_GLOBAL_PROBABILITY),
        (
            "global_scale_fraction",
            cfg.MIN_GLOBAL_SCALE_FRACTION,
            cfg.MAX_GLOBAL_SCALE_FRACTION,
        ),
    ],
)
def test_two_scale_runtime_int_bounds(field, minimum, maximum):
    current = default_runtime_rules()
    for value in (minimum, maximum):
        updated = updated_runtime_rules(current, **{field: value})
        assert getattr(updated, field) == value

    for bad in (minimum - 1, maximum + 1, True, False, 1.0, None):
        with pytest.raises(ValueError):
            updated_runtime_rules(current, **{field: bad})


@pytest.mark.parametrize("field", ["local_scale_sigma", "global_scale_sigma"])
def test_two_scale_sigma_validation_is_strict(field):
    current = default_runtime_rules()
    for value in (float(cfg.MIN_MUTATION_SIGMA), float(cfg.MAX_MUTATION_SIGMA)):
        updated = updated_runtime_rules(current, **{field: value})
        assert getattr(updated, field) == value

    for bad in (
        0.0,
        -0.1,
        float(cfg.MAX_MUTATION_SIGMA + 0.01),
        1,
        True,
        None,
        float("nan"),
        float("inf"),
        float("-inf"),
    ):
        with pytest.raises(ValueError):
            updated_runtime_rules(current, **{field: bad})


def test_two_scale_hot_update_identity_and_atomicity():
    state.update_runtime_rules(
        local_scale_sigma=0.25,
        global_probability=75,
        global_scale_fraction=40,
        global_scale_sigma=2.0,
    )
    before = state.runtime_rules

    state.update_runtime_rules(
        local_scale_sigma=0.25,
        global_probability=75,
        global_scale_fraction=40,
        global_scale_sigma=2.0,
    )
    assert state.runtime_rules is before

    with pytest.raises(ValueError):
        state.update_runtime_rules(global_probability=101)
    assert state.runtime_rules is before

    state.update_runtime_rules(global_probability=74)
    assert state.runtime_rules is not before
    assert state.runtime_rules.global_probability == 74


def test_bootstrap_fresh_restores_two_scale_defaults(monkeypatch):
    """Bootstrap zera o tuning two_scales ao default.

    As dependencias internas de bootstrap sao monkeypatchadas no
    namespace de `bootstrap` (autoridade real). simulation.bootstrap_new_world
    e a mesma funcao, entao chamar por simulation continua valido
    enquanto as substituicoes pegarem.
    """
    from primordial_soup import bootstrap
    from primordial_soup import layout
    from primordial_soup import simulation
    from primordial_soup import world

    original = state.runtime_rules
    saved_zones = state.zones
    saved_zone_centers = state.zone_centers
    saved_nests = state.nests
    saved_agents = list(agents)
    try:
        agents.clear()
        state.update_runtime_rules(
            local_scale_sigma=0.25,
            global_probability=75,
            global_scale_fraction=40,
            global_scale_sigma=2.0,
        )
        sentinel_zone_centers = tuple(
            (
                layout.LAYOUT.world_width - cfg.ZONE_RADIUS - 1,
                layout.LAYOUT.world_height - cfg.ZONE_RADIUS - 1,
            )
            for _ in range(cfg.NUMBER_OF_ZONES)
        )
        sentinel_zones = world.build_zone_mask(sentinel_zone_centers)
        sentinel_nests = (
            (cfg.NEST_RADIUS + 1, cfg.NEST_RADIUS + 1),
            (cfg.NEST_RADIUS + 1 + 2 * cfg.NEST_RADIUS + 1, cfg.NEST_RADIUS + 1),
            (cfg.NEST_RADIUS + 1 + 4 * cfg.NEST_RADIUS + 2, cfg.NEST_RADIUS + 1),
        )
        monkeypatch.setattr(bootstrap, "seed_lineages", lambda: None)
        monkeypatch.setattr(bootstrap, "place_initially", lambda: None)
        monkeypatch.setattr(bootstrap, "fill_fields", lambda: None)
        monkeypatch.setattr(
            bootstrap,
            "generate_zones",
            lambda: (sentinel_zones, sentinel_zone_centers),
        )
        monkeypatch.setattr(
            bootstrap, "generate_nests", lambda zones: sentinel_nests
        )
        monkeypatch.setattr(
            bootstrap,
            "random_population",
            lambda n: np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32),
        )

        simulation.bootstrap_new_world()

        assert state.runtime_rules.local_scale_sigma == float(
            cfg.LOCAL_SCALE_SIGMA
        )
        assert state.runtime_rules.global_probability == int(
            cfg.GLOBAL_PROBABILITY * 100
        )
        assert state.runtime_rules.global_scale_fraction == int(
            cfg.GLOBAL_SCALE_FRACTION * 100
        )
        assert state.runtime_rules.global_scale_sigma == float(
            cfg.GLOBAL_SCALE_SIGMA
        )
    finally:
        state.set_runtime_rules(original)
        state.zones = saved_zones
        state.zone_centers = saved_zone_centers
        state.nests = saved_nests
        agents[:] = saved_agents


def test_recreate_preserves_two_scale_runtime_identity(monkeypatch):
    """controls.recreate() preserva o tuning two_scales runtime.

    Monkeypatch no namespace de bootstrap (autoridade real).
    """
    from primordial_soup import bootstrap
    from primordial_soup import controls
    from primordial_soup import layout
    from primordial_soup import world

    original = state.runtime_rules
    saved_zones = state.zones
    saved_zone_centers = state.zone_centers
    saved_nests = state.nests
    saved_agents = list(agents)
    try:
        agents.clear()
        state.update_runtime_rules(
            local_scale_sigma=0.25,
            global_probability=75,
            global_scale_fraction=40,
            global_scale_sigma=2.0,
        )
        expected = state.runtime_rules
        sentinel_zone_centers = tuple(
            (
                layout.LAYOUT.world_width - cfg.ZONE_RADIUS - 1,
                layout.LAYOUT.world_height - cfg.ZONE_RADIUS - 1,
            )
            for _ in range(cfg.NUMBER_OF_ZONES)
        )
        sentinel_zones = world.build_zone_mask(sentinel_zone_centers)
        sentinel_nests = (
            (cfg.NEST_RADIUS + 1, cfg.NEST_RADIUS + 1),
            (cfg.NEST_RADIUS + 1 + 2 * cfg.NEST_RADIUS + 1, cfg.NEST_RADIUS + 1),
            (cfg.NEST_RADIUS + 1 + 4 * cfg.NEST_RADIUS + 2, cfg.NEST_RADIUS + 1),
        )
        monkeypatch.setattr(bootstrap, "seed_lineages", lambda: None)
        monkeypatch.setattr(bootstrap, "place_initially", lambda: None)
        monkeypatch.setattr(bootstrap, "fill_fields", lambda: None)
        monkeypatch.setattr(
            bootstrap,
            "generate_zones",
            lambda: (sentinel_zones, sentinel_zone_centers),
        )
        monkeypatch.setattr(
            bootstrap, "generate_nests", lambda zones: sentinel_nests
        )
        monkeypatch.setattr(
            bootstrap,
            "random_population",
            lambda n: np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32),
        )

        controls.recreate()

        assert state.runtime_rules is expected
        assert state.runtime_rules.local_scale_sigma == 0.25
        assert state.runtime_rules.global_probability == 75
        assert state.runtime_rules.global_scale_fraction == 40
        assert state.runtime_rules.global_scale_sigma == 2.0
    finally:
        state.set_runtime_rules(original)
        state.zones = saved_zones
        state.zone_centers = saved_zone_centers
        state.nests = saved_nests
        agents[:] = saved_agents