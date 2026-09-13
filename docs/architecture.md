# 🏗️ Architecture

Primordial Soup is deliberately small.

It does not use an application framework, dependency-injection container, entity hierarchy or object graph.

The architecture is primarily:

```text
Python modules
+
NumPy arrays
+
one centralized mutable runtime state
+
explicit simulation functions
```

The design goal is not abstraction for its own sake.

It is to keep the simulation:

* understandable;
* fast;
* deterministic enough for controlled experiments;
* usable both graphically and headlessly;
* inspectable at the level of individual critters;
* safe to save and restore.

This document explains how those pieces fit together.

For the simulation model itself, start with [Simulation](simulation.md).

---

# The architecture at a glance

The major flow is:

```text
                    ┌─────────────────┐
                    │    config.py    │
                    │ static laws     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    layout.py    │
                    │ derived geometry│
                    └────────┬────────┘
                             │
              ┌──────────────┴───────────────┐
              │                              │
              ▼                              ▼
      ┌───────────────┐              ┌───────────────┐
      │   state.py    │              │    world.py   │
      │ mutable state │◀────────────▶│ spatial data  │
      └───────┬───────┘              └───────┬───────┘
              │                              │
              │                 ┌────────────┼────────────┐
              │                 ▼            ▼            ▼
              │             senses.py     movement.py   genetics.py
              │                 │                         │
              │                 ▼                         │
              │              brain.py                     │
              │                 │                         │
              └─────────────────┴──────────┬──────────────┘
                                           ▼
                                   ┌───────────────┐
                                   │ evolution.py  │
                                   │ life cycle    │
                                   └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ simulation.py │
                                   │ orchestration │
                                   └───────┬───────┘
                                           │
                      ┌────────────────────┴────────────────────┐
                      │                                         │
                      ▼                                         ▼
              graphical driver                           headless driver
                      │                                         │
              controls.py                               cli.py
              rendering.py                                  │
              recording.py                                  │
                      └────────────────┬──────────────────────┘
                                       │
                                       ▼
                              persistence.py
```

`i18n.py` sits beside these layers and translates presentation strings.

It does not redefine the simulation's canonical data identifiers.

---

# Project map

The current package contains:

```text
primordial_soup/
├── __init__.py
├── __main__.py
├── cli.py
├── config.py
├── layout.py
├── state.py
├── brain.py
├── genetics.py
├── senses.py
├── movement.py
├── world.py
├── evolution.py
├── simulation.py
├── rendering.py
├── controls.py
├── persistence.py
├── i18n.py
└── recording.py
```

The package is easier to understand if those files are grouped by responsibility.

---

# Configuration and geometry

```text
config.py
layout.py
```

These define what universe can exist.

---

## `config.py`

`config.py` is the source of truth for static simulation constants.

It contains:

* screen configuration;
* lineage definitions;
* population limits;
* perception dimensions;
* neural architecture;
* HP rules;
* environmental rules;
* selection pressure;
* reproduction gates;
* crossover configuration;
* mutation configuration;
* inspection settings;
* rendering settings;
* persistence versions;
* metrics configuration;
* recording configuration.

It also contains assertions that reject internally inconsistent configurations.

The intent is:

```text
config.py
=
declared laws
```

not:

```text
config.py
=
miscellaneous global variables
```

Mutable run state belongs elsewhere.

See [Configuration](configuration.md).

---

## `layout.py`

`layout.py` derives geometry from configuration.

The user declares:

```text
SCREEN_WIDTH
SCREEN_HEIGHT
INSPECTION_PANEL_WIDTH
TARGET_PIXEL_SCALE
```

and the module derives:

```text
pixel_scale
world_width
world_height
window_width
window_height
```

once at import time.

The resulting values live in:

```python
layout.LAYOUT
```

Consumers should use the derived geometry rather than duplicating the calculation.

This makes:

```text
config.py
```

the declaration layer and:

```text
layout.py
```

the deterministic geometry layer.

Fullscreen does not rebuild this geometry.

Rendering scales the existing world instead.

---

# Runtime state

The center of the runtime architecture is:

```text
state.py
```

Primordial Soup does not distribute mutable state across dozens of objects.

Instead, simulation-wide mutable state is centralized.

Examples include:

```text
population data
mutation settings
environmental-zone state
tick counters
birth/death counters
stable identity counter
reproduction scheduler
inspection state
metric history
pause state
simulation speed
language
save slot
recording mirror
```

This produces a simple model:

```text
functions operate on
the same authoritative runtime state
```

The tradeoff is that modules are more strongly coupled through shared state than they would be in a fully encapsulated object architecture.

For a simulation of this scale, the benefit is explicitness and low allocation overhead.

---

# The population representation

There is no Python `Critter` object instantiated once per individual.

Instead, each lineage owns several parallel NumPy structures.

Conceptually:

```text
lineage
│
├── pool
│   neural genomes
│
├── agents
│   current body / neural / fitness state
│
├── ids
│   stable identities
│
└── field
    spatial density grid
```

For a lineage with `N` living critters:

```text
pool.shape
=
(N, GENOME_SIZE)

agents.shape
=
(N, 36)

ids.shape
=
(N,)

field.shape
=
(WORLD_WIDTH, WORLD_HEIGHT)
```

The important invariant is:

```text
len(pool)
=
len(agents)
=
len(ids)
```

Row `i` in all three individual structures refers to the same critter.

---

# Why parallel arrays?

Suppose:

```text
agents[12]
```

contains the body state for a critter.

Then:

```text
pool[12]
```

contains that critter's genome,

and:

```text
ids[12]
```

contains its stable identity.

This arrangement allows operations such as:

```text
filter all dead individuals
```

to be applied to the three arrays using the same mask:

```python
agents = agents[alive]
pool = pool[alive]
ids = ids[alive]
```

The arrays remain aligned.

That alignment is a fundamental runtime invariant.

---

# The agent matrix

Each living individual occupies one row of a:

```text
float32 [N, 36]
```

matrix.

The current layout is:

|  Column | Meaning                      |
| ------: | ---------------------------- |
|     `0` | HP                           |
|     `1` | X position                   |
|     `2` | Y position                   |
|     `3` | Age / lifetime               |
|     `4` | Generation                   |
|     `5` | Last action                  |
|     `6` | Low-HP flag                  |
| `7..31` | Recurrent hidden state       |
|    `32` | Cells explored               |
|    `33` | Encounters                   |
|    `34` | Reproductive-success counter |
|    `35` | Composite score              |

This one matrix therefore contains several conceptual domains:

```text
body
+
location
+
life history
+
short-term neural memory
+
selection metrics
```

---

# Why `float32`?

The neural hidden state requires floating-point storage.

Instead of maintaining separate arrays for every logical field, the simulation keeps the entire record in one `float32` matrix.

That means values that are logically integers, such as:

```text
age
generation
position
action
```

are stored as exactly representable `float32` values and converted to integer form when used as array indices or counters.

The neural hot path also uses `float32`.

This reduces:

* memory consumption;
* memory bandwidth;
* unnecessary dtype conversion.

`brain.evaluate_batch()` explicitly asserts the `float32` contract for important inputs and weight matrices.

A silent promotion to `float64` would still produce mathematically valid output.

It would just make the hottest part of the simulation considerably more expensive.

---

# Stable identity

Array position is not identity.

When critters die, arrays are compacted.

For example:

```text
before death

index 0 → ID 100
index 1 → ID 101
index 2 → ID 102
```

If `ID 101` dies:

```text
after compaction

index 0 → ID 100
index 1 → ID 102
```

Therefore:

```text
(lineage index, array index)
```

is a temporary locator.

It is not a persistent identity.

---

# `ids`

Each lineage maintains:

```text
ids: int64 [N]
```

parallel to:

```text
agents
pool
```

Every new critter receives a global stable integer ID.

IDs are allocated from:

```text
state.next_critter_id
```

which increases monotonically during a run.

Conceptually:

```text
1
2
3
...
149
150
151
...
```

Death does not reuse an ID.

---

# Identity lifecycle

A fresh run starts with:

```text
next_critter_id = 1
```

Founder IDs are allocated.

Newborns continue the sequence.

When the world is saved:

```text
ids
+
next_critter_id
```

are persisted.

When loaded, they are validated together.

The loader rejects a state where:

```text
next_critter_id <= max(existing IDs)
```

because the next birth could collide with an existing identity.

---

# Resolving identity

Observation uses stable IDs.

When code needs the current array position of:

```text
critter #1847
```

it calls the identity-resolution path in `world.py`.

Conceptually:

```text
stable ID
   ↓
search lineage ID arrays
   ↓
(lineage index, current row)
```

This allows array compaction without silently changing the subject of an inspection session.

---

# Discovery uses positions; observation uses identity

This is an intentional boundary.

Discovery functions search the current arrays and naturally return:

```text
(lineage_index, agent_index)
```

because they are selecting from the population as it exists now.

Observation converts that temporary result into:

```text
stable critter ID
```

before storing the selection.

So:

```text
DISCOVERY
current positional view

        ↓ explicit conversion

OBSERVATION
stable identity
```

This is why changing discovery criteria cannot accidentally cause an observation to drift after array compaction.

---

# World representation

`world.py` owns the spatial representation.

Every lineage contains a density field:

```text
field[world_width, world_height]
```

using an integer NumPy array.

The field answers:

> How many individuals from this lineage currently occupy this cell?

It is not the population itself.

It is a spatial projection of the population.

---

# Why density fields?

Critters perceive local lineage density.

If perception searched every other individual individually, a naïve implementation could become increasingly expensive as population grows.

Instead:

```text
individual coordinates
        ↓
density field
        ↓
local spatial lookup
```

turns perception into array indexing.

This is especially useful because several critters may occupy the same cell.

The field stores that multiplicity.

---

# Rebuilding fields

After movement, the fields are rebuilt from current positions:

```text
move everyone
      ↓
fill_fields()
      ↓
new spatial state
```

This ensures ecological consequences use post-movement positions.

Newborns created later in the tick are inserted incrementally rather than forcing another complete field rebuild.

That avoids recomputing the entire world to account for only a small number of births.

---

# Environmental zones

Zones are represented separately as a boolean mask:

```text
zones[world_width, world_height]
```

Zone generation uses toroidal distance.

So a circular zone near the right edge may continue naturally through the left edge.

This keeps environmental geometry consistent with world topology.

---

# Perception pipeline

Perception lives in:

```text
senses.py
```

For each lineage, the module builds a batch of neural inputs.

Conceptually:

```text
density fields
      +
agent positions
      +
agent internal state
      ↓
[N, NETWORK_INPUTS]
```

With the current configuration:

```text
[N, 367]
```

---

# Toroidal vision

For each critter, perception samples the:

```text
11 × 11
```

neighborhood around its current position.

Array indices wrap around the world.

No special edge branch is required conceptually:

```text
x + offset
mod
world_width
```

and similarly for Y.

The result is three lineage-density channels plus four internal-state inputs.

---

# Scratch buffers

Perception is called every tick.

Allocating large temporary arrays every time would create avoidable memory churn.

`senses.py` therefore maintains reusable per-lineage input buffers sized up to:

```text
MAX_POPULATION_PER_LINEAGE
×
NETWORK_INPUTS
```

Under the current configuration:

```text
333 × 367
```

per lineage.

Only the active prefix is used for the current population.

This is a recurring architectural principle in the project:

```text
allocate once
reuse in the hot path
```

---

# Neural evaluation

Neural computation lives in:

```text
brain.py
```

The genome is a flat vector.

`split_weights()` interprets it as:

```text
W1
W2
W3
b1
b2
R
```

with:

```text
W1: input → hidden 1
W2: hidden 1 → hidden 2
W3: hidden 2 → outputs
b1: hidden 1 biases
b2: hidden 2 biases
R:  recurrent hidden-1 weights
```

---

# Genome layout

Current architecture:

```text
367 inputs
   ↓
25 hidden
   ↓
12 hidden
   ↓
9 outputs
```

Genome components:

```text
W1  = 25 × 367 = 9,175
W2  = 12 × 25  =   300
W3  =  9 × 12  =   108
b1  =                25
b2  =                12
R   = 25 × 25  =   625
                     ─────
total             10,245
```

So every critter currently carries:

```text
10,245 float32 genes
```

---

# Batched evaluation

The main neural entry point is:

```python
evaluate_batch(...)
```

Inputs:

```text
inputs
[N, 367]

weights
[N, 10,245]

previous hidden state
[N, 25]
```

Outputs:

```text
movement outputs
[N, 9]

new hidden state
[N, 25]
```

The new hidden state is stored back in the agent matrix for the next tick.

This is the recurrent memory mechanism.

---

# Why batch instead of one critter at a time?

The simulation does not normally execute:

```python
for critter in critters:
    evaluate_network(critter)
```

Instead, each lineage is evaluated as an array batch.

That allows NumPy to perform the heavy matrix operations in compiled code.

The main neural operations use matrix multiplication through:

```python
@
```

rather than Python loops.

The source also deliberately prefers this path over `einsum` for the current batched matrix-vector shapes because it measured better throughput in the tested NumPy builds.

---

# Genetics

Genetic operators live in:

```text
genetics.py
```

A population genome pool is stored as:

```text
float32 [N, GENOME_SIZE]
```

not:

```text
list[np.ndarray]
```

This matters because neural evaluation can consume the matrix directly.

There is no need to:

```text
stack all genomes
```

on every tick.

---

# Random founders

A founder population is produced in one allocation:

```text
[count, GENOME_SIZE]
```

with random values inside the configured gene range.

Again:

```text
one matrix
```

rather than hundreds of individually allocated Python objects.

---

# Crossover

`genetics.py` supports:

```text
uniform
blocks
two_points
```

through mask generators.

The general architecture is:

```text
parent A ─┐
          ├─ crossover mask ─→ offspring batch
parent B ─┘
```

Parental genomes are broadcast as read-only views.

Only the offspring matrices need to be materialized.

---

# Mutation

Mutation operates in-place on offspring batches.

The dispatcher selects between:

```text
surgical
two_scales
```

based on static configuration.

For the current two-scale mode:

```text
mutant offspring
       ↓
local or global mutation
       ↓
sample distinct gene positions
       ↓
add Gaussian noise
       ↓
clip legal gene range
```

The gene sampling path is vectorized using `argpartition` rather than looping over each mutant with repeated `np.random.choice()` calls.

---

# Known local-scale inconsistency

The current architecture contains one important mismatch.

Runtime state exposes:

```text
state.local_scale_fraction
```

and controls can modify it.

But the active two-scale mutation implementation currently reads:

```text
cfg.LOCAL_SCALE_FRACTION
```

directly.

Architecturally, the intended path appears to be:

```text
controls
   ↓
runtime state
   ↓
genetics
```

but the current path is:

```text
config
   ↓
genetics
```

for local mutation fraction.

That is why the `O` runtime control is currently disconnected from effective mutation behavior.

See [Configuration](configuration.md).

---

# Movement

Movement lives in:

```text
movement.py
```

The neural output is reduced to one of nine actions.

The position update is toroidal:

```text
new_x = (x + dx) mod width
new_y = (y + dy) mod height
```

Movement therefore never needs wall collision handling.

There are no edges.

Only modulo arithmetic.

---

# Evolution and ecological consequences

The life-cycle mechanics live primarily in:

```text
evolution.py
```

Its two important high-level responsibilities are:

```text
evaluate_and_move()
```

and:

```text
punish_reward_and_reproduce()
```

The first handles:

```text
perception
neural evaluation
hidden-state update
movement choice
movement
exploration accounting
```

The second handles:

```text
interactions
HP changes
age
encounters
death
score computation
parent selection
reproduction
```

when that lineage has the reproductive turn.

---

# `simulation.py` is the orchestrator

`simulation.py` does not implement every biological rule itself.

It defines **when** the major subsystems run.

That makes:

```python
step()
```

the central semantic boundary of the simulation.

If you need to understand one function before modifying the runtime:

```text
understand step()
```

---

# One tick

The current tick pipeline is:

```text
state.tick_count += 1

        ↓

for each lineage
    perceive
    evaluate neural network
    choose action
    move

        ↓

rebuild density fields

        ↓

update observed trail

        ↓

determine reproductive turn

        ↓

for each lineage
    punish
    reward
    count encounters
    age
    kill
    compute score
    reproduce if this lineage owns the turn

        ↓

record metrics if due

        ↓

print diagnostics if due
```

This ordering is part of simulation semantics.

It is not merely implementation detail.

---

# Why movement happens before ecological consequences

All lineages first make their movement decision from the current spatial state.

Then all movements happen.

Then density fields are rebuilt.

Only afterward are ecological consequences evaluated.

This avoids:

```text
R moves
R gets evaluated against partly updated world
G moves
G gets evaluated against another world
```

Processing order should not create an artificial ecological advantage.

---

# Rendering is not part of a tick

`step()` explicitly does **not** render.

This allows:

```text
for _ in range(256):
    step()

draw()
```

instead of:

```text
step()
draw()
step()
draw()
step()
draw()
...
```

when accelerated simulation is requested.

The simulation clock and rendering clock are separate concepts.

This is also what makes the same core step usable headlessly.

---

# Graphical driver

The graphical loop in `simulation.py` is conceptually:

```text
bootstrap world
      ↓
initialize renderer
      ↓
draw first frame
      ↓
┌────────────────────────┐
│ handle events          │
│                        │
│ if not paused:         │
│   step N times         │
│   draw once            │
│                        │
│ limit display FPS      │
└───────────↺────────────┘
```

Keyboard and mouse translation live in:

```text
controls.py
```

Pygame drawing lives in:

```text
rendering.py
```

The simulation therefore does not need to know which key means:

```text
pause
```

or how a critter is painted.

---

# Headless driver

The headless path uses:

```python
run_headless(...)
```

It shares:

```text
bootstrap_new_world()
step()
persistence.save()
persistence.load()
```

with the rest of the application.

There is no separate:

```text
headless simulation
```

with different physics.

That is an important architectural invariant.

A graphical experiment and a headless experiment should differ by observation and execution interface, not by evolutionary rules.

---

# CLI boundary

`cli.py` decides whether execution should be:

```text
graphical
```

or:

```text
headless
```

Pygame is imported only on the graphical branch.

That allows:

```text
python -m primordial_soup --new -d 50000
```

to run without initializing a graphical display.

The CLI also owns:

* argument validation;
* load/save-slot selection;
* seed input;
* duration input;
* quiet mode;
* version output.

See [Headless](headless.md).

---

# One current headless contract discrepancy

The `run_headless()` docstring currently says:

```text
ticks=None means "run forever"
```

but the implementation only enters its stepping loop when:

```python
ticks is not None and ticks > 0
```

So a programmatic call with:

```python
ticks=None
```

currently performs no ticks and proceeds toward saving.

The public CLI does not normally expose this mismatch because normal duration-based execution supplies an integer.

Still, this is an implementation/documentation debt worth fixing.

---

# Controls are translation, not simulation

`controls.py` translates user actions into changes to state or simulation commands.

Examples:

```text
SPACE
→ state.paused

U
→ select mutation parameter

↑
→ mutate selected runtime parameter

R
→ recreate world

Enter
→ convert discovery candidate to stable observed ID

click
→ select critter at coordinates

S / L
→ persistence
```

This keeps keyboard mechanics out of the simulation domain.

Evolution does not know what key was pressed.

It only sees the resulting state.

---

# Recreate boundary

The graphical:

```text
R
```

path deliberately begins with:

```python
state.reset_counters()
```

before allocating the new population.

This ordering is important because stable IDs are allocated during placement.

If reset happened afterward:

```text
new IDs allocated
      ↓
next_critter_id reset to 1
      ↓
runtime identity becomes inconsistent
```

The current ordering prevents that regression.

This lifecycle is covered by tests.

---

# Rendering

`rendering.py` owns Pygame visualization.

Its responsibilities include:

```text
window initialization
world rasterization
HUD
charts
inspection panel
discovery marker
observation marker
death marker
trail
brain heatmaps
fullscreen scaling
frame presentation
```

Rendering reads simulation state.

It should not define evolutionary rules.

---

# Discovery is recomputed as a view

The current discovery candidate is not stored as an authoritative individual identity.

It is derived from:

```text
current population
+
discovery criterion
+
lineage filter
```

when needed.

That makes discovery:

```text
a query
```

rather than:

```text
persistent simulation state
```

The yellow marker therefore reflects the current result of that query.

---

# Observation is persistent UI state

Observation stores:

```text
inspected_critter_id
```

as a stable ID.

The state helper:

```python
set_inspection_selection(...)
```

is the single transition point responsible for maintaining:

```text
selection
trail
death snapshot
```

coherently.

Its contract is:

```text
None → X
start observation and clear trail

X → Y
change subject and clear trail/snapshot

X → X
no-op; preserve trail

X → None
end session and clear observation artifacts
```

This prevents different input paths from implementing different observation semantics.

---

# Death snapshot boundary

When the observed critter is about to disappear during population compaction, `evolution.py` captures its final:

```text
agent row
genome
identity
lineage
death tick
```

before removal.

Then the normal dead-individual mask can compact:

```text
agents
pool
ids
```

without losing the observation record.

The snapshot therefore bridges:

```text
living runtime representation
```

and:

```text
post-mortem inspection
```

---

# Trail ownership

The trail is not part of the critter.

It is part of the observation session.

`simulation._update_trail()` resolves the stable observed ID after movement and appends the current position.

It runs before death processing.

Therefore, if the critter dies during that same tick:

```text
final moved position
```

is already in the trail.

After death, the ID no longer resolves in the live population, so no further points are added.

---

# Persistence boundary

`persistence.py` is the boundary between:

```text
optimized in-memory representation
```

and:

```text
stable serialized representation
```

This distinction is important.

Internally:

```text
pool
=
float32 ndarray
```

but the save format converts it to:

```text
list[list[float]]
```

Likewise, agent matrices are serialized into their canonical save representation.

That allows hot-path optimization to evolve independently from file representation where possible.

---

# Canonical persistence language

Internal English-code dictionary keys such as:

```text
color
pool
agents
field
```

do not dictate the save schema.

The persistence layer writes the canonical Portuguese save keys.

Translation is therefore explicit at the persistence boundary.

The UI language has no authority over persistence identifiers.

This prevents switching the interface to English from silently changing the file format.

---

# Transactional loading

Loading follows a strong architectural rule:

```text
PARSE
validate everything locally
do not mutate live state

        ↓

COMMIT
replace runtime state only after validation succeeds
```

This gives `persistence.load()` atomic behavior.

A malformed save should produce:

```text
old runtime state
+
error
```

not:

```text
half old world
+
half corrupted save
```

That invariant is tested directly.

The final `persistence.md` documents this contract in detail.

---

# Failed loads and randomness

A rejected load must also avoid consuming random draws.

Why?

Suppose:

```text
seed RNG
attempt invalid load
load fails
start experiment
```

If validation accidentally generated zones during the rejected parse phase, the random generator would advance.

The resulting experiment would differ from an otherwise identical seeded run that never attempted the invalid load.

The loader therefore defers RNG-consuming fallback work until the commit path.

Reproducibility includes failure paths.

---

# Internationalization

`i18n.py` translates presentation strings.

The architecture distinguishes:

```text
canonical identifiers
```

from:

```text
display labels
```

Examples of canonical values that remain stable include metric identifiers such as:

```text
populacao
hp_medio
geracao_maxima
```

English and Portuguese interfaces render different labels for them.

The underlying identifiers remain the same.

This is important for:

* saves;
* CSVs;
* tests;
* cross-language compatibility.

---

# Recording

`recording.py` owns GIF recording.

The authoritative recording lifecycle is held there.

`state.recording` is only a lightweight mirror that allows rendering to ask:

```text
should I capture this frame?
```

without pulling recording internals into the renderer.

Pillow is imported lazily.

Users who never record GIFs do not need the recording path active during normal simulation.

---

# Rendering captures complete frames

When recording is active, capture occurs after the complete rendered frame has been assembled.

The GIF therefore includes:

```text
world
HUD
charts
inspection panel
```

rather than only the simulation grid.

Recording represents what the user actually saw.

---

# Performance architecture

Performance is dominated by repeatedly processing populations with large genomes.

At maximum current population:

```text
333 critters / lineage
×
3 lineages
=
999 critters
```

Each genome contains:

```text
10,245 float32 values
```

So a full population near the configured ceiling can represent more than:

```text
10 million genome values
```

before considering agent state, fields and temporary arrays.

That is why data representation matters.

---

# Performance rule 1 — arrays over Python objects

Hot-path data lives primarily in NumPy arrays.

Instead of:

```text
1000 Python Critter objects
each containing Python lists
```

the runtime uses dense numerical matrices.

Benefits include:

```text
fewer Python allocations
better cache locality
vectorized operations
BLAS-backed neural math
simpler batch filtering
```

---

# Performance rule 2 — keep genomes stacked

The genome pool is already:

```text
[N, 10245]
```

in memory.

The previous design required repeated stacking before batch neural evaluation.

The current design removes that conversion.

The save boundary performs conversion only when serialization is actually needed.

---

# Performance rule 3 — reuse scratch memory

`senses.py` reuses per-lineage neural-input buffers.

Repeated per-tick allocations are avoided where practical.

This is especially important because perception runs:

```text
once per lineage
per tick
```

potentially hundreds of times between rendered frames.

---

# Performance rule 4 — vectorize where N is large

Examples include:

```text
vision sampling
neural evaluation
field construction
HP changes
alive/dead filtering
composite-score calculation
mutation sampling
```

These operate over population-sized arrays.

---

# Performance rule 5 — do not vectorize tiny work blindly

Not every loop is automatically bad.

For example, two-point crossover keeps a small Python loop for dependent cut generation.

The relevant `n` there is approximately the number of offspring in one reproductive event, not the whole population.

Architecture should optimize bottlenecks.

Not syntax aesthetics.

---

# Performance rule 6 — do not render every simulation tick

Simulation acceleration is implemented by executing several:

```python
step()
```

calls before one:

```python
draw()
```

This keeps graphics from becoming the limiting factor during faster evolutionary runs.

Headless mode removes rendering entirely.

---

# Core invariants

Several invariants define valid runtime state.

The most important are:

```text
pool.shape[0]
=
agents.shape[0]
=
ids.shape[0]
```

and:

```text
pool.shape[1]
=
GENOME_SIZE
```

and:

```text
agents.shape[1]
=
36
```

and:

```text
all stable IDs are unique
```

and:

```text
next_critter_id
>
every living ID
```

and:

```text
fields match derived world geometry
```

Violating these should be treated as a bug, not as a condition to silently repair.

---

# Why strict invariants?

Suppose:

```text
agents = 50 rows
pool   = 49 rows
ids    = 50 rows
```

Which critter owns the missing genome?

There is no principled answer.

Trying to:

```text
truncate
pad
guess
reconstruct
```

would fabricate simulation history.

The architecture therefore prefers:

```text
fail loudly
```

over:

```text
repair creatively
```

Persistence follows the same philosophy.

---

# Tests

The current bundle contains four test modules:

```text
tests/
├── test_identity.py
├── test_inspection_controls.py
├── test_inspection_identity.py
└── test_load_atomicity.py
```

They focus on the invariants most recently refactored.

---

# `test_identity.py`

Covers stable identity behavior such as:

```text
ID dtype is int64
IDs remain unique
founders receive non-colliding ranges
newborn allocation advances identity
array compaction preserves alignment
save/load preserves IDs
R → save → load preserves next_critter_id
```

One important regression test specifically protects the ordering:

```text
reset counters
before
allocate new IDs
```

during recreation.

---

# `test_inspection_controls.py`

Covers Discovery vs Observation:

```text
changing criterion does not change observation
changing lineage filter does not change observation
candidate respects filter
empty lineage yields no candidate
Enter observes current candidate
no candidate preserves current observation
new observation clears old death snapshot
click does not change discovery preferences
legacy inspection field names are absent
```

These are interaction contracts, not merely rendering tests.

---

# `test_inspection_identity.py`

Covers stable-ID observation:

```text
changing ID clears trail
same ID preserves trail
compaction preserves observed identity
death captures snapshot
death of another critter does not
new observation clears snapshot
load clears inspection session
ending observation clears artifacts
```

This protects the distinction between:

```text
identity
```

and:

```text
array position
```

---

# `test_load_atomicity.py`

Covers malformed-save rejection and strong load atomicity.

Its purpose is to ensure:

```text
invalid payload
      ↓
load returns failure
      ↓
live runtime remains unchanged
```

It also exercises failure-path behavior relevant to reproducibility, including avoiding unintended random-number consumption.

---

# Current testing gap

The bundled tests are concentrated around:

```text
identity
inspection
persistence atomicity
```

Those were the areas most heavily refactored recently.

The bundle does not currently show equivalent dedicated test modules for every other subsystem such as:

```text
brain
senses
genetics
movement
evolutionary scheduling
layout
CLI
```

Many of those modules do contain runtime assertions and structural invariants.

But assertions are not a complete substitute for behavioral tests.

Expanding coverage there would be a natural future hardening step.

---

# Dependency philosophy

The project is not organized into formal architectural layers enforced by package boundaries.

Instead, it uses disciplined module responsibilities.

A practical dependency model is:

```text
config
  ↓
layout
  ↓
state / world
  ↓
senses / brain / movement / genetics
  ↓
evolution
  ↓
simulation
  ↓
controls / rendering / CLI
```

with:

```text
persistence
i18n
recording
```

serving cross-cutting boundaries.

Because the system uses centralized state, some dependencies are necessarily less linear than this diagram.

The important rule is semantic ownership.

---

# Semantic ownership

A useful guide for future changes:

```text
"What are the constants?"
→ config.py

"What are the derived dimensions?"
→ layout.py

"What changes during a run?"
→ state.py

"What does a critter row mean?"
→ world.py

"What does a critter perceive?"
→ senses.py

"How does the neural network evaluate?"
→ brain.py

"How does position change?"
→ movement.py

"How are genomes created/recombined/mutated?"
→ genetics.py

"How are life, death and reproduction applied?"
→ evolution.py

"In what order does a tick happen?"
→ simulation.py

"What does a key or click mean?"
→ controls.py

"How is state drawn?"
→ rendering.py

"How does automation start the simulation?"
→ cli.py

"How is state serialized?"
→ persistence.py

"How is text translated?"
→ i18n.py

"How are rendered frames recorded?"
→ recording.py
```

If a change seems to belong to three of these simultaneously, that is a useful signal to reconsider the boundary.

---

# Keep simulation and presentation separate

One of the strongest current architectural properties is:

```text
step()
does not render
```

Likewise:

```text
rendering
should not determine evolutionary outcomes
```

and:

```text
inspection discovery
should not mutate simulation state
```

This separation allows:

* headless runs;
* accelerated simulation;
* reproducible testing;
* independent visualization changes;
* clearer experimental semantics.

Preserve it.

---

# Keep persistence at the edge

In-memory representation is optimized for execution.

Save representation is optimized for compatibility.

Those concerns should remain separate.

Do not redesign the hot path merely because pickle currently stores lists.

Do not silently alter persistence merely because NumPy representation changed.

The conversion belongs at the boundary.

---

# Keep identity separate from position

This rule is equally important:

```text
array index
=
temporary location

stable ID
=
identity
```

Anything long-lived should use the second.

Examples:

```text
inspection observation
death snapshot
saved individual identity
```

Anything operating only on the current vectorized batch may use the first.

Examples:

```text
matrix masks
parent-row lookup
density rebuilding
batch neural evaluation
```

Do not store positional indices across operations that can compact population arrays.

---

# Keep views out of domain state

Discovery is currently a good example.

The simulation does not store:

```text
the oldest critter
the most evolved critter
```

as authoritative state.

Those are queries over the current population.

Likewise, charts and inspection trails are views over simulation history.

This keeps analytical tooling from becoming hidden evolutionary input.

---

# Avoid silent repair

Several recent refactorings move the architecture toward explicit failure rather than silent accommodation.

Examples:

```text
invalid stable IDs
→ reject save

incompatible array shapes
→ reject save

failed load
→ preserve old state

no discovery candidate
→ preserve current observation
```

This is a useful general design principle.

In a simulation used for experiments, silently changing the data can be worse than crashing.

---

# Known architectural debts

The current bundle exposes a few issues worth keeping visible.

### Runtime local mutation scale

The control/state path exists, but genetics still reads the static config value.

The runtime control is therefore not authoritative.

### Reproduction HP bonus

The executable value is currently:

```text
50
```

and lives locally in `evolution.py`.

Some older commentary still describes:

```text
250
```

The code is authoritative.

The stale commentary should eventually be corrected.

### `run_headless(ticks=None)`

The docstring describes indefinite execution.

The implementation currently performs zero steps for `None`.

One of those contracts should change.

### Test concentration

Identity, inspection and load atomicity have good focused regression coverage.

Other simulation subsystems have less dedicated behavioral coverage in the current bundle.

These are debts.

They do not invalidate the architecture.

They are places where its contracts can be made sharper.

---

# How to add a new simulation mechanic

Suppose you want to introduce:

```text
energy cost for movement
```

A disciplined path would be:

```text
1. Define the static law in config.py.

2. Determine whether it requires new runtime state.

3. If it changes the agent record,
   update world.py and persistence compatibility deliberately.

4. Apply the mechanic in evolution.py
   at the correct point in the tick.

5. Do not implement the rule in rendering.py.

6. Add metrics only if the effect needs measurement.

7. Add tests for the new invariant.

8. Decide explicitly whether SAVE_VERSION,
   ARCHITECTURE_VERSION or GENOME_VERSION must change.

9. Update simulation/evolution/configuration documentation.
```

The important question is not:

> Where is it easiest to insert this line?

It is:

> Which module owns this concept?

---

# How to change the neural architecture

Changing:

```text
vision dimensions
hidden-layer sizes
recurrent size
output count
```

changes the genome layout.

That means several contracts move together:

```text
config
↓
GENOME_SIZE
↓
brain.split_weights
↓
population genome matrices
↓
persistence compatibility
```

This is not a cosmetic configuration change.

Treat it as a versioned architecture change.

---

# How to change the agent record

Adding a new per-critter state column affects:

```text
world.py
agent layout

senses.py
if perception consumes it

evolution.py
if lifecycle updates it

rendering.py
if inspection displays it

persistence.py
save/load structure

tests
alignment and compatibility

version contracts
potentially SAVE_VERSION
```

The 36-column matrix is therefore an internal compatibility boundary.

---

# How to change save behavior

Do not make persistence changes only in:

```text
save()
```

or only in:

```text
load()
```

A persistence change should be considered as a contract involving:

```text
serialization
validation
compatibility
commit semantics
tests
versioning
metrics sidecar
```

See [Persistence](persistence.md).

---

# How to change inspection

Preserve the separation:

```text
Discovery
=
query over current population

Observation
=
stable selected identity
```

New discovery criteria should normally belong in the population-query side.

New observation behavior should normally operate through:

```text
set_inspection_selection()
```

Do not bypass that helper and assign:

```text
state.inspected_critter_id
```

directly.

That would bypass trail and snapshot lifecycle rules.

---

# The architecture in one diagram

```text
                              STATIC
                               LAWS
                                │
                                ▼
                         ┌────────────┐
                         │ config.py  │
                         └─────┬──────┘
                               │
                               ▼
                         ┌────────────┐
                         │ layout.py  │
                         └─────┬──────┘
                               │
                               ▼
                      ┌───────────────────┐
                      │     state.py      │
                      │                   │
                      │ mutable run state │
                      └─────────┬─────────┘
                                │
              ┌─────────────────┼────────────────┐
              │                 │                │
              ▼                 ▼                ▼
        ┌──────────┐       ┌─────────┐      ┌──────────┐
        │ world.py │       │senses.py│      │genetics.py│
        └────┬─────┘       └────┬────┘      └────┬─────┘
             │                  │                 │
             │                  ▼                 │
             │             ┌─────────┐            │
             │             │brain.py │            │
             │             └────┬────┘            │
             │                  │                 │
             └───────────┬──────┴─────────┬───────┘
                         │                │
                         ▼                ▼
                   movement.py       evolution.py
                         │                │
                         └───────┬────────┘
                                 ▼
                        ┌────────────────┐
                        │ simulation.py  │
                        │                │
                        │     step()     │
                        └───────┬────────┘
                                │
                   ┌────────────┴────────────┐
                   │                         │
                   ▼                         ▼
           GRAPHICAL DRIVER            HEADLESS DRIVER
                   │                         │
          controls.py                     cli.py
          rendering.py                      │
          recording.py                      │
                   │                         │
                   └────────────┬────────────┘
                                │
                                ▼
                        persistence.py

                  i18n.py → presentation text
```

---

# In one sentence

Primordial Soup is a NumPy-first, module-oriented simulation in which static laws live in configuration, mutable experiment state is centralized, critters are represented as aligned numerical matrices with stable external identity, `simulation.step()` defines the authoritative tick order, and graphical, headless, inspection and persistence features all operate around that same simulation core.

The architecture is small enough to understand.

That is an architectural feature worth protecting.

---

# Related documentation

For the simulated universe:

→ [Simulation](simulation.md)

For evolutionary mechanics:

→ [Evolution](evolution.md)

For stable observation semantics:

→ [Inspection](inspection.md)

For static laws and defaults:

→ [Configuration](configuration.md)

For automated execution:

→ [Headless](headless.md)

For save/load compatibility and transactional loading:

→ [Persistence](persistence.md)
