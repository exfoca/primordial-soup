# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import math
import os
from dataclasses import dataclass

import numpy as np
import pygame

from . import config as cfg
from . import layout
from . import nest_geometry
from . import state
from . import i18n
from . import world
from . import ui_state
from . import panels
from .state import agents
from .world import (
    INDEX_ENCOUNTERS,
    INDEX_OFFSPRING,
    INDEX_GENERATION,
    INDEX_HP,
    INDEX_COMPOSITE_SCORE,
    INDEX_TIME,
    INDEX_LAST_ACTION,
    INDEX_X,
    INDEX_Y,
    max_generation,
    average_hp_per_lineage,
    longest_lifetime,
    average_composite_score_per_lineage,
    discovery_criterion_value,
)

_screen = None
_clock = None
_font = None
_font_hud_title = None
_font_chart = None
_font_chart_title = None
_font_tip = None
_font_panel = None
_font_panel_title = None
_font_panel_small = None

# Ícone pequeno do brand, carregado uma única vez em init().
# None se o PNG falhar ao carregar; o brand degrada para só texto.
_hud_icon: pygame.Surface | None = None

# Estado de tela cheia. F11 alterna via toggle_fullscreen().
_fullscreen: bool = False


@dataclass
class _Camera:
    """Camera de apresentacao.

    Estado puramente visual da regiao logica do mundo observada.
    Nao pertence a state.py, nao vai para checkpoint, nao afeta a
    simulacao. Unico lugar onde zoom vive.

    Coordenadas sao LOGICAS do mundo (celulas), nao screen-space.
    """
    zoom: float = 1.0
    view_x: float = 0.0
    view_y: float = 0.0


_camera = _Camera()


# Retangulo fisico em que o mundo e desenhado na tela. Representa
# APENAS "onde o mundo cabe" (letterbox ja aplicado), nunca a regiao
# observada. Este retangulo e recalculado por _recompute_viewport() a
# cada resize/toggle_fullscreen.
#
# Distincao chave:
#   viewport -> screen-space (onde desenhar)
#   camera   -> world-space  (qual regiao observar)
_viewport_rect = pygame.Rect(
    0,
    0,
    layout.LAYOUT.world_width * layout.LAYOUT.pixel_scale,
    layout.LAYOUT.world_height * layout.LAYOUT.pixel_scale,
)


_MOORE_OFFSETS: tuple[tuple[int, int], ...] = tuple(
    (dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if not (dx == 0 and dy == 0)
)
_HIGHLIGHT_COLOR: tuple[int, int, int] = (255, 255, 0)

# Cor base das zonas ambientais. Tom aditivo suave sob as linhagens,
# para nao competir com as cores RPS.
_ZONE_COLOR: tuple[int, int, int] = (24, 20, 8)

# Escala aplicada a cor canonica da linhagem para desenhar o ring do
# ninho. Detalhe estatico de rendering; nao pertence a RuntimeRules
# nem a config.
_NEST_COLOR_SCALE = 0.35


_HUD_BG = cfg.HUD_BG_COLOR
_HUD_BORDER = cfg.HUD_BORDER_COLOR
_HUD_TEXT = cfg.HUD_TEXT_COLOR
_HUD_SEC = cfg.HUD_TEXT_SECONDARY_COLOR

_CHART_BG = cfg.CHART_BG_COLOR
_CHART_GRID = cfg.CHART_GRID_COLOR
_CHART_AXIS = cfg.CHART_AXIS_COLOR
_CHART_LABEL = cfg.CHART_LABEL_COLOR
_CHART_TITLE = cfg.CHART_TITLE_COLOR

_LINEAGE_COLORS: tuple[tuple[int, int, int], ...] = (
    (255, 72, 72),  # R
    (72, 255, 96),  # G
    (80, 140, 255),  # B
)

# Mapa id_de_linhagem -> cor, usado quando so temos o lineage_id do
# snapshot de morte (sem acesso a linha viva do agente). Derivado de
# _LINEAGE_COLORS para nao duplicar a fonte de cor do rendering.
_COLOR_BY_ID: dict[str, tuple[int, int, int]] = {
    lineage["id"]: _LINEAGE_COLORS[i] for i, lineage in enumerate(cfg.LINEAGES)
}
_SCALAR_COLOR: tuple[int, int, int] = (220, 220, 220)

# Indicador de gravacao (desenhado no HUD quando gravando).
_RECORDING_COLOR: tuple[int, int, int] = (255, 64, 64)


# Formatacao do cabecalho da tabela de linhagens.
#
# Precisa ser funcao, nao constante: i18n.t() le state.language em
# runtime, entao congelar a string no import de rendering.py deixaria
# o cabecalho preso ao idioma do boot mesmo apos T / painel Tools.
def _lineage_header_text() -> str:
    return (
        f"{i18n.t('col.id'):>2}  "
        f"{i18n.t('col.hp'):>6}  "
        f"{i18n.t('col.lt'):>5}  "
        f"{i18n.t('col.gen'):>4}  "
        f"{i18n.t('col.pop'):>4}  "
        f"{i18n.t('col.score'):>6}"
    )


_LINEAGE_TABLE_ROW_FMT = "{id:>2}  {hp:6.0f}  {lt:5d}  {gen:4d}  {pop:4d}  {score:6.2f}"


# Modelo semantico dos atalhos do Command Dock. Dados puros: cada
# grupo tem chave i18n do rotulo e uma tupla de (keycap, chave i18n
# da acao). O rendering nao parseia string nenhuma.
_COMMAND_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "command.group.simulation",
        (
            ("SPACE", "command.pause"),
            ("=", "command.step"),
            ("R", "command.new_world"),
            ("F11", "command.fullscreen"),
            ("ESC", "command.back_quit"),
        ),
    ),
    (
        "command.group.panels",
        (
            ("I", "command.inspect"),
            ("C", "command.configuration"),
            ("M", "command.metrics"),
            ("S", "command.session"),
            ("T", "command.tools"),
        ),
    ),
    (
        "command.group.navigation",
        (
            ("↑↓", "command.select"),
            ("←→", "command.change"),
            ("TAB", "command.panel"),
            ("ENTER", "command.activate"),
            ("LMB", "command.observe"),
        ),
    ),
    (
        "command.group.quick",
        (
            ("H", "command.hide_hud"),
            ("Ctrl+S", "command.save"),
            ("Ctrl+L", "command.load"),
            ("N", "command.slot"),
            ("Z", "command.zones"),
            ("G", "command.record"),
        ),
    ),
)


def _heatmap_color(value: float) -> tuple[int, int, int]:
    """Mapeia um peso em [-HEATMAP_LIMIT, +HEATMAP_LIMIT] para cor.

    Convencao: negativo -> azul; zero -> preto; positivo -> vermelho.
    Valores fora do limite sao saturados.
    """
    limit = cfg.HEATMAP_LIMIT
    t = max(-1.0, min(1.0, value / limit))

    if t >= 0.0:
        # black → red
        r = int(255 * t)
        return (r, 0, 0)
    else:
        # black → blue
        b = int(255 * (-t))
        return (0, 0, b)


def _draw_heatmap(
    surface: pygame.Surface,
    weights: np.ndarray,
    x0: int,
    y0: int,
    width: int,
    height: int,
    title: str,
) -> int:
    """Desenha um vetor de pesos como heatmap horizontal.

    Retorna o Y logo abaixo do bloco desenhado.

    NOTE: desenha linhas verticais de 1 px coluna a coluna, inerente
    a API immediate-mode do pygame. Se virar gargalo, o bloco inteiro
    poderia ser construido como array [width, height, 3] uint8 e
    blitado com pygame.surfarray.blit_array, mas isso mudaria o
    pipeline de desenho por um nao-bug. Deixado como esta.
    """
    g = weights.shape[0]
    if g == 0 or width <= 0:
        return y0

    # Cada gene vira uma coluna de 1 px; com mais genes que pixels,
    # agrupa pela media. Com menos, estica.
    if g <= width:
        step = max(1, width // g)
        sample = np.repeat(weights, step)
    else:
        step = g // width
        sample = weights[: step * width].reshape(width, step).mean(axis=1)

    for i, v in enumerate(sample):
        color = _heatmap_color(float(v))
        pygame.draw.line(surface, color, (x0 + i, y0), (x0 + i, y0 + height - 1))

    pygame.draw.rect(surface, cfg.PANEL_BORDER_COLOR, (x0, y0, width, height), 1)

    label = _font_panel_small.render(title, True, cfg.PANEL_SECONDARY_TEXT_COLOR)
    surface.blit(label, (x0, y0 + height + 2))

    return y0 + height + 2 + label.get_height() + 6


def _render_vision_array(critter_matrix: np.ndarray) -> np.ndarray:
    """Constroi a imagem [SIDE, SIDE, 3] uint8 da visao do bicho.

    Usa as mesmas coordenadas toroidais e a mesma composicao "max por
    canal" da imagem principal do mundo (_build_image), entao o
    painel mostra exatamente o que a rede ve.
    """
    side = cfg.VISION_SIDE

    x = int(critter_matrix[INDEX_X])
    y = int(critter_matrix[INDEX_Y])

    offsets = np.arange(-cfg.VISION_RADIUS, cfg.VISION_RADIUS + 1)
    xs = (x + offsets) % layout.LAYOUT.world_width
    ys = (y + offsets) % layout.LAYOUT.world_height

    # [SIDE, SIDE, 3] com max-por-canal vetorizado, mesma regra de
    # _build_image. Itera sobre as (ate 3) linhagens, nao sobre 121
    # celulas x 3 linhagens como a implementacao anterior.
    vision = np.zeros((side, side, 3), dtype=np.uint8)
    for ag in agents:
        # field[xs[:, None], ys[None, :]] -> [SIDE, SIDE]
        density = ag["field"][xs[:, None], ys[None, :]]
        mask = density > 0
        if not mask.any():
            continue
        for channel, value in enumerate(ag["color"]):
            if value == 0:
                continue
            channel_img = vision[..., channel]
            channel_img[mask] = np.maximum(channel_img[mask], value)

    return vision


def _draw_vision(
    surface: pygame.Surface,
    critter_matrix: np.ndarray,
    x0: int,
    y0: int,
) -> int:
    """Desenha a janela de visao 11x11 do bicho selecionado.

    Retorna o Y abaixo do bloco.
    """
    side = cfg.VISION_SIDE
    size = cfg.INSPECTION_CELL_HEIGHT

    vision = _render_vision_array(critter_matrix)

    # Blita cada celula. Loop sobre SIDE x SIDE = 121 celulas, barato;
    # o indexing caro por linhagem esta vetorizado.
    for i in range(side):
        for j in range(side):
            r, g, b = vision[i, j]
            px = x0 + i * size
            py = y0 + j * size
            pygame.draw.rect(
                surface, (int(r), int(g), int(b)), (px, py, size - 1, size - 1)
            )

    # Contorno da celula central.
    center = cfg.VISION_RADIUS * size
    pygame.draw.rect(
        surface,
        cfg.INSPECTION_HIGHLIGHT_COLOR,
        (x0 + center, y0 + center, size - 1, size - 1),
        1,
    )

    label = _font_panel_small.render(
        i18n.t(
            "panel.vision_title",
            x=int(critter_matrix[INDEX_X]),
            y=int(critter_matrix[INDEX_Y]),
        ),
        True,
        cfg.PANEL_SECONDARY_TEXT_COLOR,
    )
    surface.blit(label, (x0, y0 + side * size + 2))

    return y0 + side * size + 2 + label.get_height() + 6


@dataclass(frozen=True, slots=True)
class _InspectionSubject:
    """Sujeito da Observation resolvido para desenho.

    Cobre os dois casos (vivo, snapshot de morte) sem que o caller
    precise saber de onde os dados vieram. `alive=False` implica
    `death_tick` preenchido e `agent_row`/`genome` vindos do
    snapshot.
    """

    critter_id: int
    lineage_id: str
    lineage_color: tuple[int, int, int]
    agent_row: np.ndarray
    genome: np.ndarray
    alive: bool
    death_tick: int | None


def _resolve_inspection_subject() -> _InspectionSubject | None:
    """Resolve o bicho observado (vivo ou snapshot) para desenho.

    Retorna None se:
      - nao ha selection;
      - a selection nao resolve (ID sumiu sem snapshot);
      - o snapshot existe mas o lineage_id nao esta na config atual.
    """
    critter_id = state.inspected_critter_id
    if critter_id is None:
        return None

    snapshot = state.inspection_death_snapshot
    if snapshot is not None:
        lineage_color = _COLOR_BY_ID.get(snapshot.lineage_id, cfg.PANEL_TEXT_COLOR)
        return _InspectionSubject(
            critter_id=int(snapshot.critter_id),
            lineage_id=str(snapshot.lineage_id),
            lineage_color=lineage_color,
            agent_row=snapshot.agent,
            genome=snapshot.genome,
            alive=False,
            death_tick=int(snapshot.tick),
        )

    from .world import resolve_critter_id

    resolved = resolve_critter_id(critter_id)
    if resolved is None:
        return None

    li, ai = resolved
    lineage_id = str(agents[li]["id"])
    lineage_color = agents[li]["color"]
    agent_row = agents[li]["agents"][ai]
    genome = agents[li]["pool"][ai]
    return _InspectionSubject(
        critter_id=int(critter_id),
        lineage_id=lineage_id,
        lineage_color=lineage_color,
        agent_row=agent_row,
        genome=genome,
        alive=True,
        death_tick=None,
    )


def _draw_discovery_candidate_card(x0: int, y0: int, width: int) -> int:
    """Desenha o card do candidato atual de Discovery.

    Retorna o Y logo abaixo do card (para o caller medir
    content_height). Se nao ha candidato, retorna y0 + uma linha de
    aviso; o layout nao colapsa.

    Conteudo:
        Cabecalho "CANDIDATO"
        Linha principal: #ID  <lineage_id>
        Valor relevante ao criterio atual (rotulado)
        Hint "Enter observar"

    O valor exibido vem de world.discovery_criterion_value(), que
    retorna o valor HUMANO (sem inversao de sinal). O ranking interno
    usa a versao negada para youngest/lowest_hp; a UI nao.

    Reutiliza world.discovery_candidate() (autoridade do candidato),
    garantindo que o card mostra exatamente o bicho que Enter
    observaria. Recalculo por frame: O(N) por linhagem, aceitavel.
    """
    padding = 10
    border_color = cfg.INSPECTION_HIGHLIGHT_COLOR
    header_color = cfg.PANEL_SECONDARY_TEXT_COLOR
    body_color = cfg.PANEL_TEXT_COLOR
    inner_w = width - 2 * padding

    header = _font_panel_small.render(
        i18n.t("panel.discovery_title"), True, header_color
    )
    _screen.blit(header, (x0 + padding, y0))
    y = y0 + header.get_height() + 4

    candidate = world.discovery_candidate(
        state.discovery_criterion,
        state.discovery_lineage_filter,
    )

    # Tamanho do card: 4 linhas de texto + hint.
    card_line_h = _font_panel.get_height()
    card_h = 4 * card_line_h + 8

    # Fundo + borda.
    pygame.draw.rect(_screen, cfg.HUD_KEY_BG_COLOR, (x0 + padding, y, inner_w, card_h))
    pygame.draw.rect(_screen, border_color, (x0 + padding, y, inner_w, card_h), 1)

    cy = y + 4

    if candidate is None:
        msg = _font_panel.render(i18n.t("panel.no_candidate"), True, body_color)
        _screen.blit(msg, (x0 + padding + 6, cy))
        return y + card_h + 6

    li, ai = candidate
    agent = agents[li]
    row = agent["agents"][ai]
    stable_id = int(agent["ids"][ai])
    lineage_color = agent["color"]

    # Linha 1: #ID + lineage_id.
    line1 = _font_panel.render(f"#{stable_id}  {agent['id']}", True, lineage_color)
    _screen.blit(line1, (x0 + padding + 6, cy))
    cy += card_line_h

    # Linha 2: valor do criterio (rotulo + valor humano).
    criterion_label = i18n.t(f"criterion.{state.discovery_criterion}")
    value = discovery_criterion_value(state.discovery_criterion, row)
    line2 = _font_panel_small.render(
        f"{criterion_label}: {value:.0f}", True, body_color
    )
    _screen.blit(line2, (x0 + padding + 6, cy))
    cy += card_line_h

    # Linha 3: hint.
    hint = _font_panel_small.render(i18n.t("panel.enter_hint"), True, header_color)
    _screen.blit(hint, (x0 + padding + 6, cy))

    return y + card_h + 6


def _draw_inspection_details(
    surface: pygame.Surface,
    x0: int,
    y0: int,
    width: int,
) -> int:
    """Desenha o detalhe do bicho observado.

    Retorna o Y logo abaixo do bloco. O viewport usa isso para
    calcular a altura real do conteudo e o clamp do scroll.

    Sem selection (ou selection irresoluvel): retorna y0 sem desenhar.
    Morto: mostra dados finais + heatmaps; nao reconstroi vision.
    """
    padding = 10
    y = y0 + padding

    subject = _resolve_inspection_subject()
    if subject is None:
        return y0

    row = subject.agent_row

    # identity / life data
    line_color = subject.lineage_color
    id_line = _font_panel.render(
        f"#{subject.critter_id}  {subject.lineage_id}",
        True,
        line_color,
    )
    surface.blit(id_line, (x0 + padding, y))
    y += id_line.get_height() + 4

    if subject.alive:
        status_text = i18n.t("panel.status_alive")
    else:
        status_text = i18n.t("panel.status_dead", tick=subject.death_tick)
    status_surface = _font_panel_small.render(
        f"{i18n.t('panel.status')} {status_text}",
        True,
        cfg.PANEL_SECONDARY_TEXT_COLOR,
    )
    surface.blit(status_surface, (x0 + padding, y))
    y += status_surface.get_height() + 6

    for label_key, value in (
        ("panel.hp", f"{int(row[INDEX_HP])}"),
        ("panel.time", f"{int(row[INDEX_TIME])}"),
        ("panel.generation", f"{int(row[INDEX_GENERATION])}"),
        ("panel.offspring", f"{int(row[INDEX_OFFSPRING])}"),
        ("panel.encounters", f"{int(row[INDEX_ENCOUNTERS])}"),
        ("panel.score", f"{float(row[INDEX_COMPOSITE_SCORE]):.3f}"),
        ("panel.last_action", f"{int(row[INDEX_LAST_ACTION])}"),
        ("panel.position", f"{int(row[INDEX_X])},{int(row[INDEX_Y])}"),
    ):
        text = _font_panel_small.render(
            f"{i18n.t(label_key)} {value}",
            True,
            cfg.PANEL_TEXT_COLOR,
        )
        surface.blit(text, (x0 + padding, y))
        y += text.get_height() + 2

    y += 6

    # vision: so para vivo. Morto nao inventa historico.
    if subject.alive:
        y = _draw_vision(surface, subject.agent_row, x0 + padding, y)
    else:
        note = _font_panel_small.render(
            i18n.t("panel.vision_unavailable_dead"),
            True,
            cfg.PANEL_SECONDARY_TEXT_COLOR,
        )
        surface.blit(note, (x0 + padding, y))
        y += note.get_height() + 6

    # brain heatmaps: sempre que houver genome (vivo ou snapshot).
    from .brain import split_weights

    w1, w2, w3, b1, b2, r = split_weights(subject.genome)
    heatmap_w = max(40, width - 2 * padding)
    heatmap_h = 24

    for title_key, weights in (
        ("heatmap.w1", w1),
        ("heatmap.w2", w2),
        ("heatmap.w3", w3),
        ("heatmap.b1", b1),
        ("heatmap.b2", b2),
        ("heatmap.r", r),
    ):
        y = _draw_heatmap(
            surface,
            np.asarray(weights).reshape(-1),
            x0 + padding,
            y,
            heatmap_w,
            heatmap_h,
            i18n.t(title_key),
        )

    return y


# --- Lateral unica: abas + viewport + resumo + footer -----------------


# Ordem canonica das abas. Espelha ui_state.ALL_PANELS menos world.
_TAB_ORDER: tuple[str, ...] = (
    ui_state.PANEL_INSPECTION,
    ui_state.PANEL_CONFIGURATION,
    ui_state.PANEL_METRICS,
    ui_state.PANEL_SESSION,
    ui_state.PANEL_TOOLS,
)


# Chave de ativacao exibida em cada aba. Espelha panels.PANELS por
# panel.id; mantido aqui para o rendering nao depender do registry.
_TAB_KEYS: dict[str, str] = {
    ui_state.PANEL_INSPECTION: "I",
    ui_state.PANEL_CONFIGURATION: "C",
    ui_state.PANEL_METRICS: "M",
    ui_state.PANEL_SESSION: "S",
    ui_state.PANEL_TOOLS: "T",
}


# Geometria canonica das tabs. Unica autoridade: draw e hit-test
# derivam daqui, entao a regiao clicavel e exatamente a regiao
# desenhada. Ajustes de padding/gap sao feitos apenas nesta funcao.
_TAB_PADDING = 8
_TAB_GAP = 4
_TAB_TOP = 4
_TAB_BOTTOM_MARGIN = 8


def _tab_rects(x0: int, y0: int, width: int, height: int) -> dict[str, pygame.Rect]:
    """Retorna os Rects canonicos de cada tab da sidebar.

    x0/y0/width/height descrevem a area da tab bar (nao da sidebar
    inteira). Ordem e _TAB_ORDER. Chaves sao panel_id.
    """
    n = len(_TAB_ORDER)
    tab_w = (width - 2 * _TAB_PADDING - (n - 1) * _TAB_GAP) // n
    tab_h = height - _TAB_BOTTOM_MARGIN

    rects: dict[str, pygame.Rect] = {}
    for i, panel_id in enumerate(_TAB_ORDER):
        tx = x0 + _TAB_PADDING + i * (tab_w + _TAB_GAP)
        ty = y0 + _TAB_TOP
        rects[panel_id] = pygame.Rect(tx, ty, tab_w, tab_h)
    return rects


def panel_tab_at(pos: tuple[int, int]) -> str | None:
    """Hit-test das tabs da sidebar.

    Retorna o panel_id da tab sob `pos`, ou None se pos nao esta sobre
    nenhuma tab. Coordenadas em screen-space, correspondendo ao mesmo
    layout usado por _draw_lateral_panel().

    Usa screen.get_size() da _screen efetiva: em fullscreen/resize o
    tamanho real da janela e a autoridade, nao o LAYOUT base.
    """
    if _screen is None:
        return None
    screen_w, screen_h = _screen.get_size()
    x0 = screen_w - cfg.INSPECTION_PANEL_WIDTH
    # A tab bar ocupa os primeiros TAB_H pixels da lateral. Repetimos
    # a constante local de _draw_lateral_panel; se ela mudar, os dois
    # pontos precisam mudar juntos. Alternativa mais robusta seria
    # exportar TAB_H como constante do modulo; feito abaixo.
    rects = _tab_rects(x0, 0, cfg.INSPECTION_PANEL_WIDTH, _TAB_BAR_HEIGHT)
    for panel_id, rect in rects.items():
        if rect.collidepoint(pos):
            return panel_id
    return None


# Altura da tab bar. Compartilhada entre _draw_lateral_panel (layout
# vertical) e panel_tab_at (hit-test). Unica fonte de verdade.
_TAB_BAR_HEIGHT = 32


def _draw_tab_bar(x0: int, y0: int, width: int, height: int) -> None:
    """Desenha a barra de abas no topo da lateral.

    A aba do painel focado tem destaque forte; a aba do last_panel
    (quando active_panel == world) tem destaque suave; as demais sao
    neutras.

    Geometria vem integralmente de _tab_rects(): a regiao clicavel
    (panel_tab_at) e exatamente a regiao desenhada.
    """
    focused = ui_state.active_panel
    last = ui_state.last_panel

    pygame.draw.rect(_screen, cfg.HUD_BG_COLOR, (x0, y0, width, height))
    pygame.draw.line(
        _screen,
        cfg.PANEL_BORDER_COLOR,
        (x0, y0 + height - 1),
        (x0 + width, y0 + height - 1),
        1,
    )

    for panel_id, rect in _tab_rects(x0, y0, width, height).items():
        if panel_id == focused:
            bg = cfg.INSPECTION_HIGHLIGHT_COLOR
            fg = (0, 0, 0)
            bold = True
            underline = True
        elif panel_id == last and focused == ui_state.PANEL_WORLD:
            bg = cfg.HUD_BORDER_COLOR
            fg = cfg.HUD_TEXT_COLOR
            bold = False
            underline = True
        else:
            bg = cfg.HUD_BG_COLOR
            fg = cfg.HUD_TEXT_SECONDARY_COLOR
            bold = False
            underline = False

        pygame.draw.rect(_screen, bg, rect)
        pygame.draw.rect(_screen, cfg.PANEL_BORDER_COLOR, rect, 1)

        key = _TAB_KEYS[panel_id]
        font = _font_panel_title if bold else _font_panel
        label = font.render(key, True, fg)
        lx = rect.x + (rect.width - label.get_width()) // 2
        ly = rect.y + (rect.height - label.get_height()) // 2
        _screen.blit(label, (lx, ly))

        if underline:
            pygame.draw.line(
                _screen,
                fg,
                (rect.x + 2, rect.bottom - 2),
                (rect.right - 3, rect.bottom - 2),
                2,
            )


def _notice_text_color(kind: str) -> tuple[int, int, int]:
    """Cor do texto da notice por kind."""
    if kind == ui_state.NOTICE_SUCCESS:
        return (128, 220, 128)
    if kind == ui_state.NOTICE_ERROR:
        return (240, 120, 120)
    return cfg.HUD_TEXT_COLOR


def _draw_panel_footer(
    x0: int, y0: int, width: int, height: int, panel_id: str
) -> None:
    """Desenha o rodape da sidebar.

    Regra:
      - notice ativa   -> mostra a notice (com cor por kind);
      - notice ausente -> mostra o rodape contextual do painel.

    A notice e tempo de interface: quem expira e ui_state via
    expire_notice_if_needed(), chamado pelo loop grafico. Aqui so
    renderizamos o estado corrente.
    """
    pygame.draw.rect(_screen, cfg.HUD_BG_COLOR, (x0, y0, width, height))
    pygame.draw.line(
        _screen,
        cfg.PANEL_BORDER_COLOR,
        (x0, y0),
        (x0 + width, y0),
        1,
    )

    if ui_state.notice is not None:
        color = _notice_text_color(ui_state.notice.kind)
        text = _font_panel_small.render(ui_state.notice.message, True, color)
        _screen.blit(text, (x0 + 8, y0 + (height - text.get_height()) // 2))
        return

    panel = panels.PANELS.get(panel_id)
    footer_key = panel.footer_key if panel is not None else None
    if footer_key is None:
        footer_key = "panel.hint_actions"

    text = _font_panel_small.render(
        i18n.t(footer_key), True, cfg.HUD_TEXT_SECONDARY_COLOR
    )
    _screen.blit(text, (x0 + 8, y0 + (height - text.get_height()) // 2))


def _draw_inspection_summary(x0: int, y0: int, width: int, height: int) -> None:
    """Resumo compacto do bicho observado, sempre visivel.

    Mostra: ID, linhagem, status, HP, idade, geracao. Se nao ha
    observado, mostra "nenhum bicho observado".

    Se o bicho observado morreu, le do snapshot. Se vivo, resolve o
    ID no estado atual. Se o ID sumiu sem snapshot (estado invalido),
    mostra aviso.
    """
    pygame.draw.rect(_screen, cfg.PANEL_BG_COLOR, (x0, y0, width, height))
    pygame.draw.line(
        _screen,
        cfg.PANEL_BORDER_COLOR,
        (x0, y0),
        (x0 + width, y0),
        1,
    )

    padding = 8
    y = y0 + padding

    title = _font_panel_small.render(
        i18n.t("panel.observation_title"), True, cfg.PANEL_SECONDARY_TEXT_COLOR
    )
    _screen.blit(title, (x0 + padding, y))
    y += title.get_height() + 2

    if state.inspected_critter_id is None:
        text = _font_panel.render(
            i18n.t("panel.no_selection"), True, cfg.PANEL_TEXT_COLOR
        )
        _screen.blit(text, (x0 + padding, y))
        return

    subject = _resolve_inspection_subject()
    if subject is None:
        text = _font_panel.render(
            i18n.t("panel.stale_selection"), True, cfg.PANEL_TEXT_COLOR
        )
        _screen.blit(text, (x0 + padding, y))
        return

    row = subject.agent_row
    if subject.alive:
        status = i18n.t("panel.status_alive")
    else:
        status = i18n.t("panel.status_dead", tick=subject.death_tick)

    # Linha 1: id + linhagem + status.
    line1 = _font_panel.render(
        f"#{subject.critter_id}  {subject.lineage_id}  {status}",
        True,
        subject.lineage_color,
    )
    _screen.blit(line1, (x0 + padding, y))
    y += line1.get_height() + 2

    # Linha 2: hp / tempo / geracao.
    line2 = _font_panel_small.render(
        f"{i18n.t('panel.hp')} {int(row[INDEX_HP])}  "
        f"{i18n.t('panel.time')} {int(row[INDEX_TIME])}  "
        f"{i18n.t('panel.generation')} {int(row[INDEX_GENERATION])}",
        True,
        cfg.PANEL_TEXT_COLOR,
    )
    _screen.blit(line2, (x0 + padding, y))


def _draw_panel_viewport(
    x0: int, y0: int, width: int, height: int, panel_id: str
) -> None:
    """Desenha o conteudo do painel `panel_id` na area dada.

    Clip + scroll: o conteudo e clipado ao retangulo do viewport e o
    scroll_offset vertical e aplicado. Se o conteudo couber inteiro,
    o offset e forcado a 0; caso contrario e clampado em
    [0, content_height - height].

    Le os itens do Panel via registry e desenha cada um conforme o
    kind. O cursor e destacado com "> " quando o painel esta focado;
    quando active_panel == world, nenhum cursor e desenhado.

    Quando panel_id == PANEL_INSPECTION, apos os itens genericos o
    conteudo rico do bicho observado e desenhado por
    _draw_inspection_details.
    """
    panel = panels.PANELS.get(panel_id)
    if panel is None:
        return

    focused = ui_state.active_panel == panel_id
    cursor_id = ui_state.panel_cursors.get(panel_id) if focused else None

    scroll_offset = ui_state.panel_scroll_offsets.get(panel_id, 0)

    # --- Layout do conteudo em espaco virtual (sem scroll) ---
    #
    # Desenhamos primeiro com y virtual, medindo o fim real. Depois
    # recalculamos scroll e re-desenhamos com o offset aplicado. Para
    # nao duplicar, mantemos as duas passadas num helper local.
    padding = 10

    def _render_items(y_start: int) -> int:
        y = y_start
        title = _font_panel_title.render(
            i18n.t(panel.title_key), True, cfg.PANEL_TEXT_COLOR
        )
        _screen.blit(title, (x0 + padding, y))
        y += title.get_height() + 8

        for item in panel.items:
            if item.kind is panels.ItemKind.SECTION:
                label = _font_panel_small.render(
                    i18n.t(item.label_key),
                    True,
                    cfg.PANEL_SECONDARY_TEXT_COLOR,
                )
                _screen.blit(label, (x0 + padding, y))
                y += label.get_height() + 4
                continue

            marker = "> " if (focused and item.id == cursor_id) else "  "
            marker_color = (
                cfg.INSPECTION_HIGHLIGHT_COLOR
                if (focused and item.id == cursor_id)
                else cfg.PANEL_TEXT_COLOR
            )

            label_text = i18n.t(item.label_key)
            value_text = item.value_fn() if item.value_fn is not None else ""

            label_surface = _font_panel.render(marker + label_text, True, marker_color)
            _screen.blit(label_surface, (x0 + padding, y))

            if value_text:
                value_surface = _font_panel.render(
                    value_text, True, cfg.PANEL_TEXT_COLOR
                )
                vx = x0 + width - padding - value_surface.get_width()
                _screen.blit(value_surface, (vx, y))

            y += label_surface.get_height() + 2

        return y

    # --- Passada 1: medir ---
    #
    # Desenha normalmente; o resultado e sobrescrito pela passada 2 se
    # houver scroll. O custo de duas passadas so existe enquanto o
    # viewport nao tiver medicao pura (sem blit). Aceitavel: sao ~20
    # linhas por painel.
    end_y = _render_items(y0 + padding - scroll_offset)

    if panel_id == ui_state.PANEL_INSPECTION:
        end_y = _draw_discovery_candidate_card(x0, end_y, width)
        end_y = _draw_inspection_details(_screen, x0, end_y, width)
    elif panel_id == ui_state.PANEL_METRICS:
        end_y = _draw_metrics_dashboard(x0, end_y, width, height)

    content_height = max(0, end_y - y0)

    # --- Clamp do scroll ---
    if content_height <= height:
        scroll_offset = 0
    else:
        scroll_offset = max(0, min(scroll_offset, content_height - height))
    ui_state.panel_scroll_offsets[panel_id] = scroll_offset

    # --- Passada 2 (somente se scroll != 0) ---
    #
    # Sem scroll, a passada 1 ja esta correta; nao redesenha. Com
    # scroll, limpa o viewport e redesenha com o offset final.
    if scroll_offset != 0:
        old_clip = _screen.get_clip()
        _screen.set_clip(pygame.Rect(x0, y0, width, height))
        _screen.fill(cfg.PANEL_BG_COLOR, (x0, y0, width, height))

        end_y2 = _render_items(y0 + padding - scroll_offset)
        if panel_id == ui_state.PANEL_INSPECTION:
            end_y2 = _draw_discovery_candidate_card(x0, end_y2, width)
            _draw_inspection_details(_screen, x0, end_y2, width)
        elif panel_id == ui_state.PANEL_METRICS:
            _draw_metrics_dashboard(x0, end_y2, width, height)

        _screen.set_clip(old_clip)


def _draw_lateral_panel() -> None:
    """Desenha a lateral unica: abas + viewport + resumo + footer.

    A largura e fixa (INSPECTION_PANEL_WIDTH). O painel visivel e:
      - ui_state.active_panel, se nao for "world";
      - ui_state.last_panel, caso contrario (sem foco).

    Coordenadas screen-space derivam da _screen efetiva, nao do
    layout base: em fullscreen/resize, layout.LAYOUT.window_* nao
    reflete o tamanho atual da janela.
    """
    width = cfg.INSPECTION_PANEL_WIDTH
    screen_w, screen_h = _screen.get_size()
    x0 = screen_w - width

    # Fundo geral.
    background = pygame.Surface((width, screen_h), pygame.SRCALPHA)
    background.fill((*cfg.PANEL_BG_COLOR, 235))
    _screen.blit(background, (x0, 0))
    pygame.draw.line(
        _screen,
        cfg.PANEL_BORDER_COLOR,
        (x0, 0),
        (x0, screen_h),
        1,
    )

    # Layout vertical:
    #   tab bar      (32 px)
    #   viewport     (resto - summary_h - footer_h)
    #   summary      (56 px)
    #   footer       (24 px)
    TAB_H = _TAB_BAR_HEIGHT
    SUMMARY_H = 56
    FOOTER_H = 24
    viewport_y = TAB_H
    viewport_h = screen_h - TAB_H - SUMMARY_H - FOOTER_H
    summary_y = viewport_y + viewport_h
    footer_y = summary_y + SUMMARY_H

    _draw_tab_bar(x0, 0, width, TAB_H)

    # Painel efetivamente desenhado.
    panel_id = (
        ui_state.active_panel
        if ui_state.active_panel != ui_state.PANEL_WORLD
        else ui_state.last_panel
    )

    # Viewport clipado: nada dentro dele escapa para summary/footer/
    # tab bar nem para o mundo. O clip e restaurado em qualquer
    # caminho de saida.
    old_clip = _screen.get_clip()
    _screen.set_clip(pygame.Rect(x0, viewport_y, width, viewport_h))
    try:
        _draw_panel_viewport(x0, viewport_y, width, viewport_h, panel_id)
    finally:
        _screen.set_clip(old_clip)

    _draw_inspection_summary(x0, summary_y, width, SUMMARY_H)
    _draw_panel_footer(x0, footer_y, width, FOOTER_H, panel_id)


def init() -> None:
    global _screen, _clock, _font, _font_hud_title
    global _font_chart, _font_chart_title, _font_tip
    global _font_panel, _font_panel_title, _font_panel_small
    pygame.init()
    pygame.font.init()
    _screen = pygame.display.set_mode(
        (
            layout.LAYOUT.window_width,
            layout.LAYOUT.window_height,
        ),
        pygame.RESIZABLE,
    )
    pygame.display.set_caption(cfg.WINDOW_TITLE)

    # Icone da janela e do brand do HUD. Carregado uma unica vez;
    # a Surface original alimenta display.set_icon(), a versao
    # reduzida alimenta _draw_telemetry_brand(). Falha e nao-fatal:
    # o icone e cosmetico e o HUD degrada para so texto.
    global _hud_icon
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    try:
        original = pygame.image.load(icon_path)
        pygame.display.set_icon(original)
        _hud_icon = pygame.transform.smoothscale(original, (18, 18))
    except (pygame.error, FileNotFoundError) as e:
        _hud_icon = None
        print(f"[icon] falha ao carregar {icon_path}: {e!r}")

    _clock = pygame.time.Clock()
    _font = pygame.font.SysFont(*cfg.HUD_FONT)
    _font_hud_title = pygame.font.SysFont("monospace", 15, True)
    _font_chart = pygame.font.SysFont("monospace", 12, False)
    _font_chart_title = pygame.font.SysFont("monospace", 13, True)
    _font_tip = pygame.font.SysFont("monospace", 13, True)
    _font_panel = pygame.font.SysFont("monospace", 14, False)
    _font_panel_title = pygame.font.SysFont("monospace", 18, True)
    _font_panel_small = pygame.font.SysFont("monospace", 11, False)

    # Sincroniza _viewport_rect com a screen efetiva. Em modo janela
    # isso coincide com o valor default de _viewport_rect, mas em
    # ambientes que alteram a resolucao inicial (HiDPI, WMs que
    # arredondam) a screen real e a autoridade. Tambem dispara o
    # _clamp_camera() inicial.
    _recompute_viewport(*_screen.get_size())


def _world_viewport_rect() -> pygame.Rect:
    """Copia do retangulo fisico do mundo na tela.

    Retorna copia (nao referencia) para impedir que chamadores
    externos mutem _viewport_rect por acidente. Nao recalcula nada:
    a geometria e atualizada somente por _recompute_viewport().
    """
    return _viewport_rect.copy()


def _recompute_viewport(width: int, height: int) -> None:
    """Recalcula o retangulo fisico onde o mundo e desenhado.

    A largura UTIL e (width - INSPECTION_PANEL_WIDTH): o painel tem
    faixa cativa a direita e o mundo nao pode invadir. O retangulo e
    a maior area que preserva a proporcao do mundo dentro do espaco
    util, centralizada em ambos os eixos.

    NAO toca a camera: zoom/view_x/view_y sao estado de apresentacao
    independente do tamanho fisico da janela. Apos recalcular, a
    camera e revalidada para a nova geometria (clamp defensivo).

    Nao usa MIN_ZOOM/MAX_ZOOM: essas constantes regem a camera, nao o
    encaixe do mundo na tela.
    """
    global _viewport_rect

    usable_w = width - cfg.INSPECTION_PANEL_WIDTH
    base_w = layout.LAYOUT.world_width * layout.LAYOUT.pixel_scale
    base_h = layout.LAYOUT.world_height * layout.LAYOUT.pixel_scale

    fit_scale = min(usable_w / base_w, height / base_h)

    target_w = int(base_w * fit_scale)
    target_h = int(base_h * fit_scale)

    offset_x = (usable_w - target_w) // 2
    offset_y = (height - target_h) // 2

    _viewport_rect = pygame.Rect(
        offset_x,
        offset_y,
        target_w,
        target_h,
    )

    _clamp_camera()


def on_resize(width: int, height: int) -> None:
    """VIDEORESIZE muda apenas o viewport fisico.

    O mundo logico e a camera NAO sao rederivados: o zoom vigente e
    preservado, bem como view_x/view_y (sujeitos a clamp defensivo
    caso a nova area torne a view anterior impossivel). Nao chama
    set_mode(): o Pygame ja redimensionou a display Surface quando
    VIDEORESIZE dispara.
    """
    _recompute_viewport(width, height)


def _camera_view_size() -> tuple[float, float]:
    """Tamanho da view logica visivel, em celulas do mundo.

    Em 1x, e o mundo inteiro. Em 8x, um oitavo em cada eixo. Retorna
    floats, sem arredondamento.
    """
    return (
        layout.LAYOUT.world_width / _camera.zoom,
        layout.LAYOUT.world_height / _camera.zoom,
    )


def _clamp_camera() -> None:
    """Revalida zoom e origem da view contra o mundo logico.

    Ordem canonica:
      1. clamp do zoom em [MIN_ZOOM, MAX_ZOOM];
      2. derive view_w/view_h da view;
      3. derive max_x/max_y de deslocamento;
      4. clamp de view_x/view_y em [0, max].

    Nao quantiza view_x/view_y: a camera permanece float. A
    discretizacao e responsabilidade do raster crop.
    """
    _camera.zoom = max(
        cfg.MIN_ZOOM,
        min(_camera.zoom, cfg.MAX_ZOOM),
    )

    view_w, view_h = _camera_view_size()

    max_x = max(0.0, layout.LAYOUT.world_width - view_w)
    max_y = max(0.0, layout.LAYOUT.world_height - view_h)

    _camera.view_x = max(0.0, min(_camera.view_x, max_x))
    _camera.view_y = max(0.0, min(_camera.view_y, max_y))


def _screen_to_world_float(
    pos: tuple[int, int],
) -> tuple[float, float] | None:
    """Transformacao canonica screen -> world (float).

    Retorna None se pos cair fora do viewport fisico do mundo (isto
    inclui a sidebar, o letterbox e qualquer outro espaco de tela).

    A conversao passa por:
      screen pixel -> coordenada normalizada do viewport
                   -> offset na view logica da camera
                   -> coordenada logica do mundo.

    Nao usa PIXEL_SCALE nem source crop: esses pertencem ao raster,
    nao a interacao. Nao converte para int.
    """
    sx, sy = pos
    viewport = _viewport_rect

    if viewport.width <= 0 or viewport.height <= 0:
        return None

    if not viewport.collidepoint(sx, sy):
        return None

    u = (sx - viewport.left) / viewport.width
    v = (sy - viewport.top) / viewport.height

    view_w, view_h = _camera_view_size()

    world_x = _camera.view_x + u * view_w
    world_y = _camera.view_y + v * view_h

    return world_x, world_y


def screen_to_world(pos: tuple[int, int]) -> tuple[int, int] | None:
    """Converte posicao de tela para coordenada logica do mundo.

    Delega para _screen_to_world_float() e converte para int. Nao faz
    clamp silencioso: se a coordenada inteira cair fora do mundo, o
    resultado e None (o chamador decide o que fazer).

    Mantida como API publica: consumidores existentes (adapter de
    mouse em simulation.run) continuam usando este nome.
    """
    world_pos = _screen_to_world_float(pos)
    if world_pos is None:
        return None

    world_x = int(world_pos[0])
    world_y = int(world_pos[1])

    if not (
        0 <= world_x < layout.LAYOUT.world_width
        and 0 <= world_y < layout.LAYOUT.world_height
    ):
        return None

    return world_x, world_y


def apply_zoom_at(
    screen_pos: tuple[int, int],
    notches: int,
) -> bool:
    """Aplica zoom ancorado em screen_pos. Retorna True se mudou.

    Contrato:
      - notches == 0: no-op, retorna False.
      - screen_pos fora do viewport: no-op, retorna False.
      - novo zoom fora de [MIN_ZOOM, MAX_ZOOM]: clamped.
      - se o zoom clampado == zoom atual: no-op, retorna False.

    Ancoragem: o ponto logico sob o cursor e preservado. O algoritmo
    calcula a posicao normalizada do cursor no viewport (u, v) e, com
    o novo zoom, redefine view_x/view_y para que (u, v) aponte para a
    mesma coordenada logica.

    Nao chama draw/flip, nao toca state, prefs nem RuntimeRules.
    """
    if notches == 0:
        return False

    world_pos = _screen_to_world_float(screen_pos)
    if world_pos is None:
        return False

    sx, sy = screen_pos
    u = (sx - _viewport_rect.left) / _viewport_rect.width
    v = (sy - _viewport_rect.top) / _viewport_rect.height

    new_zoom = _camera.zoom * (cfg.ZOOM_STEP ** notches)
    new_zoom = max(
        cfg.MIN_ZOOM,
        min(new_zoom, cfg.MAX_ZOOM),
    )

    if new_zoom == _camera.zoom:
        return False

    world_x, world_y = world_pos

    new_view_w = layout.LAYOUT.world_width / new_zoom
    new_view_h = layout.LAYOUT.world_height / new_zoom

    new_view_x = world_x - u * new_view_w
    new_view_y = world_y - v * new_view_h

    _camera.zoom = new_zoom
    _camera.view_x = new_view_x
    _camera.view_y = new_view_y

    _clamp_camera()

    return True


def reset_camera() -> bool:
    """Retorna a camera ao estado canonico (1x, view no topo-esquerda).

    Retorna True se a camera estava fora do estado canonico (para que
    o chamador decida sobre redraw). Preserva a identidade da
    instancia _camera: muta in-place via atribuicao de campos.
    """
    changed = (
        _camera.zoom != 1.0
        or _camera.view_x != 0.0
        or _camera.view_y != 0.0
    )

    _camera.zoom = 1.0
    _camera.view_x = 0.0
    _camera.view_y = 0.0

    _clamp_camera()

    return changed


def _camera_source_rect() -> pygame.Rect:
    """Recorte discreto do raster logico correspondente a view.

    Converte view_x/view_y (float) em um rect inteiro [left, top,
    width, height] sobre o raster [W, H, 3] de _build_image().

    Quantizacao: floor no topo-esquerda, ceil no fundo-direita.
    Isso garante que a view float esteja sempre contida no recorte
    discreto (nunca corta pixels que pertencem a view).

    Clamp final aos limites do mundo. Nao muta a camera.
    """
    view_w, view_h = _camera_view_size()

    left = math.floor(_camera.view_x)
    top = math.floor(_camera.view_y)

    right = math.ceil(_camera.view_x + view_w)
    bottom = math.ceil(_camera.view_y + view_h)

    left = max(0, left)
    top = max(0, top)

    right = min(layout.LAYOUT.world_width, right)
    bottom = min(layout.LAYOUT.world_height, bottom)

    right = max(left + 1, right)
    bottom = max(top + 1, bottom)

    return pygame.Rect(
        left,
        top,
        right - left,
        bottom - top,
    )


def toggle_fullscreen() -> None:
    """Alterna entre modo janela e tela cheia.

    Em tela cheia, usa pygame.FULLSCREEN (o driver escolhe a
    resolucao nativa do monitor; current_w/current_h sao hint). Ao
    voltar, usa WORLD_WIDTH x WORLD_HEIGHT x PIXEL_SCALE.

    O fullscreen recalcula o viewport fisico SEM resetar a camera:
    zoom/view_x/view_y sao preservados entre modos (sujeitos a clamp
    defensivo em _clamp_camera). Nao ha redraw aqui — o adapter de
    teclado devolve DispatchResult e o loop grafico decide quando
    desenhar.

    NOTA: a janela e criada com pygame.RESIZABLE em init() para a
    troca de modo em runtime ser confiavel em todos os drivers. Sem
    RESIZABLE, alguns backends ignoram set_mode() apos a criacao.
    """
    global _screen, _fullscreen

    _fullscreen = not _fullscreen

    if _fullscreen:
        info = pygame.display.Info()
        width, height = info.current_w, info.current_h
        _screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
    else:
        width = layout.LAYOUT.window_width
        height = layout.LAYOUT.window_height
        _screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)

    on_resize(*_screen.get_size())
    # Sem draw() aqui: o redraw vem do DispatchResult do adapter
    # registrado em simulation.run(). Chamar draw() diretamente
    # contradiz o contrato de panels.py (handlers retornam redraw=True
    # e o loop grafico decide quando desenhar).


def _draw_nests(image: np.ndarray) -> None:
    """Pinta os rings dos ninhos no buffer da imagem.

    Ordem: chamado depois de zones e antes do loop de agents em
    _build_image(). Ninhos ficam sob os critters, sob trail,
    highlights e inspection marker, e sobre background/zones.

    Independe de state.zones_active: ninhos sao geometria permanente
    do mundo, nao participam do toggle de zona.

    Cor: cor canonica da linhagem multiplicada por _NEST_COLOR_SCALE,
    composta por np.maximum para nao apagar zonas ja pintadas.

    Nao muta state.nests, fields nem zones; nao consome RNG.
    """
    if state.nests is None:
        return
    if len(state.nests) != cfg.TOTAL_LINEAGES:
        raise RuntimeError(
            f"_draw_nests: state.nests tem {len(state.nests)} "
            f"centros; esperado {cfg.TOTAL_LINEAGES}."
        )

    ring_offsets = nest_geometry.nest_ring_offsets(cfg.NEST_RADIUS)
    if not ring_offsets:
        return

    for li, lineage in enumerate(cfg.LINEAGES):
        center = state.nests[li]
        xs, ys = nest_geometry.wrapped_points(
            center,
            ring_offsets,
            width=layout.LAYOUT.world_width,
            height=layout.LAYOUT.world_height,
        )
        for channel, value in enumerate(lineage["color"]):
            if value == 0:
                continue
            nest_value = int(round(value * _NEST_COLOR_SCALE))
            if nest_value == 0:
                continue
            channel_img = image[..., channel]
            channel_img[xs, ys] = np.maximum(
                channel_img[xs, ys], nest_value
            )


def _build_image() -> np.ndarray:
    image = np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height, 3),
        dtype=np.uint8,
    )

    # Pinta zonas primeiro, como tom de fundo aditivo, mas so com o
    # toggle de runtime ligado. A mascara em si nunca e modificada
    # pelo toggle; reativar restaura o visual imediatamente.
    if state.zones is not None and state.zones_active:
        for channel, value in enumerate(_ZONE_COLOR):
            if value == 0:
                continue
            channel_img = image[..., channel]
            channel_img[state.zones] = np.maximum(channel_img[state.zones], value)

    # Ninhos: fora do if de zonas. Geometria permanente do mundo.
    _draw_nests(image)

    for agent in agents:
        mask = agent["field"] > 0
        if not mask.any():
            continue
        for channel, value in enumerate(agent["color"]):
            if value == 0:
                continue
            current = image[..., channel]
            current[mask] = np.maximum(current[mask], value)
    # Trail do bicho observado: sobre as linhagens, sob os
    # contornos. Ordem importa — ver docstring de _draw_trail.
    _draw_trail(image)
    _draw_highlights(image)
    _draw_inspection_marker(image)
    return image


def _draw_highlights(image: np.ndarray) -> None:
    """Desenha o contorno amarelo de Moore em volta do CANDIDATO de
    DISCOVERY.

    Ha exatamente UM candidato por vez, e e o MESMO individuo que
    world.discovery_candidate() retorna ao painel (a linha
    "candidate:" na secao DESCOBERTA) e que controls.py adota em
    Enter. Invariante central: o amarelo que se ve == o bicho que
    Enter observa.

    Comportamento:
      - Painel OFF -> nada.
      - Painel ON  -> resolve UM candidato via
        world.discovery_candidate(criterion, lineage_filter), com a
        semantica de filtro de cfg.LINEAGE_FILTER_ORDER:
            all -> melhor global entre todas as linhagens
            R/G/B -> melhor daquela linhagem
        Sem candidato (populacao vazia, linhagem filtrada extinta,
        criterio desconhecido) -> nada. O observado, se houver, fica
        intocado: discovery e observation sao independentes.
      - Candidato == observado -> o amarelo e pintado primeiro e o
        ciano (desenhado depois por _draw_inspection_marker)
        sobrescreve, entao so se ve ciano. E o visual correto para
        "voce esta olhando o melhor candidato atual".

    Note: esta funcao NAO chama world.best_of_lineage() nem itera por
    linhagem. Comportamento de tres contornos amarelos era do modelo
    antigo. Com discovery explicito, um unico amarelo e a
    representacao honesta de "o bicho que Enter adotaria agora".

    A chamada a world.discovery_candidate() e duplicada com a de
    _draw_inspection_panel(). Deliberado: discovery e DERIVACAO PURA
    do estado, e adicionar cache ou candidate_id persistente traria
    risco de invalidacao por dois scans O(N) por frame sobre ~600
    bichos. Nao vale.
    """
    if ui_state.active_panel != ui_state.PANEL_INSPECTION:
        return

    candidate = world.discovery_candidate(
        state.discovery_criterion,
        state.discovery_lineage_filter,
    )
    if candidate is None:
        return

    li, ai = candidate
    matrix = agents[li]["agents"]
    x = int(matrix[ai, INDEX_X])
    y = int(matrix[ai, INDEX_Y])

    xs = np.array(
        [(x + dx) % layout.LAYOUT.world_width for dx, _ in _MOORE_OFFSETS],
        dtype=np.intp,
    )
    ys = np.array(
        [(y + dy) % layout.LAYOUT.world_height for _, dy in _MOORE_OFFSETS],
        dtype=np.intp,
    )
    image[xs, ys, :] = _HIGHLIGHT_COLOR


def _draw_inspection_marker(image: np.ndarray) -> None:
    """Pinta o marcador ciano de observacao.

    Duas formas, para distinguir VIVO de MORTO:

      vivo  -> contorno Moore completo (8 celulas) em volta da celula
      morto -> cruz ciana centrada na ultima celula conhecida

    A cruz usa coordenadas toroidais para uma morte na borda do
    mundo nao produzir marcador truncado. Ambas sao ciano; a FORMA
    carrega a distincao vivo/morto.
    """
    if ui_state.active_panel != ui_state.PANEL_INSPECTION:
        return

    critter_id = state.inspected_critter_id
    if critter_id is None:
        return

    snapshot = state.inspection_death_snapshot

    if snapshot is not None:
        # Morto: cruz ciana na ultima posicao conhecida.
        x = int(snapshot.agent[INDEX_X])
        y = int(snapshot.agent[INDEX_Y])
        w = layout.LAYOUT.world_width
        h = layout.LAYOUT.world_height
        cells = [
            (x, y),
            ((x - 1) % w, y),
            ((x + 1) % w, y),
            (x, (y - 1) % h),
            (x, (y + 1) % h),
        ]
        for cx, cy in cells:
            image[cx, cy, 0] = 0
            image[cx, cy, 1] = 255
            image[cx, cy, 2] = 255
        return

    # Vivo: contorno Moore ciano.
    from .world import resolve_critter_id

    resolved = resolve_critter_id(critter_id)
    if resolved is None:
        return

    li, ai = resolved
    row = agents[li]["agents"][ai]
    x = int(row[INDEX_X])
    y = int(row[INDEX_Y])

    xs = np.array(
        [(x + dx) % layout.LAYOUT.world_width for dx, _ in _MOORE_OFFSETS],
        dtype=np.intp,
    )
    ys = np.array(
        [(y + dy) % layout.LAYOUT.world_height for _, dy in _MOORE_OFFSETS],
        dtype=np.intp,
    )
    image[xs, ys, 0] = 0
    image[xs, ys, 1] = 255
    image[xs, ys, 2] = 255


def _draw_trail(image: np.ndarray) -> None:
    """Desenha o rastro do bicho observado como linha em escala de
    cinza, com fade.

    So com inspecao ligada e um bicho selecionado. Desenhado DEPOIS
    das linhagens (visivel por cima) e ANTES dos contornos e do
    marcador (nunca esconde os contornos).

    A cor esvaece com a idade: o ponto mais antigo e TRAIL_COLOR_OLD
    (quase preto), o mais novo e TRAIL_COLOR_NEW (quase branco). Da
    sensacao de direcao — a ponta clara e onde o bicho esta agora — e
    evita que um rastro longo domine a imagem.

    Cinza neutro de proposito: nao compete com as cores R/G/B nem
    com as zonas. Rastro colorido seria ambiguo (de qual linhagem?)
    e brigaria com a paleta.

    Nota toroidal: se o bicho cruza a borda do mundo, dois pontos
    consecutivos podem ficar distantes na tela (o bicho
    "teleportou"). NAO tentamos quebrar o rastro nesses cruzamentos:
    o rastro e uma sequencia de pontos, nao uma linha conectada,
    entao o cruzamento so mostra dois aglomerados de pontos.
    """
    if ui_state.active_panel != ui_state.PANEL_INSPECTION:
        return
    trail = state.inspected_trail
    n = len(trail)
    if n < 1:
        return

    # Pre-calcula o denominador do ramp (evita divisao por ponto).
    denom = max(1, n - 1)
    old_c = cfg.TRAIL_COLOR_OLD
    new_c = cfg.TRAIL_COLOR_NEW
    span = new_c - old_c

    for i, (x, y) in enumerate(trail):
        if 0 <= x < layout.LAYOUT.world_width and 0 <= y < layout.LAYOUT.world_height:
            gray = old_c + (span * i) // denom
            image[x, y] = (gray, gray, gray)


def _draw_hud_kv(
    surface: pygame.Surface,
    label: str,
    value: str,
    x: int,
    y: int,
    *,
    value_color: tuple[int, int, int] = _HUD_TEXT,
) -> int:
    """Desenha `LABEL    VALUE` e retorna o Y da proxima linha.

    Label em secundaria, value em primaria (ou cor passada). Nao e um
    sistema de widgets: apenas o par label/value com spacing fixo.
    """
    label_surface = _font.render(label, True, _HUD_SEC)
    surface.blit(label_surface, (x, y))

    value_surface = _font.render(value, True, value_color)
    value_x = (
        x + cfg.HUD_TELEMETRY_WIDTH - 2 * cfg.HUD_PADDING - value_surface.get_width()
    )
    surface.blit(value_surface, (value_x, y))

    return y + max(label_surface.get_height(), value_surface.get_height()) + 2


def _draw_hud_kv_inline(
    surface: pygame.Surface,
    pairs: list[tuple[str, str]],
    x: int,
    y: int,
    *,
    gap: int = 12,
) -> int:
    """Desenha `LABEL VALUE   LABEL VALUE ...` em sequencia horizontal.

    Sem alinhamento a direita: cada par flui da esquerda para a
    direita, separado por `gap` pixels. Usado no bloco de parametros
    do Telemetry HUD, onde varios pares curtos dividem a mesma
    linha para reduzir a altura total do painel.

    Retorna o Y da proxima linha (mesma regra de _draw_hud_kv).
    """
    cursor_x = x
    line_h = 0
    for label, value in pairs:
        label_surface = _font.render(label, True, _HUD_SEC)
        surface.blit(label_surface, (cursor_x, y))
        cursor_x += label_surface.get_width() + 4

        value_surface = _font.render(value, True, _HUD_TEXT)
        surface.blit(value_surface, (cursor_x, y))
        cursor_x += value_surface.get_width() + gap

        line_h = max(line_h, label_surface.get_height(), value_surface.get_height())

    return y + line_h + 2


def _draw_hud_divider(surface: pygame.Surface, x: int, y: int, width: int) -> int:
    """Desenha um separador horizontal e retorna o Y apos o gap."""
    pygame.draw.line(surface, cfg.HUD_DIVIDER_COLOR, (x, y), (x + width, y), 1)
    return y + cfg.HUD_SECTION_GAP


def _zone_summary() -> str:
    """Resumo de zonas para o Telemetry HUD (estado puro, sem [Z]).

    Construido direto de state.zones / state.zones_active /
    cfg.NUMBER_OF_ZONES / cfg.ZONE_RADIUS. Nao usa format_zones_txt()
    porque aquele concatena documentacao de atalho, que pertence ao
    Command Dock, nao a telemetria.
    """
    if state.zones is None:
        return i18n.t("hud.zone_summary_none")
    key = "hud.zone_summary_on" if state.zones_active else "hud.zone_summary_off"
    return i18n.t(key, n=cfg.NUMBER_OF_ZONES, r=cfg.ZONE_RADIUS)


def _draw_telemetry_brand(x0: int, y0: int, width: int) -> pygame.Rect:
    """Desenha a faixa de brand: [icon] PRIMORDIAL SOUP ... [REC] RPS.

    Sem fundo e sem borda. Retorna o Rect logico ocupado (geometria,
    nao decoracao). Se _hud_icon for None, o titulo comeca em x0 e
    nenhum espaco e reservado para o icone.
    """
    icon_size = 18
    icon_gap = 6
    inner_pad = cfg.HUD_PADDING

    title_surface = _font_hud_title.render(
        cfg.WINDOW_TITLE.upper(), True, cfg.HUD_TITLE_COLOR
    )

    # Compoe da esquerda para a direita: icon (opcional) + titulo.
    text_x = x0 + inner_pad
    if _hud_icon is not None:
        icon_x = text_x
        icon_y = y0 + max(0, (title_surface.get_height() - icon_size) // 2)
        _screen.blit(_hud_icon, (icon_x, icon_y))
        text_x = icon_x + icon_size + icon_gap
    _screen.blit(title_surface, (text_x, y0))

    # Compoe da direita para a esquerda: RPS e (se ativo) REC.
    rps_surfaces = _render_rps_compact()
    rps_width = sum(s.get_width() for s in rps_surfaces)

    right_edge = x0 + width - inner_pad
    rps_x = right_edge - rps_width
    rps_y = y0 + max(
        0, (title_surface.get_height() - _font_hud_title.get_height()) // 2
    )
    for surface in rps_surfaces:
        _screen.blit(surface, (rps_x, rps_y))
        rps_x += surface.get_width()

    if state.recording:
        rec_surface = _font_hud_title.render(
            i18n.t("hud.recording_on"), True, _RECORDING_COLOR
        )
        # 8 px de respiro entre REC e RPS.
        rec_gap = 8
        rec_x = right_edge - rps_width - rec_gap - rec_surface.get_width()
        _screen.blit(rec_surface, (rec_x, rps_y))

    return pygame.Rect(x0, y0, width, title_surface.get_height())


def _draw_telemetry_panel(x0: int, y0: int, width: int) -> pygame.Rect:
    """Desenha o painel operacional (status + parametros).

    Unica regiao do Telemetry HUD com fundo e borda. Altura derivada
    do conteudo real:
        6 linhas de status
        + 1 separador (HUD_SECTION_GAP)
        + 5 linhas de parametros
        + 2 * HUD_PADDING
    """
    STATUS_LINES = 6
    PARAMETER_LINES = 5

    line_h = _font.get_height() + 2
    content_h = STATUS_LINES * line_h + cfg.HUD_SECTION_GAP + PARAMETER_LINES * line_h
    height = content_h + 2 * cfg.HUD_PADDING

    background = pygame.Surface((width, height), pygame.SRCALPHA)
    background.fill((*cfg.HUD_BG_COLOR, cfg.HUD_OVERLAY_ALPHA))
    _screen.blit(background, (x0, y0))
    pygame.draw.rect(_screen, _HUD_BORDER, (x0, y0, width, height), 1)

    inner_x = x0 + cfg.HUD_PADDING
    inner_w = width - 2 * cfg.HUD_PADDING

    y = y0 + cfg.HUD_PADDING

    # --- Status ---
    y = _draw_hud_kv(
        _screen,
        i18n.t("hud.label.tick"),
        str(state.tick_count),
        inner_x,
        y,
    )
    y = _draw_hud_kv(
        _screen,
        i18n.t("hud.label.speed"),
        f"{state.simulation_speed:g}x",
        inner_x,
        y,
    )
    y = _draw_hud_kv(
        _screen,
        i18n.t("hud.label.zoom"),
        f"{_camera.zoom:.2f}x",
        inner_x,
        y,
    )
    y = _draw_hud_kv(
        _screen,
        i18n.t("hud.label.births"),
        str(state.births),
        inner_x,
        y,
    )
    y = _draw_hud_kv(
        _screen,
        i18n.t("hud.label.deaths"),
        str(state.deaths),
        inner_x,
        y,
    )
    y = _draw_hud_kv(
        _screen,
        i18n.t("hud.label.slot"),
        state.active_save_slot,
        inner_x,
        y,
    )

    # --- Separador ---
    y = _draw_hud_divider(_screen, inner_x, y, inner_w)

    # --- Parametros ---
    mutation_mode = i18n.t(
        "hud.value.mutation_mode."
        f"{state.runtime_rules.mutation_mode}"
    )
    y = _draw_hud_kv_inline(
        _screen,
        [
            (
                i18n.t("hud.label.mutation"),
                f"{state.runtime_rules.mutation_rate}%",
            ),
            (i18n.t("hud.label.mode"), mutation_mode),
        ],
        inner_x,
        y,
    )
    y = _draw_hud_kv_inline(
        _screen,
        [
            (
                i18n.t("hud.label.local"),
                f"{state.runtime_rules.local_scale_fraction}%",
            ),
            (
                i18n.t("hud.label.global"),
                f"{state.runtime_rules.global_probability}%@{state.runtime_rules.global_scale_fraction}%",
            ),
        ],
        inner_x,
        y,
    )
    environment = i18n.t(f"hud.value.environment.{cfg.ENVIRONMENTAL_MODIFIERS}")
    y = _draw_hud_kv_inline(
        _screen,
        [
            (i18n.t("hud.label.environment"), environment),
            (i18n.t("hud.label.zones"), _zone_summary()),
            (
                i18n.t("hud.label.zone_hp"),
                f"{state.runtime_rules.zone_hp_effect:+d}",
            ),
        ],
        inner_x,
        y,
    )
    rules = state.runtime_rules
    reproduction_criterion = i18n.t(
        "hud.value.reproduction_criterion."
        f"{rules.reproduction_criterion}"
    )
    reproduction_gates = i18n.t(
        "hud.reproduction_gates",
        age=rules.reproduction_min_age,
        hp=rules.reproduction_hp_gate,
        score=rules.reproduction_min_score,
        enc=rules.reproduction_min_encounters,
    )
    y = _draw_hud_kv_inline(
        _screen,
        [
            (
                i18n.t("hud.label.reproduction"),
                f"{reproduction_criterion} {reproduction_gates}",
            ),
        ],
        inner_x,
        y,
    )
    y = _draw_hud_kv_inline(
        _screen,
        [
            (
                i18n.t("hud.label.weights"),
                f"L {rules.longevity_weight:.1f}  "
                f"E {rules.exploration_weight:.1f}  "
                f"I {rules.interaction_weight:.1f}  "
                f"R {rules.reproduction_weight:.1f}",
            ),
        ],
        inner_x,
        y,
    )

    return pygame.Rect(x0, y0, width, height)


def _draw_lineage_table(x0: int, y0: int, width: int) -> pygame.Rect:
    """Desenha a tabela R/G/B, sem fundo e sem borda.

    Alinhamento interno: comeca em x0 + HUD_PADDING, mesma linha
    vertical do conteudo do painel central, para continuidade visual.
    """
    inner_x = x0 + cfg.HUD_PADDING

    hp = average_hp_per_lineage()
    lt = longest_lifetime()
    gen = max_generation()
    pops = [len(ag["agents"]) for ag in agents]
    scores = average_composite_score_per_lineage()

    y = y0

    header = _font.render(_lineage_header_text(), True, _HUD_SEC)
    _screen.blit(header, (inner_x, y))
    y += header.get_height() + 2

    for ag, h, t, g, p, s in zip(agents, hp, lt, gen, pops, scores):
        line = _LINEAGE_TABLE_ROW_FMT.format(
            id=ag["id"], hp=h, lt=t, gen=g, pop=p, score=s
        )
        surface = _font.render(line, True, ag["color"])
        _screen.blit(surface, (inner_x, y))
        y += surface.get_height() + 2

    return pygame.Rect(x0, y0, width, y - y0)


def _draw_telemetry_hud() -> pygame.Rect:
    """Compositor do Telemetry HUD.

    Tres regioes empilhadas verticalmente:
        brand frameless  (icon + titulo + REC + RPS)
        painel com moldura (status + parametros)
        tabela frameless   (R/G/B)

    Retorna o bounding box da composicao inteira, para que o
    contrato estrutural existente (contido na area do mundo,
    largura HUD_TELEMETRY_WIDTH) continue valido.

    O gate de floating_hud_visible e responsabilidade de draw();
    esta funcao desenha incondicionalmente.
    """
    x0 = cfg.HUD_MARGIN
    y0 = cfg.HUD_MARGIN
    width = cfg.HUD_TELEMETRY_WIDTH

    GAP_BRAND_PANEL = 5
    GAP_PANEL_LINEAGE = 7

    brand_rect = _draw_telemetry_brand(x0, y0, width)
    panel_rect = _draw_telemetry_panel(x0, brand_rect.bottom + GAP_BRAND_PANEL, width)
    lineage_rect = _draw_lineage_table(x0, panel_rect.bottom + GAP_PANEL_LINEAGE, width)

    return brand_rect.union(panel_rect).union(lineage_rect)


def _draw_generic_chart(
    x0: int,
    y0: int,
    width: int,
    height: int,
    series: list[list[tuple[int, float]]],
    title: str,
    labels: list[str],
    colors: list[tuple[int, int, int]],
    show_legend: bool = True,
) -> None:
    """Desenha um line chart com eixos, grade, titulo e legenda.

    `series[k]` e a k-esima serie, lista de (tick, valor). Todas as
    series precisam ter o mesmo numero de pontos (mesmo eixo X).
    `labels[k]` e `colors[k]` correspondem a serie k.

    show_legend: quando False, omite a legenda embutida. Usado pelo
    dashboard de small multiples, que desenha uma unica legenda no
    topo e nao repete R/G/B em cada grafico.

    Layout:
        - Faixa de titulo no topo (~18 px).
        - Area de plot com padding esquerda/inferior para eixos.
        - Legenda no canto superior direito (se show_legend).
        - Rotulos numericos: max/min no eixo Y; primeiro/ultimo tick
          no X.
    """
    if not series or len(series[0]) < 2:
        # Nada a desenhar ainda (historico curto). Desenha so a moldura
        # e o titulo, para o painel nao "piscar" no startup.
        background = pygame.Surface((width, height), pygame.SRCALPHA)
        background.fill((*_CHART_BG, 235))
        _screen.blit(background, (x0, y0))
        pygame.draw.rect(_screen, _CHART_AXIS, (x0, y0, width, height), 1)
        label = _font_chart_title.render(title, True, _CHART_TITLE)
        _screen.blit(label, (x0 + 8, y0 + 4))
        return

    pad = cfg.CHART_INNER_PADDING
    title_height = 18

    # Area de plot (dentro do painel).
    ax0 = x0 + pad
    ay0 = y0 + title_height
    ax1 = x0 + width - 8
    ay1 = y0 + height - pad

    area_width = max(1, ax1 - ax0)
    area_height = max(1, ay1 - ay0)

    background = pygame.Surface((width, height), pygame.SRCALPHA)
    background.fill((*_CHART_BG, 235))
    _screen.blit(background, (x0, y0))
    pygame.draw.rect(_screen, _CHART_AXIS, (x0, y0, width, height), 1)

    title_label = _font_chart_title.render(title, True, _CHART_TITLE)
    _screen.blit(title_label, (x0 + 8, y0 + 4))

    n = len(series[0])
    max_y = 0.0
    for serie in series:
        for _, v in serie:
            if v > max_y:
                max_y = v
    if max_y <= 0.0:
        max_y = 1.0
    # Arredonda numa "escada agradavel" (1, 2, 5, 10, ...).
    scale = 10.0 ** np.floor(np.log10(max_y))
    for step in (1, 2, 5, 10):
        if max_y <= step * scale:
            max_y = step * scale
            break

    tick_min = series[0][0][0]
    tick_max = series[0][-1][0]
    if tick_max <= tick_min:
        tick_max = tick_min + 1

    n_h = cfg.HORIZONTAL_GRID_LINES
    for i in range(n_h + 1):
        t = i / n_h
        y = ay1 - int(t * area_height)
        pygame.draw.line(_screen, _CHART_GRID, (ax0, y), (ax1, y), 1)
        value = max_y * t
        text = _font_chart.render(f"{value:.0f}", True, _CHART_LABEL)
        _screen.blit(text, (x0 + 4, y - text.get_height() // 2))

    n_v = cfg.VERTICAL_GRID_LINES
    for i in range(n_v + 1):
        t = i / n_v
        x = ax0 + int(t * area_width)
        pygame.draw.line(_screen, _CHART_GRID, (x, ay0), (x, ay1), 1)

    pygame.draw.line(_screen, _CHART_AXIS, (ax0, ay1), (ax1, ay1), 1)
    pygame.draw.line(_screen, _CHART_AXIS, (ax0, ay0), (ax0, ay1), 1)

    for i in range(n_v + 1):
        t = i / n_v
        x = ax0 + int(t * area_width)
        tick_v = tick_min + t * (tick_max - tick_min)
        text = _font_chart.render(f"{tick_v:.0f}", True, _CHART_LABEL)
        _screen.blit(text, (x - text.get_width() // 2, ay1 + 2))

    x_label = _font_chart.render(i18n.t("chart.x_axis"), True, _CHART_LABEL)
    _screen.blit(x_label, (ax1 - x_label.get_width(), ay1 + 2))

    x_step = area_width / max(1, n - 1)
    for k, serie in enumerate(series):
        color = colors[k % len(colors)]
        points = []
        for i, (_, v) in enumerate(serie):
            px = ax0 + int(i * x_step)
            py = ay1 - int((v / max_y) * area_height)
            points.append((px, py))
        if len(points) >= 2:
            pygame.draw.lines(_screen, color, False, points, cfg.CHART_LINE_THICKNESS)

    if show_legend:
        legend_x = ax1 - 8
        legend_y = ay0 + 4
        for k, (label, color) in enumerate(zip(labels, colors)):
            pygame.draw.rect(_screen, color, (legend_x - 60, legend_y + 4, 10, 3))
            text = _font_chart.render(label, True, _CHART_LABEL)
            _screen.blit(text, (legend_x - 60 + 14, legend_y))
            legend_y += text.get_height() + 2


def _series_from_history(
    data: list[tuple[int, tuple[float, ...]]],
) -> list[list[tuple[int, float]]]:
    """Transpoe um historico (tick, tupla) em lista de series.

    Se as tuplas tiverem tamanho 1, retorna uma serie. Se tiverem
    tamanho N, retorna N series (uma por posicao).
    """
    if not data:
        return []
    n_values = len(data[0][1])
    return [[(tick, values[k]) for tick, values in data] for k in range(n_values)]


def _draw_metric_chart(
    name: str,
    x0: int,
    y0: int,
    width: int,
    height: int,
    show_legend: bool = True,
) -> None:
    """Desenha o chart de uma metrica nomeada.

    `name` e argumento explicito (chave canonica em
    cfg.ADVANCED_METRICS). O rendering NAO le metric selecionada
    globalmente: cada chamador escolhe o nome.

    show_legend: propagado para _draw_generic_chart. O dashboard usa
    False e desenha uma legenda unica no topo.
    """
    data = list(state.metrics_history.get(name, []))
    readable_label = i18n.t(f"metric.{name}")

    if name == "populacao":
        title = i18n.t("chart.population_title")
    else:
        title = i18n.t("chart.metric_title", label=readable_label)

    if len(data) < 2:
        _draw_generic_chart(
            x0,
            y0,
            width,
            height,
            [],
            title,
            [],
            [],
            show_legend=show_legend,
        )
        return

    series = _series_from_history(data)

    if len(series) == 1:
        labels = [i18n.t("chart.scalar_label")]
        colors = [_SCALAR_COLOR]
    else:
        labels = [ag["id"] for ag in agents]
        colors = [_LINEAGE_COLORS[k % len(_LINEAGE_COLORS)] for k in range(len(series))]

    _draw_generic_chart(
        x0,
        y0,
        width,
        height,
        series,
        title,
        labels,
        colors,
        show_legend=show_legend,
    )


def _draw_metrics_dashboard(x0: int, y0: int, width: int, height: int) -> int:
    """Small multiples das seis metricas de cfg.ADVANCED_METRICS.

    Retorna o Y logo abaixo do conteudo, para o viewport calcular
    content_height e o scroll.

    Estrutura:
        legenda unica (R G B)
        POPULACAO        [grafico]
        HP MEDIO         [grafico]
        MAIOR TEMPO      [grafico]
        GERACAO MAXIMA   [grafico]
        SCORE COMPOSTO   [grafico]
        TAXA DE MUTACAO  [grafico]

    A ordem segue exatamente cfg.ADVANCED_METRICS: config,
    state.metrics_history, CSV e dashboard compartilham a mesma
    ordem canonica.

    Altura adaptativa: cada grafico recebe uma fracao do viewport,
    respeitando min/max legiveis. Se nao couberem todos, o scroll
    existente cobre.
    """
    padding = 10
    inner_w = max(80, width - 2 * padding)

    # Cabecalho.
    y = y0 + padding
    title = _font_panel_title.render(
        i18n.t("panel.metrics.title"), True, cfg.PANEL_TEXT_COLOR
    )
    _screen.blit(title, (x0 + padding, y))
    y += title.get_height() + 6

    # Legenda unica (R G B), alinhada a esquerda. Uma linha so.
    legend_y = y
    legend_x = x0 + padding
    for i, ag in enumerate(agents):
        color = _LINEAGE_COLORS[i % len(_LINEAGE_COLORS)]
        pygame.draw.rect(_screen, color, (legend_x, legend_y + 6, 10, 3))
        text = _font_chart.render(ag["id"], True, _CHART_LABEL)
        _screen.blit(text, (legend_x + 14, legend_y))
        legend_x += 14 + text.get_width() + 14
    y += _font_chart.get_height() + 10

    # Distribuicao vertical. Reserva cabecalho ja consumido.
    n_metrics = len(cfg.ADVANCED_METRICS)
    # Altura restante ate o fim do viewport.
    remaining = max(0, (y0 + height) - y - 4 * n_metrics)
    if n_metrics > 0:
        # Um chart + gap por metrica. Minimo legivel 60, maximo util
        # 140 (evita esticar demais quando o viewport e grande).
        per_gap = 8
        chart_h = remaining // n_metrics - per_gap
        chart_h = max(60, min(140, chart_h))
    else:
        chart_h = 100

    for name in cfg.ADVANCED_METRICS:
        _draw_metric_chart(name, x0 + padding, y, inner_w, chart_h, show_legend=False)
        y += chart_h + 8

    return y + padding


def _draw_keycap(
    surface: pygame.Surface,
    key: str,
    x: int,
    y: int,
) -> pygame.Rect:
    """Desenha um keycap e retorna o Rect ocupado.

    Borda e texto amarelos (INSPECTION_HIGHLIGHT_COLOR), fundo escuro
    (HUD_KEY_BG_COLOR). Sem rounded corners: retangulo discreto,
    consistente com o resto da UI.
    """
    pad_x = 6
    pad_y = 2
    text_surface = _font.render(key, True, cfg.INSPECTION_HIGHLIGHT_COLOR)
    w = text_surface.get_width() + 2 * pad_x
    h = text_surface.get_height() + 2 * pad_y

    pygame.draw.rect(surface, cfg.HUD_KEY_BG_COLOR, (x, y, w, h))
    pygame.draw.rect(surface, cfg.INSPECTION_HIGHLIGHT_COLOR, (x, y, w, h), 1)
    surface.blit(text_surface, (x + pad_x, y + pad_y))
    return pygame.Rect(x, y, w, h)


def _draw_shortcut(
    surface: pygame.Surface,
    key: str,
    action: str,
    x: int,
    y: int,
) -> pygame.Rect:
    """Desenha `[KEY] acao` e retorna o Rect total ocupado."""
    key_rect = _draw_keycap(surface, key, x, y)
    action_surface = _font.render(action, True, _HUD_TEXT)
    action_x = key_rect.right + 4
    action_y = y + (key_rect.height - action_surface.get_height()) // 2
    surface.blit(action_surface, (action_x, action_y))

    total_w = key_rect.width + 4 + action_surface.get_width()
    total_h = key_rect.height
    return pygame.Rect(x, y, total_w, total_h)


def _draw_command_dock() -> pygame.Rect:
    """Desenha o Command Dock e retorna o Rect ocupado.

    Cada grupo vira uma linha: `LABEL  [key] acao  [key] acao ...`.
    Largura = largura util do mundo - 2*HUD_MARGIN. Nao invade a
    sidebar. Sem hit-testing: os keycaps sao representacao visual.
    """
    screen_w, screen_h = _screen.get_size()
    usable_w = screen_w - cfg.INSPECTION_PANEL_WIDTH
    width = int((usable_w - 2 * cfg.HUD_MARGIN) * 0.42)
    x0 = cfg.HUD_MARGIN

    line_h = _font.get_height() + 4
    group_gap = 2
    # Estimativa de altura: 4 grupos x line_h + 3 gaps + 2*padding.
    n_groups = len(_COMMAND_GROUPS)
    height = 2 * cfg.HUD_PADDING + n_groups * line_h + (n_groups - 1) * group_gap
    y0 = screen_h - cfg.HUD_MARGIN - height

    background = pygame.Surface((width, height), pygame.SRCALPHA)
    background.fill((*cfg.HUD_BG_COLOR, cfg.HUD_OVERLAY_ALPHA))
    _screen.blit(background, (x0, y0))
    pygame.draw.rect(_screen, _HUD_BORDER, (x0, y0, width, height), 1)

    # Largura reservada para o rotulo do grupo, para os keycaps
    # comecarem alinhados entre as linhas. Medido do maior rotulo
    # traduzido (PAINEIS/RAPIDAS sao os mais longos em PT).
    label_w = 0
    for label_key, _shortcuts in _COMMAND_GROUPS:
        s = _font.render(i18n.t(label_key), True, _HUD_SEC)
        if s.get_width() > label_w:
            label_w = s.get_width()
    label_col_x = x0 + cfg.HUD_PADDING
    shortcuts_x = label_col_x + label_w + 10

    y = y0 + cfg.HUD_PADDING
    for label_key, shortcuts in _COMMAND_GROUPS:
        label_surface = _font.render(i18n.t(label_key), True, _HUD_SEC)
        _screen.blit(label_surface, (label_col_x, y + 2))

        x = shortcuts_x
        for key, action_key in shortcuts:
            rect = _draw_shortcut(_screen, key, i18n.t(action_key), x, y)
            x = rect.right + 12

        y += line_h + group_gap

    return pygame.Rect(x0, y0, width, height)


def _render_rps_compact() -> list[pygame.Surface]:
    """Linha compacta do ciclo RPS: R -> B -> G -> R.

    Substitui o antigo painel RPS tip de 3 linhas. Letras coloridas
    por linhagem; setas em cinza neutro. Lista de Surfaces para o
    chamador medir a largura total e desenhar sequencialmente.
    """
    arrow_color = _HUD_SEC
    parts: list[tuple[str, tuple[int, int, int]]] = [
        ("R", _LINEAGE_COLORS[0]),
        (" \u2192 ", arrow_color),
        ("G", _LINEAGE_COLORS[1]),
        (" \u2192 ", arrow_color),
        ("B", _LINEAGE_COLORS[2]),
        (" \u2192 ", arrow_color),
        ("R", _LINEAGE_COLORS[0]),
    ]
    return [_font_hud_title.render(t, True, c) for t, c in parts]


def _draw_confirm_exit_modal() -> None:
    """Desenha o modal de confirmacao de saida.

    Overlay escurecido + caixa central. Nao interage com o mundo:
    apenas cobre a tela. O input enquanto o modal existe e roteado
    pelo dispatcher (_handle_modal_event).
    """
    screen_w, screen_h = _screen.get_size()

    # Overlay escurecido (alpha 140).
    overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    _screen.blit(overlay, (0, 0))

    # Caixa central.
    box_w = 420
    box_h = 160
    box_x = (screen_w - box_w) // 2
    box_y = (screen_h - box_h) // 2

    pygame.draw.rect(_screen, cfg.HUD_BG_COLOR, (box_x, box_y, box_w, box_h))
    pygame.draw.rect(
        _screen,
        cfg.INSPECTION_HIGHLIGHT_COLOR,
        (box_x, box_y, box_w, box_h),
        2,
    )

    padding = 18
    title = _font_panel_title.render(
        i18n.t("modal.exit.title"), True, cfg.HUD_TEXT_COLOR
    )
    _screen.blit(title, (box_x + padding, box_y + padding))

    y = box_y + padding + title.get_height() + 16

    confirm = _font_panel.render(i18n.t("modal.exit.confirm"), True, cfg.HUD_TEXT_COLOR)
    _screen.blit(confirm, (box_x + padding, y))
    y += confirm.get_height() + 6

    cancel = _font_panel.render(
        i18n.t("modal.exit.cancel"), True, cfg.HUD_TEXT_SECONDARY_COLOR
    )
    _screen.blit(cancel, (box_x + padding, y))


def draw() -> None:
    image = _build_image()

    # Camera: recorta a regiao logica visivel ANTES de escalar.
    #
    # O pipeline e sempre:
    #     raster logico [W, H, 3]
    #       -> crop em _camera_source_rect()
    #       -> pygame.transform.scale(crop, viewport.size)
    #       -> blit em _viewport_rect.topleft
    #
    # O destino do scale e SEMPRE viewport.size, independente do
    # zoom. Isso garante custo de escala constante (O(viewport)) e
    # evita alocar surface gigante em zoom alto.
    source_rect = _camera_source_rect()

    # Ordem dos eixos: image[X, Y, C] (consistente com
    # state.zones[x, y] e agent["field"][x, y]). Portanto o recorte
    # e [left:right, top:bottom], nao [rows, cols]. O .copy() e
    # obrigatorio: slice nao-contiguo nao pode alimentar
    # surfarray.make_surface() com seguranca.
    source = image[
        source_rect.left:source_rect.right,
        source_rect.top:source_rect.bottom,
    ].copy()

    surface = pygame.surfarray.make_surface(source)

    viewport = _viewport_rect

    # Fundo preto para o letterbox (visivel so quando a proporcao do
    # monitor difere da do mundo).
    _screen.fill((0, 0, 0))

    if viewport.width > 0 and viewport.height > 0:
        surface = pygame.transform.scale(surface, viewport.size)

        _screen.blit(surface, viewport.topleft)

    # Elementos flutuantes sobre o mundo: gate unico aqui, nao dentro
    # de _draw_hud/_draw_rps_tip. A autoridade de composicao e draw().
    # A lateral direita fica FORA do gate: ocupa faixa estrutural
    # reservada, nao se sobrepoe ao mapa.
    if ui_state.floating_hud_visible:
        _draw_telemetry_hud()
        _draw_command_dock()

    _draw_lateral_panel()

    # Modal e o ultimo elemento: e visualmente superior a tudo o mais.
    # Gate unico aqui, nao dentro dos helpers.
    if ui_state.active_modal == "confirm_exit":
        _draw_confirm_exit_modal()

    pygame.display.flip()

    # Gravacao de tela: captura o frame COMPLETO renderizado (mundo +
    # HUD + charts + painel), logo apos o flip, para o GIF bater
    # exatamente com o que o usuario ve.
    #
    # O import e lazy e guardado pelo flag barato `state.recording`
    # (espelho do estado real em recording.py; ver state.py), para
    # quem nunca aperta G nao pagar nem o custo do import do Pillow
    # nem uma chamada por frame. Com o flag False, o unico custo e
    # uma leitura de atributo.
    if state.recording:
        from .recording import capture

        capture(_screen)


def tick_fps() -> None:
    _clock.tick(cfg.TARGET_FPS)


def shutdown() -> None:
    pygame.quit()