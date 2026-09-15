"""Contratos visuais de rendering._draw_nests e _build_image.

Objeto sob teste: o buffer NumPy [W, H, 3] uint8.

Nao testa pygame.display, janela, fullscreen nem draw(). O ponto e a
composicao do buffer: cores por canal, precedencia (critter sobre
ring), independencia do toggle de zonas e tratamento de estados
invalidos.

Todos os docstrings deste arquivo sao intencionalmente ASCII puro.
"""

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import layout
from primordial_soup import nest_geometry
from primordial_soup import rendering
from primordial_soup import state
from primordial_soup import world
from primordial_soup.state import agents


def _valid_nests():
    """Geometria canonica determinista: tres discos sem overlap."""
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


def _empty_image():
    return np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height, 3),
        dtype=np.uint8,
    )


@pytest.fixture
def rendering_state():
    """Estado limpo para desenhar sem pygame.

    Salva agents, seeda linhagens vazias, desliga zonas, instala nests
    deterministicos. Nao chama rendering.init() nem abre janela.
    """
    saved_agents = list(agents)
    saved_zones = state.zones
    saved_zones_active = state.zones_active
    saved_nests = state.nests
    saved_inspected = state.inspected_critter_id

    agents.clear()
    world.seed_lineages()

    state.zones = np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=bool,
    )
    state.zones_active = False
    state.nests = _valid_nests()
    state.inspected_critter_id = None

    yield

    agents[:] = saved_agents
    state.zones = saved_zones
    state.zones_active = saved_zones_active
    state.nests = saved_nests
    state.inspected_critter_id = saved_inspected


# ---------------------------------------------------------------------------
# Estados invalidos
# ---------------------------------------------------------------------------


def test_draw_nests_none_is_noop(rendering_state):
    image = _empty_image()
    before = image.copy()

    state.nests = None
    rendering._draw_nests(image)

    assert np.array_equal(image, before)


def test_draw_nests_invalid_count_raises(rendering_state):
    image = _empty_image()
    state.nests = ((10, 10),)

    with pytest.raises(RuntimeError):
        rendering._draw_nests(image)


# ---------------------------------------------------------------------------
# Ring escuro (cor da linhagem * _NEST_COLOR_SCALE)
# ---------------------------------------------------------------------------


def test_draw_nests_ring_uses_lineage_color_scaled(rendering_state):
    """Ring do ninho R em (0, 0): offset (-NEST_RADIUS, 0).

    O offset (-20, 0) esta no anel fino (d^2 = 400 <= 400 e
    d^2 > 19^2). O pixel wrapped resultante e
    (world_width - NEST_RADIUS, 0).
    """
    state.nests = (
        (0, 0),
        (layout.LAYOUT.world_width // 2, layout.LAYOUT.world_height // 2),
        (
            layout.LAYOUT.world_width - cfg.NEST_RADIUS - 1,
            layout.LAYOUT.world_height - cfg.NEST_RADIUS - 1,
        ),
    )

    image = _empty_image()
    rendering._draw_nests(image)

    wrapped_x = (0 - cfg.NEST_RADIUS) % layout.LAYOUT.world_width
    wrapped_y = 0

    expected_r = int(round(255 * rendering._NEST_COLOR_SCALE))
    assert image[wrapped_x, wrapped_y, 0] == expected_r
    assert image[wrapped_x, wrapped_y, 1] == 0
    assert image[wrapped_x, wrapped_y, 2] == 0


def test_draw_nests_center_is_not_ring(rendering_state):
    """Para radius > 1, o centro nao esta no anel: nao e pintado."""
    state.nests = (
        (0, 0),
        (layout.LAYOUT.world_width // 2, layout.LAYOUT.world_height // 2),
        (
            layout.LAYOUT.world_width - cfg.NEST_RADIUS - 1,
            layout.LAYOUT.world_height - cfg.NEST_RADIUS - 1,
        ),
    )

    image = _empty_image()
    rendering._draw_nests(image)

    assert image[0, 0].tolist() == [0, 0, 0]


# ---------------------------------------------------------------------------
# Independencia do toggle de zonas
# ---------------------------------------------------------------------------


def test_build_image_ring_visible_without_zones_active(rendering_state):
    """O ring e geometria permanente: nao depende de zones_active.

    Instala o ninho R em (0, 0) explicitamente. O fixture por padrao
    usa _valid_nests() (centros colineares em y=radius+1), cujo anel
    NAO passa por (world_width - NEST_RADIUS, 0). Sem esta
    instalacao, o teste verifica a coordenada errada e falha por
    motivo alheio ao toggle de zonas.
    """
    state.zones_active = False
    state.nests = (
        (0, 0),
        (layout.LAYOUT.world_width // 2, layout.LAYOUT.world_height // 2),
        (
            layout.LAYOUT.world_width - cfg.NEST_RADIUS - 1,
            layout.LAYOUT.world_height - cfg.NEST_RADIUS - 1,
        ),
    )

    image = rendering._build_image()

    wrapped_x = (0 - cfg.NEST_RADIUS) % layout.LAYOUT.world_width
    wrapped_y = 0
    expected_r = int(round(255 * rendering._NEST_COLOR_SCALE))

    assert image[wrapped_x, wrapped_y, 0] == expected_r


# ---------------------------------------------------------------------------
# Precedencia: critter > ring
# ---------------------------------------------------------------------------


def test_build_image_critter_over_nest_ring(rendering_state):
    """Um critter na celula do ring sobrescreve com cor cheia.

    _build_image desenha nests ANTES dos agents, via np.maximum. A
    cor cheia da linhagem domina o ring escuro.
    """
    # Ponto no ring de R (center = (21, 21)): offset (-20, 0).
    cx, cy = state.nests[0]
    ring_x = (cx - cfg.NEST_RADIUS) % layout.LAYOUT.world_width
    ring_y = cy

    agents[0]["field"][ring_x, ring_y] = 1

    image = rendering._build_image()

    assert tuple(image[ring_x, ring_y]) == tuple(cfg.LINEAGES[0]["color"])
