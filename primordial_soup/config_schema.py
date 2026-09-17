# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Catálogo canônico para a configuração declarativa do Primordial Soup."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from .model_contract import GENE_VALUE_SPAN


class ConfigScope(str, Enum):
    NON_HOT = "non_hot"
    OPERATOR = "operator"
    HOT = "hot"


class ConfigSection(str, Enum):
    WORLD_DISPLAY = "world_display"
    POPULATION = "population"
    NEURAL_ARCHITECTURE = "neural_architecture"
    WORLD_GEOMETRY = "world_geometry"
    PRESENTATION = "presentation"
    PERSISTENCE = "persistence"
    RECORDING = "recording"
    AUDIO = "audio"
    DIAGNOSTICS = "diagnostics"
    OPERATOR_INTERFACE = "operator_interface"
    OPERATOR_EXECUTION = "operator_execution"
    OPERATOR_AUDIO = "operator_audio"
    HOT_CROSSOVER = "hot_crossover"
    HOT_MUTATION = "hot_mutation"
    HOT_BEHAVIOR = "hot_behavior"
    HOT_ECOLOGY = "hot_ecology"
    HOT_REPRODUCTION = "hot_reproduction"
    HOT_SELECTION = "hot_selection"


class ConfigValueType(str, Enum):
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"
    RGB = "rgb"
    FONT = "font"
    STRING_TUPLE = "string_tuple"


@dataclass(frozen=True, slots=True)
class ConfigFieldRef:
    """Referencia outro campo do snapshot sem consultar estado global."""

    scope: ConfigScope
    attr_name: str


class ConfigDerivedRef(str, Enum):
    """Referencias a valores derivados que nao pertencem ao arquivo declarativo."""

    GENOME_SIZE = "genome_size"


@dataclass(frozen=True, slots=True)
class ConfigConstraintSpec:
    """Dominio declarativo de um campo, independente de qualquer interface."""

    minimum: int | float | ConfigFieldRef | None = None
    maximum: int | float | ConfigFieldRef | ConfigDerivedRef | None = None
    minimum_inclusive: bool = True
    maximum_inclusive: bool = True
    step: int | float | None = None
    choices: tuple[object, ...] | ConfigFieldRef | None = None


@dataclass(frozen=True, slots=True)
class ConfigFieldSpec:
    """Metadados estaticos para um campo de configuracao declarativa."""

    env_key: str
    attr_name: str
    scope: ConfigScope
    section: ConfigSection
    value_type: ConfigValueType
    runtime_editable: bool
    editable: bool
    restart_required: bool
    checkpoint_relevant: bool
    label_key: str
    description_key: str
    constraints: ConfigConstraintSpec


def _field(
    *,
    env_key: str,
    attr_name: str,
    scope: ConfigScope,
    section: ConfigSection,
    value_type: ConfigValueType,
    editable: bool = True,
    checkpoint_relevant: bool = False,
    constraints: ConfigConstraintSpec | None = None,
) -> ConfigFieldSpec:
    """Constroi metadata mecanica sem repetir lifecycle e chaves de traducao."""
    return ConfigFieldSpec(
        env_key=env_key,
        attr_name=attr_name,
        scope=scope,
        section=section,
        value_type=value_type,
        runtime_editable=scope is not ConfigScope.NON_HOT,
        editable=editable,
        restart_required=scope is ConfigScope.NON_HOT,
        checkpoint_relevant=checkpoint_relevant,
        label_key=f"config.{attr_name}.label",
        description_key=f"config.{attr_name}.description",
        constraints=constraints or ConfigConstraintSpec(),
    )


CONFIG_SCHEMA: tuple[ConfigFieldSpec, ...] = (
    _field(
        env_key="SCREEN_WIDTH",
        attr_name="screen_width",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.WORLD_DISPLAY,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(minimum=ConfigFieldRef(ConfigScope.NON_HOT, "inspection_panel_width"), minimum_inclusive=False),
    ),
    _field(
        env_key="SCREEN_HEIGHT",
        attr_name="screen_height",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.WORLD_DISPLAY,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(minimum=0, minimum_inclusive=False),
    ),
    _field(
        env_key="TARGET_PIXEL_SCALE",
        attr_name="target_pixel_scale",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.WORLD_DISPLAY,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(minimum=1),
    ),
    _field(
        env_key="ZOOM_STEP",
        attr_name="zoom_step",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.WORLD_DISPLAY,
        value_type=ConfigValueType.FLOAT,
    ),
    _field(
        env_key="INITIAL_POPULATION_PER_LINEAGE",
        attr_name="initial_population_per_lineage",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.POPULATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=2),
    ),
    _field(
        env_key="MAX_POPULATION_PER_LINEAGE",
        attr_name="max_population_per_lineage",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.POPULATION,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(minimum=ConfigFieldRef(ConfigScope.NON_HOT, "initial_population_per_lineage")),
    ),
    _field(
        env_key="VISION_RADIUS",
        attr_name="vision_radius",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.NEURAL_ARCHITECTURE,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
    ),
    _field(
        env_key="HIDDEN_NEURONS",
        attr_name="hidden_neurons",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.NEURAL_ARCHITECTURE,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
    ),
    _field(
        env_key="HIDDEN_NEURONS_2",
        attr_name="hidden_neurons_2",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.NEURAL_ARCHITECTURE,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(minimum=1),
    ),
    _field(
        env_key="HIDDEN_ACTIVATION",
        attr_name="hidden_activation",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.NEURAL_ARCHITECTURE,
        value_type=ConfigValueType.STRING,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(choices=("sigmoid", "tanh", "relu")),
    ),
    _field(
        env_key="HIDDEN_ACTIVATION_2",
        attr_name="hidden_activation_2",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.NEURAL_ARCHITECTURE,
        value_type=ConfigValueType.STRING,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(choices=("sigmoid", "tanh", "relu")),
    ),
    _field(
        env_key="OUTPUT_ACTIVATION",
        attr_name="output_activation",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.NEURAL_ARCHITECTURE,
        value_type=ConfigValueType.STRING,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(choices=("linear", "sigmoid", "tanh", "relu")),
    ),
    _field(
        env_key="INITIAL_HP",
        attr_name="initial_hp",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.NEURAL_ARCHITECTURE,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
    ),
    _field(
        env_key="NUMBER_OF_ZONES",
        attr_name="number_of_zones",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.WORLD_GEOMETRY,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(minimum=0),
    ),
    _field(
        env_key="ZONE_RADIUS",
        attr_name="zone_radius",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.WORLD_GEOMETRY,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(minimum=0, minimum_inclusive=False),
    ),
    _field(
        env_key="NEST_RADIUS",
        attr_name="nest_radius",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.WORLD_GEOMETRY,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(minimum=0, maximum=149, minimum_inclusive=False),
    ),
    _field(
        env_key="NEST_SPAWN_RADIUS",
        attr_name="nest_spawn_radius",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.WORLD_GEOMETRY,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(minimum=0, maximum=ConfigFieldRef(ConfigScope.NON_HOT, "nest_radius")),
    ),
    _field(
        env_key="MAX_NEST_PLACEMENT_ATTEMPTS",
        attr_name="max_nest_placement_attempts",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.WORLD_GEOMETRY,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, minimum_inclusive=False),
    ),
    _field(
        env_key="TARGET_FPS",
        attr_name="target_fps",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="HUD_FONT",
        attr_name="hud_font",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.FONT,
    ),
    _field(
        env_key="HUD_BG_COLOR",
        attr_name="hud_bg_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="HUD_BORDER_COLOR",
        attr_name="hud_border_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="HUD_TEXT_COLOR",
        attr_name="hud_text_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="HUD_TEXT_SECONDARY_COLOR",
        attr_name="hud_text_secondary_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="HUD_TITLE_COLOR",
        attr_name="hud_title_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="HUD_MARGIN",
        attr_name="hud_margin",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="HUD_PADDING",
        attr_name="hud_padding",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="HUD_TELEMETRY_WIDTH",
        attr_name="hud_telemetry_width",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="HUD_OVERLAY_ALPHA",
        attr_name="hud_overlay_alpha",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="HUD_SECTION_GAP",
        attr_name="hud_section_gap",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="HUD_DIVIDER_COLOR",
        attr_name="hud_divider_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="HUD_KEY_BG_COLOR",
        attr_name="hud_key_bg_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="CHART_INNER_PADDING",
        attr_name="chart_inner_padding",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="CHART_BG_COLOR",
        attr_name="chart_bg_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="CHART_GRID_COLOR",
        attr_name="chart_grid_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="CHART_AXIS_COLOR",
        attr_name="chart_axis_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="CHART_LABEL_COLOR",
        attr_name="chart_label_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="CHART_TITLE_COLOR",
        attr_name="chart_title_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="HORIZONTAL_GRID_LINES",
        attr_name="horizontal_grid_lines",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1),
    ),
    _field(
        env_key="VERTICAL_GRID_LINES",
        attr_name="vertical_grid_lines",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1),
    ),
    _field(
        env_key="CHART_LINE_THICKNESS",
        attr_name="chart_line_thickness",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1),
    ),
    _field(
        env_key="TRAIL_MAX_LENGTH",
        attr_name="trail_max_length",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="TRAIL_COLOR_OLD",
        attr_name="trail_color_old",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="TRAIL_COLOR_NEW",
        attr_name="trail_color_new",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="DEATH_MARKER_TTL_TICKS",
        attr_name="death_marker_ttl_ticks",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
    ),
    _field(
        env_key="INSPECTION_PANEL_WIDTH",
        attr_name="inspection_panel_width",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
        checkpoint_relevant=True,
        constraints=ConfigConstraintSpec(minimum=0, minimum_inclusive=False),
    ),
    _field(
        env_key="INSPECTION_CELL_HEIGHT",
        attr_name="inspection_cell_height",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, minimum_inclusive=False),
    ),
    _field(
        env_key="CLICK_RADIUS_IN_CELLS",
        attr_name="click_radius_in_cells",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0),
    ),
    _field(
        env_key="PANEL_BG_COLOR",
        attr_name="panel_bg_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="PANEL_BORDER_COLOR",
        attr_name="panel_border_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="PANEL_TEXT_COLOR",
        attr_name="panel_text_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="PANEL_SECONDARY_TEXT_COLOR",
        attr_name="panel_secondary_text_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="INSPECTION_HIGHLIGHT_COLOR",
        attr_name="inspection_highlight_color",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.RGB,
    ),
    _field(
        env_key="HEATMAP_LIMIT",
        attr_name="heatmap_limit",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PRESENTATION,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.0, minimum_inclusive=False),
    ),
    _field(
        env_key="SAVE_SLOTS",
        attr_name="save_slots",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PERSISTENCE,
        value_type=ConfigValueType.STRING_TUPLE,
    ),
    _field(
        env_key="DEFAULT_SAVE_SLOT",
        attr_name="default_save_slot",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.PERSISTENCE,
        value_type=ConfigValueType.STRING,
        constraints=ConfigConstraintSpec(choices=ConfigFieldRef(ConfigScope.NON_HOT, "save_slots")),
    ),
    _field(
        env_key="RECORDING_FILE",
        attr_name="recording_file",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.RECORDING,
        value_type=ConfigValueType.STRING,
    ),
    _field(
        env_key="RECORDING_FPS",
        attr_name="recording_fps",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.RECORDING,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, minimum_inclusive=False),
    ),
    _field(
        env_key="RECORDING_MAX_FRAMES",
        attr_name="recording_max_frames",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.RECORDING,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, minimum_inclusive=False),
    ),
    _field(
        env_key="RECORDING_SCALE",
        attr_name="recording_scale",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.RECORDING,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.0, maximum=1.0, minimum_inclusive=False),
    ),
    _field(
        env_key="RECORDING_LOOP",
        attr_name="recording_loop",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.RECORDING,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0),
    ),
    _field(
        env_key="RECORDING_COLORS",
        attr_name="recording_colors",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.RECORDING,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=2, maximum=256),
    ),
    _field(
        env_key="SOUND_VOLUME_MUSIC",
        attr_name="sound_volume_music",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.AUDIO,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.0, maximum=1.0),
    ),
    _field(
        env_key="SOUND_VOLUME_SFX",
        attr_name="sound_volume_sfx",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.AUDIO,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.0, maximum=1.0),
    ),
    _field(
        env_key="PRINT_EVERY_N_TICKS",
        attr_name="print_every_n_ticks",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.DIAGNOSTICS,
        value_type=ConfigValueType.INT,
    ),
    _field(
        env_key="METRICS_HISTORY_SIZE",
        attr_name="metrics_history_size",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.DIAGNOSTICS,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=2),
    ),
    _field(
        env_key="METRICS_INTERVAL",
        attr_name="metrics_interval",
        scope=ConfigScope.NON_HOT,
        section=ConfigSection.DIAGNOSTICS,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1),
    ),
    _field(
        env_key="DEFAULT_LANGUAGE",
        attr_name="default_language",
        scope=ConfigScope.OPERATOR,
        section=ConfigSection.OPERATOR_INTERFACE,
        value_type=ConfigValueType.STRING,
        constraints=ConfigConstraintSpec(choices=("en", "pt")),
    ),
    _field(
        env_key="DEFAULT_SIMULATION_SPEED",
        attr_name="default_simulation_speed",
        scope=ConfigScope.OPERATOR,
        section=ConfigSection.OPERATOR_EXECUTION,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(choices=(0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0)),
    ),
    _field(
        env_key="DEFAULT_PAUSED",
        attr_name="default_paused",
        scope=ConfigScope.OPERATOR,
        section=ConfigSection.OPERATOR_EXECUTION,
        value_type=ConfigValueType.BOOL,
    ),
    _field(
        env_key="DEFAULT_ZONES_ACTIVE",
        attr_name="default_zones_active",
        scope=ConfigScope.OPERATOR,
        section=ConfigSection.OPERATOR_EXECUTION,
        value_type=ConfigValueType.BOOL,
    ),
    _field(
        env_key="DEFAULT_FLOATING_HUD_VISIBLE",
        attr_name="default_floating_hud_visible",
        scope=ConfigScope.OPERATOR,
        section=ConfigSection.OPERATOR_INTERFACE,
        value_type=ConfigValueType.BOOL,
    ),
    _field(
        env_key="DEFAULT_MUSIC_ENABLED",
        attr_name="default_music_enabled",
        scope=ConfigScope.OPERATOR,
        section=ConfigSection.OPERATOR_AUDIO,
        value_type=ConfigValueType.BOOL,
    ),
    _field(
        env_key="DEFAULT_SFX_ENABLED",
        attr_name="default_sfx_enabled",
        scope=ConfigScope.OPERATOR,
        section=ConfigSection.OPERATOR_AUDIO,
        value_type=ConfigValueType.BOOL,
    ),
    _field(
        env_key="DEFAULT_DISCOVERY_CRITERION",
        attr_name="default_discovery_criterion",
        scope=ConfigScope.OPERATOR,
        section=ConfigSection.OPERATOR_INTERFACE,
        value_type=ConfigValueType.STRING,
        constraints=ConfigConstraintSpec(choices=("most_evolved", "oldest", "youngest", "most_offspring", "most_encounters", "most_explored", "highest_hp", "lowest_hp", "highest_generation")),
    ),
    _field(
        env_key="DEFAULT_DISCOVERY_LINEAGE_FILTER",
        attr_name="default_discovery_lineage_filter",
        scope=ConfigScope.OPERATOR,
        section=ConfigSection.OPERATOR_INTERFACE,
        value_type=ConfigValueType.STRING,
        constraints=ConfigConstraintSpec(choices=("all", "R", "G", "B")),
    ),
    _field(
        env_key="HOT_CROSSOVER_MODE",
        attr_name="crossover_mode",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_CROSSOVER,
        value_type=ConfigValueType.STRING,
        constraints=ConfigConstraintSpec(choices=("blocks", "uniform", "two_points")),
    ),
    _field(
        env_key="HOT_CROSSOVER_PROBABILITY",
        attr_name="crossover_probability",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_CROSSOVER,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.0, maximum=1.0, step=0.05),
    ),
    _field(
        env_key="HOT_BLOCK_SIZE",
        attr_name="block_size",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_CROSSOVER,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1, maximum=ConfigDerivedRef.GENOME_SIZE, step=1),
    ),
    _field(
        env_key="HOT_MUTATION_MODE",
        attr_name="mutation_mode",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_MUTATION,
        value_type=ConfigValueType.STRING,
        constraints=ConfigConstraintSpec(choices=("two_scales", "surgical")),
    ),
    _field(
        env_key="HOT_MUTATION_RATE",
        attr_name="mutation_rate",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_MUTATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, maximum=100, step=1),
    ),
    _field(
        env_key="HOT_MUTATED_GENES",
        attr_name="mutated_genes",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_MUTATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1, maximum=50, step=1),
    ),
    _field(
        env_key="HOT_LOCAL_SCALE_FRACTION",
        attr_name="local_scale_fraction",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_MUTATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1, maximum=100, step=1),
    ),
    _field(
        env_key="HOT_LOCAL_SCALE_SIGMA",
        attr_name="local_scale_sigma",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_MUTATION,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.01, maximum=GENE_VALUE_SPAN, step=0.01),
    ),
    _field(
        env_key="HOT_GLOBAL_PROBABILITY",
        attr_name="global_probability",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_MUTATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, maximum=100, step=1),
    ),
    _field(
        env_key="HOT_GLOBAL_SCALE_FRACTION",
        attr_name="global_scale_fraction",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_MUTATION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1, maximum=100, step=1),
    ),
    _field(
        env_key="HOT_GLOBAL_SCALE_SIGMA",
        attr_name="global_scale_sigma",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_MUTATION,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.01, maximum=GENE_VALUE_SPAN, step=0.05),
    ),
    _field(
        env_key="HOT_LOW_HP_THRESHOLD",
        attr_name="low_hp_threshold",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_BEHAVIOR,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, maximum=ConfigFieldRef(ConfigScope.NON_HOT, "initial_hp"), step=100),
    ),
    _field(
        env_key="HOT_STAY_STILL_IMPULSE",
        attr_name="stay_still_impulse",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_BEHAVIOR,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(step=0.1),
    ),
    _field(
        env_key="HOT_DEATH_HP_THRESHOLD",
        attr_name="death_hp_threshold",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_BEHAVIOR,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, maximum=ConfigFieldRef(ConfigScope.NON_HOT, "initial_hp"), step=100),
    ),
    _field(
        env_key="HOT_ZONE_HP_EFFECT",
        attr_name="zone_hp_effect",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_ECOLOGY,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=-100, maximum=100, step=1),
    ),
    _field(
        env_key="HOT_BASE_DECAY_PER_TICK",
        attr_name="base_decay_per_tick",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_ECOLOGY,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, maximum=10_000, step=1),
    ),
    _field(
        env_key="HOT_PREDATION_TRANSFER",
        attr_name="predation_transfer",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_ECOLOGY,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=10, maximum=200, step=10),
    ),
    _field(
        env_key="HOT_DAMAGE_PER_OWN_OVERCROWDING",
        attr_name="damage_per_own_overcrowding",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_ECOLOGY,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=10, maximum=200, step=10),
    ),
    _field(
        env_key="HOT_REPRODUCTION_INTERVAL",
        attr_name="reproduction_interval",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_REPRODUCTION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1, maximum=100_000, step=10),
    ),
    _field(
        env_key="HOT_REPRODUCTION_MIN_AGE",
        attr_name="reproduction_min_age",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_REPRODUCTION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, maximum=1_000_000, step=100),
    ),
    _field(
        env_key="HOT_REPRODUCTION_HP_GATE",
        attr_name="reproduction_hp_gate",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_REPRODUCTION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1, maximum=ConfigFieldRef(ConfigScope.NON_HOT, "initial_hp"), step=100),
    ),
    _field(
        env_key="HOT_REPRODUCTION_MIN_ENCOUNTERS",
        attr_name="reproduction_min_encounters",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_REPRODUCTION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, maximum=1_000_000, step=1),
    ),
    _field(
        env_key="HOT_REPRODUCTION_PARENT_HP_BONUS",
        attr_name="reproduction_parent_hp_bonus",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_REPRODUCTION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=0, maximum=ConfigFieldRef(ConfigScope.NON_HOT, "initial_hp"), step=10),
    ),
    _field(
        env_key="HOT_REPRODUCTION_CRITERION",
        attr_name="reproduction_criterion",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_SELECTION,
        value_type=ConfigValueType.STRING,
        constraints=ConfigConstraintSpec(choices=("composite", "longevity")),
    ),
    _field(
        env_key="HOT_REPRODUCTION_POOL_FRACTION",
        attr_name="reproduction_pool_fraction",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_SELECTION,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.01, maximum=1.0, step=0.01),
    ),
    _field(
        env_key="HOT_REPRODUCTION_ATTEMPTS_DIVISOR",
        attr_name="reproduction_attempts_divisor",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_SELECTION,
        value_type=ConfigValueType.INT,
        constraints=ConfigConstraintSpec(minimum=1, maximum=ConfigFieldRef(ConfigScope.NON_HOT, "max_population_per_lineage"), step=1),
    ),
    _field(
        env_key="HOT_REPRODUCTION_MIN_SCORE",
        attr_name="reproduction_min_score",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_SELECTION,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.0, maximum=20.0, step=0.1),
    ),
    _field(
        env_key="HOT_LONGEVITY_WEIGHT",
        attr_name="longevity_weight",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_SELECTION,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.0, maximum=5.0, step=0.1),
    ),
    _field(
        env_key="HOT_EXPLORATION_WEIGHT",
        attr_name="exploration_weight",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_SELECTION,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.0, maximum=5.0, step=0.1),
    ),
    _field(
        env_key="HOT_INTERACTION_WEIGHT",
        attr_name="interaction_weight",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_SELECTION,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.0, maximum=5.0, step=0.1),
    ),
    _field(
        env_key="HOT_REPRODUCTION_WEIGHT",
        attr_name="reproduction_weight",
        scope=ConfigScope.HOT,
        section=ConfigSection.HOT_SELECTION,
        value_type=ConfigValueType.FLOAT,
        constraints=ConfigConstraintSpec(minimum=0.0, maximum=5.0, step=0.1),
    ),
)


CONFIG_SECTION_ORDER: tuple[ConfigSection, ...] = tuple(ConfigSection)


def iter_section(section: ConfigSection) -> tuple[ConfigFieldSpec, ...]:
    """Retorna uma secao preservando a ordem relativa do schema."""
    return tuple(spec for spec in CONFIG_SCHEMA if spec.section is section)


_ENV_KEY_INDEX = {spec.env_key: spec for spec in CONFIG_SCHEMA}
_DESTINATION_INDEX = {(spec.scope, spec.attr_name): spec for spec in CONFIG_SCHEMA}


def get_field_spec(env_key: str) -> ConfigFieldSpec:
    """Retorna a entrada do schema para uma chave declarativa exata."""
    try:
        return _ENV_KEY_INDEX[env_key]
    except KeyError:
        raise KeyError(env_key) from None


def get_field_spec_by_attr(
    scope: ConfigScope,
    attr_name: str,
) -> ConfigFieldSpec:
    """Retorna a entrada do schema pelo destino materializado."""
    try:
        return _DESTINATION_INDEX[(scope, attr_name)]
    except KeyError:
        raise KeyError((scope, attr_name)) from None


def iter_scope(scope: ConfigScope) -> tuple[ConfigFieldSpec, ...]:
    """Retorna um escopo na mesma ordem canonica de serializacao."""
    return tuple(spec for spec in CONFIG_SCHEMA if spec.scope is scope)


def iter_checkpoint_relevant() -> tuple[ConfigFieldSpec, ...]:
    """Retorna os NON-HOT que participam da identidade de checkpoint."""
    return tuple(spec for spec in CONFIG_SCHEMA if spec.checkpoint_relevant)


def _choice_matches_type(value: object, value_type: ConfigValueType) -> bool:
    """Confere tipos de choices sem aceitar bool como int."""
    if value_type is ConfigValueType.INT:
        return type(value) is int
    if value_type is ConfigValueType.FLOAT:
        return type(value) is float
    if value_type is ConfigValueType.BOOL:
        return type(value) is bool
    if value_type is ConfigValueType.STRING:
        return type(value) is str and bool(value)
    return False


def _validate_schema_definition() -> None:
    """Falha cedo quando a definicao fechada do schema e incoerente."""
    if not CONFIG_SCHEMA:
        raise RuntimeError("CONFIG_SCHEMA nao pode ser vazio.")

    key_pattern = re.compile(r"[A-Z][A-Z0-9_]*\Z")
    env_keys: set[str] = set()
    destinations: set[tuple[ConfigScope, str]] = set()

    for spec in CONFIG_SCHEMA:
        if not spec.env_key or key_pattern.fullmatch(spec.env_key) is None:
            raise RuntimeError(f"Chave de configuracao invalida: {spec.env_key!r}.")
        if not spec.attr_name:
            raise RuntimeError(f"attr_name vazio para {spec.env_key}.")
        if type(spec.section) is not ConfigSection:
            raise RuntimeError(f"section invalida para {spec.env_key}.")
        if not spec.label_key or not spec.description_key:
            raise RuntimeError(f"Chaves de i18n vazias para {spec.env_key}.")
        if spec.env_key in env_keys:
            raise RuntimeError(f"Chave de configuracao duplicada: {spec.env_key}.")
        env_keys.add(spec.env_key)

        destination = (spec.scope, spec.attr_name)
        if destination in destinations:
            raise RuntimeError(
                f"Destino de configuracao duplicado: "
                f"{spec.scope.value}.{spec.attr_name}."
            )
        destinations.add(destination)

        if spec.scope is ConfigScope.HOT:
            if not spec.env_key.startswith("HOT_"):
                raise RuntimeError(f"Chave HOT sem prefixo HOT_: {spec.env_key}.")
        elif spec.env_key.startswith("HOT_"):
            raise RuntimeError(
                f"Chave nao HOT usa prefixo reservado HOT_: {spec.env_key}."
            )

        expected_runtime_editable = spec.scope is not ConfigScope.NON_HOT
        if spec.runtime_editable is not expected_runtime_editable:
            raise RuntimeError(
                f"runtime_editable incoerente para {spec.env_key}."
            )
        if type(spec.editable) is not bool:
            raise RuntimeError(f"editable deve ser bool para {spec.env_key}.")
        if type(spec.checkpoint_relevant) is not bool:
            raise RuntimeError(
                f"checkpoint_relevant deve ser bool para {spec.env_key}."
            )
        expected_restart = spec.scope is ConfigScope.NON_HOT
        if spec.restart_required is not expected_restart:
            raise RuntimeError(
                f"restart_required incoerente para {spec.env_key}."
            )
        if spec.checkpoint_relevant:
            if spec.scope is not ConfigScope.NON_HOT:
                raise RuntimeError(
                    f"checkpoint_relevant exige NON_HOT: {spec.env_key}."
                )
            if spec.restart_required is not True:
                raise RuntimeError(
                    f"checkpoint_relevant exige restart_required: {spec.env_key}."
                )

        constraints = spec.constraints
        if constraints.step is not None:
            if spec.value_type not in {ConfigValueType.INT, ConfigValueType.FLOAT}:
                raise RuntimeError(f"step em tipo nao numerico: {spec.env_key}.")
            if type(constraints.step) not in {int, float} or constraints.step <= 0:
                raise RuntimeError(f"step invalido para {spec.env_key}.")

        has_range = constraints.minimum is not None or constraints.maximum is not None
        if has_range and spec.value_type not in {ConfigValueType.INT, ConfigValueType.FLOAT}:
            raise RuntimeError(f"range em tipo nao numerico: {spec.env_key}.")

        if isinstance(constraints.choices, tuple):
            if not constraints.choices:
                raise RuntimeError(f"choices vazio para {spec.env_key}.")
            if len(set(constraints.choices)) != len(constraints.choices):
                raise RuntimeError(f"choices duplicado para {spec.env_key}.")
            if not all(
                _choice_matches_type(choice, spec.value_type)
                for choice in constraints.choices
            ):
                raise RuntimeError(f"choice com tipo invalido para {spec.env_key}.")

        minimum = constraints.minimum
        maximum = constraints.maximum
        if type(minimum) in {int, float} and type(maximum) in {int, float}:
            if minimum > maximum:
                raise RuntimeError(f"range invertido para {spec.env_key}.")
            if minimum == maximum and (
                not constraints.minimum_inclusive
                or not constraints.maximum_inclusive
            ):
                raise RuntimeError(f"range vazio para {spec.env_key}.")

    if len(CONFIG_SECTION_ORDER) != len(set(CONFIG_SECTION_ORDER)):
        raise RuntimeError("CONFIG_SECTION_ORDER contem duplicatas.")
    if set(CONFIG_SECTION_ORDER) != set(ConfigSection):
        raise RuntimeError("CONFIG_SECTION_ORDER deve cobrir exatamente ConfigSection.")

    present_sections = {spec.section for spec in CONFIG_SCHEMA}
    if present_sections != set(ConfigSection):
        raise RuntimeError("Toda ConfigSection deve aparecer ao menos uma vez no schema.")

    non_hot_sections = {
        ConfigSection.WORLD_DISPLAY,
        ConfigSection.POPULATION,
        ConfigSection.NEURAL_ARCHITECTURE,
        ConfigSection.WORLD_GEOMETRY,
        ConfigSection.PRESENTATION,
        ConfigSection.PERSISTENCE,
        ConfigSection.RECORDING,
        ConfigSection.AUDIO,
        ConfigSection.DIAGNOSTICS,
    }
    operator_sections = {
        ConfigSection.OPERATOR_INTERFACE,
        ConfigSection.OPERATOR_EXECUTION,
        ConfigSection.OPERATOR_AUDIO,
    }
    hot_sections = {
        ConfigSection.HOT_CROSSOVER,
        ConfigSection.HOT_MUTATION,
        ConfigSection.HOT_BEHAVIOR,
        ConfigSection.HOT_ECOLOGY,
        ConfigSection.HOT_REPRODUCTION,
        ConfigSection.HOT_SELECTION,
    }
    allowed_sections = {
        ConfigScope.NON_HOT: non_hot_sections,
        ConfigScope.OPERATOR: operator_sections,
        ConfigScope.HOT: hot_sections,
    }
    for spec in CONFIG_SCHEMA:
        if spec.section not in allowed_sections[spec.scope]:
            raise RuntimeError(
                f"section incoerente com scope para {spec.env_key}."
            )

    for spec in CONFIG_SCHEMA:
        constraints = spec.constraints
        refs = [constraints.minimum, constraints.maximum, constraints.choices]
        for ref in refs:
            if isinstance(ref, ConfigFieldRef):
                if (ref.scope, ref.attr_name) not in _DESTINATION_INDEX:
                    raise RuntimeError(
                        f"Referencia inexistente em {spec.env_key}: "
                        f"{ref.scope.value}.{ref.attr_name}."
                    )


_validate_schema_definition()
