# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Resolver ecologico simultaneo.

Responsavel por calcular e aplicar, em um unico tick, os efeitos
ecologicos de todas as linhagens a partir de um snapshot congelado:

    - predacao (ciclo R->G, G->B, B->R)
    - overcrowding (coefficient x N)
    - base decay
    - zone hp effect
    - encounter
    - nest protection
    - triad chaos (uma unica relacao por celula triad)
    - morte determinada apos todos os deltas
    - compactacao lockstep ids/pool/agents
    - captura de DeathSnapshot para toda mortalidade
    - archive recente e Inspection quando aplicavel
    - recomputacao do composite score

O modulo e dono da semantica ecologica; evolution.py deixa de ser.

Contrato de compute_ecology_resolution():

    Le: fields, agents, RuntimeRules, zones, nests.
    Escreve: NADA.

    Unica excecao deliberada: consumo do RNG global NumPy em triad
    chaos, para que escolhas aleatorias facam parte da sequencia
    deterministica persistida. Nao chamar de "pure function".

apply_ecology_resolution() executa os efeitos em fases globais:
todos os deltas aplicados, todas as mortalidades determinadas,
depois compactacao lockstep e recomputacao de score.

Este modulo NAO depende de pygame, rendering, panels, nem bootstrap.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import config as cfg
from . import layout
from . import nest_geometry
from . import state
from .state import agents
from .world import (
    INDEX_CELLS_VISITED,
    INDEX_COMPOSITE_SCORE,
    INDEX_ENCOUNTERS,
    INDEX_HP,
    INDEX_OFFSPRING,
    INDEX_TIME,
    INDEX_X,
    INDEX_Y,
)


# --- Estrutura do resultado ----------------------------------------------

@dataclass(frozen=True, slots=True)
class EcologyResolution:
    """Resultado do compute, pronto para o apply.

    Cada posicao das tuplas corresponde ao indice da linhagem
    (0=R, 1=G, 2=B). Cada array tem shape (N_i,) onde N_i e a
    populacao do snapshot.

    hp_deltas[i]:       variacao de HP a somar em cada individuo.
    encounter_deltas[i]: 0 ou 1, ganho de encounter no tick.
    """
    hp_deltas: tuple[np.ndarray, ...]
    encounter_deltas: tuple[np.ndarray, ...]


# --- Relacoes predatórias canonicas ---------------------------------------

# R->G, G->B, B->R.
# prey_index = (predator_index + 1) % 3
PREDATION_RELATIONS: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 2),
    (2, 0),
)


# --- Zone delta -----------------------------------------------------------

def _zone_delta(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Retorna [N] float32 com state.runtime_rules.zone_hp_effect
    para quem esta dentro de zona, 0 fora.

    Retorna zeros se nao houver zonas (state.zones is None), se
    zones_active for False, ou se zone_hp_effect for 0. O toggle
    suprime o efeito sem tocar na mascara.

    O valor e lido de state.runtime_rules (nao de config) para o
    ajuste em runtime fazer efeito no proximo tick.
    """
    effect = state.runtime_rules.zone_hp_effect
    if state.zones is None or effect == 0 or not state.zones_active:
        return np.zeros(xs.shape[0], dtype=np.float32)
    inside = state.zones[xs, ys]
    return np.where(inside, float(effect), 0.0).astype(np.float32)


# --- Nest protection ------------------------------------------------------

def _protection_mask(lineage_index: int, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Retorna bool[N]: True se o individuo esta dentro do proprio ninho.

    state.nests is None => nenhuma protecao (vetor False).

    Caso contrario, exige len(state.nests) == TOTAL_LINEAGES. Falha
    clara se o contrato for violado.
    """
    n = xs.shape[0]
    if state.nests is None:
        return np.zeros(n, dtype=bool)

    assert len(state.nests) == cfg.TOTAL_LINEAGES, (
        f"state.nests tem {len(state.nests)} centros; esperado "
        f"{cfg.TOTAL_LINEAGES}. Contrato violado."
    )

    center = state.nests[lineage_index]
    return nest_geometry.positions_inside_nest(
        xs,
        ys,
        center,
        width=layout.LAYOUT.world_width,
        height=layout.LAYOUT.world_height,
        radius=cfg.NEST_RADIUS,
    )


# --- Triad selection ------------------------------------------------------

def _select_triad_relations(
    triad_mask: np.ndarray,
    protected_by_lineage: tuple[np.ndarray, np.ndarray, np.ndarray],
    lineage_xs: tuple[np.ndarray, np.ndarray, np.ndarray],
    lineage_ys: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> np.ndarray:
    """Retorna selected_relation[W, H] int8 com:

        -1 = nenhuma
         0 = R->G
         1 = G->B
         2 = B->R

    Apenas celulas triad recebem valor != -1.

    Uma relacao e removida da escolha se a presa estiver protegida
    em alguma instancia (em qualquer posicao). Para celulas triad,
    todas as presas de todas as linhagens estao na mesma celula; o
    conjunto de protecao da presa e por individuo, entao a relacao
    e inelegivel se NENHUMA presa daquela linhagem estiver
    desprotegida.

    Consumo de RNG: um draw por celula com >= 2 relacoes elegiveis.
    Zero draws para 1 relacao, zero draws para 0 relacoes.
    """
    width, height = triad_mask.shape
    selected = np.full((width, height), -1, dtype=np.int8)

    if not triad_mask.any():
        return selected

    # Lookup de protecao por celula: para a linhagem-presa, e
    # protegida SE TODAS as suas instancias na celula estao no
    # proprio ninho. O caso "nenhuma instancia" nao ocorre em triad
    # (por definicao, todas as linhas tem field > 0 na celula).
    #
    # Para responder "esta protegida na celula (x,y)?", construimos
    # uma mascara esparsa por linhagem.
    protected_cell: list[np.ndarray] = []
    for li in range(cfg.TOTAL_LINEAGES):
        xs = lineage_xs[li]
        ys = lineage_ys[li]
        prot = protected_by_lineage[li]
        # Mapa denso [W, H]: True = todas as instancias em (x,y)
        # estao protegidas. Inicialmente True nas celulas ocupadas
        # (assumimos protegido ate achar instancia desprotegida).
        cell_any = np.zeros((width, height), dtype=bool)
        cell_all_protected = np.ones((width, height), dtype=bool)
        if xs.size:
            # Marca ocupacao.
            np.add.at(cell_any.view(np.int8), (xs, ys), 1)
            # Marca desprotegido onde ao menos uma instancia nao e
            # protegida.
            unprotected = ~prot
            if unprotected.any():
                ux = xs[unprotected]
                uy = ys[unprotected]
                cell_all_protected[ux, uy] = False
        # Efetivo: celula protegida para esta linhagem sse ocupada
        # e todas instancias protegidas.
        protected_cell.append(cell_any & cell_all_protected)

    triad_cells = np.argwhere(triad_mask)

    # Numero de relacoes elegiveis por celula e escolha.
    for tx, ty in triad_cells:
        tx = int(tx)
        ty = int(ty)

        eligible: list[int] = []
        for rel_id, (pred_li, prey_li) in enumerate(PREDATION_RELATIONS):
            # Prey protegida na celula? Se todas as instancias da
            # presa estao no proprio ninho, a relacao e inelegivel.
            if protected_cell[prey_li][tx, ty]:
                continue
            eligible.append(rel_id)

        if len(eligible) == 1:
            selected[tx, ty] = eligible[0]
        elif len(eligible) > 1:
            pick = int(np.random.randint(len(eligible)))
            selected[tx, ty] = eligible[pick]
        # Se 0: permanece -1.

    return selected


# --- Predacao vetorizada --------------------------------------------------

def _apply_predation_for_relation(
    predator_index: int,
    prey_index: int,
    relation_id: int,
    triad_mask: np.ndarray,
    selected_relation: np.ndarray,
    snapshot_hp: tuple[np.ndarray, ...],
    protected_by_lineage: tuple[np.ndarray, np.ndarray, np.ndarray],
    hp_deltas: list[np.ndarray],
) -> None:
    """Aplica o efeito de UMA relacao P->Q sobre hp_deltas, in-place.

    Regra de elegibilidade por celula:
        relation_allowed = (~triad_mask) | (triad_mask & (selected == relation_id))

    Depois:
        predator_field > 0
        AND relation_allowed
        AND (existe presa elegivel na celula: predator_count > 0 e prey not protected)

    A presa perde effective_damage EXATO (sem floor).
    Cada predador recebe floor(effective_damage / predator_count).
    Overkill usa snapshot HP; nao consulta deltas ja aplicados.

    Para triads: a relacao so e aplicada na celula triad se foi a
    escolhida. Para celulas nao-triad: aplicada sempre que houver
    contato.
    """
    predator_agent = agents[predator_index]
    prey_agent = agents[prey_index]

    predator_matrix = predator_agent["agents"]
    prey_matrix = prey_agent["agents"]

    if prey_matrix.shape[0] == 0 or predator_matrix.shape[0] == 0:
        return

    prey_xs = prey_matrix[:, INDEX_X].astype(np.int64)
    prey_ys = prey_matrix[:, INDEX_Y].astype(np.int64)

    # predador presente na celula da presa?
    predator_field_at_prey = predator_agent["field"][prey_xs, prey_ys]
    predator_present = predator_field_at_prey > 0

    # relacao permitida na celula da presa?
    triad_at_prey = triad_mask[prey_xs, prey_ys]
    relation_ok_at_prey = (
        (~triad_at_prey)
        | (triad_at_prey & (selected_relation[prey_xs, prey_ys] == relation_id))
    )

    # presa protegida em seu proprio ninho?
    prey_protected = protected_by_lineage[prey_index]

    eligible = predator_present & relation_ok_at_prey & (~prey_protected)

    if not eligible.any():
        return

    prey_hp_snapshot = snapshot_hp[prey_index]
    transfer = float(state.runtime_rules.predation_transfer)

    # effective_damage para as presas elegiveis.
    effective_damage = np.minimum(
        transfer,
        np.maximum(prey_hp_snapshot, 0.0),
    ).astype(np.float32, copy=False)

    eff_eligible = effective_damage[eligible]  # [K]
    n_predators = predator_field_at_prey[eligible].astype(np.int64)

    # HP da presa: perde effective_damage EXATO.
    hp_deltas[prey_index][eligible] -= eff_eligible

    # Recompensa por celula: soma dos shares.
    # share = floor(effective_damage / predator_count) por presa.
    share = np.floor(eff_eligible / n_predators).astype(np.float32)

    reward_field = np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=np.float32,
    )
    np.add.at(reward_field, (prey_xs[eligible], prey_ys[eligible]), share)

    # Predadores consultam o reward acumulado de suas celulas.
    pred_xs = predator_matrix[:, INDEX_X].astype(np.int64)
    pred_ys = predator_matrix[:, INDEX_Y].astype(np.int64)
    hp_deltas[predator_index] += reward_field[pred_xs, pred_ys]


# --- Compute --------------------------------------------------------------

def compute_ecology_resolution() -> EcologyResolution:
    """Calcula todos os deltas ecologicos a partir do snapshot atual.

    NAO muta HP, encounters, age, mortes, compactacao, reprodução,
    fields, births, deaths.

    Unica side effect deliberada: consumo do RNG NumPy global em
    triad chaos.

    Fields devem estar congelados (chamada precedente a fill_fields()
    pos-movimento). Nao reconstroi fields.
    """
    # 1. Snapshot de HP (predacao com overkill usa este snapshot).
    snapshot_hp = tuple(
        agent["agents"][:, INDEX_HP].copy()
        for agent in agents
    )

    # 2. Deltas zerados, shape correspondente a populacao atual.
    hp_deltas: list[np.ndarray] = []
    encounter_deltas: list[np.ndarray] = []
    lineage_xs: list[np.ndarray] = []
    lineage_ys: list[np.ndarray] = []
    for agent in agents:
        n = agent["agents"].shape[0]
        hp_deltas.append(np.zeros(n, dtype=np.float32))
        encounter_deltas.append(np.zeros(n, dtype=np.float32))
        if n:
            lineage_xs.append(agent["agents"][:, INDEX_X].astype(np.int64))
            lineage_ys.append(agent["agents"][:, INDEX_Y].astype(np.int64))
        else:
            lineage_xs.append(np.empty(0, dtype=np.int64))
            lineage_ys.append(np.empty(0, dtype=np.int64))

    # 3. Encounters: 0/1 por individuo, se QUALQUER outra linhagem
    #    esta na mesma celula.
    for li, agent in enumerate(agents):
        matrix = agent["agents"]
        if matrix.shape[0] == 0:
            continue
        xs = lineage_xs[li]
        ys = lineage_ys[li]
        other_present = np.zeros(matrix.shape[0], dtype=bool)
        for other_li, other in enumerate(agents):
            if other_li == li:
                continue
            other_present |= other["field"][xs, ys] > 0
        encounter_deltas[li] += other_present.astype(np.float32)

    # 4. Overcrowding: coefficient * N quando N >= 2.
    rules = state.runtime_rules
    for li, agent in enumerate(agents):
        matrix = agent["agents"]
        if matrix.shape[0] == 0:
            continue
        xs = lineage_xs[li]
        ys = lineage_ys[li]
        own_count = agent["field"][xs, ys].astype(np.float32)
        overcrowded = own_count >= 2.0
        hp_deltas[li] -= (
            rules.damage_per_own_overcrowding
            * own_count
            * overcrowded.astype(np.float32)
        )

    # 5. Base decay: sempre.
    for li, agent in enumerate(agents):
        if agent["agents"].shape[0] == 0:
            continue
        hp_deltas[li] -= float(rules.base_decay_per_tick)

    # 6. Zones.
    for li, agent in enumerate(agents):
        if agent["agents"].shape[0] == 0:
            continue
        hp_deltas[li] += _zone_delta(lineage_xs[li], lineage_ys[li])

    # 7. Nest protection por linhagem.
    protected_by_lineage: tuple[np.ndarray, np.ndarray, np.ndarray] = (
        _protection_mask(0, lineage_xs[0], lineage_ys[0]),
        _protection_mask(1, lineage_xs[1], lineage_ys[1]),
        _protection_mask(2, lineage_xs[2], lineage_ys[2]),
    )

    # 8. Triad mask.
    field_r = agents[0]["field"]
    field_g = agents[1]["field"]
    field_b = agents[2]["field"]
    triad_mask = (field_r > 0) & (field_g > 0) & (field_b > 0)

    # 9. Escolha de relacoes triad.
    selected_relation = _select_triad_relations(
        triad_mask,
        protected_by_lineage,
        (lineage_xs[0], lineage_xs[1], lineage_xs[2]),
        (lineage_ys[0], lineage_ys[1], lineage_ys[2]),
    )

    # 10. Predacao por relacao.
    for rel_id, (pred_li, prey_li) in enumerate(PREDATION_RELATIONS):
        _apply_predation_for_relation(
            pred_li,
            prey_li,
            rel_id,
            triad_mask,
            selected_relation,
            snapshot_hp,
            protected_by_lineage,
            hp_deltas,
        )

    return EcologyResolution(
        hp_deltas=tuple(hp_deltas),
        encounter_deltas=tuple(encounter_deltas),
    )


# --- Composite score ------------------------------------------------------

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

    rules = state.runtime_rules
    score = (
        rules.longevity_weight * (time / max_time)
        + rules.exploration_weight * (cells / max_cells)
        + rules.interaction_weight * (encounters / max_encounters)
        + rules.reproduction_weight * (offspring / max_offspring)
    )
    return score.astype(np.float32)


# --- Death snapshot -------------------------------------------------------

def _capture_death_snapshots(
    lineage_index: int,
    agent: dict,
    dead_indices: np.ndarray,
    matrix: np.ndarray,
) -> None:
    """Captura toda mortalidade antes da compactacao lockstep.

    Um DeathSnapshot independente e registrado por linha morta, na
    ordem natural dos indices. record_death_snapshot() tambem instala
    o mesmo objeto na Inspection quando o morto era o observado.
    """
    for ai_raw in dead_indices:
        ai = int(ai_raw)
        snapshot = state.DeathSnapshot(
            critter_id=int(agent["ids"][ai]),
            lineage_index=lineage_index,
            lineage_id=str(agent["id"]),
            tick=int(state.tick_count),
            agent=matrix[ai].copy(),
            genome=agent["pool"][ai].copy(),
        )
        state.record_death_snapshot(snapshot)


# --- Apply ----------------------------------------------------------------

def apply_ecology_resolution(resolution: EcologyResolution) -> None:
    """Aplica a resolucao em fases globais.

    FASE A: aplicar HP delta, encounter delta e age em TODAS as
            linhagens.
    FASE B: determinar alive masks de TODAS as linhagens.
    FASE C: capturar todos os death snapshots e contabilizar deaths.
    FASE D: compactar ids/pool/agents de TODAS as linhagens em
            lockstep.
    FASE E: recalcular composite score dos sobreviventes.

    Newborns nao existem aqui: reproducao acontece depois, fora
    deste modulo.
    """
    rules = state.runtime_rules

    # FASE A: aplicar deltas + age.
    for li, agent in enumerate(agents):
        matrix = agent["agents"]
        if matrix.shape[0] == 0:
            continue
        matrix[:, INDEX_HP] += resolution.hp_deltas[li]
        matrix[:, INDEX_ENCOUNTERS] += resolution.encounter_deltas[li]
        matrix[:, INDEX_TIME] += 1.0

    # FASE B: alive masks.
    alive_masks: list[np.ndarray] = []
    for li, agent in enumerate(agents):
        matrix = agent["agents"]
        if matrix.shape[0] == 0:
            alive_masks.append(np.empty(0, dtype=bool))
            continue
        alive_masks.append(
            matrix[:, INDEX_HP] > rules.death_hp_threshold
        )

    # FASE C: snapshots de toda mortalidade e contagem.
    total_deaths = 0
    for li, agent in enumerate(agents):
        matrix = agent["agents"]
        if matrix.shape[0] == 0:
            continue
        dead = np.nonzero(~alive_masks[li])[0]
        total_deaths += int(dead.size)
        _capture_death_snapshots(li, agent, dead, matrix)

    state.deaths += total_deaths

    # FASE D: compactar lockstep.
    for li, agent in enumerate(agents):
        matrix = agent["agents"]
        if matrix.shape[0] == 0:
            continue
        alive = alive_masks[li]
        agent["ids"] = agent["ids"][alive]
        agent["pool"] = agent["pool"][alive]
        agent["agents"] = matrix[alive]

    # FASE E: recomputar score dos sobreviventes.
    for agent in agents:
        matrix = agent["agents"]
        if matrix.shape[0] > 0:
            scores = _compute_composite_score(matrix)
            matrix[:, INDEX_COMPOSITE_SCORE] = scores
