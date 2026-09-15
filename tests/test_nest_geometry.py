"""Testes da geometria canonica dos ninhos.

Este arquivo cobre apenas a geometria em isolamento: sem pygame, sem
simulation loop, sem bootstrap. A propriedade central e que a
semantica discreta do disco e compartilhada por todas as operacoes
(pertencimento escalar, pertencimento vetorizado, overlap, interseccao
com zona).
"""

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import nest_geometry as g


# ---------------------------------------------------------------------------
# Offsets de spawn
# ---------------------------------------------------------------------------


def test_disk_offsets_radius_1_is_plus_shape():
    """NEST_SPAWN_RADIUS = 1 produz o centro mais os quatro vizinhos
    cardinais. Sem diagonais: sqrt(1^2 + 1^2) > 1."""
    expected = {(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)}
    assert set(g.nest_disk_offsets(1)) == expected


def test_disk_offsets_radius_0_is_single_center():
    assert g.nest_disk_offsets(0) == ((0, 0),)


def test_disk_offsets_are_cached():
    a = g.nest_disk_offsets(5)
    b = g.nest_disk_offsets(5)
    assert a is b


def test_disk_offsets_reject_negative_radius():
    with pytest.raises(ValueError):
        g.nest_disk_offsets(-1)


# ---------------------------------------------------------------------------
# Limite inclusivo
# ---------------------------------------------------------------------------


def test_disk_membership_is_inclusive_at_radius():
    center = (5, 5)
    r = 2
    assert g.is_position_inside_nest(7, 5, center, width=100, height=100, radius=r)
    assert g.is_position_inside_nest(5, 7, center, width=100, height=100, radius=r)
    # (8, 5): dx = 3 > r
    assert not g.is_position_inside_nest(8, 5, center, width=100, height=100, radius=r)


# ---------------------------------------------------------------------------
# Wrap toroidal escalar
# ---------------------------------------------------------------------------


def test_toroidal_membership_wraps_across_border():
    center = (0, 0)
    r = 1
    w = h = 10
    assert g.is_position_inside_nest(9, 0, center, width=w, height=h, radius=r)
    assert g.is_position_inside_nest(0, 9, center, width=w, height=h, radius=r)
    # (9, 9): dx=1, dy=1, d2=2 > 1
    assert not g.is_position_inside_nest(9, 9, center, width=w, height=h, radius=r)


# ---------------------------------------------------------------------------
# Pertencimento vetorizado
# ---------------------------------------------------------------------------


def test_positions_inside_nest_matches_scalar():
    center = (3, 3)
    r = 2
    w = h = 10
    coords = [(x, y) for x in range(w) for y in range(h)]
    xs = np.array([c[0] for c in coords], dtype=np.int64)
    ys = np.array([c[1] for c in coords], dtype=np.int64)

    vec = g.positions_inside_nest(xs, ys, center, width=w, height=h, radius=r)
    scalar = np.array(
        [
            g.is_position_inside_nest(x, y, center, width=w, height=h, radius=r)
            for (x, y) in coords
        ],
        dtype=bool,
    )
    assert np.array_equal(vec, scalar)


def test_positions_inside_nest_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        g.positions_inside_nest(
            np.array([1, 2, 3]),
            np.array([1, 2]),
            (0, 0),
            width=10,
            height=10,
            radius=1,
        )


# ---------------------------------------------------------------------------
# Wrap de offsets
# ---------------------------------------------------------------------------


def test_wrapped_points_wraps_negative_offsets():
    xs, ys = g.wrapped_points((0, 0), ((-1, 0), (0, -1)), width=10, height=10)
    assert xs.tolist() == [9, 0]
    assert ys.tolist() == [0, 9]


def test_wrapped_points_accepts_ndarray():
    off = np.array([[1, 0], [0, 1]], dtype=np.int64)
    xs, ys = g.wrapped_points((0, 0), off, width=10, height=10)
    assert xs.tolist() == [1, 0]
    assert ys.tolist() == [0, 1]


def test_wrapped_points_rejects_bad_ndarray_shape():
    with pytest.raises(ValueError):
        g.wrapped_points(
            (0, 0),
            np.zeros((4, 3), dtype=np.int64),
            width=10,
            height=10,
        )


# ---------------------------------------------------------------------------
# Overlap
# ---------------------------------------------------------------------------


def test_nests_overlap_common_cells():
    # radius=1: A=(0,0) e B=(2,0) compartilham (1,0).
    assert g.nests_overlap(
        (0, 0), (2, 0), width=100, height=100, radius=1
    ) is True


def test_nests_do_not_overlap_when_separated():
    # A=(0,0) e B=(3,0): nenhuma celula compartilhada com radius=1.
    assert g.nests_overlap(
        (0, 0), (3, 0), width=100, height=100, radius=1
    ) is False


def test_nests_overlap_across_wrap():
    # world 10x10, radius=1: A=(0,0) e B=(9,0) se tocam via wrap.
    assert g.nests_overlap(
        (0, 0), (9, 0), width=10, height=10, radius=1
    ) is True


# ---------------------------------------------------------------------------
# Intersecao ninho x zona
# ---------------------------------------------------------------------------


def test_nest_intersects_zone_common_case():
    zones = np.zeros((10, 10), dtype=bool)
    assert g.nest_intersects_zone((5, 5), zones, radius=1) is False

    zones[5, 6] = True  # dentro do disco radius=1 em (5,5)
    assert g.nest_intersects_zone((5, 5), zones, radius=1) is True


def test_nest_intersects_zone_across_wrap():
    zones = np.zeros((10, 10), dtype=bool)
    zones[9, 0] = True
    # center=(0,0), radius=1: (9,0) pertence via wrap.
    assert g.nest_intersects_zone((0, 0), zones, radius=1) is True


def test_nest_intersects_zone_rejects_non_bool():
    zones = np.zeros((10, 10), dtype=np.int8)
    with pytest.raises(ValueError):
        g.nest_intersects_zone((0, 0), zones, radius=1)


# ---------------------------------------------------------------------------
# Ring
# ---------------------------------------------------------------------------


def test_ring_is_subset_of_disk():
    for r in range(1, 6):
        disk = set(g.nest_disk_offsets(r))
        ring = set(g.nest_ring_offsets(r))
        assert ring.issubset(disk), f"ring nao e subconjunto do disk (r={r})"


def test_ring_excludes_center_for_radius_above_1():
    for r in range(2, 6):
        assert (0, 0) not in g.nest_ring_offsets(r)


def test_ring_radius_1_is_cardinal_neighbors():
    assert set(g.nest_ring_offsets(1)) == {
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
    }


def test_ring_radius_0_is_empty():
    assert g.nest_ring_offsets(0) == ()


# ---------------------------------------------------------------------------
# Constantes estaticas
# ---------------------------------------------------------------------------


def test_nest_constants_are_static():
    assert cfg.NESTS_PER_LINEAGE == 1
    assert cfg.NEST_RADIUS > 0
    assert 0 <= cfg.NEST_SPAWN_RADIUS <= cfg.NEST_RADIUS


def test_spawn_offsets_derive_from_disk():
    """A vizinhanca de spawn e literalmente nest_disk_offsets(NEST_SPAWN_RADIUS).
    Nao ha definicao paralela."""
    expected = {(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)}
    assert set(g.nest_disk_offsets(cfg.NEST_SPAWN_RADIUS)) == expected
