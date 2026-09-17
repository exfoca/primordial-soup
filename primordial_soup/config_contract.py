# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Valores materializados imutáveis para configuração declarativa."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NonHotConfig:
    """Valores de processo/modelo que não são editáveis através de RuntimeRules."""

    screen_width: int
    screen_height: int
    target_pixel_scale: int
    zoom_step: float

    initial_population_per_lineage: int
    max_population_per_lineage: int

    vision_radius: int
    hidden_neurons: int
    hidden_neurons_2: int
    hidden_activation: str
    hidden_activation_2: str
    output_activation: str
    initial_hp: int

    number_of_zones: int
    zone_radius: int
    nest_radius: int
    nest_spawn_radius: int
    max_nest_placement_attempts: int

    target_fps: int
    hud_font: tuple[str, int, bool]

    hud_bg_color: tuple[int, int, int]
    hud_border_color: tuple[int, int, int]
    hud_text_color: tuple[int, int, int]
    hud_text_secondary_color: tuple[int, int, int]
    hud_title_color: tuple[int, int, int]

    hud_margin: int
    hud_padding: int
    hud_telemetry_width: int
    hud_overlay_alpha: int
    hud_section_gap: int
    hud_divider_color: tuple[int, int, int]
    hud_key_bg_color: tuple[int, int, int]

    chart_inner_padding: int

    chart_bg_color: tuple[int, int, int]
    chart_grid_color: tuple[int, int, int]
    chart_axis_color: tuple[int, int, int]
    chart_label_color: tuple[int, int, int]
    chart_title_color: tuple[int, int, int]

    horizontal_grid_lines: int
    vertical_grid_lines: int
    chart_line_thickness: int

    trail_max_length: int
    trail_color_old: int
    trail_color_new: int
    death_marker_ttl_ticks: int

    inspection_panel_width: int
    inspection_cell_height: int
    click_radius_in_cells: int

    panel_bg_color: tuple[int, int, int]
    panel_border_color: tuple[int, int, int]
    panel_text_color: tuple[int, int, int]
    panel_secondary_text_color: tuple[int, int, int]
    inspection_highlight_color: tuple[int, int, int]

    heatmap_limit: float

    save_slots: tuple[str, ...]
    default_save_slot: str

    recording_file: str
    recording_fps: int
    recording_max_frames: int
    recording_scale: float
    recording_loop: int
    recording_colors: int

    sound_volume_music: float
    sound_volume_sfx: float

    print_every_n_ticks: int
    metrics_history_size: int
    metrics_interval: int


@dataclass(frozen=True, slots=True)
class OperatorDefaults:
    """Padrões de inicialização para estado mutável de execução e apresentação."""

    default_language: str
    default_simulation_speed: float
    default_paused: bool
    default_zones_active: bool
    default_floating_hud_visible: bool
    default_music_enabled: bool
    default_sfx_enabled: bool
    default_discovery_criterion: str
    default_discovery_lineage_filter: str


@dataclass(frozen=True, slots=True)
class HotDefaults:
    """Linha de base declarativa para o contrato vivo de RuntimeRules."""

    crossover_mode: str
    crossover_probability: float
    block_size: int

    mutation_mode: str
    mutation_rate: int
    mutated_genes: int
    local_scale_fraction: int
    local_scale_sigma: float
    global_probability: int
    global_scale_fraction: int
    global_scale_sigma: float

    low_hp_threshold: int
    stay_still_impulse: float
    death_hp_threshold: int

    zone_hp_effect: int
    base_decay_per_tick: int
    predation_transfer: int
    damage_per_own_overcrowding: int

    reproduction_interval: int
    reproduction_min_age: int
    reproduction_hp_gate: int
    reproduction_min_encounters: int
    reproduction_parent_hp_bonus: int

    reproduction_criterion: str
    reproduction_pool_fraction: float
    reproduction_attempts_divisor: int
    reproduction_min_score: float

    longevity_weight: float
    exploration_weight: float
    interaction_weight: float
    reproduction_weight: float


@dataclass(frozen=True, slots=True)
class ConfigSnapshot:
    """Snapshot imutável completo, analisado a partir de um arquivo de configuração explícito."""

    non_hot: NonHotConfig
    operator: OperatorDefaults
    hot: HotDefaults
