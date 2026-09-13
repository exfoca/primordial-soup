# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import numpy as np

from . import config as cfg


def random_genome() -> np.ndarray:
    return np.random.uniform(
        cfg.MIN_GENE_VALUE, cfg.MAX_GENE_VALUE, cfg.GENOME_SIZE
    ).astype(np.float32)


def random_population(count: int) -> np.ndarray:
    """Retorna uma matriz [count, GENOME_SIZE] float32 de genomas
    aleatorios.

    Alocacao unica para a populacao inteira: com count=200 e
    GENOME_SIZE=10.245, evita 200 alocacoes pequenas e permite que
    state.agents guarde o pool como matriz unica (ver
    world.seed_lineages), eliminando o np.stack que
    evolution.evaluate_and_move rodava por tick.

    random_genome() fica para chamadores que precisam de um genoma 1-D.
    """
    return np.random.uniform(
        cfg.MIN_GENE_VALUE, cfg.MAX_GENE_VALUE, (count, cfg.GENOME_SIZE)
    ).astype(np.float32)


def _uniform_mask(n: int, g: int) -> np.ndarray:
    """[n, g] boolean. True = pega do pai A; False = pega do pai B."""
    return np.random.rand(n, g) < cfg.CROSSOVER_PROBABILITY


def _blocks_mask(n: int, g: int) -> np.ndarray:
    """[n, g] boolean. Blocos contiguos de BLOCK_SIZE alternam pai
    A / pai B.
    """
    g = int(g)
    block = max(1, int(cfg.BLOCK_SIZE))
    n_blocks = (g + block - 1) // block

    bits = np.random.randint(0, 2, size=(n, n_blocks), dtype=np.int8)
    expanded = np.repeat(bits[:, :, None], block, axis=2)
    mask = expanded.reshape(n, n_blocks * block)[:, :g]

    return mask == 0


def _two_points_mask(n: int, g: int) -> np.ndarray:
    """[n, g] boolean. 2 cortes aleatorios; troca o segmento do meio.

    O loop por linha e intencional: os dois cortes sao dependentes
    (c2 > c1), entao uma versao totalmente vetorizada exigiria
    rejection sampling ou um truque de soma cumulativa mais dificil
    de ler do que o loop. `n` e `offspring_count` (~2 por chamada),
    entao nao e gargalo.
    """
    g = int(g)
    if g < 2:
        return np.ones((n, g), dtype=bool)

    c1 = np.random.randint(0, g - 1, size=n)
    c2 = np.empty(n, dtype=np.int64)
    for i in range(n):
        c2[i] = np.random.randint(c1[i] + 1, g + 1)

    cols = np.arange(g)[None, :]
    return (cols >= c1[:, None]) & (cols < c2[:, None])


_MASKS = {
    "uniform": _uniform_mask,
    "blocks": _blocks_mask,
    "two_points": _two_points_mask,
}


def _build_mask(n: int, g: int) -> np.ndarray:
    try:
        generator = _MASKS[cfg.CROSSOVER_MODE]
    except KeyError:
        raise ValueError(
            f"Unknown CROSSOVER_MODE: {cfg.CROSSOVER_MODE!r}. Options: {sorted(_MASKS)}"
        )
    return generator(n, g)


def crossover_and_mutate(
    parent1: np.ndarray,
    parent2: np.ndarray,
    offspring_count: int,
    mutation_rate: int,
    mutated_genes: int,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Gera duas ninhadas complementares de filhos a partir de dois
    pais.

    O algoritmo de crossover e escolhido por cfg.CROSSOVER_MODE; o de
    mutacao por cfg.MUTATION_MODE.

    `mutation_rate` e a probabilidade (em %) de cada filho sofrer
    mutacao. `mutated_genes` so e usado no modo "surgical".

    Os dois pais sao arrays 1-D de shape [GENOME_SIZE]. As ninhadas
    complementares sao construidas com broadcast e mascara:

        offspring1 = where(mask, parent1_broadcast, parent2_broadcast)
        offspring2 = where(mask, parent2_broadcast, parent1_broadcast)

    entao cada filho da ninhada 1 tem a selecao complementar do filho
    de mesmo indice na ninhada 2.

    NOTE: a funcao antes recebia uma lista `pool` e rodava
    np.stack(pool, axis=0). Esse stack sumiu: o chamador passa duas
    views da matriz pool da linhagem direto, eliminando uma copia de
    dois genomas por par.
    """
    if offspring_count <= 0:
        return [], []

    parent1 = np.asarray(parent1)
    parent2 = np.asarray(parent2)

    if parent1.ndim != 1 or parent2.ndim != 1:
        raise ValueError(
            "crossover_and_mutate expects two 1-D genomes; got "
            f"parent1.ndim={parent1.ndim}, parent2.ndim={parent2.ndim}."
        )
    if parent1.shape[0] != cfg.GENOME_SIZE or parent2.shape[0] != cfg.GENOME_SIZE:
        raise ValueError(
            "crossover_and_mutate expects both parents to have "
            f"GENOME_SIZE={cfg.GENOME_SIZE} genes; got "
            f"{parent1.shape[0]} and {parent2.shape[0]}."
        )

    # Constroi as duas matrizes de pais por broadcast. broadcast_to
    # retorna uma view read-only com stride 0 no eixo 0; np.where le
    # sem materializar copia, entao as unicas alocacoes abaixo sao as
    # duas matrizes de filhos.
    parents1 = np.broadcast_to(parent1, (offspring_count, cfg.GENOME_SIZE))
    parents2 = np.broadcast_to(parent2, (offspring_count, cfg.GENOME_SIZE))

    masks = _build_mask(offspring_count, cfg.GENOME_SIZE)

    offspring1 = np.where(masks, parents1, parents2).astype(np.float32)
    offspring2 = np.where(masks, parents2, parents1).astype(np.float32)

    probability = mutation_rate / 100.0
    for brood in (offspring1, offspring2):
        _mutate_batch(brood, probability, mutated_genes)

    return list(offspring1), list(offspring2)


def _mutate_batch(brood: np.ndarray, probability: float, mutated_genes: int) -> None:
    """Mutacao vetorizada in-place. brood tem shape [N, G].

    Despacha para o modo configurado em cfg.MUTATION_MODE.
    """
    if brood.size == 0 or probability <= 0.0:
        return

    if cfg.MUTATION_MODE == "surgical":
        _mutate_surgical(brood, probability, mutated_genes)
    elif cfg.MUTATION_MODE == "two_scales":
        _mutate_two_scales(brood, probability)
    else:
        raise ValueError(
            f"Unknown MUTATION_MODE: {cfg.MUTATION_MODE!r}. "
            f"Options: 'surgical', 'two_scales'."
        )


# Modo legado: mutacao cirurgica


def _mutate_surgical(brood: np.ndarray, probability: float, mutated_genes: int) -> None:
    """Muta exatamente `mutated_genes` genes por filho mutante, com
    valores uniformes em [MIN_GENE_VALUE, MAX_GENE_VALUE]. In-place.
    """
    n, g = brood.shape
    if n == 0 or mutated_genes <= 0:
        return

    mutants = np.random.rand(n) < probability
    if not mutants.any():
        return

    idx_mut = np.nonzero(mutants)[0]
    m = idx_mut.size

    gene_indices = np.random.randint(0, g, size=(m, mutated_genes))
    new_values = np.random.uniform(
        cfg.MIN_GENE_VALUE, cfg.MAX_GENE_VALUE, size=(m, mutated_genes)
    ).astype(np.float32)

    rows = np.repeat(idx_mut, mutated_genes)
    brood[rows, gene_indices.ravel()] = new_values.ravel()


# Modo two_scales: local refina, global explora


def _mutate_two_scales(brood: np.ndarray, probability: float) -> None:
    """Mutacao em duas escalas, in-place.

    Para cada filho mutante:
      1. Decide escala global vs local via GLOBAL_PROBABILITY.
      2. Sorteia uma fracao de genes (global ou local).
      3. Soma ruido gaussiano.

    A fracao afetada e relativa a G = GENOME_SIZE. Sorteio sem
    reposicao, entao a fracao efetiva e exatamente a configurada
    (arredondada para o numero inteiro de genes mais proximo).

    Note: ruido gaussiano puro pode exceder o range. Aplicamos clamp
    explicito em [MIN_GENE_VALUE, MAX_GENE_VALUE] em vez de rejeitar
    e reamostrar (mais caro e enviesaria a distribuicao).
    """
    n, g = brood.shape
    if n == 0:
        return

    mutants = np.random.rand(n) < probability
    if not mutants.any():
        return

    idx_mut = np.nonzero(mutants)[0]

    # Decide, para cada mutante, se a mutacao e global (True) ou
    # local (False).
    global_mutations = np.random.rand(idx_mut.size) < cfg.GLOBAL_PROBABILITY

    # Processa em dois lotes: um global, um local.
    _apply_noise(
        brood,
        idx_mut[global_mutations],
        cfg.GLOBAL_SCALE_FRACTION,
        cfg.GLOBAL_SCALE_SIGMA,
    )
    _apply_noise(
        brood,
        idx_mut[~global_mutations],
        cfg.LOCAL_SCALE_FRACTION,
        cfg.LOCAL_SCALE_SIGMA,
    )


def _apply_noise(
    brood: np.ndarray, idx_mut: np.ndarray, fraction: float, sigma: float
) -> None:
    """Aplica ruido gaussiano em `idx_mut`, in-place.

    `fraction` em (0, 1] e a fracao de genes afetados por mutante.
    Sorteio SEM REPOSICAO: nenhum gene e tocado duas vezes dentro do
    mesmo mutante.

    Implementacao: para cada linha mutante, geramos G valores
    uniformes i.i.d. e tomamos os n_genes MENORES via np.argpartition.
    Os indices dos menores sao uma amostra uniforme sem reposicao de
    tamanho n_genes sobre os G genes. Totalmente vetorizado, O(m·G)
    em C — sem loop Python sobre mutantes.

    (Alternativa equivalente: np.random.choice(replace=False) por
    linha, que era a implementacao anterior. Correta, mas mais lenta
    para m ~ 200.)
    """
    m = idx_mut.size
    if m == 0:
        return

    total_genes = brood.shape[1]
    n_genes = max(1, int(round(total_genes * fraction)))
    n_genes = min(n_genes, total_genes)  # safety

    if n_genes == total_genes:
        # Caso degenerado: muta todos os genes. Sem sorteio.
        rows = np.repeat(idx_mut, total_genes)
        cols = np.tile(np.arange(total_genes, dtype=np.int64), m)
    else:
        # Escores i.i.d. uniformes; os n_genes menores por linha
        # identificam as colunas amostradas. argpartition e O(G) por
        # linha, nao O(G log G).
        scores = np.random.rand(m, total_genes)
        # kth = n_genes - 1 poe os n_genes menores nas primeiras
        # n_genes posicoes (nao ordenadas dentro da particao, o que
        # e indiferente).
        sampled = np.argpartition(scores, n_genes - 1, axis=1)[:, :n_genes]

        rows = np.repeat(idx_mut, n_genes)
        cols = sampled.ravel()

    noise = np.random.normal(0.0, sigma, size=rows.size).astype(np.float32)

    values = brood[rows, cols] + noise
    np.clip(values, cfg.MIN_GENE_VALUE, cfg.MAX_GENE_VALUE, out=values)
    brood[rows, cols] = values
