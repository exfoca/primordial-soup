# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Resolucao e validacao semantica do schema de configuracao."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .config_contract import (
    ConfigSnapshot,
    HotDefaults,
    NonHotConfig,
    OperatorDefaults,
)
from .config_errors import ConfigError
from .model_contract import derive_neural_layout
from .config_schema import (
    CONFIG_SCHEMA,
    ConfigDerivedRef,
    ConfigFieldRef,
    ConfigFieldSpec,
    ConfigScope,
    ConfigValueType,
)


@dataclass(frozen=True, slots=True)
class ResolvedConfigConstraints:
    """Constraints materializadas contra um snapshot especifico."""

    minimum: int | float | None
    maximum: int | float | None
    minimum_inclusive: bool
    maximum_inclusive: bool
    step: int | float | None
    choices: tuple[object, ...] | None


def _scope_object(snapshot: ConfigSnapshot, scope: ConfigScope) -> object:
    """Seleciona o dataclass de valores pertencente ao escopo solicitado."""
    if scope is ConfigScope.NON_HOT:
        return snapshot.non_hot
    if scope is ConfigScope.OPERATOR:
        return snapshot.operator
    if scope is ConfigScope.HOT:
        return snapshot.hot
    raise ConfigError(f"Escopo de configuracao desconhecido: {scope!r}.")


def _resolve_field_ref(ref: ConfigFieldRef, snapshot: ConfigSnapshot) -> object:
    """Resolve uma referencia exclusivamente no snapshot recebido."""
    target = _scope_object(snapshot, ref.scope)
    try:
        return getattr(target, ref.attr_name)
    except AttributeError as exc:
        raise ConfigError(
            "Referencia de configuracao inexistente: "
            f"{ref.scope.value}.{ref.attr_name}."
        ) from exc


def _resolve_genome_size(snapshot: ConfigSnapshot) -> int:
    """Adapta o snapshot para a autoridade unica de derivacao neural."""
    non_hot = snapshot.non_hot
    return derive_neural_layout(
        vision_radius=non_hot.vision_radius,
        hidden_neurons=non_hot.hidden_neurons,
        hidden_neurons_2=non_hot.hidden_neurons_2,
    ).genome_size


def _resolve_bound(
    value: int | float | ConfigFieldRef | ConfigDerivedRef | None,
    snapshot: ConfigSnapshot,
) -> int | float | None:
    """Materializa um bound numerico literal, referenciado ou derivado."""
    if value is None:
        return None
    if isinstance(value, ConfigFieldRef):
        resolved = _resolve_field_ref(value, snapshot)
        if type(resolved) not in {int, float}:
            raise ConfigError(
                "Referencia usada como bound nao resolve para numero: "
                f"{value.scope.value}.{value.attr_name}."
            )
        return resolved
    if value is ConfigDerivedRef.GENOME_SIZE:
        return _resolve_genome_size(snapshot)
    if type(value) in {int, float}:
        return value
    raise ConfigError(f"Bound de configuracao nao suportado: {value!r}.")


def _resolve_choices(
    value: tuple[object, ...] | ConfigFieldRef | None,
    snapshot: ConfigSnapshot,
) -> tuple[object, ...] | None:
    """Materializa um dominio fechado literal ou referenciado."""
    if value is None:
        return None
    if isinstance(value, ConfigFieldRef):
        resolved = _resolve_field_ref(value, snapshot)
        if type(resolved) is not tuple:
            raise ConfigError(
                "Referencia usada como choices nao resolve para tuple: "
                f"{value.scope.value}.{value.attr_name}."
            )
        return resolved
    return value


def resolve_constraints(
    spec: ConfigFieldSpec,
    snapshot: ConfigSnapshot,
) -> ResolvedConfigConstraints:
    """Resolve as constraints de um campo contra o snapshot informado."""
    if type(snapshot) is not ConfigSnapshot:
        raise ConfigError("snapshot deve ser ConfigSnapshot estrito.")

    constraints = spec.constraints
    minimum = _resolve_bound(constraints.minimum, snapshot)
    maximum = _resolve_bound(constraints.maximum, snapshot)
    choices = _resolve_choices(constraints.choices, snapshot)

    if minimum is not None and maximum is not None:
        if minimum > maximum:
            raise ConfigError(
                f"{spec.env_key}: range resolvido invertido: "
                f"{minimum!r} > {maximum!r}."
            )
        if minimum == maximum and (
            not constraints.minimum_inclusive
            or not constraints.maximum_inclusive
        ):
            raise ConfigError(f"{spec.env_key}: range resolvido vazio.")

    return ResolvedConfigConstraints(
        minimum=minimum,
        maximum=maximum,
        minimum_inclusive=constraints.minimum_inclusive,
        maximum_inclusive=constraints.maximum_inclusive,
        step=constraints.step,
        choices=choices,
    )


def _reject_unrepresentable_text(
    env_key: str,
    value: str,
    *,
    comma_forbidden: bool = False,
) -> None:
    """Garante round-trip pela gramatica textual do loader."""
    if value != value.strip():
        raise ConfigError(f"{env_key}: texto nao pode ter espaco externo.")
    if "\n" in value or "\r" in value:
        raise ConfigError(f"{env_key}: texto nao pode conter quebra de linha.")
    if "$" in value:
        raise ConfigError(f"{env_key}: interpolacao com '$' nao e suportada.")
    if comma_forbidden and "," in value:
        raise ConfigError(f"{env_key}: texto nao pode conter virgula.")


def _validate_type(spec: ConfigFieldSpec, value: object) -> None:
    """Aplica o contrato estrito de tipos sem coercao."""
    value_type = spec.value_type

    if value_type is ConfigValueType.INT:
        if type(value) is not int:
            raise ConfigError(f"{spec.env_key}: valor deve ser int estrito.")
        return

    if value_type is ConfigValueType.FLOAT:
        if type(value) is not float:
            raise ConfigError(f"{spec.env_key}: valor deve ser float estrito.")
        if not math.isfinite(value):
            raise ConfigError(f"{spec.env_key}: float deve ser finito.")
        return

    if value_type is ConfigValueType.BOOL:
        if type(value) is not bool:
            raise ConfigError(f"{spec.env_key}: valor deve ser bool estrito.")
        return

    if value_type is ConfigValueType.STRING:
        if type(value) is not str or not value:
            raise ConfigError(f"{spec.env_key}: string deve ser nao vazia.")
        _reject_unrepresentable_text(spec.env_key, value)
        return

    if value_type is ConfigValueType.RGB:
        if type(value) is not tuple or len(value) != 3:
            raise ConfigError(f"{spec.env_key}: RGB deve conter exatamente 3 itens.")
        if any(type(component) is not int for component in value):
            raise ConfigError(f"{spec.env_key}: componentes RGB devem ser ints estritos.")
        if any(component < 0 or component > 255 for component in value):
            raise ConfigError(f"{spec.env_key}: componentes RGB devem estar em [0, 255].")
        return

    if value_type is ConfigValueType.FONT:
        if type(value) is not tuple or len(value) != 3:
            raise ConfigError(f"{spec.env_key}: FONT deve ser (nome, tamanho, negrito).")
        name, size, bold = value
        if type(name) is not str or not name:
            raise ConfigError(f"{spec.env_key}: nome da fonte deve ser string nao vazia.")
        _reject_unrepresentable_text(spec.env_key, name, comma_forbidden=True)
        if type(size) is not int or size <= 0:
            raise ConfigError(f"{spec.env_key}: tamanho da fonte deve ser int > 0.")
        if type(bold) is not bool:
            raise ConfigError(f"{spec.env_key}: flag bold deve ser bool estrito.")
        return

    if value_type is ConfigValueType.STRING_TUPLE:
        if type(value) is not tuple or not value:
            raise ConfigError(f"{spec.env_key}: tuple de strings deve ser nao vazio.")
        if any(type(item) is not str or not item for item in value):
            raise ConfigError(f"{spec.env_key}: itens devem ser strings nao vazias.")
        if len(value) != len(set(value)):
            raise ConfigError(f"{spec.env_key}: itens devem ser unicos.")
        for item in value:
            _reject_unrepresentable_text(
                spec.env_key,
                item,
                comma_forbidden=True,
            )
        return

    raise ConfigError(f"{spec.env_key}: tipo de schema nao suportado: {value_type!r}.")


def validate_config_value(
    spec: ConfigFieldSpec,
    value: object,
    snapshot: ConfigSnapshot,
) -> None:
    """Valida um valor usando tipo e constraints canonicas do schema."""
    _validate_type(spec, value)
    constraints = resolve_constraints(spec, snapshot)

    if constraints.choices is not None and value not in constraints.choices:
        raise ConfigError(
            f"{spec.env_key}: valor fora do dominio {constraints.choices!r}: {value!r}."
        )

    if spec.value_type in {ConfigValueType.INT, ConfigValueType.FLOAT}:
        if constraints.minimum is not None:
            if constraints.minimum_inclusive:
                valid_minimum = value >= constraints.minimum
            else:
                valid_minimum = value > constraints.minimum
            if not valid_minimum:
                operator = ">=" if constraints.minimum_inclusive else ">"
                raise ConfigError(
                    f"{spec.env_key}: valor deve ser {operator} "
                    f"{constraints.minimum!r}: {value!r}."
                )

        if constraints.maximum is not None:
            if constraints.maximum_inclusive:
                valid_maximum = value <= constraints.maximum
            else:
                valid_maximum = value < constraints.maximum
            if not valid_maximum:
                operator = "<=" if constraints.maximum_inclusive else "<"
                raise ConfigError(
                    f"{spec.env_key}: valor deve ser {operator} "
                    f"{constraints.maximum!r}: {value!r}."
                )


def validate_config_snapshot(snapshot: ConfigSnapshot) -> None:
    """Valida integralmente um snapshot sem normalizar nem mutar valores."""
    if type(snapshot) is not ConfigSnapshot:
        raise ConfigError("snapshot deve ser ConfigSnapshot estrito.")
    if type(snapshot.non_hot) is not NonHotConfig:
        raise ConfigError("snapshot.non_hot deve ser NonHotConfig estrito.")
    if type(snapshot.operator) is not OperatorDefaults:
        raise ConfigError("snapshot.operator deve ser OperatorDefaults estrito.")
    if type(snapshot.hot) is not HotDefaults:
        raise ConfigError("snapshot.hot deve ser HotDefaults estrito.")

    for spec in CONFIG_SCHEMA:
        target = _scope_object(snapshot, spec.scope)
        try:
            value = getattr(target, spec.attr_name)
        except AttributeError as exc:
            raise ConfigError(
                f"{spec.env_key}: destino ausente no snapshot: {spec.attr_name}."
            ) from exc
        validate_config_value(spec, value, snapshot)

    save_slots = snapshot.non_hot.save_slots
    if any("/" in slot or "\\" in slot for slot in save_slots):
        raise ConfigError(
            "SAVE_SLOTS: itens nao podem conter separadores de caminho."
        )
