# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import numpy as np

from . import config as cfg
from . import layout
from .state import agents
from .world import (
    INDEX_HP,
    INDEX_TIME,
    INDEX_LAST_ACTION,
    INDEX_LOW_HP,
)


_OFFSETS = np.arange(-cfg.VISION_RADIUS, cfg.VISION_RADIUS + 1)
_SIDE = cfg.VISION_SIDE

# Scratch buffer por linhagem para o vetor de entrada da rede.
#
# sense_batch alocava dois arrays grandes por chamada por tick
# (vision e inputs) e concatenava, alocando um terceiro. Com 3
# linhagens a 60 fps era ~105 MB/s de puro churn de alocacao.
#
# Com `index`, sense_batch escreve direto num buffer por linhagem de
# shape [MAX_POPULATION_PER_LINEAGE, NETWORK_INPUTS], alocado uma vez
# na primeira chamada. A populacao nao excede esse teto no fluxo
# normal (a reproducao respeita o ceiling), entao o buffer nunca e
# redimensionado. Fallback defensivo aloca normalmente se n exceder
# o teto, o que so acontece se outro modulo violar a invariante.
#
# Indexado por linhagem (0..TOTAL_LINEAGES-1). Entradas None sao
# preenchidas lazy. A lista em si nunca e redimensionada.
_INPUT_BUFFERS: list[np.ndarray | None] = [None] * cfg.TOTAL_LINEAGES


def _get_input_buffer(index: int) -> np.ndarray:
    """Retorna o scratch buffer por linhagem, alocando na primeira
    chamada.

    O buffer e [MAX_POPULATION_PER_LINEAGE, NETWORK_INPUTS] float32.
    """
    buf = _INPUT_BUFFERS[index]
    if buf is None:
        # Dimensionado por MAX_POPULATION_PER_LINEAGE: o teto e a
        # maior populacao que uma linhagem pode atingir, e o loop de
        # reproducao tem break explicito nesse teto, entao o buffer
        # nunca e o limitante. Sem sentinela "ilimitado"; o config
        # exige MAX_POPULATION_PER_LINEAGE > 0.
        buf = np.empty(
            (cfg.MAX_POPULATION_PER_LINEAGE, cfg.NETWORK_INPUTS),
            dtype=np.float32,
        )
        _INPUT_BUFFERS[index] = buf
    return buf


def _toroidal_coords(xs: np.ndarray, ys: np.ndarray):
    """Retorna [N, SIDE] coordenadas toroidais em X e Y."""
    xs = (xs[:, None] + _OFFSETS[None, :]) % layout.LAYOUT.world_width
    ys = (ys[:, None] + _OFFSETS[None, :]) % layout.LAYOUT.world_height
    return xs, ys


def _vision_batch(
    xs: np.ndarray, ys: np.ndarray, out: np.ndarray | None = None
) -> np.ndarray:
    """[N, VISION_INPUTS] — apenas a parte visual (um canal por
    linhagem).

    Se `out` for fornecido, o bloco de visao e escrito direto em
    `out[:n, :VISION_INPUTS]` (viewed como [n, SIDE, SIDE, CHANNELS])
    e uma view desse slice e retornada. Se `out` for None, aloca novo
    array. Quem decide o caminho e sense_batch.
    """
    xs = np.asarray(xs, dtype=np.int64)
    ys = np.asarray(ys, dtype=np.int64)
    n = xs.shape[0]

    cx, cy = _toroidal_coords(xs, ys)  # [N, SIDE] each

    if out is None:
        vision = np.empty((n, _SIDE, _SIDE, cfg.VISION_CHANNELS), dtype=np.float32)
    else:
        # View das primeiras n linhas do buffer como
        # [n, SIDE, SIDE, CHANNELS].
        vision = out[:n, : cfg.VISION_INPUTS].reshape(
            n, _SIDE, _SIDE, cfg.VISION_CHANNELS
        )

    for k, agent in enumerate(agents):
        # field tem shape [WORLD_WIDTH, WORLD_HEIGHT]; indexing
        # avancado:
        # field[cx[:, :, None], cy[:, None, :]] -> [N, SIDE, SIDE]
        vision[..., k] = agent["field"][cx[:, :, None], cy[:, None, :]]

    return vision.reshape(n, -1)


def _internal_state_batch(
    matrix: np.ndarray,
    *,
    low_hp_threshold: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Calcula os inputs de estado interno e o flag low-HP.

    matrix: [N, AGENT_COLUMNS] float32. Nao muta o array do chamador.

    Retorna:
        inputs: [N, INTERNAL_STATE_INPUTS] float32 com
                (hp_norm, time_norm, action_norm, low_hp).
        low_hp: [N] float32 com o flag recem-calculado, para o
                chamador persistir em INDEX_LOW_HP se quiser manter a
                coluna em sincronia com o que a rede consumiu.

    Note: o flag low-HP e retornado em vez de escrito em `matrix` de
    proposito. A versao anterior mutava `matrix` in-place, um efeito
    colateral escondido dentro de um helper de "leitura". Agora o
    chamador decide se persiste.
    """
    hp = matrix[:, INDEX_HP].astype(np.float32)
    time = matrix[:, INDEX_TIME].astype(np.float32)
    action = matrix[:, INDEX_LAST_ACTION].astype(np.float32)

    hp_norm = hp / float(cfg.INITIAL_HP)
    time_norm = time / float(cfg.INITIAL_HP)
    # last_action esta sempre em 0..POSSIBLE_MOVES-1 (iniciado no
    # centro).
    action_norm = action / float(cfg.POSSIBLE_MOVES - 1)

    low_hp = (hp < float(low_hp_threshold)).astype(np.float32)

    inputs = np.stack([hp_norm, time_norm, action_norm, low_hp], axis=1)
    return inputs, low_hp


def sense_batch(
    xs: np.ndarray,
    ys: np.ndarray,
    matrix: np.ndarray,
    index: int | None = None,
    *,
    low_hp_threshold: int,
) -> np.ndarray:
    """Vetor float [N, NETWORK_INPUTS].

    Concatena:
      [ vision SIDE×SIDE×3 | estado interno (4) ]

    `matrix` e `low_hp_threshold` sao obrigatorios: toda percepcao
    produtiva inclui o estado interno real do organismo. O flag low-HP
    e recalculado e escrito em `matrix[:, INDEX_LOW_HP]` para manter a
    coluna sincronizada com o valor efetivamente consumido pela rede.

    Contrato de `index`:
        - Se for um indice valido (0..TOTAL_LINEAGES-1) E n <=
          MAX_POPULATION_PER_LINEAGE, o resultado e escrito num
          scratch buffer por linhagem e uma VIEW das primeiras n
          linhas e retornada. O chamador DEVE consumir o resultado
          antes da proxima chamada com o mesmo `index`.
        - Se None, ou n excede o teto, cai no caminho de alocacao
          normal. Esse caminho alternativo e operacional e nao altera a semantica
          dos inputs internos.

    O caminho com buffer e o caminho critico: elimina churn de alocacao da
    implementacao anterior baseada em concatenate.
    """
    xs = np.asarray(xs, dtype=np.int64)
    ys = np.asarray(ys, dtype=np.int64)
    matrix = np.asarray(matrix)
    n = xs.shape[0]

    use_buffer = (
        index is not None
        and 0 <= index < cfg.TOTAL_LINEAGES
        and n <= cfg.MAX_POPULATION_PER_LINEAGE
    )

    if use_buffer:
        out = _get_input_buffer(index)[:n]
        _vision_batch(xs, ys, out=out)
        internal, low_hp = _internal_state_batch(
            matrix,
            low_hp_threshold=low_hp_threshold,
        )
        out[:, cfg.VISION_INPUTS :] = internal
        matrix[:, INDEX_LOW_HP] = low_hp.astype(matrix.dtype, copy=False)
        return out

    # Caminho alternativo de alocacao: usado quando nao ha indice de scratch ou
    # quando um chamador viola o teto operacional do buffer.
    vision = _vision_batch(xs, ys)
    internal, low_hp = _internal_state_batch(
        matrix,
        low_hp_threshold=low_hp_threshold,
    )
    matrix[:, INDEX_LOW_HP] = low_hp.astype(matrix.dtype, copy=False)
    return np.concatenate([vision, internal], axis=1)