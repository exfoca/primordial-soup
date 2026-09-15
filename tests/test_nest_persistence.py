"""Contratos de persistencia dos ninhos (schema v21).

Cobre:

  - payload exato: dict {"R": [x, y], "G": [x, y], "B": [x, y]}.
  - roundtrip: load restaura nests identico ao salvo.
  - save aborta sem nests (checkpoint nao destrutivo).
  - load rejeita payload sem nests.
  - load rejeita dict com chaves faltando ou extras.
  - load rejeita coordenadas invalidas (bool, float, np.int64, str,
    None, fora dos limites).
  - load rejeita overlap entre ninhos.
  - load rejeita interseccao ninho x zona.
  - atomicidade: load rejeitado nao muta state, agents, RNGs.

Nao usa bootstrap real; instala geometry deterministica em state.
Todos os docstrings deste arquivo sao intencionalmente ASCII puro.
"""

import pickle
import random

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import layout
from primordial_soup import persistence
from primordial_soup import state
from primordial_soup import world
from primordial_soup.state import agents


def _valid_nests():
    """Geometria canonica determinista: tres discos sem overlap."""
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


def _empty_zones():
    return np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=bool,
    )


def _prepare_checkpointable_world():
    """Runtime minimo e deterministico para save/load.

    Nao usa bootstrap real. Nao consome stdlib RNG para zones nem
    nests. Serve apenas para produzir payloads v21 validos.
    """
    state.reset_counters()
    world.seed_lineages()
    for ag in agents:
        ag["pool"] = np.zeros(
            (cfg.INITIAL_POPULATION_PER_LINEAGE, cfg.GENOME_SIZE),
            dtype=np.float32,
        )
    world.place_initially()
    world.fill_fields()
    state.zones = _empty_zones()
    state.nests = _valid_nests()


def _numpy_rng_equal(a, b) -> bool:
    return (
        a[0] == b[0]
        and np.array_equal(a[1], b[1])
        and a[2] == b[2]
        and a[3] == b[3]
        and a[4] == b[4]
    )


@pytest.fixture
def clean_state():
    """Restaura runtime e geometry ao redor de cada teste."""
    original_rules = state.runtime_rules
    saved_zones = state.zones
    saved_nests = state.nests
    saved_agents = list(agents)
    yield
    state.set_runtime_rules(original_rules)
    state.reset_counters()
    state.zones = saved_zones
    state.nests = saved_nests
    agents[:] = saved_agents


# ---------------------------------------------------------------------------
# Payload exato
# ---------------------------------------------------------------------------


def test_save_emits_canonical_nests_dict(clean_state, tmp_path):
    _prepare_checkpointable_world()
    r, g, b = state.nests

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)

    assert isinstance(data["nests"], dict)
    assert set(data["nests"].keys()) == {"R", "G", "B"}
    assert data["nests"]["R"] == [r[0], r[1]]
    assert data["nests"]["G"] == [g[0], g[1]]
    assert data["nests"]["B"] == [b[0], b[1]]
    for key in ("R", "G", "B"):
        for coord in data["nests"][key]:
            assert type(coord) is int


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------


def test_load_restores_nests_exactly(clean_state, tmp_path):
    _prepare_checkpointable_world()
    expected = state.nests

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    # Suja nests antes do load: prova que o payload restaura.
    state.nests = None

    assert persistence.load(str(path)) is True
    assert state.nests == expected


# ---------------------------------------------------------------------------
# Save aborta sem nests
# ---------------------------------------------------------------------------


def test_save_without_nests_is_non_destructive(clean_state, tmp_path):
    """save com nests=None: False, arquivo anterior preservado.

    Um checkpoint abortado nao pode destruir o arquivo previo: o
    operador confiou naquele save e o loader o rejeitaria, mas o
    arquivo em disco continua intacto.
    """
    path = tmp_path / "save.pkl"
    path.write_bytes(b"sentinel")

    _prepare_checkpointable_world()
    state.nests = None

    assert persistence.save(str(path)) is False
    assert path.read_bytes() == b"sentinel"


# ---------------------------------------------------------------------------
# Load rejeita payload sem nests
# ---------------------------------------------------------------------------


def test_load_rejects_missing_nests(clean_state, tmp_path):
    _prepare_checkpointable_world()
    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    del data["nests"]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    state.nests = None
    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Chaves invalidas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutator",
    [
        pytest.param(lambda d: d["nests"].pop("R"), id="missing_R"),
        pytest.param(lambda d: d["nests"].pop("G"), id="missing_G"),
        pytest.param(lambda d: d["nests"].pop("B"), id="missing_B"),
        pytest.param(
            lambda d: d["nests"].update({"X": [1, 1]}), id="extra_X"
        ),
    ],
)
def test_load_rejects_wrong_nest_keys(clean_state, tmp_path, mutator):
    _prepare_checkpointable_world()
    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    mutator(data)
    with open(path, "wb") as f:
        pickle.dump(data, f)

    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Coordenadas invalidas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param(True, id="bool"),
        pytest.param(5.0, id="float"),
        pytest.param(np.int64(5), id="np_int64"),
        pytest.param("5", id="str"),
        pytest.param(None, id="none"),
        pytest.param(-1, id="negative"),
    ],
)
def test_load_rejects_invalid_nest_coord(clean_state, tmp_path, bad):
    _prepare_checkpointable_world()
    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    rx, ry = data["nests"]["R"]
    data["nests"]["R"] = [bad, ry]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    assert persistence.load(str(path)) is False


def test_load_rejects_out_of_bounds_nest_coord(clean_state, tmp_path):
    _prepare_checkpointable_world()
    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    _rx, ry = data["nests"]["R"]
    data["nests"]["R"] = [layout.LAYOUT.world_width, ry]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Overlap
# ---------------------------------------------------------------------------


def test_load_rejects_overlapping_nests(clean_state, tmp_path):
    _prepare_checkpointable_world()
    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # G no mesmo centro que R: overlap inequivoco.
    data["nests"]["G"] = list(data["nests"]["R"])
    with open(path, "wb") as f:
        pickle.dump(data, f)

    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Zone intersection
# ---------------------------------------------------------------------------


def test_load_rejects_nest_inside_zone(clean_state, tmp_path):
    _prepare_checkpointable_world()
    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # Ativa uma celula no proprio centro de R: o centro pertence ao
    # disco do ninho (distancia 0 <= radius), entao há interseccao.
    rx, ry = data["nests"]["R"]
    data["zonas"][rx, ry] = True
    with open(path, "wb") as f:
        pickle.dump(data, f)

    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Atomicidade forte
# ---------------------------------------------------------------------------


def test_invalid_nests_load_is_fully_atomic(clean_state, tmp_path):
    """Load rejeitado por nests: nenhum efeito colateral observavel.

    Coleta snapshot completo de:
      - identidade de RuntimeRules, zones, nests, agents (lista e dicts);
      - conteudo de counters, scheduler, agents, ids;
      - estados dos RNGs globais (stdlib e NumPy).

    Depois de um load rejeitado por nests invalidos, TUDO precisa
    estar byte-a-byte identico. Isso prova que a validacao de nests
    roda ANTES do COMMIT, e que o parser nao consome RNG incidental.
    """
    _prepare_checkpointable_world()

    # Cria um save valido e depois corrompe apenas nests.
    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True
    with open(path, "rb") as f:
        data = pickle.load(f)
    data["nests"]["G"] = list(data["nests"]["R"])  # overlap
    with open(path, "wb") as f:
        pickle.dump(data, f)

    # Runtime deliberadamente diferente do save (contadores, seeds).
    state.tick_count = 12345
    state.births = 42
    state.deaths = 7
    state.next_critter_id = 99999
    state.reproduction_cooldown = 3
    state.reproduction_turn = 1
    random.seed(555)
    np.random.seed(555)

    rules_before = state.runtime_rules
    zones_before = state.zones
    nests_before = state.nests
    zones_id = id(state.zones)
    nests_id = id(state.nests)
    agents_list_id = id(agents)
    lineage_refs = list(agents)
    pool_refs = [ag["pool"] for ag in agents]
    agent_refs = [ag["agents"] for ag in agents]
    ids_refs = [ag["ids"] for ag in agents]
    pool_contents = [ag["pool"].copy() for ag in agents]
    agents_contents = [ag["agents"].copy() for ag in agents]
    ids_contents = [ag["ids"].copy() for ag in agents]
    py_rng = random.getstate()
    np_rng = np.random.get_state()

    assert persistence.load(str(path)) is False

    # Identidade: nada reconstruido in-place.
    assert state.runtime_rules is rules_before
    assert state.zones is zones_before
    assert state.nests is nests_before
    assert id(state.zones) == zones_id
    assert id(state.nests) == nests_id
    assert id(agents) == agents_list_id
    for i, ag in enumerate(agents):
        assert ag is lineage_refs[i]
        assert ag["pool"] is pool_refs[i]
        assert ag["agents"] is agent_refs[i]
        assert ag["ids"] is ids_refs[i]

    # Conteudo: nada substituido.
    assert state.tick_count == 12345
    assert state.births == 42
    assert state.deaths == 7
    assert state.next_critter_id == 99999
    assert state.reproduction_cooldown == 3
    assert state.reproduction_turn == 1
    for i in range(len(agents)):
        assert np.array_equal(agents[i]["pool"], pool_contents[i])
        assert np.array_equal(agents[i]["agents"], agents_contents[i])
        assert np.array_equal(agents[i]["ids"], ids_contents[i])
    assert random.getstate() == py_rng
    assert _numpy_rng_equal(np.random.get_state(), np_rng)


# ---------------------------------------------------------------------------
# Load nunca gera nests
# ---------------------------------------------------------------------------


def test_load_never_calls_generate_nests(clean_state, tmp_path, monkeypatch):
    """load restaura nests do payload, nao regenera.

    Se load caísse em generate_nests por qualquer motivo, perderia a
    geometria salva e consumiria RNG global. Monkeypatch em
    world.generate_nests transforma esse caminho em erro explicito.
    """
    _prepare_checkpointable_world()
    expected = state.nests

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    state.nests = None

    def forbidden_generate_nests(zones):
        raise AssertionError(
            "persistence.load nao pode chamar world.generate_nests"
        )

    monkeypatch.setattr(world, "generate_nests", forbidden_generate_nests)

    assert persistence.load(str(path)) is True
    assert state.nests == expected
