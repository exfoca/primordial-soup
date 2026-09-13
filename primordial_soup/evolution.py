# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import math

import numpy as np

from . import config as cfg
from . import layout
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
    fill_fields_incremental,
)

# HP concedido a cada pai por evento reprodutivo (nao por filho).
# Bonus fixo a nivel de evento: o pai que reproduz com sucesso ganha
# o mesmo bonus seja OFFSPRING_PER_PAIR 1 ou 10. 50 e 0.5% de
# INITIAL_HP (10.000): contrapeso que faz da reproducao uma
# estrategia de sobrevivencia ativa sem tornar pais ferteis quase
# imortais. Vive aqui (nao em config.py) por escolha deliberada: e um
# knob local da logica de reproducao, nao uma lei do universo.
HP_BONUS_PER_OFFSPRING = 50


def _neighbors(index: int):
    """Retorna (aliado, inimigo) conforme o ciclo R->B->G->R."""
    enemy = agents[(index + cfg.TOTAL_LINEAGES - 1) % cfg.TOTAL_LINEAGES]
    ally = agents[(index + 1) % cfg.TOTAL_LINEAGES]
    return ally, enemy


# 1-3: perceber, decidir e mover


def evaluate_and_move(index: int) -> None:
    from .brain import evaluate_batch
    from .senses import sense_batch
    from .movement import move_batch

    agent = agents[index]
    matrix = agent["agents"]
    if matrix.size == 0:
        return

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
    inputs = sense_batch(xs, ys, matrix, index=index)  # [N, E]

    # Hidden state do tick anterior.
    previous_hidden_state = matrix[:, INDEX_HIDDEN_STATE_START:INDEX_HIDDEN_STATE_END]

    # pool JA E a matriz de pesos [N, GENOME_SIZE] float32. Sem stack.
    weights = agent["pool"]  # [N, G]

    # Decisao com recorrencia leve.
    outputs, new_hidden_state = evaluate_batch(inputs, weights, previous_hidden_state)

    outputs[:, cfg.STAY_STILL_INDEX] += cfg.STAY_STILL_IMPULSE

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


# 5-6: punir, recompensar, matar, reproduzir


def _compute_composite_score(matrix: np.ndarray) -> np.ndarray:
    """Calcula o score composto [N] a partir da matriz de agentes.

    Normaliza cada componente pelo maximo da propria linhagem (piso 1
    para evitar divisao por zero). Isso garante que linhagens pequenas
    ainda tenham selecao significativa.

    Formula:
        score = W_LONG * (time / max_time)
              + W_EXPL * (cells / max_cells)
              + W_INT  * (encounters / max_encounters)
              + W_REP  * (offspring / max_offspring)
    """
    time = matrix[:, INDEX_TIME]
    cells = matrix[:, INDEX_CELLS_VISITED]
    encounters = matrix[:, INDEX_ENCOUNTERS]
    offspring = matrix[:, INDEX_OFFSPRING]

    max_time = max(float(time.max()), 1.0)
    max_cells = max(float(cells.max()), 1.0)
    max_encounters = max(float(encounters.max()), 1.0)
    max_offspring = max(float(offspring.max()), 1.0)

    score = (
        cfg.LONGEVITY_WEIGHT * (time / max_time)
        + cfg.EXPLORATION_WEIGHT * (cells / max_cells)
        + cfg.INTERACTION_WEIGHT * (encounters / max_encounters)
        + cfg.REPRODUCTION_WEIGHT * (offspring / max_offspring)
    )
    return score.astype(np.float32)


def _zone_effect(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Retorna [N] float32 com state.zone_hp_effect para quem esta
    dentro de zona, 0 fora.

    Retorna zeros se nao houver zonas (NUMBER_OF_ZONES <= 0), se
    state.zone_hp_effect for 0, ou se o toggle state.zones_active for
    False. O toggle suprime o efeito sem tocar na mascara, entao
    reativar restaura imediatamente.

    O valor e lido de state (nao de config) para o ajuste em runtime
    fazer efeito no proximo tick.
    """
    effect = state.zone_hp_effect
    if state.zones is None or effect == 0 or not state.zones_active:
        return np.zeros(xs.shape[0], dtype=np.float32)
    inside = state.zones[xs, ys]
    return np.where(inside, float(effect), 0.0).astype(np.float32)


def _capture_death_snapshot_if_needed(
    lineage_index: int,
    agent: dict,
    alive: np.ndarray,
    matrix: np.ndarray,
) -> None:
    """Captura o estado final do bicho observado, se ele morreu neste
    tick.

    Chamada de punish_reward_and_reproduce, entre o calculo de
    `alive` e a compactacao de ids/pool/agents, para a linha ainda
    estar presente ao copiar.

    Barata para linhagens nao-donas: uma busca vetorizada sobre os
    ids int64. Trabalho pesado (dois .copy()) so na linhagem que
    possui state.inspected_critter_id.

    Invariante: se o snapshot for criado, snapshot.critter_id ==
    state.inspected_critter_id e o bicho estava vivo ANTES deste
    tick e NAO esta em `alive`.
    """
    from . import state

    observed_id = state.inspected_critter_id
    if observed_id is None:
        return

    matches = np.flatnonzero(agent["ids"] == observed_id)
    if matches.size == 0:
        return

    ai = int(matches[0])
    if ai in alive:
        return  # observado sobreviveu; nada a capturar

    state.inspection_death_snapshot = state.InspectionDeathSnapshot(
        critter_id=int(observed_id),
        lineage_index=lineage_index,
        lineage_id=str(agent["id"]),
        tick=int(state.tick_count),
        agent=matrix[ai].copy(),
        genome=agent["pool"][ai].copy(),
    )


def punish_reward_and_reproduce(
    index: int, mutation_rate: int, mutated_genes: int, reproduce: bool
) -> None:
    """Pune, recompensa, mata e (opcionalmente) reproduz uma linhagem.

    `reproduce` e o flag de turno: True so para a linhagem dona do
    turno, conforme a rotacao global orquestrada por simulation.step.
    Com False, a funcao ainda aplica toda punicao/recompensa/morte,
    mas pula o bloco de reproducao inteiro. O score composto ainda e
    calculado (alimenta o HUD e a proxima selecao de pais); so as
    tentativas de reproducao sao gated.
    """
    agent = agents[index]
    matrix = agent["agents"]
    if matrix.size == 0:
        return

    ally, enemy = _neighbors(index)

    xs = matrix[:, INDEX_X].astype(np.int64)
    ys = matrix[:, INDEX_Y].astype(np.int64)

    own_field = agent["field"][xs, ys]
    enemy_field = enemy["field"][xs, ys]
    ally_field = ally["field"][xs, ys]

    # Interacao: conta qualquer celula com presenca de outra linhagem
    # (aliada ou inimiga). Alimenta o score composto.
    interacted = (enemy_field > 0) | (ally_field > 0)
    matrix[:, INDEX_ENCOUNTERS] += interacted.astype(np.float32)

    # Tres pressoes independentes, somadas algebricamente:
    #
    #   inimigo    -> dano; reduzido pela metade se houver aliado
    #                 presente (o aliado absorve parte do conflito).
    #   sobrecarga (contagem da propria linhagem > 1) -> dano;
    #                 fenomeno separado do contato inimigo, nunca
    #                 contado em dobro.
    #   aliado     -> bonus; aplica mesmo com inimigo presente (e o
    #                 bonus que torna visivel a meiacao do dano).
    #
    # Exemplos de resultado liquido:
    #   sozinho                   -> -1
    #   1 aliado                  -> +99
    #   1 inimigo                 -> -101
    #   1 inimigo + 1 aliado      -> +49   (aliado vence a celula)
    #   2+ proprios, sem a/i      -> -101
    #   2+ proprios + 1 aliado    -> -1    (aliado compensa a sobrecarga)
    #   2+ proprios + 1 inimigo   -> -201
    #   2+ proprios + 1 i + 1 a   -> -101  (inimigo atenuado + sobrecarga)
    enemy_present = enemy_field > 0
    ally_present = ally_field > 0
    overcrowded = own_field > 1

    # Dano do inimigo: cheio, ou metade com aliado presente.
    enemy_damage = np.where(
        enemy_present,
        np.where(ally_present, cfg.DAMAGE_PER_ENEMY // 2, cfg.DAMAGE_PER_ENEMY),
        0,
    )
    overcrowd_damage = np.where(overcrowded, cfg.DAMAGE_PER_OWN_OVERCROWDING, 0)
    ally_bonus = np.where(ally_present, cfg.BONUS_PER_ALLY, 0)

    matrix[:, INDEX_HP] += ally_bonus - enemy_damage - overcrowd_damage
    matrix[:, INDEX_HP] -= cfg.BASE_DECAY_PER_TICK

    # Efeito de zona (bonus se positivo, dano se negativo).
    matrix[:, INDEX_HP] += _zone_effect(xs, ys)

    matrix[:, INDEX_TIME] += 1

    alive = np.nonzero(matrix[:, INDEX_HP] > cfg.DIE_WHEN_HP_LESS_OR_EQUAL)[0]

    state.deaths += matrix.shape[0] - alive.size

    # Snapshot de morte: se o bicho observado pertence a ESTA
    # linhagem e morreu neste tick, captura seu estado final ANTES de
    # compactar ids/pool/agents. Depois da compactacao as linhas somem
    # e nao ha como reconstrui-las. So a linhagem dona faz trabalho
    # pesado; as outras duas pagam no maximo uma busca vetorizada.
    _capture_death_snapshot_if_needed(index, agent, alive, matrix)

    # Compacta ids, pool e agents em lockstep. O mesmo booleano
    # `alive` seleciona as mesmas linhas nos tres arrays paralelos;
    # esta e a invariante que mantem ID <-> genoma <-> fenotipo
    # alinhados apos mortes.
    agent["ids"] = agent["ids"][alive]
    agent["pool"] = agent["pool"][alive]
    matrix = matrix[alive]
    agent["agents"] = matrix

    # Score composto: calculado UMA vez por linhagem por tick, aqui,
    # apos a compactacao (a normalizacao usa so os sobreviventes) e
    # ANTES do loop de reproducao (que nao recalcula mais por par).
    # Ver _select_parents.
    if cfg.REPRODUCTION_CRITERION == "composite" and matrix.shape[0] > 0:
        scores = _compute_composite_score(matrix)
        matrix[:, INDEX_COMPOSITE_SCORE] = scores

    # Acumula recem-nascidos localmente para adiciona-los ao campo de
    # densidade em uma passada incremental, em vez de reconstruir o
    # campo inteiro no fim do tick.
    newborns: list[np.ndarray] = []

    # Reproducao: gated pelo turno global (ver simulation.step).
    #
    # Dentro de um turno, o numero de TENTATIVAS e fixo, nao "enquanto
    # houver espaco":
    #
    #   attempts = max(1, ceil(len / REPRODUCTION_ATTEMPTS_DIVISOR))
    #
    # Isso faz a populacao crescer como curva suave ao longo de muitos
    # turnos em vez de encher ate o teto num so turno. Tambem faz o
    # loop terminar sempre: as iteracoes sao limitadas por `attempts`,
    # e o check de teto la dentro e guarda de seguranca, nao condicao
    # de parada.
    #
    # Cada TENTATIVA gera OFFSPRING_PER_PAIR filhos em caso de
    # sucesso. Uma tentativa pode falhar em silencio (menos de 2 pais
    # elegiveis, sem crossover, etc.), por isso o numero real de
    # recem-nascidos pode ser menor que attempts * OFFSPRING_PER_PAIR.
    if reproduce:
        attempts = max(
            1,
            math.ceil(agent["agents"].shape[0] / cfg.REPRODUCTION_ATTEMPTS_DIVISOR),
        )
        for _ in range(attempts):
            if (
                agent["agents"].shape[0]
                > cfg.MAX_POPULATION_PER_LINEAGE - cfg.OFFSPRING_PER_PAIR
            ):
                break
            children = _reproduce_one_pair(agent, mutation_rate, mutated_genes)
            if not children:
                break
            newborns.extend(children)

    if newborns:
        fill_fields_incremental(agent, np.stack(newborns, axis=0))


def _select_parents(agent: dict, count: int) -> np.ndarray:
    """Seleciona `count` indices de pais do pool reprodutivo.

    Elegibilidade: precisa passar nos QUATRO portoes para ser
    candidato:
        INDEX_TIME        >= REPRODUCTION_MIN_AGE         (velho o bastante)
        INDEX_HP          <  REPRODUCTION_HP_GATE         (ferido o bastante)
        INDEX_COMPOSITE_SCORE >= REPRODUCTION_MIN_SCORE   (bom o bastante)
        INDEX_ENCOUNTERS  >= REPRODUCTION_MIN_ENCOUNTERS  (contato o bastante)
    Recem-nascidos, juvenis, bichos saudaveis, de score baixo e com
    poucos encontros ficam de fora, nao importa quao bom seja um
    metrica isolada. Os quatro portoes sao aplicados ANTES do
    ranking, entao o ranking so ve bichos que podem reproduzir.

    O score composto e lido de INDEX_COMPOSITE_SCORE, onde foi escrito
    por punish_reward_and_reproduce logo antes (mesmo tick). O
    contador de encontros e incrementado na mesma funcao. Sem novo
    caminho de dados: as duas colunas ja existem na matriz.

    Modo "longevity": ordena por INDEX_TIME.
    Modo "composite": ordena por score composto.

    O score composto NAO e mais calculado aqui. E calculado uma vez
    por tick por linhagem em punish_reward_and_reproduce, logo apos
    a compactacao, e escrito in-place em INDEX_COMPOSITE_SCORE. Esta
    funcao so le, o que transforma uma recomputacao por par (dezenas
    por tick) numa passada unica.

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
    eligible = np.nonzero(
        (matrix[:, INDEX_TIME] >= cfg.REPRODUCTION_MIN_AGE)
        & (matrix[:, INDEX_HP] < cfg.REPRODUCTION_HP_GATE)
        & (matrix[:, INDEX_COMPOSITE_SCORE] >= cfg.REPRODUCTION_MIN_SCORE)
        & (matrix[:, INDEX_ENCOUNTERS] >= cfg.REPRODUCTION_MIN_ENCOUNTERS)
    )[0]
    if eligible.size < 2:
        return eligible

    # Rank DENTRO do conjunto elegivel. argsort num subset retorna
    # indices LOCAIS em `eligible`; mapeamos de volta com
    # eligible[order].
    if cfg.REPRODUCTION_CRITERION == "composite":
        scores = matrix[eligible, INDEX_COMPOSITE_SCORE]
        local_order = np.argsort(-scores)
    else:
        times = matrix[eligible, INDEX_TIME]
        local_order = np.argsort(-times)

    ranked = eligible[local_order]

    pool_size = max(2, int(len(ranked) * cfg.REPRODUCTIVE_POOL_FRACTION))
    pool_size = min(pool_size, len(ranked))
    return ranked[:pool_size]


def _reproduce_one_pair(
    agent: dict, mutation_rate: int, mutated_genes: int
) -> list[np.ndarray]:
    """Sorteia 2 pais do pool reprodutivo e gera
    OFFSPRING_PER_PAIR filhos.

    Geracao do filho: max(parent1_gen, parent2_gen) + 1. Filhos
    nascem com hidden state zerado (sem memoria herdada). Pais tem o
    contador INDEX_OFFSPRING incrementado.

    Retorna a lista de REGISTROS dos filhos (cada um ndarray
    [AGENT_COLUMNS] float32) anexados a linhagem, para o chamador
    acumular e adicionar ao campo de densidade em uma passada
    incremental (ver fill_fields_incremental). Retorna lista vazia se
    nenhum par pode ser sorteado.
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
    )
    if not batch1 or not batch2:
        return []

    new_records: list[np.ndarray] = []
    new_genomes: list[np.ndarray] = []
    for child in (batch1[0], batch2[0]):
        x = int(np.random.randint(0, layout.LAYOUT.world_width))
        y = int(np.random.randint(0, layout.LAYOUT.world_height))
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
        # OFFSPRING_PER_PAIR. Aplicado in-place em `matrix`, entao cai
        # nas linhas dos pais em agent["agents"] antes do concatenate
        # abaixo estender a matriz com os recem-nascidos.
        matrix[i1, INDEX_HP] += HP_BONUS_PER_OFFSPRING
        matrix[i2, INDEX_HP] += HP_BONUS_PER_OFFSPRING

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
