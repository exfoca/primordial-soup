# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from . import config as cfg

# agents[i] = {"id", "color", "pool": ndarray [N, GENOME_SIZE],
#              "agents": ndarray [N, AGENT_COLUMNS],
#              "ids": ndarray [N], "field": ndarray}
#
# As chaves internas usam os nomes em ingles; a ponte para as chaves
# em portugues do savegame acontece so em persistence.py.
agents: list[dict[str, Any]] = []

mutation_rate: int = 0
mutated_genes: int = 0
# Fracao de genes afetada pela escala local (em %). So usada em
# "two_scales"; a escala global usa GLOBAL_SCALE_FRACTION.
local_scale_fraction: int = int(cfg.LOCAL_SCALE_FRACTION * 100)

# Mascara booleana [WORLD_WIDTH, WORLD_HEIGHT] das zonas ambientais.
# None significa mundo homogeneo.
zones: np.ndarray | None = None

zones_active: bool = True

# Efeito de HP por tick para bichos dentro de zona.
# Inicializado de cfg.HP_EFFECT_IN_ZONE; ajustado em runtime com E +
# setas. Positivo = bonus (refugio); negativo = dano (armadilha).
# Persistido em "efeito_hp_zonas" (opcional; default cfg).
# Nao resetado por reset_counters(): preferencia do operador.
zone_hp_effect: int = int(cfg.HP_EFFECT_IN_ZONE)

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

ticks_per_frame: int = 1

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

# Metrica exibida no chart. Indice e a posicao em cfg.ADVANCED_METRICS;
# M cicla.
selected_metric_index: int = 0
selected_metric: str = cfg.ADVANCED_METRICS[0]

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
class InspectionDeathSnapshot:
    """Estado final do bicho observado, capturado na morte.

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
inspection_death_snapshot: InspectionDeathSnapshot | None = None

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


def cycle_metric() -> str:
    """Avanca para a proxima metrica e retorna o nome selecionado."""
    global selected_metric_index, selected_metric
    selected_metric_index = (selected_metric_index + 1) % len(cfg.ADVANCED_METRICS)
    selected_metric = cfg.ADVANCED_METRICS[selected_metric_index]
    return selected_metric


# ---------------------------------------------------------------------------
# Reset semantics
# ---------------------------------------------------------------------------


def reset_counters() -> None:
    """Reseta telemetria, historicos e estado de inspecao.

    E um reset de TELEMETRIA, nao do mundo. Deliberadamente NAO toca:

      - `agents`            (a populacao),
      - `zones`             (o ambiente),
      - `mutation_rate`     (ajustado pelo operador),
      - `mutated_genes`     (ajustado pelo operador),
      - `local_scale_fraction` (ajustado pelo operador),
      - `ticks_per_frame`   (velocidade),
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
      - inspected_trail,
      - metrics_history,
      - selected_metric_index / selected_metric,
      - zones_active (volta ao default ON, porque R regenera as
        zonas; manter "zonas escondidas" da run antiga seria
        inconsistente).
    """
    global tick_count, last_print, births, deaths
    global inspected_critter_id, inspection_death_snapshot
    global selected_metric_index, selected_metric
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
    for series in metrics_history.values():
        series.clear()

    # --- Trail ---
    # A sessao foi encerrada acima; o trail vai junto.
    inspected_trail.clear()

    # --- Selecao de metrica ---
    selected_metric_index = 0
    selected_metric = cfg.ADVANCED_METRICS[0]

    # --- Gravacao ---
    # NAO resetada por design: o gravador e ferramenta, nao estado da
    # simulacao. Parar em R truncaria um GIF em andamento. O flag
    # `recording` e espelho do estado em recording.py.


# ---------------------------------------------------------------------------
# Inspection selection
# ---------------------------------------------------------------------------


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
