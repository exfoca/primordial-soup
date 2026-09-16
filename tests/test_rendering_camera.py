# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Contratos de camera e zoom do rendering.

Cobre a matematica do `_Camera`, a separacao entre viewport fisico
(screen-space) e view logica (world-space), o pipeline de
crop-before-scale, os limites de zoom e a delegacao de
screen_to_world().

Nao abre janela real, nao executa o loop grafico, nao depende de
simulation.run(). Toda interacao acontece sobre uma Surface em
memoria.

O objetivo e tornar auditavel o contrato implementado no commit
4e3343f sem refatorar a producao.

Todos os docstrings deste arquivo sao intencionalmente ASCII puro.
"""

import numpy as np
import pygame
import pytest

from primordial_soup import config as cfg
from primordial_soup import layout
from primordial_soup import rendering
from primordial_soup import state
from primordial_soup import ui_state


# ---------------------------------------------------------------------------
# Fixture: Surface em memoria, sem display real
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _camera_environment(monkeypatch):
    """Instala uma Surface falsa e a camera canonica em cada teste."""
    fake_screen = pygame.Surface(
        (
            layout.LAYOUT.window_width,
            layout.LAYOUT.window_height,
        )
    )
    monkeypatch.setattr(rendering, "_screen", fake_screen)

    rendering.reset_camera()
    rendering.on_resize(*fake_screen.get_size())

    yield

    rendering.reset_camera()
    rendering.on_resize(
        layout.LAYOUT.window_width,
        layout.LAYOUT.window_height,
    )


def _viewport_center() -> tuple[int, int]:
    """Centro do viewport fisico atual (screen-space)."""
    viewport = rendering._world_viewport_rect()
    return (
        viewport.left + viewport.width // 2,
        viewport.top + viewport.height // 2,
    )


# ---------------------------------------------------------------------------
# Geometria do viewport
# ---------------------------------------------------------------------------


def test_default_viewport_matches_pre_zoom_geometry():
    """Em 1x o viewport fisico coincide com o tamanho do mundo
    escalado, ancorado em (0, 0)."""
    viewport = rendering._world_viewport_rect()

    assert viewport.left == 0
    assert viewport.top == 0

    assert viewport.width == (
        layout.LAYOUT.world_width * layout.LAYOUT.pixel_scale
    )
    assert viewport.height == (
        layout.LAYOUT.world_height * layout.LAYOUT.pixel_scale
    )


def test_world_viewport_rect_returns_copy():
    """_world_viewport_rect() retorna copia, nao referencia viva.

    A copia impede que chamadores externos mutem `_viewport_rect` por
    acidente. Se um deles alterar a copia, a proxima chamada deve
    refletir o estado interno inalterado.
    """
    first = rendering._world_viewport_rect()
    original = first.copy()

    first.x += 100
    first.y += 100

    second = rendering._world_viewport_rect()
    assert second == original


# ---------------------------------------------------------------------------
# Camera canonica
# ---------------------------------------------------------------------------


def test_camera_canonical_state_is_fit_world():
    """Apos reset, a camera observa o mundo inteiro em 1x."""
    assert rendering._camera.zoom == pytest.approx(1.0)
    assert rendering._camera.view_x == pytest.approx(0.0)
    assert rendering._camera.view_y == pytest.approx(0.0)

    view_w, view_h = rendering._camera_view_size()
    assert view_w == pytest.approx(layout.LAYOUT.world_width)
    assert view_h == pytest.approx(layout.LAYOUT.world_height)


# ---------------------------------------------------------------------------
# Zoom ancorado
# ---------------------------------------------------------------------------


def test_zoom_preserves_world_point_under_cursor():
    """O ponto logico sob o cursor permanece o mesmo depois do zoom.

    Usa _screen_to_world_float() (transformacao continua), nao
    screen_to_world() (que quantiza para celula inteira). A ancoragem
    e uma propriedade da camera float.
    """
    pos = _viewport_center()

    before = rendering._screen_to_world_float(pos)
    assert before is not None

    changed = rendering.apply_zoom_at(pos, +1)
    assert changed is True

    after = rendering._screen_to_world_float(pos)
    assert after is not None

    assert after[0] == pytest.approx(before[0], abs=1e-9)
    assert after[1] == pytest.approx(before[1], abs=1e-9)


def test_zero_notches_are_noop():
    """notches=0 nao altera a camera nem reporta mudanca."""
    before = (
        rendering._camera.zoom,
        rendering._camera.view_x,
        rendering._camera.view_y,
    )

    changed = rendering.apply_zoom_at(_viewport_center(), 0)

    assert changed is False
    assert (
        rendering._camera.zoom,
        rendering._camera.view_x,
        rendering._camera.view_y,
    ) == before


def test_zoom_clamps_at_maximum():
    """Zoom satura em MAX_ZOOM e nao excede."""
    pos = _viewport_center()

    for _ in range(100):
        rendering.apply_zoom_at(pos, +1)

    assert rendering._camera.zoom == pytest.approx(cfg.MAX_ZOOM)

    changed = rendering.apply_zoom_at(pos, +1)
    assert changed is False


def test_zoom_clamps_at_minimum():
    """Zoom satura em MIN_ZOOM; em 1x a view volta a origem."""
    rendering.apply_zoom_at(_viewport_center(), +3)

    for _ in range(100):
        rendering.apply_zoom_at(_viewport_center(), -1)

    assert rendering._camera.zoom == pytest.approx(cfg.MIN_ZOOM)
    assert rendering._camera.view_x == pytest.approx(0.0)
    assert rendering._camera.view_y == pytest.approx(0.0)

    changed = rendering.apply_zoom_at(_viewport_center(), -1)
    assert changed is False


def test_zoom_outside_world_viewport_is_noop():
    """Posicao na sidebar nao afeta a camera.

    O viewport fisico do mundo nao inclui a sidebar; o hit-test de
    _screen_to_world_float retorna None nessa regiao e apply_zoom_at
    permanece no-op.
    """
    screen = rendering._screen
    pos = (screen.get_width() - 1, 10)

    before = (
        rendering._camera.zoom,
        rendering._camera.view_x,
        rendering._camera.view_y,
    )

    changed = rendering.apply_zoom_at(pos, +1)

    assert changed is False
    assert (
        rendering._camera.zoom,
        rendering._camera.view_x,
        rendering._camera.view_y,
    ) == before


# ---------------------------------------------------------------------------
# Invariantes da camera
# ---------------------------------------------------------------------------


def test_camera_view_remains_inside_world():
    """A view logica permanece contida no mundo logico.

    Valida invariantes (limites nao negativos, extensao dentro do
    mundo), nao valores exatos de view_x/view_y.
    """
    viewport = rendering._world_viewport_rect()
    corners = [
        (viewport.left + 1, viewport.top + 1),
        (viewport.right - 2, viewport.top + 1),
        (viewport.left + 1, viewport.bottom - 2),
        (viewport.right - 2, viewport.bottom - 2),
        _viewport_center(),
    ]
    for pos in corners:
        rendering.apply_zoom_at(pos, +3)
        rendering.apply_zoom_at(pos, -1)

    view_w, view_h = rendering._camera_view_size()

    assert rendering._camera.view_x >= 0.0
    assert rendering._camera.view_y >= 0.0

    assert (
        rendering._camera.view_x + view_w
        <= layout.LAYOUT.world_width + 1e-9
    )
    assert (
        rendering._camera.view_y + view_h
        <= layout.LAYOUT.world_height + 1e-9
    )


# ---------------------------------------------------------------------------
# reset_camera
# ---------------------------------------------------------------------------


def test_reset_camera_restores_canonical_state():
    """reset_camera() volta para 1x/origem e reporta mudanca.

    A segunda chamada consecutiva e no-op: retorna False e nao altera
    o estado.
    """
    rendering.apply_zoom_at(_viewport_center(), +2)

    changed = rendering.reset_camera()
    assert changed is True
    assert rendering._camera.zoom == pytest.approx(1.0)
    assert rendering._camera.view_x == pytest.approx(0.0)
    assert rendering._camera.view_y == pytest.approx(0.0)

    changed = rendering.reset_camera()
    assert changed is False


# ---------------------------------------------------------------------------
# screen_to_world / _screen_to_world_float
# ---------------------------------------------------------------------------


def test_screen_to_world_quantizes_float_transform():
    """screen_to_world() e a versao quantizada da transformacao float."""
    pos = _viewport_center()
    rendering.apply_zoom_at(pos, +1)

    floating = rendering._screen_to_world_float(pos)
    integer = rendering.screen_to_world(pos)

    assert floating is not None
    assert integer is not None
    assert integer == (int(floating[0]), int(floating[1]))


def test_screen_to_world_returns_none_outside_viewport():
    """Posicao na sidebar nao resolve para coordenada de mundo."""
    pos = (rendering._screen.get_width() - 1, 10)

    assert rendering._screen_to_world_float(pos) is None
    assert rendering.screen_to_world(pos) is None


# ---------------------------------------------------------------------------
# Source rect (raster crop)
# ---------------------------------------------------------------------------


def test_source_rect_at_one_x_is_full_world():
    """Em 1x o crop cobre todo o raster logico."""
    rect = rendering._camera_source_rect()
    assert rect == pygame.Rect(
        0,
        0,
        layout.LAYOUT.world_width,
        layout.LAYOUT.world_height,
    )


def test_source_rect_shrinks_when_zooming_in():
    """Zoom-in reduz o source rect nos dois eixos.

    Nao exige igualdade exata com world/1.2 porque floor/ceil
    introduz discretizacao.
    """
    before = rendering._camera_source_rect()

    rendering.apply_zoom_at(_viewport_center(), +1)

    after = rendering._camera_source_rect()

    assert after.width < before.width
    assert after.height < before.height


def test_source_rect_contains_continuous_camera_view():
    """O source rect inteiro cobre a view continua da camera.

    O crop e discreto (floor/ceil); a camera e float. O invariante
    util e contencao: o rect precisa abranger integralmente
    [view_x, view_x + view_w]. Igualdade exata seria um bug, nao um
    requisito.
    """
    rendering.apply_zoom_at(_viewport_center(), +2)

    rect = rendering._camera_source_rect()
    view_w, view_h = rendering._camera_view_size()

    assert rect.left <= rendering._camera.view_x
    assert rect.top <= rendering._camera.view_y

    assert rect.right >= rendering._camera.view_x + view_w
    assert rect.bottom >= rendering._camera.view_y + view_h


# ---------------------------------------------------------------------------
# Resize preserva camera
# ---------------------------------------------------------------------------


def test_resize_preserves_camera_state():
    """on_resize() recalcula o viewport fisico mas preserva a camera.

    Zoom, view_x e view_y sao estado de apresentacao independente da
    janela; o resize nao deve reinterpreta-los nem resetar a view.
    """
    rendering.apply_zoom_at(_viewport_center(), +2)
    before = (
        rendering._camera.zoom,
        rendering._camera.view_x,
        rendering._camera.view_y,
    )

    rendering.on_resize(1600, 900)

    after = (
        rendering._camera.zoom,
        rendering._camera.view_x,
        rendering._camera.view_y,
    )

    assert after[0] == pytest.approx(before[0])
    assert after[1] == pytest.approx(before[1])
    assert after[2] == pytest.approx(before[2])


# ---------------------------------------------------------------------------
# draw(): destino constante do scale
# ---------------------------------------------------------------------------


def test_draw_scales_crop_to_constant_viewport_size(monkeypatch):
    """draw() escala sempre para viewport.size, independente do zoom.

    Protege diretamente a decisao de crop-before-scale: em zoom alto
    o custo de escala nao cresce, porque o destino e a area fisica
    fixa do viewport e apenas o source encolhe.
    """
    world_image = np.zeros(
        (
            layout.LAYOUT.world_width,
            layout.LAYOUT.world_height,
            3,
        ),
        dtype=np.uint8,
    )
    monkeypatch.setattr(
        rendering,
        "_build_image",
        lambda: world_image,
    )
    monkeypatch.setattr(
        ui_state,
        "floating_hud_visible",
        False,
    )
    monkeypatch.setattr(
        rendering,
        "_draw_lateral_panel",
        lambda: None,
    )
    # _draw_zone_labels usa rendering._font, que nao e inicializada
    # neste teste (nao chamamos rendering.init()). O teste de escala
    # nao pretende cobrir Zone HP labels; isolar e o correto.
    monkeypatch.setattr(
        rendering,
        "_draw_zone_labels",
        lambda: None,
    )
    monkeypatch.setattr(
        pygame.display,
        "flip",
        lambda: None,
    )
    monkeypatch.setattr(state, "recording", False)

    real_scale = pygame.transform.scale
    calls: list[tuple[int, int]] = []

    def spy_scale(surface, size):
        calls.append(tuple(size))
        return real_scale(surface, size)

    monkeypatch.setattr(pygame.transform, "scale", spy_scale)

    rendering.reset_camera()
    calls.clear()
    rendering.draw()

    viewport_size = tuple(rendering._world_viewport_rect().size)
    assert calls == [viewport_size]

    rendering.apply_zoom_at(_viewport_center(), +2)
    calls.clear()
    rendering.draw()

    assert calls == [viewport_size]


# ---------------------------------------------------------------------------
# Zoom nao avanca simulacao
# ---------------------------------------------------------------------------


def test_camera_operations_do_not_advance_simulation():
    """Operacoes de camera nao alteram estado da simulacao.

    `tick_count` e `runtime_rules` sao as duas superficies mais
    faceis de verificar. A camera nem recebe referencia aos arrays
    de populacao, entao a checagem cobre o contrato real.
    """
    tick_before = state.tick_count
    rules_before = state.runtime_rules

    rendering.apply_zoom_at(_viewport_center(), +1)
    rendering.reset_camera()

    assert state.tick_count == tick_before
    assert state.runtime_rules is rules_before
