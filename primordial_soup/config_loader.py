# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Leitor estrito para arquivos de configuração declarativa explícita."""

from __future__ import annotations

import math
from pathlib import Path
import re

from .config_contract import (
    ConfigSnapshot,
    HotDefaults,
    NonHotConfig,
    OperatorDefaults,
)
from .config_errors import ConfigError
from .config_schema import CONFIG_SCHEMA, ConfigScope, ConfigValueType
from .config_validation import validate_config_snapshot


_KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9_]*\Z")
_INT_PATTERN = re.compile(r"[+-]?\d+\Z")


def load_config(path: str | Path) -> ConfigSnapshot:
    """Lê um arquivo explícito e materializa um snapshot tipado completo."""
    config_path = Path(path)
    try:
        text = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ConfigError(f"Could not read config file {config_path}: {exc}") from exc

    raw_values = _parse_assignments(text)
    expected_keys = {spec.env_key for spec in CONFIG_SCHEMA}
    actual_keys = set(raw_values)

    unknown = sorted(actual_keys - expected_keys)
    if unknown:
        raise ConfigError(f"Unknown configuration key: {unknown[0]}")

    missing = sorted(expected_keys - actual_keys)
    if missing:
        raise ConfigError(f"Missing configuration key: {missing[0]}")

    grouped: dict[ConfigScope, dict[str, object]] = {
        ConfigScope.NON_HOT: {},
        ConfigScope.OPERATOR: {},
        ConfigScope.HOT: {},
    }

    for spec in CONFIG_SCHEMA:
        try:
            value = _convert_value(raw_values[spec.env_key], spec.value_type)
        except ConfigError as exc:
            raise ConfigError(f"Invalid value for {spec.env_key}: {exc}") from exc
        grouped[spec.scope][spec.attr_name] = value

    try:
        non_hot = NonHotConfig(**grouped[ConfigScope.NON_HOT])
        operator = OperatorDefaults(**grouped[ConfigScope.OPERATOR])
        hot = HotDefaults(**grouped[ConfigScope.HOT])
    except TypeError as exc:
        raise ConfigError(f"Invalid configuration structure: {exc}") from exc

    snapshot = ConfigSnapshot(non_hot=non_hot, operator=operator, hot=hot)
    validate_config_snapshot(snapshot)
    return snapshot


def _parse_assignments(text: str) -> dict[str, str]:
    """Analisa a gramática de configuração intencionalmente pequena sem semântica de shell."""
    values: dict[str, str] = {}

    for line_number, original_line in enumerate(text.splitlines(), start=1):
        line = original_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"Malformed assignment on line {line_number}.")

        key, raw_value = line.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if _KEY_PATTERN.fullmatch(key) is None:
            raise ConfigError(
                f"Invalid configuration key on line {line_number}: {key!r}"
            )
        if key in values:
            raise ConfigError(
                f"Duplicate configuration key on line {line_number}: {key}"
            )
        if "$" in raw_value:
            raise ConfigError(
                f"Interpolation is not supported on line {line_number}: {key}"
            )

        values[key] = raw_value

    return values


def _convert_value(raw_value: str, value_type: ConfigValueType) -> object:
    """Converte um valor bruto já sem espaços de acordo com os metadados de tipo do schema."""
    if value_type is ConfigValueType.INT:
        return _parse_int(raw_value)
    if value_type is ConfigValueType.FLOAT:
        return _parse_float(raw_value)
    if value_type is ConfigValueType.BOOL:
        return _parse_bool(raw_value)
    if value_type is ConfigValueType.STRING:
        return _parse_string(raw_value)
    if value_type is ConfigValueType.RGB:
        return _parse_rgb(raw_value)
    if value_type is ConfigValueType.FONT:
        return _parse_font(raw_value)
    if value_type is ConfigValueType.STRING_TUPLE:
        return _parse_string_tuple(raw_value)
    raise ConfigError(f"Unsupported schema value type: {value_type!r}")


def _parse_int(raw_value: str) -> int:
    if _INT_PATTERN.fullmatch(raw_value) is None:
        raise ConfigError(f"expected decimal integer, got {raw_value!r}")
    return int(raw_value, 10)


def _parse_float(raw_value: str) -> float:
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigError(f"expected float, got {raw_value!r}") from exc
    if not math.isfinite(value):
        raise ConfigError(f"float must be finite, got {raw_value!r}")
    return value


def _parse_bool(raw_value: str) -> bool:
    if raw_value == "true":
        return True
    if raw_value == "false":
        return False
    raise ConfigError(f"expected lowercase true or false, got {raw_value!r}")


def _parse_string(raw_value: str) -> str:
    if not raw_value:
        raise ConfigError("string must not be empty")
    return raw_value


def _parse_rgb(raw_value: str) -> tuple[int, int, int]:
    parts = [part.strip() for part in raw_value.split(",")]
    if len(parts) != 3:
        raise ConfigError(f"expected R,G,B, got {raw_value!r}")
    values = tuple(_parse_int(part) for part in parts)
    if any(value < 0 or value > 255 for value in values):
        raise ConfigError(f"RGB components must be in [0, 255], got {raw_value!r}")
    return values


def _parse_font(raw_value: str) -> tuple[str, int, bool]:
    parts = [part.strip() for part in raw_value.split(",")]
    if len(parts) != 3:
        raise ConfigError(f"expected name,size,bold, got {raw_value!r}")
    name, raw_size, raw_bold = parts
    if not name:
        raise ConfigError("font name must not be empty")
    size = _parse_int(raw_size)
    if size <= 0:
        raise ConfigError(f"font size must be > 0, got {raw_size!r}")
    bold = _parse_bool(raw_bold)
    return name, size, bold


def _parse_string_tuple(raw_value: str) -> tuple[str, ...]:
    parts = tuple(part.strip() for part in raw_value.split(","))
    if not parts or any(not part for part in parts):
        raise ConfigError(f"tuple items must not be empty, got {raw_value!r}")
    if len(parts) != len(set(parts)):
        raise ConfigError(f"tuple items must be unique, got {raw_value!r}")
    return parts
