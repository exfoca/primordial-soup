"""Testes estruturais da composicao do Telemetry HUD.

Cobrem o contrato do compositor apos a refatoracao em tres regioes:
brand frameless, painel com moldura, tabela frameless. Os testes
verificam geometria logica, nao pixels: sao robustos a mudanca de
fonte do sistema e a ajustes de padding dentro da faixa esperada.
"""

from __future__ import annotations

import numpy as np
import pygame
import pytest

from primordial_soup import config as cfg
from primordial_soup import rendering
from primordial_soup import state
from primordial_soup import ui_state
from primordial_soup.state import agents
from primordial_soup.world import seed_lineages, place_initially, fill_fields


@pytest.fixture(scope="module", autouse=True)
def _pygame_font():
    pygame.font.init()
    yield


@pytest.fixture
def fresh_world():
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
    from primordial_soup import layout
    return pygame.Surface(
        (layout.LAYOUT.window_width, layout.LAYOUT.window_height)
    )


@pytest.fixture
def render_fonts(monkeypatch):
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
    monkeypatch.setattr(rendering, "_screen", screen)


# ---------------------------------------------------------------------------
# Geometria vertical: brand -> panel -> lineage
# ---------------------------------------------------------------------------


def test_brand_anchored_at_hud_margin(
    fresh_world, screen, render_fonts, monkeypatch
):
    _set_screen(screen, monkeypatch)
    rect = rendering._draw_telemetry_brand(
        cfg.HUD_MARGIN, cfg.HUD_MARGIN, cfg.HUD_TELEMETRY_WIDTH
    )
    assert rect.top == cfg.HUD_MARGIN
    assert rect.left == cfg.HUD_MARGIN


def test_panel_below_brand(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Panel comeca estritamente abaixo do brand."""
    _set_screen(screen, monkeypatch)
    brand = rendering._draw_telemetry_brand(
        cfg.HUD_MARGIN, cfg.HUD_MARGIN, cfg.HUD_TELEMETRY_WIDTH
    )
    panel = rendering._draw_telemetry_panel(
        cfg.HUD_MARGIN, brand.bottom + 5, cfg.HUD_TELEMETRY_WIDTH
    )
    assert panel.top > brand.bottom


def test_lineage_below_panel(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Tabela comeca estritamente abaixo do painel."""
    _set_screen(screen, monkeypatch)
    panel_y = cfg.HUD_MARGIN + 40
    panel = rendering._draw_telemetry_panel(
        cfg.HUD_MARGIN, panel_y, cfg.HUD_TELEMETRY_WIDTH
    )
    lineage = rendering._draw_lineage_table(
        cfg.HUD_MARGIN, panel.bottom + 7, cfg.HUD_TELEMETRY_WIDTH
    )
    assert lineage.top > panel.bottom


def test_compositor_bounding_box(
    fresh_world, screen, render_fonts, monkeypatch
):
    """_draw_telemetry_hud retorna o bounding box das tres regioes."""
    _set_screen(screen, monkeypatch)
    rect = rendering._draw_telemetry_hud()

    assert rect.top == cfg.HUD_MARGIN
    assert rect.left == cfg.HUD_MARGIN
    assert rect.width == cfg.HUD_TELEMETRY_WIDTH
    assert rect.height > 0


def test_compositor_fits_usable_width(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Bounding box respeita usable_right - HUD_MARGIN."""
    _set_screen(screen, monkeypatch)
    rect = rendering._draw_telemetry_hud()
    usable_right = screen.get_width() - cfg.INSPECTION_PANEL_WIDTH
    assert rect.right <= usable_right - cfg.HUD_MARGIN


# ---------------------------------------------------------------------------
# Frameless: brand e tabela nao desenham moldura
# ---------------------------------------------------------------------------


def test_brand_has_no_border(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Brand nao emite retangulos de fundo/borda.

    Spy em pygame.draw.rect: com brand isolado, a contagem deve ser
    zero (brand so blita Surfaces).
    """
    _set_screen(screen, monkeypatch)
    calls = []
    real_rect = pygame.draw.rect

    def spy_rect(*args, **kwargs):
        calls.append(args)
        return real_rect(*args, **kwargs)

    monkeypatch.setattr(pygame.draw, "rect", spy_rect)

    rendering._draw_telemetry_brand(
        cfg.HUD_MARGIN, cfg.HUD_MARGIN, cfg.HUD_TELEMETRY_WIDTH
    )

    assert calls == [], (
        f"brand nao deve desenhar retangulos; obteve {len(calls)} "
        f"chamadas a pygame.draw.rect."
    )


def test_lineage_table_has_no_border(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Tabela nao emite retangulos de fundo/borda."""
    _set_screen(screen, monkeypatch)
    calls = []
    real_rect = pygame.draw.rect

    def spy_rect(*args, **kwargs):
        calls.append(args)
        return real_rect(*args, **kwargs)

    monkeypatch.setattr(pygame.draw, "rect", spy_rect)

    rendering._draw_lineage_table(
        cfg.HUD_MARGIN, cfg.HUD_MARGIN, cfg.HUD_TELEMETRY_WIDTH
    )

    assert calls == [], (
        f"tabela nao deve desenhar retangulos; obteve {len(calls)} "
        f"chamadas a pygame.draw.rect."
    )


def test_panel_has_border(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Painel central e a unica regiao com moldura.

    Espia pygame.draw.rect: o painel desenha exatamente um rect de
    borda (o fundo translucido nao usa draw.rect, e um Surface.blit).
    """
    _set_screen(screen, monkeypatch)
    calls = []
    real_rect = pygame.draw.rect

    def spy_rect(*args, **kwargs):
        calls.append(args)
        return real_rect(*args, **kwargs)

    monkeypatch.setattr(pygame.draw, "rect", spy_rect)

    rendering._draw_telemetry_panel(
        cfg.HUD_MARGIN, cfg.HUD_MARGIN, cfg.HUD_TELEMETRY_WIDTH
    )

    # O painel desenha a borda com width=1 e possivelmente o
    # separador via _draw_hud_divider (pygame.draw.line, nao rect).
    # Esperamos exatamente 1 rect de borda.
    assert len(calls) == 1, (
        f"painel deve emitir exatamente 1 pygame.draw.rect (borda); "
        f"obteve {len(calls)}."
    )


# ---------------------------------------------------------------------------
# Tabela: alinhamento interno
# ---------------------------------------------------------------------------


class _BlitSpyScreen:
    """Wrapper de Surface que registra blits.

    pygame.Surface e tipo C imutavel em pygame 2; nao da para
    monkeypatch em Surface.blit. Este wrapper e injetado como
    rendering._screen e intercepta as chamadas que o modulo faz
    nessa surface.
    """

    def __init__(self, real):
        self._real = real
        self.blits = []

    def blit(self, source, dest, *args, **kwargs):
        self.blits.append((source, dest))
        return self._real.blit(source, dest, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_lineage_table_aligned_with_panel_inner(
    fresh_world, screen, render_fonts, monkeypatch
):
    """Tabela comeca em x0 + HUD_PADDING, mesma linha interna do painel.

    Verificacao via spy no _screen injetado: registra o destino de
    cada blit e confirma que a header comeca em x0 + HUD_PADDING.
    """
    spy_screen = _BlitSpyScreen(screen)
    _set_screen(spy_screen, monkeypatch)

    rendering._draw_lineage_table(
        cfg.HUD_MARGIN, cfg.HUD_MARGIN, cfg.HUD_TELEMETRY_WIDTH
    )

    expected_x = cfg.HUD_MARGIN + cfg.HUD_PADDING
    assert spy_screen.blits, "tabela nao blitou nada"
    header_blits = [
        (source, dest) for source, dest in spy_screen.blits
        if isinstance(dest, tuple) and dest[0] == expected_x
    ]
    assert header_blits, (
        f"tabela deve blitar em x={expected_x} (x0 + HUD_PADDING); "
        f"destinos observados: {[d for _, d in spy_screen.blits[:3]]}"
    )


# ---------------------------------------------------------------------------
# Icone: graceful degradation
# ---------------------------------------------------------------------------


def test_brand_works_without_icon(
    fresh_world, screen, render_fonts, monkeypatch
):
    """_hud_icon=None: brand desenha normalmente, sem crash."""
    _set_screen(screen, monkeypatch)
    monkeypatch.setattr(rendering, "_hud_icon", None)

    rect = rendering._draw_telemetry_brand(
        cfg.HUD_MARGIN, cfg.HUD_MARGIN, cfg.HUD_TELEMETRY_WIDTH
    )

    assert rect.width == cfg.HUD_TELEMETRY_WIDTH
    assert rect.height > 0


def test_brand_with_icon_blits_icon(
    fresh_world, screen, render_fonts, monkeypatch
):
    """_hud_icon definido: brand blita a Surface do icone."""
    spy_screen = _BlitSpyScreen(screen)
    _set_screen(spy_screen, monkeypatch)

    fake_icon = pygame.Surface((18, 18))
    fake_icon.fill((255, 0, 255))  # cor de sentinela
    monkeypatch.setattr(rendering, "_hud_icon", fake_icon)

    rendering._draw_telemetry_brand(
        cfg.HUD_MARGIN, cfg.HUD_MARGIN, cfg.HUD_TELEMETRY_WIDTH
    )

    blitted_sources = [source for source, _ in spy_screen.blits]
    assert fake_icon in blitted_sources, (
        "brand deve blitar o icone quando _hud_icon esta definido"
    )


# ---------------------------------------------------------------------------
# draw() gate: floating_hud_visible
# ---------------------------------------------------------------------------


def test_draw_gate_still_hides_all_three_regions(
    fresh_world, screen, render_fonts, monkeypatch
):
    """floating_hud_visible=False: _draw_telemetry_hud nao e chamado."""
    _set_screen(screen, monkeypatch)
    ui_state.floating_hud_visible = False

    calls = {"hud": 0}
    monkeypatch.setattr(
        rendering, "_draw_telemetry_hud",
        lambda: calls.__setitem__("hud", calls["hud"] + 1),
    )
    monkeypatch.setattr(
        rendering, "_draw_lateral_panel", lambda: None,
    )
    monkeypatch.setattr(
        rendering, "_build_image",
        lambda: np.zeros((2, 2, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(
        pygame.transform, "scale", lambda s, size: s,
    )
    monkeypatch.setattr(pygame.display, "flip", lambda: None)

    rendering.draw()

    assert calls["hud"] == 0


# ---------------------------------------------------------------------------
# Zone HP no Telemetry: delegacao ao formatter canonico
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("effect", "expected"),
    [
        (5, "+5"),
        (0, "0"),
        (-1, "-1"),
    ],
)
def test_telemetry_zone_hp_uses_canonical_format(
    effect,
    expected,
    monkeypatch,
):
    """Telemetry formata zone_hp_effect via world.format_zone_hp_effect.

    O bug original era f"{effect:+d}" -> "+0" para effect == 0.
    Este teste exercita _draw_telemetry_panel() - a fronteira real
    onde o defeito vivia - e intercepta o par (label, value) enviado
    a _draw_hud_kv_inline. Nao testa apenas a funcao isolada, porque
    isso nao teria impedido a regressao do consumidor.
    """
    from primordial_soup import i18n
    from primordial_soup import rendering
    from primordial_soup import state

    original_rules = state.runtime_rules
    try:
        state.update_runtime_rules(zone_hp_effect=effect)

        monkeypatch.setattr(
            rendering, "_screen", pygame.Surface((800, 600))
        )
        monkeypatch.setattr(
            rendering,
            "_draw_hud_kv",
            lambda screen, label, value, x, y: y + 1,
        )
        monkeypatch.setattr(
            rendering,
            "_draw_hud_divider",
            lambda screen, x, y, width: y + 1,
        )
        monkeypatch.setattr(
            rendering, "_zone_summary", lambda: "zones"
        )

        captured: list[tuple[str, str]] = []

        def capture_inline(screen, entries, x, y):
            captured.extend(entries)
            return y + 1

        monkeypatch.setattr(
            rendering, "_draw_hud_kv_inline", capture_inline
        )

        rendering._draw_telemetry_panel(0, 0, 400)

        zone_hp_label = i18n.t("hud.label.zone_hp")
        zone_hp_entries = [
            value
            for label, value in captured
            if label == zone_hp_label
        ]

        assert zone_hp_entries == [expected], (
            f"effect={effect}: esperado [{expected!r}] em "
            f"hud.label.zone_hp; obtido {zone_hp_entries!r}."
        )

        if effect == 0:
            # Reforca a regressao especifica: zero nunca pode virar "+0".
            assert "+0" not in zone_hp_entries
    finally:
        state.set_runtime_rules(original_rules)


def test_telemetry_zone_hp_delegates_to_world_formatter(
    monkeypatch,
):
    """Telemetry delega a world.format_zone_hp_effect, sem include_unit.

    Prova arquitetural: o Telemetry nao recria regra local de sinal.
    Se o formatter for substituido, o valor sentinel precisa aparecer
    no par enviado ao HUD, e o formatter precisa receber
    include_unit=False (o label do HUD ja e "ZONE HP").
    """
    from primordial_soup import i18n
    from primordial_soup import rendering
    from primordial_soup import state

    original_rules = state.runtime_rules
    try:
        state.update_runtime_rules(zone_hp_effect=37)

        calls: list[tuple[int, bool]] = []

        def fake_format(effect, *, include_unit=False):
            calls.append((effect, include_unit))
            return "ZONE_HP_SENTINEL"

        monkeypatch.setattr(
            rendering.world,
            "format_zone_hp_effect",
            fake_format,
        )

        monkeypatch.setattr(
            rendering, "_screen", pygame.Surface((800, 600))
        )
        monkeypatch.setattr(
            rendering,
            "_draw_hud_kv",
            lambda screen, label, value, x, y: y + 1,
        )
        monkeypatch.setattr(
            rendering,
            "_draw_hud_divider",
            lambda screen, x, y, width: y + 1,
        )
        monkeypatch.setattr(
            rendering, "_zone_summary", lambda: "zones"
        )

        captured: list[tuple[str, str]] = []

        def capture_inline(screen, entries, x, y):
            captured.extend(entries)
            return y + 1

        monkeypatch.setattr(
            rendering, "_draw_hud_kv_inline", capture_inline
        )

        rendering._draw_telemetry_panel(0, 0, 400)

        assert calls == [(37, False)], (
            f"Telemetry deve chamar format_zone_hp_effect(37, "
            f"include_unit=False); chamadas observadas: {calls!r}."
        )

        zone_hp_label = i18n.t("hud.label.zone_hp")
        zone_hp_entries = [
            value
            for label, value in captured
            if label == zone_hp_label
        ]
        assert zone_hp_entries == ["ZONE_HP_SENTINEL"], (
            "Telemetry nao propagou o retorno do formatter canonico "
            f"para o HUD; observado: {zone_hp_entries!r}."
        )
    finally:
        state.set_runtime_rules(original_rules)


# ---------------------------------------------------------------------------
# RuntimeRules x config: Telemetry le o valor ativo, nao o default
# ---------------------------------------------------------------------------


def test_telemetry_global_mutation_uses_runtime_rules(
    fresh_world,
    screen,
    render_fonts,
    monkeypatch,
):
    """O Telemetry le global_probability/global_scale_fraction de
    RuntimeRules, nao dos defaults estaticos correspondentes em
    config.py.

    Monkeypatcha cfg.GLOBAL_PROBABILITY e cfg.GLOBAL_SCALE_FRACTION
    para valores deliberadamente divergentes; o valor exibido deve
    seguir RuntimeRules.
    """
    _set_screen(screen, monkeypatch)

    original = state.runtime_rules
    captured: list[tuple[str, str]] = []
    try:
        state.update_runtime_rules(
            global_probability=75,
            global_scale_fraction=40,
        )
        monkeypatch.setattr(cfg, "GLOBAL_PROBABILITY", 0.10)
        monkeypatch.setattr(cfg, "GLOBAL_SCALE_FRACTION", 0.20)

        monkeypatch.setattr(
            rendering,
            "_draw_hud_kv",
            lambda screen_, label, value, x, y: y + 1,
        )
        monkeypatch.setattr(
            rendering,
            "_draw_hud_divider",
            lambda screen_, x, y, width: y + 1,
        )

        def fake_inline(screen_, entries, x, y):
            captured.extend(entries)
            return y + 1

        monkeypatch.setattr(
            rendering, "_draw_hud_kv_inline", fake_inline
        )
        monkeypatch.setattr(
            rendering, "_zone_summary", lambda: "zones"
        )

        rendering._draw_telemetry_panel(0, 0, 400)

        values = [value for _label, value in captured]
        assert "75%@40%" in values
        assert "10%@20%" not in values
    finally:
        state.set_runtime_rules(original)


# ---------------------------------------------------------------------------
# Camera zoom: Telemetry reflete o fator atual
# ---------------------------------------------------------------------------


def test_telemetry_displays_camera_zoom(
    fresh_world,
    screen,
    render_fonts,
    monkeypatch,
):
    """O painel de telemetria mostra o fator de zoom atual da camera.

    Este teste valida apenas a FORMATACAO do HUD (label + valor),
    nao a matematica da camera. Por isso manipula `_camera.zoom`
    diretamente em vez de simular wheel. A matematica da camera e
    coberta por tests/test_rendering_camera.py.
    """
    _set_screen(screen, monkeypatch)

    from primordial_soup import i18n

    monkeypatch.setattr(
        rendering,
        "_draw_hud_divider",
        lambda screen_, x, y, width: y + 1,
    )

    captured_zoom: list[tuple[str, str]] = []

    def fake_kv(screen_, label, value, x, y):
        captured_zoom.append((label, value))
        return y + 1

    monkeypatch.setattr(rendering, "_draw_hud_kv", fake_kv)

    def capture_inline(screen_, entries, x, y):
        for label, value in entries:
            captured_zoom.append((label, value))
        return y + 1

    monkeypatch.setattr(
        rendering, "_draw_hud_kv_inline", capture_inline
    )
    monkeypatch.setattr(
        rendering, "_zone_summary", lambda: "zones"
    )

    try:
        rendering.reset_camera()
        captured_zoom.clear()
        rendering._draw_telemetry_panel(0, 0, 400)
        assert (
            i18n.t("hud.label.zoom"),
            "1.00x",
        ) in captured_zoom

        captured_zoom.clear()
        rendering._camera.zoom = 1.20
        rendering._draw_telemetry_panel(0, 0, 400)
        assert (
            i18n.t("hud.label.zoom"),
            "1.20x",
        ) in captured_zoom
    finally:
        rendering.reset_camera()
