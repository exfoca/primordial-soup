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


def _internal_state_batch(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
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

    low_hp = (hp < float(cfg.LOW_HP_THRESHOLD)).astype(np.float32)

    inputs = np.stack([hp_norm, time_norm, action_norm, low_hp], axis=1)
    return inputs, low_hp


def sense_batch(
    xs: np.ndarray,
    ys: np.ndarray,
    matrix: np.ndarray | None = None,
    index: int | None = None,
) -> np.ndarray:
    """Vetor float [N, NETWORK_INPUTS].

    Concatena:
      [ vision SIDE×SIDE×3 | estado interno (4) ]

    Contrato de `matrix`:
        - Se fornecida, o flag low-HP e recalculado e ESCRITO em
          `matrix[:, INDEX_LOW_HP]` para a coluna refletir o que a
          rede consumiu neste tick. Esta e a UNICA mutacao in-place
          da funcao, feita explicitamente aqui.
        - Se None, o estado interno e zerado (fallback de
          compatibilidade com chamadas antigas de `sense`) e NENHUMA
          mutacao ocorre.

    Contrato de `index`:
        - Se for um indice valido (0..TOTAL_LINEAGES-1) E n <=
          MAX_POPULATION_PER_LINEAGE, o resultado e escrito num
          scratch buffer por linhagem e uma VIEW das primeiras n
          linhas e retornada. O chamador DEVE consumir o resultado
          antes da proxima chamada com o mesmo `index` — senao ela
          sobrescreve. Na pratica o unico chamador e
          evolution.evaluate_and_move, que consome imediatamente.
        - Se None, ou n excede o teto, cai no caminho de alocacao
          normal. Mantem `sense(x, y)` (sem index) e qualquer chamada
          fora da invariante corretos.

    O caminho com buffer e o hot path: elimina ~105 MB/s de churn de
    alocacao da implementacao anterior baseada em concatenate.
    """
    xs = np.asarray(xs, dtype=np.int64)
    ys = np.asarray(ys, dtype=np.int64)
    n = xs.shape[0]

    # Decide se o caminho com buffer esta disponivel nesta chamada.
    use_buffer = (
        index is not None
        and 0 <= index < cfg.TOTAL_LINEAGES
        and n <= cfg.MAX_POPULATION_PER_LINEAGE
    )

    if use_buffer:
        out = _get_input_buffer(index)[:n]
        vision = _vision_batch(xs, ys, out=out)
        if matrix is None:
            out[:, cfg.VISION_INPUTS :] = 0.0
        else:
            matrix = np.asarray(matrix)
            internal, low_hp = _internal_state_batch(matrix)
            out[:, cfg.VISION_INPUTS :] = internal
            matrix[:, INDEX_LOW_HP] = low_hp.astype(matrix.dtype, copy=False)
        # `out` ja contem [vision | internal] nas colunas certas.
        # `vision` era uma view de out[:, :VISION_INPUTS], entao
        # escrever o bloco interno acima nao a perturbou.
        return out

    # Fallback: caminho de alocacao original. Usado por sense(x, y) e
    # por qualquer chamada sem index ou acima do teto.
    vision = _vision_batch(xs, ys)
    if matrix is None:
        internal = np.zeros((n, cfg.INTERNAL_STATE_INPUTS), dtype=np.float32)
    else:
        matrix = np.asarray(matrix)
        internal, low_hp = _internal_state_batch(matrix)
        matrix[:, INDEX_LOW_HP] = low_hp.astype(matrix.dtype, copy=False)
    return np.concatenate([vision, internal], axis=1)


def sense(x: int, y: int) -> np.ndarray:
    """Compatibilidade: um unico bicho, sem estado interno (zeros).

    Para chamadores que so precisam do vetor de visao e nao tem uma
    matriz de agentes em maos. O bloco interno vai zerado e nenhuma
    mutacao ocorre.
    """
    return sense_batch(np.array([x], dtype=np.int64), np.array([y], dtype=np.int64))[0]
