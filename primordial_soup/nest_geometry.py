# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Geometria canonica dos ninhos.

Modulo de baixo nivel: puro, sem estado global. Nao importa config,
state, world, layout nem pygame. Todas as dimensoes (width, height,
radius) sao recebidas explicitamente, para que as funcoes operem
tanto sobre o mundo ativo quanto sobre dados ainda nao commitados
(ex: load transacional validando um payload antes do COMMIT).

Convencao de coordenadas: (x, y), consistente com field[x, y] e
zones[x, y] do resto do projeto. NAO converter para (row, column).

Autoridade unica de:

    distancia toroidal entre duas posicoes
    offsets discretos de disco
    offsets discretos de anel
    wrap toroidal de offsets
    pertencimento ao ninho (escalar e vetorizado)
    sobreposicao entre dois ninhos
    interseccao ninho x zona

Os patches seguintes (protecao ecologica, geracao de ninhos, spawn
de descendentes, rendering do anel, validacao no loader) DEVEM
consumir esta API em vez de reimplementar qualquer destas operacoes.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence, TypeAlias

import numpy as np


NestCenter: TypeAlias = tuple[int, int]
NestCenters: TypeAlias = tuple[NestCenter, ...]


# ---------------------------------------------------------------------------
# Validacao minima
# ---------------------------------------------------------------------------


def _validate_dimensions(width: int, height: int) -> None:
    if width <= 0:
        raise ValueError(f"width deve ser > 0, recebido {width}.")
    if height <= 0:
        raise ValueError(f"height deve ser > 0, recebido {height}.")


def _validate_radius(radius: int) -> None:
    if radius < 0:
        raise ValueError(f"radius deve ser >= 0, recebido {radius}.")


# ---------------------------------------------------------------------------
# Offsets discretos do disco e do anel
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def nest_disk_offsets(radius: int) -> tuple[tuple[int, int], ...]:
    """Offsets inteiros (dx, dy) com dx**2 + dy**2 <= radius**2.

    Ordem lexicografica determinista: dx crescente, depois dy
    crescente. Esta e a autoridade discreta do disco funcional do
    ninho; a mesma semantica alimenta protecao, geracao e validacao.

    Cacheado: NEST_RADIUS e NEST_SPAWN_RADIUS sao estaticos e o
    resultado e reutilizado por multiplos subsistemas. Retorno
    imutavel (tuple de tuples), para o cache nao vazar referencia
    mutavel.
    """
    _validate_radius(radius)
    r2 = radius * radius
    offsets: list[tuple[int, int]] = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx * dx + dy * dy <= r2:
                offsets.append((dx, dy))
    return tuple(offsets)


@lru_cache(maxsize=None)
def nest_ring_offsets(radius: int) -> tuple[tuple[int, int], ...]:
    """Offsets inteiros (dx, dy) na borda discreta do disco.

    Anel fino: (radius - 1)**2 < dx**2 + dy**2 <= radius**2, para
    radius > 0. O anel e subconjunto estrito do disco: garantir isso
    e o ponto do teste. Para radius == 0 o anel e vazio.

    Derivado da mesma definicao de disco: o rendering futuro NAO
    deve desenhar uma circunferencia com logica propria.
    """
    _validate_radius(radius)
    if radius == 0:
        return ()
    r2 = radius * radius
    inner = (radius - 1) * (radius - 1)
    offsets: list[tuple[int, int]] = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            d2 = dx * dx + dy * dy
            if inner < d2 <= r2:
                offsets.append((dx, dy))
    return tuple(offsets)


# ---------------------------------------------------------------------------
# Wrap toroidal
# ---------------------------------------------------------------------------


def wrapped_points(
    center: NestCenter,
    offsets: Sequence[tuple[int, int]] | np.ndarray,
    *,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Aplica wrap toroidal de `center + offset` em cada offset.

    Retorna (xs, ys) como ndarrays int64 de shape (N,), prontos para
    indexacao de field[xs, ys] / zones[xs, ys].

    Aceita dois formatos de offsets, ambos validados:

        Sequence de pares (tuple[tuple[int, int], ...])
            formato nativo de nest_disk_offsets / nest_ring_offsets

        np.ndarray de shape (N, 2) e dtype int
            util quando o chamador ja materializou a matriz

    Shape invalido levanta ValueError explicito, em vez de deixar o
    NumPy falhar com mensagem obscura.
    """
    _validate_dimensions(width, height)
    cx, cy = int(center[0]), int(center[1])

    if isinstance(offsets, np.ndarray):
        if offsets.ndim != 2 or offsets.shape[1] != 2:
            raise ValueError(
                "wrapped_points: ndarray de offsets deve ter shape "
                f"(N, 2), recebido {offsets.shape}."
            )
        off = offsets.astype(np.int64, copy=False)
    else:
        off = np.asarray(offsets, dtype=np.int64)
        if off.size == 0:
            off = np.empty((0, 2), dtype=np.int64)
        elif off.ndim != 2 or off.shape[1] != 2:
            raise ValueError(
                "wrapped_points: sequencia de offsets deve ter shape "
                f"(N, 2), recebido {off.shape}."
            )

    dx = off[:, 0]
    dy = off[:, 1]
    xs = (cx + dx) % width
    ys = (cy + dy) % height
    return xs.astype(np.int64, copy=False), ys.astype(np.int64, copy=False)


# ---------------------------------------------------------------------------
# Pertencimento ao ninho
# ---------------------------------------------------------------------------


def is_position_inside_nest(
    x: int,
    y: int,
    center: NestCenter,
    *,
    width: int,
    height: int,
    radius: int,
) -> bool:
    """True se (x, y) pertence ao disco discreto do ninho.

    Distancia toroidal minima por eixo:

        dx = abs(x - cx); dx = min(dx, width - dx)
        dy = abs(y - cy); dy = min(dy, height - dy)

    Pertencimento: dx**2 + dy**2 <= radius**2 (limite inclusivo).

    Funcao escalar: usada para validacao, diagnostico e triad
    eligibility. No hot path de protecao, usar a versao vetorizada
    positions_inside_nest.
    """
    _validate_dimensions(width, height)
    _validate_radius(radius)

    cx, cy = int(center[0]), int(center[1])
    dx = abs(int(x) - cx)
    dx = min(dx, width - dx)
    dy = abs(int(y) - cy)
    dy = min(dy, height - dy)
    return dx * dx + dy * dy <= radius * radius


def positions_inside_nest(
    xs: np.ndarray,
    ys: np.ndarray,
    center: NestCenter,
    *,
    width: int,
    height: int,
    radius: int,
) -> np.ndarray:
    """Versao vetorizada de is_position_inside_nest.

    xs, ys: ndarrays 1-D de mesmo shape (N,), dtype inteiro.

    Retorna bool[N]. Sem loop Python sobre os individuos.

    Contrato: para qualquer (x, y) do par (xs, ys), o resultado
    coincide elemento a elemento com is_position_inside_nest(x, y,
    center, ...). Um teste protege esta equivalencia.
    """
    _validate_dimensions(width, height)
    _validate_radius(radius)

    xs = np.asarray(xs)
    ys = np.asarray(ys)
    if xs.shape != ys.shape:
        raise ValueError(
            "positions_inside_nest: xs e ys devem ter o mesmo shape, "
            f"recebidos {xs.shape} e {ys.shape}."
        )
    if xs.ndim != 1:
        raise ValueError(
            "positions_inside_nest: xs/ys devem ser 1-D, "
            f"recebido ndim={xs.ndim}."
        )

    cx, cy = int(center[0]), int(center[1])
    dx = np.abs(xs.astype(np.int64, copy=False) - cx)
    dx = np.minimum(dx, width - dx)
    dy = np.abs(ys.astype(np.int64, copy=False) - cy)
    dy = np.minimum(dy, height - dy)
    return (dx * dx + dy * dy) <= (radius * radius)


# ---------------------------------------------------------------------------
# Sobreposicao entre ninhos
# ---------------------------------------------------------------------------


def nests_overlap(
    first: NestCenter,
    second: NestCenter,
    *,
    width: int,
    height: int,
    radius: int,
) -> bool:
    """True se os dois discos discretos compartilham ao menos uma celula.

    Semantica: ocupacao DISCRETA de celulas, nao geometria continua.
    Implementacao deliberada:

        1. offsets discretos do primeiro disco;
        2. wrap toroidal;
        3. teste vetorial contra o segundo disco;
        4. any().

    A semantica de overlap e, por construcao, identica a usada por
    is_position_inside_nest. Trocar por "distancia_entre_centros <=
    2*radius" seria divergente em fronteiras discretas e quebraria a
    coincidencia com a protecao futura.

    Tangencia discreta conta como overlap: se duas bordas
    compartilham celula, e sobreposicao.
    """
    _validate_dimensions(width, height)
    _validate_radius(radius)

    offsets = nest_disk_offsets(radius)
    if not offsets:
        return False
    xs, ys = wrapped_points(first, offsets, width=width, height=height)
    inside = positions_inside_nest(
        xs, ys, second, width=width, height=height, radius=radius
    )
    return bool(np.any(inside))


# ---------------------------------------------------------------------------
# Interseccao ninho x zona
# ---------------------------------------------------------------------------


def nest_intersects_zone(
    center: NestCenter,
    zones: np.ndarray,
    *,
    radius: int,
) -> bool:
    """True se o disco discreto do ninho intersecta qualquer zona ativa.

    `zones` e passado como argumento explicito: esta funcao NAO le
    state.zones. Isso e obrigatorio para o load transacional futuro,
    que validara ninhos contra parsed_zones ANTES do COMMIT, sem
    tocar no runtime.

    Shape de zones e a autoridade das dimensoes do mundo; width e
    height sao derivados de zones.shape, garantindo consistencia
    topologica entre a mascara e a geometria.
    """
    _validate_radius(radius)

    zones_arr = np.asarray(zones)
    if zones_arr.ndim != 2:
        raise ValueError(
            f"nest_intersects_zone: zones deve ser 2-D, "
            f"recebido ndim={zones_arr.ndim}."
        )
    if zones_arr.dtype != np.bool_:
        raise ValueError(
            "nest_intersects_zone: zones deve ter dtype=bool, "
            f"recebido {zones_arr.dtype}."
        )

    height = zones_arr.shape[1]
    width = zones_arr.shape[0]

    offsets = nest_disk_offsets(radius)
    if not offsets:
        return False
    xs, ys = wrapped_points(center, offsets, width=width, height=height)
    return bool(np.any(zones_arr[xs, ys]))
