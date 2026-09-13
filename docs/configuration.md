# ⚙️ Configuration

Primordial Soup has two kinds of settings:

```text
STATIC CONFIGURATION
defined in config.py
defines the laws of the universe

        +

RUNTIME STATE
stored in state.py
changes while a run is executing
```

Understanding the difference is important.

Changing:

```text
REPRODUCTION_MIN_AGE
```

changes the simulation model.

Changing:

```text
state.mutation_rate
```

changes the current experiment.

Changing:

```text
HUD_TEXT_COLOR
```

changes neither.

Not every number deserves equal philosophical weight.

---

# Where configuration lives

The authoritative static configuration is:

```text
primordial_soup/config.py
```

Derived screen and world geometry lives in:

```text
primordial_soup/layout.py
```

Mutable runtime values live in:

```text
primordial_soup/state.py
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
state.py
mutable run state
```

`config.py` should be treated as the project's constitution.

`state.py` is what happens after the government opens.

---

# Static vs runtime values

A useful classification is:

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

Static configuration changes generally require restarting the process.

Runtime controls are documented in [Controls](controls.md).

---

# 0. Identity

Current identity constants:

| Constant        |               Value |
| --------------- | ------------------: |
| `WORLD_NAME`    | `"Primordial Soup"` |
| `WORLD_VERSION` |           `"0.4.0"` |
| `RANDOM_SEED`   |              `None` |

`WORLD_VERSION` identifies the application release.

It is distinct from:

```text
SAVE_VERSION
ARCHITECTURE_VERSION
GENOME_VERSION
```

which describe persistence compatibility.

---

## RANDOM_SEED caveat

`RANDOM_SEED` currently exists in `config.py`, but the current runtime does not consume it.

For reproducible command-line experiments, use:

```bash
python -m primordial_soup --new -d 50000 --seed 42
```

The CLI seeds both random-number sources used by the simulation.

Until `RANDOM_SEED` is wired into world bootstrap, editing it alone should not be treated as a reproducibility mechanism.

Configuration values are only powerful when code reads them.

---

# 1. World geometry

The user-facing geometry configuration is:

| Constant             | Default |
| -------------------- | ------: |
| `SCREEN_WIDTH`       |  `1920` |
| `SCREEN_HEIGHT`      |  `1080` |
| `TARGET_PIXEL_SCALE` |     `2` |
| `MIN_WORLD_WIDTH`    |   `400` |
| `MIN_WORLD_HEIGHT`   |   `300` |

You configure the desired screen area.

You do **not** directly configure:

```text
WORLD_WIDTH
WORLD_HEIGHT
WINDOW_WIDTH
WINDOW_HEIGHT
PIXEL_SCALE
```

Those are derived by `layout.py`.

---

# Derived layout

The inspection panel reserves a fixed strip on the right.

Current panel width:

```text
320 px
```

Available world display width is therefore:

```text
SCREEN_WIDTH - INSPECTION_PANEL_WIDTH
```

With the default configuration:

```text
1920 - 320 = 1600 px
```

At pixel scale:

```text
2
```

the resulting world is:

```text
800 × 540 cells
```

and the complete window is:

```text
1920 × 1080
```

So:

```text
screen
┌──────────────────────────────────────────────┐
│                           │                  │
│        world              │ inspection panel │
│        800 × 540          │     320 px       │
│                           │                  │
└──────────────────────────────────────────────┘
```

The panel's horizontal space is reserved even when inspection mode is closed.

The world never grows underneath it.

---

# Automatic pixel-scale fallback

`layout.py` begins with:

```text
TARGET_PIXEL_SCALE
```

and lowers the scale toward:

```text
1
```

if necessary to preserve the configured minimum world size.

This allows smaller displays to remain usable.

If even scale `1` cannot satisfy:

```text
MIN_WORLD_WIDTH
MIN_WORLD_HEIGHT
```

the application warns but can still run, provided there is positive world space.

A screen narrower than the inspection panel is an invalid configuration.

There is, mathematically speaking, nowhere to put the soup.

---

# Fullscreen does not change world geometry

Pressing:

```text
F11
```

changes presentation.

It does not recalculate the simulation grid.

The existing world is scaled to the fullscreen display using letterboxing when necessary.

This is important because dynamically changing world dimensions would also change:

* coordinates;
* density fields;
* environmental-zone masks;
* persistence assumptions.

Fullscreen is therefore visual.

Not cosmological.

---

# 2. Lineages

Current lineage configuration:

```python
R = Red
G = Green
B = Blue
```

with colors:

| Lineage | RGB              |
| ------- | ---------------- |
| `R`     | `(255, 0, 0)`    |
| `G`     | `(0, 255, 0)`    |
| `B`     | `(80, 140, 255)` |

The total number of lineages is derived:

```text
TOTAL_LINEAGES = len(LINEAGES)
```

Currently:

```text
3
```

Lineage ordering is significant because ecological ally/enemy relationships and reproductive turns depend on that ordering.

Changing it is not merely a palette modification.

See [Simulation](simulation.md).

---

# 3. Population

Current defaults:

| Constant                         | Value |
| -------------------------------- | ----: |
| `INITIAL_POPULATION_PER_LINEAGE` |  `50` |
| `MAX_POPULATION_PER_LINEAGE`     | `333` |

A fresh world therefore begins with:

```text
50 R
50 G
50 B

= 150 total critters
```

if all three configured lineages are present.

Reproduction can grow each lineage independently up to:

```text
333
```

living individuals.

The maximum theoretical living population with the current three-lineage model is therefore:

```text
333 × 3 = 999
```

Actual populations are usually lower because death remains enthusiastic.

---

# Population invariants

Configuration checks require:

```text
INITIAL_POPULATION_PER_LINEAGE >= 2

MAX_POPULATION_PER_LINEAGE > 0

MAX_POPULATION_PER_LINEAGE
>= INITIAL_POPULATION_PER_LINEAGE

MAX_POPULATION_PER_LINEAGE
>= OFFSPRING_PER_PAIR
```

There is no:

```text
0 = unlimited
```

sentinel for maximum population.

The ceiling must be a positive integer.

This keeps reproductive loops bounded.

---

# 4. Perception

Current perception configuration:

| Constant                |  Value |
| ----------------------- | -----: |
| `VISION_RADIUS`         |    `5` |
| `VISION_SIDE`           |   `11` |
| `VISION_CHANNELS`       |    `3` |
| `VISION_INPUTS`         |  `363` |
| `INTERNAL_STATE_INPUTS` |    `4` |
| `NETWORK_INPUTS`        |  `367` |
| `LOW_HP_THRESHOLD`      | `2000` |

The vision window is derived from:

```text
2 × VISION_RADIUS + 1
```

so:

```text
2 × 5 + 1 = 11
```

Each of the:

```text
11 × 11 = 121
```

spatial cells contains one channel per lineage:

```text
121 × 3 = 363
```

visual inputs.

Add four internal-state inputs:

```text
363 + 4 = 367
```

total neural inputs.

---

# Why perception constants are structural

Changing:

```text
VISION_RADIUS
VISION_CHANNELS
INTERNAL_STATE_INPUTS
```

changes:

```text
NETWORK_INPUTS
```

which changes the first neural weight matrix.

That changes:

```text
GENOME_SIZE
```

and therefore the genome layout.

So increasing vision radius is not comparable to changing enemy damage.

It changes the shape of the organism's brain.

Treat perception changes as architectural changes.

---

# 5. Neural architecture

Current neural-controller configuration:

| Constant              |      Value |
| --------------------- | ---------: |
| `HIDDEN_NEURONS`      |       `25` |
| `HIDDEN_NEURONS_2`    |       `12` |
| `HIDDEN_ACTIVATION`   |   `"tanh"` |
| `HIDDEN_ACTIVATION_2` |   `"tanh"` |
| `OUTPUT_ACTIVATION`   | `"linear"` |
| `POSSIBLE_MOVES`      |        `9` |
| `STAY_STILL_INDEX`    |        `4` |

The architecture is:

```text
367 inputs
    ↓
25 hidden neurons
    ↓
12 hidden neurons
    ↓
9 outputs
```

The first hidden layer also has recurrent weights:

```text
25 × 25
```

---

# Genome size

Genome size is derived from all neural components:

```text
input → hidden 1
367 × 25
= 9,175

hidden 1 → hidden 2
25 × 12
= 300

hidden 2 → outputs
12 × 9
= 108

hidden 1 biases
= 25

hidden 2 biases
= 12

recurrent weights
25 × 25
= 625
```

Total:

```text
9,175
+ 300
+ 108
+ 25
+ 12
+ 625
=
10,245 genes
```

So:

```text
GENOME_SIZE = 10,245
```

is derived.

Do not manually edit the total while leaving its components unchanged.

The configuration asserts that the layout remains internally consistent.

---

# Activation functions

The hidden layers currently use:

```text
tanh
```

and outputs use:

```text
linear
```

Supported hidden activation names include:

```text
sigmoid
tanh
relu
```

Supported output activation names additionally include:

```text
linear
```

Changing activation functions changes controller behavior without changing genome shape.

That still makes it a major experimental change.

Same genes.

Different mathematics.

---

# Movement outputs

There are exactly:

```text
9
```

movement choices corresponding to the Moore neighborhood:

```text
↖ ↑ ↗
← • →
↙ ↓ ↘
```

The center output is index:

```text
4
```

and means:

```text
stay still
```

The configuration asserts this relationship explicitly.

---

# 6. Metabolism and ecology

Current survival constants:

| Constant                      |  Default |
| ----------------------------- | -------: |
| `INITIAL_HP`                  | `10,000` |
| `BASE_DECAY_PER_TICK`         |      `1` |
| `STAY_STILL_IMPULSE`          |      `1` |
| `DAMAGE_PER_ENEMY`            |    `100` |
| `DAMAGE_PER_OWN_OVERCROWDING` |    `100` |
| `BONUS_PER_ALLY`              |    `100` |
| `DIE_WHEN_HP_LESS_OR_EQUAL`   |      `0` |

These values define core ecological pressure.

Changing them directly changes what constitutes a survivable strategy.

---

# Initial HP

Every newborn begins with:

```text
10,000 HP
```

This is also the value used by the graphical:

```text
H
```

intervention to reset living critters' HP.

---

# Base decay

Every surviving critter loses:

```text
1 HP / tick
```

before accounting for favorable environmental effects.

Without positive ecological interactions, life is finite.

At minimum:

```text
existence has maintenance cost
```

This creates persistent survival pressure.

---

# Enemy damage

Current full enemy damage:

```text
100 HP
```

When an ally is simultaneously present, the implementation halves enemy damage.

That halving factor is currently part of the interaction implementation rather than a separate configuration constant.

Not every meaningful number has yet been promoted into `config.py`.

---

# Reproductive HP reward is not in config.py

Successful parents currently receive:

```text
+50 HP
```

per reproductive event.

This value is defined locally in:

```text
evolution.py
```

as:

```text
HP_BONUS_PER_OFFSPRING = 50
```

despite the historical name referring to “offspring.”

The current reward is event-level, not multiplied per child.

Because it is outside `config.py`, do not expect to find it in the configuration tables above.

The old README still mentioned `250`; that value is stale.

---

# Stay-still impulse

The movement output for remaining stationary receives:

```text
+1
```

before the winning action is chosen.

This slightly biases the controller against movement caused purely by approximately equal noisy outputs.

Changing it alters the behavioral prior of every neural controller.

---

# 6b. Environmental zones

Current zone configuration:

| Constant                  |   Default |
| ------------------------- | --------: |
| `ENVIRONMENTAL_MODIFIERS` | `"zonas"` |
| `NUMBER_OF_ZONES`         |       `6` |
| `ZONE_RADIUS`             |      `30` |
| `HP_EFFECT_IN_ZONE`       |      `+5` |
| `MIN_ZONE_HP_EFFECT`      |    `-100` |
| `MAX_ZONE_HP_EFFECT`      |    `+100` |

The current model always uses the zone system.

`ENVIRONMENTAL_MODIFIERS` is expected to remain:

```text
"zonas"
```

The older idea of selecting:

```text
"none"
```

as a different environmental mode no longer exists.

Use the runtime **Z** toggle when you want zone mechanics temporarily disabled.

---

# Zone count and radius

A fresh world generates:

```text
6
```

zones.

Each has radius:

```text
30 world cells
```

Their generated geometry becomes part of the world state.

Changing zone count or radius changes the spatial selection landscape.

---

# Zone HP effect

Static default:

```text
+5 HP / tick
```

inside a zone.

At runtime, the current value lives in:

```text
state.zone_hp_effect
```

and can be adjusted using:

```text
E
↑ / ↓
```

Current allowed runtime range:

```text
-100 to +100
```

Interpretation:

```text
positive → refuge
zero     → neutral
negative → hazard
```

Unlike most static ecological parameters, this one is explicitly designed for live intervention.

---

# Z — zones active state

The runtime toggle:

```text
state.zones_active
```

controls whether zone rendering and mechanics are active.

Press:

```text
Z
```

to toggle it.

Turning zones off does not destroy their mask.

Turning them back on restores the same geography.

Starting a new run with **R**, however, regenerates the zone mask and resets the toggle to:

```text
ON
```

---

# 7. Selection

Current parent-selection configuration:

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

These values define much of the evolutionary pressure.

See [Evolution](evolution.md) before changing them.

---

# Selection criterion

Supported configured criteria are:

```text
composite
longevity
```

Current default:

```text
composite
```

With composite selection, eligible individuals are ranked by the composite score.

With longevity selection, ranking is based on age.

The four eligibility gates still apply before ranking.

Changing the ranking criterion does not mean:

```text
ignore reproductive gates
```

It means:

```text
among those allowed to reproduce,
how should they be ranked?
```

---

# Composite weights

Current formula:

```text
score =
    0.5 × normalized longevity
  + 0.3 × normalized exploration
  + 0.3 × normalized interaction
  + 0.3 × normalized reproduction
```

The weights are required to be non-negative.

They are not required to sum to:

```text
1.0
```

Current sum:

```text
1.4
```

So do not interpret composite score as a probability or percentage.

---

# Reproductive pool

Current:

```text
REPRODUCTIVE_POOL_FRACTION = 1 / 3
```

After eligibility and ranking, approximately the top third becomes the parent pool.

This is one of the clearest controls over selection intensity.

Smaller fraction:

```text
stronger elitism
```

Larger fraction:

```text
broader parent diversity
```

Neither is universally better.

That is what experiments are for.

---

# Reproduction attempts

Current formula:

```text
attempts =
max(
    1,
    ceil(population / 50)
)
```

because:

```text
REPRODUCTION_ATTEMPTS_DIVISOR = 50
```

Lowering the divisor increases reproduction attempts per lineage turn.

Raising it reduces them.

Do not set it below:

```text
1
```

The configuration will reject that.

Zero remains unpopular with division.

---

# Reproductive turn interval

Current:

```text
150
```

The reproduction scheduler rotates:

```text
R → G → B → R
```

using one global turn and cooldown.

Lower values create more frequent reproductive opportunities.

Higher values lengthen the ecological interval between opportunities.

---

# Reproductive HP gate

Eligibility requires:

```text
HP < REPRODUCTION_HP_GATE
```

not:

```text
HP <= REPRODUCTION_HP_GATE
```

The current threshold equals initial HP:

```text
10,000
```

so a critter still at untouched full health does not qualify through this gate.

The configuration requires the gate to be:

```text
> 0
```

and:

```text
<= INITIAL_HP
```

---

# 8. Genetics

Current crossover configuration:

| Constant                |    Default |
| ----------------------- | ---------: |
| `CROSSOVER_MODE`        | `"blocks"` |
| `BLOCK_SIZE`            |       `64` |
| `CROSSOVER_PROBABILITY` |      `0.5` |

Supported modes:

```text
blocks
uniform
two_points
```

See [Evolution](evolution.md) for their semantics.

---

# Mutation configuration

Current mutation defaults:

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

Supported mutation modes:

```text
two_scales
surgical
```

The default is:

```text
two_scales
```

---

# Two-scale mutation

Current effective model:

```text
child selected for mutation
        ↓
10% global
90% local
```

Local:

```text
5% of genes
Gaussian sigma = 0.1
```

Global:

```text
20% of genes
Gaussian sigma = 1.0
```

All resulting genes are clipped to:

```text
[-2.0, +2.0]
```

---

# Mutation rate range

The runtime mutation rate uses integer percentages:

```text
0 to 100
```

Default:

```text
5%
```

Use:

```text
U
↑ / ↓
```

to change it interactively.

This runtime value **does** feed the current mutation algorithm.

---

# Surgical mutated-gene count

The configuration includes:

```text
INITIAL_MUTATED_GENES = 1
MIN_MUTATED_GENES     = 1
MAX_MUTATED_GENES     = 50
```

This value matters in:

```text
MUTATION_MODE = "surgical"
```

In the current default:

```text
two_scales
```

it is not used by the mutation algorithm.

The state still carries and persists the value for mode compatibility.

---

# ⚠️ Runtime local-scale discrepancy

The graphical interface exposes:

```text
O
↑ / ↓
```

for:

```text
state.local_scale_fraction
```

and the value:

* changes in memory;
* appears in the HUD;
* is saved;
* is restored.

However, the current effective `two_scales` mutation implementation still reads:

```text
cfg.LOCAL_SCALE_FRACTION
```

directly.

So today:

```text
state.local_scale_fraction = 50%
```

does **not** mean the mutation algorithm actually affects 50% of genes locally.

The effective value remains:

```text
cfg.LOCAL_SCALE_FRACTION = 5%
```

until the runtime value is connected to the mutation path.

Therefore:

```text
U
```

is currently an effective evolutionary control.

```text
O
```

is currently a disconnected runtime control.

Do not use **O** as an experimental variable until this is fixed.

---

# Runtime parameter limits

The configuration defines these UI ranges:

| Runtime value  | Minimum | Maximum |
| -------------- | ------: | ------: |
| Mutation rate  |    `0%` |  `100%` |
| Local scale    |    `1%` |  `100%` |
| Zone HP effect |  `-100` |  `+100` |

Canonical parameter IDs:

```text
mutation
local_scale
zone_hp_effect
```

These are internal identifiers used by the active-parameter control system.

---

# 9. Inspection configuration

Discovery criteria are configured in this order:

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

This order is what:

```text
← / →
```

cycles through.

Current lineage-filter order:

```text
all
R
G
B
```

used by:

```text
Tab
```

---

# Inspection defaults

Important constants:

| Constant                 | Default |
| ------------------------ | ------: |
| `INSPECTION_MODE`        | `False` |
| `INSPECTION_PANEL_WIDTH` |   `320` |
| `INSPECTION_CELL_HEIGHT` |     `8` |
| `CLICK_RADIUS_IN_CELLS`  |     `4` |
| `TRAIL_MAX_LENGTH`       |  `2000` |
| `TRAIL_COLOR_OLD`        |    `40` |
| `TRAIL_COLOR_NEW`        |   `240` |
| `HEATMAP_LIMIT`          |   `2.0` |

`TRAIL_MAX_LENGTH` bounds the observation trail.

At most:

```text
2000
```

positions are retained.

This is visualization state.

Not evolutionary memory.

---

# Discovery preferences are not simulation state

The active:

```text
discovery criterion
lineage filter
```

are UI preferences.

They do not affect:

* behavior;
* HP;
* selection;
* reproduction;
* persistence of the world.

Changing how you search for an individual does not change the individual.

The universe remains blissfully unaware of your dropdown preferences.

---

# 9b. Rendering and performance controls

Current defaults:

| Constant              |   Value |
| --------------------- | ------: |
| `TARGET_FPS`          |    `60` |
| `MIN_TICKS_PER_FRAME` |     `1` |
| `MAX_TICKS_PER_FRAME` |   `256` |
| `OVERLAP_POLICY`      | `"max"` |

Simulation acceleration with:

```text
, / .
```

therefore ranges from:

```text
1
```

to:

```text
256 ticks/frame
```

in powers of two under normal key usage.

Ticks per frame changes throughput.

It does not change one tick's simulation rules.

---

# Overlap policy

Current:

```text
OVERLAP_POLICY = "max"
```

When multiple visual contributions occupy the same rendered cell/channel, the display uses the maximum channel intensity according to the rendering rules.

This is primarily a visualization/composition choice.

Do not confuse display intensity with population count.

---

# Charts

Important chart defaults:

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

These affect presentation only.

They are safe to change without altering evolutionary dynamics.

Unless, of course, you define evolutionary success as having nicer axes.

---

# UI colors

`config.py` also centralizes colors for:

* HUD background;
* HUD text;
* borders;
* chart grid;
* chart axes;
* chart labels;
* panel background;
* panel text;
* discovery highlight;
* trail grayscale.

These values are presentation configuration.

Changing them should not change simulation state.

The lineage colors are a partial exception because lineage channels and their visual identity are conceptually linked, even though the controller operates on density channels rather than human color perception.

---

# 10. Persistence

Current persistence configuration:

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

Legacy filenames:

```text
genome_pool.pkl
genome_pool_metricas.csv
```

are retained only for the limited persistence fallback described in [Persistence](persistence.md).

---

# The three versions mean different things

```text
WORLD_VERSION
```

means:

> Which Primordial Soup release is this?

```text
SAVE_VERSION
```

means:

> Which persistence schema does this save use?

```text
ARCHITECTURE_VERSION
```

means:

> Which neural architecture contract does this world expect?

```text
GENOME_VERSION
```

means:

> Which genome layout contract does the saved genetic material use?

Do not update these casually.

They protect different compatibility boundaries.

---

# Save-version history

The current configuration records this evolution:

```text
v2  original save
v3  versioning
v4  internal state added as neural input
v5  light recurrence
v6  second hidden layer
v7  block crossover
v8  two-scale mutation
v9  composite selection pressure
v10 stable individual identity
v11 exact continuation state: reproductive scheduler phase
    and RNG states
```

Current:

```text
SAVE_VERSION = 11
```

The loader follows a strict compatibility policy for save versions.

See [Persistence](persistence.md).

---

# Screen size affects persistence

Environmental zones are stored as a mask matching the derived world geometry.

Therefore changing:

```text
SCREEN_WIDTH
SCREEN_HEIGHT
INSPECTION_PANEL_WIDTH
TARGET_PIXEL_SCALE
```

can change:

```text
WORLD_WIDTH
WORLD_HEIGHT
```

which can make an existing saved zone mask incompatible with the new runtime geometry.

Changing display geometry is therefore not always persistence-neutral.

Fullscreen is safe because it does not re-derive the world.

Changing static screen configuration is a different operation.

---

# 10b. GIF recording

Current recording configuration:

| Constant               |                 Value |
| ---------------------- | --------------------: |
| `RECORDING_FILE`       | `primordial_soup.gif` |
| `RECORDING_FPS`        |                  `15` |
| `RECORDING_MAX_FRAMES` |                 `400` |
| `RECORDING_SCALE`      |                 `0.5` |
| `RECORDING_LOOP`       |                   `0` |
| `RECORDING_COLORS`     |                 `128` |

Interpretation:

```text
400 frames / 15 fps
≈ 26.7 seconds
```

of playback if the recording reaches its frame limit.

`RECORDING_LOOP = 0` means infinite GIF playback looping.

The half-scale capture substantially reduces buffered image memory.

Recording settings do not alter simulation behavior.

They may alter how quickly your disk fills with evidence that Blue did something questionable.

---

# 11. Diagnostics and metrics

Current diagnostic configuration:

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

These Portuguese identifiers are canonical.

They remain stable across English and Portuguese display modes.

Translation happens at presentation time.

The data contract itself is not translated.

---

# Metrics history window

With:

```text
600 samples
```

recorded every:

```text
10 ticks
```

the in-memory chart history covers up to approximately:

```text
6,000 ticks
```

of sampled history once full.

The simulation may have run much longer.

The chart is a bounded recent-history view.

Saved CSV output is the appropriate artifact for experiment analysis.

---

# 12. Invariants

`config.py` does more than store constants.

It also asserts relationships that must remain valid.

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

A configuration error discovered at import time is preferable to a universe running for 70,000 ticks before discovering its genome has the wrong shape.

---

# Runtime values and persistence

Several static values provide defaults for mutable state.

The relationship looks like this:

```text
config default
     ↓
fresh bootstrap
     ↓
runtime state
     ↓
operator modifies value
     ↓
save
     ↓
load restores runtime value
```

Important examples:

| Concept                        | Static default          | Runtime state                | Persisted? |
| ------------------------------ | ----------------------- | ---------------------------- | ---------- |
| Mutation rate                  | `INITIAL_MUTATION_RATE` | `state.mutation_rate`        | Yes        |
| Surgical gene count            | `INITIAL_MUTATED_GENES` | `state.mutated_genes`        | Yes        |
| Local scale                    | `LOCAL_SCALE_FRACTION`  | `state.local_scale_fraction` | Yes        |
| Zone HP effect                 | `HP_EFFECT_IN_ZONE`     | `state.zone_hp_effect`       | Yes        |
| Zones enabled                  | implicit ON             | `state.zones_active`         | Yes        |
| Reproductive scheduler phase   | `R` + cooldown 0        | `state.reproduction_cooldown` / `state.reproduction_turn` | Yes |
| RNG states                     | seeded at bootstrap     | `random` + `np.random`       | Yes        |
| Speed                          | `1` at bootstrap        | `state.ticks_per_frame`      | No         |
| Active parameter               | mutation                | `state.active_param`         | No         |
| Language                       | UI default              | `state.language`             | No         |
| Discovery criterion            | most evolved            | runtime state                | No         |
| Discovery lineage filter       | all                     | runtime state                | No         |

Remember the local-scale caveat: persistence of a value does not currently imply that the two-scale mutation implementation consumes it.

---

# Fresh bootstrap vs R recreate

These operations intentionally have different configuration semantics.

---

## Application bootstrap / headless --new

A truly fresh bootstrap resets runtime experiment parameters to defaults:

```text
mutation rate
→ INITIAL_MUTATION_RATE = 5%

mutated genes
→ INITIAL_MUTATED_GENES = 1

local scale
→ LOCAL_SCALE_FRACTION = 5%

ticks/frame
→ 1

active parameter
→ mutation
```

It also constructs fresh:

```text
populations
genomes
positions
zones
counters
identity sequence
reproductive cycle
```

---

## R — recreate

The graphical **R** key creates a new population and world, but deliberately preserves several operator tunings.

For example, if you set:

```text
mutation = 50%
```

and press:

```text
R
```

the new run still uses:

```text
50%
```

This makes it practical to repeat experimental conditions.

`R` preserves operator-level values such as:

```text
mutation rate
mutated-gene state
local-scale runtime value
speed
pause state
language
active parameter
```

while resetting run-specific telemetry and identity.

Environmental zones are regenerated, and their active toggle returns to:

```text
ON
```

The current zone HP effect itself is preserved.

This distinction is useful:

```text
R
→ new experimental replicate
   under current operator tuning

--new / bootstrap
→ new run initialized from static defaults
```

---

# Configuration changes for experiments

A disciplined experiment should record every static configuration value that differs from baseline.

For example:

```text
Experiment:
selection pressure

Changed:
LONGEVITY_WEIGHT = 0.8

Unchanged:
EXPLORATION_WEIGHT = 0.3
INTERACTION_WEIGHT = 0.3
REPRODUCTION_WEIGHT = 0.3

Duration:
50,000 ticks

Seeds:
1–20
```

A changed source constant is part of the experimental treatment.

Commit hashes are useful because they preserve the entire configuration context.

---

# Parameters worth changing first

If you want to explore the system without redesigning it, reasonable experimental targets include:

```text
INITIAL_MUTATION_RATE

HP_EFFECT_IN_ZONE

REPRODUCTION_MIN_AGE

REPRODUCTION_MIN_SCORE

REPRODUCTION_MIN_ENCOUNTERS

REPRODUCTION_INTERVAL

selection weights

REPRODUCTIVE_POOL_FRACTION

GLOBAL_PROBABILITY

LOCAL_SCALE_FRACTION

GLOBAL_SCALE_FRACTION

crossover mode
```

Change one at a time until you understand the result.

---

# Parameters to change carefully

These modify structural assumptions:

```text
VISION_RADIUS

HIDDEN_NEURONS

HIDDEN_NEURONS_2

POSSIBLE_MOVES

LINEAGES

neural activations

SCREEN geometry when saves matter
```

They may affect:

* genome shape;
* neural interpretation;
* persistence compatibility;
* world dimensions;
* performance;
* scientific comparability with earlier runs.

These are closer to model redesign than parameter tuning.

---

# Presentation-only settings

These are generally safe from an evolutionary perspective:

```text
HUD colors
chart colors
chart size
font
trail colors
panel colors
recording scale
recording FPS
```

Changing them should not alter the simulated life history.

This distinction is useful when reviewing experiment commits.

Not every diff invalidates a comparison.

Changing the chart border from gray to slightly darker gray probably did not cause extinction.

Probably.

---

# Configuration debts

## Resolved since this document was written

### `local_scale_fraction`

The runtime value is now consumed by the two-scale mutation path via
an explicit argument chain (`state` → `evolution` → `genetics`). The
`O` control is effective again.

### `HP_BONUS_PER_OFFSPRING`

The per-event parent HP bonus is now a config constant,
`REPRODUCTION_PARENT_HP_BONUS`, living in `config.py`. The earlier
local definition and its stale `250` commentary have been removed.

## Remaining

### `RANDOM_SEED`

`RANDOM_SEED` remains declared in `config.py` but is not consumed by
world bootstrap. For reproducible runs, use the CLI flag:

```bash
python -m primordial_soup --new -d 50000 --seed 42
```

Editing `RANDOM_SEED` alone should not be treated as a reproducibility
mechanism until it is wired into bootstrap or removed.

---

# A practical mental model

When deciding where a value belongs, ask:

```text
Does it define the universe?
        ↓
config.py

Is it derived from those laws?
        ↓
layout.py or another derived module

Can the operator change it during a run?
        ↓
state.py

Does it affect only presentation?
        ↓
UI / rendering configuration

Does it define save compatibility?
        ↓
versioned persistence contract
```

That keeps configuration from becoming an undifferentiated warehouse of integers.

---

# In one sentence

`config.py` defines Primordial Soup's static laws and defaults, `layout.py` derives geometry from them, and `state.py` carries the mutable values of the experiment currently in progress.

Changing a number can alter a color.

Or an ecosystem.

Check which one before committing.

---

# Related documentation

For what these laws mean inside the simulated universe:

→ [Simulation](simulation.md)

For selection and genetics:

→ [Evolution](evolution.md)

For runtime keyboard adjustments:

→ [Controls](controls.md)

For designing controlled parameter studies:

→ [Experiments](experiments.md)

For save/version compatibility:

→ [Persistence](persistence.md)

For how configuration is consumed internally:

→ [Architecture](architecture.md)
