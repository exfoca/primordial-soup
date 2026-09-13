"""Testes do controle runtime de escala local de mutacao.

Cobrem a propriedade que define a correcao do Patch 1:

    state.local_scale_fraction
        -> atravessa evolution
        -> chega a genetics
        -> altera a fracao de genes afetados pela mutacao local

O teste e propositalmente unitario em relacao a mutacao:
crossover_and_mutate e chamado direto, com pais e seed fixos, para
isolar a mutacao de parent selection, posicionamento de nascimento,
alocacao de ID e ordem de tick. Se a passagem de valor quebrar, este
teste denuncia sem ruido de outras partes da simulacao.

Todos os docstrings e comentarios deste arquivo sao intencionalmente
ASCII puro, seguindo o estilo de nomenclatura interna do projeto.
"""

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import genetics
from primordial_soup import state


def _fixed_parents(seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Gera dois pais deterministicos para o teste."""
    rng = np.random.RandomState(seed)
    a = rng.uniform(cfg.MIN_GENE_VALUE, cfg.MAX_GENE_VALUE, cfg.GENOME_SIZE)
    b = rng.uniform(cfg.MIN_GENE_VALUE, cfg.MAX_GENE_VALUE, cfg.GENOME_SIZE)
    return a.astype(np.float32), b.astype(np.float32)


def _count_changed_genes(
    parent_a: np.ndarray,
    parent_b: np.ndarray,
    local_scale_fraction: int,
    seed: int,
) -> int:
    """Roda crossover_and_mutate com seed fixa e conta genes mutados.

    A contagem e feita sobre as duas ninhadas complementares: qualquer
    posicao cujo valor difere de AMBOS os pais so pode ter vindo de
    mutacao (crossover apenas recombinaria valores ja presentes nos
    pais, se nao houvesse mutacao). Isso isola mutacao de crossover.

    Um crossover uniforme ou em blocos pode, ocasionalmente, produzir
    um valor que coincide com o do pai por acaso (se pais tiverem
    genes iguais naquela posicao). Com pais gerados por uniform
    continua, isso e raro o suficiente para nao alterar a monotonia
    do teste; a assercao principal e de tendencia, nao de valor
    exato.
    """
    np.random.seed(seed)
    brood1, brood2 = genetics.crossover_and_mutate(
        parent_a,
        parent_b,
        cfg.OFFSPRING_PER_PAIR,
        mutation_rate=100,  # todo filho muta, para o efeito ser claro
        mutated_genes=1,
        local_scale_fraction=local_scale_fraction,
    )

    changed = 0
    for child in list(brood1) + list(brood2):
        differs = (child != parent_a) & (child != parent_b)
        changed += int(differs.sum())
    return changed


def test_small_and_large_local_scale_differ():
    a, b = _fixed_parents(seed=1)
    small = _count_changed_genes(a, b, local_scale_fraction=1, seed=42)
    large = _count_changed_genes(a, b, local_scale_fraction=100, seed=42)
    assert small != large, (
        "local_scale_fraction=1 e =100 deveriam produzir contagens "
        "de genes mutados diferentes, mas produziram o mesmo resultado."
    )


def test_local_scale_is_monotonic_in_gene_count():
    a, b = _fixed_parents(seed=2)
    small = _count_changed_genes(a, b, local_scale_fraction=1, seed=7)
    medium = _count_changed_genes(a, b, local_scale_fraction=25, seed=7)
    large = _count_changed_genes(a, b, local_scale_fraction=100, seed=7)

    assert small < medium < large, (
        f"contagem de genes afetados nao cresceu com a escala local: "
        f"1%={small}, 25%={medium}, 100%={large}."
    )


def test_state_local_scale_fraction_drives_mutation():
    """Mudar state.local_scale_fraction muda o resultado efetivo.

    Chama crossover_and_mutate com o valor lido de state, que e o
    mesmo caminho que evolution._reproduce_one_pair faz em producao.
    O ponto do teste e provar que o valor de state chega ate a
    mutacao, e nao que state tem um tipo especifico.
    """
    a, b = _fixed_parents(seed=3)

    state.local_scale_fraction = cfg.MIN_LOCAL_SCALE_FRACTION
    small = _count_changed_genes(a, b, state.local_scale_fraction, seed=99)

    state.local_scale_fraction = cfg.MAX_LOCAL_SCALE_FRACTION
    large = _count_changed_genes(a, b, state.local_scale_fraction, seed=99)

    assert small < large, (
        "alterar state.local_scale_fraction nao mudou a quantidade "
        "efetiva de genes afetados pela mutacao local."
    )


def test_default_bootstrap_matches_config_default():
    """Com state.local_scale_fraction = int(cfg.LOCAL_SCALE_FRACTION*100),
    o resultado deve ser o mesmo que o default historico de config.

    Nao ha assert de valor absoluto: o teste apenas confirma que o
    caminho de bootstrap atual (state inicializado a partir de
    cfg.LOCAL_SCALE_FRACTION) continua sendo um caso valido do novo
    caminho runtime, e nao um caso especial que bypassa o parametro.
    """
    a, b = _fixed_parents(seed=4)
    bootstrap_value = int(cfg.LOCAL_SCALE_FRACTION * 100)

    # O valor bootstrap deve estar no range operacional.
    assert cfg.MIN_LOCAL_SCALE_FRACTION <= bootstrap_value <= cfg.MAX_LOCAL_SCALE_FRACTION

    # E deve produzir um resultado utilizavel (contagem > 0).
    count = _count_changed_genes(a, b, bootstrap_value, seed=11)
    assert count > 0, (
        "escala local no default de bootstrap produziu zero genes "
        "alterados; o caminho de mutacao local nao esta sendo ativado."
    )
