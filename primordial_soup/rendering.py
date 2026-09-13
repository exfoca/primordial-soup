# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import os

import numpy as np
import pygame

from . import config as cfg
from . import layout
from . import state
from . import i18n
from . import world
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
    format_zones_txt,
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

# Estado de tela cheia. F11 alterna via toggle_fullscreen().
_fullscreen: bool = False

# Escala e offset da imagem do mundo quando a resolucao da janela
# difere do tamanho base (WORLD_WIDTH * PIXEL_SCALE,
# WORLD_HEIGHT * PIXEL_SCALE).
#
# Em modo janela: _scale = 1.0, _offset = 0.
# Em tela cheia: recalculados para esticar o mundo ate preencher a
# janela, preservando a proporcao (letterbox na dimensao que sobra).
#
# Usados por controls._select_critter_at_click para converter clique
# do mouse em coordenadas do mundo.
_scale: float = 1.0
_offset_x: int = 0
_offset_y: int = 0


_MOORE_OFFSETS: tuple[tuple[int, int], ...] = tuple(
    (dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if not (dx == 0 and dy == 0)
)
_HIGHLIGHT_COLOR: tuple[int, int, int] = (255, 255, 0)

# Cor base das zonas ambientais. Tom aditivo suave sob as linhagens,
# para nao competir com as cores RPS.
_ZONE_COLOR: tuple[int, int, int] = (24, 20, 8)


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
_SCALAR_COLOR: tuple[int, int, int] = (220, 220, 220)

# Indicador de gravacao (desenhado no HUD quando gravando).
_RECORDING_COLOR: tuple[int, int, int] = (255, 64, 64)

# Formatacao da tabela de linhagens.
#
# Os rotulos de coluna vem do i18n (chaves "col.*") para cada rotulo
# ser traduzido independentemente. As larguras ficam no codigo: o
# layout e recalculado por frame a partir do cabecalho renderizado,
# entao trocar de idioma nao quebra o alinhamento.
_LINEAGE_TABLE_HEADER = (
    ("col.id", 2),
    ("col.hp", 6),
    ("col.lt", 5),
    ("col.gen", 4),
    ("col.pop", 4),
    ("col.score", 6),
)
_LINEAGE_TABLE_ROW_FMT = "{id:>2}  {hp:6.0f}  {lt:5d}  {gen:4d}  {pop:4d}  {score:6.2f}"


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


def _draw_inspection_panel() -> None:
    """Painel lateral com detalhes do bicho selecionado.

    O painel e CATIVO: ocupa sempre os INSPECTION_PANEL_WIDTH pixels
    mais a direita da janela. Isso casa com layout._derive(), que
    reserva essa faixa ao calcular world_width/window_width — mundo e
    painel nunca se sobrepoem. Ancorar em (window_width - width) e a
    casa correta do painel, nao acidente do tamanho atual da janela.
    """
    width = cfg.INSPECTION_PANEL_WIDTH
    x0 = layout.LAYOUT.window_width - width
    total_height = layout.LAYOUT.window_height

    background = pygame.Surface((width, total_height), pygame.SRCALPHA)
    background.fill((*cfg.PANEL_BG_COLOR, 230))
    _screen.blit(background, (x0, 0))
    pygame.draw.line(_screen, cfg.PANEL_BORDER_COLOR, (x0, 0), (x0, total_height), 1)

    padding = 10
    y = padding

    # Cabecalho em duas linhas.
    #
    # O cabecalho e SEMPRE mostrado com o painel aberto, mesmo quando
    # o criterio atual nao casa com ninguem. O operador precisa ver
    # QUAL lente esta ativa para decidir se troca de criterio
    # (esquerda/direita) ou de linhagem (Tab).
    #
    # Linha 1 e o titulo do painel, fonte grande em negrito. Linha 2
    # leva o contador de criterio e o filtro de linhagem, fonte
    # pequena: a string combinada pode ser longa (ex: "[4/10] mais
    # encontros (linhagem: todas)") e a 18px negrito estoura a
    # largura do painel (320px) e e cortada. A 11px cabe confortavel
    # mesmo no pior caso.
    title_line = _font_panel_title.render(
        i18n.t("panel.title"), True, cfg.INSPECTION_HIGHLIGHT_COLOR
    )
    _screen.blit(title_line, (x0 + padding, y))
    y += title_line.get_height() + 2

    nav_hint = _font_panel_small.render(
        i18n.t("panel.hint_navigation"), True, cfg.PANEL_SECONDARY_TEXT_COLOR
    )
    _screen.blit(nav_hint, (x0 + padding, y))
    y += nav_hint.get_height() + 2

    action_hint = _font_panel_small.render(
        i18n.t("panel.hint_actions"), True, cfg.PANEL_SECONDARY_TEXT_COLOR
    )
    _screen.blit(action_hint, (x0 + padding, y))
    y += action_hint.get_height() + 10

    # ------------------------------------------------------------------
    # DESCOBERTA (discovery)
    #
    # Candidato = exatamente o que world.discovery_candidate() retorna
    # para (criterion, lineage_filter) AGORA. Mesmo valor que
    # _draw_highlights() desenha em amarelo e que controls.K_RETURN
    # adota em Enter. Invariante: amarelo == candidate line == Enter.
    #
    # Independe de existir observado. Uma linhagem filtrada extinta
    # produz "nenhum candidato" sem tocar a secao OBSERVANDO.
    # ------------------------------------------------------------------
    discovery_title = _font_panel.render(
        i18n.t("panel.discovery_title"), True, cfg.INSPECTION_HIGHLIGHT_COLOR
    )
    _screen.blit(discovery_title, (x0 + padding, y))
    y += discovery_title.get_height() + 2

    # Contador [i/n] e filtro de linhagem precisam do indice do
    # criterio e do total.
    try:
        i = cfg.CRITERIA_ORDER.index(state.discovery_criterion) + 1
    except ValueError:
        i = 1
    n = len(cfg.CRITERIA_ORDER)

    # Linha 1: contador [i/n] + label do criterio.
    criterion_label = i18n.t(f"criterion.{state.discovery_criterion}")
    discovery_line = _font_panel_small.render(
        f"[{i}/{n}] {criterion_label}", True, cfg.PANEL_SECONDARY_TEXT_COLOR
    )
    _screen.blit(discovery_line, (x0 + padding, y))
    y += discovery_line.get_height() + 2

    # Linha 2: filtro de linhagem.
    lineage_label_d = i18n.t(f"lineage_filter.{state.discovery_lineage_filter}")
    discovery_lineage = _font_panel_small.render(
        f"{i18n.t('panel.lineage')} {lineage_label_d}",
        True, cfg.PANEL_SECONDARY_TEXT_COLOR,
    )
    _screen.blit(discovery_lineage, (x0 + padding, y))
    y += discovery_lineage.get_height() + 2

    # Linha 3: candidato (ou "nenhum candidato").
    candidate = world.discovery_candidate(
        state.discovery_criterion,
        state.discovery_lineage_filter,
    )
    if candidate is None:
        candidate_value = i18n.t("panel.no_candidate")
        candidate_color = cfg.PANEL_SECONDARY_TEXT_COLOR
    else:
        cli, cai = candidate
        candidate_value = f"{agents[cli]['id']} #{int(agents[cli]['ids'][cai])}"
        candidate_color = agents[cli]["color"]
    candidate_label = i18n.t("panel.candidate_label")
    candidate_text = _font_panel.render(
        f"{candidate_label} {candidate_value}", True, candidate_color
    )
    _screen.blit(candidate_text, (x0 + padding, y))
    y += candidate_text.get_height() + 2

    # Linha 4: lembrete do Enter.
    enter_hint = _font_panel_small.render(
        i18n.t("panel.enter_hint"), True, cfg.PANEL_SECONDARY_TEXT_COLOR
    )
    _screen.blit(enter_hint, (x0 + padding, y))
    y += enter_hint.get_height() + 10

    # ------------------------------------------------------------------
    # OBSERVANDO (observation)
    #
    # Secao estavel: identidade do bicho observado, trail, visao,
    # heatmaps. NAO muda por causa de discovery. Sem observado, mostra
    # "nenhum bicho observado" e retorna (a secao DESCOBERTA ja foi
    # renderizada acima).
    # ------------------------------------------------------------------
    observation_title = _font_panel.render(
        i18n.t("panel.observation_title"), True, cfg.INSPECTION_HIGHLIGHT_COLOR
    )
    _screen.blit(observation_title, (x0 + padding, y))
    y += observation_title.get_height() + 2

    critter_id = state.inspected_critter_id
    if critter_id is None:
        warning = _font_panel.render(
            i18n.t("panel.no_selection"), True, cfg.PANEL_TEXT_COLOR
        )
        _screen.blit(warning, (x0 + padding, y))
        return

    snapshot = state.inspection_death_snapshot

    if snapshot is not None:
        # Morto: renderiza a partir do snapshot congelado.
        li = snapshot.lineage_index
        lineage_id = snapshot.lineage_id
        lineage_color = _COLOR_BY_ID.get(lineage_id, cfg.PANEL_TEXT_COLOR)
        critter_matrix = snapshot.agent
        genome = snapshot.genome
        ai = -1  # nao ha indice vivo; nao usado abaixo
    else:
        # Vivo: resolve o ID no estado atual.
        from .world import resolve_critter_id

        resolved = resolve_critter_id(critter_id)
        if resolved is None:
            # ID sumiu sem snapshot: estado invalido. Nao reseleciona
            # (observacao automatica e proibida), apenas avisa.
            warning = _font_panel.render(
                i18n.t("panel.stale_selection"), True, cfg.PANEL_TEXT_COLOR
            )
            _screen.blit(warning, (x0 + padding, y))
            return
        li, ai = resolved
        lineage_id = agents[li]["id"]
        lineage_color = agents[li]["color"]
        critter_matrix = agents[li]["agents"][ai]
        genome = agents[li]["pool"][ai]

    agent = agents[li] if snapshot is None else {"id": lineage_id, "color": lineage_color}

    # Identificacao. Rotulos alinhados a esquerda e valores sempre
    # comecam na mesma coluna (LABEL_WIDTH), para o alinhamento
    # vertical nao quebrar com rotulo mais longo.
    LABEL_WIDTH = 96

    def _draw_info_line(label: str, value: str, color: tuple[int, int, int]) -> None:
        nonlocal y
        label_surface = _font_panel.render(label, True, cfg.PANEL_SECONDARY_TEXT_COLOR)
        value_surface = _font_panel.render(value, True, color)
        _screen.blit(label_surface, (x0 + padding, y))
        _screen.blit(value_surface, (x0 + padding + LABEL_WIDTH, y))
        y += max(label_surface.get_height(), value_surface.get_height()) + 2

    _draw_info_line(i18n.t("panel.id"), str(critter_id), cfg.PANEL_TEXT_COLOR)
    _draw_info_line(i18n.t("panel.lineage"), str(lineage_id), lineage_color)
    if snapshot is not None:
        _draw_info_line(
            i18n.t("panel.status"),
            i18n.t("panel.status_dead", tick=snapshot.tick),
            cfg.PANEL_TEXT_COLOR,
        )
    else:
        _draw_info_line(
            i18n.t("panel.status"),
            i18n.t("panel.status_alive"),
            cfg.PANEL_TEXT_COLOR,
        )
    _draw_info_line(
        i18n.t("panel.hp"), str(int(critter_matrix[INDEX_HP])), cfg.PANEL_TEXT_COLOR
    )
    _draw_info_line(
        i18n.t("panel.time"),
        str(int(critter_matrix[INDEX_TIME])),
        cfg.PANEL_TEXT_COLOR,
    )
    _draw_info_line(
        i18n.t("panel.generation"),
        str(int(critter_matrix[INDEX_GENERATION])),
        cfg.PANEL_TEXT_COLOR,
    )
    _draw_info_line(
        i18n.t("panel.offspring"),
        str(int(critter_matrix[INDEX_OFFSPRING])),
        cfg.PANEL_TEXT_COLOR,
    )
    _draw_info_line(
        i18n.t("panel.encounters"),
        str(int(critter_matrix[INDEX_ENCOUNTERS])),
        cfg.PANEL_TEXT_COLOR,
    )
    _draw_info_line(
        i18n.t("panel.score"),
        f"{critter_matrix[INDEX_COMPOSITE_SCORE]:.3f}",
        cfg.PANEL_TEXT_COLOR,
    )
    _draw_info_line(
        i18n.t("panel.last_action"),
        str(int(critter_matrix[INDEX_LAST_ACTION])),
        cfg.PANEL_TEXT_COLOR,
    )
    _draw_info_line(
        i18n.t("panel.position"),
        f"({int(critter_matrix[INDEX_X])},{int(critter_matrix[INDEX_Y])})",
        cfg.PANEL_TEXT_COLOR,
    )

    y += 6

    # Visao.
    y = _draw_vision(_screen, critter_matrix, x0 + padding, y)

    # Heatmaps de pesos (W1, W2, W3, b1, b2, R) do cerebro. `genome`
    # foi definido acima: linha viva do pool, ou copia do snapshot se
    # morto.
    weights = genome if genome is not None else None
    if weights is None:
        return

    heat_width = width - 2 * padding
    heat_height = 10

    start = 0
    end = start + cfg.INPUT_HIDDEN_WEIGHTS
    y = _draw_heatmap(
        _screen,
        weights[start:end],
        x0 + padding,
        y,
        heat_width,
        heat_height,
        i18n.t("heatmap.w1"),
    )

    start = end
    end = start + cfg.HIDDEN1_HIDDEN2_WEIGHTS
    y = _draw_heatmap(
        _screen,
        weights[start:end],
        x0 + padding,
        y,
        heat_width,
        heat_height,
        i18n.t("heatmap.w2"),
    )

    start = end
    end = start + cfg.HIDDEN2_OUTPUT_WEIGHTS
    y = _draw_heatmap(
        _screen,
        weights[start:end],
        x0 + padding,
        y,
        heat_width,
        heat_height,
        i18n.t("heatmap.w3"),
    )

    start = end
    end = start + cfg.HIDDEN_BIASES
    y = _draw_heatmap(
        _screen,
        weights[start:end],
        x0 + padding,
        y,
        heat_width,
        heat_height,
        i18n.t("heatmap.b1"),
    )

    start = end
    end = start + cfg.HIDDEN_BIASES_2
    y = _draw_heatmap(
        _screen,
        weights[start:end],
        x0 + padding,
        y,
        heat_width,
        heat_height,
        i18n.t("heatmap.b2"),
    )

    start = end
    end = start + cfg.RECURRENCE_WEIGHTS
    y = _draw_heatmap(
        _screen,
        weights[start:end],
        x0 + padding,
        y,
        heat_width,
        heat_height,
        i18n.t("heatmap.r"),
    )


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

    # Icone da janela. Carregado do PNG empacotado junto ao modulo.
    # Falha e nao-fatal: o icone e cosmetico e nao deve impedir o jogo
    # de rodar.
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    try:
        pygame.display.set_icon(pygame.image.load(icon_path))
    except (pygame.error, FileNotFoundError) as e:
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


def _recompute_scale_and_offset(width: int, height: int) -> None:
    """Recalcula _scale, _offset_x, _offset_y para a resolucao dada.

    A largura UTIL e (width - INSPECTION_PANEL_WIDTH): o painel tem
    faixa cativa a direita e o mundo nao pode invadir. Medir o
    letterbox sobre a largura total empurrava o mundo para a direita
    em modo janela e o painel caia em cima da metade direita do
    mundo.

    Preserva a proporcao original (letterbox na dimensao que sobra
    dentro do espaco util). Em modo janela, _scale = 1.0 e
    _offset_x = 0. Em tela cheia num monitor mais largo que
    SCREEN_*, o mundo e centrado no espaco util (a esquerda do
    painel), nao na janela inteira.
    """
    global _scale, _offset_x, _offset_y
    usable_w = width - cfg.INSPECTION_PANEL_WIDTH
    base_w = layout.LAYOUT.world_width * layout.LAYOUT.pixel_scale
    base_h = layout.LAYOUT.world_height * layout.LAYOUT.pixel_scale
    _scale = min(usable_w / base_w, height / base_h)
    _offset_x = (usable_w - int(base_w * _scale)) // 2
    _offset_y = (height - int(base_h * _scale)) // 2


def toggle_fullscreen() -> None:
    """Alterna entre modo janela e tela cheia.

    Em tela cheia, usa pygame.FULLSCREEN (o driver escolhe a
    resolucao nativa do monitor; current_w/current_h sao hint). Ao
    voltar, usa WORLD_WIDTH x WORLD_HEIGHT x PIXEL_SCALE.

    Recalcula _scale/_offset_* e redesenha imediatamente para o
    usuario ver a mudanca mesmo pausado.

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

    _recompute_scale_and_offset(width, height)
    draw()


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
    if not state.inspection_mode:
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
    if not state.inspection_mode:
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
    if not state.inspection_mode:
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


def _measure_block(
    lines: list[tuple[str, tuple[int, int, int], bool]],
) -> tuple[int, int]:
    """Mede a largura/altura de um bloco do HUD.

    `lines` e lista de (texto, cor, negrito). Retorna (width, height)
    em pixels, ja incluindo padding.
    """
    width = 0
    height = 0
    for text, _, bold in lines:
        font = _font_hud_title if bold else _font
        surface = font.render(text, True, (0, 0, 0))
        width = max(width, surface.get_width())
        height += surface.get_height() + 2
    return width, height


def _draw_hud_block(
    x0: int,
    y0: int,
    lines: list[tuple[str, tuple[int, int, int], bool]],
    padding: int = 8,
) -> int:
    """Desenha um bloco do HUD com fundo translucido e borda.

    Retorna o Y logo abaixo do bloco.
    """
    content_width, content_height = _measure_block(lines)
    width = content_width + 2 * padding
    height = content_height + 2 * padding

    background = pygame.Surface((width, height), pygame.SRCALPHA)
    background.fill((*_HUD_BG, 210))
    _screen.blit(background, (x0, y0))
    pygame.draw.rect(_screen, _HUD_BORDER, (x0, y0, width, height), 1)

    y = y0 + padding
    for text, color, bold in lines:
        font = _font_hud_title if bold else _font
        surface = font.render(text, True, color)
        _screen.blit(surface, (x0 + padding, y))
        y += surface.get_height() + 2

    return y0 + height + 6


def _lineage_header_text() -> str:
    """Constroi o cabecalho da tabela de linhagens a partir dos
    rotulos de coluna traduzidos."""
    parts = []
    for key, width in _LINEAGE_TABLE_HEADER:
        label = i18n.t(key)
        parts.append(f"{label:>{width}}")
    return "  ".join(parts)


def _draw_hud() -> None:
    hp = average_hp_per_lineage()
    lt = longest_lifetime()
    gen = max_generation()
    pops = [len(ag["agents"]) for ag in agents]
    scores = average_composite_score_per_lineage()

    zones_txt = format_zones_txt()

    # --- Bloco A: status ---
    #
    # O indicador de gravacao e anexado na primeira linha (tick/speed)
    # quando gravando, para o usuario sempre saber que o GIF esta
    # sendo capturado — mesmo com o painel aberto, que esconde o
    # console. O flag e espelho do estado em recording.py; ler aqui e
    # barato e seguro.
    tick_line = i18n.t(
        "hud.tick_speed", tick=state.tick_count, speed=state.ticks_per_frame
    )
    if state.recording:
        tick_line += "  " + i18n.t("hud.recording_on")

    status_block: list[tuple[str, tuple[int, int, int], bool]] = [
        (
            tick_line,
            _RECORDING_COLOR if state.recording else _HUD_TEXT,
            state.recording,
        ),
        (
            i18n.t("hud.births_deaths", births=state.births, deaths=state.deaths),
            _HUD_TEXT,
            False,
        ),
        (
            i18n.t("hud.save_slot", slot=state.active_save_slot),
            _HUD_SEC,
            False,
        ),
    ]

    # --- Bloco B: parametros de experimento ---
    #
    # O parametro ativo (state.active_param) e destacado com dois
    # sinais: um marcador " <" ao lado do valor e cor amarela na
    # linha toda. So o marcador pode passar batido; so a cor nao diz
    # QUAL valor numa linha compartilhada esta ativo. Juntos sao
    # inequivocos.
    #
    # mut e local compartilham uma linha (hud.mutation), entao cada
    # um tem seu placeholder de marcador. O efeito de HP das zonas
    # tem linha propria, movido para ca do bloco de controles porque
    # e parametro, nao lembrete de tecla.
    marker = i18n.t("hud.active_marker")
    mut_marker = marker if state.active_param == cfg.PARAM_MUTATION else ""
    local_marker = marker if state.active_param == cfg.PARAM_LOCAL_SCALE else ""
    zone_marker = (
        marker if state.active_param == cfg.PARAM_ZONE_HP_EFFECT else ""
    )

    mut_line_color = (
        cfg.INSPECTION_HIGHLIGHT_COLOR
        if state.active_param == cfg.PARAM_MUTATION
        else _HUD_TEXT
    )
    local_line_color = (
        cfg.INSPECTION_HIGHLIGHT_COLOR
        if state.active_param == cfg.PARAM_LOCAL_SCALE
        else _HUD_TEXT
    )
    zone_line_color = (
        cfg.INSPECTION_HIGHLIGHT_COLOR
        if state.active_param == cfg.PARAM_ZONE_HP_EFFECT
        else _HUD_TEXT
    )

    # mut e local compartilham linha: se QUALQUER um estiver ativo, a
    # linha fica amarela. O marcador desambigua qual dos dois.
    mutation_line_color = (
        cfg.INSPECTION_HIGHLIGHT_COLOR
        if state.active_param in (cfg.PARAM_MUTATION, cfg.PARAM_LOCAL_SCALE)
        else _HUD_TEXT
    )

    params_block: list[tuple[str, tuple[int, int, int], bool]] = [
        (
            i18n.t(
                "hud.mutation",
                mut=state.mutation_rate,
                mut_marker=mut_marker,
                mode=cfg.MUTATION_MODE,
                local=state.local_scale_fraction,
                local_marker=local_marker,
                gp=int(cfg.GLOBAL_PROBABILITY * 100),
                gf=int(cfg.GLOBAL_SCALE_FRACTION * 100),
            ),
            mutation_line_color,
            False,
        ),
        (
            i18n.t("hud.zone_hp_param", v=state.zone_hp_effect) + zone_marker,
            zone_line_color,
            False,
        ),
        (
            i18n.t(
                "hud.repro_gates",
                age=cfg.REPRODUCTION_MIN_AGE,
                hp=cfg.REPRODUCTION_HP_GATE,
                score=f"{cfg.REPRODUCTION_MIN_SCORE:.2f}",
                enc=cfg.REPRODUCTION_MIN_ENCOUNTERS,
            ),
            _HUD_SEC,
            False,
        ),
        (
            i18n.t(
                "hud.selection",
                crit=cfg.REPRODUCTION_CRITERION,
                w1=f"{cfg.LONGEVITY_WEIGHT:.1f}",
                w2=f"{cfg.EXPLORATION_WEIGHT:.1f}",
                w3=f"{cfg.INTERACTION_WEIGHT:.1f}",
                w4=f"{cfg.REPRODUCTION_WEIGHT:.1f}",
            ),
            _HUD_TEXT,
            False,
        ),
        (
            i18n.t(
                "hud.environment",
                env=cfg.ENVIRONMENTAL_MODIFIERS,
                zones=zones_txt,
            ),
            _HUD_TEXT,
            False,
        ),
    ]

    # --- Bloco C: controles ---
    controls_block: list[tuple[str, tuple[int, int, int], bool]] = [
        (i18n.t("hud.section_sim"), _HUD_SEC, False),
        (i18n.t("hud.controls_1"), _HUD_SEC, False),
        (i18n.t("hud.controls_2"), _HUD_SEC, False),
        (i18n.t("hud.section_tune"), _HUD_SEC, False),
        (i18n.t("hud.controls_3"), _HUD_SEC, False),
        (i18n.t("hud.controls_4"), _HUD_SEC, False),
        (i18n.t("hud.section_analysis"), _HUD_SEC, False),
        (i18n.t("hud.controls_5"), _HUD_SEC, False),
        (i18n.t("hud.controls_6"), _HUD_SEC, False),
        (i18n.t("hud.controls_7"), _HUD_SEC, False),
        (i18n.t("hud.controls_8"), _HUD_SEC, False),
    ]

    # --- Bloco D: por linhagem ---
    lineage_block: list[tuple[str, tuple[int, int, int], bool]] = [
        (_lineage_header_text(), _HUD_SEC, False),
    ]
    for ag, h, t, g, p, s in zip(agents, hp, lt, gen, pops, scores):
        line = _LINEAGE_TABLE_ROW_FMT.format(
            id=ag["id"], hp=h, lt=t, gen=g, pop=p, score=s
        )
        lineage_block.append((line, ag["color"], False))

    y = 8
    x = 8
    y = _draw_hud_block(x, y, status_block)
    y = _draw_hud_block(x, y, params_block)
    y = _draw_hud_block(x, y, lineage_block)
    y = _draw_hud_block(x, y, controls_block)


def _chart_panel_x0() -> int:
    """Borda esquerda do painel de chart, considerando o painel de
    inspecao (que ocupa a direita da tela)."""
    x0 = layout.LAYOUT.window_width - cfg.CHART_WIDTH - cfg.CHART_MARGIN
    if state.inspection_mode:
        x0 -= cfg.INSPECTION_PANEL_WIDTH
    return x0


def _draw_generic_chart(
    x0: int,
    y0: int,
    width: int,
    height: int,
    series: list[list[tuple[int, float]]],
    title: str,
    labels: list[str],
    colors: list[tuple[int, int, int]],
) -> None:
    """Desenha um line chart com eixos, grade, titulo e legenda.

    `series[k]` e a k-esima serie, lista de (tick, valor). Todas as
    series precisam ter o mesmo numero de pontos (mesmo eixo X).
    `labels[k]` e `colors[k]` correspondem a serie k.

    Layout:
        - Faixa de titulo no topo (~18 px).
        - Area de plot com padding esquerda/inferior para eixos.
        - Legenda no canto superior direito, alinhada a direita.
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


def _draw_metric_chart(x0: int, y0: int) -> None:
    """Desenha o painel unico de chart para a metrica selecionada.

    A tecla M cicla por todas as entradas de cfg.ADVANCED_METRICS,
    incluindo "populacao" como primeira. Nao ha mais painel fixo de
    "populacao por linhagem": populacao e so uma das metricas do
    ciclo, com o mesmo caminho de codigo e a mesma janela temporal
    (METRICS_INTERVAL ticks) das outras.

    Titulos:
      - "populacao por linhagem" para a metrica populacao;
      - "metrica: <label>  (M cicla)" para as demais.
    """
    name = state.selected_metric
    data = list(state.metrics_history.get(name, []))
    readable_label = i18n.t(f"metric.{name}")

    if name == "populacao":
        title = i18n.t("chart.population_title")
    else:
        title = i18n.t("chart.metric_title", label=readable_label)

    if len(data) < 2:
        _draw_generic_chart(
            x0, y0, cfg.CHART_WIDTH, cfg.CHART_HEIGHT, [], title, [], []
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
        x0, y0, cfg.CHART_WIDTH, cfg.CHART_HEIGHT, series, title, labels, colors
    )


def _draw_chart_panel() -> None:
    """Painel unico de chart, canto superior direito.

    Antes eram dois paineis empilhados (populacao fixa no topo,
    metrica ciclando embaixo). Agora e um so: M cicla por todas as
    metricas incluindo populacao, e este painel renderiza a
    selecionada.
    """
    x0 = _chart_panel_x0()
    y0 = cfg.CHART_MARGIN
    _draw_metric_chart(x0, y0)


_RPS_CYCLE: tuple[tuple[str, str, str], ...] = (
    ("R", "B", "G"),
    ("G", "R", "B"),
    ("B", "G", "R"),
)

_COLOR_BY_ID: dict[str, tuple[int, int, int]] = {
    "R": (255, 72, 72),
    "G": (72, 255, 96),
    "B": (80, 140, 255),
}
_TIP_TEXT_COLOR: tuple[int, int, int] = (200, 200, 200)


def _draw_rps_tip() -> None:
    """Dica do ciclo RPS, canto inferior direito.

    A largura da caixa e medida a partir do texto renderizado em vez
    de constante fixa. Isso evita clipping quando as strings mudam
    (ex: a traducao PT usa seta e palavras mais longas). Medir e
    barato: tres linhas x cinco segmentos, uma vez por frame.
    """
    line_height = 18
    padding = 8

    # Pre-renderiza todos os segmentos para medir a linha mais larga.
    rendered_rows: list[list[pygame.Surface]] = []
    max_row_width = 0
    for me, enemy, ally in _RPS_CYCLE:
        segments: list[tuple[str, tuple[int, int, int]]] = [
            (me, _COLOR_BY_ID[me]),
            (i18n.t("rps.enemy"), _TIP_TEXT_COLOR),
            (enemy, _COLOR_BY_ID[enemy]),
            (i18n.t("rps.ally"), _TIP_TEXT_COLOR),
            (ally, _COLOR_BY_ID[ally]),
        ]
        surfaces = [_font_tip.render(text, True, color) for text, color in segments]
        rendered_rows.append(surfaces)
        row_width = sum(s.get_width() for s in surfaces)
        if row_width > max_row_width:
            max_row_width = row_width

    width = max_row_width + 2 * padding
    height = padding * 2 + line_height * len(_RPS_CYCLE)

    x0 = layout.LAYOUT.window_width - width - cfg.CHART_MARGIN
    y0 = layout.LAYOUT.window_height - height - cfg.CHART_MARGIN

    # Desliza para a esquerda se o painel estiver aberto.
    if state.inspection_mode:
        x0 -= cfg.INSPECTION_PANEL_WIDTH

    background = pygame.Surface((width, height), pygame.SRCALPHA)
    background.fill((*_CHART_BG, 220))
    _screen.blit(background, (x0, y0))
    pygame.draw.rect(_screen, _CHART_AXIS, (x0, y0, width, height), 1)

    for i, surfaces in enumerate(rendered_rows):
        y = y0 + padding + i * line_height
        x = x0 + padding
        for surface in surfaces:
            _screen.blit(surface, (x, y))
            x += surface.get_width()


def draw() -> None:
    image = _build_image()
    surface = pygame.surfarray.make_surface(image)

    # Tamanho efetivo do mundo apos a escala corrente. Em modo janela,
    # _scale = 1.0 e o resultado e WORLD_WIDTH x WORLD_HEIGHT x
    # PIXEL_SCALE. Em tela cheia, _scale e < 1.0 (letterbox) e o mundo
    # preenche a tela sem distorcao.
    target_w = int(layout.LAYOUT.world_width * layout.LAYOUT.pixel_scale * _scale)
    target_h = int(layout.LAYOUT.world_height * layout.LAYOUT.pixel_scale * _scale)
    surface = pygame.transform.scale(surface, (target_w, target_h))

    # Fundo preto para as faixas de letterbox (visiveis so em tela
    # cheia quando a proporcao do monitor difere da do mundo).
    _screen.fill((0, 0, 0))
    _screen.blit(surface, (_offset_x, _offset_y))
    _draw_hud()
    _draw_chart_panel()
    _draw_rps_tip()
    if state.inspection_mode:
        _draw_inspection_panel()
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
