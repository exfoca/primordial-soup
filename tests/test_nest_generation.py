"""Contratos de world.generate_nests.

Cobre:

  - estrutura basica: tuple, TOTAL_LINEAGES centros, coords int.
  - distância ao zone: nenhum disco de ninho intersecta zona.
  - distância entre ninhos: discos nao se sobrepoem.
  - determinismo: mesma seed stdlib -> mesmo resultado.
  - isolamento: generate_nests NUNCA consome np.random.
  - rejeicao de input invalido (dtype, shape, ndim).
  - exhaustion do orcamento de tentativas -> RuntimeError.
  - nao muta o array de zones.

E tambem cobre a orquestracao de bootstrap: sob o schema v22,
generate_zones retorna (zones, zone_centers); bootstrap instala
AMBOS e DEPOIS chama generate_nests(zones), instalando o resultado
em state.nests.

Todos os docstrings deste arquivo sao intencionalmente ASCII puro.
"""

import random

import numpy as np
import pytest

from primordial_soup import bootstrap
from primordial_soup import config as cfg
from primordial_soup import layout
from primordial_soup import nest_geometry
from primordial_soup import state
from primordial_soup import world


def _empty_zones():
    return np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=bool,
    )


def _numpy_rng_equal(a, b) -> bool:
    """Comparacao estrutural de np.random.get_state().

    get_state() devolve (str, ndarray, int, int, float); comparar
    direto com == produz ndarray de bool, nao bool escalar.
    """
    return (
        a[0] == b[0]
        and np.array_equal(a[1], b[1])
        and a[2] == b[2]
        and a[3] == b[3]
        and a[4] == b[4]
    )


# ---------------------------------------------------------------------------
# Contrato estrutural
# ---------------------------------------------------------------------------


def test_generate_nests_returns_canonical_structure():
    random.seed(1234)
    nests = world.generate_nests(_empty_zones())

    assert type(nests) is tuple
    assert len(nests) == cfg.TOTAL_LINEAGES

    for center in nests:
        assert type(center) is tuple
        assert len(center) == 2
        x, y = center
        assert type(x) is int
        assert type(y) is int
        assert 0 <= x < layout.LAYOUT.world_width
        assert 0 <= y < layout.LAYOUT.world_height


def test_generate_nests_rejects_non_bool_zones():
    zones = np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=np.int8,
    )
    with pytest.raises(ValueError):
        world.generate_nests(zones)


def test_generate_nests_rejects_wrong_shape_zones():
    zones = np.zeros((10, 10), dtype=bool)
    with pytest.raises(ValueError):
        world.generate_nests(zones)


def test_generate_nests_rejects_wrong_ndim_zones():
    zones = np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height, 1),
        dtype=bool,
    )
    with pytest.raises(ValueError):
        world.generate_nests(zones)


# ---------------------------------------------------------------------------
# Restricoes geometricas
# ---------------------------------------------------------------------------


def test_generate_nests_avoids_zones():
    zones = _empty_zones()
    # Bloqueia uma faixa horizontal; ainda ha espaco suficiente para
    # colocar tres discos de NEST_RADIUS sem overlap.
    zones[10:80, :] = True

    random.seed(4321)
    nests = world.generate_nests(zones)

    for center in nests:
        assert not nest_geometry.nest_intersects_zone(
            center, zones, radius=cfg.NEST_RADIUS
        )


def test_generate_nests_disks_do_not_overlap():
    random.seed(7777)
    nests = world.generate_nests(_empty_zones())

    for i in range(len(nests)):
        for j in range(i + 1, len(nests)):
            assert not nest_geometry.nests_overlap(
                nests[i],
                nests[j],
                width=layout.LAYOUT.world_width,
                height=layout.LAYOUT.world_height,
                radius=cfg.NEST_RADIUS,
            )


# ---------------------------------------------------------------------------
# Determinismo
# ---------------------------------------------------------------------------


def test_generate_nests_is_deterministic_under_fixed_seed():
    zones = _empty_zones()

    random.seed(4321)
    a = world.generate_nests(zones)

    random.seed(4321)
    b = world.generate_nests(zones)

    assert a == b


def test_generate_nests_does_not_consume_numpy_rng():
    """generate_nests nao pode tocar o RNG global do NumPy.

    O bootstrap usa random da stdlib; NumPy e usado por genetics e
    evolution. Se generate_nests consumisse NumPy, um sweep com seed
    fixa divergiria silenciosamente.
    """
    zones = _empty_zones()

    np.random.seed(999)
    before = np.random.get_state()

    random.seed(123)
    world.generate_nests(zones)

    after = np.random.get_state()
    assert _numpy_rng_equal(before, after), (
        "generate_nests consumiu o RNG global do NumPy."
    )


# ---------------------------------------------------------------------------
# Nao muta input
# ---------------------------------------------------------------------------


def test_generate_nests_does_not_mutate_zones():
    zones = _empty_zones()
    zones[100:150, 100:150] = True
    before = zones.copy()

    random.seed(2024)
    world.generate_nests(zones)

    assert np.array_equal(zones, before)


# ---------------------------------------------------------------------------
# Budget de tentativas
# ---------------------------------------------------------------------------


def test_generate_nests_exhaustion_raises(monkeypatch):
    """Teto de tentativas esgotado: RuntimeError, nao geometria
    parcial.

    Zonas totalmente cheias: nenhum candidato pode ser aceito.
    Reduzimos o teto via monkeypatch para o teste ser barato; o
    comportamento verificado e o mesmo do valor real, apenas com
    menos tentativas.
    """
    monkeypatch.setattr(cfg, "MAX_NEST_PLACEMENT_ATTEMPTS", 3)
    zones = np.ones(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=bool,
    )

    random.seed(1)
    with pytest.raises(RuntimeError):
        world.generate_nests(zones)


# ---------------------------------------------------------------------------
# Orquestracao de bootstrap
# ---------------------------------------------------------------------------


def test_bootstrap_new_world_installs_sentinel_nests(monkeypatch):
    """bootstrap_new_world chama generate_zones e generate_nests(zones).

    Sob v22, generate_zones() retorna (zones, zone_centers); o
    bootstrap instala AMBOS, e passa exatamente a mask recebida para
    generate_nests(). Sentinels identificam ordem e encadeamento.
    """
    center = (
        layout.LAYOUT.world_width - cfg.ZONE_RADIUS - 1,
        layout.LAYOUT.world_height - cfg.ZONE_RADIUS - 1,
    )
    sentinel_zone_centers = tuple(
        center
        for _ in range(cfg.NUMBER_OF_ZONES)
    )
    sentinel_zones = world.build_zone_mask(sentinel_zone_centers)
    sentinel_nests = (
        (cfg.NEST_RADIUS + 1, cfg.NEST_RADIUS + 1),
        (cfg.NEST_RADIUS + 1 + 2 * cfg.NEST_RADIUS + 1, cfg.NEST_RADIUS + 1),
        (cfg.NEST_RADIUS + 1 + 4 * cfg.NEST_RADIUS + 2, cfg.NEST_RADIUS + 1),
    )
    calls: list[str] = []

    def fake_generate_zones():
        calls.append("zones")
        return (
            sentinel_zones,
            sentinel_zone_centers,
        )

    def fake_generate_nests(zones):
        assert zones is sentinel_zones, (
            "bootstrap passou zones errado para generate_nests."
        )
        calls.append("nests")
        return sentinel_nests

    original_rules = state.runtime_rules
    original_zones = state.zones
    original_zone_centers = state.zone_centers
    original_nests = state.nests
    try:
        monkeypatch.setattr(bootstrap, "seed_lineages", lambda: None)
        monkeypatch.setattr(bootstrap, "place_initially", lambda: None)
        monkeypatch.setattr(bootstrap, "fill_fields", lambda: None)
        monkeypatch.setattr(bootstrap, "agents", [])
        monkeypatch.setattr(
            bootstrap,
            "random_population",
            lambda n: np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32),
        )
        monkeypatch.setattr(bootstrap, "generate_zones", fake_generate_zones)
        monkeypatch.setattr(bootstrap, "generate_nests", fake_generate_nests)

        bootstrap.bootstrap_new_world()

        assert calls == ["zones", "nests"]
        assert state.zones is sentinel_zones
        assert state.zone_centers == sentinel_zone_centers
        assert state.nests == sentinel_nests
    finally:
        state.set_runtime_rules(original_rules)
        state.zones = original_zones
        state.zone_centers = original_zone_centers
        state.nests = original_nests
