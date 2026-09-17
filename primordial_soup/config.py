# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from typing import Final

from ._version import __version__
from .config_loader import load_config
from .config_source import CONFIG_PATH
from .model_contract import (
    INTERNAL_STATE_INPUTS,
    MAX_GENE_VALUE,
    MIN_GENE_VALUE,
    POSSIBLE_MOVES,
    STAY_STILL_INDEX,
    VISION_CHANNELS,
    derive_neural_layout,
)

CONFIG_SNAPSHOT: Final = load_config(CONFIG_PATH)
_NON_HOT: Final = CONFIG_SNAPSHOT.non_hot



# Defaults HOT nao sao espelhados intencionalmente como constantes cfg.*.
# O baseline declarativo HOT vive em CONFIG_SNAPSHOT.hot e e materializado/
# validado por runtime_rules.default_runtime_rules().


# 0. IDENTIDADE
WORLD_NAME: Final = "Primordial Soup"
WORLD_VERSION: Final = __version__

# 1. O MUNDO — geometria e topologia
# Usuario declara a tela; escala, mundo e janela sao derivados em layout.py.
# Painel de inspecao tem largura fixa a direita. Sem resize em runtime.
SCREEN_WIDTH: Final = _NON_HOT.screen_width
SCREEN_HEIGHT: Final = _NON_HOT.screen_height

TARGET_PIXEL_SCALE: Final = _NON_HOT.target_pixel_scale

# Zoom de apresentacao (camera). Nao pertence a RuntimeRules: e
# view-only, nao persiste em checkpoint, nao e HOT, nao altera
# PIXEL_SCALE nem layout.LAYOUT.
MIN_ZOOM: Final = 1.0
MAX_ZOOM: Final = 8.0
ZOOM_STEP: Final = _NON_HOT.zoom_step

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
INITIAL_POPULATION_PER_LINEAGE: Final = _NON_HOT.initial_population_per_lineage

# Teto por linhagem. Inteiro positivo.
MAX_POPULATION_PER_LINEAGE: Final = _NON_HOT.max_population_per_lineage


# 4. PERCEPCAO — o que uma criatura ve
VISION_RADIUS: Final = _NON_HOT.vision_radius


# 5. COGNIÇÃO — arquitetura do cérebro
HIDDEN_NEURONS: Final = _NON_HOT.hidden_neurons
HIDDEN_NEURONS_2: Final = _NON_HOT.hidden_neurons_2

HIDDEN_ACTIVATION: Final = _NON_HOT.hidden_activation
HIDDEN_ACTIVATION_2: Final = _NON_HOT.hidden_activation_2
OUTPUT_ACTIVATION: Final = _NON_HOT.output_activation

_NEURAL_LAYOUT: Final = derive_neural_layout(
    vision_radius=VISION_RADIUS,
    hidden_neurons=HIDDEN_NEURONS,
    hidden_neurons_2=HIDDEN_NEURONS_2,
)

VISION_SIDE: Final = _NEURAL_LAYOUT.vision_side
VISION_INPUTS: Final = _NEURAL_LAYOUT.vision_inputs
NETWORK_INPUTS: Final = _NEURAL_LAYOUT.network_inputs
INPUT_HIDDEN_WEIGHTS: Final = _NEURAL_LAYOUT.input_hidden_weights
HIDDEN1_HIDDEN2_WEIGHTS: Final = _NEURAL_LAYOUT.hidden1_hidden2_weights
HIDDEN2_OUTPUT_WEIGHTS: Final = _NEURAL_LAYOUT.hidden2_output_weights
HIDDEN_BIASES: Final = _NEURAL_LAYOUT.hidden_biases
HIDDEN_BIASES_2: Final = _NEURAL_LAYOUT.hidden_biases_2
RECURRENCE_WEIGHTS: Final = _NEURAL_LAYOUT.recurrence_weights
GENOME_SIZE: Final = _NEURAL_LAYOUT.genome_size

if TOTAL_LINEAGES != VISION_CHANNELS:
    raise RuntimeError(
        "TOTAL_LINEAGES deve coincidir com VISION_CHANNELS no modelo atual."
    )


# 6. METABOLISMO — vida, dano e morte
# NON-HOT: define fundadores, recém-nascidos, Heal all e a base de normalização.
INITIAL_HP: Final = _NON_HOT.initial_hp



# 6b. ZONAS AMBIENTAIS — heterogeneidade geografica
NUMBER_OF_ZONES: Final = _NON_HOT.number_of_zones
ZONE_RADIUS: Final = _NON_HOT.zone_radius


# 6c. NINHOS — geometria estatica por linhagem
# Ha exatamente um ninho por linhagem. A posicao no tuple de
# state.nests corresponde ao indice canonico da linhagem (0 -> R,
# 1 -> G, 2 -> B), definido por cfg.LINEAGES.
#
# Estes parametros de geometria sao NON-HOT e nao entram em RuntimeRules.
# Os centros dos ninhos pertencem ao checkpoint; NEST_RADIUS e
# NEST_SPAWN_RADIUS participam da metadata NON-HOT de compatibilidade.
#
# NEST_RADIUS define o disco funcional de protecao. O limite e
# inclusivo: distancia toroidal quadratica <= radius^2 pertence ao
# ninho. NEST_SPAWN_RADIUS define a vizinhanca discreta em torno do
# centro usada para posicionar descendentes.
NESTS_PER_LINEAGE: Final = 1
NEST_RADIUS: Final = _NON_HOT.nest_radius
NEST_SPAWN_RADIUS: Final = _NON_HOT.nest_spawn_radius

# Teto de candidatos sorteados por linhagem durante generate_nests().
# Esgotar o teto e erro de configuracao do mundo (zonas grandes demais,
# raio grande demais, mundo pequeno demais): generate_nests() falha
# ruidosamente em vez de retornar geometria incompleta ou sobreposta.
MAX_NEST_PLACEMENT_ATTEMPTS: Final = _NON_HOT.max_nest_placement_attempts


# 7. SELECAO — contratos estruturais de reproducao
OFFSPRING_PER_PAIR: Final = 2
REPRODUCE_IN_PAIRS: Final = True


# 8. HERANCA — contrato estrutural genetico
# Os limites de genes vem da autoridade neutra model_contract.


# 9. INTERFACE — a janela para o mundo
TARGET_FPS: Final = _NON_HOT.target_fps
WINDOW_TITLE: Final = WORLD_NAME
HUD_FONT: Final = _NON_HOT.hud_font


# Paleta da UI.
HUD_BG_COLOR: Final = _NON_HOT.hud_bg_color
HUD_BORDER_COLOR: Final = _NON_HOT.hud_border_color
HUD_TEXT_COLOR: Final = _NON_HOT.hud_text_color
HUD_TEXT_SECONDARY_COLOR: Final = _NON_HOT.hud_text_secondary_color
HUD_TITLE_COLOR: Final = _NON_HOT.hud_title_color

# Telemetry HUD (floating, canto superior esquerdo do mundo).
HUD_MARGIN: Final = _NON_HOT.hud_margin
HUD_PADDING: Final = _NON_HOT.hud_padding
HUD_TELEMETRY_WIDTH: Final = _NON_HOT.hud_telemetry_width
HUD_OVERLAY_ALPHA: Final = _NON_HOT.hud_overlay_alpha

HUD_SECTION_GAP: Final = _NON_HOT.hud_section_gap
HUD_DIVIDER_COLOR: Final = _NON_HOT.hud_divider_color
HUD_KEY_BG_COLOR: Final = _NON_HOT.hud_key_bg_color

# Gráficos.
CHART_INNER_PADDING: Final = _NON_HOT.chart_inner_padding

CHART_BG_COLOR: Final = _NON_HOT.chart_bg_color
CHART_GRID_COLOR: Final = _NON_HOT.chart_grid_color
CHART_AXIS_COLOR: Final = _NON_HOT.chart_axis_color
CHART_LABEL_COLOR: Final = _NON_HOT.chart_label_color
CHART_TITLE_COLOR: Final = _NON_HOT.chart_title_color

HORIZONTAL_GRID_LINES: Final = _NON_HOT.horizontal_grid_lines
VERTICAL_GRID_LINES: Final = _NON_HOT.vertical_grid_lines

CHART_LINE_THICKNESS: Final = _NON_HOT.chart_line_thickness

# Rastro do bicho inspecionado (nao persistido, nao resetado por
# reset_counters). TRAIL_MAX_LENGTH limita o deque.
TRAIL_MAX_LENGTH: Final = _NON_HOT.trail_max_length
TRAIL_COLOR_OLD: Final = _NON_HOT.trail_color_old
TRAIL_COLOR_NEW: Final = _NON_HOT.trail_color_new

# Retencao temporal dos death markers, em simulation ticks.
# Coincide numericamente com TRAIL_MAX_LENGTH, mas tem semantica
# independente e nao deve ser acoplada ao tamanho do trail.
DEATH_MARKER_TTL_TICKS: Final = _NON_HOT.death_marker_ttl_ticks

INSPECTION_PANEL_WIDTH: Final = _NON_HOT.inspection_panel_width
INSPECTION_CELL_HEIGHT: Final = _NON_HOT.inspection_cell_height

CLICK_RADIUS_IN_CELLS: Final = _NON_HOT.click_radius_in_cells

PANEL_BG_COLOR: Final = _NON_HOT.panel_bg_color
PANEL_BORDER_COLOR: Final = _NON_HOT.panel_border_color
PANEL_TEXT_COLOR: Final = _NON_HOT.panel_text_color
PANEL_SECONDARY_TEXT_COLOR: Final = _NON_HOT.panel_secondary_text_color
INSPECTION_HIGHLIGHT_COLOR: Final = _NON_HOT.inspection_highlight_color

HEATMAP_LIMIT: Final = _NON_HOT.heatmap_limit


# 10. PERSISTENCIA
# Sufixo CSV faz parte do contrato do formato de savegame.
# Lista declarativa de slots. Edite SAVE_SLOTS no .env e reinicie.
SAVE_SLOTS: Final = _NON_HOT.save_slots
DEFAULT_SAVE_SLOT: Final = _NON_HOT.default_save_slot
SAVE_SLOT_TEMPLATE: Final = "genome_pool_{slot}.pkl"
METRICS_SLOT_TEMPLATE: Final = "genome_pool_{slot}_metricas.csv"

METRICS_CSV_SUFFIX: Final = "_metricas.csv"

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
# v24: snapshot de compatibilidade dos NON-HOT que afetam continuacao de
#     checkpoint. Incompativel com v23.
# v25: limpeza canonica do contrato de persistencia; removidos aliases
#     historicos de chaves, caminho alternativo implicito de arquivo unico e payloads
#     redundantes nao consumidos pelo loader. Incompativel com v24.
SAVE_VERSION: Final = 25
ARCHITECTURE_VERSION: Final = "mlp-2hidden-h1rec-v1"
GENOME_VERSION: Final = "layout-v4"


# 10b. GRAVACAO — exportacao de GIF
# Tecla G alterna; frames capturados apos draw() completo.
RECORDING_FILE: Final = _NON_HOT.recording_file
RECORDING_FPS: Final = _NON_HOT.recording_fps
RECORDING_MAX_FRAMES: Final = _NON_HOT.recording_max_frames
RECORDING_SCALE: Final = _NON_HOT.recording_scale
RECORDING_LOOP: Final = _NON_HOT.recording_loop
RECORDING_COLORS: Final = _NON_HOT.recording_colors


# 10c. AUDIO — feedback sonoro da interface
# Somente apresentacao grafica. Nao altera o estado da simulacao.
SOUND_VOLUME_MUSIC: Final = _NON_HOT.sound_volume_music
SOUND_VOLUME_SFX: Final = _NON_HOT.sound_volume_sfx


# 11. DIAGNOSTICO — telemetria do experimento
PRINT_EVERY_N_TICKS: Final = _NON_HOT.print_every_n_ticks

# Tamanho de cada serie em metrics_history.
METRICS_HISTORY_SIZE: Final = _NON_HOT.metrics_history_size

ADVANCED_METRICS: Final = (
    "populacao",
    "hp_medio",
    "maior_tempo_de_vida",
    "geracao_maxima",
    "score_composto_medio",
    "taxa_de_mutacao",
)
METRICS_INTERVAL: Final = _NON_HOT.metrics_interval


# 12. INVARIANTES — o que nao pode ser violado
assert VISION_SIDE % 2 == 1, "A janela de visao deve ter lado impar."
assert TOTAL_LINEAGES >= 3, "O ciclo precisa de pelo menos 3 especies."
assert POSSIBLE_MOVES == 9, "Vizinhanca de Moore tem exatamente 9 celulas."
assert STAY_STILL_INDEX == POSSIBLE_MOVES // 2, "Centro da vizinhanca."
assert MIN_GENE_VALUE < MAX_GENE_VALUE, "Faixa de genes invertida."
assert INTERNAL_STATE_INPUTS == 4, "Estado interno: 4 entradas."
assert SAVE_VERSION >= 1, "Versao de save invalida."
assert isinstance(ARCHITECTURE_VERSION, str) and ARCHITECTURE_VERSION, (
    "ARCHITECTURE_VERSION deve ser string nao vazia."
)
assert isinstance(GENOME_VERSION, str) and GENOME_VERSION, (
    "GENOME_VERSION deve ser string nao vazia."
)
assert NESTS_PER_LINEAGE == 1, (
    "NESTS_PER_LINEAGE == 1. A representacao atual depende de um centro "
    "canonico por linhagem."
)
assert OFFSPRING_PER_PAIR == 2, (
    "A implementacao atual materializa exatamente dois filhos por evento."
)
assert REPRODUCE_IN_PAIRS is True, (
    "A implementacao atual seleciona exatamente dois pais por evento."
)
assert len(ADVANCED_METRICS) >= 1, "Pelo menos uma metrica e necessaria."
assert METRICS_CSV_SUFFIX == "_metricas.csv", (
    "METRICS_CSV_SUFFIX faz parte do contrato de compatibilidade."
)
assert "{slot}" in SAVE_SLOT_TEMPLATE, (
    "SAVE_SLOT_TEMPLATE deve conter o placeholder {slot}."
)
assert "{slot}" in METRICS_SLOT_TEMPLATE, (
    "METRICS_SLOT_TEMPLATE deve conter o placeholder {slot}."
)
assert GENOME_SIZE == (
    INPUT_HIDDEN_WEIGHTS
    + HIDDEN1_HIDDEN2_WEIGHTS
    + HIDDEN2_OUTPUT_WEIGHTS
    + HIDDEN_BIASES
    + HIDDEN_BIASES_2
    + RECURRENCE_WEIGHTS
), "GENOME_SIZE e inconsistente com seus componentes."
