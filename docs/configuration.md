# ⚙️ Configuration

Primordial Soup has three distinct categories of settings:

```text
STATIC CONFIGURATION
config.py
defines the laws of the universe and their defaults

        +

SIMULATION RUNTIME STATE
state.py
mutable state of the running experiment

        +

GRAPHICAL UI STATE
ui_state.py
transient navigation state of the graphical application
```

Changing `REPRODUCTION_MIN_AGE` changes the simulation model.

Changing `state.mutation_rate` changes the current experiment.

Changing `ui_state.active_panel` changes only the focused panel. It is
not part of the experiment at all.

Changing `HUD_TEXT_COLOR` changes neither.

Not every number deserves equal philosophical weight.

---

# Where configuration lives

```text
primordial_soup/
├── config.py       static laws and defaults
├── layout.py       derived geometry
├── state.py        mutable simulation runtime state
└── ui_state.py     transient graphical navigation state
```

Conceptually:

```text
config.py
   │
   │ static laws
   ▼
layout.py ──→ derived geometry
   │
   ▼
simulation
   │
   ▼
state.py             ui_state.py
simulation runtime   graphical navigation
state                state
```

`config.py` should be treated as the project's constitution.

`state.py` is what happens after the government opens.

`ui_state.py` is which panel the operator happens to be looking at.

---

# Static vs runtime values

| Kind                     | Example                  | Changes during a run?        |
| ------------------------ | ------------------------ | ---------------------------- |
| Structural               | Neural layer sizes       | No                           |
| Simulation law           | Enemy damage             | No                           |
| Selection law            | Minimum reproductive age | No                           |
| Default                  | Initial mutation rate    | Seeds runtime state          |
| Runtime parameter        | Current mutation rate    | Yes                          |
| Derived value            | Genome size              | Computed                     |
| Presentation             | HUD colors               | No simulation effect         |
| Persistent runtime state | Mutation rate            | Saved                        |
| Operator preference      | Language                 | Not part of simulation state |
| Graphical navigation     | active_panel, cursor     | Not part of simulation state |

Static configuration changes generally require restarting the process.

Runtime controls are documented in [Controls](controls.md).

---

# 0. Identity

| Constant        |               Value |
| --------------- | ------------------: |
| `WORLD_NAME`    | `"Primordial Soup"` |
| `WORLD_VERSION` |           `"0.5.0"` |
| `RANDOM_SEED`   |              `None` |

`WORLD_VERSION` identifies the application release. It is distinct from
`SAVE_VERSION`, `ARCHITECTURE_VERSION` and `GENOME_VERSION`.

## RANDOM_SEED caveat

`RANDOM_SEED` currently exists in `config.py`, but the current runtime
does not consume it.

For reproducible command-line experiments:

```bash
python -m primordial_soup --new -d 50000 --seed 42
```

The CLI seeds both random-number sources used by the simulation.

Until `RANDOM_SEED` is wired into world bootstrap, editing it alone
should not be treated as a reproducibility mechanism.

---

# 1. World geometry

| Constant             | Default |
| -------------------- | ------: |
| `SCREEN_WIDTH`       |  `1920` |
| `SCREEN_HEIGHT`      |  `1080` |
| `TARGET_PIXEL_SCALE` |     `2` |
| `MIN_WORLD_WIDTH`    |   `400` |
| `MIN_WORLD_HEIGHT`   |   `300` |

You configure the desired screen area. You do **not** directly configure
`WORLD_WIDTH`, `WORLD_HEIGHT`, `WINDOW_WIDTH`, `WINDOW_HEIGHT`,
`PIXEL_SCALE`.

Those are derived by `layout.py`.

## Derived layout

The inspection panel reserves a fixed strip on the right. Current panel
width: `320 px`.

Available world display width: `SCREEN_WIDTH - INSPECTION_PANEL_WIDTH`.

With defaults: `1920 - 320 = 1600 px`. At `TARGET_PIXEL_SCALE = 2`, the
world is `800 × 540` cells and the window is `1920 × 1080`.

The panel's horizontal space is reserved even when the panel is not
focused.

## Automatic pixel-scale fallback

`layout.py` begins with `TARGET_PIXEL_SCALE` and lowers the scale
toward `1` if necessary to preserve the configured minimum world size.

A screen narrower than the inspection panel is an invalid configuration.

## Fullscreen does not change world geometry

Pressing **F11** changes presentation. It does not recalculate the
simulation grid.

The existing world is scaled to the fullscreen display using
letterboxing when necessary. Fullscreen is therefore visual, not
cosmological.

---

# 2. Lineages

```python
R = Red
G = Green
B = Blue
```

| Lineage | RGB              |
| ------- | ---------------- |
| `R`     | `(255, 0, 0)`    |
| `G`     | `(0, 255, 0)`    |
| `B`     | `(80, 140, 255)` |

`TOTAL_LINEAGES = len(LINEAGES)` = `3`.

Lineage ordering is significant because ecological ally/enemy
relationships and reproductive turns depend on that ordering.

See [Simulation](simulation.md).

---

# 3. Population

| Constant                         | Value |
| -------------------------------- | ----: |
| `INITIAL_POPULATION_PER_LINEAGE` |  `50` |
| `MAX_POPULATION_PER_LINEAGE`     | `333` |

A fresh world begins with `50 R + 50 G + 50 B = 150 total critters`.

Maximum theoretical living population: `333 × 3 = 999`.

## Population invariants

```text
INITIAL_POPULATION_PER_LINEAGE >= 2
MAX_POPULATION_PER_LINEAGE > 0
MAX_POPULATION_PER_LINEAGE >= INITIAL_POPULATION_PER_LINEAGE
MAX_POPULATION_PER_LINEAGE >= OFFSPRING_PER_PAIR
```

There is no `0 = unlimited` sentinel.

---

# 4. Perception

| Constant                |  Value |
| ----------------------- | -----: |
| `VISION_RADIUS`         |    `5` |
| `VISION_SIDE`           |   `11` |
| `VISION_CHANNELS`       |    `3` |
| `VISION_INPUTS`         |  `363` |
| `INTERNAL_STATE_INPUTS` |    `4` |
| `NETWORK_INPUTS`        |  `367` |
| `LOW_HP_THRESHOLD`      | `2000` |

```text
2 × 5 + 1 = 11
11 × 11 = 121
121 × 3 = 363
363 + 4 = 367
```

Changing `VISION_RADIUS`, `VISION_CHANNELS` or `INTERNAL_STATE_INPUTS`
changes `NETWORK_INPUTS`, `GENOME_SIZE` and the genome layout.

Treat perception changes as architectural changes.

---

# 5. Neural architecture

| Constant              |      Value |
| --------------------- | ---------: |
| `HIDDEN_NEURONS`      |       `25` |
| `HIDDEN_NEURONS_2`    |       `12` |
| `HIDDEN_ACTIVATION`   |   `"tanh"` |
| `HIDDEN_ACTIVATION_2` |   `"tanh"` |
| `OUTPUT_ACTIVATION`   | `"linear"` |
| `POSSIBLE_MOVES`      |        `9` |
| `STAY_STILL_INDEX`    |        `4` |

```text
367 inputs → 25 hidden → 12 hidden → 9 outputs
```

The first hidden layer also has recurrent weights (`25 × 25`).

## Genome size

```text
input → hidden 1    367 × 25 = 9,175
hidden 1 → hidden 2 25 × 12  =   300
hidden 2 → outputs  12 × 9   =   108
hidden 1 biases             =    25
hidden 2 biases             =    12
recurrent weights   25 × 25  =   625
                              ─────
GENOME_SIZE                  = 10,245
```

`GENOME_SIZE` is derived. Do not manually edit the total while leaving
its components unchanged.

## Activation functions

Supported hidden activation names: `sigmoid`, `tanh`, `relu`.

Supported output activation names: `linear`, `sigmoid`, `tanh`, `relu`.

Changing activation functions changes controller behavior without
changing genome shape. Still a major experimental change.

## Movement outputs

Nine movement choices corresponding to the Moore neighborhood:

```text
↖ ↑ ↗
← • →
↙ ↓ ↘
```

The center output is index `4` and means stay still.

---

# 6. Metabolism and ecology

| Constant                      |  Default |
| ----------------------------- | -------: |
| `INITIAL_HP`                  | `10,000` |
| `BASE_DECAY_PER_TICK`         |      `1` |
| `STAY_STILL_IMPULSE`          |      `1` |
| `DAMAGE_PER_ENEMY`            |    `100` |
| `DAMAGE_PER_OWN_OVERCROWDING` |    `100` |
| `BONUS_PER_ALLY`              |    `100` |
| `DIE_WHEN_HP_LESS_OR_EQUAL`   |      `0` |

**Initial HP**: every newborn begins with `10,000 HP`. Also used as the
target of Configuration → Heal all critters.

**Base decay**: `1 HP / tick`. Without positive ecological interactions,
life is finite.

**Enemy damage**: `100 HP`, halved when an ally is simultaneously
present. The halving factor is currently part of the interaction
implementation rather than a separate configuration constant.

## Reproductive HP reward

Successful parents currently receive `+50 HP` per reproductive event,
defined in `config.py` as `REPRODUCTION_PARENT_HP_BONUS`.

Applied once per event, not multiplied per child.

Coverage: `tests/test_reproduction_hp_bonus.py`.

**Stay-still impulse**: the movement output for remaining stationary
receives `+1` before the winning action is chosen.

---

# 6b. Environmental zones

| Constant                  |   Default |
| ------------------------- | --------: |
| `ENVIRONMENTAL_MODIFIERS` | `"zonas"` |
| `NUMBER_OF_ZONES`         |       `8` |
| `ZONE_RADIUS`             |      `27` |
| `HP_EFFECT_IN_ZONE`       |      `+5` |
| `MIN_ZONE_HP_EFFECT`      |    `-100` |
| `MAX_ZONE_HP_EFFECT`      |    `+100` |

`ENVIRONMENTAL_MODIFIERS` is expected to remain `"zonas"`.

Use the runtime **Z** toggle or Configuration → **Environmental zones**
when you want zone mechanics temporarily disabled.

## Zone count and radius

A fresh world generates 8 zones of radius 30 world cells. Changing
count or radius changes the spatial selection landscape.

## Zone HP effect

Static default: `+5 HP / tick` inside a zone.

At runtime the current value lives in `state.zone_hp_effect` and can be
adjusted through **Configuration → Zone HP effect** with `← / →`.

Interpretation:

```text
positive → refuge
zero     → neutral
negative → hazard
```

Unlike most static ecological parameters, this one is explicitly
designed for live intervention.

## Z — zones active state

`state.zones_active` controls whether zone rendering and mechanics are
active.

Global **Z** toggles it. The Configuration panel also toggles it as
**Environmental zones**.

Turning zones off does not destroy their mask. Turning them back on
restores the same geography. Starting a new run with **R** regenerates
the zone mask and resets the toggle to ON.

---

# 7. Selection

| Constant                        |       Default |
| ------------------------------- | ------------: |
| `REPRODUCTION_CRITERION`        | `"composite"` |
| `LONGEVITY_WEIGHT`              |         `0.5` |
| `EXPLORATION_WEIGHT`            |         `0.3` |
| `INTERACTION_WEIGHT`            |         `0.3` |
| `REPRODUCTION_WEIGHT`           |         `0.3` |
| `REPRODUCTIVE_POOL_FRACTION`    |         `1/3` |
| `OFFSPRING_PER_PAIR`            |           `2` |
| `REPRODUCTION_ATTEMPTS_DIVISOR` |          `50` |

Eligibility gates:

| Constant                      | Default |
| ----------------------------- | ------: |
| `REPRODUCTION_MIN_AGE`        |  `5555` |
| `REPRODUCTION_HP_GATE`        | `10000` |
| `REPRODUCTION_MIN_SCORE`      |   `0.6` |
| `REPRODUCTION_MIN_ENCOUNTERS` |     `6` |
| `REPRODUCTION_INTERVAL`       |   `150` |

See [Evolution](evolution.md) before changing them.

## Selection criterion

Supported: `composite`, `longevity`. Current default: `composite`.

Eligibility gates still apply before ranking.

## Composite weights

```text
score = 0.5 × normalized longevity
      + 0.3 × normalized exploration
      + 0.3 × normalized interaction
      + 0.3 × normalized reproduction
```

Weights are non-negative. They are not required to sum to `1.0`.
Current sum: `1.4`. So do not interpret composite score as a
probability or percentage.

## Reproductive pool

`REPRODUCTIVE_POOL_FRACTION = 1/3`.

Smaller fraction: stronger elitism. Larger fraction: broader parent
diversity.

## Reproductive turn interval

`REPRODUCTION_INTERVAL = 150`.

The reproduction scheduler rotates `R → G → B → R` using one global
turn and cooldown.

## Reproductive HP gate

Eligibility requires `HP < REPRODUCTION_HP_GATE`, not `<=`. The current
threshold equals initial HP, so a critter still at untouched full health
does not qualify through this gate.

---

# 8. Genetics

| Constant                |    Default |
| ----------------------- | ---------: |
| `CROSSOVER_MODE`        | `"blocks"` |
| `BLOCK_SIZE`            |       `64` |
| `CROSSOVER_PROBABILITY` |      `0.5` |

Supported crossover modes: `blocks`, `uniform`, `two_points`.

See [Evolution](evolution.md).

## Mutation

| Constant                |        Default |
| ----------------------- | -------------: |
| `MUTATION_MODE`         | `"two_scales"` |
| `INITIAL_MUTATION_RATE` |            `5` |
| `INITIAL_MUTATED_GENES` |            `1` |
| `LOCAL_SCALE_FRACTION`  |         `0.05` |
| `LOCAL_SCALE_SIGMA`     |          `0.1` |
| `GLOBAL_SCALE_FRACTION` |         `0.20` |
| `GLOBAL_SCALE_SIGMA`    |          `1.0` |
| `GLOBAL_PROBABILITY`    |         `0.10` |
| `MIN_GENE_VALUE`        |         `-2.0` |
| `MAX_GENE_VALUE`        |          `2.0` |

Supported mutation modes: `two_scales`, `surgical`. Default:
`two_scales`.

## Two-scale mutation

```text
child selected for mutation
        ↓
10% global, 90% local
```

Local: 5% of genes, Gaussian sigma 0.1.

Global: 20% of genes, Gaussian sigma 1.0.

All resulting genes are clipped to `[-2.0, +2.0]`.

## Runtime mutation rate

Integer percentage: `0 to 100`. Default `5`.

Adjustable through **Configuration → Mutation rate**.

## Runtime local scale

Integer percentage: `1 to 100`. Adjustable through
**Configuration → Local mutation scale**.

The runtime value is consumed by the two-scale mutation path via an
explicit argument chain:

```text
state.local_scale_fraction
    → evolution._reproduce_one_pair
    → genetics.crossover_and_mutate
    → genetics._mutate_two_scales
```

Coverage: `tests/test_local_scale_effective.py`.

## Surgical mutated-gene count

Matters only in `MUTATION_MODE = "surgical"`. Not used by the current
default `two_scales`.

---

# 9. Runtime parameter limits

| Runtime value  | Minimum | Maximum |
| -------------- | ------: | ------: |
| Mutation rate  |    `0%` |  `100%` |
| Local scale    |    `1%` |  `100%` |
| Zone HP effect |  `-100` |  `+100` |

Adjusted through the Configuration panel:

```text
C
↓
Configuration
↓
item
↓
← / →
```

The `PARAM_*` identifiers in `config.py` and `state.active_param`
remain internally as legacy; they are not the current graphical
interaction model.

---

# 10. Inspection configuration

Discovery criteria:

```text
most_evolved
oldest
youngest
most_offspring
most_encounters
most_explored
highest_hp
lowest_hp
highest_generation
best_score
```

Lineage filter order:

```text
all
R
G
B
```

Both are selected inside the Inspection panel:

```text
Inspection
↓
Criterion or Lineage filter
↓
← / →
```

**Tab** does not select the lineage filter. **Tab** cycles the focused
panel.

Inspection defaults:

| Constant                 | Default |
| ------------------------ | ------: |
| `INSPECTION_PANEL_WIDTH` |   `320` |
| `INSPECTION_CELL_HEIGHT` |     `8` |
| `CLICK_RADIUS_IN_CELLS`  |     `4` |
| `TRAIL_MAX_LENGTH`       |  `2000` |
| `TRAIL_COLOR_OLD`        |    `40` |
| `TRAIL_COLOR_NEW`        |   `240` |
| `HEATMAP_LIMIT`          |   `2.0` |

There is no `INSPECTION_MODE` configuration value. Inspection is a
focused panel, not a boolean mode. The transient navigation state lives
in `ui_state.py`.

---

# 11. Rendering and performance controls

| Constant              |   Value |
| --------------------- | ------: |
| `TARGET_FPS`          |    `60` |
| `MIN_TICKS_PER_FRAME` |     `1` |
| `MAX_TICKS_PER_FRAME` |   `256` |
| `OVERLAP_POLICY`      | `"max"` |

Simulation speed is adjusted through **Configuration → Simulation
speed**.

Ticks per frame changes throughput, not rules.

## Charts

| Constant                | Value |
| ----------------------- | ----: |
| `CHART_WIDTH`           | `340` |
| `CHART_HEIGHT`          | `140` |
| `CHART_MARGIN`          |  `12` |
| `CHART_SPACING`         |   `8` |
| `CHART_INNER_PADDING`   |  `28` |
| `HORIZONTAL_GRID_LINES` |   `4` |
| `VERTICAL_GRID_LINES`   |   `5` |
| `CHART_LINE_THICKNESS`  |   `2` |

Presentation only.

## UI colors

`config.py` centralizes colors for HUD background, text, borders, chart
grid, chart axes, chart labels, panel background, panel text, discovery
highlight, trail grayscale.

Presentation only.

---

# 12. Persistence

| Constant                | Value                                      |
| ----------------------- | ------------------------------------------ |
| `SAVE_SLOTS`            | `default`, `world_a`, `world_b`, `world_c` |
| `DEFAULT_SAVE_SLOT`     | `default`                                  |
| `SAVE_SLOT_TEMPLATE`    | `genome_pool_{slot}.pkl`                   |
| `METRICS_SLOT_TEMPLATE` | `genome_pool_{slot}_metricas.csv`          |
| `SAVE_FORMAT`           | `pickle`                                   |
| `SAVE_VERSION`          | `11`                                       |
| `ARCHITECTURE_VERSION`  | `mlp-1x25x12-rec`                          |
| `GENOME_VERSION`        | `layout-v4`                                |

The three versions mean different things:

```text
WORLD_VERSION          Which Primordial Soup release is this?
SAVE_VERSION           Which persistence schema does this save use?
ARCHITECTURE_VERSION   Which neural architecture contract?
GENOME_VERSION         Which genome layout contract?
```

Do not update them casually.

See [Persistence](persistence.md).

---

# 13. GIF recording

| Constant               |                 Value |
| ---------------------- | --------------------: |
| `RECORDING_FILE`       | `primordial_soup.gif` |
| `RECORDING_FPS`        |                  `15` |
| `RECORDING_MAX_FRAMES` |                 `400` |
| `RECORDING_SCALE`      |                 `0.5` |
| `RECORDING_LOOP`       |                   `0` |
| `RECORDING_COLORS`     |                 `128` |

Recording settings do not alter simulation behavior.

---

# 14. Diagnostics and metrics

| Constant               | Value |
| ---------------------- | ----: |
| `PRINT_EVERY_N_TICKS`  | `100` |
| `METRICS_HISTORY_SIZE` | `600` |
| `METRICS_INTERVAL`     |  `10` |

Recorded metric identifiers:

```text
populacao
hp_medio
maior_tempo_de_vida
geracao_maxima
score_composto_medio
taxa_de_mutacao
```

These Portuguese identifiers are canonical. They remain stable across
English and Portuguese display modes.

---

# 15. Invariants

`config.py` does more than store constants. It also asserts relationships
that must remain valid.

Examples include:

```text
vision side must be odd
possible moves must equal 9
stay-still index must be the center
gene range must be ordered
population ceiling must be positive
reproduction interval must be >= 1
mutation fractions must be valid
save slots must be unique
save slot names cannot contain path separators
recording palette must fit GIF limits
genome size must match neural components
```

These checks intentionally fail early.

---

# Fresh bootstrap vs R recreate

These operations intentionally have different configuration semantics.

## Application bootstrap / headless --new

A truly fresh bootstrap resets runtime experiment parameters to
defaults:

```text
mutation rate         → INITIAL_MUTATION_RATE = 5%
mutated genes         → INITIAL_MUTATED_GENES = 1
local scale           → LOCAL_SCALE_FRACTION = 5%
ticks/frame           → 1
```

It also constructs fresh populations, genomes, positions, zones,
counters, identity sequence, reproductive cycle.

## R — recreate

The graphical **R** key creates a new population and world, but
deliberately preserves several operator tunings.

For example, if you set mutation to 50% through the Configuration panel
and then press **R**, the new run still uses 50%.

`R` preserves operator-level values such as mutation rate, mutated-gene
state, local-scale runtime value, speed, pause state, language.

It resets run-specific telemetry and identity.

Environmental zones are regenerated, and their active toggle returns to
ON. The current zone HP effect itself is preserved.

This distinction is useful:

```text
R
→ new experimental replicate under current operator tuning

--new / bootstrap
→ new run initialized from static defaults
```

## GUI navigation is not part of any of this

`ui_state.py` (focused panel, cursors, scroll offsets, floating HUD
visibility) is neither persisted in savegames nor touched by `R` or by
`--new`.

From the point of view of the savegame and of the simulation, the
operator's navigation choices simply do not exist.

---

# Configuration notes

## `local_scale_fraction`

The runtime value is consumed by the two-scale mutation path via an
explicit argument chain. Coverage:
`tests/test_local_scale_effective.py`.

## `REPRODUCTION_PARENT_HP_BONUS`

Applied once per successful reproductive event, not per child.
Coverage: `tests/test_reproduction_hp_bonus.py`.

## `RANDOM_SEED`

Declared in `config.py` but not consumed by world bootstrap. For
reproducible runs, use the CLI flag:

```bash
python -m primordial_soup --new -d 50000 --seed 42
```

---

# A practical mental model

When deciding where a value belongs, ask:

```text
Does it define the universe?              → config.py

Is it derived from those laws?            → layout.py

Can the operator change it during a run
and does it affect the experiment?        → state.py

Is it navigation/presentation of the
graphical application, with no effect
on the experiment and no savegame
representation?                           → ui_state.py

Does it affect only presentation?         → UI / rendering configuration

Does it define save compatibility?        → versioned persistence contract
```

That keeps configuration from becoming an undifferentiated warehouse of
integers.

---

# In one sentence

`config.py` defines Primordial Soup's static laws and defaults,
`layout.py` derives geometry from them, `state.py` carries the mutable
values of the experiment currently in progress, and `ui_state.py` carries
the transient navigation state of the graphical application.

Changing a number can alter a color.

Or an ecosystem.

Or just which panel is focused.

Check which one before committing.

---

# Related documentation

→ [Simulation](simulation.md)
→ [Evolution](evolution.md)
→ [Controls](controls.md)
→ [Experiments](experiments.md)
→ [Persistence](persistence.md)
→ [Architecture](architecture.md)
