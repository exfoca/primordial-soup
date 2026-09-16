"""Teste comportamental do bonus de HP por evento reprodutivo.

Protege a semantica do contrato, nao o valor numerico:

    cada pai beneficiado recebe exatamente
    +cfg.REPRODUCTION_PARENT_HP_BONUS por evento reprodutivo,
    independente de quantos filhos o evento gerou.

O bug que este teste protege e do tipo "o bonus virou por filho em
vez de por evento": com OFFSPRING_PER_PAIR=2, isso dobraria o
beneficio e mudaria silenciosamente a pressao evolutiva.

Nao testamos cfg.REPRODUCTION_PARENT_HP_BONUS == 50: fixar o valor
em teste congelaria tuning evolutivo. O contrato e "o bonus configurado
e aplicado uma vez por evento", nao "o bonus e 50".

Todos os docstrings e comentarios deste arquivo sao intencionalmente
ASCII puro, seguindo o estilo de nomenclatura interna do projeto.
"""

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import evolution
from primordial_soup import state
from primordial_soup import world
from primordial_soup.state import agents
from primordial_soup.world import (
    INDEX_HP,
    INDEX_TIME,
    INDEX_ENCOUNTERS,
    INDEX_COMPOSITE_SCORE,
)


def _valid_test_nests():
    """Geometria deterministica de ninhos valida para fixtures de
    checkpoint.

    Tres centros colineares, separados por 2*radius+1, de modo que os
    discos de radius NEST_RADIUS nao compartilhem celulas. Mesmo
    helper dos demais arquivos de teste de persistencia/spawn.
    """
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


@pytest.fixture
def breeding_pair():
    """Monta um cenario onde _reproduce_one_pair vai sortear pais
    elegiveis e reproduzir.

    Simplificacao: em vez de rodar N ticks ate a reproducao acontecer
    naturalmente, forcamos manualmente o estado dos agentes para
    satisfazer os quatro portoes e chamamos _reproduce_one_pair
    direto. Isso isola o bonus de HP do resto do ciclo de vida.
    """
    state.reset_counters()
    world.seed_lineages()

    # Populacao minima: 4 agentes em R, pools validos, ids alocados.
    n = 4
    for ag in agents:
        ag["pool"] = np.random.uniform(
            cfg.MIN_GENE_VALUE, cfg.MAX_GENE_VALUE,
            (n, cfg.GENOME_SIZE),
        ).astype(np.float32)
    world.place_initially()

    # Ajusta o estado dos dois primeiros agentes de R para passarem
    # nos quatro portoes reprodutivos.
    matrix = agents[0]["agents"]
    for i in (0, 1):
        matrix[i, INDEX_TIME] = cfg.REPRODUCTION_MIN_AGE + 100
        matrix[i, INDEX_HP] = cfg.REPRODUCTION_HP_GATE - 1000
        matrix[i, INDEX_ENCOUNTERS] = cfg.REPRODUCTION_MIN_ENCOUNTERS + 10
        matrix[i, INDEX_COMPOSITE_SCORE] = cfg.REPRODUCTION_MIN_SCORE + 0.5

    # Estado do scheduler reprodutivo nao importa aqui; chamamos
    # _reproduce_one_pair direto. Mas garantimos que ele nao vai
    # interferir via state.
    state.mutation_rate = 0  # sem mutacao: previsivel

    # _reproduce_one_pair exige state.nests inicializado (spawn dos
    # filhos). Instalamos um conjunto deterministico, sem consumir RNG.
    state.nests = _valid_test_nests()

    yield

    state.reset_counters()
    agents.clear()


def test_each_parent_receives_bonus_once_per_event(breeding_pair):
    """Com OFFSPRING_PER_PAIR=2, cada pai recebe o bonus UMA vez.

    Antes do Patch 5, o nome HP_BONUS_PER_OFFSPRING sugeria
    multiplicacao por filho. O teste fixa que o comportamento
    efetivo e por evento.
    """
    matrix = agents[0]["agents"]
    hp_before = [float(matrix[i, INDEX_HP]) for i in range(4)]

    children = evolution._reproduce_one_pair(
        agents[0],
        mutation_rate=0,
        mutated_genes=1,
        local_scale_fraction=cfg.MIN_LOCAL_SCALE_FRACTION,
        lineage_index=0,
        crossover_mode=cfg.CROSSOVER_MODE,
        crossover_probability=float(cfg.CROSSOVER_PROBABILITY),
        block_size=int(cfg.BLOCK_SIZE),
        mutation_mode=cfg.MUTATION_MODE,
        local_scale_sigma=float(cfg.LOCAL_SCALE_SIGMA),
        global_probability=int(cfg.GLOBAL_PROBABILITY * 100),
        global_scale_fraction=int(cfg.GLOBAL_SCALE_FRACTION * 100),
        global_scale_sigma=float(cfg.GLOBAL_SCALE_SIGMA),
    )

    # O evento deve ter produzido OFFSPRING_PER_PAIR filhos.
    assert len(children) == cfg.OFFSPRING_PER_PAIR, (
        f"esperado {cfg.OFFSPRING_PER_PAIR} filhos, "
        f"obtido {len(children)}."
    )

    # Os pais escolhidos sao dois dos quatro agentes de R. Nao
    # sabemos QUAIS dois foram sorteados, mas sabemos que exatamente
    # dois receberam o bonus. Contamos quantos subiram exatamente o
    # valor configurado.
    matrix_after = agents[0]["agents"]
    delta_positive = matrix_after[:, INDEX_HP] - np.array(
        [float(m) for m in matrix[:, INDEX_HP]]
    ) if matrix_after.shape[0] == matrix.shape[0] else None

    # Como os filhos foram anexados, o shape mudou. Em vez de comparar
    # linhas, olhamos so os INDICES que existiam antes e comparamos.
    # Os dois pais (por construcao, entre indices 0..3) sao os unicos
    # que sofreram +bonus entre os agentes antigos. Os nao-pais
    # permanecem com HP intacto.
    hp_after = [float(matrix_after[i, INDEX_HP]) for i in range(4)]
    bumped = [
        i for i in range(4)
        if hp_after[i] - hp_before[i] == cfg.REPRODUCTION_PARENT_HP_BONUS
    ]
    unchanged = [
        i for i in range(4)
        if hp_after[i] == hp_before[i]
    ]

    assert len(bumped) == 2, (
        f"exatamente 2 pais deveriam receber "
        f"+{cfg.REPRODUCTION_PARENT_HP_BONUS} HP; "
        f"receberam: indices {bumped}."
    )
    assert len(unchanged) == 2, (
        f"os 2 nao-pais deveriam manter HP intacto; "
        f"intactos: indices {unchanged}."
    )

    # Verificacao crucial: NENHUM pai recebeu 2x o bonus. Se a
    # implementacao tivesse virado "por filho", o delta seria
    # 2 * BONUS, nao BONUS.
    for i in bumped:
        delta = hp_after[i] - hp_before[i]
        assert delta == cfg.REPRODUCTION_PARENT_HP_BONUS, (
            f"pai {i} recebeu {delta}, esperado "
            f"{cfg.REPRODUCTION_PARENT_HP_BONUS}. "
            f"Bonus por filho em vez de por evento?"
        )


def test_bonus_constant_does_not_leak_local(breeding_pair):
    """Nao deve mais existir HP_BONUS_PER_OFFSPRING em evolution.py.

    Protege a fonte unica de verdade: se alguem reintroduzir a
    constante local, o teste denuncia.
    """
    assert not hasattr(evolution, "HP_BONUS_PER_OFFSPRING"), (
        "evolution.py nao deve ter constante local de bonus; "
        "use cfg.REPRODUCTION_PARENT_HP_BONUS."
    )
    assert hasattr(cfg, "REPRODUCTION_PARENT_HP_BONUS"), (
        "config.py deve expor REPRODUCTION_PARENT_HP_BONUS."
    )
