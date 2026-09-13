# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Gravacao de tela para GIF animado usando Pillow.

O gravador captura o frame COMPLETO renderizado (mundo + HUD + charts
+ painel) logo apos pygame.display.flip(), entao o GIF mostra
exatamente o que o usuario ve na tela.

Design:
  - Frames sao armazenados como PIL.Image em memoria, reduzidos por
    cfg.RECORDING_SCALE para manter a memoria limitada.
  - Em stop(), os frames sao quantizados numa paleta compartilhada e
    salvos como um unico GIF animado via PIL.Image.save(...,
    save_all=True).
  - Nao ha modo streaming-para-disco: GIF e formato single-file e o
    PIL precisa de todos os frames juntos para construir a paleta.
    Para gravacoes longas, baixe RECORDING_SCALE ou RECORDING_COLORS.

Por que nao pygame.image.save() por frame? Produziria N PNGs e exigiria
ferramenta externa (ffmpeg, gifsicle) para montar. O ponto do modulo e
produzir um GIF unico sem dependencia externa alem do Pillow.

Pillow e importado lazy (dentro de start()) para quem nunca aperta G
nao pagar o custo do import e nao precisar do Pillow instalado para
rodar a simulacao. A dependencia e opcional.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import numpy as np
import pygame

from . import config as cfg
from . import layout
from . import state
from . import i18n

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


# Estado do gravador no nivel do modulo. Deliberadamente FORA de
# state.py: o gravador e ferramenta do usuario, nao parte da
# simulacao.
_frames: list["PILImage"] = []
_target_size: tuple[int, int] | None = None
_started: bool = False


def is_recording() -> bool:
    """True se ha gravacao em andamento."""
    return _started


def start() -> None:
    """Inicia a gravacao. Idempotente: chamar start() duas vezes e
    no-op."""
    global _started, _target_size
    if _started:
        return

    # Import lazy: quem nunca grava nao precisa do Pillow instalado.
    try:
        from PIL import Image  # noqa: F401  (imported for the side effect of failing early)
    except ImportError as e:
        print(
            "[recording] Pillow is not installed. Install it with: "
            "pip install Pillow   (or add it to your environment)."
        )
        print(f"[recording] import error: {e!r}")
        return

    _frames.clear()
    _target_size = (
        max(
            1,
            int(
                layout.LAYOUT.world_width
                * layout.LAYOUT.pixel_scale
                * cfg.RECORDING_SCALE
            ),
        ),
        max(
            1,
            int(
                layout.LAYOUT.world_height
                * layout.LAYOUT.pixel_scale
                * cfg.RECORDING_SCALE
            ),
        ),
    )
    _started = True
    state.recording = True
    print(
        i18n.t(
            "log.recording_start",
            path=cfg.RECORDING_FILE,
            fps=cfg.RECORDING_FPS,
            max=cfg.RECORDING_MAX_FRAMES,
            scale=cfg.RECORDING_SCALE,
        )
    )


def stop() -> None:
    """Para a gravacao e escreve o GIF. Idempotente."""
    global _started
    if not _started:
        return

    _started = False
    state.recording = False

    if not _frames:
        print(i18n.t("log.recording_empty"))
        return

    try:
        from PIL import Image
    except ImportError as e:
        print(f"[recording] Pillow disappeared mid-recording: {e!r}")
        return

    path = cfg.RECORDING_FILE
    duration_ms = max(1, int(1000 / cfg.RECORDING_FPS))

    # Converte todo frame para modo P (paleta) com paleta
    # COMPARTILHADA. O escritor GIF do PIL exige todos os frames no
    # mesmo modo; converter para "P" usando o primeiro frame como
    # referencia e o truque padrao. Image.convert("P",
    # palette=Image.ADAPTIVE, colors=N) por frame daria a cada um sua
    # propria paleta, o que o GIF permite mas a maioria dos viewers
    # renderiza mal (flicker). Usar a paleta do primeiro frame como
    # referencia da resultado estavel, sem artefatos.
    first = _frames[0]
    if first.mode != "P":
        first = first.convert("P", palette=Image.ADAPTIVE, colors=cfg.RECORDING_COLORS)

    converted = [first]
    for frame in _frames[1:]:
        if frame.mode != "P":
            frame = frame.convert(
                "P", palette=Image.ADAPTIVE, colors=cfg.RECORDING_COLORS
            )
        converted.append(frame)

    try:
        converted[0].save(
            path,
            save_all=True,
            append_images=converted[1:],
            duration=duration_ms,
            loop=cfg.RECORDING_LOOP,
            optimize=False,
            disposal=2,
        )
    except OSError as e:
        print(i18n.t("log.recording_save_fail", e=repr(e)))
        return

    size_bytes = os.path.getsize(path) if os.path.exists(path) else 0
    print(
        i18n.t(
            "log.recording_ok",
            path=path,
            n=len(_frames),
            fps=cfg.RECORDING_FPS,
            kb=size_bytes // 1024,
        )
    )

    _frames.clear()


def toggle() -> None:
    """Inicia se parado, para se iniciado."""
    if _started:
        stop()
    else:
        start()


def capture(surface: pygame.Surface) -> None:
    """Captura um frame da surface do Pygame.

    Chamado por rendering.draw() apos pygame.display.flip(). Nao faz
    nada se nao houver gravacao em andamento ou se o budget de frames
    acabou.

    A surface vira array NumPy via surfarray (rapido, sem string
    intermediaria), transposta (os eixos do Pygame sao invertidos
    em relacao ao PIL), reduzida por RECORDING_SCALE e armazenada
    como PIL.Image em modo RGB.
    """
    if not _started:
        return
    if len(_frames) >= cfg.RECORDING_MAX_FRAMES:
        print(i18n.t("log.recording_full", max=cfg.RECORDING_MAX_FRAMES))
        stop()
        return

    try:
        from PIL import Image
    except ImportError:
        # Nao deveria acontecer (start() ja verificou), mas defensivo.
        stop()
        return

    # pygame.surfarray.array3d retorna [W, H, 3]; transpomos para
    # [H, W, 3]. Pygame e PIL usam Y crescente para baixo, entao nao
    # precisa de flip vertical (historicamente confuso; so o transpose
    # ja e correto).
    array = pygame.surfarray.array3d(surface)
    array = np.transpose(array, (1, 0, 2))
    image = Image.fromarray(array, mode="RGB")

    if _target_size is not None and image.size != _target_size:
        image = image.resize(_target_size, Image.BILINEAR)

    _frames.append(image)
