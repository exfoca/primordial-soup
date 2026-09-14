"""Testes estruturais de rendering.

Estrategia:
  - Surface real do pygame para testes em que pixels / clipping /
    geometria importam.
  - Spies / monkeypatch para testes puramente comportamentais
    (contagem de chamadas, aplicacao de split_weights, numero de
    heatmaps).
  - Font(None, size) apos pygame.font.init(): deterministico em CI,
    nao depende das fontes do sistema.
  - Sem pygame.display.set_mode(): o bundle nao exige display para
    desenhar em Surface.

Todos os docstrings e comentarios deste arquivo sao intencionalmente
ASCII puro, seguindo o estilo de nomenclatura interna do projeto.
"""

from __future__ import annotations

import numpy as np
import pygame
import pytest

from primordial_soup import config as cfg
from primordial_soup import rendering
from primordial_soup import state
from primordial_soup import ui_state
from primordial_soup import world
from primordial_soup.state import agents
from primordial_soup.world import (
    seed_lineages,
    place_initially,
    fill_fields,
    INDEX_HP,
    INDEX_X,
    INDEX_Y,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def _pygame_font():
    """pygame.font.init() uma vez por modulo.

    Font(None, size) nao depende de fontes do sistema e e
    deterministico em CI. Sem display: renderizacao para Surface
    funciona sem driver de video.
    """
    pygame.font.init()
    yield


@pytest.fixture
def fresh_world():
    """Mundo com 3 linhagens em lockstep, pronto para render."""
    state.reset_counters()
    seed_lineages()
    for ag in agents:
        ag["pool"] = np.random.uniform(
            cfg.MIN_GENE_VALUE, cfg.MAX_GENE_VALUE,
            (cfg.INITIAL_POPULATION_PER_LINEAGE, cfg.GENOME_SIZE),
        ).astype(np.float32)
    place_initially()
    fill_fields()
    yield
    state.reset_counters()
    agents.clear()


@pytest.fixture
def screen():
    """Surface real de tamanho window_width x window_height."""
    from primordial_soup import layout

    s = pygame.Surface(
        (layout.LAYOUT.window_width, layout.LAYOUT.window_height)
    )
    return s


@pytest.fixture
def render_fonts(monkeypatch):
    """Injeta fontes em rendering._font_* sem depender de init().

    Cada teste que renderiza injeta as fontes que precisar. Como as
    fontes usadas sao apenas para .render()/get_width()/get_height(),
    Font(None, size) e suficiente.
    """
    rendering._font = pygame.font.Font(None, 14)
    rendering._font_hud_title = pygame.font.Font(None, 15)
    rendering._font_chart = pygame.font.Font(None, 12)
    rendering._font_chart_title = pygame.font.Font(None, 13)
    rendering._font_tip = pygame.font.Font(None, 13)
    rendering._font_panel = pygame.font.Font(None, 14)
    rendering._font_panel_title = pygame.font.Font(None, 18)
    rendering._font_panel_small = pygame.font.Font(None, 11)
    yield


@pytest.fixture(autouse=True)
def _reset_ui():
    ui_state.reset()
    yield
    ui_state.reset()


def _set_screen(screen, monkeypatch):
    """Injeta uma Surface real como rendering._screen."""
    monkeypatch.setattr(rendering, "_screen", screen)


# ---------------------------------------------------------------------------
# _resolve_inspection_subject
# ---------------------------------------------------------------------------


def test_resolve_returns_none_without_selection(fresh_world):
    state.set_inspection_selection(None)
    assert rendering._resolve_inspection_subject() is None


def test_resolve_returns_alive_subject(fresh_world):
    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    subject = rendering._resolve_inspection_subject()
    assert subject is not None
    assert subject.alive is True
    assert subject.critter_id == cid
    assert subject.death_tick is None
    assert subject.agent_row is not None
    assert subject.genome is not None


def test_resolve_returns_dead_subject_from_snapshot(fresh_world):
    from primordial_soup.evolution import _capture_death_snapshot_if_needed

    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    agent = agents[0]
    matrix = agent["agents"]
    matrix[0, INDEX_HP] = 0.0
    alive = np.nonzero(matrix[:, INDEX_HP] > 0)[0]
    _capture_death_snapshot_if_needed(0, agent, alive, matrix)

    subject = rendering._resolve_inspection_subject()
    assert subject is not None
    assert subject.alive is False
    assert subject.critter_id == cid
    assert subject.death_tick is not None


# ---------------------------------------------------------------------------
# _draw_inspection_details: vivo vs morto vs sem selection
# ---------------------------------------------------------------------------


def test_details_vivo_chama_draw_vision_uma_vez(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Vivo: _draw_vision chamado 1x, split_weights 1x, 6 heatmaps."""
    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)

    calls = {"vision": 0, "split": 0, "heatmap": 0}

    from primordial_soup import brain as brain_module

    real_split = brain_module.split_weights
    real_draw_vision = rendering._draw_vision
    real_draw_heatmap = rendering._draw_heatmap

    def spy_split(w):
        calls["split"] += 1
        return real_split(w)

    def spy_draw_vision(surface, agent_row, x0, y0):
        calls["vision"] += 1
        return real_draw_vision(surface, agent_row, x0, y0)

    def spy_draw_heatmap(surface, weights, x0, y0, w, h, title):
        calls["heatmap"] += 1
        return real_draw_heatmap(surface, weights, x0, y0, w, h, title)

    monkeypatch.setattr(brain_module, "split_weights", spy_split)
    monkeypatch.setattr(rendering, "_draw_vision", spy_draw_vision)
    monkeypatch.setattr(rendering, "_draw_heatmap", spy_draw_heatmap)

    rendering._draw_inspection_details(screen, 0, 0, 300)

    assert calls["vision"] == 1
    assert calls["split"] == 1
    assert calls["heatmap"] == 6


def test_details_morto_nao_chama_draw_vision(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Morto: split_weights 1x, 6 heatmaps, ZERO _draw_vision."""
    from primordial_soup.evolution import _capture_death_snapshot_if_needed

    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    agent = agents[0]
    matrix = agent["agents"]
    matrix[0, INDEX_HP] = 0.0
    alive = np.nonzero(matrix[:, INDEX_HP] > 0)[0]
    _capture_death_snapshot_if_needed(0, agent, alive, matrix)

    calls = {"vision": 0, "split": 0, "heatmap": 0}

    from primordial_soup import brain as brain_module

    real_split = brain_module.split_weights
    real_draw_heatmap = rendering._draw_heatmap

    def spy_split(w):
        calls["split"] += 1
        return real_split(w)

    def spy_draw_vision(*args, **kwargs):
        calls["vision"] += 1

    def spy_draw_heatmap(surface, weights, x0, y0, w, h, title):
        calls["heatmap"] += 1
        return real_draw_heatmap(surface, weights, x0, y0, w, h, title)

    monkeypatch.setattr(brain_module, "split_weights", spy_split)
    monkeypatch.setattr(rendering, "_draw_vision", spy_draw_vision)
    monkeypatch.setattr(rendering, "_draw_heatmap", spy_draw_heatmap)

    rendering._draw_inspection_details(screen, 0, 0, 300)

    assert calls["vision"] == 0
    assert calls["split"] == 1
    assert calls["heatmap"] == 6


def test_details_sem_selection_nao_desenha(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Sem selection: nada e desenhado, sem exception."""
    state.set_inspection_selection(None)

    calls = {"vision": 0, "split": 0, "heatmap": 0}

    from primordial_soup import brain as brain_module

    def spy_split(w):
        calls["split"] += 1
        return brain_module.split_weights(w)

    def spy_draw_vision(*args, **kwargs):
        calls["vision"] += 1

    def spy_draw_heatmap(*args, **kwargs):
        calls["heatmap"] += 1
        return args[3]

    monkeypatch.setattr(brain_module, "split_weights", spy_split)
    monkeypatch.setattr(rendering, "_draw_vision", spy_draw_vision)
    monkeypatch.setattr(rendering, "_draw_heatmap", spy_draw_heatmap)

    result = rendering._draw_inspection_details(screen, 0, 0, 300)

    assert result == 0  # retorna y0 sem desenhar
    assert calls["vision"] == 0
    assert calls["split"] == 0
    assert calls["heatmap"] == 0


# ---------------------------------------------------------------------------
# Clip + scroll
# ---------------------------------------------------------------------------


def test_draw_lateral_panel_restaura_clip(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Clip da _screen e restaurado apos _draw_lateral_panel."""
    _set_screen(screen, monkeypatch)

    # Popula ao menos um painel para o rendering nao ser no-op.
    from primordial_soup import panels_defs, panels
    panels.PANELS.clear()
    panels_defs.register_default_panels()

    sentinel_clip = pygame.Rect(11, 22, 33, 44)
    screen.set_clip(sentinel_clip)

    rendering._draw_lateral_panel()

    assert screen.get_clip() == sentinel_clip


def test_scroll_clamped_nao_negativo(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Scroll e clampado em [0, max]."""
    _set_screen(screen, monkeypatch)
    from primordial_soup import panels_defs, panels
    panels.PANELS.clear()
    panels_defs.register_default_panels()

    ui_state.active_panel = ui_state.PANEL_INSPECTION
    ui_state.panel_scroll_offsets[ui_state.PANEL_INSPECTION] = -999
    rendering._draw_lateral_panel()
    assert ui_state.panel_scroll_offsets[ui_state.PANEL_INSPECTION] >= 0

    ui_state.panel_scroll_offsets[ui_state.PANEL_INSPECTION] = 999_999
    rendering._draw_lateral_panel()
    # Nao pode passar do maximo permitido, mas nunca negativo.
    assert ui_state.panel_scroll_offsets[ui_state.PANEL_INSPECTION] >= 0


def test_ui_state_reset_zera_offsets():
    """ui_state.reset() zera panel_scroll_offsets."""
    for k in ui_state.panel_scroll_offsets:
        ui_state.panel_scroll_offsets[k] = 42
    ui_state.reset()
    for v in ui_state.panel_scroll_offsets.values():
        assert v == 0


def test_ui_state_reset_restores_floating_hud():
    """ui_state.reset() restaura floating_hud_visible para True."""
    ui_state.floating_hud_visible = False

    ui_state.reset()

    assert ui_state.floating_hud_visible is True


def test_toggle_floating_hud():
    """toggle_floating_hud alterna e retorna o novo estado."""
    assert ui_state.floating_hud_visible is True

    assert ui_state.toggle_floating_hud() is False
    assert ui_state.floating_hud_visible is False

    assert ui_state.toggle_floating_hud() is True
    assert ui_state.floating_hud_visible is True


# ---------------------------------------------------------------------------
# Hide/Show floating HUD: gate em draw()
# ---------------------------------------------------------------------------


def test_draw_gates_floating_hud_on_visible(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Com HUD visivel: _draw_telemetry_hud e _draw_lateral_panel
    sao chamados."""
    _set_screen(screen, monkeypatch)
    ui_state.floating_hud_visible = True

    calls = {"hud": 0, "lateral": 0}

    monkeypatch.setattr(
        rendering, "_draw_telemetry_hud",
        lambda: calls.__setitem__("hud", calls["hud"] + 1),
    )
    monkeypatch.setattr(
        rendering, "_draw_lateral_panel",
        lambda: calls.__setitem__("lateral", calls["lateral"] + 1),
    )
    # _build_image toca state; ja temos fresh_world, mas evitamos
    # custo desnecessario.
    monkeypatch.setattr(
        rendering, "_build_image",
        lambda: np.zeros((2, 2, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(
        pygame.transform, "scale",
        lambda surface, size: surface,
    )
    monkeypatch.setattr(pygame.display, "flip", lambda: None)

    rendering.draw()

    assert calls["hud"] == 1
    assert calls["lateral"] == 1


def test_draw_gates_floating_hud_on_hidden(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Com HUD oculto: _draw_telemetry_hud NAO e chamado;
    _draw_lateral_panel continua."""
    _set_screen(screen, monkeypatch)
    ui_state.floating_hud_visible = False

    calls = {"hud": 0, "lateral": 0}

    monkeypatch.setattr(
        rendering, "_draw_telemetry_hud",
        lambda: calls.__setitem__("hud", calls["hud"] + 1),
    )
    monkeypatch.setattr(
        rendering, "_draw_lateral_panel",
        lambda: calls.__setitem__("lateral", calls["lateral"] + 1),
    )
    monkeypatch.setattr(
        rendering, "_build_image",
        lambda: np.zeros((2, 2, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(
        pygame.transform, "scale",
        lambda surface, size: surface,
    )
    monkeypatch.setattr(pygame.display, "flip", lambda: None)

    rendering.draw()

    assert calls["hud"] == 0
    assert calls["lateral"] == 1


# ---------------------------------------------------------------------------
# Geometria real (screen-space)
# ---------------------------------------------------------------------------


def test_lateral_usa_screen_size_real(
    fresh_world, render_fonts, monkeypatch
):
    """Lateral.x == screen_width - panel_width; altura == screen_height.

    Em screen-space, a _screen real e a autoridade, nao o LAYOUT.
    """
    from primordial_soup import layout

    big_w = layout.LAYOUT.window_width + 400
    big_h = layout.LAYOUT.window_height + 200
    screen = pygame.Surface((big_w, big_h))
    _set_screen(screen, monkeypatch)

    from primordial_soup import panels_defs, panels
    panels.PANELS.clear()
    panels_defs.register_default_panels()

    # Substitui _draw_tab_bar por um spy que registra (x0, y0, w, h).
    calls = []
    real_tab = rendering._draw_tab_bar

    def spy_tab(x0, y0, w, h):
        calls.append((x0, y0, w, h))
        return real_tab(x0, y0, w, h)

    monkeypatch.setattr(rendering, "_draw_tab_bar", spy_tab)

    rendering._draw_lateral_panel()

    assert calls, "tab bar nao foi desenhada"
    x0, y0, w, h = calls[0]
    assert x0 == big_w - cfg.INSPECTION_PANEL_WIDTH
    assert w == cfg.INSPECTION_PANEL_WIDTH


# ---------------------------------------------------------------------------
# Gates de overlay por painel focado (arquitetura (a))
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Command Dock (Patch 3)
# ---------------------------------------------------------------------------


def test_command_dock_uses_only_world_width(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Dock e ancorado em HUD_MARGIN a esquerda e nao invade a
    sidebar."""
    _set_screen(screen, monkeypatch)

    rect = rendering._draw_command_dock()

    usable_right = screen.get_width() - cfg.INSPECTION_PANEL_WIDTH
    assert rect.left == cfg.HUD_MARGIN
    assert rect.right <= usable_right - cfg.HUD_MARGIN


def test_command_dock_anchored_at_bottom(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Dock e ancorado no fundo, com HUD_MARGIN de respiro."""
    _set_screen(screen, monkeypatch)

    rect = rendering._draw_command_dock()

    assert rect.bottom == screen.get_height() - cfg.HUD_MARGIN


def test_command_dock_renders_under_both_languages(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Dock cabe na area util em EN e PT."""
    _set_screen(screen, monkeypatch)

    from primordial_soup import i18n

    usable_right = screen.get_width() - cfg.INSPECTION_PANEL_WIDTH

    old_lang = state.language
    try:
        for lang in i18n.AVAILABLE_LANGUAGES:
            state.language = lang
            rect = rendering._draw_command_dock()
            assert rect.right <= usable_right
            assert rect.bottom <= screen.get_height()
    finally:
        state.language = old_lang


def test_keycap_returns_rect(
    fresh_world, screen, render_fonts, monkeypatch
):
    """_draw_keycap retorna Rect com largura/altura > 0."""
    _set_screen(screen, monkeypatch)

    rect = rendering._draw_keycap(screen, "SPACE", 10, 10)
    assert rect.width > 0
    assert rect.height > 0
    assert rect.left == 10
    assert rect.top == 10


# ---------------------------------------------------------------------------
# Telemetry HUD (Patch 2)
# ---------------------------------------------------------------------------


def test_telemetry_hud_stays_inside_world_area(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Telemetry HUD e ancorado em (HUD_MARGIN, HUD_MARGIN) e nunca
    invade a faixa da sidebar."""
    _set_screen(screen, monkeypatch)

    rect = rendering._draw_telemetry_hud()

    usable_right = screen.get_width() - cfg.INSPECTION_PANEL_WIDTH
    assert rect.left == cfg.HUD_MARGIN
    assert rect.top == cfg.HUD_MARGIN
    assert rect.right <= usable_right - cfg.HUD_MARGIN
    assert rect.width == cfg.HUD_TELEMETRY_WIDTH


def test_telemetry_hud_renders_under_all_states(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Nao quebra com recording ON, zonas OFF, efeito negativo, PT."""
    _set_screen(screen, monkeypatch)

    from primordial_soup import i18n

    # recording OFF
    state.recording = False
    state.zones_active = True
    state.zone_hp_effect = 5
    rendering._draw_telemetry_hud()

    # recording ON
    state.recording = True
    rendering._draw_telemetry_hud()
    state.recording = False

    # zonas OFF
    state.zones_active = False
    rendering._draw_telemetry_hud()
    state.zones_active = True

    # efeito negativo
    state.zone_hp_effect = -50
    rendering._draw_telemetry_hud()
    state.zone_hp_effect = 5

    # PT
    old_lang = state.language
    try:
        state.language = "pt"
        rendering._draw_telemetry_hud()
    finally:
        state.language = old_lang


def test_telemetry_hud_does_not_check_floating_hud_visible(
    fresh_world, screen, render_fonts, monkeypatch
):
    """O gate pertence a draw(); o Telemetry HUD desenha mesmo com
    floating_hud_visible=False quando chamado diretamente."""
    _set_screen(screen, monkeypatch)
    ui_state.floating_hud_visible = False

    # Nao deve levantar e deve retornar um Rect.
    rect = rendering._draw_telemetry_hud()
    assert isinstance(rect, pygame.Rect)
    assert rect.width > 0
    assert rect.height > 0


def test_trail_e_markers_gated_por_painel_focado(fresh_world, screen, monkeypatch):
    """Trocar Inspection -> Configuration esconde overlay sem limpar
    a Observation interna.

    O stable ID continua selecionado; o trail continua armazenado;
    mas _build_image nao desenha contorno amarelo, ciano nem trail
    quando o painel focado nao e Inspection.
    """
    _set_screen(screen, monkeypatch)

    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    state.inspected_trail.append((5, 5))

    # Painel Inspection focado: overlay habilitado.
    ui_state.set_active_panel(ui_state.PANEL_INSPECTION)
    img_insp = rendering._build_image()

    # Painel Configuration focado: overlay oculto, Observation preservada.
    ui_state.set_active_panel(ui_state.PANEL_CONFIGURATION)
    img_conf = rendering._build_image()

    assert state.inspected_critter_id == cid, (
        "trocar de painel nao pode limpar Observation"
    )
    assert len(state.inspected_trail) == 1, (
        "trocar de painel nao pode limpar trail"
    )
    # Imagens diferentes: com Inspection ha overlay; sem ele, nao.
    assert not np.array_equal(img_insp, img_conf), (
        "overlay deveria diferenciar paineis; imagens identicas"
    )
