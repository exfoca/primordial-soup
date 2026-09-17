# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Contrato das regras runtime da simulacao.

Este modulo representa apenas o contrato dos parametros que ja sao
runtime hoje, nao a configuracao estatica do mundo. Nao importa
state, nao conhece UI, nao conhece pygame, nao possui estado global.

A intencao e que RuntimeRules seja imutavel: uma alteracao cria um
novo objeto validado e somente entao substitui o objeto antigo em
state. Nenhum campo deve ser mutado parcialmente in-place.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

from . import config as cfg
from .config_contract import HotDefaults
from .config_errors import ConfigError
from .config_schema import ConfigScope, iter_scope
from .config_validation import validate_config_value


@dataclass(frozen=True, slots=True)
class RuntimeRules:
    """Regras runtime ajustaveis em execucao.

    Campos:
        crossover_mode:                operador de crossover canonico.
        crossover_probability:         viés por gene do crossover uniform.
        block_size:                    largura dos blocos no crossover blocks.
        mutation_mode:                 operador de mutacao canonico.
        mutation_rate:                 prob. de mutacao, em % inteiro.
        mutated_genes:                 genes afetados no modo surgical.
        local_scale_fraction:          fracao local, em % inteiro.
        local_scale_sigma:             sigma gaussiano do ramo local.
        global_probability:            chance do ramo global, em % inteiro.
        global_scale_fraction:         fracao global, em % inteiro.
        global_scale_sigma:            sigma gaussiano do ramo global.
        low_hp_threshold:              limiar sensorial de HP baixo.
        stay_still_impulse:            bias escalar da acao de ficar parado.
        death_hp_threshold:            HP <= limiar morre no tick ecologico.
        zone_hp_effect:                efeito de HP por tick em zona.
        base_decay_per_tick:           custo metabolico basal por tick.
        predation_transfer:            HP transferido por predacao.
        damage_per_own_overcrowding:   coeficiente de superlotacao propria.
        reproduction_interval:         ticks entre turnos reprodutivos.
        reproduction_min_age:          idade minima do pai elegivel.
        reproduction_hp_gate:          HP do pai deve ser MENOR que isto.
        reproduction_min_encounters:   encontros minimos do pai.
        reproduction_parent_hp_bonus:  HP ganho por pai, por evento.
        reproduction_criterion:         algoritmo de ranking dos pais.
        reproduction_pool_fraction:     fracao ranqueada no pool de pais.
        reproduction_attempts_divisor:  divisor das tentativas por turno.
        reproduction_min_score:         score composto minimo do pai.
        longevity_weight:               peso da longevidade no score.
        exploration_weight:             peso da exploracao no score.
        interaction_weight:             peso dos encontros no score.
        reproduction_weight:            peso dos descendentes no score.

    Nenhum campo e auto-corrigido. Valores fora dos limites de config
    sao rejeitados por validate_runtime_rules().
    """
    crossover_mode: str
    crossover_probability: float
    block_size: int
    mutation_mode: str
    mutation_rate: int
    mutated_genes: int
    local_scale_fraction: int
    local_scale_sigma: float
    global_probability: int
    global_scale_fraction: int
    global_scale_sigma: float
    low_hp_threshold: int
    stay_still_impulse: float
    death_hp_threshold: int
    zone_hp_effect: int
    base_decay_per_tick: int
    predation_transfer: int
    damage_per_own_overcrowding: int
    reproduction_interval: int
    reproduction_min_age: int
    reproduction_hp_gate: int
    reproduction_min_encounters: int
    reproduction_parent_hp_bonus: int
    reproduction_criterion: str
    reproduction_pool_fraction: float
    reproduction_attempts_divisor: int
    reproduction_min_score: float
    longevity_weight: float
    exploration_weight: float
    interaction_weight: float
    reproduction_weight: float


def default_runtime_rules() -> RuntimeRules:
    """Constroi RuntimeRules a partir do baseline declarativo HOT.

    HotDefaults ja usa as mesmas unidades e tipos de RuntimeRules; esta
    funcao nao converte percentuais nem mantem aliases legados. O
    candidato completo e validado antes de retornar.
    """
    hot = cfg.CONFIG_SNAPSHOT.hot
    candidate = RuntimeRules(
        crossover_mode=hot.crossover_mode,
        crossover_probability=hot.crossover_probability,
        block_size=hot.block_size,
        mutation_mode=hot.mutation_mode,
        mutation_rate=hot.mutation_rate,
        mutated_genes=hot.mutated_genes,
        local_scale_fraction=hot.local_scale_fraction,
        local_scale_sigma=hot.local_scale_sigma,
        global_probability=hot.global_probability,
        global_scale_fraction=hot.global_scale_fraction,
        global_scale_sigma=hot.global_scale_sigma,
        low_hp_threshold=hot.low_hp_threshold,
        stay_still_impulse=hot.stay_still_impulse,
        death_hp_threshold=hot.death_hp_threshold,
        zone_hp_effect=hot.zone_hp_effect,
        base_decay_per_tick=hot.base_decay_per_tick,
        predation_transfer=hot.predation_transfer,
        damage_per_own_overcrowding=hot.damage_per_own_overcrowding,
        reproduction_interval=hot.reproduction_interval,
        reproduction_min_age=hot.reproduction_min_age,
        reproduction_hp_gate=hot.reproduction_hp_gate,
        reproduction_min_encounters=hot.reproduction_min_encounters,
        reproduction_parent_hp_bonus=hot.reproduction_parent_hp_bonus,
        reproduction_criterion=hot.reproduction_criterion,
        reproduction_pool_fraction=hot.reproduction_pool_fraction,
        reproduction_attempts_divisor=hot.reproduction_attempts_divisor,
        reproduction_min_score=hot.reproduction_min_score,
        longevity_weight=hot.longevity_weight,
        exploration_weight=hot.exploration_weight,
        interaction_weight=hot.interaction_weight,
        reproduction_weight=hot.reproduction_weight,
    )
    validate_runtime_rules(candidate)
    return candidate


def validate_runtime_rules(rules: RuntimeRules) -> None:
    """Valida RuntimeRules pelo mesmo contrato canonico usado pelo loader."""
    if type(rules) is not RuntimeRules:
        raise ValueError("rules deve ser RuntimeRules estrito.")

    hot_values = {
        field.name: getattr(rules, field.name)
        for field in fields(HotDefaults)
    }
    candidate_snapshot = replace(
        cfg.CONFIG_SNAPSHOT,
        hot=HotDefaults(**hot_values),
    )

    try:
        for spec in iter_scope(ConfigScope.HOT):
            validate_config_value(
                spec,
                getattr(rules, spec.attr_name),
                candidate_snapshot,
            )
    except ConfigError as exc:
        raise ValueError(str(exc)) from exc


def updated_runtime_rules(current: RuntimeRules, **changes) -> RuntimeRules:
    """Cria um novo RuntimeRules com as mudancas aplicadas.

    Contrato:
        estado atual -> candidate -> validate(candidate) -> retorno

    Se qualquer mudanca for invalida, levanta ValueError e o objeto
    original permanece completamente intacto. Nao modifica current.
    """
    candidate = replace(current, **changes)
    validate_runtime_rules(candidate)

    # No-op semantico: se o candidate e igual ao current, nao
    # substitui a instancia. Um clamp que nao altera o valor efetivo
    # nao deve recriar o objeto. Propriedade central da abstracao.
    if candidate == current:
        return current

    return candidate