# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import numpy as np

from . import config as cfg
from . import layout
from .world import INDEX_X, INDEX_Y


def _build_deltas() -> np.ndarray:
    """Vizinhanca de Moore 3x3, linha a linha.

    Indices:
        0 1 2
        3 4 5
        6 7 8
    O centro (4) e "ficar parado".
    """
    deltas = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            deltas.append((dx, dy))
    return np.array(deltas, dtype=np.int64)


_DELTAS = _build_deltas()


def move(critter: list, index: int) -> None:
    """Aplica movimento toroidal. critter = [hp, x, y, time_alive]."""
    dx, dy = _DELTAS[index]
    critter[INDEX_X] = (critter[INDEX_X] + int(dx)) % layout.LAYOUT.world_width
    critter[INDEX_Y] = (critter[INDEX_Y] + int(dy)) % layout.LAYOUT.world_height


def move_batch(matrix: np.ndarray, choices: np.ndarray) -> None:
    """Aplica movimento toroidal em batch, in-place.

    matrix:  [N, AGENT_COLUMNS] float32
    choices: [N] int (0..POSSIBLE_MOVES-1)
    """
    choices = np.asarray(choices, dtype=np.int64)
    deltas = _DELTAS[choices]  # [N,2]
    matrix[:, INDEX_X] = (
        matrix[:, INDEX_X] + deltas[:, 0]
    ) % layout.LAYOUT.world_width
    matrix[:, INDEX_Y] = (
        matrix[:, INDEX_Y] + deltas[:, 1]
    ) % layout.LAYOUT.world_height
