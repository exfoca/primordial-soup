"""Testes de robustez do loader: rejeicao de payload corrompido e

atomicidade forte de persistence.load().
"""

import pickle
import random as _random

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup.config_compatibility import checkpoint_non_hot_payload
from primordial_soup.config_schema import ConfigScope, get_field_spec_by_attr
from primordial_soup.config_validation import resolve_constraints
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
    """Geometria deterministica de ninhos valida para o checkpoint atual."""
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


def _valid_test_zone_centers():
    """Centros de zona deterministicos, sem consumir RNG."""
    center = (
        layout.LAYOUT.world_width - cfg.ZONE_RADIUS - 1,
        layout.LAYOUT.world_height - cfg.ZONE_RADIUS - 1,
    )
    return tuple(
        center
        for _ in range(cfg.NUMBER_OF_ZONES)
    )


def _install_checkpoint_geometry():
    """Instala geometry valida para o checkpoint atual sem consumir RNG.

    zone_centers e a autoridade geometrica; zones e derivada por
    world.build_zone_mask(). Nao consome RNG.
    """
    centers = _valid_test_zone_centers()
    state.zone_centers = centers
    state.zones = world.build_zone_mask(centers)
    state.nests = _valid_test_nests()


@pytest.fixture
def fresh_world():
    """Populacao limpa com 3 linhagens, IDs alocados e geometry.

    O pool precisa ter o mesmo tamanho de agents/ids: deixar (0, G)
    aqui criaria um estado impossivel no runtime (agents=50, ids=50,
    pool=0) e quebraria os testes de compactacao e de save/load.

    Geometry e instalada explicitamente: o checkpoint atual exige
    zone_centers, zones e nests validos. Fixtures que salvam mundo
    manual precisam de um runtime checkpointavel deterministico.
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
    state.zone_centers = None
    state.nests = None
    agents.clear()


def _isolate_state():
    """Esvazia o runtime para que um load() rejeitado nao encontre
    estado residual. Usado depois de salvar um save valido, para que o
    proprio load de teste parta de um runtime limpo."""
    state.reset_counters()
    state.zones = None
    state.zone_centers = None
    state.nests = None
    agents.clear()
    seed_lineages()
    for ag in agents:
        ag["pool"] = np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32)


# ---------------------------------------------------------------------------
# Structural validation of the current contract: lineage count, per-array
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
    state.discovery_criterion = "oldest"
    state.discovery_lineage_filter = "G"

    # Metrica sintetica no historico.
    state.metrics_history["populacao"].append((0, (1.0, 1.0, 1.0)))

    # Archive/Inspection de morto sinteticos. O ID nao esta vivo e ja
    # foi alocado segundo next_critter_id, logo o runtime e saveavel.
    dead_agent = np.zeros((world.AGENT_COLUMNS,), dtype=np.float32)
    dead_agent[world.INDEX_X] = 33.0
    dead_agent[world.INDEX_Y] = 44.0
    dead_snapshot = state.DeathSnapshot(
        critter_id=4000,
        lineage_index=0,
        lineage_id="R",
        tick=100,
        agent=dead_agent,
        genome=np.zeros((cfg.GENOME_SIZE,), dtype=np.float32),
    )
    state.record_death_snapshot(dead_snapshot)
    state.set_inspection_death_selection(dead_snapshot)
    state.inspected_trail.append((33, 44))

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
        "zone_centers": state.zone_centers,
        "zone_centers_id": id(state.zone_centers),
        "nests": state.nests,
        "nests_id": id(state.nests),
        "inspected_critter_id": state.inspected_critter_id,
        "inspection_death_snapshot": state.inspection_death_snapshot,
        "recent_deaths": tuple(state.recent_deaths),
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
    recent_deaths_ref = state.recent_deaths

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
    assert state.zone_centers == before["zone_centers"]
    assert id(state.zone_centers) == before["zone_centers_id"]
    assert state.nests == before["nests"]
    assert id(state.nests) == before["nests_id"]
    assert state.inspected_critter_id == before["inspected_critter_id"]
    assert state.inspection_death_snapshot is before["inspection_death_snapshot"]
    assert tuple(state.recent_deaths) == before["recent_deaths"]
    assert state.recent_deaths is recent_deaths_ref
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
# Behavior/lifecycle runtime persistence in the current checkpoint schema
# ---------------------------------------------------------------------------


def test_current_runtime_rules_world_geometry_and_death_history_round_trip(
    fresh_world, tmp_path
):
    """Roundtrip atual: RuntimeRules + geometry + recent deaths.

    Roundtrip do contrato atual: campos behavior, RuntimeRules
    completo e TODA a geometria persistente (zone centers, mascara de
    zonas e nests) precisam ser restaurados identicos ao que foi
    salvo.
    """
    from primordial_soup import persistence

    _install_checkpoint_geometry()
    expected_zone_centers = state.zone_centers
    expected_zones = state.zones.copy()
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
    state.tick_count = 100
    state.deaths = 1
    dead_agent = np.zeros((world.AGENT_COLUMNS,), dtype=np.float32)
    dead_agent[world.INDEX_X] = 12.0
    dead_agent[world.INDEX_Y] = 13.0
    expected_death = state.DeathSnapshot(
        critter_id=state.next_critter_id,
        lineage_index=0,
        lineage_id="R",
        tick=100,
        agent=dead_agent,
        genome=np.zeros((cfg.GENOME_SIZE,), dtype=np.float32),
    )
    state.next_critter_id += 1
    state.record_death_snapshot(expected_death)
    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    with open(path, "rb") as f:
        data = pickle.load(f)
    assert data["versao"] == cfg.SAVE_VERSION
    assert cfg.SAVE_VERSION == 25
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
    state.zone_centers = None
    state.zones = None
    state.recent_deaths.clear()

    assert state.runtime_rules != saved_rules
    assert persistence.load(str(path)) is True
    assert state.runtime_rules == saved_rules
    assert state.zone_centers == expected_zone_centers
    assert np.array_equal(state.zones, expected_zones)
    assert state.nests == expected_nests
    assert len(state.recent_deaths) == 1
    restored = state.recent_deaths[0]
    assert restored.critter_id == expected_death.critter_id
    assert restored.lineage_id == expected_death.lineage_id
    assert restored.tick == expected_death.tick
    assert np.array_equal(restored.agent, expected_death.agent)
    assert np.array_equal(restored.genome, expected_death.genome)


@pytest.mark.parametrize(
    "field",
    [
        "low_hp_threshold",
        "stay_still_impulse",
        "death_hp_threshold",
    ],
)
def test_current_schema_rejects_missing_lifecycle_runtime_field_atomically(
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


def test_v24_is_rejected_without_migration(fresh_world, tmp_path):
    """v24 e predecessor direto do schema atual; sem migracao.

    A politica do projeto e rejeitar tudo abaixo de SAVE_VERSION. Um
    v24 encontrado em disco deve ser recusado de forma limpa, sem
    tocar no runtime.
    """
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True
    with open(path, "rb") as f:
        data = pickle.load(f)
    data["versao"] = 24
    with open(path, "wb") as f:
        pickle.dump(data, f)

    before = state.runtime_rules
    assert persistence.load(str(path)) is False
    assert state.runtime_rules is before


# ---------------------------------------------------------------------------
# Metadados NON-HOT de compatibilidade do checkpoint no schema corrente
# ---------------------------------------------------------------------------


def _rewrite_checkpoint(path, mutate):
    with open(path, "rb") as handle:
        data = pickle.load(handle)
    mutate(data)
    with open(path, "wb") as handle:
        pickle.dump(data, handle)
    return data


def test_save_writes_canonical_non_hot_compatibility_payload(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True
    with open(path, "rb") as handle:
        data = pickle.load(handle)

    assert data["versao"] == cfg.SAVE_VERSION == 25
    assert data["config_non_hot"] == checkpoint_non_hot_payload(cfg.CONFIG_SNAPSHOT)


def test_load_rejects_missing_non_hot_compatibility_payload_atomically(
    fresh_world, tmp_path
):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True
    _rewrite_checkpoint(path, lambda data: data.pop("config_non_hot"))

    rules_before = state.runtime_rules
    tick_before = state.tick_count
    assert persistence.load(str(path)) is False
    assert state.runtime_rules is rules_before
    assert state.tick_count == tick_before


def test_load_rejects_non_hot_compatibility_payload_with_wrong_shape(
    fresh_world, tmp_path
):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True
    _rewrite_checkpoint(path, lambda data: data.__setitem__("config_non_hot", []))

    assert persistence.load(str(path)) is False


def test_load_rejects_non_hot_compatibility_payload_missing_subfield(
    fresh_world, tmp_path
):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    def corrupt(data):
        del data["config_non_hot"]["INITIAL_HP"]

    _rewrite_checkpoint(path, corrupt)
    assert persistence.load(str(path)) is False


def test_load_rejects_non_hot_compatibility_payload_extra_subfield(
    fresh_world, tmp_path
):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    def corrupt(data):
        data["config_non_hot"]["FUTURE_NON_HOT"] = 1

    _rewrite_checkpoint(path, corrupt)
    assert persistence.load(str(path)) is False


@pytest.mark.parametrize(
    "env_key",
    [
        "NEST_RADIUS",
        "HIDDEN_NEURONS",
        "MAX_POPULATION_PER_LINEAGE",
        "SCREEN_WIDTH",
    ],
)
def test_load_rejects_non_hot_value_mismatch_before_main_parse(
    fresh_world, tmp_path, env_key
):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    def corrupt(data):
        data["config_non_hot"][env_key] += 1

    _rewrite_checkpoint(path, corrupt)
    assert persistence.load(str(path)) is False


def test_non_hot_mismatch_preserves_runtime_state_and_object_identity(
    fresh_world, tmp_path
):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    def corrupt(data):
        data["config_non_hot"]["NEST_RADIUS"] += 1

    _rewrite_checkpoint(path, corrupt)

    rules_before = state.runtime_rules
    tick_before = state.tick_count
    births_before = state.births
    deaths_before = state.deaths
    cooldown_before = state.reproduction_cooldown
    turn_before = state.reproduction_turn
    agents_ref = agents
    lineage_refs = tuple(agents)
    pool_refs = tuple(lineage["pool"] for lineage in agents)
    agent_refs = tuple(lineage["agents"] for lineage in agents)
    ids_refs = tuple(lineage["ids"] for lineage in agents)
    field_refs = tuple(lineage["field"] for lineage in agents)
    zones_ref = state.zones
    zone_centers_ref = state.zone_centers
    nests_ref = state.nests
    recent_deaths_ref = state.recent_deaths
    recent_deaths_before = tuple(state.recent_deaths)

    assert persistence.load(str(path)) is False

    assert state.runtime_rules is rules_before
    assert state.tick_count == tick_before
    assert state.births == births_before
    assert state.deaths == deaths_before
    assert state.reproduction_cooldown == cooldown_before
    assert state.reproduction_turn == turn_before
    assert agents is agents_ref
    assert all(current is expected for current, expected in zip(agents, lineage_refs))
    assert all(
        lineage["pool"] is expected for lineage, expected in zip(agents, pool_refs)
    )
    assert all(
        lineage["agents"] is expected for lineage, expected in zip(agents, agent_refs)
    )
    assert all(
        lineage["ids"] is expected for lineage, expected in zip(agents, ids_refs)
    )
    assert all(
        lineage["field"] is expected for lineage, expected in zip(agents, field_refs)
    )
    assert state.zones is zones_ref
    assert state.zone_centers is zone_centers_ref
    assert state.nests is nests_ref
    assert state.recent_deaths is recent_deaths_ref
    assert tuple(state.recent_deaths) == recent_deaths_before


def test_non_hot_mismatch_does_not_consume_python_or_numpy_rng(
    fresh_world, tmp_path
):
    from primordial_soup import persistence

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    def corrupt(data):
        data["config_non_hot"]["NEST_RADIUS"] += 1

    _rewrite_checkpoint(path, corrupt)

    _random.seed(12345)
    np.random.seed(54321)
    expected_python = [_random.random() for _ in range(5)]
    expected_numpy = np.random.random(5)

    _random.seed(12345)
    np.random.seed(54321)
    assert persistence.load(str(path)) is False
    actual_python = [_random.random() for _ in range(5)]
    actual_numpy = np.random.random(5)

    assert actual_python == expected_python
    assert np.array_equal(actual_numpy, expected_numpy)


_EXPECTED_V25_TOP_LEVEL_KEYS = {
    "versao",
    "arquitetura",
    "genoma",
    "config_non_hot",
    "mutation",
    "mutategen",
    "crossover_mode",
    "crossover_probability",
    "block_size",
    "mutation_mode",
    "escala_local",
    "local_scale_sigma",
    "global_probability",
    "global_scale_fraction",
    "global_scale_sigma",
    "low_hp_threshold",
    "stay_still_impulse",
    "death_hp_threshold",
    "tick",
    "proximo_id",
    "nascimentos",
    "mortes",
    "mortes_recentes",
    "reproduction_cooldown",
    "reproduction_turn",
    "rng_python_state",
    "rng_numpy_state",
    "zonas",
    "centros_zonas",
    "zonas_ativas",
    "efeito_hp_zonas",
    "nests",
    "base_decay_per_tick",
    "predation_transfer",
    "damage_per_own_overcrowding",
    "reproduction_interval",
    "reproduction_min_age",
    "reproduction_hp_gate",
    "reproduction_min_encounters",
    "reproduction_parent_hp_bonus",
    "reproduction_criterion",
    "reproduction_pool_fraction",
    "reproduction_attempts_divisor",
    "reproduction_min_score",
    "longevity_weight",
    "exploration_weight",
    "interaction_weight",
    "reproduction_weight",
    "linhagens",
}


_TOP_LEVEL_HISTORICAL_ALIASES = (
    ("versao", "version"),
    ("arquitetura", "architecture"),
    ("genoma", "genome"),
    ("centros_zonas", "zone_centers"),
    ("escala_local", "local_scale"),
    ("nascimentos", "births"),
    ("mortes", "deaths"),
    ("zonas", "zones"),
    ("zonas_ativas", "zones_active"),
    ("efeito_hp_zonas", "zone_hp_effect"),
    ("linhagens", "lineages"),
    ("mortes_recentes", "recent_deaths"),
)


def test_v25_writer_has_exact_canonical_top_level_and_lineage_shape(
    fresh_world, tmp_path
):
    from primordial_soup import persistence

    path = tmp_path / "v25.pkl"
    assert persistence.save(str(path)) is True
    with open(path, "rb") as handle:
        data = pickle.load(handle)

    assert cfg.SAVE_VERSION == 25
    assert len(_EXPECTED_V25_TOP_LEVEL_KEYS) == 49
    assert set(data) == _EXPECTED_V25_TOP_LEVEL_KEYS
    assert "modificadores_ambientais" not in data
    for record in data["linhagens"]:
        assert set(record) == {"id", "pools", "agentes", "ids"}
        assert "cor" not in record
        assert "color" not in record


@pytest.mark.parametrize(
    "canonical,alias",
    _TOP_LEVEL_HISTORICAL_ALIASES,
    ids=[f"{canonical}-not-{alias}" for canonical, alias in _TOP_LEVEL_HISTORICAL_ALIASES],
)
def test_v25_rejects_top_level_historical_key_aliases(
    fresh_world, tmp_path, canonical, alias
):
    from primordial_soup import persistence

    path = tmp_path / f"alias-{alias}.pkl"
    assert persistence.save(str(path)) is True

    def corrupt(data):
        data[alias] = data.pop(canonical)

    _rewrite_checkpoint(path, corrupt)
    assert persistence.load(str(path)) is False


@pytest.mark.parametrize(
    "canonical,alias",
    (("pools", "pool"), ("agentes", "agents")),
)
def test_v25_rejects_nested_lineage_historical_key_aliases(
    fresh_world, tmp_path, canonical, alias
):
    from primordial_soup import persistence

    path = tmp_path / f"nested-{alias}.pkl"
    assert persistence.save(str(path)) is True

    def corrupt(data):
        record = data["linhagens"][0]
        record[alias] = record.pop(canonical)

    _rewrite_checkpoint(path, corrupt)
    assert persistence.load(str(path)) is False


def test_historical_alias_failure_preserves_runtime_atomically(fresh_world, tmp_path):
    from primordial_soup import persistence

    path = tmp_path / "alias-atomicity.pkl"
    assert persistence.save(str(path)) is True

    def corrupt(data):
        data["version"] = data.pop("versao")

    _rewrite_checkpoint(path, corrupt)
    rules_before = state.runtime_rules
    tick_before = state.tick_count
    agents_before = tuple(agents)

    assert persistence.load(str(path)) is False
    assert state.runtime_rules is rules_before
    assert state.tick_count == tick_before
    assert tuple(agents) == agents_before


def test_implicit_load_does_not_discover_legacy_single_file(
    fresh_world, tmp_path, monkeypatch
):
    from primordial_soup import persistence

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(state, "active_save_slot", cfg.DEFAULT_SAVE_SLOT)
    legacy = tmp_path / "genome_pool.pkl"
    assert persistence.save(str(legacy)) is True
    assert not (tmp_path / "genome_pool_default.pkl").exists()

    state.tick_count = 987654
    rules_before = state.runtime_rules
    assert persistence.load() is False
    assert state.tick_count == 987654
    assert state.runtime_rules is rules_before


def test_explicit_legacy_filename_is_not_blacklisted(
    fresh_world, tmp_path, monkeypatch
):
    from primordial_soup import persistence

    monkeypatch.chdir(tmp_path)
    legacy = tmp_path / "genome_pool.pkl"
    state.tick_count = 321
    assert persistence.save(str(legacy)) is True

    state.tick_count = 999
    assert persistence.load(str(legacy)) is True
    assert state.tick_count == 321
