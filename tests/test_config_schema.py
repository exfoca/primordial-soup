# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Testes para o schema canonico de configuracao declarativa."""

from dataclasses import FrozenInstanceError, fields, replace
from typing import get_type_hints
from pathlib import Path

import pytest

from primordial_soup import config as cfg
from primordial_soup import config_source
from primordial_soup import i18n
from primordial_soup.config_contract import HotDefaults, NonHotConfig, OperatorDefaults
from primordial_soup.config_schema import (
    CONFIG_SCHEMA,
    CONFIG_SECTION_ORDER,
    ConfigConstraintSpec,
    ConfigFieldRef,
    ConfigFieldSpec,
    ConfigScope,
    ConfigSection,
    ConfigValueType,
    get_field_spec,
    get_field_spec_by_attr,
    iter_checkpoint_relevant,
    iter_section,
)
from primordial_soup.config_validation import resolve_constraints
from primordial_soup.runtime_rules import RuntimeRules


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_schema_is_immutable_tuple_of_field_specs():
    assert isinstance(CONFIG_SCHEMA, tuple)
    assert CONFIG_SCHEMA
    assert all(isinstance(spec, ConfigFieldSpec) for spec in CONFIG_SCHEMA)


def test_schema_and_constraint_specs_are_frozen_and_slotted():
    spec = CONFIG_SCHEMA[0]
    with pytest.raises(FrozenInstanceError):
        spec.env_key = "OTHER"
    with pytest.raises(FrozenInstanceError):
        spec.constraints.minimum = 0
    assert not hasattr(spec, "__dict__")
    assert not hasattr(spec.constraints, "__dict__")


def test_schema_keys_and_destinations_are_unique():
    env_keys = [spec.env_key for spec in CONFIG_SCHEMA]
    destinations = [(spec.scope, spec.attr_name) for spec in CONFIG_SCHEMA]
    assert len(env_keys) == len(set(env_keys))
    assert len(destinations) == len(set(destinations))


def test_schema_has_exact_scope_cardinality():
    assert len(CONFIG_SCHEMA) == 107
    assert sum(spec.scope is ConfigScope.NON_HOT for spec in CONFIG_SCHEMA) == 67
    assert sum(spec.scope is ConfigScope.OPERATOR for spec in CONFIG_SCHEMA) == 9
    assert sum(spec.scope is ConfigScope.HOT for spec in CONFIG_SCHEMA) == 31


def test_schema_covers_contract_dataclasses_in_exact_order():
    contract_by_scope = {
        ConfigScope.NON_HOT: NonHotConfig,
        ConfigScope.OPERATOR: OperatorDefaults,
        ConfigScope.HOT: HotDefaults,
    }
    for scope, contract_type in contract_by_scope.items():
        schema_names = tuple(
            spec.attr_name for spec in CONFIG_SCHEMA if spec.scope is scope
        )
        contract_names = tuple(field.name for field in fields(contract_type))
        assert schema_names == contract_names


def test_schema_value_types_match_contract_annotations_exactly():
    expected_types = {
        ConfigValueType.INT: int,
        ConfigValueType.FLOAT: float,
        ConfigValueType.BOOL: bool,
        ConfigValueType.STRING: str,
        ConfigValueType.RGB: tuple[int, int, int],
        ConfigValueType.FONT: tuple[str, int, bool],
        ConfigValueType.STRING_TUPLE: tuple[str, ...],
    }
    contract_by_scope = {
        ConfigScope.NON_HOT: NonHotConfig,
        ConfigScope.OPERATOR: OperatorDefaults,
        ConfigScope.HOT: HotDefaults,
    }
    for scope, contract_type in contract_by_scope.items():
        hints = get_type_hints(contract_type)
        for spec in CONFIG_SCHEMA:
            if spec.scope is scope:
                assert hints[spec.attr_name] == expected_types[spec.value_type]


def test_every_config_value_type_is_used_by_schema():
    assert {spec.value_type for spec in CONFIG_SCHEMA} == set(ConfigValueType)


def test_hot_schema_has_exact_runtime_rules_shape_and_types():
    hot_specs = tuple(spec for spec in CONFIG_SCHEMA if spec.scope is ConfigScope.HOT)
    hot_names = tuple(field.name for field in fields(HotDefaults))
    runtime_names = tuple(field.name for field in fields(RuntimeRules))
    hot_hints = get_type_hints(HotDefaults)
    runtime_hints = get_type_hints(RuntimeRules)
    assert len(hot_specs) == 31
    assert tuple(spec.attr_name for spec in hot_specs) == hot_names == runtime_names
    assert tuple(hot_hints[name] for name in hot_names) == tuple(
        runtime_hints[name] for name in runtime_names
    )



def test_config_sections_are_closed_complete_and_ordered():
    expected_values = (
        "world_display",
        "population",
        "neural_architecture",
        "world_geometry",
        "presentation",
        "persistence",
        "recording",
        "audio",
        "diagnostics",
        "operator_interface",
        "operator_execution",
        "operator_audio",
        "hot_crossover",
        "hot_mutation",
        "hot_behavior",
        "hot_ecology",
        "hot_reproduction",
        "hot_selection",
    )
    assert tuple(section.value for section in ConfigSection) == expected_values
    assert CONFIG_SECTION_ORDER == tuple(ConfigSection)
    assert len(CONFIG_SECTION_ORDER) == 18
    assert all(type(spec.section) is ConfigSection for spec in CONFIG_SCHEMA)
    assert {spec.section for spec in CONFIG_SCHEMA} == set(ConfigSection)


def test_iter_section_preserves_relative_schema_order():
    for section in ConfigSection:
        expected = tuple(spec for spec in CONFIG_SCHEMA if spec.section is section)
        assert iter_section(section) == expected
        assert expected


def test_lifecycle_metadata_is_derived_from_scope_and_editable_is_boolean():
    for spec in CONFIG_SCHEMA:
        assert spec.runtime_editable is (spec.scope is not ConfigScope.NON_HOT)
        assert spec.restart_required is (spec.scope is ConfigScope.NON_HOT)
        assert type(spec.checkpoint_relevant) is bool
        assert spec.editable is True

    candidate = replace(CONFIG_SCHEMA[0], editable=False)
    assert candidate.editable is False

def test_field_spec_metadata_shape_contains_contract_not_values():
    assert [field.name for field in fields(ConfigFieldSpec)] == [
        "env_key",
        "attr_name",
        "scope",
        "section",
        "value_type",
        "runtime_editable",
        "editable",
        "restart_required",
        "checkpoint_relevant",
        "label_key",
        "description_key",
        "constraints",
    ]
    assert not hasattr(CONFIG_SCHEMA[0], "default")
    assert not hasattr(CONFIG_SCHEMA[0], "value")


def test_lifecycle_and_i18n_metadata_match_scope():
    for spec in CONFIG_SCHEMA:
        assert spec.editable is True
        assert spec.label_key == f"config.{spec.attr_name}.label"
        assert spec.description_key == f"config.{spec.attr_name}.description"
        if spec.scope is ConfigScope.NON_HOT:
            assert spec.runtime_editable is False
            assert spec.restart_required is True
        else:
            assert spec.runtime_editable is True
            assert spec.restart_required is False


def test_hot_prefixes_match_scope():
    for spec in CONFIG_SCHEMA:
        if spec.scope is ConfigScope.HOT:
            assert spec.env_key.startswith("HOT_")
        else:
            assert not spec.env_key.startswith("HOT_")


def test_lookup_by_key_and_destination_are_consistent():
    for spec in CONFIG_SCHEMA:
        assert get_field_spec(spec.env_key) is spec
        assert get_field_spec_by_attr(spec.scope, spec.attr_name) is spec


def test_constraint_definition_integrity():
    numeric_types = {ConfigValueType.INT, ConfigValueType.FLOAT}
    destinations = {(spec.scope, spec.attr_name) for spec in CONFIG_SCHEMA}
    for spec in CONFIG_SCHEMA:
        constraints = spec.constraints
        assert isinstance(constraints, ConfigConstraintSpec)
        if constraints.step is not None:
            assert constraints.step > 0
            assert spec.value_type in numeric_types
        if isinstance(constraints.choices, tuple):
            assert constraints.choices
            assert len(constraints.choices) == len(set(constraints.choices))
        if type(constraints.minimum) in {int, float} and type(constraints.maximum) in {int, float}:
            assert constraints.minimum <= constraints.maximum
        if constraints.minimum is not None or constraints.maximum is not None:
            assert spec.value_type in numeric_types
        for ref in (constraints.minimum, constraints.maximum, constraints.choices):
            if isinstance(ref, ConfigFieldRef):
                assert (ref.scope, ref.attr_name) in destinations


def test_canonical_choice_domains_are_exact_and_ordered():
    expected = {
        "HOT_CROSSOVER_MODE": ("blocks", "uniform", "two_points"),
        "HOT_MUTATION_MODE": ("two_scales", "surgical"),
        "HOT_REPRODUCTION_CRITERION": ("composite", "longevity"),
        "DEFAULT_LANGUAGE": ("en", "pt"),
        "DEFAULT_SIMULATION_SPEED": (
            0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0,
        ),
        "DEFAULT_DISCOVERY_CRITERION": (
            "most_evolved", "oldest", "youngest", "most_offspring",
            "most_encounters", "most_explored", "highest_hp", "lowest_hp",
            "highest_generation",
        ),
        "DEFAULT_DISCOVERY_LINEAGE_FILTER": ("all", "R", "G", "B"),
    }
    for env_key, choices in expected.items():
        assert get_field_spec(env_key).constraints.choices == choices


def test_i18n_language_domain_follows_schema_exactly():
    choices = get_field_spec("DEFAULT_LANGUAGE").constraints.choices
    assert i18n.AVAILABLE_LANGUAGES == choices
    assert set(i18n.TRANSLATIONS) == set(choices)


def test_dynamic_constraints_resolve_against_canonical_snapshot():
    snapshot = cfg.CONFIG_SNAPSHOT
    expected = {
        "HOT_BLOCK_SIZE": cfg.GENOME_SIZE,
        "HOT_LOW_HP_THRESHOLD": cfg.INITIAL_HP,
        "HOT_DEATH_HP_THRESHOLD": cfg.INITIAL_HP,
        "HOT_REPRODUCTION_HP_GATE": cfg.INITIAL_HP,
        "HOT_REPRODUCTION_PARENT_HP_BONUS": cfg.INITIAL_HP,
        "HOT_REPRODUCTION_ATTEMPTS_DIVISOR": cfg.MAX_POPULATION_PER_LINEAGE,
        "NEST_SPAWN_RADIUS": cfg.NEST_RADIUS,
    }
    for env_key, maximum in expected.items():
        assert resolve_constraints(get_field_spec(env_key), snapshot).maximum == maximum
    assert resolve_constraints(
        get_field_spec("DEFAULT_SAVE_SLOT"), snapshot
    ).choices == cfg.SAVE_SLOTS


def test_screen_width_constraint_is_dynamic_and_exclusive():
    resolved = resolve_constraints(get_field_spec("SCREEN_WIDTH"), cfg.CONFIG_SNAPSHOT)
    assert resolved.minimum == cfg.INSPECTION_PANEL_WIDTH
    assert resolved.minimum_inclusive is False


def test_genome_and_gene_range_constraints_match_structural_derivations():
    block = resolve_constraints(get_field_spec("HOT_BLOCK_SIZE"), cfg.CONFIG_SNAPSHOT)
    sigma = resolve_constraints(
        get_field_spec("HOT_LOCAL_SCALE_SIGMA"), cfg.CONFIG_SNAPSHOT
    )
    assert block.maximum == cfg.GENOME_SIZE
    assert sigma.maximum == cfg.MAX_GENE_VALUE - cfg.MIN_GENE_VALUE == 4.0


def test_nest_radius_schema_ceiling_matches_minimum_world_geometry():
    constraints = resolve_constraints(get_field_spec("NEST_RADIUS"), cfg.CONFIG_SNAPSHOT)
    assert constraints.maximum == 149
    assert 2 * constraints.maximum < cfg.MIN_WORLD_HEIGHT
    assert 2 * constraints.maximum < cfg.MIN_WORLD_WIDTH


def test_env_assignment_order_matches_schema():
    env_lines = config_source.PACKAGED_CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    env_keys = []
    for original_line in env_lines:
        line = original_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, _value = line.partition("=")
        assert separator == "="
        env_keys.append(key.strip())
    assert env_keys == [spec.env_key for spec in CONFIG_SCHEMA]

def test_checkpoint_relevant_fields_are_exact_and_ordered():
    expected = (
        "SCREEN_WIDTH",
        "SCREEN_HEIGHT",
        "TARGET_PIXEL_SCALE",
        "MAX_POPULATION_PER_LINEAGE",
        "VISION_RADIUS",
        "HIDDEN_NEURONS",
        "HIDDEN_NEURONS_2",
        "HIDDEN_ACTIVATION",
        "HIDDEN_ACTIVATION_2",
        "OUTPUT_ACTIVATION",
        "INITIAL_HP",
        "NUMBER_OF_ZONES",
        "ZONE_RADIUS",
        "NEST_RADIUS",
        "NEST_SPAWN_RADIUS",
        "DEATH_MARKER_TTL_TICKS",
        "INSPECTION_PANEL_WIDTH",
    )

    assert tuple(spec.env_key for spec in iter_checkpoint_relevant()) == expected


def test_checkpoint_relevant_metadata_is_non_hot_restart_required_only():
    for spec in CONFIG_SCHEMA:
        if spec.checkpoint_relevant:
            assert spec.scope is ConfigScope.NON_HOT
            assert spec.restart_required is True
        if spec.scope in {ConfigScope.OPERATOR, ConfigScope.HOT}:
            assert spec.checkpoint_relevant is False


def test_checkpoint_irrelevant_sentinels_stay_out_of_universe_identity():
    for env_key in (
        "INITIAL_POPULATION_PER_LINEAGE",
        "MAX_NEST_PLACEMENT_ATTEMPTS",
        "ZOOM_STEP",
        "TARGET_FPS",
        "SAVE_SLOTS",
        "RECORDING_FILE",
        "SOUND_VOLUME_MUSIC",
        "METRICS_INTERVAL",
    ):
        assert get_field_spec(env_key).checkpoint_relevant is False


def test_removed_non_hot_fields_are_absent_from_schema_contract_env_and_facade():
    removed = (
        ("HUD_COLOR", "hud_color"),
        ("OVERLAP_POLICY", "overlap_policy"),
        ("CHART_WIDTH", "chart_width"),
        ("CHART_HEIGHT", "chart_height"),
        ("CHART_MARGIN", "chart_margin"),
        ("CHART_SPACING", "chart_spacing"),
    )
    env_text = config_source.PACKAGED_CONFIG_PATH.read_text(encoding="utf-8")
    schema_keys = {spec.env_key for spec in CONFIG_SCHEMA}
    contract_fields = {field.name for field in fields(NonHotConfig)}

    for env_key, attr_name in removed:
        assert env_key not in schema_keys
        assert attr_name not in contract_fields
        assert not hasattr(cfg, env_key)
        assert not any(
            line.startswith(f"{env_key}=")
            for line in env_text.splitlines()
        )
