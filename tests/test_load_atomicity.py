"""Testes de robustez do loader: rejeicao de payload corrompido e

atomicidade forte de persistence.load().
"""

import pickle
import random as _random

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import layout
from primordial_soup import state
from primordial_soup import world
from primordial_soup.world import (
    allocate_critter_ids,
    seed_lineages,
    place_initially,
)
from primordial_soup.state import agents


def _valid_test_nests():
    """Geometria deterministica de ninhos valida para o contrato v21."""
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


def _install_checkpoint_geometry():
    """Instala zones vazias e nests determinísticos.

    Nao consome RNG: fixtures de persistence nao devem alterar a
    sequencia aleatoria global so por preparar um checkpoint.
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

    Geometry e instalada explicitamente: o checkpoint v21 exige zones
    e nests validos. Fixtures que salvam mundo manual precisam de um
    runtime checkpointavel deterministico.
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


def _isolate_state():
    """Esvazia o runtime para que um load() rejeitado nao encontre
    estado residual. Usado depois de salvar um save valido, para que o
    proprio load de teste parta de um runtime limpo."""
    state.reset_counters()
    state.zones = None
    state.nests = None
    agents.clear()
    seed_lineages()
    for ag in agents:
        ag["pool"] = np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32)


# ---------------------------------------------------------------------------
# Structural validation of the v10 contract: lineage count, per-array
# rank, and cross-array lockstep. Each test corrupts exactly one aspect of
# a valid save and asserts that load() rejects it with False.
# ---------------------------------------------------------------------------


def test_load_rejects_missing_ids(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    for lin in data["linhagens"]:
        del lin["ids"]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_missing_proximo_id(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    del data["proximo_id"]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_duplicate_ids(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # Forca duplicata: copia o primeiro id de R para o primeiro de G.
    data["linhagens"][1]["ids"][0] = data["linhagens"][0]["ids"][0]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_proximo_id_too_small(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["proximo_id"] = 1  # menor que max(ids), que sera ~600
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_id_length_mismatch(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # Remove um id de R, deixando len(ids) < len(agents).
    data["linhagens"][0]["ids"] = data["linhagens"][0]["ids"][:-1]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_wrong_lineage_count(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # Remove a linhagem B, deixando 2 de 3.
    data["linhagens"] = data["linhagens"][:2]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_pool_width_mismatch(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # Encolhe o pool de R em 1 gene. pool.ndim continua 2, mas a largura
    # diverge de GENOME_SIZE.
    data["linhagens"][0]["pools"] = [
        row[:-1] for row in data["linhagens"][0]["pools"]
    ]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_agents_width_mismatch(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # Encolhe a matriz de agentes de R em 1 coluna. agents.shape[1]
    # diverge de AGENT_COLUMNS.
    data["linhagens"][0]["agentes"] = [
        row[:-1] for row in data["linhagens"][0]["agentes"]
    ]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_ids_rank_mismatch(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # ids vira 2-D (N, 1). A conversao para int64 nao falha, mas o
    # check de ndim=1 rejeita.
    data["linhagens"][0]["ids"] = [
        [v] for v in data["linhagens"][0]["ids"]
    ]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_non_numeric_ids(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # ids com strings nao-numericas: a validacao lossless rejeita
    # antes de qualquer conversao.
    data["linhagens"][0]["ids"] = ["x"] * len(data["linhagens"][0]["ids"])
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_non_numeric_proximo_id(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["proximo_id"] = "x"
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Hardening adicional (pos-revisao): payloads que o helper antigo aceitava
# silenciosamente e que agora devem ser rejeitados.
# ---------------------------------------------------------------------------


def test_load_rejects_non_integral_float_ids(fresh_world, tmp_path):
    """IDs float nao-integrais nao podem ser truncados silenciosamente.

    np.asarray(..., dtype=np.int64) converteria 1.9 -> 1, alterando
    a identidade persistida. O loader deve rejeitar.
    """
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # 1.9 na primeira posicao de R.
    data["linhagens"][0]["ids"][0] = 1.9
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_bool_ids(fresh_world, tmp_path):
    """True/False satisfazem numbers.Integral mas nao sao IDs validos."""
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["linhagens"][0]["ids"][0] = True
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_zero_ids(fresh_world, tmp_path):
    """IDs comecam em 1; 0 e invalido."""
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["linhagens"][0]["ids"][0] = 0
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_invalid_version_string(fresh_world, tmp_path):
    """versao="x" deve logar e devolver False, sem ValueError."""
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["versao"] = "x"
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    # Sem a protecao, int("x") levantaria ValueError aqui.
    assert persistence.load(str(path)) is False


def test_load_rejects_explicit_none_mutation(fresh_world, tmp_path):
    """mutation=None explicito e presenca invalida, nao ausencia."""
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["mutation"] = None
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_non_integral_tick(fresh_world, tmp_path):
    """tick=3.7 nao pode virar 3 silenciosamente."""
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["tick"] = 3.7
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_out_of_bounds_xy(fresh_world, tmp_path):
    """x/y fora do mundo devem ser rejeitados no parse, nao no commit.

    Sem a pre-construcao do field, este payload passava pelo parse e
    so quebrava em fill_fields() apos o commit, deixando o runtime
    em estado inconsistente.
    """
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    # x fora do mundo na primeira criatura de R.
    import primordial_soup.layout as layout

    data["linhagens"][0]["agentes"][0][1] = layout.LAYOUT.world_width + 100
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


def test_load_rejects_non_integral_xy(fresh_world, tmp_path):
    """x=3.7 nao pode virar 3 silenciosamente."""
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["linhagens"][0]["agentes"][0][1] = 3.7
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()
    assert persistence.load(str(path)) is False


# ---------------------------------------------------------------------------
# Atomicity contract: a rejected load leaves every piece of runtime state
# exactly as it was. This is the test that turns the "transactional"
# comment in persistence.load() into a checkable contract.
#
# Duas familias de assercoes, ambas necessarias:
#   - conteudo: campos escalares e arrays comparados por valor
#   - identidade: comparacao por `is` para provar que nada foi
#     reconstruido in-place. Uma implementacao que "reconstroi com o
#     mesmo conteudo" passaria nas assercoes de conteudo mas falharia
#     nas de identidade — e o teste deve distinguir as duas.
#
# O contrato de identidade em caso de rejeicao e:
#   agents[i]                mesma lista externa
#   agents[i]                mesmo dict
#   agents[i]["pool"]        mesmo ndarray
#   agents[i]["agents"]      mesmo ndarray
#   agents[i]["ids"]         mesmo ndarray
#   agents[i]["field"]       mesmo ndarray
#
# (Em load BEM-SUCEDIDO apenas a lista externa e preservada; os dicts
# e arrays sao substituidos. Este teste cobre somente o caminho de
# rejeicao.)
# ---------------------------------------------------------------------------


def test_failed_load_does_not_mutate_runtime_state(fresh_world, tmp_path):
    """Um load estruturalmente invalido nao pode tocar `state`.

    Prepara um runtime com valores conhecidos, tenta carregar um save
    invalido (duas linhagens em vez de tres, com escalares
    propositalmente diferentes) e verifica que absolutamente nada em
    `state` mudou — nem os escalares, nem as zonas, nem os agentes,
    nem a sessao de inspecao, nem o historico de metricas.
    """
    from primordial_soup import persistence

    # --- 1. Runtime conhecido, deliberadamente diferente do save ---
    state.update_runtime_rules(
        mutation_rate=7,
        mutated_genes=3,
        local_scale_fraction=42,
        zone_hp_effect=5,
    )
    state.tick_count = 123
    state.last_print = 123
    state.births = 9
    state.deaths = 4
    state.next_critter_id = 4242
    state.zones_active = True

    # Sessao de inspecao ativa, com trail e tudo.
    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    state.inspected_trail.append((11, 22))
    state.discovery_criterion = cfg.CRITERION_OLDEST
    state.discovery_lineage_filter = "G"

    # Metrica sintetica no historico.
    state.metrics_history["populacao"].append((0, (1.0, 1.0, 1.0)))

    # Snapshot de conteudo (para comparacao por valor).
    rules_before = state.runtime_rules
    before = {
        "mutation_rate": state.runtime_rules.mutation_rate,
        "mutated_genes": state.runtime_rules.mutated_genes,
        "local_scale_fraction": state.runtime_rules.local_scale_fraction,
        "zone_hp_effect": state.runtime_rules.zone_hp_effect,
        "tick_count": state.tick_count,
        "last_print": state.last_print,
        "births": state.births,
        "deaths": state.deaths,
        "next_critter_id": state.next_critter_id,
        "zones_active": state.zones_active,
        "zones_id": id(state.zones),
        "nests": state.nests,
        "nests_id": id(state.nests),
        "inspected_critter_id": state.inspected_critter_id,
        "discovery_criterion": state.discovery_criterion,
        "discovery_lineage_filter": state.discovery_lineage_filter,
        "trail": list(state.inspected_trail),
        "metrics_populacao": list(state.metrics_history["populacao"]),
        "agents_ids": [ag["ids"].copy() for ag in agents],
        "agents_len": [len(ag["agents"]) for ag in agents],
        "pool_len": [ag["pool"].shape[0] for ag in agents],
    }

    # Snapshot de identidade (para comparacao por `is`).
    agents_ref = agents
    lineage_refs = list(agents)
    pool_refs = [ag["pool"] for ag in agents]
    agent_refs = [ag["agents"] for ag in agents]
    ids_refs = [ag["ids"] for ag in agents]
    field_refs = [ag["field"] for ag in agents]

    # --- 2. Save com 2 linhagens e escalares diferentes ---
    path = tmp_path / "invalido.pkl"
    persistence.save(str(path))
    with open(path, "rb") as f:
        data = pickle.load(f)
    data["linhagens"] = data["linhagens"][:2]
    data["mutation"] = 99
    data["tick"] = 9999
    data["nascimentos"] = 777
    data["mortes"] = 888
    with open(path, "wb") as f:
        pickle.dump(data, f)

    # --- 3. Load rejeitado ---
    assert persistence.load(str(path)) is False

    # --- 4. Tudo intacto: conteudo ---
    #
    # Prova mais forte: load rejeitado nao substituiu nem sequer a
    # INSTANCIA de runtime_rules. Igualdade de valores nao basta.
    assert state.runtime_rules is rules_before
    assert state.runtime_rules.mutation_rate == before["mutation_rate"]
    assert state.runtime_rules.mutated_genes == before["mutated_genes"]
    assert (
        state.runtime_rules.local_scale_fraction
        == before["local_scale_fraction"]
    )
    assert state.runtime_rules.zone_hp_effect == before["zone_hp_effect"]
    assert state.tick_count == before["tick_count"]
    assert state.last_print == before["last_print"]
    assert state.births == before["births"]
    assert state.deaths == before["deaths"]
    assert state.next_critter_id == before["next_critter_id"]
    assert state.zones_active == before["zones_active"]
    assert id(state.zones) == before["zones_id"]
    assert state.nests == before["nests"]
    assert id(state.nests) == before["nests_id"]
    assert state.inspected_critter_id == before["inspected_critter_id"]
    assert state.discovery_criterion == before["discovery_criterion"]
    assert state.discovery_lineage_filter == before["discovery_lineage_filter"]
    assert list(state.inspected_trail) == before["trail"]
    assert list(state.metrics_history["populacao"]) == before["metrics_populacao"]
    for ag, expected_ids, expected_n, expected_pool in zip(
        agents,
        before["agents_ids"],
        before["agents_len"],
        before["pool_len"],
    ):
        assert np.array_equal(ag["ids"], expected_ids)
        assert len(ag["agents"]) == expected_n
        assert ag["pool"].shape[0] == expected_pool

    # --- 5. Tudo intacto: identidade ---
    # Uma implementacao que reconstroi o runtime com o mesmo conteudo
    # passaria nas assercoes acima mas falharia nestas. As duas
    # familias juntas sao o que prova ausencia de mutacao in-place.
    assert agents is agents_ref

    for i, ag in enumerate(agents):
        assert ag is lineage_refs[i]
        assert ag["pool"] is pool_refs[i]
        assert ag["agents"] is agent_refs[i]
        assert ag["ids"] is ids_refs[i]
        assert ag["field"] is field_refs[i]


def test_failed_load_does_not_consume_rng(fresh_world, tmp_path):
    """Um load rejeitado nao pode consumir draws do RNG global.

    generate_zones() usa o RNG global (stdlib random). Se um load
    rejeitado chamasse generate_zones() antes de falhar, uma run
    subsequente com a mesma seed divergiria de uma run identica que
    nunca tentou o load rejeitado.
    """
    from primordial_soup import persistence

    path = tmp_path / "invalido.pkl"
    assert persistence.save(str(path)) is True
    with open(path, "rb") as f:
        data = pickle.load(f)
    data["linhagens"] = data["linhagens"][:2]
    # Remove a chave de zonas: sem a correcao, load() cairia em
    # generate_zones() no parse phase.
    del data["zonas"]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _isolate_state()

    # Duas amostras identicas do RNG global com a mesma seed.
    _random.seed(12345)
    expected = [_random.random() for _ in range(5)]

    _random.seed(12345)
    assert persistence.load(str(path)) is False
    actual = [_random.random() for _ in range(5)]

    assert actual == expected, (
        "load() rejeitado consumiu draws do RNG global "
        "(generate_zones chamado no parse phase)."
    )
# ---------------------------------------------------------------------------
# Patch final: v20 behavior/lifecycle runtime persistence
# ---------------------------------------------------------------------------


def test_v21_runtime_rules_and_nests_round_trip(fresh_world, tmp_path):
    """Roundtrip v21: RuntimeRules + nests.

    Roundtrip do contrato atual: nao apenas os campos behavior, mas
    tambem a geometria persistente (nests) precisa ser restaurada
    identica ao que foi salvo.
    """
    from primordial_soup import persistence

    _install_checkpoint_geometry()
    expected_nests = state.nests
    state.update_runtime_rules(
        local_scale_sigma=0.25,
        global_probability=75,
        global_scale_fraction=40,
        global_scale_sigma=2.0,
        low_hp_threshold=3500,
        stay_still_impulse=-0.5,
        death_hp_threshold=500,
    )
    saved_rules = state.runtime_rules
    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    assert data["versao"] == cfg.SAVE_VERSION
    assert data["versao"] == 21
    assert data["low_hp_threshold"] == 3500
    assert data["stay_still_impulse"] == -0.5
    assert data["death_hp_threshold"] == 500

    # O save canonico externaliza nests como dict de lists.
    r_nest, g_nest, b_nest = expected_nests
    assert data["nests"] == {
        "R": [r_nest[0], r_nest[1]],
        "G": [g_nest[0], g_nest[1]],
        "B": [b_nest[0], b_nest[1]],
    }

    state.update_runtime_rules(
        local_scale_sigma=0.50,
        global_probability=10,
        global_scale_fraction=20,
        global_scale_sigma=1.0,
        low_hp_threshold=100,
        stay_still_impulse=3.0,
        death_hp_threshold=0,
    )
    state.nests = None

    assert state.runtime_rules != saved_rules
    assert persistence.load(str(path)) is True
    assert state.runtime_rules == saved_rules
    assert state.nests == expected_nests


@pytest.mark.parametrize(
    "field",
    [
        "low_hp_threshold",
        "stay_still_impulse",
        "death_hp_threshold",
    ],
)
def test_v21_rejects_missing_lifecycle_runtime_field_atomically(
    fresh_world, tmp_path, field
):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True
    with open(path, "rb") as f:
        data = pickle.load(f)
    del data[field]
    with open(path, "wb") as f:
        pickle.dump(data, f)

    before = state.runtime_rules
    assert persistence.load(str(path)) is False
    assert state.runtime_rules is before


def test_v20_is_rejected_without_migration(fresh_world, tmp_path):
    """v20 e predecessor direto do schema atual; sem migration.

    A politica do projeto e rejeitar tudo abaixo de SAVE_VERSION. Um
    v20 encontrado em disco deve ser recusado de forma limpa, sem
    tocar no runtime.
    """
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True
    with open(path, "rb") as f:
        data = pickle.load(f)
    data["versao"] = 20
    with open(path, "wb") as f:
        pickle.dump(data, f)

    before = state.runtime_rules
    assert persistence.load(str(path)) is False
    assert state.runtime_rules is before