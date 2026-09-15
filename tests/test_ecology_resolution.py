"""Contratos do resolver ecologico (Patch 3).

Cobre a semantica de compute_ecology_resolution() em isolamento:
deltas de HP e de encounter sob predation, overkill, multiplos
predadores, multiplas presas, overcrowding proporcional, encounter
unico e triad chaos.

Depois cobre apply_ecology_resolution(): mortes simultaneas em mais
de uma linhagem, lockstep ids/pool/agents, contagem de deaths,
recomputacao de score, e ausencia de mutacao observavel em compute.

Todos os docstrings sao ASCII puro.
"""

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import ecology
from primordial_soup import state
from primordial_soup import world
from primordial_soup.state import agents
from primordial_soup.world import (
    INDEX_HP,
    INDEX_TIME,
    INDEX_X,
    INDEX_Y,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_world(positions):
    """Cria uma populacao minima com os individuos nas posicoes dadas.

    positions: lista de listas; positions[li] = [(x, y), ...]
    aloca n_i individuos na linhagem li.

    Retorna nada; assume state limpo.
    """
    state.reset_counters()
    world.seed_lineages()

    # Monta pool/agents/ids por linhagem em lockstep.
    for li, coords in enumerate(positions):
        n = len(coords)
        agent = agents[li]
        agent["pool"] = np.zeros(
            (n, cfg.GENOME_SIZE), dtype=np.float32
        )
        agent["agents"] = np.zeros(
            (n, world.AGENT_COLUMNS), dtype=np.float32
        )
        agent["ids"] = np.arange(
            1 + sum(len(p) for p in positions[:li]),
            1 + sum(len(p) for p in positions[:li]) + n,
            dtype=np.int64,
        )
        for i, (x, y) in enumerate(coords):
            agent["agents"][i, INDEX_X] = float(x)
            agent["agents"][i, INDEX_Y] = float(y)
            agent["agents"][i, INDEX_HP] = 1000.0
            agent["agents"][i, INDEX_TIME] = 0.0
        agent["field"] = np.zeros(
            (__import__("primordial_soup.layout", fromlist=["LAYOUT"]).LAYOUT.world_width,
             __import__("primordial_soup.layout", fromlist=["LAYOUT"]).LAYOUT.world_height),
            dtype=np.int16,
        )

    # Avanca next_critter_id.
    state.next_critter_id = 1 + sum(len(p) for p in positions)

    world.fill_fields()


def _reset_ecology_rules():
    """Zera base/zone e usa predation_transfer default.

    Overcrowding permanece no default (>= MIN) para evitar rejeicao
    de validacao.
    """
    state.zones = None
    state.nests = None
    state.update_runtime_rules(
        base_decay_per_tick=0,
        predation_transfer=cfg.MIN_PREDATION_TRANSFER,
    )


# ---------------------------------------------------------------------------
# Predation cycle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pred_li,prey_li",
    [(0, 1), (1, 2), (2, 0)],
    ids=["R_hunts_G", "G_hunts_B", "B_hunts_R"],
)
def test_predation_cycle_hits_only_canonical_relation(pred_li, prey_li):
    positions = [[] for _ in range(cfg.TOTAL_LINEAGES)]
    positions[pred_li] = [(10, 10)]
    positions[prey_li] = [(10, 10)]
    _setup_world(positions)
    _reset_ecology_rules()
    state.update_runtime_rules(predation_transfer=100)

    res = ecology.compute_ecology_resolution()

    assert res.hp_deltas[pred_li][0] > 0
    assert res.hp_deltas[prey_li][0] < 0
    # A terceira linhagem nao participa.
    other = ({0, 1, 2} - {pred_li, prey_li}).pop()
    assert res.hp_deltas[other].size == 0


def test_predation_reverse_relation_does_not_happen():
    """R e G na mesma celula: apenas R->G; G nao dana R."""
    _setup_world([[(10, 10)], [(10, 10)], []])
    _reset_ecology_rules()
    state.update_runtime_rules(predation_transfer=100)

    res = ecology.compute_ecology_resolution()

    assert res.hp_deltas[0][0] == pytest.approx(100.0)
    assert res.hp_deltas[1][0] == pytest.approx(-100.0)


# ---------------------------------------------------------------------------
# Overkill
# ---------------------------------------------------------------------------


def test_overkill_uses_snapshot_hp():
    _setup_world([[(10, 10)], [(10, 10)], []])
    _reset_ecology_rules()
    state.update_runtime_rules(predation_transfer=100)

    # Presa com HP baixo.
    agents[1]["agents"][0, INDEX_HP] = 37.0

    res = ecology.compute_ecology_resolution()

    # Presa perde no maximo 37; predador recebe 37.
    assert res.hp_deltas[1][0] == pytest.approx(-37.0)
    assert res.hp_deltas[0][0] == pytest.approx(37.0)


# ---------------------------------------------------------------------------
# Multiplos predadores
# ---------------------------------------------------------------------------


def test_multiple_predators_share_floor_reward():
    _setup_world([[(10, 10), (10, 10)], [(10, 10)], []])
    _reset_ecology_rules()
    state.update_runtime_rules(
        predation_transfer=100,
        damage_per_own_overcrowding=10,
    )

    res = ecology.compute_ecology_resolution()

    # Presa: -100 pela predacao.
    # Predacao contribui +50 para cada R.
    # Overcrowding R: 2 proprios -> -10*2 = -20 cada R.
    # Delta liquido por R: +50 - 20 = +30.
    assert res.hp_deltas[1][0] == pytest.approx(-100.0)
    assert res.hp_deltas[0][0] == pytest.approx(30.0)
    assert res.hp_deltas[0][1] == pytest.approx(30.0)


def test_floor_division_discards_remainder():
    """3 R + 1 G, transfer=100: cada R recebe 33, presa perde 100."""
    _setup_world([[(10, 10), (10, 10), (10, 10)], [(10, 10)], []])
    _reset_ecology_rules()
    state.update_runtime_rules(
        predation_transfer=100,
        damage_per_own_overcrowding=cfg.MIN_DAMAGE_PER_OWN_OVERCROWDING,
    )

    res = ecology.compute_ecology_resolution()

    # Presa: -100.
    assert res.hp_deltas[1][0] == pytest.approx(-100.0)

    # Cada R: +33 pela predacao, -30 pela overcrowding (10 * 3),
    # -10 da base * nao * (base_decay = 0).
    # Portanto cada R: +33 - 30 = +3.
    for i in range(3):
        assert res.hp_deltas[0][i] == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# Multiplas presas
# ---------------------------------------------------------------------------


def test_multiple_preys_accumulate_reward():
    """1 R, 2 G: R recebe de cada presa."""
    _setup_world([[(10, 10)], [(10, 10), (10, 10)], []])
    _reset_ecology_rules()
    state.update_runtime_rules(
        predation_transfer=100,
        damage_per_own_overcrowding=cfg.MIN_DAMAGE_PER_OWN_OVERCROWDING,
    )

    res = ecology.compute_ecology_resolution()

    # Cada G: -100 (predacao) -20 (overcrowding: 10*2).
    for i in range(2):
        assert res.hp_deltas[1][i] == pytest.approx(-120.0)

    # R recebe +100 de cada presa = +200.
    assert res.hp_deltas[0][0] == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# Overcrowding proporcional
# ---------------------------------------------------------------------------


def test_overcrowding_scales_with_N():
    """3 R mesma celula, factor 10: -30 cada."""
    _setup_world([[(10, 10), (10, 10), (10, 10)], [], []])
    _reset_ecology_rules()
    state.update_runtime_rules(damage_per_own_overcrowding=10)

    res = ecology.compute_ecology_resolution()

    for i in range(3):
        assert res.hp_deltas[0][i] == pytest.approx(-30.0)


def test_overcrowding_is_zero_below_two():
    _setup_world([[(10, 10)], [], []])
    _reset_ecology_rules()
    state.update_runtime_rules(damage_per_own_overcrowding=10)

    res = ecology.compute_ecology_resolution()

    assert res.hp_deltas[0][0] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Encounter
# ---------------------------------------------------------------------------


def test_encounter_marks_presence_only():
    """R + G mesma celula: ambos recebem encounter +1, nao +2."""
    _setup_world([[(10, 10)], [(10, 10)], []])
    _reset_ecology_rules()

    res = ecology.compute_ecology_resolution()

    assert res.encounter_deltas[0][0] == pytest.approx(1.0)
    assert res.encounter_deltas[1][0] == pytest.approx(1.0)


def test_encounter_is_not_duplicated_by_multiple_rivals():
    """R + 2 G mesma celula: R recebe +1 (nao +2)."""
    _setup_world([[(10, 10)], [(10, 10), (10, 10)], []])
    _reset_ecology_rules()

    res = ecology.compute_ecology_resolution()

    assert res.encounter_deltas[0][0] == pytest.approx(1.0)


def test_encounter_in_triad_is_still_one_per_individual():
    _setup_world([[(10, 10)], [(10, 10)], [(10, 10)]])
    _reset_ecology_rules()

    res = ecology.compute_ecology_resolution()

    for li in range(3):
        assert res.encounter_deltas[li][0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Triad chaos
# ---------------------------------------------------------------------------


def test_triad_selects_exactly_one_relation():
    _setup_world([[(10, 10)], [(10, 10)], [(10, 10)]])
    _reset_ecology_rules()
    state.update_runtime_rules(
        predation_transfer=100,
        damage_per_own_overcrowding=cfg.MIN_DAMAGE_PER_OWN_OVERCROWDING,
    )

    # Base_decay = 0, sem overcrowding. Vamos olhar so predation:
    # exatamente 1 ganhador, 1 perdedor, 1 neutro.
    res = ecology.compute_ecology_resolution()

    positives = sum(1 for li in range(3) if res.hp_deltas[li][0] > 0)
    negatives = sum(1 for li in range(3) if res.hp_deltas[li][0] < 0)
    zeros = sum(1 for li in range(3) if res.hp_deltas[li][0] == 0)

    assert positives == 1
    assert negatives == 1
    assert zeros == 1


def test_triad_determinism_same_rng_same_result():
    _setup_world([[(10, 10)], [(10, 10)], [(10, 10)]])
    _reset_ecology_rules()
    state.update_runtime_rules(predation_transfer=100)

    np.random.seed(42)
    res_a = ecology.compute_ecology_resolution()

    np.random.seed(42)
    res_b = ecology.compute_ecology_resolution()

    for li in range(3):
        assert res_a.hp_deltas[li][0] == res_b.hp_deltas[li][0]


# ---------------------------------------------------------------------------
# Nest protection
# ---------------------------------------------------------------------------


def test_nest_protection_blocks_predation():
    """G protegido em seu ninho nao sofre R->G."""
    _setup_world([[(50, 50)], [(50, 50)], []])
    _reset_ecology_rules()
    state.update_runtime_rules(predation_transfer=100)

    # Ninhos: G em (50,50).
    state.nests = (
        (10, 10),  # R -- longe
        (50, 50),  # G -- sobre o individuo
        (80, 80),  # B
    )

    res = ecology.compute_ecology_resolution()

    # G nao sofre predacao, R nao recebe.
    assert res.hp_deltas[1][0] == pytest.approx(0.0)
    assert res.hp_deltas[0][0] == pytest.approx(0.0)
    # Encounter ainda acontece.
    assert res.encounter_deltas[0][0] == pytest.approx(1.0)
    assert res.encounter_deltas[1][0] == pytest.approx(1.0)


def test_nests_none_means_no_protection():
    """state.nests is None: nenhuma protecao."""
    _setup_world([[(50, 50)], [(50, 50)], []])
    _reset_ecology_rules()
    state.update_runtime_rules(predation_transfer=100)
    state.nests = None

    res = ecology.compute_ecology_resolution()

    assert res.hp_deltas[1][0] == pytest.approx(-100.0)
    assert res.hp_deltas[0][0] == pytest.approx(100.0)


def test_nests_invalid_length_fails():
    _setup_world([[(50, 50)], [(50, 50)], []])
    _reset_ecology_rules()
    state.nests = ((10, 10),)  # so 1 centro

    with pytest.raises(AssertionError):
        ecology.compute_ecology_resolution()


# ---------------------------------------------------------------------------
# compute nao muta populacao
# ---------------------------------------------------------------------------


def test_compute_does_not_mutate_populations():
    _setup_world([[(10, 10)], [(20, 20)], [(30, 30)]])
    _reset_ecology_rules()

    before_agents = [ag["agents"].copy() for ag in agents]
    before_pools = [ag["pool"].copy() for ag in agents]
    before_ids = [ag["ids"].copy() for ag in agents]
    before_fields = [ag["field"].copy() for ag in agents]
    before_births = state.births
    before_deaths = state.deaths

    ecology.compute_ecology_resolution()

    for i, ag in enumerate(agents):
        assert np.array_equal(ag["agents"], before_agents[i])
        assert np.array_equal(ag["pool"], before_pools[i])
        assert np.array_equal(ag["ids"], before_ids[i])
        assert np.array_equal(ag["field"], before_fields[i])
    assert state.births == before_births
    assert state.deaths == before_deaths


# ---------------------------------------------------------------------------
# apply: mortes simultaneas, lockstep, score
# ---------------------------------------------------------------------------


def test_apply_handles_simultaneous_deaths():
    """Duas linhagens perdem individuos no mesmo tick."""
    _setup_world([[(10, 10)], [(20, 20)], [(30, 30)]])
    _reset_ecology_rules()

    # Mata R e G por starvation direta.
    agents[0]["agents"][0, INDEX_HP] = 0.0
    agents[1]["agents"][0, INDEX_HP] = 0.0

    res = ecology.compute_ecology_resolution()
    deaths_before = state.deaths
    ecology.apply_ecology_resolution(res)

    assert agents[0]["agents"].shape[0] == 0
    assert agents[1]["agents"].shape[0] == 0
    assert agents[2]["agents"].shape[0] == 1
    assert state.deaths == deaths_before + 2


def test_apply_keeps_lockstep():
    _setup_world([[(10, 10), (11, 11)], [], []])
    _reset_ecology_rules()
    agents[0]["agents"][0, INDEX_HP] = 0.0

    res = ecology.compute_ecology_resolution()
    ecology.apply_ecology_resolution(res)

    ag = agents[0]
    assert ag["agents"].shape[0] == 1
    assert ag["pool"].shape[0] == 1
    assert ag["ids"].shape[0] == 1


def test_apply_recomputes_scores():
    _setup_world([[(10, 10)], [], []])
    _reset_ecology_rules()

    res = ecology.compute_ecology_resolution()
    ecology.apply_ecology_resolution(res)

    # Score foi escrito.
    assert agents[0]["agents"][0, world.INDEX_COMPOSITE_SCORE] >= 0.0


def test_apply_does_not_cap_hp():
    """HP pode ultrapassar INITIAL_HP."""
    _setup_world([[(10, 10)], [(10, 10)], []])
    _reset_ecology_rules()
    state.update_runtime_rules(predation_transfer=200)
    agents[0]["agents"][0, INDEX_HP] = float(cfg.INITIAL_HP)
    agents[1]["agents"][0, INDEX_HP] = float(cfg.INITIAL_HP)

    res = ecology.compute_ecology_resolution()
    ecology.apply_ecology_resolution(res)

    assert agents[0]["agents"][0, INDEX_HP] > float(cfg.INITIAL_HP)
