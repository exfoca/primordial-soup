# ⚙️ Runtime Configuration

Primordial Soup has one declarative configuration system and three lifecycle scopes:

```text
declarative values
        ↓
ConfigSchema
        ↓
ConfigSnapshot
        ↓
scope-specific authority
```

The scopes are:

```text
NON_HOT   process/model/presentation configuration that requires a new process
OPERATOR  declarative startup defaults for mutable operator/application state
HOT       declarative defaults used to construct live RuntimeRules
```

**This is the single authority for configuration architecture, sources, scopes, defaults, constraints, and the distinction between declarative baselines and live rules.** Ecological semantics live in [World Rules](world-rules.md); evolutionary semantics live in [Evolution](evolution.md); checkpoint compatibility lives in [Persistence](persistence.md).

The packaged baseline currently contains **107 configuration fields**: **67 NON_HOT**, **9 OPERATOR**, and **31 HOT**, organized across **18 schema sections**.

> The `.env` stores values.
>
> The schema stores meaning.
>
> The running world stores its current laws.

---

# 🧭 Configuration lifecycle

## NON_HOT

NON_HOT fields are declarative process, model, or presentation values that are not changed through `RuntimeRules`.

Their lifecycle metadata is:

```text
runtime_editable = False
restart_required = True
```

Editing a NON_HOT value on disk does not mutate the current process. The value is materialized only by a new process that loads that configuration source.

NON_HOT does **not** mean “checkpoint identity” in every case. Only a selected subset of NON_HOT fields is compatibility-relevant for continuation; the rest may affect startup, presentation, recording, diagnostics, or fresh-world construction without redefining an already saved universe.

---

## OPERATOR

OPERATOR fields are declarative startup defaults for mutable application/operator state.

They are not `RuntimeRules`, and they are not automatically checkpoint state.

```text
OPERATOR scope != prefs.json
```

Some operator values later participate in `prefs.json`; others are startup baselines only. The scope describes where the initial value comes from, not where every later mutation is persisted.

---

## HOT

HOT fields are the declarative baseline for live `RuntimeRules`.

The active `.env` supplies the values used to construct a fresh rule object. Once a world exists, the live authority is:

```text
state.runtime_rules
```

Changing the declarative file on disk does not change the `RuntimeRules` object of the current world. There is no file watcher and no automatic reload.

A HOT rule may change while a run is active through the validated runtime path. The rule object itself remains immutable: updates create a candidate, validate the entire candidate, and replace the reference only if validation succeeds.

```text
current rules
     ↓
create candidate
     ↓
validate everything
     ↓
valid?
 ┌───┴────┐
 yes      no
  ↓        ↓
commit    reject
```

There is no partial mutation.

> The universe accepts regime change.
>
> It does not accept malformed paperwork.

---

# 🚀 Startup and fresh-world construction

The startup path is:

```text
CONFIG_PATH
    ↓
load_config()
    ↓
ConfigSnapshot
    ↓
config.py facade
    ↓
bootstrap_new_world()
    ↓
default_runtime_rules()
    ↓
state.runtime_rules
```

`CONFIG_SNAPSHOT` is materialized once during configuration import/startup. It is frozen, typed, and fully validated.

A normal fresh bootstrap uses:

```text
bootstrap_new_world()
    → RuntimeRules from CONFIG_SNAPSHOT.hot
    → simulation_speed from the OPERATOR baseline
    → paused from the OPERATOR baseline
```

The graphical `R` command has deliberately different semantics. `controls.recreate()` preserves the current `RuntimeRules`, current simulation speed, and current paused state across the fresh-world bootstrap, then restores those values.

```text
process boot / headless --new
    → HOT declarative baseline

graphical R
    → current HOT tuning preserved
```

`R` also leaves operator/session state that bootstrap does not own in place, including language, active save slot, discovery settings, floating-HUD preference, and audio preferences.

One operator value is intentionally reset by new-run construction: `zones_active` returns to `DEFAULT_ZONES_ACTIVE` when `reset_counters()` initializes the new run.

So “operator state survives `R`” is too broad. The exact rule is narrower: current `RuntimeRules`, simulation speed, and paused state are explicitly preserved; other operator/session preferences remain because bootstrap does not reset them; `zones_active` returns to its declarative OPERATOR baseline.

---

# 📍 Configuration sources

`config_source.py` resolves three concepts:

```text
PACKAGED_CONFIG_PATH
CONFIG_PATH
CONFIG_WRITE_PATH
```

The packaged baseline is:

```text
primordial_soup/.env
```

It is versioned with the application and included as package data. It is not a temporary file synthesized on first boot.

Source precedence is exact:

```text
1. PRIMORDIAL_SOUP_CONFIG
2. existing user config
3. packaged primordial_soup/.env
```

## Explicit override

```text
PRIMORDIAL_SOUP_CONFIG=/path/to/config.env
```

The environment variable selects one **complete** configuration file. It does not inject individual values.

A relative override path is resolved against the current working directory. An explicitly selected override that cannot be read fails loudly; it does not silently fall back to the packaged baseline.

## User configuration paths

Linux / BSD:

```text
$XDG_CONFIG_HOME/primordial-soup/.env
```

or, when `XDG_CONFIG_HOME` is absent:

```text
~/.config/primordial-soup/.env
```

macOS:

```text
~/Library/Application Support/PrimordialSoup/.env
```

Windows with `APPDATA`:

```text
%APPDATA%\PrimordialSoup\.env
```

Windows fallback:

```text
~/AppData/Roaming/PrimordialSoup/.env
```

If there is no explicit override and no user file exists, the process reads the packaged baseline while `CONFIG_WRITE_PATH` points at the user-config destination.

```text
read path
    → packaged .env

write path
    → user config path
```

Importing configuration does **not** create the user file automatically.

If a user `.env` exists but is invalid, loading fails. The file is not ignored in favor of the packaged baseline.

---

# 🧾 Declarative file grammar

The loader intentionally implements a small grammar rather than shell semantics.

Accepted forms:

```text
blank lines
# comments
KEY=value
```

A configuration file is complete, not additive. The current contract requires all **107 canonical assignments**.

Validation rules include:

```text
unknown key      → error
missing key      → error
duplicate key    → error
invalid key      → error
$ interpolation  → unsupported / error
```

There is no shell quoting, interpolation, or environment-variable substitution inside values.

The seven `ConfigValueType` values are:

| Type | Canonical representation example |
| --- | --- |
| `INT` | `123` |
| `FLOAT` | `1.25` |
| `BOOL` | `true` / `false` |
| `STRING` | `tanh` |
| `RGB` | `255,0,0` |
| `FONT` | `monospace,14,true` |
| `STRING_TUPLE` | `default,world_a,world_b,world_c` |

Boolean spelling is lowercase.

---

# 🗂️ ConfigSchema

`primordial_soup/config_schema.py` is the metadata authority for declarative configuration.

The current schema contains:

```text
107 ConfigFieldSpec
18 ConfigSection
```

Each field specifies:

```text
env_key
attr_name
scope
section
value_type
runtime_editable
editable
restart_required
checkpoint_relevant
label_key
description_key
constraints
```

The schema defines meaning, constraints, and lifecycle. It does **not** own default values.

```text
ConfigSchema
    → meaning / constraints / lifecycle

.env
    → baseline values
```

The baseline value is the value materialized from the selected declarative file.

A useful architectural rule is:

```text
one semantic rule → one authority
```

Examples:

```text
HOT ranges                         → ConfigSchema
HOT choices                        → ConfigSchema
HOT UI steps                       → ConfigSchema
OPERATOR closed domains            → ConfigSchema
active HOT values                  → state.runtime_rules
checkpoint compatibility membership → ConfigFieldSpec.checkpoint_relevant
```

The application does not maintain parallel local tables of HOT ranges, choices, or steps.

---

# 🧊 ConfigSnapshot

`ConfigSnapshot` groups the materialized values by lifecycle scope:

```text
ConfigSnapshot
├── NonHotConfig
├── OperatorDefaults
└── HotDefaults
```

It is frozen, typed, and fully validated. It represents the declarative values effective for the process.

It is not the entire live application state. In particular, active `RuntimeRules`, current pause state, current speed, preferences, and checkpoint state can diverge from their startup baselines after initialization.

---

# ✅ Candidate-aware validation

`config_validation.py` validates a complete candidate snapshot rather than consulting arbitrary global state.

Constraints may depend on:

```text
another field
current derived value
choices
bounds
steps
```

For example, the maximum valid `HOT_BLOCK_SIZE` is the `GENOME_SIZE` derived from the candidate snapshot's neural dimensions.

That prevents validation from becoming an accidental second configuration runtime.

---

# 🧠 Structural model contract

Fixed neural/genetic structural constants and the canonical layout derivation live in `model_contract.py`.

The single canonical derivation function is:

```text
derive_neural_layout()
```

It derives:

```text
vision_side
vision_inputs
network_inputs
input→hidden weight count
hidden1→hidden2 weight count
hidden2→output weight count
bias counts
recurrence count
genome_size
```

The formula is not duplicated elsewhere.

With the packaged baseline, `VISION_RADIUS=5`, `HIDDEN_NEURONS=25`, and `HIDDEN_NEURONS_2=12`, so the derived genome size is `10,245`. A different valid NON_HOT snapshot can derive a different value.

---

# 🧩 `config.py` facade

`config.py` is not the authority for declarative defaults and HOT validation limits.

It is the materialized runtime facade used by existing runtime modules. It exposes:

```text
materialized NON_HOT aliases
operator-related facade values used by the runtime
derived structural dimensions
model/application persistence constants
```

The declarative schema remains the authority for field constraints and lifecycle metadata.

---

# ✍️ Programmatic configuration service

`config_service.py` provides:

```text
get_config_value()
updated_config()
serialize_config()
write_config()
```

The update/write path is immutable and transactional:

```text
current snapshot
    ↓
immutable candidate
    ↓
full validation
    ↓
canonical serialization
    ↓
same-directory temp
    ↓
flush + fsync
    ↓
reload temp
    ↓
round-trip equality
    ↓
os.replace
```

`write_config()` persists a declarative baseline for a future process. It does **not**:

```text
rebind cfg.CONFIG_SNAPSHOT
alter state.runtime_rules
alter live state
hot-reload the process
```

The service is programmatic infrastructure; no Setup UI, settings editor, automatic config form, or config CLI is currently wired to it.

The Configuration panel is therefore **not** a declarative `.env` editor.

---

# 🧱 NON_HOT reference

The packaged baseline currently defines these 67 NON_HOT fields.

## World display

| Key | Packaged baseline | Checkpoint-relevant? | Purpose |
| --- | ---: | :---: | --- |
| `SCREEN_WIDTH` | `1920` | yes | Logical display width used by world/layout derivation |
| `SCREEN_HEIGHT` | `1080` | yes | Logical display height |
| `TARGET_PIXEL_SCALE` | `4` | yes | Preferred logical cell render scale |
| `ZOOM_STEP` | `1.2` | no | Camera zoom multiplier per step |

## Population

| Key | Packaged baseline | Checkpoint-relevant? | Purpose |
| --- | ---: | :---: | --- |
| `INITIAL_POPULATION_PER_LINEAGE` | `50` | no | Founder population created for each lineage |
| `MAX_POPULATION_PER_LINEAGE` | `350` | yes | Maximum living population per lineage |

## Neural architecture

| Key | Packaged baseline | Checkpoint-relevant? | Purpose |
| --- | ---: | :---: | --- |
| `VISION_RADIUS` | `5` | yes | Radius of the square local vision window |
| `HIDDEN_NEURONS` | `25` | yes | Width of the first recurrent hidden layer |
| `HIDDEN_NEURONS_2` | `12` | yes | Width of the second hidden layer |
| `HIDDEN_ACTIVATION` | `tanh` | yes | First hidden-layer activation |
| `HIDDEN_ACTIVATION_2` | `tanh` | yes | Second hidden-layer activation |
| `OUTPUT_ACTIVATION` | `linear` | yes | Output-layer activation |
| `INITIAL_HP` | `10000` | yes | Initial HP and normalization scale |

## World geometry

| Key | Packaged baseline | Checkpoint-relevant? | Purpose |
| --- | ---: | :---: | --- |
| `NUMBER_OF_ZONES` | `8` | yes | Number of environmental zones |
| `ZONE_RADIUS` | `27` | yes | Zone radius |
| `NEST_RADIUS` | `20` | yes | Functional nest-protection radius |
| `NEST_SPAWN_RADIUS` | `1` | yes | Descendant spawn radius around the nest center |
| `MAX_NEST_PLACEMENT_ATTEMPTS` | `10000` | no | Placement-attempt ceiling during fresh-world nest generation |

## Presentation

| Key | Packaged baseline | Checkpoint-relevant? | Purpose |
| --- | ---: | :---: | --- |
| `TARGET_FPS` | `60` | no | Graphical target frame rate |
| `HUD_FONT` | `monospace,14,true` | no | HUD font tuple |
| `HUD_BG_COLOR` | `8,10,14` | no | HUD background color |
| `HUD_BORDER_COLOR` | `60,70,85` | no | HUD border color |
| `HUD_TEXT_COLOR` | `220,230,240` | no | Primary HUD text color |
| `HUD_TEXT_SECONDARY_COLOR` | `140,155,175` | no | Secondary HUD text color |
| `HUD_TITLE_COLOR` | `255,215,0` | no | HUD title color |
| `HUD_MARGIN` | `8` | no | HUD outer margin |
| `HUD_PADDING` | `10` | no | HUD internal padding |
| `HUD_TELEMETRY_WIDTH` | `400` | no | Telemetry block width |
| `HUD_OVERLAY_ALPHA` | `0` | no | HUD overlay alpha |
| `HUD_SECTION_GAP` | `8` | no | Vertical spacing between HUD sections |
| `HUD_DIVIDER_COLOR` | `40,48,60` | no | HUD divider color |
| `HUD_KEY_BG_COLOR` | `18,21,27` | no | HUD key-cap background color |
| `CHART_INNER_PADDING` | `28` | no | Inner chart padding |
| `CHART_BG_COLOR` | `6,8,12` | no | Chart background color |
| `CHART_GRID_COLOR` | `26,32,42` | no | Chart grid color |
| `CHART_AXIS_COLOR` | `90,100,115` | no | Chart axis color |
| `CHART_LABEL_COLOR` | `170,185,200` | no | Chart label color |
| `CHART_TITLE_COLOR` | `230,240,250` | no | Chart title color |
| `HORIZONTAL_GRID_LINES` | `4` | no | Horizontal chart grid-line count |
| `VERTICAL_GRID_LINES` | `5` | no | Vertical chart grid-line count |
| `CHART_LINE_THICKNESS` | `2` | no | Chart series thickness |
| `TRAIL_MAX_LENGTH` | `2000` | no | Maximum inspection trail length |
| `TRAIL_COLOR_OLD` | `40` | no | Old-end trail intensity |
| `TRAIL_COLOR_NEW` | `240` | no | New-end trail intensity |
| `DEATH_MARKER_TTL_TICKS` | `2000` | yes | Retention window for recent-death history |
| `INSPECTION_PANEL_WIDTH` | `320` | yes | Sidebar width participating in logical world-width derivation |
| `INSPECTION_CELL_HEIGHT` | `8` | no | Inspection-row height calibration |
| `CLICK_RADIUS_IN_CELLS` | `4` | no | World click-selection radius |
| `PANEL_BG_COLOR` | `10,10,10` | no | Panel background color |
| `PANEL_BORDER_COLOR` | `80,80,80` | no | Panel border color |
| `PANEL_TEXT_COLOR` | `230,230,230` | no | Primary panel text color |
| `PANEL_SECONDARY_TEXT_COLOR` | `160,160,160` | no | Secondary panel text color |
| `INSPECTION_HIGHLIGHT_COLOR` | `255,255,0` | no | Inspection highlight color |
| `HEATMAP_LIMIT` | `2.0` | no | Neural heatmap display limit |

Two presentation fields are compatibility-relevant for concrete state reasons. `DEATH_MARKER_TTL_TICKS` participates in validation of the persisted recent-death archive. `INSPECTION_PANEL_WIDTH` currently participates in derivation of the logical world width.

By contrast, Birth Wave calibration remains code-level presentation state in `ui_state.py`; it is not part of `CONFIG_SCHEMA`.

## Persistence selection

| Key | Packaged baseline | Checkpoint-relevant? | Purpose |
| --- | --- | :---: | --- |
| `SAVE_SLOTS` | `default,world_a,world_b,world_c` | no | Slots cycled by the graphical UI |
| `DEFAULT_SAVE_SLOT` | `default` | no | Initial active save slot |

## Recording

| Key | Packaged baseline | Checkpoint-relevant? | Purpose |
| --- | ---: | :---: | --- |
| `RECORDING_FILE` | `primordial_soup.gif` | no | Default GIF filename |
| `RECORDING_FPS` | `15` | no | Recording frame rate |
| `RECORDING_MAX_FRAMES` | `400` | no | Maximum frames retained for one recording |
| `RECORDING_SCALE` | `0.5` | no | Recording output scale |
| `RECORDING_LOOP` | `0` | no | GIF loop parameter |
| `RECORDING_COLORS` | `128` | no | GIF palette size |

## Audio

| Key | Packaged baseline | Checkpoint-relevant? | Purpose |
| --- | ---: | :---: | --- |
| `SOUND_VOLUME_MUSIC` | `0.1` | no | Music volume calibration |
| `SOUND_VOLUME_SFX` | `1.0` | no | Sound-effect volume calibration |

## Diagnostics

| Key | Packaged baseline | Checkpoint-relevant? | Purpose |
| --- | ---: | :---: | --- |
| `PRINT_EVERY_N_TICKS` | `100` | no | Periodic console-report interval |
| `METRICS_HISTORY_SIZE` | `600` | no | In-memory metric-history capacity |
| `METRICS_INTERVAL` | `10` | no | Metric-sampling interval |

---

# 👤 OPERATOR defaults

The nine OPERATOR fields are startup defaults, not `RuntimeRules`.

| Key | Packaged baseline | Valid choices / meaning |
| --- | --- | --- |
| `DEFAULT_LANGUAGE` | `en` | `en`, `pt` |
| `DEFAULT_SIMULATION_SPEED` | `1.0` | `0.25`, `0.5`, `1`, `2`, `4`, `8`, `16`, `32`, `64`, `128`, `256` |
| `DEFAULT_PAUSED` | `true` | Initial paused state |
| `DEFAULT_ZONES_ACTIVE` | `true` | Initial zone-effects toggle |
| `DEFAULT_FLOATING_HUD_VISIBLE` | `true` | Initial floating-HUD visibility |
| `DEFAULT_MUSIC_ENABLED` | `true` | Initial music preference |
| `DEFAULT_SFX_ENABLED` | `true` | Initial SFX preference |
| `DEFAULT_DISCOVERY_CRITERION` | `most_evolved` | `most_evolved`, `oldest`, `youngest`, `most_offspring`, `most_encounters`, `most_explored`, `highest_hp`, `lowest_hp`, `highest_generation` |
| `DEFAULT_DISCOVERY_LINEAGE_FILTER` | `all` | `all`, `R`, `G`, `B` |

`prefs.json` currently persists only:

```text
language
active_save_slot
discovery_criterion
discovery_lineage_filter
floating_hud_visible
music_enabled
sfx_enabled
```

It does **not** persist `simulation_speed`, `paused`, or `zones_active`.

The preferences schema version is `PREFS_VERSION = 1`. Headless execution does not load operator preferences.

---

# 🔥 HOT rules

The values below are the current packaged declarative defaults. After world construction, `state.runtime_rules` is the live authority.

Percent-like mutation controls remain integer percentage units. For example, `mutation_rate = 5` means five percent; the active rule value is not rewritten as `0.05`.

## Crossover

| Rule | Default | Valid range / choices | UI step | Meaning |
| --- | ---: | --- | ---: | --- |
| `crossover_mode` | `blocks` | `blocks`, `uniform`, `two_points` | — | Genetic recombination strategy |
| `crossover_probability` | `0.5` | `0.0 .. 1.0` | `0.05` | Parent-A probability in `uniform` mode |
| `block_size` | `64` | `1 .. GENOME_SIZE` | `1` | Block width in `blocks` mode |

`block_size` does not have a universal numeric maximum. Its maximum is the `GENOME_SIZE` derived from the active snapshot. With the packaged baseline, that maximum is `10245`.

## Mutation

| Rule | Default | Valid range / choices | UI step | Meaning |
| --- | ---: | --- | ---: | --- |
| `mutation_mode` | `two_scales` | `two_scales`, `surgical` | — | Mutation algorithm |
| `mutation_rate` | `5` | `0 .. 100` | `1` | Percentage chance that each child mutates |
| `mutated_genes` | `1` | `1 .. 50` | `1` | Genes replaced in `surgical` mode |
| `local_scale_fraction` | `5` | `1 .. 100` | `1` | Percentage of genome affected by local mutation |
| `local_scale_sigma` | `0.1` | `0.01 .. 4.0` | `0.01` | Local Gaussian noise strength |
| `global_probability` | `10` | `0 .. 100` | `1` | Percentage chance that a mutating child uses the global branch |
| `global_scale_fraction` | `20` | `1 .. 100` | `1` | Percentage of genome affected by global mutation |
| `global_scale_sigma` | `1.0` | `0.01 .. 4.0` | `0.05` | Global Gaussian noise strength |

`mutation_rate` is a probability per child, not per gene.

When `two_scales` is active, `global_probability` chooses between local refinement and the broader global branch. In `surgical` mode, exactly `mutated_genes` positions are selected for each mutating child; the two-scale fraction/sigma controls are irrelevant to that mutation mode.

Local mutation refines. Global mutation explores. Both occasionally produce something evolution will regret.

## Behavior

| Rule | Default | Valid range / choices | UI step | Meaning |
| --- | ---: | --- | ---: | --- |
| `low_hp_threshold` | `2000` | `0 .. 10000` | `100` | Threshold for the neural low-HP input |
| `stay_still_impulse` | `1.0` | no min/max constraint | `0.1` | Bias added to the stay-still output |
| `death_hp_threshold` | `0` | `0 .. 10000` | `100` | Death threshold applied after ecology |

The low-HP threshold changes what the organism is told about its own condition; it does not directly change HP.

`stay_still_impulse` biases one neural output. It does not force the action.

Mortality uses `HP <= death_hp_threshold`.

## Ecology

| Rule | Default | Valid range / choices | UI step | Meaning |
| --- | ---: | --- | ---: | --- |
| `zone_hp_effect` | `5` | `-100 .. 100` | `1` | HP delta per tick inside active zones |
| `base_decay_per_tick` | `1` | `0 .. 10000` | `1` | Basal metabolic HP cost per tick |
| `predation_transfer` | `100` | `10 .. 200` | `10` | Predation HP transfer amount |
| `damage_per_own_overcrowding` | `10` | `10 .. 200` | `10` | Same-lineage overcrowding coefficient |

`zones_active` is not a `RuntimeRule`; it is mutable operator/run state initialized from the OPERATOR baseline.

Turning zones off suppresses zone HP application and the zone HP map label while preserving zone geometry.

## Reproduction

| Rule | Default | Valid range / choices | UI step | Meaning |
| --- | ---: | --- | ---: | --- |
| `reproduction_interval` | `150` | `1 .. 100000` | `10` | Interval between global lineage turns |
| `reproduction_min_age` | `5000` | `0 .. 1000000` | `100` | Minimum parent age |
| `reproduction_hp_gate` | `10000` | `1 .. 10000` | `100` | Parent HP must be strictly below this value |
| `reproduction_min_encounters` | `6` | `0 .. 1000000` | `1` | Minimum encounter count |
| `reproduction_parent_hp_bonus` | `50` | `0 .. 10000` | `10` | HP reward for each successful parent |

Changing `reproduction_interval` reconciles the live cooldown without rewriting the rest of scheduler history: reducing the interval may clamp a larger remaining cooldown; increasing it does not postpone a turn that is already closer than the new interval.

## Selection

| Rule | Default | Valid range / choices | UI step | Meaning |
| --- | ---: | --- | ---: | --- |
| `reproduction_criterion` | `composite` | `composite`, `longevity` | — | Parent ranking strategy |
| `reproduction_pool_fraction` | `0.9` | `0.01 .. 1.0` | `0.01` | Top-ranked fraction admitted to the parent pool |
| `reproduction_attempts_divisor` | `50` | `1 .. 350` | `1` | Controls attempts per reproductive turn |
| `reproduction_min_score` | `0.6` | `0.0 .. 20.0` | `0.1` | Minimum composite score |
| `longevity_weight` | `0.3` | `0.0 .. 5.0` | `0.1` | Longevity score contribution |
| `exploration_weight` | `0.3` | `0.0 .. 5.0` | `0.1` | Exploration score contribution |
| `interaction_weight` | `0.3` | `0.0 .. 5.0` | `0.1` | Encounter score contribution |
| `reproduction_weight` | `0.3` | `0.0 .. 5.0` | `0.1` | Offspring score contribution |

With `composite`, the score is:

```text
score =
    longevity_weight    × normalized longevity
  + exploration_weight  × normalized exploration
  + interaction_weight  × normalized encounters
  + reproduction_weight × normalized offspring
```

The weights are not probabilities and do not need to sum to `1.0`.

---

# 🎛️ Live controls that are not RuntimeRules

Not every live control is a simulation law.

| Control | RuntimeRules? | Persistence role |
| --- | :---: | --- |
| Simulation speed | no | operator/execution state; not checkpointed |
| Pause / resume | no | execution state; not checkpointed |
| Environmental zones ON/OFF | no | run state; checkpointed as part of universe continuation |
| Active save slot | no | operator preference |
| Language | no | operator preference |
| GIF recording | no | tool state |
| Discovery criterion/filter | no | operator preference |
| Floating HUD | no | operator preference |
| Music / SFX enabled | no | operator preference |

The Configuration panel edits active HOT rules and also exposes selected operator/execution controls and actions. It does **not** edit NON_HOT `.env` values, replace `CONFIG_SNAPSHOT`, or write the user configuration file.

---

# 💾 Configuration and checkpoints

The three configuration scopes interact with checkpoints differently.

```text
HOT
    checkpoint stores active RuntimeRules
    saved rules override current HOT defaults on load

OPERATOR
    not checkpoint identity

NON_HOT
    selected compatibility-relevant fields must match
```

The current checkpoint compatibility payload contains exactly these **17 NON_HOT** fields:

```text
SCREEN_WIDTH
SCREEN_HEIGHT
TARGET_PIXEL_SCALE
MAX_POPULATION_PER_LINEAGE
VISION_RADIUS
HIDDEN_NEURONS
HIDDEN_NEURONS_2
HIDDEN_ACTIVATION
HIDDEN_ACTIVATION_2
OUTPUT_ACTIVATION
INITIAL_HP
NUMBER_OF_ZONES
ZONE_RADIUS
NEST_RADIUS
NEST_SPAWN_RADIUS
DEATH_MARKER_TTL_TICKS
INSPECTION_PANEL_WIDTH
```

They are selected by `ConfigFieldSpec.checkpoint_relevant` and materialized through `config_compatibility.py`.

Not all 67 NON_HOT values invalidate a checkpoint. Examples that do not define saved-world continuation include `ZOOM_STEP`, HUD colors, audio calibration, recording settings, metrics-history capacity, `INITIAL_POPULATION_PER_LINEAGE`, and `MAX_NEST_PLACEMENT_ATTEMPTS`.

Those values may influence how a process starts, displays, records, or creates a **new** world without changing the identity required to continue an **existing** checkpoint.

Loading a checkpoint restores its saved active `RuntimeRules`. Current HOT defaults from the `.env` do not overwrite them.

> Change a rule and you are experimenting.
>
> Load a checkpoint and you are continuing history.
>
> Confusing the two is how alternate timelines acquire bugs.

See [Persistence](persistence.md) for the complete checkpoint contract.

---

# 👤 Declarative config, prefs, and checkpoint state

These are three different persistence axes:

```text
declarative .env
    → startup/process baselines

prefs.json
    → operator preferences

checkpoint .pkl
    → universe continuation
```

None substitutes for another.

---

# 🔒 Configuration invariants

```text
CONFIG_SCHEMA is the metadata authority
CONFIG_SNAPSHOT is immutable
.env contains values, not semantic constraints
config.py is not a second schema
NON_HOT changes require a new process
RuntimeRules is immutable
state.runtime_rules is the active HOT authority
config writes do not hot-apply
checkpoint NON-HOT compatibility is schema-driven
persistence does not maintain shadow HOT ranges
prefs are not checkpoint state
saved worlds restore their own RuntimeRules
percent-like mutation fields retain integer percentage units
```

---

## Final note

Configuration is intentionally split by lifecycle rather than by convenience.

The declarative file defines the starting conditions of a process. The schema defines what those values mean. A fresh world turns HOT defaults into a `RuntimeRules` object. From that point onward, the world owns its live laws and a checkpoint preserves them.

The operator can still change the exam while the class is taking it.

Evolution handles the grading.
