"""Semantica hot das cinco regras reprodutivas (Patch 3).

Cobre:

  - scheduler real: simulation.step usa runtime reproduction_interval
    ao recarregar o cooldown.
  - transicao de interval -> cooldown (reducao, aumento, zero, no-op).
  - gates hot (age, HP, encounters) usando runtime_rules.
  - parent HP bonus runtime.
  - HP gate: fronteira HP == gate continua inelegivel.

Todos os docstrings deste arquivo sao ASCII puro.
"""

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import evolution
from primordial_soup import layout
from primordial_soup import nest_geometry
from primordial_soup import simulation
from primordial_soup import state
from primordial_soup import world
from primordial_soup.runtime_rules import default_runtime_rules
from primordial_soup.state import agents
from primordial_soup.world import (
    INDEX_COMPOSITE_SCORE,
    INDEX_ENCOUNTERS,
    INDEX_HP,
    INDEX_TIME,
    INDEX_X,
    INDEX_Y,
)


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
    """Instala zones vazias e nests deterministicos.

    Nao consome RNG. Fixtures de persistence/step precisam de geometry
    valida sob o contrato v21.
    """
    state.zones = np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=bool,
    )
    state.nests = _valid_test_nests()


@pytest.fixture(autouse=True)
def _cleanup():
    # reset_counters() preserva de proposito as regras runtime, entao
    # nao e fixture de isolamento suficiente. Restaurar RuntimeRules
    # integral antes e depois garante que cada teste comece de um
    # estado conhecido.
    #
    # zones e nests nao sao propriedade de nenhum teste deste arquivo
    # por padrao: cada teste que precisa de geometry instala
    # explicitamente. Zerar aqui evita vazamento entre testes.
    state.set_runtime_rules(default_runtime_rules())
    state.reproduction_cooldown = 0
    state.reproduction_turn = 0
    state.zones = None
    state.nests = None

    yield

    state.set_runtime_rules(default_runtime_rules())
    state.reproduction_cooldown = 0
    state.reproduction_turn = 0
    state.zones = None
    state.nests = None
    state.reset_counters()
    agents.clear()


# ---------------------------------------------------------------------------
# Scheduler real: simulation.step usa runtime interval
# ---------------------------------------------------------------------------


def test_step_uses_runtime_interval_when_reloading_cooldown():
    """Depois de consumir um turno, o cooldown e
    runtime_rules.reproduction_interval, nao cfg.REPRODUCTION_INTERVAL.
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

    state.update_runtime_rules(reproduction_interval=17)
    state.reproduction_cooldown = 0
    state.reproduction_turn = 0
    state.nests = _valid_test_nests()

    simulation.step()

    # O tick consumiu o turno disponivel (cooldown==0) e recarregou
    # com o runtime interval.
    assert state.reproduction_cooldown == 17, (
        "step() recarregou o cooldown com cfg.REPRODUCTION_INTERVAL "
        "em vez de runtime_rules.reproduction_interval."
    )


# ---------------------------------------------------------------------------
# Transicao interval -> cooldown (casos A, B, C, D)
# ---------------------------------------------------------------------------


def _setup_rules(interval: int) -> None:
    state.update_runtime_rules(reproduction_interval=interval)


def test_interval_reduction_clamps_cooldown():
    """A: reduzir interval abaixo do cooldown clampa em interval."""
    _setup_rules(150)
    state.reproduction_cooldown = 117

    state.update_runtime_rules(reproduction_interval=30)

    assert state.runtime_rules.reproduction_interval == 30
    assert state.reproduction_cooldown == 30


def test_interval_increase_does_not_postpone_turn():
    """B: aumentar interval nao posterga turno ja proximo."""
    _setup_rules(30)
    state.reproduction_cooldown = 7

    state.update_runtime_rules(reproduction_interval=300)

    assert state.runtime_rules.reproduction_interval == 300
    assert state.reproduction_cooldown == 7


def test_interval_change_with_zero_cooldown_keeps_zero():
    """C: cooldown zero permanece zero mesmo com interval menor."""
    _setup_rules(150)
    state.reproduction_cooldown = 0

    state.update_runtime_rules(reproduction_interval=20)

    assert state.runtime_rules.reproduction_interval == 20
    assert state.reproduction_cooldown == 0


def test_same_interval_keeps_identity_and_cooldown():
    """D: mudanca efetiva nula preserva identidade e cooldown."""
    _setup_rules(150)
    state.reproduction_cooldown = 90
    before = state.runtime_rules

    state.update_runtime_rules(reproduction_interval=150)

    assert state.runtime_rules is before
    assert state.reproduction_cooldown == 90


# ---------------------------------------------------------------------------
# Gates hot
# ---------------------------------------------------------------------------


def _minimal_population(n: int = 4):
    """Monta uma populacao minima com todos os gates permissivos.

    Cuidados:
      - place_initially() cria agents/ids com
        INITIAL_POPULATION_PER_LINEAGE linhas; reduzir para n para
        preservar o lockstep com pool.
      - HP default (INITIAL_HP) == MAX_REPRODUCTION_HP_GATE == gate
        default; como o gate usa comparacao estrita (<), definir HP
        abaixo do gate e obrigatorio para os individuos serem
        elegiveis por HP neste cenario.
    """
    state.reset_counters()
    world.seed_lineages()
    for ag in agents:
        ag["pool"] = np.random.uniform(
            cfg.MIN_GENE_VALUE, cfg.MAX_GENE_VALUE,
            (n, cfg.GENOME_SIZE),
        ).astype(np.float32)
    world.place_initially()
    for ag in agents:
        ag["agents"] = ag["agents"][:n].copy()
        ag["ids"] = ag["ids"][:n].copy()
        assert (
            ag["pool"].shape[0]
            == ag["agents"].shape[0]
            == ag["ids"].shape[0]
            == n
        ), "_minimal_population: lockstep violado"
    world.fill_fields()
    # Todos os individuos aptos por padrao.
    for ag in agents:
        m = ag["agents"]
        m[:, INDEX_HP] = float(cfg.MAX_REPRODUCTION_HP_GATE - 1)
        m[:, INDEX_COMPOSITE_SCORE] = cfg.REPRODUCTION_MIN_SCORE + 0.5
    state.update_runtime_rules(
        reproduction_min_age=0,
        reproduction_hp_gate=cfg.MAX_REPRODUCTION_HP_GATE,
        reproduction_min_encounters=0,
    )


def _eligible_ids_after(agent_index: int = 0) -> np.ndarray:
    """Retorna os IDs elegiveis da linhagem 0 pelo estado atual."""
    matrix = agents[agent_index]["agents"]
    rules = state.runtime_rules
    eligible = np.nonzero(
        (matrix[:, INDEX_TIME] >= rules.reproduction_min_age)
        & (matrix[:, INDEX_HP] < rules.reproduction_hp_gate)
        & (
            matrix[:, INDEX_COMPOSITE_SCORE]
            >= rules.reproduction_min_score
        )
        & (
            matrix[:, INDEX_ENCOUNTERS]
            >= rules.reproduction_min_encounters
        )
    )[0]
    return agents[agent_index]["ids"][eligible]


def test_age_gate_hot_change():
    _minimal_population()
    m = agents[0]["agents"]
    m[:, INDEX_TIME] = 1000

    # min_age=2000: ninguem passa no gate de idade.
    state.update_runtime_rules(reproduction_min_age=2000)
    assert _eligible_ids_after().size == 0

    # min_age=500 hot: os mesmos individuos passam sem reconstruir.
    state.update_runtime_rules(reproduction_min_age=500)
    assert _eligible_ids_after().size == m.shape[0]


def test_hp_gate_hot_change():
    _minimal_population()
    m = agents[0]["agents"]
    m[:, INDEX_HP] = 8000

    state.update_runtime_rules(reproduction_hp_gate=7000)
    assert _eligible_ids_after().size == 0

    state.update_runtime_rules(reproduction_hp_gate=9000)
    assert _eligible_ids_after().size == m.shape[0]


def test_hp_gate_is_strict():
    """HP == gate continua inelegivel (comparacao estrita)."""
    _minimal_population()
    m = agents[0]["agents"]
    m[:, INDEX_HP] = 5000

    state.update_runtime_rules(reproduction_hp_gate=5000)
    assert _eligible_ids_after().size == 0

    state.update_runtime_rules(reproduction_hp_gate=5001)
    assert _eligible_ids_after().size == m.shape[0]


def test_encounters_gate_hot_change():
    _minimal_population()
    m = agents[0]["agents"]
    m[:, INDEX_ENCOUNTERS] = 3

    state.update_runtime_rules(reproduction_min_encounters=5)
    assert _eligible_ids_after().size == 0

    state.update_runtime_rules(reproduction_min_encounters=2)
    assert _eligible_ids_after().size == m.shape[0]


# ---------------------------------------------------------------------------
# Parent HP bonus runtime
# ---------------------------------------------------------------------------


def _prepare_breeding_pair(lineage_index: int = 0):
    """Prepara 4 agentes da linhagem dada prontos para reproduzir.

    Os gates sao por linhagem; preparar apenas a linhagem de interesse
    evita que um teste que exercita G veja o conjunto vazio porque o
    helper montou R. O default preserva o uso anterior.
    """
    state.reset_counters()
    world.seed_lineages()
    n = 4
    for ag in agents:
        ag["pool"] = np.random.uniform(
            cfg.MIN_GENE_VALUE, cfg.MAX_GENE_VALUE,
            (n, cfg.GENOME_SIZE),
        ).astype(np.float32)
    world.place_initially()
    for ag in agents:
        ag["agents"] = ag["agents"][:n].copy()
        ag["ids"] = ag["ids"][:n].copy()

    m = agents[lineage_index]["agents"]
    for i in (0, 1):
        m[i, INDEX_TIME] = cfg.REPRODUCTION_MIN_AGE + 100
        m[i, INDEX_HP] = cfg.REPRODUCTION_HP_GATE - 1000
        m[i, INDEX_ENCOUNTERS] = cfg.REPRODUCTION_MIN_ENCOUNTERS + 10
        m[i, INDEX_COMPOSITE_SCORE] = cfg.REPRODUCTION_MIN_SCORE + 0.5

    state.nests = _valid_test_nests()


def test_parent_bonus_runtime_value():
    """Bonus efetivo vem de runtime_rules, nao de cfg."""
    _prepare_breeding_pair()
    state.update_runtime_rules(mutation_rate=0)
    state.update_runtime_rules(reproduction_parent_hp_bonus=250)

    m = agents[0]["agents"]
    hp_before = [float(m[i, INDEX_HP]) for i in range(4)]

    evolution._reproduce_one_pair(
        agents[0],
        mutation_rate=0,
        mutated_genes=1,
        local_scale_fraction=cfg.MIN_LOCAL_SCALE_FRACTION,
        lineage_index=0,
        crossover_mode=state.runtime_rules.crossover_mode,
        crossover_probability=state.runtime_rules.crossover_probability,
        block_size=state.runtime_rules.block_size,
        mutation_mode=state.runtime_rules.mutation_mode,
        local_scale_sigma=state.runtime_rules.local_scale_sigma,
        global_probability=state.runtime_rules.global_probability,
        global_scale_fraction=state.runtime_rules.global_scale_fraction,
        global_scale_sigma=state.runtime_rules.global_scale_sigma,
    )

    m_after = agents[0]["agents"]
    hp_after = [float(m_after[i, INDEX_HP]) for i in range(4)]
    bumped = [
        i for i in range(4)
        if hp_after[i] - hp_before[i] == 250
    ]
    assert len(bumped) == 2, (
        f"exatamente 2 pais deveriam receber +250; "
        f"receberam: indices {bumped}."
    )


def test_parent_bonus_hot_change():
    """Alterar o bonus em runtime muda o beneficio no proximo evento."""
    _prepare_breeding_pair()
    state.update_runtime_rules(mutation_rate=0)
    state.update_runtime_rules(reproduction_parent_hp_bonus=100)

    m = agents[0]["agents"]
    hp_before = [float(m[i, INDEX_HP]) for i in range(4)]
    evolution._reproduce_one_pair(
        agents[0],
        mutation_rate=0,
        mutated_genes=1,
        local_scale_fraction=cfg.MIN_LOCAL_SCALE_FRACTION,
        lineage_index=0,
        crossover_mode=state.runtime_rules.crossover_mode,
        crossover_probability=state.runtime_rules.crossover_probability,
        block_size=state.runtime_rules.block_size,
        mutation_mode=state.runtime_rules.mutation_mode,
        local_scale_sigma=state.runtime_rules.local_scale_sigma,
        global_probability=state.runtime_rules.global_probability,
        global_scale_fraction=state.runtime_rules.global_scale_fraction,
        global_scale_sigma=state.runtime_rules.global_scale_sigma,
    )
    m_after = agents[0]["agents"]
    hp_after = [float(m_after[i, INDEX_HP]) for i in range(4)]
    deltas = [hp_after[i] - hp_before[i] for i in range(4)]
    assert sorted(deltas)[-2:] == [100.0, 100.0], (
        f"bonus runtime=100 deveria aparecer em exatamente dois pais; "
        f"deltas={deltas}."
    )

    # Segundo evento com bonus 700, sem restart.
    state.update_runtime_rules(reproduction_parent_hp_bonus=700)
    hp_before2 = [float(m_after[i, INDEX_HP]) for i in range(4)]
    evolution._reproduce_one_pair(
        agents[0],
        mutation_rate=0,
        mutated_genes=1,
        local_scale_fraction=cfg.MIN_LOCAL_SCALE_FRACTION,
        lineage_index=0,
        crossover_mode=state.runtime_rules.crossover_mode,
        crossover_probability=state.runtime_rules.crossover_probability,
        block_size=state.runtime_rules.block_size,
        mutation_mode=state.runtime_rules.mutation_mode,
        local_scale_sigma=state.runtime_rules.local_scale_sigma,
        global_probability=state.runtime_rules.global_probability,
        global_scale_fraction=state.runtime_rules.global_scale_fraction,
        global_scale_sigma=state.runtime_rules.global_scale_sigma,
    )
    m_after2 = agents[0]["agents"]
    hp_after2 = [float(m_after2[i, INDEX_HP]) for i in range(4)]
    deltas2 = [hp_after2[i] - hp_before2[i] for i in range(4)]
    assert sorted(deltas2)[-2:] == [700.0, 700.0], (
        f"bonus runtime=700 deveria aparecer em exatamente dois pais; "
        f"deltas={deltas2}."
    )


# ---------------------------------------------------------------------------
# Load nao aplica semantica hot
# ---------------------------------------------------------------------------


def test_load_restores_cooldown_without_hot_clamp(tmp_path):
    """Um save com cooldown salvo > interval novo NAO existe, porque
    o loader rejeita. Mas se cooldown == interval salvo, load deve
    preservar exatamente. E se cooldown < interval, tambem.

    Este teste cobre o caso cooldown < interval: load nao deve
    reescrever o cooldown via semantica hot (min), porque nao ha
    mudanca de interval sendo aplicada.
    """
    from primordial_soup import persistence

    state.reset_counters()
    world.seed_lineages()
    for ag in agents:
        ag["pool"] = np.zeros(
            (cfg.INITIAL_POPULATION_PER_LINEAGE, cfg.GENOME_SIZE),
            dtype=np.float32,
        )
    world.place_initially()
    world.fill_fields()

    # Geometry precisa existir explicitamente: o save v21 exige
    # zones e nests validos. Instalacao deterministica, sem RNG.
    _install_checkpoint_geometry()

    state.update_runtime_rules(reproduction_interval=200)
    state.reproduction_cooldown = 42
    state.reproduction_turn = 2

    path = tmp_path / "save.pkl"
    assert persistence.save(str(path)) is True

    # Suja o runtime.
    state.update_runtime_rules(
        reproduction_interval=int(cfg.REPRODUCTION_INTERVAL)
    )
    state.reproduction_cooldown = 999
    state.reproduction_turn = 0

    assert persistence.load(str(path)) is True

    assert state.runtime_rules.reproduction_interval == 200
    assert state.reproduction_cooldown == 42
    assert state.reproduction_turn == 2

# ---------------------------------------------------------------------------
# Newborn nest spawn
# ---------------------------------------------------------------------------


def _fake_crossover_and_mutate(*args, **kwargs):
    """Devolve um filho por lado, sem consumir RNG.

    Usado pelos testes de spawn para isolar a unica fonte de
    aleatoriedade que importa: o sorteio do offset dentro do disco do
    ninho.
    """
    return (
        [np.zeros(cfg.GENOME_SIZE, dtype=np.float32)],
        [np.zeros(cfg.GENOME_SIZE, dtype=np.float32)],
    )


def _expected_spawn_positions(center):
    """Conjunto de posicoes validas de spawn em torno de `center`.

    Derivado da autoridade canonica (nest_geometry), nao duplicado
    manualmente.
    """
    offsets = nest_geometry.nest_disk_offsets(cfg.NEST_SPAWN_RADIUS)
    xs, ys = nest_geometry.wrapped_points(
        center,
        offsets,
        width=layout.LAYOUT.world_width,
        height=layout.LAYOUT.world_height,
    )
    return set(zip(xs.tolist(), ys.tolist()))


def test_newborns_spawn_in_own_nest_disk(monkeypatch):
    """Os filhos nascem no disco de spawn do ninho da propria linhagem.

    R em (50, 50). Todos os filhos devem cair no disco
    NEST_SPAWN_RADIUS em volta do centro, com wrap toroidal.
    """
    _prepare_breeding_pair()
    state.nests = (
        (50, 50),
        (150, 50),
        (250, 50),
    )

    monkeypatch.setattr(
        evolution, "crossover_and_mutate", _fake_crossover_and_mutate
    )
    # Zera a unica fonte de aleatoriedade do spawn: o index do offset.
    monkeypatch.setattr(evolution.np.random, "randint", lambda n: 0)

    children = evolution._reproduce_one_pair(
        agents[0],
        mutation_rate=0,
        mutated_genes=1,
        local_scale_fraction=cfg.MIN_LOCAL_SCALE_FRACTION,
        lineage_index=0,
        crossover_mode=state.runtime_rules.crossover_mode,
        crossover_probability=state.runtime_rules.crossover_probability,
        block_size=state.runtime_rules.block_size,
        mutation_mode=state.runtime_rules.mutation_mode,
        local_scale_sigma=state.runtime_rules.local_scale_sigma,
        global_probability=state.runtime_rules.global_probability,
        global_scale_fraction=state.runtime_rules.global_scale_fraction,
        global_scale_sigma=state.runtime_rules.global_scale_sigma,
    )

    assert len(children) == 2
    valid = _expected_spawn_positions(state.nests[0])
    for child in children:
        x = int(child[INDEX_X])
        y = int(child[INDEX_Y])
        assert (x, y) in valid, (
            f"newborn em ({x}, {y}) fora do disco de spawn da R."
        )


def test_newborns_use_the_given_lineage_nest(monkeypatch):
    """O spawn usa o ninho da linhagem passada, nao outro.

    lineage_index=1 (G). Os filhos devem estar no disco em torno de
    G, nao de R ou B.
    """
    _prepare_breeding_pair(lineage_index=1)
    state.nests = (
        (50, 50),
        (150, 50),
        (250, 50),
    )

    monkeypatch.setattr(
        evolution, "crossover_and_mutate", _fake_crossover_and_mutate
    )
    monkeypatch.setattr(evolution.np.random, "randint", lambda n: 0)

    children = evolution._reproduce_one_pair(
        agents[1],
        mutation_rate=0,
        mutated_genes=1,
        local_scale_fraction=cfg.MIN_LOCAL_SCALE_FRACTION,
        lineage_index=1,
        crossover_mode=state.runtime_rules.crossover_mode,
        crossover_probability=state.runtime_rules.crossover_probability,
        block_size=state.runtime_rules.block_size,
        mutation_mode=state.runtime_rules.mutation_mode,
        local_scale_sigma=state.runtime_rules.local_scale_sigma,
        global_probability=state.runtime_rules.global_probability,
        global_scale_fraction=state.runtime_rules.global_scale_fraction,
        global_scale_sigma=state.runtime_rules.global_scale_sigma,
    )

    assert len(children) == 2
    g_valid = _expected_spawn_positions(state.nests[1])
    r_valid = _expected_spawn_positions(state.nests[0])
    b_valid = _expected_spawn_positions(state.nests[2])

    for child in children:
        x = int(child[INDEX_X])
        y = int(child[INDEX_Y])
        assert (x, y) in g_valid, (
            f"newborn em ({x}, {y}) fora do disco de spawn da G."
        )
        assert (x, y) not in r_valid
        assert (x, y) not in b_valid


def test_sibling_offsets_may_coincide(monkeypatch):
    """Dois filhos no mesmo tick podem ocupar a mesma celula.

    O sorteio de offset e independente por filho; coincidir e
    permitido (fill_fields contabiliza os dois). O teste força o
    mesmo offset para os dois e verifica que ambos caem na mesma
    celula.
    """
    _prepare_breeding_pair()
    state.nests = (
        (50, 50),
        (150, 50),
        (250, 50),
    )

    monkeypatch.setattr(
        evolution, "crossover_and_mutate", _fake_crossover_and_mutate
    )
    monkeypatch.setattr(evolution.np.random, "randint", lambda n: 0)

    children = evolution._reproduce_one_pair(
        agents[0],
        mutation_rate=0,
        mutated_genes=1,
        local_scale_fraction=cfg.MIN_LOCAL_SCALE_FRACTION,
        lineage_index=0,
        crossover_mode=state.runtime_rules.crossover_mode,
        crossover_probability=state.runtime_rules.crossover_probability,
        block_size=state.runtime_rules.block_size,
        mutation_mode=state.runtime_rules.mutation_mode,
        local_scale_sigma=state.runtime_rules.local_scale_sigma,
        global_probability=state.runtime_rules.global_probability,
        global_scale_fraction=state.runtime_rules.global_scale_fraction,
        global_scale_sigma=state.runtime_rules.global_scale_sigma,
    )

    assert len(children) == 2
    assert children[0][INDEX_X] == children[1][INDEX_X]
    assert children[0][INDEX_Y] == children[1][INDEX_Y]


def test_spawn_wraps_across_world_border(monkeypatch):
    """Spawn com offset negativo faz wrap toroidal.

    R em (0, 0), offset (-1, 0) => x = world_width - 1, y = 0. O
    teste descobre o index de (-1, 0) na autoridade canonica em vez de
    hardcodar.
    """
    _prepare_breeding_pair()
    state.nests = (
        (0, 0),
        (150, 50),
        (250, 50),
    )

    spawn_offsets = nest_geometry.nest_disk_offsets(
        cfg.NEST_SPAWN_RADIUS
    )
    target_index = spawn_offsets.index((-1, 0))

    monkeypatch.setattr(
        evolution, "crossover_and_mutate", _fake_crossover_and_mutate
    )
    monkeypatch.setattr(
        evolution.np.random, "randint", lambda n: target_index
    )

    children = evolution._reproduce_one_pair(
        agents[0],
        mutation_rate=0,
        mutated_genes=1,
        local_scale_fraction=cfg.MIN_LOCAL_SCALE_FRACTION,
        lineage_index=0,
        crossover_mode=state.runtime_rules.crossover_mode,
        crossover_probability=state.runtime_rules.crossover_probability,
        block_size=state.runtime_rules.block_size,
        mutation_mode=state.runtime_rules.mutation_mode,
        local_scale_sigma=state.runtime_rules.local_scale_sigma,
        global_probability=state.runtime_rules.global_probability,
        global_scale_fraction=state.runtime_rules.global_scale_fraction,
        global_scale_sigma=state.runtime_rules.global_scale_sigma,
    )

    expected_x = layout.LAYOUT.world_width - 1
    expected_y = 0
    for child in children:
        assert int(child[INDEX_X]) == expected_x
        assert int(child[INDEX_Y]) == expected_y


# ---------------------------------------------------------------------------
# Invariantes estruturais de reproduce_lineage
# ---------------------------------------------------------------------------


def test_reproduce_lineage_index_negative_raises():
    _prepare_breeding_pair()
    with pytest.raises(IndexError):
        evolution.reproduce_lineage(-1)


def test_reproduce_lineage_index_out_of_range_raises():
    _prepare_breeding_pair()
    with pytest.raises(IndexError):
        evolution.reproduce_lineage(cfg.TOTAL_LINEAGES)


def test_reproduce_lineage_missing_nests_raises():
    _prepare_breeding_pair()
    state.nests = None
    with pytest.raises(RuntimeError):
        evolution.reproduce_lineage(0)


def test_reproduce_lineage_invalid_nest_count_raises():
    _prepare_breeding_pair()
    state.nests = ((10, 10),)
    with pytest.raises(RuntimeError):
        evolution.reproduce_lineage(0)


def test_reproduce_lineage_empty_lineage_returns_silently():
    """Linhagem extinta retorna cedo, ANTES de exigir geometry.

    Ordem deliberada: um runtime sem nests nao impede que uma
    linhagem vazia seja processada (nada a fazer).
    """
    _prepare_breeding_pair()
    agents[0]["agents"] = agents[0]["agents"][:0]
    agents[0]["pool"] = agents[0]["pool"][:0]
    agents[0]["ids"] = agents[0]["ids"][:0]
    state.nests = None
    # Nao levanta.
    evolution.reproduce_lineage(0)


# ---------------------------------------------------------------------------
# Propagation into the genetic boundary
# ---------------------------------------------------------------------------


def test_reproduction_propagates_two_scale_runtime_snapshot(monkeypatch):
    """Evolution passes one RuntimeRules snapshot into the genetic boundary."""
    _prepare_breeding_pair()
    state.update_runtime_rules(
        mutation_rate=5,
        mutated_genes=2,
        local_scale_fraction=7,
        local_scale_sigma=0.25,
        global_probability=75,
        global_scale_fraction=40,
        global_scale_sigma=2.0,
    )
    expected_rules = state.runtime_rules
    seen = []

    def fake_reproduce(agent, mutation_rate, mutated_genes, local_scale_fraction, **kwargs):
        seen.append((mutation_rate, mutated_genes, local_scale_fraction, kwargs))
        return []

    monkeypatch.setattr(evolution, "_reproduce_one_pair", fake_reproduce)
    evolution.reproduce_lineage(0)

    assert seen
    mutation_rate, mutated_genes, local_scale_fraction, kwargs = seen[0]
    assert mutation_rate == 5
    assert mutated_genes == 2
    assert local_scale_fraction == 7
    assert kwargs["lineage_index"] == 0
    assert kwargs["local_scale_sigma"] == 0.25
    assert kwargs["global_probability"] == 75
    assert kwargs["global_scale_fraction"] == 40
    assert kwargs["global_scale_sigma"] == 2.0