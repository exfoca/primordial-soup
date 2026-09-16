# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from typing import Final

from ._version import __version__

# 0. IDENTIDADE
WORLD_NAME: Final = "Primordial Soup"
WORLD_VERSION: Final = __version__
RANDOM_SEED: Final = None


# 1. O MUNDO — geometria e topologia
# Usuario declara a tela; escala, mundo e janela sao derivados em layout.py.
# Painel de inspecao tem largura fixa a direita. Sem resize em runtime.
SCREEN_WIDTH: Final = 1920
SCREEN_HEIGHT: Final = 1080

TARGET_PIXEL_SCALE: Final = 4

# Zoom de apresentacao (camera). Nao pertence a RuntimeRules: e
# view-only, nao persiste em checkpoint, nao e HOT, nao altera
# PIXEL_SCALE nem layout.LAYOUT.
MIN_ZOOM: Final = 1.0
MAX_ZOOM: Final = 8.0
ZOOM_STEP: Final = 1.20

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
MAX_POPULATION_PER_LINEAGE: Final = 350


# 4. PERCEPCAO — o que uma criatura ve
VISION_RADIUS: Final = 5
VISION_SIDE: Final = 2 * VISION_RADIUS + 1
VISION_CHANNELS: Final = TOTAL_LINEAGES
VISION_INPUTS: Final = VISION_SIDE**2 * VISION_CHANNELS

INTERNAL_STATE_INPUTS: Final = 4
NETWORK_INPUTS: Final = VISION_INPUTS + INTERNAL_STATE_INPUTS

# HOT default: effective value lives in RuntimeRules.low_hp_threshold.
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
# WARM/static: defines founders, newborns, Heal all and normalization.
INITIAL_HP: Final = 10_000
BASE_DECAY_PER_TICK: Final = 1
# HOT default: effective decision bias lives in RuntimeRules.
STAY_STILL_IMPULSE: Final = 1

PREDATION_TRANSFER: Final = 100
DAMAGE_PER_OWN_OVERCROWDING: Final = 10

# HOT default: effective mortality threshold lives in RuntimeRules.
DIE_WHEN_HP_LESS_OR_EQUAL: Final = 0

MIN_LOW_HP_THRESHOLD: Final = 0
MAX_LOW_HP_THRESHOLD: Final = INITIAL_HP

MIN_DEATH_HP_THRESHOLD: Final = 0
MAX_DEATH_HP_THRESHOLD: Final = INITIAL_HP


# 6b. MODIFICADORES AMBIENTAIS — heterogeneidade geografica
# Valores fazem parte do contrato de savegame.
ENVIRONMENTAL_MODIFIERS: Final = "zonas"
NUMBER_OF_ZONES: Final = 8
ZONE_RADIUS: Final = 27
HP_EFFECT_IN_ZONE: Final = 5


# 6c. NINHOS — geometria estatica por linhagem
# Ha exatamente um ninho por linhagem. A posicao no tuple de
# state.nests corresponde ao indice canonico da linhagem (0 -> R,
# 1 -> G, 2 -> B), definido por cfg.LINEAGES.
#
# Estas constantes sao estaticas: nao entram em RuntimeRules, nao
# aparecem no painel Configuration e nao sao persistidas.
#
# NEST_RADIUS define o disco funcional de protecao. O limite e
# inclusivo: distancia toroidal quadratica <= radius^2 pertence ao
# ninho. NEST_SPAWN_RADIUS define a vizinhanca discreta em torno do
# centro usada para posicionar descendentes.
NESTS_PER_LINEAGE: Final = 1
NEST_RADIUS: Final = 20
NEST_SPAWN_RADIUS: Final = 1

# Teto de candidatos sorteados por linhagem durante generate_nests().
# Esgotar o teto e erro de configuracao do mundo (zonas grandes demais,
# raio grande demais, mundo pequeno demais): generate_nests() falha
# ruidosamente em vez de retornar geometria incompleta ou sobreposta.
MAX_NEST_PLACEMENT_ATTEMPTS: Final = 10_000


# 7. SELECAO — quem se torna pai
# config.py contem os defaults e dominios canonicos. Para parametros
# ja promovidos, o valor efetivo durante a execucao vive em RuntimeRules.
REPRODUCTION_CRITERIA: Final = (
    "composite",
    "longevity",
)
REPRODUCTION_CRITERION: Final = "composite"
LONGEVITY_WEIGHT: Final = 0.3
EXPLORATION_WEIGHT: Final = 0.3
INTERACTION_WEIGHT: Final = 0.3
REPRODUCTION_WEIGHT: Final = 0.3

REPRODUCTIVE_POOL_FRACTION: Final = 0.9

# Contratos estruturais fixos: o algoritmo materializa exatamente dois
# filhos complementares a partir de exatamente dois pais.
OFFSPRING_PER_PAIR: Final = 2
REPRODUCE_IN_PAIRS: Final = True

# Default de bootstrap. O hot path usa
# RuntimeRules.reproduction_attempts_divisor.
REPRODUCTION_ATTEMPTS_DIVISOR: Final = 50

# Portao 1: idade minima.
REPRODUCTION_MIN_AGE: Final = 5000

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
# config.py contem os defaults canonicos. CROSSOVER_MODE,
# CROSSOVER_PROBABILITY e BLOCK_SIZE sao defaults de bootstrap; os valores
# efetivos durante a execucao vivem em RuntimeRules. MUTATION_MODE e toda a
# parametrizacao comportamental de two_scales tambem sao runtime.
CROSSOVER_MODES: Final = (
    "blocks",
    "uniform",
    "two_points",
)
CROSSOVER_MODE: Final = "blocks"
BLOCK_SIZE: Final = 64
CROSSOVER_PROBABILITY: Final = 0.5

MIN_CROSSOVER_PROBABILITY: Final = 0.0
MAX_CROSSOVER_PROBABILITY: Final = 1.0
MIN_BLOCK_SIZE: Final = 1
MAX_BLOCK_SIZE: Final = GENOME_SIZE

MUTATION_MODES: Final = (
    "two_scales",
    "surgical",
)
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

MIN_GLOBAL_PROBABILITY: Final = 0
MAX_GLOBAL_PROBABILITY: Final = 100
MIN_GLOBAL_SCALE_FRACTION: Final = 1
MAX_GLOBAL_SCALE_FRACTION: Final = 100

MIN_MUTATION_SIGMA: Final = 0.01
MAX_MUTATION_SIGMA: Final = MAX_GENE_VALUE - MIN_GENE_VALUE

# Limites runtime das regras ecologicas.
# Base decay aceita 0. Predation transfer e overcrowding tem minimo
# 10: zerar essas regras quebraria o contrato do resolver.
MIN_BASE_DECAY_PER_TICK: Final = 0
MAX_BASE_DECAY_PER_TICK: Final = 10_000

MIN_PREDATION_TRANSFER: Final = 10
MAX_PREDATION_TRANSFER: Final = 200
PREDATION_TRANSFER_STEP: Final = 10

MIN_DAMAGE_PER_OWN_OVERCROWDING: Final = 10
MAX_DAMAGE_PER_OWN_OVERCROWDING: Final = 200
DAMAGE_PER_OWN_OVERCROWDING_STEP: Final = 10

# Limites runtime das regras reprodutivas (v13). Escolhas:
#   interval >= 1: 0 congelaria a reproducao.
#   hp_gate <= INITIAL_HP: preserva a invariante do projeto
#   (HP gate <= INITIAL_HP); com gate > INITIAL_HP todo recem-nascido
#   ja seria elegivel, anulando o portao.
#   hp_gate >= 1: com gate 0 nenhum bicho vivo (HP > 0) seria elegivel.
MIN_REPRODUCTION_INTERVAL: Final = 1
MAX_REPRODUCTION_INTERVAL: Final = 100_000

MIN_REPRODUCTION_MIN_AGE: Final = 0
MAX_REPRODUCTION_MIN_AGE: Final = 1_000_000

MIN_REPRODUCTION_HP_GATE: Final = 1
MAX_REPRODUCTION_HP_GATE: Final = INITIAL_HP

MIN_REPRODUCTION_MIN_ENCOUNTERS: Final = 0
MAX_REPRODUCTION_MIN_ENCOUNTERS: Final = 1_000_000

MIN_REPRODUCTION_PARENT_HP_BONUS: Final = 0
MAX_REPRODUCTION_PARENT_HP_BONUS: Final = INITIAL_HP

# Limites runtime do score de selecao (v14). Pesos nao sao
# probabilidades e nao precisam somar 1.0. Cada componente normalizado
# fica aproximadamente em [0, 1], portanto quatro pesos no teto 5.0
# produzem score teorico maximo 20.0.
MIN_SELECTION_WEIGHT: Final = 0.0
MAX_SELECTION_WEIGHT: Final = 5.0
MIN_REPRODUCTION_MIN_SCORE: Final = 0.0
MAX_REPRODUCTION_MIN_SCORE: Final = 4.0 * MAX_SELECTION_WEIGHT

# Limites runtime da pressao reprodutiva (v16).
MIN_REPRODUCTION_POOL_FRACTION: Final = 0.01
MAX_REPRODUCTION_POOL_FRACTION: Final = 1.0

MIN_REPRODUCTION_ATTEMPTS_DIVISOR: Final = 1
MAX_REPRODUCTION_ATTEMPTS_DIVISOR: Final = MAX_POPULATION_PER_LINEAGE

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

OVERLAP_POLICY: Final = "max"

# Paleta da UI.
HUD_BG_COLOR: Final = (8, 10, 14)
HUD_BORDER_COLOR: Final = (60, 70, 85)
HUD_TEXT_COLOR: Final = (220, 230, 240)
HUD_TEXT_SECONDARY_COLOR: Final = (140, 155, 175)
HUD_TITLE_COLOR: Final = (255, 215, 0)

# Telemetry HUD (floating, canto superior esquerdo do mundo).
HUD_MARGIN: Final = 8
HUD_PADDING: Final = 10
HUD_TELEMETRY_WIDTH: Final = 400
HUD_OVERLAY_ALPHA: Final = 0

HUD_SECTION_GAP: Final = 8
HUD_DIVIDER_COLOR: Final = (40, 48, 60)
HUD_KEY_BG_COLOR: Final = (18, 21, 27)

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

# Rastro do bicho inspecionado (nao persistido, nao resetado por
# reset_counters). TRAIL_MAX_LENGTH limita o deque.
TRAIL_MAX_LENGTH: Final = 2000
TRAIL_COLOR_OLD: Final = 40
TRAIL_COLOR_NEW: Final = 240

# Retencao temporal dos death markers, em simulation ticks.
# Coincide numericamente com TRAIL_MAX_LENGTH, mas tem semantica
# independente e nao deve ser acoplada ao tamanho do trail.
DEATH_MARKER_TTL_TICKS: Final = 2000

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
# v12: primeira persistencia de regras ecologicas runtime;
#     contrato posteriormente substituido por v21.
# v13 runtime reproduction rules:
#     interval, minimum age, HP gate, minimum encounters,
#     parent HP reward.
# v14 runtime selection-score rules:
#     minimum score, longevity weight, exploration weight,
#     interaction weight, reproduction weight.
# v15 runtime selection criterion:
#     reproduction_criterion.
# v16 runtime reproduction-pressure rules:
#     reproduction_pool_fraction, reproduction_attempts_divisor.
# v17 runtime genetic operator modes:
#     crossover_mode, mutation_mode.
# v18 runtime crossover tuning:
#     crossover_probability, block_size.
# v19 runtime two-scale mutation tuning:
#     local_scale_sigma, global_probability, global_scale_fraction,
#     global_scale_sigma.
# v20 runtime behavior/lifecycle:
#     low_hp_threshold, stay_still_impulse, death_hp_threshold.
# v21: contrato ecologico atual + geometria persistente de nests:
#     base_decay_per_tick, predation_transfer,
#     damage_per_own_overcrowding, nests.
#     Incompativel com v20.
# v22: persistencia dos centros canonicos das zonas;
#     mascara e centros passam a ser validados como uma
#     geometria unica. Incompativel com v21.
# v23: historico recente de mortes persistente; DeathSnapshot
#     completo com agent/genome; death markers clicaveis preservados
#     entre save/load. Incompativel com v22.
SAVE_VERSION: Final = 23
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


# 10c. AUDIO — feedback sonoro da interface
# Somente apresentacao grafica. Nao altera o estado da simulacao.
SOUND_VOLUME_MUSIC: Final = 0.1
SOUND_VOLUME_SFX: Final = 1.0


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

assert CROSSOVER_MODE in CROSSOVER_MODES, "CROSSOVER_MODE desconhecido."
assert (
    MIN_CROSSOVER_PROBABILITY <= CROSSOVER_PROBABILITY <= MAX_CROSSOVER_PROBABILITY
), "CROSSOVER_PROBABILITY fora da faixa runtime."
assert MIN_BLOCK_SIZE <= BLOCK_SIZE <= MAX_BLOCK_SIZE, (
    "BLOCK_SIZE fora da faixa runtime."
)
assert MUTATION_MODE in MUTATION_MODES, "MUTATION_MODE desconhecido."
assert 0.0 < LOCAL_SCALE_FRACTION <= 1.0, "LOCAL_SCALE_FRACTION em (0, 1]."
assert (
    MIN_GLOBAL_SCALE_FRACTION
    <= int(GLOBAL_SCALE_FRACTION * 100)
    <= MAX_GLOBAL_SCALE_FRACTION
), "GLOBAL_SCALE_FRACTION fora da faixa runtime."
assert (
    MIN_GLOBAL_PROBABILITY <= int(GLOBAL_PROBABILITY * 100) <= MAX_GLOBAL_PROBABILITY
), "GLOBAL_PROBABILITY fora da faixa runtime."
assert MIN_MUTATION_SIGMA <= LOCAL_SCALE_SIGMA <= MAX_MUTATION_SIGMA, (
    "LOCAL_SCALE_SIGMA fora da faixa runtime."
)
assert MIN_MUTATION_SIGMA <= GLOBAL_SCALE_SIGMA <= MAX_MUTATION_SIGMA, (
    "GLOBAL_SCALE_SIGMA fora da faixa runtime."
)
assert REPRODUCTION_CRITERION in REPRODUCTION_CRITERIA, (
    "REPRODUCTION_CRITERION desconhecido."
)
assert MIN_SELECTION_WEIGHT <= MAX_SELECTION_WEIGHT, (
    "Faixa de pesos de selecao invertida."
)
assert MIN_REPRODUCTION_MIN_SCORE <= MAX_REPRODUCTION_MIN_SCORE, (
    "Faixa de score minimo reprodutivo invertida."
)
assert MIN_SELECTION_WEIGHT <= LONGEVITY_WEIGHT <= MAX_SELECTION_WEIGHT, (
    "LONGEVITY_WEIGHT fora da faixa runtime."
)
assert MIN_SELECTION_WEIGHT <= EXPLORATION_WEIGHT <= MAX_SELECTION_WEIGHT, (
    "EXPLORATION_WEIGHT fora da faixa runtime."
)
assert MIN_SELECTION_WEIGHT <= INTERACTION_WEIGHT <= MAX_SELECTION_WEIGHT, (
    "INTERACTION_WEIGHT fora da faixa runtime."
)
assert MIN_SELECTION_WEIGHT <= REPRODUCTION_WEIGHT <= MAX_SELECTION_WEIGHT, (
    "REPRODUCTION_WEIGHT fora da faixa runtime."
)

# O mundo sempre tem zonas; "nenhum" não é mais aceito.
assert ENVIRONMENTAL_MODIFIERS == "zonas", (
    "ENVIRONMENTAL_MODIFIERS deve ser 'zonas' (o mundo sempre tem zonas)."
)
assert NUMBER_OF_ZONES >= 0, "NUMBER_OF_ZONES não-negativo."
assert ZONE_RADIUS > 0, "ZONE_RADIUS deve ser positivo."

assert NESTS_PER_LINEAGE == 1, (
    "NESTS_PER_LINEAGE == 1. A representacao de state.nests como "
    "tuple[tuple[int, int], ...] de exatamente TOTAL_LINEAGES "
    "centros depende desta invariante. Uma lista de ninhos por "
    "linhagem exigiria repensar o schema."
)
assert NEST_RADIUS > 0, "NEST_RADIUS deve ser positivo."
assert NEST_SPAWN_RADIUS >= 0 and NEST_SPAWN_RADIUS <= NEST_RADIUS, (
    "NEST_SPAWN_RADIUS em [0, NEST_RADIUS]: spawn deve caber no "
    "disco funcional do ninho."
)
assert MAX_NEST_PLACEMENT_ATTEMPTS > 0, (
    "MAX_NEST_PLACEMENT_ATTEMPTS deve ser positivo: um teto zero "
    "impediria generate_nests() de sequer tentar."
)
# Sanidade dimensional: MIN_WORLD_* estao na mesma unidade logica de
# layout.LAYOUT.world_width/world_height (celulas do mundo), conforme
# layout._derive(). Um disco que envolva o toro em qualquer eixo
# degenera a semantica de distancia toroidal (todo ponto ficaria a
# <= radius de qualquer centro). Este e um limite conservador.
assert 2 * NEST_RADIUS < MIN_WORLD_WIDTH, (
    "2 * NEST_RADIUS deve caber na largura minima do mundo; caso "
    "contrario o disco envolve o toro em X."
)
assert 2 * NEST_RADIUS < MIN_WORLD_HEIGHT, (
    "2 * NEST_RADIUS deve caber na altura minima do mundo; caso "
    "contrario o disco envolve o toro em Y."
)
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
assert OFFSPRING_PER_PAIR == 2, (
    "A implementação atual materializa exatamente "
    "dois filhos complementares por evento."
)
assert REPRODUCE_IN_PAIRS is True, (
    "A implementação atual seleciona exatamente dois pais por evento."
)
assert (
    MIN_REPRODUCTION_POOL_FRACTION
    <= REPRODUCTIVE_POOL_FRACTION
    <= MAX_REPRODUCTION_POOL_FRACTION
), "REPRODUCTIVE_POOL_FRACTION fora da faixa runtime."
assert (
    MIN_REPRODUCTION_ATTEMPTS_DIVISOR
    <= REPRODUCTION_ATTEMPTS_DIVISOR
    <= MAX_REPRODUCTION_ATTEMPTS_DIVISOR
), "REPRODUCTION_ATTEMPTS_DIVISOR fora da faixa runtime."
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
assert (
    MIN_REPRODUCTION_MIN_SCORE <= REPRODUCTION_MIN_SCORE <= MAX_REPRODUCTION_MIN_SCORE
), "REPRODUCTION_MIN_SCORE fora da faixa runtime."
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

# --- invariantes de audio ----------------------------------------------
assert 0.0 <= SOUND_VOLUME_MUSIC <= 1.0, "SOUND_VOLUME_MUSIC deve estar em [0.0, 1.0]."
assert 0.0 <= SOUND_VOLUME_SFX <= 1.0, "SOUND_VOLUME_SFX deve estar em [0.0, 1.0]."

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
