# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Contratos de integracao do zoom com o bootstrap grafico.

Captura os adapters reais registrados dentro de simulation.run() e
exercita a politica efetiva: Ctrl+wheel no mundo faz zoom, wheel puro
no mundo e no-op, e a sidebar tem precedencia mesmo com Ctrl
pressionado.

Nao abre janela, nao executa o loop grafico. Neutraliza bootstrap,
prefs, rendering e o proprio loop via monkeypatch.

Todos os docstrings deste arquivo sao intencionalmente ASCII puro.
"""

import pygame
import pytest

from primordial_soup import input_dispatcher
from primordial_soup import layout
from primordial_soup import panels_defs
from primordial_soup import prefs
from primordial_soup import rendering
from primordial_soup import simulation
from primordial_soup import state
from primordial_soup import ui_state
from primordial_soup.panels import DispatchResult


def _capture_zoom_bindings(monkeypatch):
    """Executa simulation.run() neutralizado e captura os bindings.

    O objetivo e exercitar exatamente a politica implementada em
    simulation.run() sem abrir janela nem entrar em loop. Os
    monkeypatches seguem o padrao de
    test_paused_redraw_is_honored_by_graphical_loop.
    """
    captured = {
        "wheel": None,
        "global_actions": [],
    }

    monkeypatch.setattr(
        simulation,
        "bootstrap_new_world",
        lambda: None,
    )
    monkeypatch.setattr(
        panels_defs,
        "register_default_panels",
        lambda: None,
    )
    monkeypatch.setattr(prefs, "load", lambda: None)
    monkeypatch.setattr(
        prefs,
        "save_if_dirty",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(rendering, "init", lambda: None)
    monkeypatch.setattr(rendering, "draw", lambda: None)
    monkeypatch.setattr(rendering, "shutdown", lambda: None)
    monkeypatch.setattr(rendering, "tick_fps", lambda: None)

    monkeypatch.setattr(
        input_dispatcher,
        "process_events",
        lambda: DispatchResult.exit_(),
    )

    monkeypatch.setattr(
        input_dispatcher,
        "register_step_handler",
        lambda fn: None,
    )
    monkeypatch.setattr(
        input_dispatcher,
        "register_space_handler",
        lambda fn: None,
    )
    monkeypatch.setattr(
        input_dispatcher,
        "register_fullscreen_handler",
        lambda fn: None,
    )
    monkeypatch.setattr(
        input_dispatcher,
        "register_mouse_handler",
        lambda fn: None,
    )
    monkeypatch.setattr(
        input_dispatcher,
        "register_resize_handler",
        lambda fn: None,
    )
    monkeypatch.setattr(
        input_dispatcher,
        "register_tab_hit_test_handler",
        lambda fn: None,
    )

    def capture_wheel(fn):
        captured["wheel"] = fn

    monkeypatch.setattr(
        input_dispatcher,
        "register_wheel_handler",
        capture_wheel,
    )

    def capture_global_action(key, handler, modifiers=0):
        captured["global_actions"].append(
            (key, modifiers, handler)
        )

    monkeypatch.setattr(
        input_dispatcher,
        "register_global_action",
        capture_global_action,
    )

    simulation.run()

    assert captured["wheel"] is not None, (
        "simulation.run() nao registrou wheel handler."
    )
    return captured


def _install_fake_screen(monkeypatch):
    """Surface em memoria + display.get_surface falsos."""
    fake_screen = pygame.Surface(
        (
            layout.LAYOUT.window_width,
            layout.LAYOUT.window_height,
        )
    )
    monkeypatch.setattr(
        pygame.display,
        "get_surface",
        lambda: fake_screen,
    )
    monkeypatch.setattr(rendering, "_screen", fake_screen)
    rendering.reset_camera()
    rendering.on_resize(*fake_screen.get_size())
    return fake_screen


# ---------------------------------------------------------------------------
# Ctrl+wheel no mundo faz zoom
# ---------------------------------------------------------------------------


def test_ctrl_wheel_over_world_zooms(monkeypatch):
    """Ctrl+wheel sobre o viewport do mundo aplica zoom."""
    captured = _capture_zoom_bindings(monkeypatch)
    _install_fake_screen(monkeypatch)

    wheel = captured["wheel"]
    pos = rendering._world_viewport_rect().center

    before_zoom = rendering._camera.zoom

    result = wheel(+1, pos, pygame.KMOD_CTRL)

    assert rendering._camera.zoom > before_zoom
    assert result.redraw is True

    # A sidebar nao muda nesse caminho.
    assert (
        ui_state.panel_scroll_offsets.get(
            ui_state.PANEL_INSPECTION, 0
        )
        == 0
    )


def test_plain_wheel_over_world_is_noop(monkeypatch):
    """Sem Ctrl, o wheel sobre o mundo nao altera camera nem scroll."""
    captured = _capture_zoom_bindings(monkeypatch)
    _install_fake_screen(monkeypatch)

    wheel = captured["wheel"]
    pos = rendering._world_viewport_rect().center

    before = (
        rendering._camera.zoom,
        rendering._camera.view_x,
        rendering._camera.view_y,
    )

    result = wheel(+1, pos, 0)

    assert result.redraw is False
    assert (
        rendering._camera.zoom,
        rendering._camera.view_x,
        rendering._camera.view_y,
    ) == before


def test_sidebar_wheel_has_priority_over_ctrl_zoom(monkeypatch):
    """Sidebar rola o painel mesmo com Ctrl pressionado.

    A prioridade e absoluta: a sidebar e uma regiao fisica de UI e o
    zoom nao invade esse dominio. Ctrl+wheel sobre a sidebar continua
    rolando.
    """
    captured = _capture_zoom_bindings(monkeypatch)
    fake_screen = _install_fake_screen(monkeypatch)

    ui_state.last_panel = ui_state.PANEL_INSPECTION
    ui_state.active_panel = ui_state.PANEL_WORLD
    ui_state.panel_scroll_offsets[ui_state.PANEL_INSPECTION] = 100

    wheel = captured["wheel"]
    pos = (fake_screen.get_width() - 1, 100)

    result = wheel(+1, pos, pygame.KMOD_CTRL)

    assert (
        ui_state.panel_scroll_offsets[ui_state.PANEL_INSPECTION] == 70
    )
    assert rendering._camera.zoom == pytest.approx(1.0)
    assert result.redraw is True


# ---------------------------------------------------------------------------
# Ctrl+0 registrado
# ---------------------------------------------------------------------------


def test_ctrl_zero_is_registered_as_camera_reset(monkeypatch):
    """Ctrl+0 esta registrado como accelerator e reseta a camera.

    Verifica tanto o registro (uma unica entry para (K_0, Ctrl))
    quanto a semantica: primeira invocacao reporta mudanca (True),
    segunda nao (False).
    """
    captured = _capture_zoom_bindings(monkeypatch)
    _install_fake_screen(monkeypatch)

    matches = [
        handler
        for key, modifiers, handler
        in captured["global_actions"]
        if key == pygame.K_0 and modifiers == pygame.KMOD_CTRL
    ]
    assert len(matches) == 1, (
        f"esperado exatamente 1 accelerator Ctrl+0, "
        f"encontrado {len(matches)}"
    )

    rendering.apply_zoom_at(
        rendering._world_viewport_rect().center,
        +1,
    )
    assert rendering._camera.zoom > 1.0

    result = matches[0]()
    assert rendering._camera.zoom == pytest.approx(1.0)
    assert rendering._camera.view_x == pytest.approx(0.0)
    assert rendering._camera.view_y == pytest.approx(0.0)
    assert result.redraw is True

    result = matches[0]()
    assert result.redraw is False
