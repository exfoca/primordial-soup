# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Derivacao de layout a partir do tamanho de tela declarado.

Usuario declara SCREEN_WIDTH / SCREEN_HEIGHT em config.py; este modulo
deriva PIXEL_SCALE, WORLD_WIDTH, WORLD_HEIGHT, WINDOW_WIDTH e
WINDOW_HEIGHT para o mundo preencher o espaco disponivel.

O painel lateral tem largura FIXA e ocupa sempre a faixa direita,
independente de qual painel esta focado. Mundo e painel nunca se
sobrepoem.

Regras (ver _derive):
  1. available_w = SCREEN_WIDTH - INSPECTION_PANEL_WIDTH
     available_h = SCREEN_HEIGHT
  2. PIXEL_SCALE comeca em TARGET_PIXEL_SCALE e cai para 1 enquanto
     o mundo ficaria abaixo de MIN_WORLD_*.
  3. WORLD_WIDTH  = available_w // PIXEL_SCALE
     WORLD_HEIGHT = available_h // PIXEL_SCALE
  4. WINDOW_WIDTH  = WORLD_WIDTH  * PIXEL_SCALE + INSPECTION_PANEL_WIDTH
     WINDOW_HEIGHT = WORLD_HEIGHT * PIXEL_SCALE

A janela e sempre <= SCREEN_*. O leftover e 0 quando available_* sao
multiplos de PIXEL_SCALE; caso contrario sobra o resto da divisao.

Sem resize em runtime. F11 alterna fullscreen usando a resolucao do
monitor, mas o mundo NAO e re-derivado: o letterbox de rendering.py
cuida do ajuste visual.

NOTA DE DESIGN: este modulo NAO escreve de volta em config. As
constantes derivadas vivem em LAYOUT. Isso mantem config.py como
fonte unica da verdade e isola a derivacao num lugar testavel.
"""

from __future__ import annotations
from collections import namedtuple

from . import config as cfg


Layout = namedtuple(
    "Layout",
    [
        "pixel_scale",
        "world_width",
        "world_height",
        "window_width",
        "window_height",
    ],
)


def _derive() -> Layout:
    """Deriva o layout a partir de cfg.SCREEN_* e cfg.INSPECTION_PANEL_WIDTH.

    Retorna um Layout nomeado. Emite aviso (mas nao rejeita a tela) se,
    mesmo em escala 1, o mundo ficaria abaixo de cfg.MIN_WORLD_*. Isso
    so ocorre em telas muito pequenas.

    Levanta ValueError se a tela for menor que o painel (available_w
    <= 0), que e erro de configuracao sem solucao razoavel.
    """
    available_w = cfg.SCREEN_WIDTH - cfg.INSPECTION_PANEL_WIDTH
    available_h = cfg.SCREEN_HEIGHT

    if available_w <= 0:
        raise ValueError(
            f"SCREEN_WIDTH ({cfg.SCREEN_WIDTH}) <= INSPECTION_PANEL_WIDTH "
            f"({cfg.INSPECTION_PANEL_WIDTH}): nao ha espaco para o mundo. "
            f"Aumente SCREEN_WIDTH ou reduza o painel."
        )
    if available_h <= 0:
        raise ValueError(
            f"SCREEN_HEIGHT ({cfg.SCREEN_HEIGHT}) <= 0: sem espaco vertical."
        )

    scale = cfg.TARGET_PIXEL_SCALE
    while scale > 1:
        if (available_w // scale >= cfg.MIN_WORLD_WIDTH and
                available_h // scale >= cfg.MIN_WORLD_HEIGHT):
            break
        scale -= 1

    world_w = available_w // scale
    world_h = available_h // scale

    # Aviso: caiu para escala 1 e ainda assim o mundo ficou abaixo do
    # minimo. Aceito, mas registrado.
    if (world_w < cfg.MIN_WORLD_WIDTH or world_h < cfg.MIN_WORLD_HEIGHT):
        print(
            f"[layout] aviso: tela {cfg.SCREEN_WIDTH}x{cfg.SCREEN_HEIGHT} "
            f"com painel {cfg.INSPECTION_PANEL_WIDTH} gera mundo "
            f"{world_w}x{world_h}, abaixo do minimo "
            f"{cfg.MIN_WORLD_WIDTH}x{cfg.MIN_WORLD_HEIGHT}. "
            f"Rodando mesmo assim (escala {scale})."
        )

    return Layout(
        pixel_scale=scale,
        world_width=world_w,
        world_height=world_h,
        window_width=world_w * scale + cfg.INSPECTION_PANEL_WIDTH,
        window_height=world_h * scale,
    )


LAYOUT = _derive()


# Invariantes: mesmas regras do config, mas sobre o resultado da
# derivacao. Se algum assert falhar, o import quebra imediatamente.

assert LAYOUT.pixel_scale >= 1, "pixel_scale deve ser >= 1"
assert LAYOUT.world_width > 0, "world_width deve ser > 0"
assert LAYOUT.world_height > 0, "world_height deve ser > 0"
assert LAYOUT.window_width <= cfg.SCREEN_WIDTH, (
    f"window_width ({LAYOUT.window_width}) > SCREEN_WIDTH ({cfg.SCREEN_WIDTH})"
)
assert LAYOUT.window_height <= cfg.SCREEN_HEIGHT, (
    f"window_height ({LAYOUT.window_height}) > SCREEN_HEIGHT ({cfg.SCREEN_HEIGHT})"
)
assert LAYOUT.window_width == (
    LAYOUT.world_width * LAYOUT.pixel_scale + cfg.INSPECTION_PANEL_WIDTH
), "window_width inconsistente com world_width * pixel_scale + painel"
assert LAYOUT.window_height == LAYOUT.world_height * LAYOUT.pixel_scale, (
    "window_height inconsistente com world_height * pixel_scale"
)
