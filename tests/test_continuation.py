"""Testes de continuidade exata do checkpoint (SAVE_VERSION 11).

A propriedade central que estes testes definem:

    checkpoint
    =
    continuacao exata da simulacao

Concretamente: rodar N ticks, salvar, rodar M ticks a partir do save
carregado, deve produzir o MESMO estado que rodar N+M ticks
ininterruptos. Sem essa propriedade, "salvar o mundo" nao passa de
"salvar a populacao"; scheduler reprodutivo e RNG ficariam para tras,
e o futuro divergiria silenciosamente.

Cobrem:
  - scheduler reprodutivo (reproduction_cooldown / reproduction_turn)
  - RNG da stdlib random
  - RNG global do NumPy
  - todo o resto do estado observavel (pool, agents, ids, tick,
    births, deaths, next_critter_id, zones, mutation runtime)

Todos os docstrings e comentarios deste arquivo sao intencionalmente
ASCII puro, seguindo o estilo de nomenclatura interna do projeto.
"""

import random

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import persistence
from primordial_soup import simulation
from primordial_soup import state
from primordial_soup.state import agents


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_runtime_snapshot() -> dict:
    """Snapshot comparavel do estado observavel da simulacao.

    Cobre tudo o que as Diretrizes de execucao (bloco 2) listam como
    parte da continuacao exata, mais os RNGs. Nao inclui campos que
    NAO fazem parte do contrato (inspection, language, recording,
    metric history): esses sao preferencias ou views, nao mundo.
    """
    return {
        # Populacao, em lockstep.
        "pool": [
            ag["pool"].copy() if ag["pool"].size else ag["pool"].copy()
            for ag in agents
        ],
        "agents": [
            ag["agents"].copy() if ag["agents"].size else ag["agents"].copy()
            for ag in agents
        ],
        "ids": [ag["ids"].copy() for ag in agents],
        # Contadores e relogio.
        "tick_count": state.tick_count,
        "births": state.births,
        "deaths": state.deaths,
        "next_critter_id": state.next_critter_id,
        # Scheduler reprodutivo.
        "reproduction_cooldown": state.reproduction_cooldown,
        "reproduction_turn": state.reproduction_turn,
        # Ambiente.
        "zones": None if state.zones is None else state.zones.copy(),
        "zones_active": state.zones_active,
        "zone_hp_effect": state.runtime_rules.zone_hp_effect,
        # Parametros runtime de mutacao.
        "mutation_rate": state.runtime_rules.mutation_rate,
        "mutated_genes": state.runtime_rules.mutated_genes,
        "local_scale_fraction": state.runtime_rules.local_scale_fraction,
        # RNGs. random.getstate() e comparavel com == (tupla pura);
        # np.random.get_state() devolve ndarray, entao tem helper.
        "rng_python_state": random.getstate(),
        "rng_numpy_state": np.random.get_state(),
    }


def _rng_numpy_states_equal(a, b) -> bool:
    """Compara dois resultados de np.random.get_state().

    get_state() devolve (str, ndarray[624] uint32, int, int, float).
    Comparar direto com == devolve ndarray de bool, nao bool; por
    isso este helper existe. Comparacao estrutural completa, sem
    atalhos: qualquer divergencia nos elementos nao-array tambem
    invalida.
    """
    if a[0] != b[0]:
        return False
    if not np.array_equal(a[1], b[1]):
        return False
    if a[2] != b[2] or a[3] != b[3] or a[4] != b[4]:
        return False
    return True


def _assert_snapshots_equal(a: dict, b: dict) -> None:
    """Compara dois snapshots e reporta o primeiro campo divergente."""
    for key in a:
        av, bv = a[key], b[key]
        if key == "rng_numpy_state":
            assert _rng_numpy_states_equal(av, bv), (
                f"campo {key!r} divergiu entre as duas execucoes."
            )
        elif key in ("pool", "agents", "ids", "zones"):
            if av is None or bv is None:
                assert av is bv, (
                    f"campo {key!r} divergiu (None vs non-None)."
                )
                continue
            assert len(av) == len(bv), (
                f"campo {key!r}: comprimento divergiu."
            )
            for i, (x, y) in enumerate(zip(av, bv)):
                assert np.array_equal(x, y), (
                    f"campo {key!r}[{i}] divergiu entre as duas "
                    f"execucoes."
                )
        else:
            assert av == bv, (
                f"campo {key!r} divergiu: {av!r} vs {bv!r}."
            )


def _dirty_runtime():
    """Deixa o runtime num estado comprovadamente diferente do save.

    reset_counters() + seed_lineages() limpam contadores e
    populacao, mas nao mexem nos RNGs. Semear com valor diferente do
    save garante que, se o load esquecesse de restaurar o RNG, a
    comparacao A==B detectaria. Sem essa semeadura, o RNG poderia
    coincidir por acidente com o estado salvo, mascarando um bug.
    """
    state.reset_counters()
    agents.clear()
    from primordial_soup.world import seed_lineages

    seed_lineages()
    for ag in agents:
        ag["pool"] = np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32)

    # Semeadura deliberadamente diferente da usada no bootstrap do
    # teste. Os valores concretos sao irrelevantes; o que importa e
    # serem distintos da seed principal.
    random.seed(987_654_321)
    np.random.seed(123_456_789)


# ---------------------------------------------------------------------------
# Continuidade A == B
# ---------------------------------------------------------------------------


def test_checkpoint_is_exact_continuation(tmp_path):
    """Rodar N+M ticks ininterruptos == rodar N, salvar, carregar, M.

    Este e o teste que define a propriedade "checkpoint = continuacao
    exata da simulacao". Se ele passa, scheduler reprodutivo e RNGs
    estao persistidos corretamente; se falha, o save nao captura o
    futuro do mundo.
    """
    # --- Execucao A: ininterrupta, sem passar por disco ---------------
    random.seed(42)
    np.random.seed(42)
    simulation.bootstrap_new_world()
    for _ in range(30):
        simulation.step()

    path = tmp_path / "checkpoint.pkl"
    persistence.save(str(path))

    for _ in range(30):
        simulation.step()

    snapshot_a = _capture_runtime_snapshot()

    # --- Execucao B: mesma seed, checkpoint no meio, M ticks depois ---
    _dirty_runtime()

    random.seed(42)
    np.random.seed(42)
    simulation.bootstrap_new_world()
    for _ in range(30):
        simulation.step()
    persistence.save(str(path))

    # Antes de carregar: suja o runtime de novo, para provar que o
    # load substitui TODO o estado, nao apenas concorda por acaso.
    _dirty_runtime()

    assert persistence.load(str(path)) is True

    for _ in range(30):
        simulation.step()

    snapshot_b = _capture_runtime_snapshot()

    _assert_snapshots_equal(snapshot_a, snapshot_b)


def test_load_restores_rng_state(tmp_path):
    """Apos load, o proximo sorteio bate com o que teria acontecido.

    Mais direto que o teste A==B: apos o load, os proximos draws de
    random.random() e np.random.rand() batem com os draws que a
    execucao ininterrupta faria no mesmo ponto.
    """
    random.seed(7)
    np.random.seed(7)
    simulation.bootstrap_new_world()
    for _ in range(20):
        simulation.step()

    # Draws de referencia que a execucao ininterrupta faria.
    expected_py = random.random()
    expected_np = float(np.random.rand())

    # Rebobina o tempo da simulacao: nova execucao com a mesma seed.
    _dirty_runtime()
    random.seed(7)
    np.random.seed(7)
    simulation.bootstrap_new_world()
    for _ in range(20):
        simulation.step()

    path = tmp_path / "rng.pkl"
    persistence.save(str(path))

    # Suja o runtime (inclusive RNGs) e carrega.
    _dirty_runtime()
    assert persistence.load(str(path)) is True

    got_py = random.random()
    got_np = float(np.random.rand())

    assert got_py == expected_py, (
        "random.random() apos load divergiu do draw que a execucao "
        "ininterrupta faria no mesmo ponto."
    )
    assert got_np == expected_np, (
        "np.random.rand() apos load divergiu do draw que a execucao "
        "ininterrupta faria no mesmo ponto."
    )


def test_load_restores_reproduction_scheduler(tmp_path):
    """Apos load, a fase do scheduler reprodutivo e a mesma do save."""
    random.seed(11)
    np.random.seed(11)
    simulation.bootstrap_new_world()
    for _ in range(45):  # meio do segundo ciclo de turno
        simulation.step()

    saved_cooldown = state.reproduction_cooldown
    saved_turn = state.reproduction_turn

    path = tmp_path / "sched.pkl"
    persistence.save(str(path))

    # Suja o runtime e o scheduler.
    _dirty_runtime()
    state.reproduction_cooldown = 999
    state.reproduction_turn = 999 % cfg.TOTAL_LINEAGES

    assert persistence.load(str(path)) is True

    assert state.reproduction_cooldown == saved_cooldown, (
        "reproduction_cooldown nao foi restaurado do checkpoint."
    )
    assert state.reproduction_turn == saved_turn, (
        "reproduction_turn nao foi restaurado do checkpoint."
    )


def test_failed_load_does_not_touch_rng(tmp_path):
    """Load rejeitado nao pode alterar os RNGs globais.

    Complementa tests/test_load_atomicity.py (que cobre estado do
    mundo). Aqui o foco e o RNG: um payload invalido nao pode, nem
    por probe mal posicionado, deixar o gerador global num estado
    diferente do que estava.
    """
    path = tmp_path / "bad.pkl"
    persistence.save(str(path))

    # Corrompe o payload: scheduler com turno fora do range.
    import pickle

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["reproduction_turn"] = cfg.TOTAL_LINEAGES + 5
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _dirty_runtime()

    # Referencia: dois draws identicos se a seed for repetida.
    random.seed(555)
    np.random.seed(555)
    expected_py = [random.random() for _ in range(3)]
    expected_np = [float(np.random.rand()) for _ in range(3)]

    random.seed(555)
    np.random.seed(555)
    assert persistence.load(str(path)) is False
    got_py = [random.random() for _ in range(3)]
    got_np = [float(np.random.rand()) for _ in range(3)]

    assert got_py == expected_py, (
        "load() rejeitado consumiu ou alterou o RNG da stdlib."
    )
    assert got_np == expected_np, (
        "load() rejeitado consumiu ou alterou o RNG global do NumPy."
    )


def test_failed_load_does_not_touch_reproduction_scheduler(tmp_path):
    """Load rejeitado nao pode alterar reproduction_cooldown/turn."""
    path = tmp_path / "bad2.pkl"
    persistence.save(str(path))

    import pickle

    with open(path, "rb") as f:
        data = pickle.load(f)
    data["reproduction_cooldown"] = -1  # fora do range
    with open(path, "wb") as f:
        pickle.dump(data, f)

    _dirty_runtime()
    state.reproduction_cooldown = 77
    state.reproduction_turn = 2

    assert persistence.load(str(path)) is False

    assert state.reproduction_cooldown == 77
    assert state.reproduction_turn == 2