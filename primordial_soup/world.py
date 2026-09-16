# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import random
import numpy as np

from . import config as cfg
from . import layout
from . import nest_geometry
from . import state
from .state import agents


# Layout do registro de agente (AGENT_COLUMNS colunas float32).
#
# Armazenado como ndarray [N, AGENT_COLUMNS] float32 em state.agents;
# nunca vira lista Python exceto na fronteira de savegame (ver
# persistence.save). float32 em todos os hot paths, inclusive
# INDEX_LOW_HP (ver senses._internal_state_batch).
AGENT_COLUMNS: int = 7 + cfg.HIDDEN_NEURONS + 4  # 36
INDEX_HP: int = 0
INDEX_X: int = 1
INDEX_Y: int = 2
INDEX_TIME: int = 3
INDEX_GENERATION: int = 4
INDEX_LAST_ACTION: int = 5
INDEX_LOW_HP: int = 6
INDEX_HIDDEN_STATE_START: int = 7
INDEX_HIDDEN_STATE_END: int = INDEX_HIDDEN_STATE_START + cfg.HIDDEN_NEURONS
INDEX_CELLS_VISITED: int = INDEX_HIDDEN_STATE_END
INDEX_ENCOUNTERS: int = INDEX_CELLS_VISITED + 1
INDEX_OFFSPRING: int = INDEX_ENCOUNTERS + 1
INDEX_COMPOSITE_SCORE: int = INDEX_OFFSPRING + 1


def format_zones_txt() -> str:
    """Constroi a descricao localizada de zonas usada pelo HUD e
    print_state().

    Fonte unica do texto de zonas: antes era duplicado em
    rendering._draw_hud e controls.print_state, que divergiriam agora
    que o efeito de HP e ajustavel em runtime.

    Le state.runtime_rules.zone_hp_effect (nao cfg.HP_EFFECT_IN_ZONE)
    para o valor exibido sempre bater com a mecanica ativa.
    """
    from . import i18n
    from . import state

    if state.zones is None:
        return i18n.t("hud.zones_none")

    effect = int(state.runtime_rules.zone_hp_effect)
    txt = i18n.t(
        "hud.zones_fmt",
        n=cfg.NUMBER_OF_ZONES,
        r=cfg.ZONE_RADIUS,
        bonus=format_zone_hp_effect(effect),
    )
    if not state.zones_active:
        txt = i18n.t("hud.zones_off_suffix", base=txt)
    if effect < 0:
        txt += " " + i18n.t("hud.zones_damage")
    txt += i18n.t("hud.zones_zkey")
    return txt


def build_zone_mask(
    centers: tuple[tuple[int, int], ...],
) -> np.ndarray | None:
    """Deriva a mascara booleana das zonas a partir dos centros.

    Autoridade unica da conversao centros -> mascara. Pura e
    deterministica: NAO consome RNG, NAO muta state, NAO le
    runtime_rules.

    Contrato:
      - Se cfg.NUMBER_OF_ZONES <= 0: o unico input valido e
        centers == () e o retorno e None.
      - Caso contrario: len(centers) == NUMBER_OF_ZONES, cada centro
        e tuple[int, int] estrito, cada coordenada esta em
        [0, world_width) x [0, world_height).

    Nao aceita list, bool, float, np.int64, str, None ou coordenadas
    fora do mundo. Essas violacoes levantam ValueError; a fronteira
    de persistencia e quem lida com payload externo (listas do
    pickle), nao esta funcao.

    A mascara e a uniao toroidal dos discos de raio cfg.ZONE_RADIUS
    centrados em cada entrada; sobreposicao e permitida (OR).
    """
    if cfg.NUMBER_OF_ZONES <= 0:
        if centers != ():
            raise ValueError(
                "build_zone_mask: NUMBER_OF_ZONES <= 0 exige "
                f"centers == (), recebido {centers!r}."
            )
        return None

    if not isinstance(centers, tuple):
        raise ValueError(
            "build_zone_mask: centers deve ser tuple, "
            f"recebido {type(centers).__name__}."
        )

    if len(centers) != cfg.NUMBER_OF_ZONES:
        raise ValueError(
            "build_zone_mask: esperado exatamente "
            f"{cfg.NUMBER_OF_ZONES} centros, recebido {len(centers)}."
        )

    width = layout.LAYOUT.world_width
    height = layout.LAYOUT.world_height

    for index, center in enumerate(centers):
        if type(center) is not tuple:
            raise ValueError(
                f"build_zone_mask: centro {index} deve ser tuple, "
                f"recebido {type(center).__name__}."
            )
        if len(center) != 2:
            raise ValueError(
                f"build_zone_mask: centro {index} deve ter exatamente "
                f"2 elementos, recebido {len(center)}."
            )
        cx, cy = center
        if type(cx) is not int or type(cy) is not int:
            raise ValueError(
                f"build_zone_mask: centro {index} deve conter "
                "exatamente 2 int Python estritos; recebido "
                f"({type(cx).__name__}, {type(cy).__name__})."
            )
        if not (0 <= cx < width):
            raise ValueError(
                f"build_zone_mask: centro {index} x={cx} fora do "
                f"intervalo [0, {width})."
            )
        if not (0 <= cy < height):
            raise ValueError(
                f"build_zone_mask: centro {index} y={cy} fora do "
                f"intervalo [0, {height})."
            )

    mask = np.zeros((width, height), dtype=bool)
    r = cfg.ZONE_RADIUS
    r2 = r * r

    xs = np.arange(width)
    ys = np.arange(height)

    for cx, cy in centers:
        dx = np.abs(xs - cx)
        dx = np.minimum(dx, width - dx)
        dy = np.abs(ys - cy)
        dy = np.minimum(dy, height - dy)
        dist2 = dx[:, None] ** 2 + dy[None, :] ** 2
        mask |= dist2 <= r2

    return mask


def generate_zones(
) -> tuple[np.ndarray | None, tuple[tuple[int, int], ...]]:
    """Sorteia centros de zonas e deriva a mascara correspondente.

    Retorna (mask, centers). O par e coerente por construcao:
    centers descreve exatamente a geometria que produziu mask.

    Caso NUMBER_OF_ZONES <= 0: retorna (None, ()).

    Caso normal: sorteia exatamente NUMBER_OF_ZONES pares (x, y) com
    random.randrange(width) / random.randrange(height), na ordem
    x,y,x,y,... A sequencia de RNG e identica a da versao anterior
    (2 draws por zona); a mudanca de API nao altera a sequencia
    estocastica do bootstrap.

    A mascara e derivada por build_zone_mask(), autoridade unica da
    conversao centros->mascara. Nao ha logica duplicada aqui.

    O valor canonico da chave "modificadores_ambientais" e "zonas". O
    literal "nenhum" foi removido como opcao de config; a funcao nao
    checa mais por ele.
    """
    if cfg.NUMBER_OF_ZONES <= 0:
        return None, ()

    width = layout.LAYOUT.world_width
    height = layout.LAYOUT.world_height

    centers_list: list[tuple[int, int]] = []
    for _ in range(cfg.NUMBER_OF_ZONES):
        cx = random.randrange(width)
        cy = random.randrange(height)
        centers_list.append((cx, cy))

    centers = tuple(centers_list)
    mask = build_zone_mask(centers)
    return mask, centers


def format_zone_hp_effect(
    effect: int,
    *,
    include_unit: bool = False,
) -> str:
    """Formata o efeito de HP das zonas.

    Contrato exato:
        effect > 0   -> "+5"
        effect == 0  -> "0"
        effect < 0   -> "-5"

    Nunca produz "+0". Nunca usa f"{effect:+d}" (que produziria
    "+0"). A unidade "HP" e canonica e nao e localizada; se
    include_unit for True, o retorno e "+5 HP", "0 HP" ou "-5 HP".

    Esta funcao NAO le state.runtime_rules. O chamador passa o valor
    efetivo.
    """
    value = f"+{effect}" if effect > 0 else str(effect)
    if include_unit:
        return f"{value} HP"
    return value


def generate_nests(
    zones: np.ndarray | None,
) -> tuple[tuple[int, int], ...]:
    """Sorteia exatamente um centro de ninho por linhagem.

    Retorna tuple na ordem canonica de cfg.LINEAGES (0 -> R, 1 -> G,
    2 -> B). Cada centro e (x, y) int Python dentro do mundo.

    Usa exclusivamente o RNG global da stdlib (random), exatamente
    como generate_zones(). O estado desse RNG ja e persistido pelo
    savegame; usar outra fonte tornaria o bootstrap nao-reproduzivel
    com --seed.

    `zones`:
        None       -> nao ha zonas a evitar (regra de zona desativada).
        ndarray    -> dtype bool e shape
                      (layout.LAYOUT.world_width,
                       layout.LAYOUT.world_height).
                      Shape/estrutura invalida e erro de programacao
                      do chamador: ValueError.

    Restricoes por candidato:

        1. o DISCO inteiro do ninho nao pode intersectar nenhuma zona;
        2. o DISCO nao pode compartilhar nenhuma celula com outro
           ninho ja aceito.

    Zonas avaliadas mesmo quando state.zones_active e False: a mascara
    define area geometria do mundo; o toggle controla somente efeito
    e renderizacao.

    Falha ruidosamente (RuntimeError) se uma linhagem esgotar
    cfg.MAX_NEST_PLACEMENT_ATTEMPTS candidatos. A funcao NAO muta
    state, NAO escreve nada em disco e NAO usa np.random.
    """
    width = layout.LAYOUT.world_width
    height = layout.LAYOUT.world_height

    if zones is not None:
        zones_arr = np.asarray(zones)
        if zones_arr.ndim != 2:
            raise ValueError(
                "generate_nests: zones deve ser 2-D, "
                f"recebido ndim={zones_arr.ndim}."
            )
        if zones_arr.dtype != np.bool_:
            raise ValueError(
                "generate_nests: zones deve ter dtype=bool, "
                f"recebido {zones_arr.dtype}."
            )
        expected_shape = (width, height)
        if zones_arr.shape != expected_shape:
            raise ValueError(
                "generate_nests: zones.shape deve ser "
                f"{expected_shape}, recebido {zones_arr.shape}."
            )

    centers: list[tuple[int, int]] = []

    for lineage in cfg.LINEAGES:
        placed = False
        for _attempt in range(cfg.MAX_NEST_PLACEMENT_ATTEMPTS):
            candidate = (
                random.randrange(width),
                random.randrange(height),
            )

            if zones is not None and nest_geometry.nest_intersects_zone(
                candidate,
                zones,
                radius=cfg.NEST_RADIUS,
            ):
                continue

            overlaps = any(
                nest_geometry.nests_overlap(
                    candidate,
                    existing,
                    width=width,
                    height=height,
                    radius=cfg.NEST_RADIUS,
                )
                for existing in centers
            )
            if overlaps:
                continue

            centers.append(candidate)
            placed = True
            break

        if not placed:
            raise RuntimeError(
                f"generate_nests: unable to place nest for lineage "
                f"{lineage['id']!r} after "
                f"{cfg.MAX_NEST_PLACEMENT_ATTEMPTS} attempts "
                f"(NEST_RADIUS={cfg.NEST_RADIUS}, "
                f"world={width}x{height}, zones={'yes' if zones is not None else 'no'})."
            )

    assert len(centers) == cfg.TOTAL_LINEAGES, (
        f"generate_nests: colocou {len(centers)} centros, "
        f"esperado {cfg.TOTAL_LINEAGES}."
    )

    return tuple(centers)


def _initial_record(
    hp: int, x: int, y: int, generation: int, action: int
) -> np.ndarray:
    """Cria um registro de agente com AGENT_COLUMNS colunas.

    Retorna ndarray float32, NAO lista Python. A matriz de agentes e
    o estado da simulacao; so vira lista na fronteira de savegame
    (ver persistence.save).

    O registro comeca zerado e so os campos com valor inicial
    significativo sao sobrescritos. Ficam zerados de proposito:

      - INDEX_TIME            (idade = 0)
      - INDEX_LOW_HP          (flag = 0)
      - INDEX_HIDDEN_STATE_*  (memoria = 0; nao herdada)
      - INDEX_CELLS_VISITED   (exploracao = 0)
      - INDEX_ENCOUNTERS      (interacoes = 0)
      - INDEX_OFFSPRING       (filhos = 0)
      - INDEX_COMPOSITE_SCORE (score = 0; recalculado na selecao)
    """
    record = np.zeros(AGENT_COLUMNS, dtype=np.float32)
    record[INDEX_HP] = float(hp)
    record[INDEX_X] = float(x)
    record[INDEX_Y] = float(y)
    record[INDEX_GENERATION] = float(generation)
    record[INDEX_LAST_ACTION] = float(action)
    return record


def seed_lineages() -> None:
    """Cria as linhagens vazias.

    As chaves internas do dict usam nomes em ingles ("color", "pool",
    "agents", "field"); a ponte para as chaves em portugues do
    savegame acontece em persistence.py.
    """
    agents.clear()
    for lineage in cfg.LINEAGES:
        agents.append(
            {
                "id": lineage["id"],
                "color": lineage["color"],
                # pool e ndarray [N, GENOME_SIZE] float32, nao lista
                # de arrays. Manter como matriz unica permite ao hot
                # path passar direto para evaluate_batch, sem np.stack
                # por tick. A fronteira de savegame converte de volta
                # para list[list[float]] via .tolist().
                "pool": np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32),
                "agents": np.zeros((0, AGENT_COLUMNS), dtype=np.float32),
                # Identidade estavel: paralelo a pool/agents. Invariante:
                # len(ids) == len(pool) == len(agents).
                "ids": np.empty(0, dtype=np.int64),
                "field": np.zeros(
                    (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
                    dtype=np.int16,
                ),
            }
        )


def allocate_critter_ids(count: int) -> np.ndarray:
    """Aloca IDs globais consecutivos para novas criaturas."""
    if count < 0:
        raise ValueError(f"count deve ser >= 0, recebido {count}")
    if count == 0:
        return np.empty(0, dtype=np.int64)
    from . import state

    start = state.next_critter_id
    ids = np.arange(start, start + count, dtype=np.int64)
    state.next_critter_id = start + count
    return ids


def resolve_critter_id(critter_id: int) -> tuple[int, int] | None:
    """Resolve um ID estavel para (linhagem, indice) atual."""
    for li, agent in enumerate(agents):
        ids = agent.get("ids")
        if ids is None or ids.size == 0:
            continue
        matches = np.flatnonzero(ids == critter_id)
        if matches.size:
            return li, int(matches[0])
    return None


def place_initially() -> None:
    """Distribui todos aleatoriamente, HP/tempo zerados, geracao 0.

    `last_action` comeca no centro (parado) para nao injetar vies nos
    primeiros ticks; `low_hp`, hidden state e contadores comecam em 0
    (ver _initial_record).

    Resultado: um ndarray [N, AGENT_COLUMNS] float32 por linhagem (nao
    lista de registros). Construir a matriz de uma vez evita N
    alocacoes seguidas de re-stack em cada hot path.
    """
    neutral_action = cfg.STAY_STILL_INDEX
    n = cfg.INITIAL_POPULATION_PER_LINEAGE
    for agent in agents:
        records = np.zeros((n, AGENT_COLUMNS), dtype=np.float32)
        records[:, INDEX_HP] = float(cfg.INITIAL_HP)
        records[:, INDEX_X] = np.random.randint(
            0, layout.LAYOUT.world_width, size=n
        ).astype(np.float32)
        records[:, INDEX_Y] = np.random.randint(
            0, layout.LAYOUT.world_height, size=n
        ).astype(np.float32)
        records[:, INDEX_GENERATION] = 0.0
        records[:, INDEX_LAST_ACTION] = float(neutral_action)
        agent["agents"] = records
        agent["ids"] = allocate_critter_ids(n)


def fill_fields() -> None:
    """Reconstroi os campos de densidade a partir das posicoes.

    Usa np.add.at (acumulacao por elemento) em vez de += com fancy
    indexing, porque este NAO conta pares (x, y) duplicados: quando
    dois bichos dividem a celula, `field[xs, ys] += 1` incrementa uma
    unica vez. np.add.at e a primitiva correta.

    `agent["agents"]` e ndarray float32 (nao lista); nao precisa de
    np.asarray.
    """
    for agent in agents:
        agent["field"].fill(0)
        matrix = agent["agents"]
        if matrix.size == 0:
            continue
        xs = matrix[:, INDEX_X].astype(np.int64)
        ys = matrix[:, INDEX_Y].astype(np.int64)
        np.add.at(agent["field"], (xs, ys), 1)


def population_per_lineage() -> list[int]:
    return [len(ag["agents"]) for ag in agents]


def longest_lifetime() -> list[int]:
    out: list[int] = []
    for ag in agents:
        matrix = ag["agents"]
        if matrix.size == 0:
            out.append(0)
        else:
            out.append(int(matrix[:, INDEX_TIME].max()))
    return out


def max_generation() -> list[int]:
    """Maior geracao ja alcancada por cada linhagem.

    Linhagem extinta retorna 0.
    """
    out: list[int] = []
    for ag in agents:
        matrix = ag["agents"]
        if matrix.size == 0:
            out.append(0)
        else:
            out.append(int(matrix[:, INDEX_GENERATION].max()))
    return out


def average_hp_per_lineage() -> list[float]:
    """HP medio de cada linhagem. Zero se extinta."""
    averages: list[float] = []
    for ag in agents:
        matrix = ag["agents"]
        if matrix.size == 0:
            averages.append(0.0)
        else:
            averages.append(float(matrix[:, INDEX_HP].mean()))
    return averages


def average_composite_score_per_lineage() -> list[float]:
    """Score composto medio de cada linhagem.

    Zero se extinta. Usado apenas para diagnostico no HUD.

    O score de selecao e atualizado uma vez por tick, apos a
    resolucao ecologica e antes da reproducao, e escrito em
    INDEX_COMPOSITE_SCORE. O valor lido aqui esta sempre atual para
    o tick.
    """
    averages: list[float] = []
    for ag in agents:
        matrix = ag["agents"]
        if matrix.size == 0:
            averages.append(0.0)
        else:
            averages.append(float(matrix[:, INDEX_COMPOSITE_SCORE].mean()))
    return averages


def heal_all(hp: float | None = None) -> int:
    """Define o HP de todo bicho vivo para `hp` (default: INITIAL_HP).

    Retorna o numero de bichos afetados.

    Semantica (reset, nao soma): o HP vira EXATAMENTE o valor alvo.
    Bichos abaixo sao curados; acima sao reduzidos. Sem cap, sem
    overflow, sem acumulacao.

    Escopo:
        - Toca SOMENTE a coluna INDEX_HP.
        - NAO toca posicao, idade, geracao, hidden state,
          cells_visited, encounters, offspring nem composite score.
        - NAO revive bichos mortos.
        - NAO reconstroi campos de densidade (posicoes nao mudam).

    Ferramenta de "clemencia" para experimentos: traz a populacao de
    volta ao HP cheio sem reiniciar a run, preservando a diversidade
    genetica acumulada.

    Vive aqui (nao em evolution.py) porque e operacao de manutencao
    sobre os registros, sem interacao com a ordem do tick nem com a
    selecao.
    """
    target = float(cfg.INITIAL_HP if hp is None else hp)
    affected = 0
    for agent in agents:
        matrix = agent["agents"]
        affected += matrix.shape[0]
        matrix[:, INDEX_HP] = target
    return affected




# ---------------------------------------------------------------------------
# Agent lookup by position (for mouse clicks)
# ---------------------------------------------------------------------------


def find_agent_at(x: int, y: int, radius: int | None = None) -> tuple[int, int] | None:
    """Retorna (linhagem, indice) do bicho mais proximo num raio
    `radius` (toroidal). Se `radius` for None, usa
    cfg.CLICK_RADIUS_IN_CELLS.

    Retorna None se nao houver bicho no raio. Empates de distancia
    sao resolvidos pelo primeiro encontrado.
    """
    if radius is None:
        radius = cfg.CLICK_RADIUS_IN_CELLS

    if radius <= 0:
        # Comportamento estrito: so acerta se a celula for exata.
        for li, agent in enumerate(agents):
            matrix = agent["agents"]
            if matrix.size == 0:
                continue
            xs = matrix[:, INDEX_X].astype(np.int64)
            ys = matrix[:, INDEX_Y].astype(np.int64)
            hits = np.nonzero((xs == x) & (ys == y))[0]
            if hits.size > 0:
                return (li, int(hits[0]))
        return None

    r2 = radius * radius
    best: tuple[int, int] | None = None
    best_d2 = r2 + 1

    for li, agent in enumerate(agents):
        matrix = agent["agents"]
        if matrix.size == 0:
            continue
        xs = matrix[:, INDEX_X].astype(np.int64)
        ys = matrix[:, INDEX_Y].astype(np.int64)
        dx = np.abs(xs - x)
        dx = np.minimum(dx, layout.LAYOUT.world_width - dx)
        dy = np.abs(ys - y)
        dy = np.minimum(dy, layout.LAYOUT.world_height - dy)
        d2 = dx * dx + dy * dy
        within = np.nonzero(d2 <= r2)[0]
        if within.size == 0:
            continue
        # Mais proximo desta linhagem; empate pelo primeiro indice.
        local_best = int(within[np.argmin(d2[within])])
        local_d2 = int(d2[local_best])
        if local_d2 < best_d2:
            best_d2 = local_d2
            best = (li, local_best)

    return best


def find_recent_death_at(
    x: int,
    y: int,
    radius: int | None = None,
) -> state.DeathSnapshot | None:
    """Retorna o DeathSnapshot mais proximo num raio toroidal.

    Em empate de distancia vence a morte mais recente. Como o archive
    e cronologico, iterar em ordem reversa e substituir somente por
    distancia estritamente menor implementa esse desempate sem usar
    tick como criterio primario.
    """
    if radius is None:
        radius = cfg.CLICK_RADIUS_IN_CELLS

    snapshots = state.get_recent_deaths()
    if radius <= 0:
        for snapshot in reversed(snapshots):
            sx = int(snapshot.agent[INDEX_X])
            sy = int(snapshot.agent[INDEX_Y])
            if sx == x and sy == y:
                return snapshot
        return None

    width = layout.LAYOUT.world_width
    height = layout.LAYOUT.world_height
    r2 = radius * radius
    best: state.DeathSnapshot | None = None
    best_d2 = r2 + 1

    for snapshot in reversed(snapshots):
        sx = int(snapshot.agent[INDEX_X])
        sy = int(snapshot.agent[INDEX_Y])
        dx = abs(sx - x)
        dx = min(dx, width - dx)
        dy = abs(sy - y)
        dy = min(dy, height - dy)
        d2 = dx * dx + dy * dy
        if d2 <= r2 and d2 < best_d2:
            best_d2 = d2
            best = snapshot

    return best


# ---------------------------------------------------------------------------
# Selecao por criterio (modo de inspecao)
# ---------------------------------------------------------------------------
#
# Cada helper recebe uma matriz de agentes [N, AGENT_COLUMNS] e
# retorna o indice LOCAL do melhor candidato, ou None se a matriz
# estiver vazia. Os helpers NAO conhecem filtro de linhagem:
# select_by_criterion resolve o filtro em uma lista de linhagens,
# chama cada helper uma vez por linhagem elegivel e reduz os
# vencedores locais para um (li, ai) global.
#
# Empates: cada helper retorna o PRIMEIRO indice local que atinge o
# extremo, via np.argmax / np.argmin.


def _criterion_most_evolved(matrix: np.ndarray) -> int | None:
    """Indice local do bicho mais evoluido nesta matriz.

    Mesmo criterio de world.most_evolved_agent() (score composto,
    depois geracao, depois tempo), mas sobre uma unica linhagem.
    select_by_criterion usa este helper para aplicar "most_evolved"
    sob filtro de linhagem.
    """
    if matrix.shape[0] == 0:
        return None
    scores = matrix[:, INDEX_COMPOSITE_SCORE]
    gens = matrix[:, INDEX_GENERATION]
    times = matrix[:, INDEX_TIME]
    order = np.lexsort((times, gens, scores))
    return int(order[-1])


def _criterion_oldest(matrix: np.ndarray) -> int | None:
    if matrix.shape[0] == 0:
        return None
    return int(np.argmax(matrix[:, INDEX_TIME]))


def _criterion_youngest(matrix: np.ndarray) -> int | None:
    if matrix.shape[0] == 0:
        return None
    return int(np.argmin(matrix[:, INDEX_TIME]))


def _criterion_most_offspring(matrix: np.ndarray) -> int | None:
    if matrix.shape[0] == 0:
        return None
    return int(np.argmax(matrix[:, INDEX_OFFSPRING]))


def _criterion_most_encounters(matrix: np.ndarray) -> int | None:
    if matrix.shape[0] == 0:
        return None
    return int(np.argmax(matrix[:, INDEX_ENCOUNTERS]))


def _criterion_most_explored(matrix: np.ndarray) -> int | None:
    if matrix.shape[0] == 0:
        return None
    return int(np.argmax(matrix[:, INDEX_CELLS_VISITED]))


def _criterion_highest_hp(matrix: np.ndarray) -> int | None:
    if matrix.shape[0] == 0:
        return None
    return int(np.argmax(matrix[:, INDEX_HP]))


def _criterion_lowest_hp(matrix: np.ndarray) -> int | None:
    if matrix.shape[0] == 0:
        return None
    return int(np.argmin(matrix[:, INDEX_HP]))


def _criterion_highest_generation(matrix: np.ndarray) -> int | None:
    if matrix.shape[0] == 0:
        return None
    return int(np.argmax(matrix[:, INDEX_GENERATION]))


def _criterion_best_score(matrix: np.ndarray) -> int | None:
    if matrix.shape[0] == 0:
        return None
    return int(np.argmax(matrix[:, INDEX_COMPOSITE_SCORE]))


_CRITERION_FUNCS = {
    "most_evolved": _criterion_most_evolved,
    "oldest": _criterion_oldest,
    "youngest": _criterion_youngest,
    "most_offspring": _criterion_most_offspring,
    "most_encounters": _criterion_most_encounters,
    "most_explored": _criterion_most_explored,
    "highest_hp": _criterion_highest_hp,
    "lowest_hp": _criterion_lowest_hp,
    "highest_generation": _criterion_highest_generation,
    "best_score": _criterion_best_score,
}


def _select_by_criterion(
    criterion: str, lineage_filter: str = "all"
) -> tuple[int, int] | None:
    """Engine interno de discovery: melhor critter sob um criterio e
    um filtro de linhagem.

    `criterion` e um de cfg.CRITERIA_ORDER.
    `lineage_filter` e cfg.LINEAGE_FILTER_ALL ou um id de linhagem.

    Retorna None se nao houver candidato (linhagem extinta, populacao
    vazia, criterio desconhecido).

    Uso externo deve passar por discovery_candidate().
    """
    func = _CRITERION_FUNCS.get(criterion)
    if func is None:
        return None

    if lineage_filter == cfg.LINEAGE_FILTER_ALL:
        eligible = range(len(agents))
    else:
        eligible = [
            i for i, ag in enumerate(agents) if ag["id"] == lineage_filter
        ]
        if not eligible:
            return None

    best: tuple[int, int] | None = None
    best_key: tuple[float, float, float] | None = None

    for li in eligible:
        matrix = agents[li]["agents"]
        local = func(matrix)
        if local is None:
            continue
        row = matrix[local]
        # Desempate global entre linhagens: valor primario do
        # criterio, depois geracao, depois tempo. Para "youngest" e
        # "lowest_hp" o valor primario e invertido (menor e melhor),
        # entao ele e negado na chave de ordenacao.
        primary = _criterion_primary_value(criterion, row)
        key = (primary, float(row[INDEX_GENERATION]), float(row[INDEX_TIME]))
        if best_key is None or key > best_key:
            best_key = key
            best = (li, int(local))

    return best


def discovery_criterion_value(criterion: str, row: np.ndarray) -> float:
    """Valor HUMANO do criterio para uma linha de agente.

    Retorna o numero bruto correspondente ao criterio, SEM inversao
    de sinal. Este e o valor que a UI deve exibir ao usuario ("tempo:
    1240", "hp: 8700", "geracao: 42"). Nao e o escalar usado para
    ranking.

    Para criterios cujo extremo desejado e o menor (youngest,
    lowest_hp), o ranking interno usa _criterion_primary_value, que
    nega este valor para manter a comparacao "maior e melhor"
    uniforme. A UI nao: ela mostra o valor real, para o operador ler
    "tempo: 120" e nao "tempo: -120".

    Contrato:
      - row: ndarray [AGENT_COLUMNS] da linha do agente
      - retorno: float nao-negativo (todos os campos sao contadores,
        tempos, hps ou scores >= 0)
      - criterio desconhecido cai no score composto (mesmo fallback
        de _criterion_primary_value)
    """
    if criterion == "oldest":
        return float(row[INDEX_TIME])
    if criterion == "youngest":
        return float(row[INDEX_TIME])
    if criterion == "most_offspring":
        return float(row[INDEX_OFFSPRING])
    if criterion == "most_encounters":
        return float(row[INDEX_ENCOUNTERS])
    if criterion == "most_explored":
        return float(row[INDEX_CELLS_VISITED])
    if criterion == "highest_hp":
        return float(row[INDEX_HP])
    if criterion == "lowest_hp":
        return float(row[INDEX_HP])
    if criterion == "highest_generation":
        return float(row[INDEX_GENERATION])
    if criterion == "best_score":
        return float(row[INDEX_COMPOSITE_SCORE])
    # "most_evolved" e qualquer criterio desconhecido caem no score
    # composto.
    return float(row[INDEX_COMPOSITE_SCORE])


def _criterion_primary_value(criterion: str, row: np.ndarray) -> float:
    """Escalar usado para comparar vencedores de linhagens diferentes.

    Maior e sempre melhor. Para "youngest" e "lowest_hp" o valor
    humano (discovery_criterion_value) e negado para que a mesma
    comparacao "maior e melhor" funcione uniformemente.
    """
    human = discovery_criterion_value(criterion, row)
    if criterion in ("youngest", "lowest_hp"):
        return -human
    return human


def discovery_candidate(
    criterion: str, lineage_filter: str = "all"
) -> tuple[int, int] | None:
    """Superficie semantica de discovery para a UI de inspecao.

    Delega para _select_by_criterion(), que e o engine de selecao.
    Existe para:

      1. Explicitar a separacao DISCOVERY x OBSERVATION na camada de
         apresentacao (rendering.py e controls.py).
      2. Concentrar o contrato da invariante "o amarelo que vejo == o
         bicho que Enter observa".

    NAO le `state`. `criterion` e `lineage_filter` sao passados
    explicitamente, o que mantem world.py deterministico.

    Resultado: (lineage_index, agent_index) posicional. Para a
    identidade estavel, converter via world.resolve_critter_id() ou
    lendo agents[li]["ids"][ai].

    Retorna None se nao houver candidato elegivel.
    """
    return _select_by_criterion(criterion, lineage_filter)