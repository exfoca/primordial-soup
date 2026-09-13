# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from typing import Final

# 0. IDENTIDADE
WORLD_NAME: Final = "Primordial Soup"
WORLD_VERSION: Final = "0.4.0"
RANDOM_SEED: Final = None


# 1. O MUNDO — geometria e topologia
# Usuario declara a tela; escala, mundo e janela sao derivados em layout.py.
# Painel de inspecao tem largura fixa a direita. Sem resize em runtime.
SCREEN_WIDTH: Final = 1920
SCREEN_HEIGHT: Final = 1080

TARGET_PIXEL_SCALE: Final = 2

MIN_WORLD_WIDTH: Final = 400
MIN_WORLD_HEIGHT: Final = 300

# 2. LINHAGENS — as espécies e seus ciclos
LINEAGES: Final = (
    {"id": "R", "color": (255, 0, 0), "name": "Red"},
    {"id": "G", "color": (0, 255, 0), "name": "Green"},
    {"id": "B", "color": (80, 140, 255), "name": "Blue"},
)
TOTAL_LINEAGES: Final = len(LINEAGES)


# 3. CORPOS — a populacao viva
INITIAL_POPULATION_PER_LINEAGE: Final = 50

# Teto por linhagem. Inteiro positivo.
MAX_POPULATION_PER_LINEAGE: Final = 333


# 4. PERCEPCAO — o que uma criatura ve
VISION_RADIUS: Final = 5
VISION_SIDE: Final = 2 * VISION_RADIUS + 1
VISION_CHANNELS: Final = TOTAL_LINEAGES
VISION_INPUTS: Final = VISION_SIDE**2 * VISION_CHANNELS

INTERNAL_STATE_INPUTS: Final = 4
NETWORK_INPUTS: Final = VISION_INPUTS + INTERNAL_STATE_INPUTS

LOW_HP_THRESHOLD: Final = 2_000


# 5. COGNIÇÃO — arquitetura do cérebro
HIDDEN_NEURONS: Final = 25
HIDDEN_NEURONS_2: Final = 12

HIDDEN_ACTIVATION: Final = "tanh"
HIDDEN_ACTIVATION_2: Final = "tanh"
OUTPUT_ACTIVATION: Final = "linear"

POSSIBLE_MOVES: Final = 9
STAY_STILL_INDEX: Final = 4

INPUT_HIDDEN_WEIGHTS: Final = NETWORK_INPUTS * HIDDEN_NEURONS
HIDDEN1_HIDDEN2_WEIGHTS: Final = HIDDEN_NEURONS * HIDDEN_NEURONS_2
HIDDEN2_OUTPUT_WEIGHTS: Final = HIDDEN_NEURONS_2 * POSSIBLE_MOVES
HIDDEN_BIASES: Final = HIDDEN_NEURONS
HIDDEN_BIASES_2: Final = HIDDEN_NEURONS_2
RECURRENCE_WEIGHTS: Final = HIDDEN_NEURONS * HIDDEN_NEURONS
GENOME_SIZE: Final = (
    INPUT_HIDDEN_WEIGHTS
    + HIDDEN1_HIDDEN2_WEIGHTS
    + HIDDEN2_OUTPUT_WEIGHTS
    + HIDDEN_BIASES
    + HIDDEN_BIASES_2
    + RECURRENCE_WEIGHTS
)


# 6. METABOLISMO — vida, dano e morte
INITIAL_HP: Final = 10_000
BASE_DECAY_PER_TICK: Final = 1
STAY_STILL_IMPULSE: Final = 1

DAMAGE_PER_ENEMY: Final = 100
DAMAGE_PER_OWN_OVERCROWDING: Final = 100
BONUS_PER_ALLY: Final = 100

DIE_WHEN_HP_LESS_OR_EQUAL: Final = 0


# 6b. MODIFICADORES AMBIENTAIS — heterogeneidade geografica
# Valores fazem parte do contrato de savegame.
ENVIRONMENTAL_MODIFIERS: Final = "zonas"
NUMBER_OF_ZONES: Final = 6
ZONE_RADIUS: Final = 30
HP_EFFECT_IN_ZONE: Final = 5


# 7. SELECAO — quem se torna pai
# Nao persistido; lido em runtime por evolution.py.
REPRODUCTION_CRITERION: Final = "composite"
LONGEVITY_WEIGHT: Final = 0.5
EXPLORATION_WEIGHT: Final = 0.3
INTERACTION_WEIGHT: Final = 0.3
REPRODUCTION_WEIGHT: Final = 0.3

REPRODUCTIVE_POOL_FRACTION: Final = 1 / 3
OFFSPRING_PER_PAIR: Final = 2
REPRODUCE_IN_PAIRS: Final = True

# Tentativas por linhagem por tick:
# attempts = max(1, ceil(len(agents) / REPRODUCTION_ATTEMPTS_DIVISOR))
REPRODUCTION_ATTEMPTS_DIVISOR: Final = 50

# Portao 1: idade minima.
REPRODUCTION_MIN_AGE: Final = 5555

# Portao 2: HP estritamente abaixo deste valor.
REPRODUCTION_HP_GATE: Final = 10000

# Evento global turn-based; a cada N ticks uma linhagem (R->G->B) tem vez.
REPRODUCTION_INTERVAL: Final = 150

# Bonus de HP concedido a CADA pai por evento reprodutivo bem-sucedido.
# Nao multiplicado por filho: com OFFSPRING_PER_PAIR=2, cada pai ainda
# recebe este valor uma unica vez. ~0.5% de INITIAL_HP (10.000):
# contrapeso que faz da reproducao uma estrategia de sobrevivencia
# ativa sem tornar pais ferteis quase imortais.
REPRODUCTION_PARENT_HP_BONUS: Final = 50

# Portao 3: score composto minimo.
REPRODUCTION_MIN_SCORE: Final = 0.6

# Portao 4: minimo de encontros (aliados + inimigos).
REPRODUCTION_MIN_ENCOUNTERS: Final = 6


# 8. HERANCA — crossover e mutacao
# Nenhum destes valores e persistido.
CROSSOVER_MODE: Final = "blocks"
BLOCK_SIZE: Final = 64
CROSSOVER_PROBABILITY: Final = 0.5

MUTATION_MODE: Final = "two_scales"

INITIAL_MUTATION_RATE: Final = 5
INITIAL_MUTATED_GENES: Final = 1

LOCAL_SCALE_FRACTION: Final = 0.05
LOCAL_SCALE_SIGMA: Final = 0.1
GLOBAL_SCALE_FRACTION: Final = 0.20
GLOBAL_SCALE_SIGMA: Final = 1.0
GLOBAL_PROBABILITY: Final = 0.10

MIN_GENE_VALUE: Final = -2.0
MAX_GENE_VALUE: Final = 2.0

MIN_MUTATION_RATE: Final = 0
MAX_MUTATION_RATE: Final = 100
MIN_MUTATED_GENES: Final = 1
MAX_MUTATED_GENES: Final = 50
MIN_LOCAL_SCALE_FRACTION: Final = 1
MAX_LOCAL_SCALE_FRACTION: Final = 100

# Limites de runtime para o efeito de HP das zonas.
MIN_ZONE_HP_EFFECT: Final = -100
MAX_ZONE_HP_EFFECT: Final = 100

# Identificadores canonicos dos parametros ajustaveis em runtime.
# Nao persistidos; so os valores vao para o savegame.
PARAM_MUTATION: Final = "mutation"
PARAM_LOCAL_SCALE: Final = "local_scale"
PARAM_ZONE_HP_EFFECT: Final = "zone_hp_effect"

# Criterios de inspecao (nao persistidos).
CRITERION_MOST_EVOLVED: Final = "most_evolved"
CRITERION_OLDEST: Final = "oldest"
CRITERION_YOUNGEST: Final = "youngest"
CRITERION_MOST_OFFSPRING: Final = "most_offspring"
CRITERION_MOST_ENCOUNTERS: Final = "most_encounters"
CRITERION_MOST_EXPLORED: Final = "most_explored"
CRITERION_HIGHEST_HP: Final = "highest_hp"
CRITERION_LOWEST_HP: Final = "lowest_hp"
CRITERION_HIGHEST_GENERATION: Final = "highest_generation"
CRITERION_BEST_SCORE: Final = "best_score"

CRITERIA_ORDER: Final = (
    CRITERION_MOST_EVOLVED,
    CRITERION_OLDEST,
    CRITERION_YOUNGEST,
    CRITERION_MOST_OFFSPRING,
    CRITERION_MOST_ENCOUNTERS,
    CRITERION_MOST_EXPLORED,
    CRITERION_HIGHEST_HP,
    CRITERION_LOWEST_HP,
    CRITERION_HIGHEST_GENERATION,
    CRITERION_BEST_SCORE,
)

# Filtro de linhagem (Tab). "all" = todas.
LINEAGE_FILTER_ALL: Final = "all"
LINEAGE_FILTER_ORDER: Final = ("all", "R", "G", "B")


# 9. INTERFACE — a janela para o mundo
TARGET_FPS: Final = 60
WINDOW_TITLE: Final = WORLD_NAME
HUD_COLOR: Final = (0, 255, 0)
HUD_FONT: Final = ("monospace", 14, True)

MIN_TICKS_PER_FRAME: Final = 1
MAX_TICKS_PER_FRAME: Final = 256

OVERLAP_POLICY: Final = "max"

# Paleta da UI.
HUD_BG_COLOR: Final = (8, 10, 14)
HUD_BORDER_COLOR: Final = (60, 70, 85)
HUD_TEXT_COLOR: Final = (220, 230, 240)
HUD_TEXT_SECONDARY_COLOR: Final = (140, 155, 175)

# Gráficos.
CHART_WIDTH: Final = 340
CHART_HEIGHT: Final = 140
CHART_MARGIN: Final = 12
CHART_SPACING: Final = 8
CHART_INNER_PADDING: Final = 28

CHART_BG_COLOR: Final = (6, 8, 12)
CHART_GRID_COLOR: Final = (26, 32, 42)
CHART_AXIS_COLOR: Final = (90, 100, 115)
CHART_LABEL_COLOR: Final = (170, 185, 200)
CHART_TITLE_COLOR: Final = (230, 240, 250)

HORIZONTAL_GRID_LINES: Final = 4
VERTICAL_GRID_LINES: Final = 5

CHART_LINE_THICKNESS: Final = 2

# Modo de inspecao.
INSPECTION_MODE: Final = False

# Rastro do bicho inspecionado (nao persistido, nao resetado por
# reset_counters). TRAIL_MAX_LENGTH limita o deque.
TRAIL_MAX_LENGTH: Final = 2000
TRAIL_COLOR_OLD: Final = 40
TRAIL_COLOR_NEW: Final = 240

INSPECTION_PANEL_WIDTH: Final = 320
INSPECTION_CELL_HEIGHT: Final = 8

CLICK_RADIUS_IN_CELLS: Final = 4

PANEL_BG_COLOR: Final = (10, 10, 10)
PANEL_BORDER_COLOR: Final = (80, 80, 80)
PANEL_TEXT_COLOR: Final = (230, 230, 230)
PANEL_SECONDARY_TEXT_COLOR: Final = (160, 160, 160)
INSPECTION_HIGHLIGHT_COLOR: Final = (255, 255, 0)

HEATMAP_LIMIT: Final = 2.0


# 10. PERSISTENCIA
# Sufixo CSV faz parte do contrato do formato de savegame.
# Slots fixos: edite SAVE_SLOTS e reinicie para adicionar.
SAVE_SLOTS: Final = ("default", "world_a", "world_b", "world_c")
DEFAULT_SAVE_SLOT: Final = "default"
SAVE_SLOT_TEMPLATE: Final = "genome_pool_{slot}.pkl"
METRICS_SLOT_TEMPLATE: Final = "genome_pool_{slot}_metricas.csv"

# Nomes legados single-file (fallback em persistence.load).
GENOME_FILE: Final = "genome_pool.pkl"
METRICS_FILE: Final = "genome_pool_metricas.csv"
METRICS_CSV_SUFFIX: Final = "_metricas.csv"
SAVE_FORMAT: Final = "pickle"

# Historico de versoes do savegame:
# v2 save original; v3 versionamento; v4 estado interno como input;
# v5 recorrencia leve; v6 segunda camada oculta; v7 crossover em blocos;
# v8 mutacao em duas escalas; v9 pressao seletiva composta;
# v10 identidade estavel dos individuos;
# v11 estado exato de continuacao:
#     fase do scheduler reprodutivo + estado dos RNGs.
SAVE_VERSION: Final = 11
ARCHITECTURE_VERSION: Final = "mlp-1x25x12-rec"
GENOME_VERSION: Final = "layout-v4"


# 10b. GRAVACAO — exportacao de GIF
# Tecla G alterna; frames capturados apos draw() completo.
RECORDING_FILE: Final = "primordial_soup.gif"
RECORDING_FPS: Final = 15
RECORDING_MAX_FRAMES: Final = 400
RECORDING_SCALE: Final = 0.5
RECORDING_LOOP: Final = 0  # 0 = loop infinito
RECORDING_COLORS: Final = 128  # paleta GIF (<= 256)


# 11. DIAGNOSTICO — telemetria do experimento
PRINT_EVERY_N_TICKS: Final = 100

# Tamanho de cada serie em metrics_history.
METRICS_HISTORY_SIZE: Final = 600

ADVANCED_METRICS: Final = (
    "populacao",
    "hp_medio",
    "maior_tempo_de_vida",
    "geracao_maxima",
    "score_composto_medio",
    "taxa_de_mutacao",
)
METRICS_INTERVAL: Final = 10


# 12. INVARIANTES — o que nao pode ser violado
assert VISION_SIDE % 2 == 1, "A janela de visao deve ter lado impar."
assert TOTAL_LINEAGES >= 3, "O ciclo precisa de pelo menos 3 espécies."
assert POSSIBLE_MOVES == 9, "Vizinhança de Moore tem exatamente 9 células."
assert STAY_STILL_INDEX == POSSIBLE_MOVES // 2, "Centro da vizinhança."
assert 0 <= INITIAL_MUTATION_RATE <= 100, "Taxa de mutação em %."
assert MIN_GENE_VALUE < MAX_GENE_VALUE, "Faixa de genes invertida."
assert INTERNAL_STATE_INPUTS == 4, "Estado interno: 4 entradas."
assert SAVE_VERSION >= 1, "Versão de save inválida."
assert isinstance(ARCHITECTURE_VERSION, str) and ARCHITECTURE_VERSION, (
    "ARCHITECTURE_VERSION deve ser string não vazia."
)
assert isinstance(GENOME_VERSION, str) and GENOME_VERSION, (
    "GENOME_VERSION deve ser string não vazia."
)
assert HIDDEN_ACTIVATION in ("sigmoid", "tanh", "relu"), "Ativação oculta desconhecida."
assert HIDDEN_ACTIVATION_2 in ("sigmoid", "tanh", "relu"), (
    "Ativação da segunda camada oculta desconhecida."
)
assert OUTPUT_ACTIVATION in ("linear", "sigmoid", "tanh", "relu"), (
    "Ativação de saída desconhecida."
)
assert HIDDEN_NEURONS_2 > 0, "A segunda camada oculta deve ter neurônios."

# CROSSOVER_MODE / MUTATION_MODE aceitam grafias EN e PT durante a migração.
assert CROSSOVER_MODE in ("uniform", "blocks", "two_points"), (
    "CROSSOVER_MODE desconhecido."
)
assert BLOCK_SIZE > 0, "BLOCK_SIZE deve ser positivo."
assert MUTATION_MODE in ("surgical", "two_scales"), "MUTATION_MODE desconhecido."
assert 0.0 < LOCAL_SCALE_FRACTION <= 1.0, "LOCAL_SCALE_FRACTION em (0, 1]."
assert 0.0 < GLOBAL_SCALE_FRACTION <= 1.0, "GLOBAL_SCALE_FRACTION em (0, 1]."
assert 0.0 <= GLOBAL_PROBABILITY <= 1.0, "GLOBAL_PROBABILITY em [0, 1]."
assert LOCAL_SCALE_SIGMA > 0.0, "LOCAL_SCALE_SIGMA deve ser positivo."
assert GLOBAL_SCALE_SIGMA > 0.0, "GLOBAL_SCALE_SIGMA deve ser positivo."
assert REPRODUCTION_CRITERION in ("longevity", "composite"), (
    "REPRODUCTION_CRITERION desconhecido."
)
assert LONGEVITY_WEIGHT >= 0.0, "LONGEVITY_WEIGHT não-negativo."
assert EXPLORATION_WEIGHT >= 0.0, "EXPLORATION_WEIGHT não-negativo."
assert INTERACTION_WEIGHT >= 0.0, "INTERACTION_WEIGHT não-negativo."
assert REPRODUCTION_WEIGHT >= 0.0, "REPRODUCTION_WEIGHT não-negativo."

# O mundo sempre tem zonas; "nenhum" não é mais aceito.
assert ENVIRONMENTAL_MODIFIERS == "zonas", (
    "ENVIRONMENTAL_MODIFIERS deve ser 'zonas' (o mundo sempre tem zonas)."
)
assert NUMBER_OF_ZONES >= 0, "NUMBER_OF_ZONES não-negativo."
assert ZONE_RADIUS > 0, "ZONE_RADIUS deve ser positivo."
assert isinstance(HP_EFFECT_IN_ZONE, (int, float)), (
    "HP_EFFECT_IN_ZONE deve ser numérico (positivo = bônus, negativo = dano)."
)
assert MIN_ZONE_HP_EFFECT <= MAX_ZONE_HP_EFFECT, "Faixa ZONE_HP_EFFECT invertida."
assert MIN_ZONE_HP_EFFECT <= HP_EFFECT_IN_ZONE <= MAX_ZONE_HP_EFFECT, (
    "HP_EFFECT_IN_ZONE deve estar em [MIN_ZONE_HP_EFFECT, MAX_ZONE_HP_EFFECT]."
)

assert INSPECTION_PANEL_WIDTH > 0, "INSPECTION_PANEL_WIDTH deve ser positivo."
assert INSPECTION_CELL_HEIGHT > 0, "INSPECTION_CELL_HEIGHT deve ser positivo."
assert HEATMAP_LIMIT > 0.0, "HEATMAP_LIMIT deve ser positivo."
assert CLICK_RADIUS_IN_CELLS >= 0, "CLICK_RADIUS_IN_CELLS não-negativo."

assert CHART_WIDTH > CHART_INNER_PADDING, "CHART_WIDTH muito pequeno."
assert CHART_HEIGHT > CHART_INNER_PADDING, "CHART_HEIGHT muito pequeno."
assert HORIZONTAL_GRID_LINES >= 1, "Grade precisa de ao menos 1 linha horizontal."
assert VERTICAL_GRID_LINES >= 1, "Grade precisa de ao menos 1 linha vertical."
assert CHART_LINE_THICKNESS >= 1, "Espessura da linha deve ser >= 1."

assert len(ADVANCED_METRICS) >= 1, "Pelo menos uma métrica é necessária."
assert INITIAL_POPULATION_PER_LINEAGE >= 2, (
    "INITIAL_POPULATION_PER_LINEAGE deve ser >= 2 (um par é necessário para reproduzir)."
)
assert MAX_POPULATION_PER_LINEAGE > 0, (
    "MAX_POPULATION_PER_LINEAGE deve ser inteiro positivo. O sentinela "
    "'0 = ilimitado' foi removido: tornava o loop de reprodução não-terminante."
)
assert MAX_POPULATION_PER_LINEAGE >= INITIAL_POPULATION_PER_LINEAGE, (
    "MAX_POPULATION_PER_LINEAGE deve ser >= INITIAL_POPULATION_PER_LINEAGE. "
    "Um teto abaixo da população inicial encolheria a linhagem no primeiro tick."
)
assert MAX_POPULATION_PER_LINEAGE >= OFFSPRING_PER_PAIR, (
    "MAX_POPULATION_PER_LINEAGE deve ser >= OFFSPRING_PER_PAIR. Um teto "
    "menor que um evento reprodutivo tornaria a reprodução impossível."
)
assert REPRODUCTION_ATTEMPTS_DIVISOR >= 1, (
    "REPRODUCTION_ATTEMPTS_DIVISOR deve ser >= 1 (0 dividiria por zero; "
    "1 significaria tantas tentativas quantas criaturas vivas)."
)
assert REPRODUCTION_MIN_AGE >= 0, "REPRODUCTION_MIN_AGE deve ser >= 0."
assert REPRODUCTION_HP_GATE > 0, (
    "REPRODUCTION_HP_GATE deve ser positivo. Uma criatura só é pai "
    "elegível se seu HP for ESTRITAMENTE MENOR que este valor."
)
assert REPRODUCTION_HP_GATE <= INITIAL_HP, (
    "REPRODUCTION_HP_GATE deve ser <= INITIAL_HP. Um portão acima de "
    "INITIAL_HP tornaria todo recém-nascido elegível desde o nascimento, "
    "anulando o propósito do portão de HP."
)
assert REPRODUCTION_INTERVAL >= 1, (
    "REPRODUCTION_INTERVAL deve ser >= 1. Com 1, o turno rotaciona a cada "
    "tick; com N, a cada N ticks. O valor 0 congelaria a reprodução."
)
assert REPRODUCTION_MIN_SCORE >= 0.0, (
    "REPRODUCTION_MIN_SCORE deve ser >= 0.0. O score composto é "
    "normalizado por linhagem e não-negativo por construção."
)
assert REPRODUCTION_MIN_ENCOUNTERS >= 0, (
    "REPRODUCTION_MIN_ENCOUNTERS deve ser >= 0. Encontros são um "
    "contador não-negativo (um tick com qualquer outra linhagem na mesma célula)."
)
assert METRICS_INTERVAL >= 1, "METRICS_INTERVAL deve ser >= 1."
assert METRICS_HISTORY_SIZE >= 2, "Histórico de métricas muito curto."

assert METRICS_CSV_SUFFIX == "_metricas.csv", (
    "METRICS_CSV_SUFFIX faz parte do contrato de compatibilidade "
    "com a base PT canônica; deve permanecer '_metricas.csv'."
)

# --- invariantes multi-slot --------------------------------------------
# Nomes de slot devem ser seguros para filename: não vazios e sem
# separadores de caminho. Templates devem conter o placeholder {slot}.
assert len(SAVE_SLOTS) >= 1, "SAVE_SLOTS deve conter ao menos um slot."
assert all(isinstance(s, str) and s for s in SAVE_SLOTS), (
    "Entradas de SAVE_SLOTS devem ser strings não vazias."
)
assert all("/" not in s and "\\" not in s for s in SAVE_SLOTS), (
    "Entradas de SAVE_SLOTS não devem conter separadores de caminho."
)
assert len(set(SAVE_SLOTS)) == len(SAVE_SLOTS), (
    "Entradas de SAVE_SLOTS devem ser únicas."
)
assert DEFAULT_SAVE_SLOT in SAVE_SLOTS, "DEFAULT_SAVE_SLOT deve estar em SAVE_SLOTS."
assert "{slot}" in SAVE_SLOT_TEMPLATE, (
    "SAVE_SLOT_TEMPLATE deve conter o placeholder {slot}."
)
assert "{slot}" in METRICS_SLOT_TEMPLATE, (
    "METRICS_SLOT_TEMPLATE deve conter o placeholder {slot}."
)

# --- invariantes de gravação -------------------------------------------
# RECORDING_SCALE reduz cada frame antes de bufferizar (maior alavanca de
# memória). RECORDING_COLORS deve ficar no limite da paleta GIF 8-bit.
assert isinstance(RECORDING_FILE, str) and RECORDING_FILE, (
    "RECORDING_FILE deve ser string não vazia."
)
assert RECORDING_FPS > 0, "RECORDING_FPS deve ser positivo."
assert RECORDING_MAX_FRAMES > 0, "RECORDING_MAX_FRAMES deve ser positivo."
assert 0.0 < RECORDING_SCALE <= 1.0, "RECORDING_SCALE deve estar em (0, 1]."
assert 0 <= RECORDING_LOOP, "RECORDING_LOOP deve ser >= 0 (0 = infinito)."
assert 2 <= RECORDING_COLORS <= 256, "RECORDING_COLORS deve estar em [2, 256]."

# --- consistência do layout do genoma ----------------------------------
# Documenta o layout pretendido e protege contra edições futuras que
# adicionem um componente a GENOME_SIZE sem adicioná-lo aqui (ou vice-versa).
assert GENOME_SIZE == (
    INPUT_HIDDEN_WEIGHTS
    + HIDDEN1_HIDDEN2_WEIGHTS
    + HIDDEN2_OUTPUT_WEIGHTS
    + HIDDEN_BIASES
    + HIDDEN_BIASES_2
    + RECURRENCE_WEIGHTS
), "GENOME_SIZE é inconsistente com seus componentes."

# --- invariantes de critérios de inspeção / filtro de linhagem ---------
assert len(CRITERIA_ORDER) >= 1, "CRITERIA_ORDER não deve ser vazio."
assert len(set(CRITERIA_ORDER)) == len(CRITERIA_ORDER), (
    "Entradas de CRITERIA_ORDER devem ser únicas."
)
assert CRITERION_MOST_EVOLVED in CRITERIA_ORDER, (
    "CRITERION_MOST_EVOLVED deve fazer parte de CRITERIA_ORDER."
)
assert LINEAGE_FILTER_ALL in LINEAGE_FILTER_ORDER, (
    "LINEAGE_FILTER_ALL deve fazer parte de LINEAGE_FILTER_ORDER."
)
assert len(set(LINEAGE_FILTER_ORDER)) == len(LINEAGE_FILTER_ORDER), (
    "Entradas de LINEAGE_FILTER_ORDER devem ser únicas."
)
