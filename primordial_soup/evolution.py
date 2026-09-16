# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import math

import numpy as np

from . import config as cfg
from . import layout
from . import nest_geometry
from . import state
from .state import agents
from .genetics import crossover_and_mutate
from .world import (
    INDEX_HP,
    INDEX_X,
    INDEX_Y,
    INDEX_TIME,
    INDEX_GENERATION,
    INDEX_LAST_ACTION,
    INDEX_HIDDEN_STATE_START,
    INDEX_HIDDEN_STATE_END,
    INDEX_CELLS_VISITED,
    INDEX_ENCOUNTERS,
    INDEX_OFFSPRING,
    INDEX_COMPOSITE_SCORE,
    _initial_record,
    allocate_critter_ids,
)

# 1-3: perceber, decidir e mover


def evaluate_and_move(index: int) -> None:
    from .brain import evaluate_batch
    from .senses import sense_batch
    from .movement import move_batch

    agent = agents[index]
    matrix = agent["agents"]
    if matrix.size == 0:
        return

    # Snapshot unico das regras comportamentais deste processamento.
    rules = state.runtime_rules

    n = matrix.shape[0]
    # pool e ndarray [N, GENOME_SIZE]. A truncagem defensiva fica
    # (protege contra chamador que mute pool sem mutar agents em
    # lockstep), agora como slice no primeiro eixo.
    if agent["pool"].shape[0] != n:
        agent["pool"] = agent["pool"][:n]

    xs = matrix[:, INDEX_X].astype(np.int64)
    ys = matrix[:, INDEX_Y].astype(np.int64)

    # Percepcao: visao + estado interno.
    #
    # Passar `index` faz sense_batch escrever no scratch buffer por
    # linhagem em vez de alocar vision + inputs + concatenado todo
    # tick. O array retornado e uma VIEW do buffer; e consumido logo
    # abaixo (evaluate_batch) antes de qualquer outra chamada
    # sobrescrever.
    inputs = sense_batch(
        xs,
        ys,
        matrix,
        index=index,
        low_hp_threshold=rules.low_hp_threshold,
    )  # [N, E]

    # Hidden state do tick anterior.
    previous_hidden_state = matrix[:, INDEX_HIDDEN_STATE_START:INDEX_HIDDEN_STATE_END]

    # pool JA E a matriz de pesos [N, GENOME_SIZE] float32. Sem stack.
    weights = agent["pool"]  # [N, G]

    # Decisao com recorrencia leve.
    outputs, new_hidden_state = evaluate_batch(inputs, weights, previous_hidden_state)

    outputs[:, cfg.STAY_STILL_INDEX] += rules.stay_still_impulse

    choices = np.argmax(outputs, axis=1)

    # Grava o novo hidden state ANTES de mover (o estado pertence ao
    # tick).
    matrix[:, INDEX_HIDDEN_STATE_START:INDEX_HIDDEN_STATE_END] = new_hidden_state

    # Contador de exploracao: incrementado quando o bicho muda de
    # celula. "Ficar parado" nao conta.
    moved = choices != cfg.STAY_STILL_INDEX
    matrix[:, INDEX_CELLS_VISITED] += moved.astype(np.float32)

    move_batch(matrix, choices)

    # Grava a ultima acao para o proximo tick (auto-percepcao).
    matrix[:, INDEX_LAST_ACTION] = choices.astype(np.float32)

    # matrix E agent["agents"] (mesmo objeto, mutado in-place por
    # move_batch e pelos writes de hidden state acima). Sem .tolist().


def _select_parents(agent: dict, count: int) -> np.ndarray:
    """Seleciona `count` indices de pais do pool reprodutivo.

    Elegibilidade: precisa passar nos QUATRO portoes para ser
    candidato:
        INDEX_TIME        >= rules.reproduction_min_age        (velho)
        INDEX_HP          <  rules.reproduction_hp_gate        (ferido)
        INDEX_COMPOSITE_SCORE >= rules.reproduction_min_score (bom)
        INDEX_ENCOUNTERS  >= rules.reproduction_min_encounters (contato)
    Recem-nascidos, juvenis, bichos saudaveis, de score baixo e com
    poucos encontros ficam de fora, nao importa quao bom seja um
    metrica isolada. Os quatro portoes sao aplicados ANTES do
    ranking, entao o ranking so ve bichos que podem reproduzir.

    Os quatro gates, o criterion e a fracao do pool sao lidos de
    state.runtime_rules.

    O score composto e lido de INDEX_COMPOSITE_SCORE. Ele e
    recalculado por apply_ecology_resolution() apos mortes e compactacao,
    antes do scheduler reprodutivo do mesmo tick. INDEX_ENCOUNTERS tambem
    ja contem o resultado ecologico desse tick.

    Modo "longevity": ordena por INDEX_TIME.
    Modo "composite": ordena por score composto.

    O score composto nao e calculado aqui. apply_ecology_resolution()
    o recalcula uma vez por tick e por linhagem depois da compactacao;
    esta funcao apenas consome o valor para ranking.

    HUD: como o score agora e escrito uma vez por tick, o valor lido
    por world.average_composite_score_per_lineage esta sempre atual. O
    aviso de "pode estar um tick atrasado" nao se aplica mais.

    Retorna array possivelmente vazio. Com menos de 2 elegiveis, o
    array tem 0 ou 1 entradas e o chamador (_reproduce_one_pair)
    retorna lista vazia sozinho.
    """
    matrix = agent["agents"]

    # Portoes de elegibilidade. As quatro comparacoes sao
    # vetorizadas; nonzero e O(N). O `&` e AND logico sobre os quatro
    # arrays booleanos, aplicado elemento a elemento ANTES do
    # nonzero, entao os quatro portoes sao avaliados juntos (sem
    # array intermediario de "elegivel por um portao so").
    #
    # Gates, criterion e pool fraction sao runtime.
    rules = state.runtime_rules
    eligible = np.nonzero(
        (matrix[:, INDEX_TIME] >= rules.reproduction_min_age)
        & (matrix[:, INDEX_HP] < rules.reproduction_hp_gate)
        & (matrix[:, INDEX_COMPOSITE_SCORE] >= rules.reproduction_min_score)
        & (matrix[:, INDEX_ENCOUNTERS] >= rules.reproduction_min_encounters)
    )[0]
    if eligible.size < 2:
        return eligible

    # Rank DENTRO do conjunto elegivel. argsort num subset retorna
    # indices LOCAIS em `eligible`; mapeamos de volta com
    # eligible[order].
    if rules.reproduction_criterion == "composite":
        scores = matrix[eligible, INDEX_COMPOSITE_SCORE]
        local_order = np.argsort(-scores)
    else:
        times = matrix[eligible, INDEX_TIME]
        local_order = np.argsort(-times)

    ranked = eligible[local_order]

    pool_size = max(2, int(len(ranked) * rules.reproduction_pool_fraction))
    pool_size = min(pool_size, len(ranked))
    return ranked[:pool_size]


def _reproduce_one_pair(
    agent: dict,
    mutation_rate: int,
    mutated_genes: int,
    local_scale_fraction: int,
    *,
    lineage_index: int,
    crossover_mode: str,
    crossover_probability: float,
    block_size: int,
    mutation_mode: str,
    local_scale_sigma: float,
    global_probability: int,
    global_scale_fraction: int,
    global_scale_sigma: float,
) -> list[np.ndarray]:
    """Sorteia 2 pais do pool reprodutivo e gera
    OFFSPRING_PER_PAIR filhos.

    Geracao do filho: max(parent1_gen, parent2_gen) + 1. Filhos
    nascem com hidden state zerado (sem memoria herdada). Pais tem o
    contador INDEX_OFFSPRING incrementado.

    Os onze parametros geneticos runtime chegam explicitamente e sao
    repassados a crossover_and_mutate. A conversao % -> fracao acontece em
    genetics._mutate_two_scales; aqui o valor e tratado como opaco.

    Retorna a lista de REGISTROS dos filhos (cada um ndarray
    [AGENT_COLUMNS] float32) anexados a linhagem. Retorna lista
    vazia se nenhum par pode ser sorteado.

    O chamador nao usa mais o retorno para atualizar fields
    incrementalmente: o lifecycle reconstroi fields com fill_fields()
    ao final do tick.
    """
    matrix = agent["agents"]
    if matrix.shape[0] < 2:
        return []

    reproductive_pool = _select_parents(agent, matrix.shape[0])
    if len(reproductive_pool) < 2:
        return []

    i1, i2 = np.random.choice(reproductive_pool, size=2, replace=False)
    i1 = int(i1)
    i2 = int(i2)

    parent1_gen = matrix[i1, INDEX_GENERATION]
    parent2_gen = matrix[i2, INDEX_GENERATION]
    offspring_gen = max(float(parent1_gen), float(parent2_gen)) + 1.0

    # Incrementa o contador de filhos dos pais (in-place).
    matrix[i1, INDEX_OFFSPRING] += 1.0
    matrix[i2, INDEX_OFFSPRING] += 1.0

    batch1, batch2 = crossover_and_mutate(
        agent["pool"][i1],
        agent["pool"][i2],
        cfg.OFFSPRING_PER_PAIR,
        mutation_rate,
        mutated_genes,
        local_scale_fraction,
        crossover_mode=crossover_mode,
        crossover_probability=crossover_probability,
        block_size=block_size,
        mutation_mode=mutation_mode,
        local_scale_sigma=local_scale_sigma,
        global_probability=global_probability,
        global_scale_fraction=global_scale_fraction,
        global_scale_sigma=global_scale_sigma,
    )
    if not batch1 or not batch2:
        return []

    # Precondicao do spawn: ninhos inicializados. A validacao
    # estrutural completa (len == TOTAL_LINEAGES) e responsabilidade
    # do chamador reproduce_lineage(); aqui so impedimos dereference
    # de None e documentamos a precondicao da funcao privada.
    nests = state.nests
    if nests is None:
        raise RuntimeError(
            "_reproduce_one_pair requires initialized nests"
        )
    center = nests[lineage_index]

    # Offsets canonicos do disco de spawn, calculados uma vez por par.
    spawn_offsets = nest_geometry.nest_disk_offsets(
        cfg.NEST_SPAWN_RADIUS
    )

    new_records: list[np.ndarray] = []
    new_genomes: list[np.ndarray] = []
    for child in (batch1[0], batch2[0]):
        offset = spawn_offsets[
            int(np.random.randint(len(spawn_offsets)))
        ]
        xs, ys = nest_geometry.wrapped_points(
            center,
            (offset,),
            width=layout.LAYOUT.world_width,
            height=layout.LAYOUT.world_height,
        )
        x = int(xs[0])
        y = int(ys[0])
        record = _initial_record(
            cfg.INITIAL_HP,
            x,
            y,
            int(offspring_gen),
            cfg.STAY_STILL_INDEX,
        )
        new_genomes.append(child)
        new_records.append(record)
        state.births += 1

    # IDs dos recem-nascidos. Alocados a partir do tamanho real da
    # lista (nao da constante OFFSPRING_PER_PAIR) para que a
    # identidade nao dependa de um parametro reprodutivo.
    new_ids = allocate_critter_ids(len(new_records))

    if new_records:
        # Recompensa cada pai uma vez por evento reprodutivo (nao
        # por filho): bonus fixo por ter reproduzido, independente de
        # OFFSPRING_PER_PAIR. Fonte efetiva em state.runtime_rules.
        # Aplicado in-place em `matrix`, entao cai nas linhas dos
        # pais em agent["agents"] antes do concatenate abaixo
        # estender a matriz com os recem-nascidos.
        parent_bonus = state.runtime_rules.reproduction_parent_hp_bonus
        matrix[i1, INDEX_HP] += parent_bonus
        matrix[i2, INDEX_HP] += parent_bonus

        # Anexa os filhos ao pool e a matriz da linhagem em uma
        # alocacao cada. pool e ndarray [N, GENOME_SIZE], entao e um
        # concatenate unico no eixo 0 — nao N appends de arrays
        # pequenos (que forcavam o np.stack do proximo tick a copiar
        # tudo de novo).
        agent["pool"] = np.concatenate(
            [agent["pool"], np.stack(new_genomes, axis=0)], axis=0
        )
        agent["agents"] = np.concatenate(
            [matrix, np.stack(new_records, axis=0)], axis=0
        )
        agent["ids"] = np.concatenate(
            [agent["ids"], new_ids], axis=0
        )

    return new_records


# --- Reproducao -----------------------------------------------------------

def reproduce_lineage(index: int) -> int:
    """Executa o bloco reprodutivo para a linhagem dona do turno.

    Le state.runtime_rules uma vez. Nao aplica ecologia. Nao toca em
    fields. Newborns sao apenas anexados a matriz/pool/ids; o
    fill_fields() final do tick os torna visiveis espacialmente.

    Chamado depois de apply_ecology_resolution(); ver
    simulation.step().

    Returns:
        Quantidade de descendentes efetivamente anexados a linhagem
        nesta chamada. Zero cobre linhagem extinta, nenhum pai
        elegivel, todos os attempts esgotados e ausencia de pool
        reproduzivel. Nao emite feedback, nao conhece UI, nao
        desenha; a observacao e apenas local ao bloco reprodutivo.
    """
    if not (0 <= index < cfg.TOTAL_LINEAGES):
        raise IndexError(
            f"reproduce_lineage: index {index} fora do intervalo "
            f"[0, {cfg.TOTAL_LINEAGES})."
        )

    agent = agents[index]
    matrix = agent["agents"]
    if matrix.shape[0] == 0:
        # Linhagem extinta: nada a reproduzir, nao exige geometria.
        return 0

    nests = state.nests
    if nests is None:
        raise RuntimeError(
            "reproduce_lineage requires initialized nests "
            "(state.nests is None)."
        )
    if len(nests) != cfg.TOTAL_LINEAGES:
        raise RuntimeError(
            f"reproduce_lineage: state.nests tem {len(nests)} "
            f"centros; esperado {cfg.TOTAL_LINEAGES}."
        )

    rules = state.runtime_rules
    newborn_count = 0

    attempts = max(
        1,
        math.ceil(
            matrix.shape[0] / rules.reproduction_attempts_divisor
        ),
    )
    for _ in range(attempts):
        if (
            agent["agents"].shape[0]
            > cfg.MAX_POPULATION_PER_LINEAGE - cfg.OFFSPRING_PER_PAIR
        ):
            break
        children = _reproduce_one_pair(
            agent,
            rules.mutation_rate,
            rules.mutated_genes,
            rules.local_scale_fraction,
            lineage_index=index,
            crossover_mode=rules.crossover_mode,
            crossover_probability=rules.crossover_probability,
            block_size=rules.block_size,
            mutation_mode=rules.mutation_mode,
            local_scale_sigma=rules.local_scale_sigma,
            global_probability=rules.global_probability,
            global_scale_fraction=rules.global_scale_fraction,
            global_scale_sigma=rules.global_scale_sigma,
        )
        if not children:
            break
        newborn_count += len(children)

    return newborn_count
