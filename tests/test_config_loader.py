# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Testes para carregamento rigoroso de configuração declarativa orientada a schema."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from primordial_soup.config_contract import (
    ConfigSnapshot,
    HotDefaults,
    NonHotConfig,
    OperatorDefaults,
)
from primordial_soup import config_source
from primordial_soup.config_loader import ConfigError, load_config


ENV_PATH = config_source.PACKAGED_CONFIG_PATH


def _valid_env_text() -> str:
    return ENV_PATH.read_text(encoding="utf-8")


def _replace_assignment(text: str, key: str, replacement: str) -> str:
    prefix = f"{key}="
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    assert len(matches) == 1
    lines[matches[0]] = replacement
    return "\n".join(lines) + "\n"


def _remove_assignment(text: str, key: str) -> str:
    prefix = f"{key}="
    lines = text.splitlines()
    filtered = [line for line in lines if not line.startswith(prefix)]
    assert len(filtered) == len(lines) - 1
    return "\n".join(filtered) + "\n"


def _load_temp(tmp_path: Path, text: str) -> ConfigSnapshot:
    path = tmp_path / "config.env"
    path.write_text(text, encoding="utf-8")
    return load_config(path)


def test_packaged_baseline_loads_into_typed_snapshot():
    snapshot = load_config(ENV_PATH)

    assert isinstance(snapshot, ConfigSnapshot)
    assert isinstance(snapshot.non_hot, NonHotConfig)
    assert isinstance(snapshot.operator, OperatorDefaults)
    assert isinstance(snapshot.hot, HotDefaults)


def test_non_hot_sentinels_match_commit_defaults():
    config = load_config(ENV_PATH).non_hot

    assert config.screen_width == 1920
    assert config.initial_population_per_lineage == 50
    assert config.vision_radius == 5
    assert config.hidden_neurons == 25
    assert config.initial_hp == 10000
    assert config.nest_radius == 20
    assert config.target_fps == 60
    assert config.recording_fps == 15
    assert config.sound_volume_music == 0.1
    assert config.metrics_interval == 10


def test_operator_sentinels_match_declared_defaults():
    config = load_config(ENV_PATH).operator

    assert config.default_language == "en"
    assert config.default_simulation_speed == 1.0
    assert config.default_paused is True
    assert config.default_zones_active is True
    assert config.default_floating_hud_visible is True
    assert config.default_music_enabled is True
    assert config.default_sfx_enabled is True
    assert config.default_discovery_criterion == "most_evolved"
    assert config.default_discovery_lineage_filter == "all"


def test_hot_sentinels_use_runtime_rules_units():
    config = load_config(ENV_PATH).hot

    assert config.crossover_mode == "blocks"
    assert config.mutation_rate == 5
    assert config.local_scale_fraction == 5
    assert config.global_probability == 10
    assert config.global_scale_fraction == 20
    assert config.low_hp_threshold == 2000
    assert config.predation_transfer == 100
    assert config.reproduction_interval == 150
    assert config.reproduction_min_age == 5000
    assert config.reproduction_pool_fraction == 0.9
    assert config.longevity_weight == 0.3


def test_snapshot_contracts_are_frozen():
    snapshot = load_config(ENV_PATH)

    with pytest.raises(FrozenInstanceError):
        snapshot.hot.mutation_rate = 99
    with pytest.raises(FrozenInstanceError):
        snapshot.non_hot.screen_width = 123


def test_missing_file_raises_config_error_with_path(tmp_path):
    missing = tmp_path / "missing.env"

    with pytest.raises(ConfigError, match=str(missing)):
        load_config(missing)


def test_missing_key_is_rejected(tmp_path):
    text = _remove_assignment(_valid_env_text(), "SCREEN_WIDTH")

    with pytest.raises(ConfigError, match="SCREEN_WIDTH"):
        _load_temp(tmp_path, text)


def test_unknown_key_is_rejected(tmp_path):
    text = _valid_env_text() + "FUTURE_UNKNOWN_THING=123\n"

    with pytest.raises(ConfigError, match="FUTURE_UNKNOWN_THING"):
        _load_temp(tmp_path, text)


def test_removed_hud_color_is_rejected_as_unknown_key(tmp_path):
    text = _valid_env_text() + "HUD_COLOR=0,255,0\n"

    with pytest.raises(ConfigError, match="HUD_COLOR"):
        _load_temp(tmp_path, text)


def test_duplicate_key_is_rejected(tmp_path):
    text = _valid_env_text() + "SCREEN_WIDTH=1920\n"

    with pytest.raises(ConfigError, match="SCREEN_WIDTH"):
        _load_temp(tmp_path, text)


def test_malformed_assignment_is_rejected(tmp_path):
    text = _valid_env_text() + "SCREEN_WIDTH 1920\n"

    with pytest.raises(ConfigError, match="Malformed assignment"):
        _load_temp(tmp_path, text)


def test_export_syntax_is_rejected(tmp_path):
    text = _replace_assignment(
        _valid_env_text(),
        "SCREEN_WIDTH",
        "export SCREEN_WIDTH=1920",
    )

    with pytest.raises(ConfigError):
        _load_temp(tmp_path, text)


def test_interpolation_is_rejected(tmp_path):
    text = _replace_assignment(
        _valid_env_text(),
        "RECORDING_FILE",
        "RECORDING_FILE=${HOME}/foo.gif",
    )

    with pytest.raises(ConfigError, match="Interpolation"):
        _load_temp(tmp_path, text)


def test_invalid_int_is_rejected(tmp_path):
    text = _replace_assignment(
        _valid_env_text(),
        "SCREEN_WIDTH",
        "SCREEN_WIDTH=1920.0",
    )

    with pytest.raises(ConfigError, match="SCREEN_WIDTH"):
        _load_temp(tmp_path, text)


def test_invalid_bool_is_rejected(tmp_path):
    text = _replace_assignment(
        _valid_env_text(),
        "DEFAULT_PAUSED",
        "DEFAULT_PAUSED=True",
    )

    with pytest.raises(ConfigError, match="DEFAULT_PAUSED"):
        _load_temp(tmp_path, text)


def test_non_finite_float_is_rejected(tmp_path):
    text = _replace_assignment(
        _valid_env_text(),
        "ZOOM_STEP",
        "ZOOM_STEP=nan",
    )

    with pytest.raises(ConfigError, match="ZOOM_STEP"):
        _load_temp(tmp_path, text)


def test_invalid_rgb_is_rejected(tmp_path):
    text = _replace_assignment(
        _valid_env_text(),
        "HUD_BG_COLOR",
        "HUD_BG_COLOR=256,0,0",
    )

    with pytest.raises(ConfigError, match="HUD_BG_COLOR"):
        _load_temp(tmp_path, text)


def test_invalid_font_is_rejected(tmp_path):
    text = _replace_assignment(
        _valid_env_text(),
        "HUD_FONT",
        "HUD_FONT=monospace,0,true",
    )

    with pytest.raises(ConfigError, match="HUD_FONT"):
        _load_temp(tmp_path, text)


def test_duplicate_string_tuple_item_is_rejected(tmp_path):
    text = _replace_assignment(
        _valid_env_text(),
        "SAVE_SLOTS",
        "SAVE_SLOTS=default,world_a,world_a",
    )

    with pytest.raises(ConfigError, match="SAVE_SLOTS"):
        _load_temp(tmp_path, text)


def test_process_environment_does_not_override_file(monkeypatch, tmp_path):
    monkeypatch.setenv("SCREEN_WIDTH", "123")
    snapshot = _load_temp(tmp_path, _valid_env_text())

    assert snapshot.non_hot.screen_width == 1920


@pytest.mark.parametrize(
    "key,replacement",
    [
        ("HIDDEN_ACTIVATION", "HIDDEN_ACTIVATION=gelu"),
        (
            "INITIAL_POPULATION_PER_LINEAGE",
            "INITIAL_POPULATION_PER_LINEAGE=1",
        ),
        (
            "MAX_POPULATION_PER_LINEAGE",
            "MAX_POPULATION_PER_LINEAGE=49",
        ),
        ("NEST_SPAWN_RADIUS", "NEST_SPAWN_RADIUS=21"),
        ("DEFAULT_SAVE_SLOT", "DEFAULT_SAVE_SLOT=missing"),
        ("RECORDING_SCALE", "RECORDING_SCALE=0.0"),
        ("RECORDING_SCALE", "RECORDING_SCALE=1.01"),
        ("SOUND_VOLUME_MUSIC", "SOUND_VOLUME_MUSIC=-0.01"),
        ("SOUND_VOLUME_SFX", "SOUND_VOLUME_SFX=1.01"),
        ("DEFAULT_LANGUAGE", "DEFAULT_LANGUAGE=fr"),
        ("DEFAULT_SIMULATION_SPEED", "DEFAULT_SIMULATION_SPEED=3.0"),
        (
            "DEFAULT_DISCOVERY_CRITERION",
            "DEFAULT_DISCOVERY_CRITERION=random",
        ),
        ("HOT_CROSSOVER_MODE", "HOT_CROSSOVER_MODE=single_point"),
        ("HOT_MUTATION_RATE", "HOT_MUTATION_RATE=-1"),
        ("HOT_MUTATION_RATE", "HOT_MUTATION_RATE=101"),
        ("HOT_PREDATION_TRANSFER", "HOT_PREDATION_TRANSFER=9"),
        (
            "HOT_REPRODUCTION_POOL_FRACTION",
            "HOT_REPRODUCTION_POOL_FRACTION=1.01",
        ),
    ],
)
def test_semantically_invalid_assignments_are_rejected_by_loader(
    tmp_path,
    key,
    replacement,
):
    text = _replace_assignment(_valid_env_text(), key, replacement)
    with pytest.raises(ConfigError, match=key):
        _load_temp(tmp_path, text)


def test_cross_field_screen_width_constraint_is_rejected(tmp_path):
    text = _replace_assignment(
        _valid_env_text(),
        "SCREEN_WIDTH",
        "SCREEN_WIDTH=320",
    )
    with pytest.raises(ConfigError, match="SCREEN_WIDTH"):
        _load_temp(tmp_path, text)


def test_save_slot_path_separator_is_rejected_semantically(tmp_path):
    text = _replace_assignment(
        _valid_env_text(),
        "SAVE_SLOTS",
        "SAVE_SLOTS=default,bad/path",
    )
    with pytest.raises(ConfigError, match="SAVE_SLOTS"):
        _load_temp(tmp_path, text)


def test_config_error_is_reexported_from_loader():
    from primordial_soup.config_errors import ConfigError as CanonicalConfigError

    assert ConfigError is CanonicalConfigError
