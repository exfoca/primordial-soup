# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Composicao concreta dos paineis da interface.

Este modulo e a camada que conhece DOMINIO: chama world, state,
persistence, recording, i18n. panels.py permanece neutro. O
dispatcher permanece neutro. A ligacao acontece aqui.

Registro explicito: register_default_panels() e chamado pelo
bootstrap grafico (simulation.run). Importar este modulo NAO altera
estado global.
"""

from __future__ import annotations

import pygame

from . import config as cfg
from . import i18n
from . import persistence
from . import prefs
from . import state
from . import ui_state
from . import world
from .panels import (
    DispatchResult,
    Item,
    ItemKind,
    Panel,
    register,
)


# --- Helpers de valor (value_fn) ------------------------------------------


def _v_crossover_mode() -> str:
    return i18n.t(
        "crossover_mode."
        f"{state.runtime_rules.crossover_mode}"
    )


def _v_crossover_probability() -> str:
    return f"{state.runtime_rules.crossover_probability * 100:.0f}%"


def _v_block_size() -> str:
    return str(state.runtime_rules.block_size)


def _v_mutation_mode() -> str:
    return i18n.t(
        "hud.value.mutation_mode."
        f"{state.runtime_rules.mutation_mode}"
    )


def _v_mutation_rate() -> str:
    return f"{state.runtime_rules.mutation_rate}%"


def _v_local_scale() -> str:
    return f"{state.runtime_rules.local_scale_fraction}%"


def _v_local_scale_sigma() -> str:
    return f"{state.runtime_rules.local_scale_sigma:.2f}"


def _v_global_probability() -> str:
    return f"{state.runtime_rules.global_probability}%"


def _v_global_scale_fraction() -> str:
    return f"{state.runtime_rules.global_scale_fraction}%"


def _v_global_scale_sigma() -> str:
    return f"{state.runtime_rules.global_scale_sigma:.2f}"


def _v_stay_still_impulse() -> str:
    return f"{state.runtime_rules.stay_still_impulse:.1f}"


def _v_speed() -> str:
    return f"{state.simulation_speed:g}x"


def _v_zones() -> str:
    return i18n.t("hud.on" if state.zones_active else "hud.off")


def _v_zone_hp() -> str:
    effect = state.runtime_rules.zone_hp_effect
    sign = "+" if effect >= 0 else ""
    return f"{sign}{effect}"


def _v_base_decay() -> str:
    return str(state.runtime_rules.base_decay_per_tick)


def _v_low_hp_threshold() -> str:
    return str(state.runtime_rules.low_hp_threshold)


def _v_death_hp_threshold() -> str:
    return str(state.runtime_rules.death_hp_threshold)


def _v_predation_transfer() -> str:
    return str(state.runtime_rules.predation_transfer)


def _v_overcrowding_factor() -> str:
    return str(state.runtime_rules.damage_per_own_overcrowding)


def _v_reproduction_interval() -> str:
    return str(state.runtime_rules.reproduction_interval)


def _v_reproduction_min_age() -> str:
    return str(state.runtime_rules.reproduction_min_age)


def _v_reproduction_hp_gate() -> str:
    return str(state.runtime_rules.reproduction_hp_gate)


def _v_reproduction_min_encounters() -> str:
    return str(state.runtime_rules.reproduction_min_encounters)


def _v_reproduction_parent_hp_bonus() -> str:
    return str(state.runtime_rules.reproduction_parent_hp_bonus)


def _v_reproduction_criterion() -> str:
    return i18n.t(
        "reproduction_criterion."
        f"{state.runtime_rules.reproduction_criterion}"
    )


def _v_reproduction_pool_fraction() -> str:
    return f"{state.runtime_rules.reproduction_pool_fraction * 100:.0f}%"


def _v_reproduction_attempts_divisor() -> str:
    return str(state.runtime_rules.reproduction_attempts_divisor)


def _v_reproduction_min_score() -> str:
    return f"{state.runtime_rules.reproduction_min_score:.1f}"


def _v_longevity_weight() -> str:
    return f"{state.runtime_rules.longevity_weight:.1f}"


def _v_exploration_weight() -> str:
    return f"{state.runtime_rules.exploration_weight:.1f}"


def _v_interaction_weight() -> str:
    return f"{state.runtime_rules.interaction_weight:.1f}"


def _v_reproduction_weight() -> str:
    return f"{state.runtime_rules.reproduction_weight:.1f}"


def _v_save_slot() -> str:
    return state.active_save_slot


def _v_language() -> str:
    return state.language.upper()


def _v_recording() -> str:
    return i18n.t("hud.on" if state.recording else "hud.off")


def _v_criterion() -> str:
    return i18n.t(f"criterion.{state.discovery_criterion}")


def _v_lineage_filter() -> str:
    return i18n.t(f"lineage_filter.{state.discovery_lineage_filter}")


# --- Handlers: modos geneticos (ENUM) -------------------------------------


def _h_crossover_mode(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    order = cfg.CROSSOVER_MODES
    current = state.runtime_rules.crossover_mode
    index = order.index(current)
    candidate = order[(index + direction) % len(order)]
    state.update_runtime_rules(crossover_mode=candidate)
    return DispatchResult.continue_(redraw=True)


def _h_mutation_mode(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    order = cfg.MUTATION_MODES
    current = state.runtime_rules.mutation_mode
    index = order.index(current)
    candidate = order[(index + direction) % len(order)]
    state.update_runtime_rules(mutation_mode=candidate)
    return DispatchResult.continue_(redraw=True)


def _h_crossover_probability(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_float(
        "crossover_probability",
        direction,
        step=0.05,
        minimum=cfg.MIN_CROSSOVER_PROBABILITY,
        maximum=cfg.MAX_CROSSOVER_PROBABILITY,
        precision=2,
    )
    return DispatchResult.continue_(redraw=True)


def _h_block_size(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_int(
        "block_size",
        direction,
        step=1,
        minimum=cfg.MIN_BLOCK_SIZE,
        maximum=cfg.MAX_BLOCK_SIZE,
    )
    return DispatchResult.continue_(redraw=True)


# --- Handlers: mutacao (VALUE, em %) --------------------------------------


def _h_mutation_rate(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    current = state.runtime_rules.mutation_rate
    new_value = max(
        cfg.MIN_MUTATION_RATE,
        min(cfg.MAX_MUTATION_RATE, current + direction),
    )
    state.update_runtime_rules(mutation_rate=new_value)
    return DispatchResult.continue_(redraw=True)


def _h_local_scale(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    current = state.runtime_rules.local_scale_fraction
    new_value = max(
        cfg.MIN_LOCAL_SCALE_FRACTION,
        min(cfg.MAX_LOCAL_SCALE_FRACTION, current + direction),
    )
    state.update_runtime_rules(local_scale_fraction=new_value)
    return DispatchResult.continue_(redraw=True)


def _h_local_scale_sigma(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.runtime_rules
    _adjust_runtime_float(
        "local_scale_sigma",
        direction,
        step=0.01,
        minimum=cfg.MIN_MUTATION_SIGMA,
        maximum=cfg.MAX_MUTATION_SIGMA,
        precision=2,
    )
    return DispatchResult.continue_(redraw=state.runtime_rules is not before)


def _h_global_probability(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.runtime_rules
    _adjust_runtime_int(
        "global_probability",
        direction,
        step=1,
        minimum=cfg.MIN_GLOBAL_PROBABILITY,
        maximum=cfg.MAX_GLOBAL_PROBABILITY,
    )
    return DispatchResult.continue_(redraw=state.runtime_rules is not before)


def _h_global_scale_fraction(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.runtime_rules
    _adjust_runtime_int(
        "global_scale_fraction",
        direction,
        step=1,
        minimum=cfg.MIN_GLOBAL_SCALE_FRACTION,
        maximum=cfg.MAX_GLOBAL_SCALE_FRACTION,
    )
    return DispatchResult.continue_(redraw=state.runtime_rules is not before)


def _h_global_scale_sigma(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.runtime_rules
    _adjust_runtime_float(
        "global_scale_sigma",
        direction,
        step=0.05,
        minimum=cfg.MIN_MUTATION_SIGMA,
        maximum=cfg.MAX_MUTATION_SIGMA,
        precision=2,
    )
    return DispatchResult.continue_(redraw=state.runtime_rules is not before)


def _h_stay_still_impulse(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    current = state.runtime_rules.stay_still_impulse
    candidate = round(current + direction * 0.1, 1)
    before = state.runtime_rules
    state.update_runtime_rules(stay_still_impulse=float(candidate))
    return DispatchResult.continue_(redraw=state.runtime_rules is not before)


# --- Handler: speed (ENUM) ------------------------------------------------


_SPEED_VALUES: tuple[float, ...] = (
    0.25,
    0.5,
    1.0,
    2.0,
    4.0,
    8.0,
    16.0,
    32.0,
    64.0,
    128.0,
    256.0,
)


def _h_speed(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    current = state.simulation_speed
    if current in _SPEED_VALUES:
        idx = _SPEED_VALUES.index(current)
    else:
        idx = 0
    idx = max(0, min(len(_SPEED_VALUES) - 1, idx + direction))
    state.simulation_speed = _SPEED_VALUES[idx]
    return DispatchResult.continue_(redraw=True)


# --- Helper: ajuste de inteiros runtime -----------------------------------


def _adjust_runtime_int(
    field: str,
    direction: int,
    *,
    step: int,
    minimum: int,
    maximum: int,
) -> None:
    """Ajusta um campo int de state.runtime_rules com clamp.

    Le o valor corrente, soma direction*step, aplica clamp em
    [minimum, maximum] e comita via state.update_runtime_rules. Se o
    valor clamped for igual ao corrente, update_runtime_rules e no-op
    de identidade (ver runtime_rules.updated_runtime_rules).

    Helper de UI: step e range pertencem a apresentacao; state nao
    deve conhecer esses detalhes.
    """
    current = getattr(state.runtime_rules, field)
    candidate = current + direction * step
    clamped = max(minimum, min(maximum, candidate))
    state.update_runtime_rules(**{field: clamped})


def _adjust_runtime_float(
    field: str,
    direction: int,
    *,
    step: float,
    minimum: float,
    maximum: float,
    precision: int = 1,
) -> None:
    """Ajusta um campo float runtime com round e clamp."""
    current = getattr(state.runtime_rules, field)
    candidate = round(current + direction * step, precision)
    clamped = max(minimum, min(maximum, candidate))
    clamped = round(float(clamped), precision)
    state.update_runtime_rules(**{field: clamped})


# --- Handlers: ecologia (VALUE, inteiros) --------------------------------


def _h_base_decay(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_int(
        "base_decay_per_tick",
        direction,
        step=1,
        minimum=cfg.MIN_BASE_DECAY_PER_TICK,
        maximum=cfg.MAX_BASE_DECAY_PER_TICK,
    )
    return DispatchResult.continue_(redraw=True)


def _h_low_hp_threshold(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.runtime_rules
    _adjust_runtime_int(
        "low_hp_threshold",
        direction,
        step=100,
        minimum=cfg.MIN_LOW_HP_THRESHOLD,
        maximum=cfg.MAX_LOW_HP_THRESHOLD,
    )
    return DispatchResult.continue_(redraw=state.runtime_rules is not before)


def _h_death_hp_threshold(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.runtime_rules
    _adjust_runtime_int(
        "death_hp_threshold",
        direction,
        step=100,
        minimum=cfg.MIN_DEATH_HP_THRESHOLD,
        maximum=cfg.MAX_DEATH_HP_THRESHOLD,
    )
    return DispatchResult.continue_(redraw=state.runtime_rules is not before)


def _h_predation_transfer(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.runtime_rules
    _adjust_runtime_int(
        "predation_transfer",
        direction,
        step=cfg.PREDATION_TRANSFER_STEP,
        minimum=cfg.MIN_PREDATION_TRANSFER,
        maximum=cfg.MAX_PREDATION_TRANSFER,
    )
    return DispatchResult.continue_(
        redraw=state.runtime_rules is not before
    )


def _h_overcrowding_factor(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.runtime_rules
    _adjust_runtime_int(
        "damage_per_own_overcrowding",
        direction,
        step=cfg.DAMAGE_PER_OWN_OVERCROWDING_STEP,
        minimum=cfg.MIN_DAMAGE_PER_OWN_OVERCROWDING,
        maximum=cfg.MAX_DAMAGE_PER_OWN_OVERCROWDING,
    )
    return DispatchResult.continue_(
        redraw=state.runtime_rules is not before
    )


# --- Handlers: reproducao (VALUE, inteiros) ------------------------------


def _h_reproduction_interval(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_int(
        "reproduction_interval",
        direction,
        step=10,
        minimum=cfg.MIN_REPRODUCTION_INTERVAL,
        maximum=cfg.MAX_REPRODUCTION_INTERVAL,
    )
    return DispatchResult.continue_(redraw=True)


def _h_reproduction_min_age(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_int(
        "reproduction_min_age",
        direction,
        step=100,
        minimum=cfg.MIN_REPRODUCTION_MIN_AGE,
        maximum=cfg.MAX_REPRODUCTION_MIN_AGE,
    )
    return DispatchResult.continue_(redraw=True)


def _h_reproduction_hp_gate(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_int(
        "reproduction_hp_gate",
        direction,
        step=100,
        minimum=cfg.MIN_REPRODUCTION_HP_GATE,
        maximum=cfg.MAX_REPRODUCTION_HP_GATE,
    )
    return DispatchResult.continue_(redraw=True)


def _h_reproduction_min_encounters(
    panel, item, direction: int
) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_int(
        "reproduction_min_encounters",
        direction,
        step=1,
        minimum=cfg.MIN_REPRODUCTION_MIN_ENCOUNTERS,
        maximum=cfg.MAX_REPRODUCTION_MIN_ENCOUNTERS,
    )
    return DispatchResult.continue_(redraw=True)


def _h_reproduction_parent_hp_bonus(
    panel, item, direction: int
) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_int(
        "reproduction_parent_hp_bonus",
        direction,
        step=10,
        minimum=cfg.MIN_REPRODUCTION_PARENT_HP_BONUS,
        maximum=cfg.MAX_REPRODUCTION_PARENT_HP_BONUS,
    )
    return DispatchResult.continue_(redraw=True)


# --- Handlers: zonas ------------------------------------------------------


def _h_zones_toggle(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    from . import controls
    return controls.action_toggle_zones()


def _h_zone_hp(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    current = state.runtime_rules.zone_hp_effect
    new_value = max(
        cfg.MIN_ZONE_HP_EFFECT,
        min(cfg.MAX_ZONE_HP_EFFECT, current + direction),
    )
    state.update_runtime_rules(zone_hp_effect=new_value)
    return DispatchResult.continue_(redraw=True)


# --- Handlers: intervencoes -----------------------------------------------


def _h_heal_all(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    from . import controls
    return controls.action_heal_all()


# --- Handlers: metrica (ENUM) ---------------------------------------------


# --- Handlers: Inspection (discovery) -------------------------------------


def _h_criterion(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.discovery_criterion
    order = cfg.CRITERIA_ORDER
    try:
        i = order.index(state.discovery_criterion)
    except ValueError:
        i = 0
    state.discovery_criterion = order[(i + direction) % len(order)]
    if state.discovery_criterion != before:
        prefs.mark_dirty()
    # Discovery mudou: nao toca observacao nem trail.
    return DispatchResult.continue_(redraw=True)


def _h_lineage_filter(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.discovery_lineage_filter
    order = cfg.LINEAGE_FILTER_ORDER
    try:
        i = order.index(state.discovery_lineage_filter)
    except ValueError:
        i = 0
    state.discovery_lineage_filter = order[(i + direction) % len(order)]
    if state.discovery_lineage_filter != before:
        prefs.mark_dirty()
    return DispatchResult.continue_(redraw=True)


def _observe_discovery_candidate() -> DispatchResult:
    """Observa o candidato atual de Discovery.

    Fonte unica da operacao. Sem candidato (populacao vazia, linhagem
    filtrada extinta, criterio desconhecido): preserva a observacao
    existente e emite notice informativa. NAO limpa trail, NAO troca
    selection.

    O log de console continua sendo emitido nos dois caminhos
    (sucesso e sem candidato) para manter a trilha tecnica que ja
    existia antes.

    Retorna sempre redraw=True: no sucesso, os marcadores e o painel
    mudam; no no-op, a notice precisa aparecer.
    """
    from . import ui_state
    candidate = world.discovery_candidate(
        state.discovery_criterion,
        state.discovery_lineage_filter,
    )
    if candidate is None:
        criterion_label = i18n.t(f"criterion.{state.discovery_criterion}")
        lineage_label = i18n.t(
            f"lineage_filter.{state.discovery_lineage_filter}"
        )
        print(
            i18n.t(
                "log.inspection_no_match",
                criterion=criterion_label,
                lineage=lineage_label,
            )
        )
        ui_state.show_notice(
            i18n.t("notice.no_candidate"),
            kind=ui_state.NOTICE_INFO,
        )
        return DispatchResult.continue_(redraw=True)

    li, ai = candidate
    new_id = int(state.agents[li]["ids"][ai])
    state.set_inspection_selection(new_id)
    print(
        i18n.t(
            "log.inspection_observe",
            desc=f"linhagem={state.agents[li]['id']} id={new_id}",
        )
    )
    return DispatchResult.continue_(redraw=True)


def _h_clear_observation(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    state.set_inspection_selection(None)
    return DispatchResult.continue_(redraw=True)


# --- Handlers: selecao ----------------------------------------------------


def _h_reproduction_criterion(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)

    order = cfg.REPRODUCTION_CRITERIA
    current = state.runtime_rules.reproduction_criterion
    index = order.index(current)
    candidate = order[(index + direction) % len(order)]
    state.update_runtime_rules(reproduction_criterion=candidate)
    return DispatchResult.continue_(redraw=True)


def _h_reproduction_pool_fraction(
    panel, item, direction: int
) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_float(
        "reproduction_pool_fraction",
        direction,
        step=0.01,
        minimum=cfg.MIN_REPRODUCTION_POOL_FRACTION,
        maximum=cfg.MAX_REPRODUCTION_POOL_FRACTION,
        precision=2,
    )
    return DispatchResult.continue_(redraw=True)


def _h_reproduction_attempts_divisor(
    panel, item, direction: int
) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_int(
        "reproduction_attempts_divisor",
        direction,
        step=1,
        minimum=cfg.MIN_REPRODUCTION_ATTEMPTS_DIVISOR,
        maximum=cfg.MAX_REPRODUCTION_ATTEMPTS_DIVISOR,
    )
    return DispatchResult.continue_(redraw=True)


# --- Handlers: score de selecao (VALUE, floats) ---------------------------


def _h_reproduction_min_score(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_float(
        "reproduction_min_score",
        direction,
        step=0.1,
        minimum=cfg.MIN_REPRODUCTION_MIN_SCORE,
        maximum=cfg.MAX_REPRODUCTION_MIN_SCORE,
    )
    return DispatchResult.continue_(redraw=True)


def _h_longevity_weight(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_float(
        "longevity_weight", direction, step=0.1,
        minimum=cfg.MIN_SELECTION_WEIGHT, maximum=cfg.MAX_SELECTION_WEIGHT,
    )
    return DispatchResult.continue_(redraw=True)


def _h_exploration_weight(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_float(
        "exploration_weight", direction, step=0.1,
        minimum=cfg.MIN_SELECTION_WEIGHT, maximum=cfg.MAX_SELECTION_WEIGHT,
    )
    return DispatchResult.continue_(redraw=True)


def _h_interaction_weight(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_float(
        "interaction_weight", direction, step=0.1,
        minimum=cfg.MIN_SELECTION_WEIGHT, maximum=cfg.MAX_SELECTION_WEIGHT,
    )
    return DispatchResult.continue_(redraw=True)


def _h_reproduction_weight(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    _adjust_runtime_float(
        "reproduction_weight", direction, step=0.1,
        minimum=cfg.MIN_SELECTION_WEIGHT, maximum=cfg.MAX_SELECTION_WEIGHT,
    )
    return DispatchResult.continue_(redraw=True)


# --- Handlers: Session ----------------------------------------------------


def _h_save_slot(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    from . import controls
    # Seta direita delega para a action, que e a autoridade do
    # mark_dirty() nesse caminho. Seta esquerda muta direto aqui e
    # marca localmente: um unico ponto de autoridade por mutacao.
    if direction > 0:
        return controls.action_cycle_save_slot()
    before = state.active_save_slot
    slots = cfg.SAVE_SLOTS
    try:
        i = slots.index(state.active_save_slot)
    except ValueError:
        i = 0
    state.active_save_slot = slots[(i - 1) % len(slots)]
    if state.active_save_slot != before:
        prefs.mark_dirty()
    print(i18n.t("log.save_slot", slot=state.active_save_slot))
    return DispatchResult.continue_(redraw=True)


def _h_save_now(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    from . import controls
    return controls.action_save()


def _h_load_now(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    from . import controls
    return controls.action_load()


def _h_new_world(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    # Fase 9 substitui por modal de confirmacao.
    from . import controls
    return controls.action_recreate()


# --- Handlers: Tools ------------------------------------------------------


def _h_language(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    before = state.language
    if direction > 0:
        i18n.cycle_language()
    else:
        # Ciclo reverso.
        langs = i18n.AVAILABLE_LANGUAGES
        try:
            i = langs.index(state.language)
        except ValueError:
            i = 0
        state.language = langs[(i - 1) % len(langs)]
    if state.language != before:
        prefs.mark_dirty()
    return DispatchResult.continue_(redraw=True)


def _h_recording(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    from . import controls
    return controls.action_toggle_recording()


def _h_print_state(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    from . import controls
    return controls.action_print_state()


# --- Construcao dos paineis -----------------------------------------------


def _inspection_enter_handler(
    panel: Panel, item: Item | None, direction: int
) -> DispatchResult:
    """Enter contextual do painel Inspection.

    Contrato:
      - Cursor em clear_observation -> limpa observacao.
      - Qualquer outro cursor (criterion, lineage_filter) ou None
        -> observa o candidato atual de Discovery.

    Reutiliza a assinatura de Handler: o parametro `direction` e
    sempre 0 (Enter). O item e apenas o cursor atual; o handler NAO
    ativa o item no sentido generico, ele redefine o significado de
    Enter no painel.
    """
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    if item is not None and item.id == "clear_observation":
        return _h_clear_observation(panel, item, 0)
    return _observe_discovery_candidate()


def _build_inspection() -> Panel:
    return Panel(
        id=ui_state.PANEL_INSPECTION,
        activation_key=pygame.K_i,
        title_key="panel.inspection.title",
        footer_key="footer.inspection",
        items=[
            Item("section_discovery", ItemKind.SECTION, "panel.discovery_title"),
            Item("criterion", ItemKind.ENUM, "item.criterion",
                 value_fn=_v_criterion, handler=_h_criterion),
            Item("lineage_filter", ItemKind.ENUM, "item.lineage_filter",
                 value_fn=_v_lineage_filter, handler=_h_lineage_filter),
            Item("section_observation", ItemKind.SECTION, "panel.observation_title"),
            Item("clear_observation", ItemKind.ACTION, "item.clear_observation",
                 handler=_h_clear_observation),
        ],
        enter_handler=_inspection_enter_handler,
    )


def _build_configuration() -> Panel:
    return Panel(
        id=ui_state.PANEL_CONFIGURATION,
        activation_key=pygame.K_c,
        title_key="panel.configuration.title",
        footer_key="footer.configuration",
        items=[
            Item("speed", ItemKind.ENUM, "item.speed",
                 value_fn=_v_speed, handler=_h_speed),
            Item("section_genetics", ItemKind.SECTION,
                 "panel.configuration.genetics"),
            Item("crossover_mode", ItemKind.ENUM, "item.crossover_mode",
                 value_fn=_v_crossover_mode, handler=_h_crossover_mode),
            Item("crossover_probability", ItemKind.VALUE,
                 "item.crossover_probability",
                 value_fn=_v_crossover_probability,
                 handler=_h_crossover_probability),
            Item("block_size", ItemKind.VALUE, "item.block_size",
                 value_fn=_v_block_size, handler=_h_block_size),
            Item("mutation_mode", ItemKind.ENUM, "item.mutation_mode",
                 value_fn=_v_mutation_mode, handler=_h_mutation_mode),
            Item("mutation_rate", ItemKind.VALUE, "item.mutation_rate",
                 value_fn=_v_mutation_rate, handler=_h_mutation_rate),
            Item("local_scale", ItemKind.VALUE, "item.local_scale",
                 value_fn=_v_local_scale, handler=_h_local_scale),
            Item("local_scale_sigma", ItemKind.VALUE,
                 "item.local_scale_sigma",
                 value_fn=_v_local_scale_sigma, handler=_h_local_scale_sigma),
            Item("global_probability", ItemKind.VALUE,
                 "item.global_probability",
                 value_fn=_v_global_probability, handler=_h_global_probability),
            Item("global_scale_fraction", ItemKind.VALUE,
                 "item.global_scale_fraction",
                 value_fn=_v_global_scale_fraction,
                 handler=_h_global_scale_fraction),
            Item("global_scale_sigma", ItemKind.VALUE,
                 "item.global_scale_sigma",
                 value_fn=_v_global_scale_sigma, handler=_h_global_scale_sigma),
            Item("stay_still_impulse", ItemKind.VALUE,
                 "item.stay_still_impulse",
                 value_fn=_v_stay_still_impulse, handler=_h_stay_still_impulse),
            Item("section_ecology", ItemKind.SECTION,
                 "panel.configuration.ecology"),
            Item("base_decay", ItemKind.VALUE, "item.base_decay",
                 value_fn=_v_base_decay, handler=_h_base_decay),
            Item("low_hp_threshold", ItemKind.VALUE,
                 "item.low_hp_threshold",
                 value_fn=_v_low_hp_threshold, handler=_h_low_hp_threshold),
            Item("death_hp_threshold", ItemKind.VALUE,
                 "item.death_hp_threshold",
                 value_fn=_v_death_hp_threshold, handler=_h_death_hp_threshold),
            Item("predation_transfer", ItemKind.VALUE,
                 "item.predation_transfer",
                 value_fn=_v_predation_transfer,
                 handler=_h_predation_transfer),
            Item("overcrowding_factor", ItemKind.VALUE,
                 "item.overcrowding_factor",
                 value_fn=_v_overcrowding_factor,
                 handler=_h_overcrowding_factor),
            Item("zones", ItemKind.TOGGLE, "item.zones",
                 value_fn=_v_zones, handler=_h_zones_toggle),
            Item("zone_hp", ItemKind.VALUE, "item.zone_hp_effect",
                 value_fn=_v_zone_hp, handler=_h_zone_hp),
            Item("section_reproduction", ItemKind.SECTION,
                 "panel.configuration.reproduction"),
            Item("reproduction_interval", ItemKind.VALUE,
                 "item.reproduction_interval",
                 value_fn=_v_reproduction_interval,
                 handler=_h_reproduction_interval),
            Item("reproduction_min_age", ItemKind.VALUE,
                 "item.reproduction_min_age",
                 value_fn=_v_reproduction_min_age,
                 handler=_h_reproduction_min_age),
            Item("reproduction_hp_gate", ItemKind.VALUE,
                 "item.reproduction_hp_gate",
                 value_fn=_v_reproduction_hp_gate,
                 handler=_h_reproduction_hp_gate),
            Item("reproduction_min_encounters", ItemKind.VALUE,
                 "item.reproduction_min_encounters",
                 value_fn=_v_reproduction_min_encounters,
                 handler=_h_reproduction_min_encounters),
            Item("reproduction_parent_hp_bonus", ItemKind.VALUE,
                 "item.reproduction_parent_hp_bonus",
                 value_fn=_v_reproduction_parent_hp_bonus,
                 handler=_h_reproduction_parent_hp_bonus),
            Item("section_selection", ItemKind.SECTION,
                 "panel.configuration.selection"),
            Item("reproduction_criterion", ItemKind.ENUM,
                 "item.reproduction_criterion",
                 value_fn=_v_reproduction_criterion,
                 handler=_h_reproduction_criterion),
            Item("reproduction_pool_fraction", ItemKind.VALUE,
                 "item.reproduction_pool_fraction",
                 value_fn=_v_reproduction_pool_fraction,
                 handler=_h_reproduction_pool_fraction),
            Item("reproduction_attempts_divisor", ItemKind.VALUE,
                 "item.reproduction_attempts_divisor",
                 value_fn=_v_reproduction_attempts_divisor,
                 handler=_h_reproduction_attempts_divisor),
            Item("reproduction_min_score", ItemKind.VALUE,
                 "item.reproduction_min_score",
                 value_fn=_v_reproduction_min_score,
                 handler=_h_reproduction_min_score),
            Item("longevity_weight", ItemKind.VALUE,
                 "item.longevity_weight",
                 value_fn=_v_longevity_weight,
                 handler=_h_longevity_weight),
            Item("exploration_weight", ItemKind.VALUE,
                 "item.exploration_weight",
                 value_fn=_v_exploration_weight,
                 handler=_h_exploration_weight),
            Item("interaction_weight", ItemKind.VALUE,
                 "item.interaction_weight",
                 value_fn=_v_interaction_weight,
                 handler=_h_interaction_weight),
            Item("reproduction_weight", ItemKind.VALUE,
                 "item.reproduction_weight",
                 value_fn=_v_reproduction_weight,
                 handler=_h_reproduction_weight),
            Item("heal_all", ItemKind.ACTION, "item.heal_all",
                 handler=_h_heal_all),
        ],
    )


def _build_metrics() -> Panel:
    """Painel Metrics sem itens interativos.

    O dashboard de seis small multiples e desenhado pelo renderer
    quando o painel esta focado (ver rendering._draw_panel_viewport).
    Nao ha selecao: todas as metricas visiveis simultaneamente.

    default_cursor_id() retorna None (items vazio). Tab / Shift+Tab /
    Esc continuam funcionando porque pertencem ao dispatcher, nao
    aos itens.
    """
    return Panel(
        id=ui_state.PANEL_METRICS,
        activation_key=pygame.K_m,
        title_key="panel.metrics.title",
        footer_key="footer.metrics",
        items=[],
    )


def _build_session() -> Panel:
    return Panel(
        id=ui_state.PANEL_SESSION,
        activation_key=pygame.K_s,
        title_key="panel.session.title",
        footer_key="footer.session",
        items=[
            Item("save_slot", ItemKind.ENUM, "item.save_slot",
                 value_fn=_v_save_slot, handler=_h_save_slot),
            Item("save", ItemKind.ACTION, "item.save",
                 handler=_h_save_now),
            Item("load", ItemKind.ACTION, "item.load",
                 handler=_h_load_now),
            Item("new_world", ItemKind.ACTION, "item.new_world",
                 handler=_h_new_world),
        ],
    )


def _build_tools() -> Panel:
    return Panel(
        id=ui_state.PANEL_TOOLS,
        activation_key=pygame.K_t,
        title_key="panel.tools.title",
        footer_key="footer.tools",
        items=[
            Item("language", ItemKind.ENUM, "item.language",
                 value_fn=_v_language, handler=_h_language),
            Item("recording", ItemKind.TOGGLE, "item.recording",
                 value_fn=_v_recording, handler=_h_recording),
            Item("print_state", ItemKind.ACTION, "item.print_state",
                 handler=_h_print_state),
        ],
    )


def register_default_panels() -> None:
    """Registra os cinco paineis no registry global.

    Chamado pelo bootstrap grafico. Idempotente: registrar o mesmo id
    duas vezes sobrescreve, o que e aceitavel para o bootstrap.
    """
    register(_build_inspection())
    register(_build_configuration())
    register(_build_metrics())
    register(_build_session())
    register(_build_tools())