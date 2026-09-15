"""Testes da infraestrutura de identidade estavel (Fase 1)."""

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import layout
from primordial_soup import state
from primordial_soup import world
from primordial_soup.world import (
    allocate_critter_ids,
    resolve_critter_id,
    seed_lineages,
    place_initially,
)
from primordial_soup.state import agents


def _valid_test_nests():
    """Geometria deterministica de ninhos valida para o contrato v21.

    Tres centros colineares, separados por 2*radius+1, de modo que os
    discos de radius NEST_RADIUS nao compartilhem celulas.
    """
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


def _install_checkpoint_geometry():
    """Instala zones e nests deterministicos em state.

    Fixtures que preparam mundo manualmente precisam de geometry
    valida sob o schema v21 antes de qualquer save. Esta funcao faz
    isso sem consumir RNG.
    """
    state.zones = np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=bool,
    )
    state.nests = _valid_test_nests()


@pytest.fixture
def fresh_world():
    """Populacao limpa com 3 linhagens, IDs alocados e geometry.

    O pool precisa ter o mesmo tamanho de agents/ids: deixar (0, G)
    aqui criaria um estado impossivel no runtime (agents=50, ids=50,
    pool=0) e quebraria os testes de compactacao e de save/load.
    """
    state.reset_counters()
    seed_lineages()
    for agent in agents:
        agent["pool"] = np.zeros(
            (cfg.INITIAL_POPULATION_PER_LINEAGE, cfg.GENOME_SIZE),
            dtype=np.float32,
        )
    place_initially()
    _install_checkpoint_geometry()
    yield
    state.reset_counters()
    state.zones = None
    state.nests = None
    agents.clear()


def test_allocate_returns_int64(fresh_world):
    ids = allocate_critter_ids(5)
    assert ids.dtype == np.int64
    assert ids.size == 5


def test_allocate_zero_does_not_advance(fresh_world):
    before = state.next_critter_id
    ids = allocate_critter_ids(0)
    assert ids.size == 0
    assert state.next_critter_id == before


def test_allocate_negative_raises(fresh_world):
    with pytest.raises(ValueError):
        allocate_critter_ids(-1)


def test_first_id_is_one(fresh_world):
    state.next_critter_id = 1
    ids = allocate_critter_ids(3)
    assert ids[0] == 1


def test_successive_allocations_do_not_collide(fresh_world):
    a = allocate_critter_ids(10)
    b = allocate_critter_ids(10)
    assert np.intersect1d(a, b).size == 0


def test_founders_have_unique_ids(fresh_world):
    all_ids = np.concatenate([ag["ids"] for ag in agents])
    assert np.unique(all_ids).size == all_ids.size


def test_founders_get_consecutive_ranges(fresh_world):
    n = cfg.INITIAL_POPULATION_PER_LINEAGE
    r_ids = agents[0]["ids"]
    g_ids = agents[1]["ids"]
    b_ids = agents[2]["ids"]
    assert r_ids[0] == 1
    assert r_ids[-1] == n
    assert g_ids[0] == n + 1
    assert g_ids[-1] == 2 * n
    assert b_ids[0] == 2 * n + 1
    assert b_ids[-1] == 3 * n


def test_compaction_preserves_alignment(fresh_world):
    # Marca um individuo no meio e mata os anteriores a ele.
    agent = agents[0]
    target_row = agent["agents"][5].copy()
    target_genome = agent["pool"][5].copy()
    target_id = int(agent["ids"][5])

    alive = np.ones(agent["agents"].shape[0], dtype=bool)
    alive[:5] = False  # mata os indices 0..4

    agent["ids"] = agent["ids"][alive]
    agent["pool"] = agent["pool"][alive]
    agent["agents"] = agent["agents"][alive]

    found = resolve_critter_id(target_id)
    assert found is not None
    li, ai = found
    assert li == 0
    assert np.array_equal(agent["agents"][ai], target_row)
    assert np.array_equal(agent["pool"][ai], target_genome)


def test_newborn_gets_new_id(fresh_world):
    before_max = max(int(ag["ids"].max()) for ag in agents)
    new_ids = allocate_critter_ids(2)
    assert int(new_ids[0]) > before_max


def test_resolve_returns_none_for_unknown(fresh_world):
    assert resolve_critter_id(999_999) is None


def test_reset_restarts_next_id(fresh_world):
    allocate_critter_ids(50)
    assert state.next_critter_id > 1
    state.reset_counters()
    assert state.next_critter_id == 1


def test_save_load_preserves_ids(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    saved_ids = [ag["ids"].copy() for ag in agents]
    saved_next = state.next_critter_id
    assert persistence.save(str(path)) is True

    # Esvazia o estado e recarrega.
    state.reset_counters()
    state.zones = None
    state.nests = None
    agents.clear()
    seed_lineages()
    for ag in agents:
        ag["pool"] = np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32)

    assert persistence.load(str(path))
    for ag, expected in zip(agents, saved_ids):
        assert np.array_equal(ag["ids"], expected)
    assert state.next_critter_id == saved_next


def test_recreate_save_load_preserves_ids(
    fresh_world,
    tmp_path,
    monkeypatch,
):
    """Regressao: recreate -> save -> load deve preservar identidade.

    O bug original: recreate() criava a populacao nova (alocando IDs
    via place_initially -> allocate_critter_ids) ANTES de chamar
    reset_counters(), que zera next_critter_id para 1. O save entao
    gravava proximo_id=1 com max(ids)=150, e o load rejeitava
    corretamente em _validate_identity. Este teste exercita o
    lifecycle inteiro da tecla R e falha se a ordem regredir.

    recreate() nao desenha mais: o redraw e responsabilidade do loop
    grafico via DispatchResult. Por isso nao ha monkeypatch de draw.
    """
    from primordial_soup import controls, persistence

    controls.recreate()

    # Invariante forte: em um mundo recem-recriado os IDs sao alocados
    # sequencialmente e sem lacunas, entao max(ids) + 1 e o contrato
    # exato de next_critter_id. Um refactor futuro que pule IDs
    # durante a inicializacao deve denunciar aqui.
    all_ids = np.concatenate([ag["ids"] for ag in agents])
    assert state.next_critter_id == int(all_ids.max()) + 1

    saved_ids = [ag["ids"].copy() for ag in agents]
    saved_next = state.next_critter_id

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    # Isola o runtime antes do load, seguindo o padrao da suite.
    state.reset_counters()
    state.zones = None
    state.nests = None
    agents.clear()
    seed_lineages()
    for ag in agents:
        ag["pool"] = np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32)

    assert persistence.load(str(path)) is True

    for ag, expected in zip(agents, saved_ids):
        assert np.array_equal(ag["ids"], expected)

    assert state.next_critter_id == saved_next


# Os testes de loader corrompido e atomicidade forte vivem em
# tests/test_load_atomicity.py. Este arquivo cobre apenas a
# infraestrutura de identidade estavel.