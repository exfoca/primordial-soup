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


def _v_mutation_rate() -> str:
    return f"{state.mutation_rate}%"


def _v_local_scale() -> str:
    return f"{state.local_scale_fraction}%"


def _v_speed() -> str:
    return f"{state.ticks_per_frame}x"


def _v_zones() -> str:
    return i18n.t("hud.on" if state.zones_active else "hud.off")


def _v_zone_hp() -> str:
    sign = "+" if state.zone_hp_effect >= 0 else ""
    return f"{sign}{state.zone_hp_effect}"


def _v_save_slot() -> str:
    return state.active_save_slot


def _v_language() -> str:
    return state.language.upper()


def _v_recording() -> str:
    return i18n.t("hud.on" if state.recording else "hud.off")


def _v_metric() -> str:
    return i18n.t(f"metric.{state.selected_metric}")


def _v_criterion() -> str:
    return i18n.t(f"criterion.{state.discovery_criterion}")


def _v_discovery_candidate() -> str:
    candidate = world.discovery_candidate(
        state.discovery_criterion,
        state.discovery_lineage_filter,
    )
    if candidate is None:
        return i18n.t("panel.no_candidate")
    li, ai = candidate
    stable_id = int(state.agents[li]["ids"][ai])
    lineage_id = state.agents[li]["id"]
    return f"#{stable_id} {lineage_id}"


def _v_lineage_filter() -> str:
    return i18n.t(f"lineage_filter.{state.discovery_lineage_filter}")


# --- Handlers: mutacao (VALUE, em %) --------------------------------------


def _h_mutation_rate(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    state.mutation_rate = max(
        cfg.MIN_MUTATION_RATE,
        min(cfg.MAX_MUTATION_RATE, state.mutation_rate + direction),
    )
    return DispatchResult.continue_(redraw=True)


def _h_local_scale(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    state.local_scale_fraction = max(
        cfg.MIN_LOCAL_SCALE_FRACTION,
        min(cfg.MAX_LOCAL_SCALE_FRACTION,
            state.local_scale_fraction + direction),
    )
    return DispatchResult.continue_(redraw=True)


# --- Handler: speed (ENUM) ------------------------------------------------


_SPEED_VALUES = (1, 2, 4, 8, 16, 32, 64, 128, 256)


def _h_speed(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    current = state.ticks_per_frame
    if current in _SPEED_VALUES:
        idx = _SPEED_VALUES.index(current)
    else:
        idx = 0
    idx = max(0, min(len(_SPEED_VALUES) - 1, idx + direction))
    state.ticks_per_frame = _SPEED_VALUES[idx]
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
    state.zone_hp_effect = max(
        cfg.MIN_ZONE_HP_EFFECT,
        min(cfg.MAX_ZONE_HP_EFFECT, state.zone_hp_effect + direction),
    )
    return DispatchResult.continue_(redraw=True)


# --- Handlers: intervencoes -----------------------------------------------


def _h_heal_all(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    from . import controls
    return controls.action_heal_all()


# --- Handlers: metrica (ENUM) ---------------------------------------------


def _h_metric(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    # cycle_metric ja cicla +1; para -1, ciclamos ate len-1.
    if direction > 0:
        state.cycle_metric()
    else:
        n = len(cfg.ADVANCED_METRICS)
        state.selected_metric_index = (
            state.selected_metric_index - 1
        ) % n
        state.selected_metric = cfg.ADVANCED_METRICS[state.selected_metric_index]
    return DispatchResult.continue_(redraw=True)


# --- Handlers: Inspection (discovery) -------------------------------------


def _h_criterion(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    order = cfg.CRITERIA_ORDER
    try:
        i = order.index(state.discovery_criterion)
    except ValueError:
        i = 0
    state.discovery_criterion = order[(i + direction) % len(order)]
    # Discovery mudou: nao toca observacao nem trail.
    return DispatchResult.continue_(redraw=True)


def _h_lineage_filter(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    order = cfg.LINEAGE_FILTER_ORDER
    try:
        i = order.index(state.discovery_lineage_filter)
    except ValueError:
        i = 0
    state.discovery_lineage_filter = order[(i + direction) % len(order)]
    return DispatchResult.continue_(redraw=True)


def _h_observe_candidate(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    candidate = world.discovery_candidate(
        state.discovery_criterion,
        state.discovery_lineage_filter,
    )
    if candidate is None:
        print(i18n.t("log.inspection_no_match",
                     criterion=i18n.t(f"criterion.{state.discovery_criterion}"),
                     lineage=i18n.t(f"lineage_filter.{state.discovery_lineage_filter}")))
        return DispatchResult.continue_(redraw=False)
    li, ai = candidate
    new_id = int(state.agents[li]["ids"][ai])
    state.set_inspection_selection(new_id)
    print(i18n.t("log.inspection_observe",
                 desc=f"linhagem={state.agents[li]['id']} id={new_id}"))
    return DispatchResult.continue_(redraw=True)


def _h_clear_observation(panel, item, direction: int) -> DispatchResult:
    if direction != 0:
        return DispatchResult.continue_(redraw=False)
    state.set_inspection_selection(None)
    return DispatchResult.continue_(redraw=True)


# --- Handlers: Session ----------------------------------------------------


def _h_save_slot(panel, item, direction: int) -> DispatchResult:
    if direction == 0:
        return DispatchResult.continue_(redraw=False)
    from . import controls
    if direction > 0:
        return controls.action_cycle_save_slot()
    slots = cfg.SAVE_SLOTS
    try:
        i = slots.index(state.active_save_slot)
    except ValueError:
        i = 0
    state.active_save_slot = slots[(i - 1) % len(slots)]
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
            Item("candidate", ItemKind.READ_ONLY, "item.discovery_candidate",
                 value_fn=_v_discovery_candidate),
            Item("observe_candidate", ItemKind.ACTION, "item.observe_candidate",
                 handler=_h_observe_candidate),
            Item("section_observation", ItemKind.SECTION, "panel.observation_title"),
            Item("clear_observation", ItemKind.ACTION, "item.clear_observation",
                 handler=_h_clear_observation),
        ],
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
            Item("mutation_rate", ItemKind.VALUE, "item.mutation_rate",
                 value_fn=_v_mutation_rate, handler=_h_mutation_rate),
            Item("local_scale", ItemKind.VALUE, "item.local_scale",
                 value_fn=_v_local_scale, handler=_h_local_scale),
            Item("zones", ItemKind.TOGGLE, "item.zones",
                 value_fn=_v_zones, handler=_h_zones_toggle),
            Item("zone_hp", ItemKind.VALUE, "item.zone_hp_effect",
                 value_fn=_v_zone_hp, handler=_h_zone_hp),
            Item("heal_all", ItemKind.ACTION, "item.heal_all",
                 handler=_h_heal_all),
        ],
    )


def _build_metrics() -> Panel:
    return Panel(
        id=ui_state.PANEL_METRICS,
        activation_key=pygame.K_m,
        title_key="panel.metrics.title",
        footer_key="footer.metrics",
        items=[
            Item("metric", ItemKind.ENUM, "item.metric",
                 value_fn=_v_metric, handler=_h_metric),
        ],
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
