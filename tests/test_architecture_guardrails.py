# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Guardrails permanentes contra a reintroducao da arquitetura removida."""

from __future__ import annotations

import ast
from pathlib import Path

from primordial_soup import config as cfg
from primordial_soup import i18n
from primordial_soup import state
from primordial_soup.config_schema import iter_checkpoint_relevant


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "primordial_soup"

_REMOVED_CONFIG_SYMBOLS = {
    "CROSSOVER_MODES",
    "MUTATION_MODES",
    "REPRODUCTION_CRITERIA",
    "MIN_CROSSOVER_PROBABILITY",
    "MAX_CROSSOVER_PROBABILITY",
    "MIN_BLOCK_SIZE",
    "MAX_BLOCK_SIZE",
    "MIN_MUTATION_RATE",
    "MAX_MUTATION_RATE",
    "MIN_MUTATED_GENES",
    "MAX_MUTATED_GENES",
    "MIN_LOCAL_SCALE_FRACTION",
    "MAX_LOCAL_SCALE_FRACTION",
    "MIN_GLOBAL_PROBABILITY",
    "MAX_GLOBAL_PROBABILITY",
    "MIN_GLOBAL_SCALE_FRACTION",
    "MAX_GLOBAL_SCALE_FRACTION",
    "MIN_MUTATION_SIGMA",
    "MAX_MUTATION_SIGMA",
    "MIN_LOW_HP_THRESHOLD",
    "MAX_LOW_HP_THRESHOLD",
    "MIN_DEATH_HP_THRESHOLD",
    "MAX_DEATH_HP_THRESHOLD",
    "MIN_BASE_DECAY_PER_TICK",
    "MAX_BASE_DECAY_PER_TICK",
    "MIN_PREDATION_TRANSFER",
    "MAX_PREDATION_TRANSFER",
    "PREDATION_TRANSFER_STEP",
    "MIN_DAMAGE_PER_OWN_OVERCROWDING",
    "MAX_DAMAGE_PER_OWN_OVERCROWDING",
    "DAMAGE_PER_OWN_OVERCROWDING_STEP",
    "MIN_ZONE_HP_EFFECT",
    "MAX_ZONE_HP_EFFECT",
    "MIN_REPRODUCTION_INTERVAL",
    "MAX_REPRODUCTION_INTERVAL",
    "MIN_REPRODUCTION_MIN_AGE",
    "MAX_REPRODUCTION_MIN_AGE",
    "MIN_REPRODUCTION_HP_GATE",
    "MAX_REPRODUCTION_HP_GATE",
    "MIN_REPRODUCTION_MIN_ENCOUNTERS",
    "MAX_REPRODUCTION_MIN_ENCOUNTERS",
    "MIN_REPRODUCTION_PARENT_HP_BONUS",
    "MAX_REPRODUCTION_PARENT_HP_BONUS",
    "MIN_SELECTION_WEIGHT",
    "MAX_SELECTION_WEIGHT",
    "MIN_REPRODUCTION_MIN_SCORE",
    "MAX_REPRODUCTION_MIN_SCORE",
    "MIN_REPRODUCTION_POOL_FRACTION",
    "MAX_REPRODUCTION_POOL_FRACTION",
    "MIN_REPRODUCTION_ATTEMPTS_DIVISOR",
    "MAX_REPRODUCTION_ATTEMPTS_DIVISOR",
    "CRITERIA_ORDER",
    "LINEAGE_FILTER_ORDER",
    "LINEAGE_FILTER_ALL",
    "CRITERION_MOST_EVOLVED",
    "CRITERION_OLDEST",
    "CRITERION_YOUNGEST",
    "CRITERION_MOST_OFFSPRING",
    "CRITERION_MOST_ENCOUNTERS",
    "CRITERION_MOST_EXPLORED",
    "CRITERION_HIGHEST_HP",
    "CRITERION_LOWEST_HP",
    "CRITERION_HIGHEST_GENERATION",
    "PARAM_MUTATION",
    "PARAM_LOCAL_SCALE",
    "PARAM_ZONE_HP_EFFECT",
    "RANDOM_SEED",
    "GENOME_FILE",
    "METRICS_FILE",
    "SAVE_FORMAT",
    "ENVIRONMENTAL_MODIFIERS",
    "HUD_COLOR",
    "OVERLAP_POLICY",
    "CHART_WIDTH",
    "CHART_HEIGHT",
    "CHART_MARGIN",
    "CHART_SPACING",
}

_DEAD_I18N_KEYS = {
    "log.load_legacy_fallback",
    "log.param_selected",
    "log.param_name.mutation",
    "log.param_name.local_scale",
    "log.param_name.zone_hp_effect",
    "log.mut",
    "log.local_scale",
    "log.zone_hp_effect",
}


def _tree(module_name: str) -> ast.Module:
    path = PACKAGE_ROOT / f"{module_name}.py"
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _package_trees() -> dict[str, ast.Module]:
    return {
        path.stem: ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for path in PACKAGE_ROOT.glob("*.py")
    }


def _relative_imports(module_name: str) -> set[str]:
    imported: set[str] = set()
    for node in _tree(module_name).body:
        if isinstance(node, ast.ImportFrom) and node.level:
            if node.module:
                imported.add(node.module.split(".", 1)[0])
            else:
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "primordial_soup":
                    imported.add("__package__")
                elif alias.name.startswith("primordial_soup."):
                    imported.add(alias.name.split(".", 1)[1].split(".", 1)[0])
    return imported


def _string_constants(module_name: str) -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree(module_name))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_removed_config_symbols_are_not_public_attributes():
    for name in _REMOVED_CONFIG_SYMBOLS:
        assert not hasattr(cfg, name), f"simbolo removido voltou a config.py: {name}"


def test_production_does_not_consume_removed_cfg_symbols():
    violations: list[tuple[str, str]] = []
    for module_name, tree in _package_trees().items():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "cfg"
                and node.attr in _REMOVED_CONFIG_SYMBOLS
            ):
                violations.append((module_name, node.attr))
    assert violations == []


def test_dead_active_parameter_state_does_not_reappear():
    assert not hasattr(state, "active_param")
    violations: list[str] = []
    for module_name, tree in _package_trees().items():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "state"
                and node.attr == "active_param"
            ):
                violations.append(module_name)
    assert violations == []
    assert not any(
        isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(
            isinstance(target, ast.Name) and target.id == "active_param"
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
        )
        for node in ast.walk(_tree("state"))
    )


def test_persistence_has_no_key_alias_reader_or_legacy_file_fallback():
    tree = _tree("persistence")
    defined = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "_read_key" not in defined
    assert "_read_key" not in called
    assert "log.load_legacy_fallback" not in _string_constants("persistence")


def test_persistence_dependency_boundary_and_runtime_validation_gate():
    forbidden = {
        "config_schema",
        "config_validation",
        "config_service",
        "config_loader",
        "config_source",
    }
    assert _relative_imports("persistence").isdisjoint(forbidden)

    called = {
        node.func.id
        for node in ast.walk(_tree("persistence"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "validate_runtime_rules" in called


def test_dead_i18n_keys_are_absent_from_all_languages():
    for translations in i18n.TRANSLATIONS.values():
        assert set(translations).isdisjoint(_DEAD_I18N_KEYS)


def test_low_level_configuration_dependency_boundaries():
    exact = {
        "model_contract": set(),
        "config_contract": set(),
        "config_errors": set(),
        "config_source": {"config_errors"},
        "config_schema": {"model_contract"},
        "config_validation": {
            "config_contract",
            "config_errors",
            "config_schema",
            "model_contract",
        },
        "config_loader": {
            "config_contract",
            "config_errors",
            "config_schema",
            "config_validation",
        },
        "config_service": {
            "config_contract",
            "config_errors",
            "config_loader",
            "config_schema",
            "config_validation",
        },
        "config_compatibility": {
            "config_contract",
            "config_errors",
            "config_schema",
            "config_validation",
        },
    }
    for module_name, allowed in exact.items():
        assert _relative_imports(module_name) <= allowed


def test_config_facade_and_runtime_rules_keep_their_layer_boundaries():
    assert _relative_imports("config").isdisjoint(
        {
            "config_schema",
            "config_validation",
            "config_service",
            "config_compatibility",
            "runtime_rules",
            "state",
        }
    )
    assert _relative_imports("runtime_rules").isdisjoint(
        {"state", "persistence", "panels", "panels_defs", "rendering", "pygame"}
    )


def test_simulation_core_does_not_import_config_editing_paths():
    for module_name in (
        "brain",
        "senses",
        "movement",
        "ecology",
        "genetics",
        "evolution",
        "world",
        "bootstrap",
        "state",
        "simulation",
    ):
        assert _relative_imports(module_name).isdisjoint(
            {"config_service", "config_source"}
        )


def test_checkpoint_field_composition_is_not_duplicated_in_consumers():
    checkpoint_keys = {spec.env_key for spec in iter_checkpoint_relevant()}
    assert checkpoint_keys
    assert _string_constants("config_compatibility").isdisjoint(checkpoint_keys)
    assert _string_constants("persistence").isdisjoint(checkpoint_keys)
