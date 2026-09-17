# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Servicos imutaveis e transacionais para configuracao declarativa."""

from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import tempfile

from .config_contract import ConfigSnapshot
from .config_errors import ConfigError
from .config_loader import load_config
from .config_schema import CONFIG_SCHEMA, ConfigScope, ConfigValueType, get_field_spec
from .config_validation import validate_config_snapshot


def _scope_object(snapshot: ConfigSnapshot, scope: ConfigScope) -> object:
    """Seleciona o dataclass materializado correspondente ao escopo."""
    if scope is ConfigScope.NON_HOT:
        return snapshot.non_hot
    if scope is ConfigScope.OPERATOR:
        return snapshot.operator
    if scope is ConfigScope.HOT:
        return snapshot.hot
    raise ConfigError(f"Escopo de configuracao desconhecido: {scope!r}.")


def get_config_value(snapshot: ConfigSnapshot, env_key: str) -> object:
    """Le um valor materializado por sua chave declarativa canonica."""
    try:
        spec = get_field_spec(env_key)
    except KeyError as exc:
        raise ConfigError(f"Chave de configuracao desconhecida: {env_key}.") from exc
    return getattr(_scope_object(snapshot, spec.scope), spec.attr_name)


def updated_config(
    current: ConfigSnapshot,
    env_key: str,
    value: object,
) -> ConfigSnapshot:
    """Cria um candidato validado sem alterar snapshot, runtime ou arquivo."""
    if type(current) is not ConfigSnapshot:
        raise ConfigError("current deve ser ConfigSnapshot estrito.")
    try:
        spec = get_field_spec(env_key)
    except KeyError as exc:
        raise ConfigError(f"Chave de configuracao desconhecida: {env_key}.") from exc
    if not spec.editable:
        raise ConfigError(f"{env_key}: campo nao e editavel.")

    target = _scope_object(current, spec.scope)
    current_value = getattr(target, spec.attr_name)
    if value == current_value and type(value) is type(current_value):
        return current

    updated_scope = replace(target, **{spec.attr_name: value})
    if spec.scope is ConfigScope.NON_HOT:
        candidate = replace(current, non_hot=updated_scope)
    elif spec.scope is ConfigScope.OPERATOR:
        candidate = replace(current, operator=updated_scope)
    else:
        candidate = replace(current, hot=updated_scope)

    validate_config_snapshot(candidate)
    return candidate


def _serialize_value(value_type: ConfigValueType, value: object) -> str:
    """Converte um valor ja validado para a representacao textual canonica."""
    if value_type is ConfigValueType.INT:
        return str(value)
    if value_type is ConfigValueType.FLOAT:
        return repr(value)
    if value_type is ConfigValueType.BOOL:
        return "true" if value else "false"
    if value_type is ConfigValueType.STRING:
        return value
    if value_type is ConfigValueType.RGB:
        return ",".join(str(component) for component in value)
    if value_type is ConfigValueType.FONT:
        name, size, bold = value
        return f"{name},{size},{'true' if bold else 'false'}"
    if value_type is ConfigValueType.STRING_TUPLE:
        return ",".join(value)
    raise ConfigError(f"Tipo de schema nao serializavel: {value_type!r}.")


def serialize_config(snapshot: ConfigSnapshot) -> str:
    """Serializa um snapshot validado na ordem canonica do schema."""
    validate_config_snapshot(snapshot)
    lines = []
    for spec in CONFIG_SCHEMA:
        value = get_config_value(snapshot, spec.env_key)
        lines.append(f"{spec.env_key}={_serialize_value(spec.value_type, value)}")
    return "\n".join(lines) + "\n"


def write_config(path: str | Path, snapshot: ConfigSnapshot) -> None:
    """Grava um snapshot de forma atomica apos round-trip pelo loader canonico."""
    target = Path(path)
    text = serialize_config(snapshot)
    temp_path: Path | None = None

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, raw_temp_path = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
        )
        temp_path = Path(raw_temp_path)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())

        reloaded = load_config(temp_path)
        if reloaded != snapshot:
            raise ConfigError(
                "Round-trip do arquivo temporario divergiu do snapshot original."
            )

        os.replace(temp_path, target)
        temp_path = None
    except ConfigError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ConfigError(f"Falha ao gravar configuracao em {target}: {exc}") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
