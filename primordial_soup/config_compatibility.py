# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Compatibilidade NON-HOT necessaria para continuar checkpoints."""

from __future__ import annotations

from .config_contract import ConfigSnapshot
from .config_errors import ConfigError
from .config_schema import iter_checkpoint_relevant
from .config_validation import validate_config_snapshot


def checkpoint_non_hot_payload(
    snapshot: ConfigSnapshot,
) -> dict[str, object]:
    """Materializa os valores NON-HOT que definem continuidade."""
    validate_config_snapshot(snapshot)
    return {
        spec.env_key: getattr(snapshot.non_hot, spec.attr_name)
        for spec in iter_checkpoint_relevant()
    }


def validate_checkpoint_non_hot_payload(
    payload: object,
    snapshot: ConfigSnapshot,
) -> None:
    """Exige identidade estrita entre metadata salva e processo atual."""
    validate_config_snapshot(snapshot)
    expected = checkpoint_non_hot_payload(snapshot)

    if type(payload) is not dict:
        raise ConfigError(
            "config_non_hot: payload deve ser dict estrito; "
            f"recebido {type(payload).__name__}."
        )

    expected_keys = tuple(expected)
    missing = [key for key in expected_keys if key not in payload]
    extra = [key for key in payload if key not in expected]
    if missing or extra:
        raise ConfigError(
            "config_non_hot key mismatch: "
            f"missing={missing!r}, extra={extra!r}."
        )

    for env_key in expected_keys:
        saved_value = payload[env_key]
        current_value = expected[env_key]
        if type(saved_value) is not type(current_value):
            raise ConfigError(
                f"{env_key}: saved type={type(saved_value).__name__}, "
                f"current type={type(current_value).__name__}."
            )
        if saved_value != current_value:
            raise ConfigError(
                f"{env_key}: saved={saved_value!r}, current={current_value!r}."
            )
