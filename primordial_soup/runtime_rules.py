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

from dataclasses import dataclass, replace
import math

from . import config as cfg


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
    """Constroi o RuntimeRules inicial a partir dos defaults de config.

    Nao renomeia nem cria DEFAULT_* em config.py neste patch; apenas
    le as constantes existentes. Valida o proprio resultado antes de
    retornar, para erros de config falharem cedo no bootstrap.
    """
    candidate = RuntimeRules(
        crossover_mode=cfg.CROSSOVER_MODE,
        crossover_probability=float(cfg.CROSSOVER_PROBABILITY),
        block_size=int(cfg.BLOCK_SIZE),
        mutation_mode=cfg.MUTATION_MODE,
        mutation_rate=int(cfg.INITIAL_MUTATION_RATE),
        mutated_genes=int(cfg.INITIAL_MUTATED_GENES),
        local_scale_fraction=int(cfg.LOCAL_SCALE_FRACTION * 100),
        local_scale_sigma=float(cfg.LOCAL_SCALE_SIGMA),
        global_probability=int(cfg.GLOBAL_PROBABILITY * 100),
        global_scale_fraction=int(cfg.GLOBAL_SCALE_FRACTION * 100),
        global_scale_sigma=float(cfg.GLOBAL_SCALE_SIGMA),
        low_hp_threshold=int(cfg.LOW_HP_THRESHOLD),
        stay_still_impulse=float(cfg.STAY_STILL_IMPULSE),
        death_hp_threshold=int(cfg.DIE_WHEN_HP_LESS_OR_EQUAL),
        zone_hp_effect=int(cfg.HP_EFFECT_IN_ZONE),
        base_decay_per_tick=int(cfg.BASE_DECAY_PER_TICK),
        predation_transfer=int(cfg.PREDATION_TRANSFER),
        damage_per_own_overcrowding=int(cfg.DAMAGE_PER_OWN_OVERCROWDING),
        reproduction_interval=int(cfg.REPRODUCTION_INTERVAL),
        reproduction_min_age=int(cfg.REPRODUCTION_MIN_AGE),
        reproduction_hp_gate=int(cfg.REPRODUCTION_HP_GATE),
        reproduction_min_encounters=int(cfg.REPRODUCTION_MIN_ENCOUNTERS),
        reproduction_parent_hp_bonus=int(cfg.REPRODUCTION_PARENT_HP_BONUS),
        reproduction_criterion=cfg.REPRODUCTION_CRITERION,
        reproduction_pool_fraction=float(cfg.REPRODUCTIVE_POOL_FRACTION),
        reproduction_attempts_divisor=int(cfg.REPRODUCTION_ATTEMPTS_DIVISOR),
        reproduction_min_score=float(cfg.REPRODUCTION_MIN_SCORE),
        longevity_weight=float(cfg.LONGEVITY_WEIGHT),
        exploration_weight=float(cfg.EXPLORATION_WEIGHT),
        interaction_weight=float(cfg.INTERACTION_WEIGHT),
        reproduction_weight=float(cfg.REPRODUCTION_WEIGHT),
    )
    validate_runtime_rules(candidate)
    return candidate


def _validate_float_field(
    name: str,
    value: float,
    minimum: float,
    maximum: float,
) -> None:
    """Valida um float runtime estrito, finito e dentro da faixa."""
    if type(value) is not float:
        raise ValueError(
            f"{name} deve ser float estrito, "
            f"recebido {type(value).__name__}."
        )
    if not math.isfinite(value):
        raise ValueError(f"{name} deve ser finito: {value}.")
    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name} fora do range [{minimum}, {maximum}]: {value}."
        )


def _validate_choice_field(
    name: str,
    value: str,
    allowed,
) -> None:
    """Valida uma string canonica sem normalizacao ou coercao."""
    if type(value) is not str:
        raise ValueError(
            f"{name} deve ser str estrita, "
            f"recebido {type(value).__name__}."
        )
    if value not in allowed:
        raise ValueError(
            f"{name} fora do dominio permitido {tuple(allowed)!r}: {value!r}."
        )


def validate_runtime_rules(rules: RuntimeRules) -> None:
    """Valida todos os campos de um RuntimeRules.

    Levanta ValueError para valor semanticamente invalido. Nao faz
    clamp: a validacao responde apenas valido/invalido. Clamp e
    responsabilidade de quem converte seta do usuario em novo valor.

    Checagem de tipo estrita: type(x) is int, nao isinstance(x, int),
    porque isinstance(True, int) e True e True nao e um valor
    runtime valido.
    """
    _validate_choice_field(
        "crossover_mode",
        rules.crossover_mode,
        cfg.CROSSOVER_MODES,
    )
    _validate_float_field(
        "crossover_probability",
        rules.crossover_probability,
        cfg.MIN_CROSSOVER_PROBABILITY,
        cfg.MAX_CROSSOVER_PROBABILITY,
    )
    if type(rules.block_size) is not int:
        raise ValueError(
            f"block_size deve ser int estrito, "
            f"recebido {type(rules.block_size).__name__}."
        )
    if not cfg.MIN_BLOCK_SIZE <= rules.block_size <= cfg.MAX_BLOCK_SIZE:
        raise ValueError(
            f"block_size fora do range "
            f"[{cfg.MIN_BLOCK_SIZE}, {cfg.MAX_BLOCK_SIZE}]: "
            f"{rules.block_size}."
        )
    _validate_choice_field(
        "mutation_mode",
        rules.mutation_mode,
        cfg.MUTATION_MODES,
    )

    if type(rules.mutation_rate) is not int:
        raise ValueError(
            f"mutation_rate deve ser int estrito, "
            f"recebido {type(rules.mutation_rate).__name__}."
        )
    if not cfg.MIN_MUTATION_RATE <= rules.mutation_rate <= cfg.MAX_MUTATION_RATE:
        raise ValueError(
            f"mutation_rate fora do range "
            f"[{cfg.MIN_MUTATION_RATE}, {cfg.MAX_MUTATION_RATE}]: "
            f"{rules.mutation_rate}."
        )

    if type(rules.mutated_genes) is not int:
        raise ValueError(
            f"mutated_genes deve ser int estrito, "
            f"recebido {type(rules.mutated_genes).__name__}."
        )
    if not cfg.MIN_MUTATED_GENES <= rules.mutated_genes <= cfg.MAX_MUTATED_GENES:
        raise ValueError(
            f"mutated_genes fora do range "
            f"[{cfg.MIN_MUTATED_GENES}, {cfg.MAX_MUTATED_GENES}]: "
            f"{rules.mutated_genes}."
        )

    if type(rules.local_scale_fraction) is not int:
        raise ValueError(
            f"local_scale_fraction deve ser int estrito, "
            f"recebido {type(rules.local_scale_fraction).__name__}."
        )
    if not (
        cfg.MIN_LOCAL_SCALE_FRACTION
        <= rules.local_scale_fraction
        <= cfg.MAX_LOCAL_SCALE_FRACTION
    ):
        raise ValueError(
            f"local_scale_fraction fora do range "
            f"[{cfg.MIN_LOCAL_SCALE_FRACTION}, {cfg.MAX_LOCAL_SCALE_FRACTION}]: "
            f"{rules.local_scale_fraction}."
        )

    _validate_float_field(
        "local_scale_sigma",
        rules.local_scale_sigma,
        cfg.MIN_MUTATION_SIGMA,
        cfg.MAX_MUTATION_SIGMA,
    )

    if type(rules.global_probability) is not int:
        raise ValueError(
            f"global_probability deve ser int estrito, "
            f"recebido {type(rules.global_probability).__name__}."
        )
    if not (
        cfg.MIN_GLOBAL_PROBABILITY
        <= rules.global_probability
        <= cfg.MAX_GLOBAL_PROBABILITY
    ):
        raise ValueError(
            f"global_probability fora do range "
            f"[{cfg.MIN_GLOBAL_PROBABILITY}, {cfg.MAX_GLOBAL_PROBABILITY}]: "
            f"{rules.global_probability}."
        )

    if type(rules.global_scale_fraction) is not int:
        raise ValueError(
            f"global_scale_fraction deve ser int estrito, "
            f"recebido {type(rules.global_scale_fraction).__name__}."
        )
    if not (
        cfg.MIN_GLOBAL_SCALE_FRACTION
        <= rules.global_scale_fraction
        <= cfg.MAX_GLOBAL_SCALE_FRACTION
    ):
        raise ValueError(
            f"global_scale_fraction fora do range "
            f"[{cfg.MIN_GLOBAL_SCALE_FRACTION}, "
            f"{cfg.MAX_GLOBAL_SCALE_FRACTION}]: "
            f"{rules.global_scale_fraction}."
        )

    _validate_float_field(
        "global_scale_sigma",
        rules.global_scale_sigma,
        cfg.MIN_MUTATION_SIGMA,
        cfg.MAX_MUTATION_SIGMA,
    )

    if type(rules.low_hp_threshold) is not int:
        raise ValueError(
            "low_hp_threshold deve ser int estrito, "
            f"recebido {type(rules.low_hp_threshold).__name__}."
        )
    if not (
        cfg.MIN_LOW_HP_THRESHOLD
        <= rules.low_hp_threshold
        <= cfg.MAX_LOW_HP_THRESHOLD
    ):
        raise ValueError(
            "low_hp_threshold fora do range "
            f"[{cfg.MIN_LOW_HP_THRESHOLD}, {cfg.MAX_LOW_HP_THRESHOLD}]: "
            f"{rules.low_hp_threshold}."
        )

    if type(rules.stay_still_impulse) is not float:
        raise ValueError(
            "stay_still_impulse deve ser float estrito, "
            f"recebido {type(rules.stay_still_impulse).__name__}."
        )
    if not math.isfinite(rules.stay_still_impulse):
        raise ValueError(
            f"stay_still_impulse deve ser finito: {rules.stay_still_impulse}."
        )

    if type(rules.death_hp_threshold) is not int:
        raise ValueError(
            "death_hp_threshold deve ser int estrito, "
            f"recebido {type(rules.death_hp_threshold).__name__}."
        )
    if not (
        cfg.MIN_DEATH_HP_THRESHOLD
        <= rules.death_hp_threshold
        <= cfg.MAX_DEATH_HP_THRESHOLD
    ):
        raise ValueError(
            "death_hp_threshold fora do range "
            f"[{cfg.MIN_DEATH_HP_THRESHOLD}, {cfg.MAX_DEATH_HP_THRESHOLD}]: "
            f"{rules.death_hp_threshold}."
        )

    if type(rules.zone_hp_effect) is not int:
        raise ValueError(
            f"zone_hp_effect deve ser int estrito, "
            f"recebido {type(rules.zone_hp_effect).__name__}."
        )
    if not cfg.MIN_ZONE_HP_EFFECT <= rules.zone_hp_effect <= cfg.MAX_ZONE_HP_EFFECT:
        raise ValueError(
            f"zone_hp_effect fora do range "
            f"[{cfg.MIN_ZONE_HP_EFFECT}, {cfg.MAX_ZONE_HP_EFFECT}]: "
            f"{rules.zone_hp_effect}."
        )

    if type(rules.base_decay_per_tick) is not int:
        raise ValueError(
            f"base_decay_per_tick deve ser int estrito, "
            f"recebido {type(rules.base_decay_per_tick).__name__}."
        )
    if not (
        cfg.MIN_BASE_DECAY_PER_TICK
        <= rules.base_decay_per_tick
        <= cfg.MAX_BASE_DECAY_PER_TICK
    ):
        raise ValueError(
            f"base_decay_per_tick fora do range "
            f"[{cfg.MIN_BASE_DECAY_PER_TICK}, {cfg.MAX_BASE_DECAY_PER_TICK}]: "
            f"{rules.base_decay_per_tick}."
        )

    if type(rules.predation_transfer) is not int:
        raise ValueError(
            f"predation_transfer deve ser int estrito, "
            f"recebido {type(rules.predation_transfer).__name__}."
        )
    if not (
        cfg.MIN_PREDATION_TRANSFER
        <= rules.predation_transfer
        <= cfg.MAX_PREDATION_TRANSFER
    ):
        raise ValueError(
            f"predation_transfer fora do range "
            f"[{cfg.MIN_PREDATION_TRANSFER}, {cfg.MAX_PREDATION_TRANSFER}]: "
            f"{rules.predation_transfer}."
        )

    if type(rules.damage_per_own_overcrowding) is not int:
        raise ValueError(
            f"damage_per_own_overcrowding deve ser int estrito, "
            f"recebido {type(rules.damage_per_own_overcrowding).__name__}."
        )
    if not (
        cfg.MIN_DAMAGE_PER_OWN_OVERCROWDING
        <= rules.damage_per_own_overcrowding
        <= cfg.MAX_DAMAGE_PER_OWN_OVERCROWDING
    ):
        raise ValueError(
            f"damage_per_own_overcrowding fora do range "
            f"[{cfg.MIN_DAMAGE_PER_OWN_OVERCROWDING}, "
            f"{cfg.MAX_DAMAGE_PER_OWN_OVERCROWDING}]: "
            f"{rules.damage_per_own_overcrowding}."
        )

    if type(rules.reproduction_interval) is not int:
        raise ValueError(
            f"reproduction_interval deve ser int estrito, "
            f"recebido {type(rules.reproduction_interval).__name__}."
        )
    if not (
        cfg.MIN_REPRODUCTION_INTERVAL
        <= rules.reproduction_interval
        <= cfg.MAX_REPRODUCTION_INTERVAL
    ):
        raise ValueError(
            f"reproduction_interval fora do range "
            f"[{cfg.MIN_REPRODUCTION_INTERVAL}, "
            f"{cfg.MAX_REPRODUCTION_INTERVAL}]: "
            f"{rules.reproduction_interval}."
        )

    if type(rules.reproduction_min_age) is not int:
        raise ValueError(
            f"reproduction_min_age deve ser int estrito, "
            f"recebido {type(rules.reproduction_min_age).__name__}."
        )
    if not (
        cfg.MIN_REPRODUCTION_MIN_AGE
        <= rules.reproduction_min_age
        <= cfg.MAX_REPRODUCTION_MIN_AGE
    ):
        raise ValueError(
            f"reproduction_min_age fora do range "
            f"[{cfg.MIN_REPRODUCTION_MIN_AGE}, "
            f"{cfg.MAX_REPRODUCTION_MIN_AGE}]: "
            f"{rules.reproduction_min_age}."
        )

    if type(rules.reproduction_hp_gate) is not int:
        raise ValueError(
            f"reproduction_hp_gate deve ser int estrito, "
            f"recebido {type(rules.reproduction_hp_gate).__name__}."
        )
    if not (
        cfg.MIN_REPRODUCTION_HP_GATE
        <= rules.reproduction_hp_gate
        <= cfg.MAX_REPRODUCTION_HP_GATE
    ):
        raise ValueError(
            f"reproduction_hp_gate fora do range "
            f"[{cfg.MIN_REPRODUCTION_HP_GATE}, "
            f"{cfg.MAX_REPRODUCTION_HP_GATE}]: "
            f"{rules.reproduction_hp_gate}."
        )

    if type(rules.reproduction_min_encounters) is not int:
        raise ValueError(
            f"reproduction_min_encounters deve ser int estrito, "
            f"recebido {type(rules.reproduction_min_encounters).__name__}."
        )
    if not (
        cfg.MIN_REPRODUCTION_MIN_ENCOUNTERS
        <= rules.reproduction_min_encounters
        <= cfg.MAX_REPRODUCTION_MIN_ENCOUNTERS
    ):
        raise ValueError(
            f"reproduction_min_encounters fora do range "
            f"[{cfg.MIN_REPRODUCTION_MIN_ENCOUNTERS}, "
            f"{cfg.MAX_REPRODUCTION_MIN_ENCOUNTERS}]: "
            f"{rules.reproduction_min_encounters}."
        )

    if type(rules.reproduction_parent_hp_bonus) is not int:
        raise ValueError(
            f"reproduction_parent_hp_bonus deve ser int estrito, "
            f"recebido {type(rules.reproduction_parent_hp_bonus).__name__}."
        )
    if not (
        cfg.MIN_REPRODUCTION_PARENT_HP_BONUS
        <= rules.reproduction_parent_hp_bonus
        <= cfg.MAX_REPRODUCTION_PARENT_HP_BONUS
    ):
        raise ValueError(
            f"reproduction_parent_hp_bonus fora do range "
            f"[{cfg.MIN_REPRODUCTION_PARENT_HP_BONUS}, "
            f"{cfg.MAX_REPRODUCTION_PARENT_HP_BONUS}]: "
            f"{rules.reproduction_parent_hp_bonus}."
        )
    _validate_choice_field(
        "reproduction_criterion",
        rules.reproduction_criterion,
        cfg.REPRODUCTION_CRITERIA,
    )
    _validate_float_field(
        "reproduction_pool_fraction",
        rules.reproduction_pool_fraction,
        cfg.MIN_REPRODUCTION_POOL_FRACTION,
        cfg.MAX_REPRODUCTION_POOL_FRACTION,
    )
    if type(rules.reproduction_attempts_divisor) is not int:
        raise ValueError(
            "reproduction_attempts_divisor deve ser int estrito, "
            f"recebido {type(rules.reproduction_attempts_divisor).__name__}."
        )
    if not (
        cfg.MIN_REPRODUCTION_ATTEMPTS_DIVISOR
        <= rules.reproduction_attempts_divisor
        <= cfg.MAX_REPRODUCTION_ATTEMPTS_DIVISOR
    ):
        raise ValueError(
            "reproduction_attempts_divisor fora do range "
            f"[{cfg.MIN_REPRODUCTION_ATTEMPTS_DIVISOR}, "
            f"{cfg.MAX_REPRODUCTION_ATTEMPTS_DIVISOR}]: "
            f"{rules.reproduction_attempts_divisor}."
        )
    _validate_float_field(
        "reproduction_min_score",
        rules.reproduction_min_score,
        cfg.MIN_REPRODUCTION_MIN_SCORE,
        cfg.MAX_REPRODUCTION_MIN_SCORE,
    )
    _validate_float_field(
        "longevity_weight",
        rules.longevity_weight,
        cfg.MIN_SELECTION_WEIGHT,
        cfg.MAX_SELECTION_WEIGHT,
    )
    _validate_float_field(
        "exploration_weight",
        rules.exploration_weight,
        cfg.MIN_SELECTION_WEIGHT,
        cfg.MAX_SELECTION_WEIGHT,
    )
    _validate_float_field(
        "interaction_weight",
        rules.interaction_weight,
        cfg.MIN_SELECTION_WEIGHT,
        cfg.MAX_SELECTION_WEIGHT,
    )
    _validate_float_field(
        "reproduction_weight",
        rules.reproduction_weight,
        cfg.MIN_SELECTION_WEIGHT,
        cfg.MAX_SELECTION_WEIGHT,
    )


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