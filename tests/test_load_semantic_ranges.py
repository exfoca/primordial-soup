"""Validacao semantica de ranges no loader.

Cobre a camada de DOMINIO adicionada no Patch 3: apos a coercao
lossless de _coerce_int, cada campo inteiro escalar do payload e
validado contra seu range operacional. Valores fora do range sao
rejeitados; NAO sao silenciosamente clamped.

Escopo deliberadamente separado de tests/test_load_atomicity.py:
aquele arquivo cobre a propriedade estrutural de load() rejeitar sem
mutar o runtime (transactional). Este cobre QUAIS valores o loader
aceita como validos em cada campo. As duas perguntas sao diferentes e
merecem arquivos diferentes.

Contrato lexical preservado (NAO endurecer aqui):
  _coerce_int aceita int, np.integer, float integral finito, str de
  int. Rejeita bool, None, NaN, inf, float nao integral, str de
  float, str nao numerica.

Por isso "5" e 5.0 sao VALIDOS (coercao lossless) e NAO aparecem na
lista de invalidos deste arquivo. O objetivo aqui e validar dominio,
nao mudar compatibilidade lexical.

Todos os docstrings e comentarios deste arquivo sao intencionalmente
ASCII puro, seguindo o estilo de nomenclatura interna do projeto.
"""

import pickle

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import persistence
from primordial_soup import state
from primordial_soup import world
from primordial_soup.state import agents


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def saved_payload(tmp_path):
    """Gera um save valido e devolve (path, dict_carregado).

    O dict e o payload cru, para o teste mutar um campo especifico
    antes de reescrever. O path e onde o teste reescreve o payload
    mutado.
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

    path = tmp_path / "save.pkl"
    persistence.save(str(path))
    with open(path, "rb") as f:
        data = pickle.load(f)
    return path, data


def _isolate_runtime():
    """Zera o runtime sem depender do payload."""
    state.reset_counters()
    agents.clear()
    world.seed_lineages()
    for ag in agents:
        ag["pool"] = np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32)


def _write_payload(path, data):
    with open(path, "wb") as f:
        pickle.dump(data, f)


# ---------------------------------------------------------------------------
# Campos opcionais com range fechado
# ---------------------------------------------------------------------------
#
# Casos por campo:
#   - limite inferior valido
#   - limite superior valido
#   - logo abaixo do inferior
#   - logo acima do superior
#   - tipo corrompido (3.7, None, True, "abc")
#
# "5" (str de int) e 5.0 (float integral) sao validos por contrato
# de _coerce_int; nao entram na lista de invalidos. Ver
# test_coerce_int_lexical_contract_is_preserved abaixo.


_OPTIONAL_RANGED_CASES = [
    # (nome, campo, chave, minimo, maximo)
    ("mutation", "mutation", "mutation",
     cfg.MIN_MUTATION_RATE, cfg.MAX_MUTATION_RATE),
    ("mutategen", "mutategen", "mutategen",
     cfg.MIN_MUTATED_GENES, cfg.MAX_MUTATED_GENES),
    ("escala_local", "escala_local", "local_scale",
     cfg.MIN_LOCAL_SCALE_FRACTION, cfg.MAX_LOCAL_SCALE_FRACTION),
    ("efeito_hp_zonas", "efeito_hp_zonas", "zone_hp_effect",
     cfg.MIN_ZONE_HP_EFFECT, cfg.MAX_ZONE_HP_EFFECT),
]


@pytest.mark.parametrize(
    "field, key, minimum, maximum",
    [(c[1], c[2], c[3], c[4]) for c in _OPTIONAL_RANGED_CASES],
    ids=[c[0] for c in _OPTIONAL_RANGED_CASES],
)
def test_optional_ranged_accepts_bounds(saved_payload, field, key, minimum, maximum):
    path, data = saved_payload
    for value in (minimum, maximum):
        data[field] = value
        _write_payload(path, data)
        _isolate_runtime()
        assert persistence.load(str(path)) is True


@pytest.mark.parametrize(
    "field, key, minimum, maximum",
    [(c[1], c[2], c[3], c[4]) for c in _OPTIONAL_RANGED_CASES],
    ids=[c[0] for c in _OPTIONAL_RANGED_CASES],
)
def test_optional_ranged_rejects_below(saved_payload, field, key, minimum, maximum):
    path, data = saved_payload
    data[field] = minimum - 1
    _write_payload(path, data)
    _isolate_runtime()
    assert persistence.load(str(path)) is False


@pytest.mark.parametrize(
    "field, key, minimum, maximum",
    [(c[1], c[2], c[3], c[4]) for c in _OPTIONAL_RANGED_CASES],
    ids=[c[0] for c in _OPTIONAL_RANGED_CASES],
)
def test_optional_ranged_rejects_above(saved_payload, field, key, minimum, maximum):
    path, data = saved_payload
    data[field] = maximum + 1
    _write_payload(path, data)
    _isolate_runtime()
    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Campos obrigatorios com range fechado
# ---------------------------------------------------------------------------


_OBLIGATORY_RANGED_CASES = [
    ("reproduction_cooldown", "reproduction_cooldown",
     0, cfg.REPRODUCTION_INTERVAL),
    ("reproduction_turn", "reproduction_turn",
     0, cfg.TOTAL_LINEAGES - 1),
]


@pytest.mark.parametrize(
    "field, minimum, maximum",
    [(c[1], c[2], c[3]) for c in _OBLIGATORY_RANGED_CASES],
    ids=[c[0] for c in _OBLIGATORY_RANGED_CASES],
)
def test_obligatory_ranged_accepts_bounds(saved_payload, field, minimum, maximum):
    path, data = saved_payload
    for value in (minimum, maximum):
        data[field] = value
        _write_payload(path, data)
        _isolate_runtime()
        assert persistence.load(str(path)) is True


@pytest.mark.parametrize(
    "field, minimum, maximum",
    [(c[1], c[2], c[3]) for c in _OBLIGATORY_RANGED_CASES],
    ids=[c[0] for c in _OBLIGATORY_RANGED_CASES],
)
def test_obligatory_ranged_rejects_outside(saved_payload, field, minimum, maximum):
    path, data = saved_payload
    for value in (minimum - 1, maximum + 1):
        data[field] = value
        _write_payload(path, data)
        _isolate_runtime()
        assert persistence.load(str(path)) is False


@pytest.mark.parametrize(
    "field",
    [c[1] for c in _OBLIGATORY_RANGED_CASES],
    ids=[c[0] for c in _OBLIGATORY_RANGED_CASES],
)
def test_obligatory_ranged_rejects_missing(saved_payload, field):
    """Chave ausente em campo obrigatorio e rejeitada.

    O helper usa default=_MISSING nesses campos, entao ausente cai em
    _INVALID. E o contrato de v11: scheduler precisa estar no save
    para a continuacao ser exata.
    """
    path, data = saved_payload
    del data[field]
    _write_payload(path, data)
    _isolate_runtime()
    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# tick / births / deaths: range inferior 0, sem maximo
# ---------------------------------------------------------------------------


_UNBOUNDED_CASES = [
    ("tick", "tick"),
    ("nascimentos", "nascimentos"),
    ("mortes", "mortes"),
]


@pytest.mark.parametrize(
    "field, key",
    [(c[1], c[1]) for c in _UNBOUNDED_CASES],
    ids=[c[0] for c in _UNBOUNDED_CASES],
)
def test_unbounded_accepts_zero_and_positive(saved_payload, field, key):
    path, data = saved_payload
    for value in (0, 1, 10_000):
        data[field] = value
        _write_payload(path, data)
        _isolate_runtime()
        assert persistence.load(str(path)) is True


@pytest.mark.parametrize(
    "field, key",
    [(c[1], c[1]) for c in _UNBOUNDED_CASES],
    ids=[c[0] for c in _UNBOUNDED_CASES],
)
def test_unbounded_rejects_negative(saved_payload, field, key):
    path, data = saved_payload
    data[field] = -1
    _write_payload(path, data)
    _isolate_runtime()
    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Tipos corrompidos: mesmos para todos os campos inteiros
# ---------------------------------------------------------------------------
#
# Lista deliberadamente SEM "5" e SEM 5.0. Esses dois continuam
# validos por contrato de _coerce_int (test_coerce_int_lexical_*
# abaixo protege essa propriedade).


_BAD_TYPES = [
    ("float_nao_integral", 3.7),
    ("none", None),
    ("bool_true", True),
    ("str_nao_numerica", "abc"),
]


_ALL_INT_FIELDS = [
    "mutation", "mutategen", "escala_local",
    "tick", "nascimentos", "mortes",
    "efeito_hp_zonas", "reproduction_cooldown", "reproduction_turn",
]


@pytest.mark.parametrize("field", _ALL_INT_FIELDS)
@pytest.mark.parametrize(
    "label, bad_value",
    _BAD_TYPES,
    ids=[c[0] for c in _BAD_TYPES],
)
def test_int_fields_reject_bad_types(saved_payload, field, label, bad_value):
    path, data = saved_payload
    data[field] = bad_value
    _write_payload(path, data)
    _isolate_runtime()
    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Contrato lexical de _coerce_int preservado
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lexical_value",
    [
        pytest.param("5", id="str_de_int"),
        pytest.param(5.0, id="float_integral"),
        pytest.param(np.int64(5), id="np_int64"),
        pytest.param(np.int32(5), id="np_int32"),
    ],
)
def test_coerce_int_lexical_contract_is_preserved(saved_payload, lexical_value):
    """Formas coerciveis para int continuam validas.

    Protege a compatibilidade lexical existente do loader: o Patch 3
    adiciona dominio por cima, nao muda o que _coerce_int aceita.
    Sem esta protecao, alguem poderia "endurecer" o campo e quebrar
    saves legitimamente produzidos por versoes anteriores, ou
    payloads serializados por ferramentas que gravaram "5" em vez
    de 5.
    """
    path, data = saved_payload
    # Usa um campo de range conhecido: mutation. O valor 5 esta
    # dentro de [MIN_MUTATION_RATE, MAX_MUTATION_RATE].
    assert cfg.MIN_MUTATION_RATE <= 5 <= cfg.MAX_MUTATION_RATE
    data["mutation"] = lexical_value
    _write_payload(path, data)
    _isolate_runtime()
    assert persistence.load(str(path)) is True


# ---------------------------------------------------------------------------
# zonas_ativas: bool estrito
# ---------------------------------------------------------------------------


def test_zones_active_accepts_bool_true(saved_payload):
    path, data = saved_payload
    data["zonas_ativas"] = True
    _write_payload(path, data)
    _isolate_runtime()
    assert persistence.load(str(path)) is True


def test_zones_active_accepts_bool_false(saved_payload):
    path, data = saved_payload
    data["zonas_ativas"] = False
    _write_payload(path, data)
    _isolate_runtime()
    assert persistence.load(str(path)) is True


def test_zones_active_rejects_missing(saved_payload):
    """zonas_ativas e obrigatoria no contrato v11."""
    path, data = saved_payload
    del data["zonas_ativas"]
    _write_payload(path, data)
    _isolate_runtime()

    assert persistence.load(str(path)) is False


@pytest.mark.parametrize(
    "bad_value",
    [
        pytest.param("true", id="str_true"),
        pytest.param("false", id="str_false"),
        pytest.param(0, id="int_zero"),
        pytest.param(1, id="int_one"),
        pytest.param(None, id="none"),
        pytest.param(np.bool_(True), id="np_bool_"),
    ],
)
def test_zones_active_rejects_non_bool(saved_payload, bad_value):
    """Strings, ints e np.bool_ sao rejeitados.

    O payload canonical grava state.zones_active, sempre bool Python.
    Qualquer outra coisa e payload corrompido ou editado a mao.
    """
    path, data = saved_payload
    data["zonas_ativas"] = bad_value
    _write_payload(path, data)
    _isolate_runtime()
    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Runtime intacto apos rejeicao semantica
# ---------------------------------------------------------------------------
#
# Verificacao leve aqui (sentinela representativo), para nao duplicar
# o teste pesado de atomicidade de tests/test_load_atomicity.py. A
# propriedade "load rejeitado nao muta o runtime" ja esta provada
# la; este teste so confirma que as rejeicoes de range do Patch 3
# passam pelo mesmo caminho.


def test_rejected_range_does_not_mutate_runtime(saved_payload):
    path, data = saved_payload

    # Estado conhecido antes do load invalido.
    state.tick_count = 12345
    state.next_critter_id = 99999
    state.reproduction_cooldown = 7
    state.reproduction_turn = 1

    # mutation fora do range: rejeicao garantida.
    data["mutation"] = cfg.MAX_MUTATION_RATE + 1
    _write_payload(path, data)

    assert persistence.load(str(path)) is False

    assert state.tick_count == 12345
    assert state.next_critter_id == 99999
    assert state.reproduction_cooldown == 7
    assert state.reproduction_turn == 1


def test_rejected_bool_does_not_mutate_runtime(saved_payload):
    path, data = saved_payload

    state.tick_count = 12345
    state.next_critter_id = 99999

    # zonas_ativas como string: rejeicao estrita.
    data["zonas_ativas"] = "false"
    _write_payload(path, data)

    assert persistence.load(str(path)) is False

    assert state.tick_count == 12345
    assert state.next_critter_id == 99999
