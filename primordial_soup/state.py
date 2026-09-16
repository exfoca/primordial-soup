# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from . import config as cfg
from .runtime_rules import (
    RuntimeRules,
    default_runtime_rules,
    updated_runtime_rules,
    validate_runtime_rules,
)

# agents[i] = {"id", "color", "pool": ndarray [N, GENOME_SIZE],
#              "agents": ndarray [N, AGENT_COLUMNS],
#              "ids": ndarray [N], "field": ndarray}
#
# As chaves internas usam os nomes em ingles; a ponte para as chaves
# em portugues do savegame acontece so em persistence.py.
agents: list[dict[str, Any]] = []

# Fonte unica das regras runtime ajustaveis em execucao. Substitui
# as antigas variaveis module-level mutation_rate / mutated_genes /
# local_scale_fraction. Alteracoes passam por set_runtime_rules /
# update_runtime_rules; o dataclass e frozen, entao nao ha mutacao
# parcial in-place.
runtime_rules: RuntimeRules = default_runtime_rules()

# Mascara booleana [WORLD_WIDTH, WORLD_HEIGHT] das zonas ambientais.
# None significa mundo homogeneo.
zones: np.ndarray | None = None

# Centros dos ninhos, um por linhagem, na ordem canonica definida por
# cfg.LINEAGES (0 -> R, 1 -> G, 2 -> B). Tuple imutavel: a geometria
# dos ninhos e fixa durante a run.
#
# None significa "geometria ainda nao inicializada" (estado
# pre-bootstrap). Apos bootstrap_new_world() ou load() bem-sucedido,
# ha exatamente TOTAL_LINEAGES centros. NAO usar
# ((0,0),(0,0),(0,0)) como placeholder: None e o contrato de
# "ausente", a tupla de 3 centros e o contrato de "presente".
nests: tuple[tuple[int, int], ...] | None = None

# Centros canonicos das zonas ambientais. Tuple de NUMBER_OF_ZONES
# pares (x, y) int Python, na mesma ordem em que os centros foram
# sorteados por generate_zones(). A mascara state.zones e a uniao
# toroidal dos discos definidos por estes centros com cfg.ZONE_RADIUS;
# a coerencia mascara<->centros e validada por save/load.
#
# None significa "geometria ainda nao inicializada". Apos bootstrap
# ou load bem-sucedido, quando NUMBER_OF_ZONES > 0, ha exatamente
# NUMBER_OF_ZONES centros. Sempre substituido junto com state.zones e
# state.nests.
zone_centers: tuple[tuple[int, int], ...] | None = None

zones_active: bool = True

# O efeito de HP por tick dentro de zona vive em runtime_rules
# (runtime_rules.zone_hp_effect). A mascara em si continua em
# state.zones, e o toggle em state.zones_active.

def set_runtime_rules(new_rules: RuntimeRules) -> None:
    """Substitui o RuntimeRules ativo. Valida antes de qualquer escrita.

    Contrato:
        1. validar new_rules;
        2. somente depois substituir state.runtime_rules.

    Se a validacao falhar, o objeto antigo permanece intacto.
    """
    validate_runtime_rules(new_rules)

    global runtime_rules
    runtime_rules = new_rules


def update_runtime_rules(**changes) -> RuntimeRules:
    """Aplica mudancas sobre o RuntimeRules atual e devolve o novo.

    Porta normal para handlers de UI e para intervencoes em runtime.
    Le state.runtime_rules, constroi um candidate com as mudancas,
    valida e substitui atomicamente. Retorna o objeto em vigor (ja
    com as mudancas).

    Se o candidate for igual ao runtime_rules atual, e no-op de
    identidade: nada e substituido, e o cooldown nao e tocado.

    Coordenacao com o scheduler reprodutivo:

    reproduction_interval e uma LEI (quantos ticks entre turnos),
    enquanto reproduction_cooldown e a FASE ATUAL do scheduler. Ao
    alterar o intervalo em runtime, a fase precisa permanecer
    coerente com a nova lei:

        new_cooldown = min(cooldown_atual, novo_interval)

    Interpretacao:
      - Reduzir o intervalo (ex.: 150 -> 30): se o cooldown atual
        (117) exceder o novo intervalo, ele e derrubado para 30. Isso
        antecipa o proximo turno, o que e coerente com "turnos
        ficaram mais frequentes".
      - Aumentar o intervalo (ex.: 30 -> 300): se o cooldown atual
        (7) for menor que o novo intervalo, ele permanece em 7. O
        turno ja proximo nao e postergado apenas porque a lei mudou.
      - Cooldown zero: permanece zero. O turno disponivel continua
        disponivel.

    A ordem e importante: candidate validado primeiro, so entao
    commit. Se a validacao falhar, nem runtime_rules nem
    reproduction_cooldown sao tocados.

    Esta funcao NAO e usada pelo loader: restauracao de checkpoint
    chama set_runtime_rules() seguido de atribuicao direta de
    cooldown/turn, sem reinterpretar a lei salva como intervencao
    hot. Ver persistence.load().
    """
    global reproduction_cooldown

    current = runtime_rules
    candidate = updated_runtime_rules(current, **changes)

    if candidate is current:
        # No-op de identidade propagado: nem rules nem cooldown
        # mudam.
        return current

    new_cooldown = reproduction_cooldown

    if candidate.reproduction_interval != current.reproduction_interval:
        new_cooldown = min(
            reproduction_cooldown,
            candidate.reproduction_interval,
        )

    set_runtime_rules(candidate)
    reproduction_cooldown = new_cooldown

    return runtime_rules


# Contador global de identidade. Toda criatura recebe um ID unico,
# monotonico e persistente, independente da posicao no ndarray.
next_critter_id: int = 1

# Parametro ajustavel ativo. As setas atuam sobre este; U, O, E
# selecionam qual esta ativo.
#
# Valores sao os identificadores de config.py (PARAM_*). None = sem
# selecao (setas sao no-op). O jogo comeca com PARAM_MUTATION ativo
# (ver simulation.run).
#
# Preferencia de UI, como language: NAO persistida no savegame e NAO
# resetada por reset_counters(). R mantem o parametro selecionado.
active_param: str | None = cfg.PARAM_MUTATION

# Lente de discovery: criterio e filtro de linhagem ativos para
# selecao de candidato (ver cfg.CRITERIA_ORDER e
# cfg.LINEAGE_FILTER_ORDER). Preferencias de UI, como active_param:
# NAO persistidas no savegame nem resetadas por reset_counters().
discovery_criterion: str = cfg.CRITERION_MOST_EVOLVED
discovery_lineage_filter: str = cfg.LINEAGE_FILTER_ALL

tick_count: int = 0
last_print: int = 0
paused: bool = True

# Multiplicador de velocidade da simulacao. 1.0 = 1 tick por frame
# grafico (semantica historica). Valores < 1.0 espacam ticks ao longo
# de varios frames; valores > 1.0 executam multiplos ticks por frame.
# Estado operacional do operador, nao pertence a RuntimeRules nem ao
# checkpoint. A enum de valores selecionaveis vive em panels_defs.
simulation_speed: float = 1.0

births: int = 0
deaths: int = 0

# --- Maquina de turno de reproducao -----------------------------
#
# Reproducao e evento GLOBAL turn-based: a cada REPRODUCTION_INTERVAL
# ticks, exatamente UMA linhagem reproduz — a dona do turno. O turno
# rotaciona R -> G -> B -> R -> ...
#
# reproduction_cooldown conta de REPRODUCTION_INTERVAL ate 0. Ao
# chegar a 0, a linhagem em `reproduction_turn` recebe o turno, o
# turno avanca e o cooldown reinicia. E um contador UNICO global, nao
# um por linhagem: o turno E o estado por linhagem.
#
# Ambos sao estado de simulacao, nao preferencia: sao resetados por
# reset_counters() porque R comeca uma run nova.
reproduction_cooldown: int = 0
reproduction_turn: int = 0

# Historico de metricas avancadas. Cada deque guarda
# (tick, tupla_de_floats). Tuplas de tamanho 1 = metrica escalar;
# tamanho N = uma entrada por linhagem.
#
# As chaves vem de cfg.ADVANCED_METRICS, que usa nomes canonicos em
# portugues ("populacao", "hp_medio", ...), o formato real do
# savegame e do CSV. Strings de exibicao sao traduzidas so em
# rendering.
#
# Este e o UNICO historico mantido. Populacao e uma das metricas
# ("populacao"), amostrada junto com as outras a cada METRICS_INTERVAL.
# Nao ha historico separado por tick; o painel de chart cicla por
# todas as entradas via M.
metrics_history: dict[str, deque[tuple[int, tuple[float, ...]]]] = {
    name: deque(maxlen=cfg.METRICS_HISTORY_SIZE) for name in cfg.ADVANCED_METRICS
}

# --- Sessao de observacao --------------------------------------
#
# `inspected_critter_id` e a identidade ESTAVEL do bicho observado,
# nao um indice posicional. Sobrevive a compactacao do ndarray
# (mortes) e e o handle autoritativo de "quem esta sendo observado".
# Use world.resolve_critter_id() para obter (lineage, index) atuais.
#
# A sessao NAO depende do painel focado: o operador pode navegar para
# Metrics, Configuration ou world e a Observation continua ativa,
# acumulando trail. Apenas a VISIBILIDADE (markers e trail desenhados)
# e gated por ui_state.active_panel == PANEL_INSPECTION.
#
# Quando o bicho observado morre, a sessao NAO troca para outro
# individuo: a observacao congela. O estado final vai para
# `inspection_death_snapshot`, e o painel/marcador renderizam a
# partir do snapshot.
inspected_critter_id: int | None = None


@dataclass(frozen=True, slots=True)
class DeathSnapshot:
    """Estado final de uma criatura capturado no momento da morte.

    `agent` e copia da linha de AGENT_COLUMNS no momento da morte;
    `genome` e copia da linha correspondente do pool. Ambos usam
    .copy() para que compactacoes posteriores nao corrompam o
    snapshot.

    `lineage_index` e informativo; NAO e um indice vivo em `agents`
    apos a morte.
    """
    critter_id: int
    lineage_index: int
    lineage_id: str
    tick: int
    agent: np.ndarray
    genome: np.ndarray


# Snapshot de morte do bicho observado, ou None se o observado esta
# vivo (ou nenhuma sessao ativa). Invariante (garantida por
# set_inspection_selection): se nao-None, critter_id ==
# inspected_critter_id.
inspection_death_snapshot: DeathSnapshot | None = None

# Historico recente de toda mortalidade, em ordem cronologica. Sem
# maxlen: a unica politica de retencao e temporal, aplicada por
# expire_recent_deaths() em simulation ticks.
recent_deaths: deque[DeathSnapshot] = deque()

# Rastro do bicho observado. Cada entrada e (x, y). Vazio quando nada
# esta selecionado; cresce um ponto por tick enquanto ha observado; e
# limpo quando a selecao MUDA (nao quando um clique repete o mesmo
# bicho).
#
# Ha no maximo UM rastro por vez, o do bicho observado. 600 rastros
# simultaneos afogariam a imagem em ruido.
#
# E estado de VIEW, nao de simulacao: nao vai para o savegame e nao e
# resetado por reset_counters(). A regra de limpeza esta em
# set_inspection_selection.
inspected_trail: deque[tuple[int, int]] = deque(maxlen=cfg.TRAIL_MAX_LENGTH)

# --- Internacionalizacao ---
# Idioma de exibicao. Independente do savegame e do CSV, que sempre
# usam as chaves canonicas em portugues. Nao resetado por
# reset_counters(). Ver i18n.py para a tabela; T cicla em runtime.
language: str = "en"

# --- Save slots ---
# Slot ativo. persistence.save()/load() sem path resolvem para este;
# N cicla por cfg.SAVE_SLOTS.
#
# Preferencia de usuario, como language: NAO resetada por
# reset_counters() e NAO persistida no savegame (seria
# autorreferente).
active_save_slot: str = cfg.DEFAULT_SAVE_SLOT

# --- Gravacao de tela ------------------------------------------
# True enquanto uma gravacao esta em andamento. Este flag e ESPELHO
# do estado autoritativo em recording.py, para que modulos que nao
# podem importar recording.py (ex: rendering, para evitar o import
# pesado do Pillow por frame) chequem barato "estou gravando?".
#
# O gravador e FERRAMENTA, nao parte da simulacao. Portanto:
#   - NAO persistido no savegame,
#   - NAO resetado por reset_counters().
#
# Motivo: R (recreate) pode ser usado no meio de uma gravacao; parar
# como efeito colateral truncaria o GIF. Se um design futuro quiser
# que R pare a gravacao, deve ser decisao explicita.
recording: bool = False


# ---------------------------------------------------------------------------
# Histories
# ---------------------------------------------------------------------------


def register_metrics(values: Mapping[str, Sequence[float]]) -> None:
    """Guarda um snapshot das metricas avancadas no tick atual.

    `values` mapeia nome -> sequencia de floats. Metricas ausentes sao
    ignoradas, o que permite ao config declarar nomes a mais.

    A tupla e normalizada para floats; escalares viram tupla de um
    elemento.

    Os nomes DEVEM ser as chaves canonicas em portugues de
    cfg.ADVANCED_METRICS (ex: "populacao", "taxa_de_mutacao"), que e o
    formato real do savegame e do CSV.

    Populacao tambem e registrada aqui, sob "populacao": e a primeira
    entrada de cfg.ADVANCED_METRICS, entao o painel de chart cicla ate
    ela com o mesmo M.
    """
    for name in cfg.ADVANCED_METRICS:
        if name not in values:
            continue
        series = tuple(float(v) for v in values[name])
        metrics_history[name].append((tick_count, series))


# ---------------------------------------------------------------------------
# Reset semantics
# ---------------------------------------------------------------------------


def reset_counters() -> None:
    """Reseta telemetria, historicos e estado de inspecao.

    E um reset de TELEMETRIA, nao do mundo. Deliberadamente NAO toca:

      - `agents`            (a populacao),
      - `zones`             (o ambiente),
      - `runtime_rules`     (configuracao runtime do operador),
      - `simulation_speed`  (velocidade),
      - `paused`            (controlado pelo operador),
      - `language`          (idioma de exibicao),
      - `recording`         (gravacao em andamento).

    Motivo: R (recreate) reinicia a RUN, nao a configuracao do
    operador. Se o usuario ajustou mutacao para 50% e apertou R, ele
    espera que a nova run comece em 50%. Vale para velocidade, pausa
    e idioma.

    O gravador segue a mesma logica: parar em R truncaria um GIF em
    andamento. O estado autoritativo do gravador vive em
    recording.py.

    O que E resetado:
      - tick_count, last_print,
      - births, deaths,
      - inspected_critter_id (o ID se refere a populacao antiga),
      - inspection_death_snapshot,
      - recent_deaths,
      - inspected_trail,
      - metrics_history,
      - zones_active (volta ao default ON, porque R regenera as
        zonas; manter "zonas escondidas" da run antiga seria
        inconsistente).

    Preferencias de visualizacao (discovery_criterion,
    discovery_lineage_filter) nao sao resetadas: pertencem ao
    operador, nao a run.
    """
    global tick_count, last_print, births, deaths
    global inspected_critter_id, inspection_death_snapshot
    global zones_active
    global reproduction_cooldown, reproduction_turn
    global next_critter_id

    # --- Relogio e contadores ---
    tick_count = 0
    last_print = 0
    births = 0
    deaths = 0

    # --- Identidade ---
    # Nova run comeca do zero: o mundo anterior deixou de existir.
    next_critter_id = 1

    # --- Turno de reproducao ---
    # Run nova = ciclo de turno novo: cooldown 0 (primeira linhagem
    # reproduz ja no tick 0), turno 0 (R comeca).
    reproduction_cooldown = 0
    reproduction_turn = 0

    # --- Toggle de zonas ---
    # A mascara em si (state.zones) e regenerada por recreate(), nao
    # aqui. O toggle volta ao default para a run nova comecar com
    # zonas visiveis e ativas.
    zones_active = True

    # --- Sessao de observacao ---
    # Uma run nova encerra a Observation antiga: o ID observado
    # pertence a populacao descartada. Limpa ID, snapshot e trail
    # juntos. Navegacao de GUI (active_panel, panel_cursors) vive em
    # ui_state e NAO e responsabilidade de reset_counters().
    inspected_critter_id = None
    inspection_death_snapshot = None

    # --- Historicos ---
    recent_deaths.clear()
    for series in metrics_history.values():
        series.clear()

    # --- Trail ---
    # A sessao foi encerrada acima; o trail vai junto.
    inspected_trail.clear()

    # --- Gravacao ---
    # NAO resetada por design: o gravador e ferramenta, nao estado da
    # simulacao. Parar em R truncaria um GIF em andamento. O flag
    # `recording` e espelho do estado em recording.py.


# ---------------------------------------------------------------------------
# Death history / Inspection selection
# ---------------------------------------------------------------------------


def record_death_snapshot(snapshot: DeathSnapshot) -> None:
    """Registra uma morte mantendo ordem cronologica e Observation.

    O mesmo objeto armazenado no archive e instalado na Inspection
    quando a criatura morta e a atualmente observada. O trail nao e
    limpo: ele pertence a Observation que acabou de congelar.
    """
    global inspection_death_snapshot

    if recent_deaths and snapshot.tick < recent_deaths[-1].tick:
        raise ValueError("death snapshot tick regressivo")

    recent_deaths.append(snapshot)
    if snapshot.critter_id == inspected_critter_id:
        inspection_death_snapshot = snapshot


def get_recent_deaths() -> tuple[DeathSnapshot, ...]:
    """Retorna uma visao imutavel do archive recente de mortes."""
    return tuple(recent_deaths)


def expire_recent_deaths(*, current_tick: int | None = None) -> int:
    """Remove snapshots cujo TTL em simulation ticks terminou.

    O archive e cronologico, entao somente o prefixo vencido precisa
    ser removido. Uma Inspection ja iniciada pode continuar apontando
    para um snapshot que deixou de ser descobrivel no mapa.
    """
    if current_tick is None:
        current_tick = tick_count

    removed = 0
    while recent_deaths:
        oldest = recent_deaths[0]
        if current_tick - oldest.tick < cfg.DEATH_MARKER_TTL_TICKS:
            break
        recent_deaths.popleft()
        removed += 1
    return removed


def set_inspection_death_selection(snapshot: DeathSnapshot) -> None:
    """Seleciona atomicamente um DeathSnapshot para Inspection."""
    global inspected_critter_id, inspection_death_snapshot

    if inspected_critter_id != snapshot.critter_id:
        inspected_trail.clear()

    inspected_critter_id = snapshot.critter_id
    inspection_death_snapshot = snapshot


def set_inspection_selection(critter_id: int | None) -> None:
    """Define o bicho observado por ID ESTAVEL; reinicia trail na troca.

    Ponto unico de verdade para "selecao mudou -> trail reinicia".
    Todo codigo que muda inspected_critter_id DEVE passar por aqui, em
    vez de atribuir state.inspected_critter_id direto. Assim o trail
    nunca carrega de um bicho para outro, independente de COMO a
    selecao mudou.

    Contrato:
        None -> X   nova sessao; trail limpo
        X -> Y      selecao mudou; trail limpo; snapshot limpo
        X -> X      no-op (trail preservado)
        X -> None   sessao encerrada; trail limpo; snapshot limpo

    O snapshot e limpo a cada troca de ID observado, para manter a
    invariante `snapshot != None => snapshot.critter_id ==
    inspected_critter_id`. Snapshot de observacao anterior nunca
    vaza para uma nova.
    """
    global inspected_critter_id, inspection_death_snapshot
    if critter_id == inspected_critter_id:
        return
    inspected_critter_id = critter_id
    inspected_trail.clear()
    inspection_death_snapshot = None