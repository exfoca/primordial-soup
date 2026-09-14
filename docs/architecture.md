# 🏗️ Architecture

Primordial Soup is deliberately small.

It does not use an application framework, dependency-injection
container, entity hierarchy or object graph.

The architecture is primarily:

```text
Python modules
+
NumPy arrays
+
one centralized mutable simulation state
+
a separate transient graphical navigation state
+
explicit simulation functions
```

The design goal is not abstraction for its own sake. It is to keep the
simulation understandable, fast, deterministic enough for controlled
experiments, usable both graphically and headlessly, inspectable at the
level of individual critters, and safe to save and restore.

For the simulation model itself, start with [Simulation](simulation.md).

---

# The architecture at a glance

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
      │ mutable       │◀────────────▶│ spatial data  │
      │ simulation    │              └───────┬───────┘
      │ state         │                      │
      └───────┬───────┘                      │
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
            ┌─────────┴──────────┐                            cli.py
            │                    │                              │
      bootstrap +          input_dispatcher                     │
      GUI state            (event routing)                     │
            │                    │                              │
      ui_state.py         ┌──────┴──────┐                       │
      panels_defs.py      │             │                       │
            │          panels.py    controls.py                 │
            │             │             │                       │
            └─────────────┴──────┬──────┘                       │
                                 │                              │
                          DispatchResult                        │
                                 │                              │
                                 ▼                              │
                          rendering.py                          │
                          recording.py                          │
                                 │                              │
                                 └──────────────┬───────────────┘
                                                │
                                                ▼
                                        persistence.py
```

`i18n.py` sits beside these layers and translates presentation
strings. It does not redefine the simulation's canonical data
identifiers.

`ui_state.py` holds the transient navigation state of the graphical
application. It is neither simulation state nor persistence state:
nothing in it goes to a savegame, and nothing in it influences the
evolutionary rules.

---

# Project map

```text
primordial_soup/
├── __init__.py
├── __main__.py
├── cli.py
├── config.py
├── layout.py
├── state.py
├── ui_state.py
├── brain.py
├── genetics.py
├── senses.py
├── movement.py
├── world.py
├── evolution.py
├── simulation.py
├── rendering.py
├── panels.py
├── panels_defs.py
├── input_dispatcher.py
├── controls.py
├── persistence.py
├── i18n.py
└── recording.py
```

---

# Configuration and geometry

## `config.py`

The source of truth for static simulation constants.

Contains screen configuration, lineage definitions, population limits,
perception dimensions, neural architecture, HP rules, environmental
rules, selection pressure, reproduction gates, crossover configuration,
mutation configuration, inspection settings, rendering settings,
persistence versions, metrics configuration, recording configuration.

It also contains assertions that reject internally inconsistent
configurations.

The intent is: `config.py` is declared laws, not miscellaneous global
variables.

See [Configuration](configuration.md).

## `layout.py`

Derives geometry from configuration.

The user declares `SCREEN_WIDTH`, `SCREEN_HEIGHT`,
`INSPECTION_PANEL_WIDTH`, `TARGET_PIXEL_SCALE`, and the module derives
`pixel_scale`, `world_width`, `world_height`, `window_width`,
`window_height` once at import time.

The resulting values live in `layout.LAYOUT`.

Fullscreen does not rebuild this geometry. Rendering scales the
existing world instead.

---

# Runtime state

The center of the runtime architecture is `state.py`.

Primordial Soup does not distribute mutable **simulation** state across
dozens of objects. Instead, simulation-wide mutable state is
centralized.

Examples:

```text
population data
mutation settings
environmental-zone state
tick counters
births/deaths counters
stable identity counter
reproduction scheduler
inspection session
metric history
pause state
simulation speed
language
save slot
recording mirror
```

A deliberate exception exists for the graphical navigation layer:
`ui_state.py` holds transient state such as the focused panel, panel
cursors, panel scroll offsets, modal navigation state and floating-HUD
visibility.

`ui_state.py` is not part of the simulation and never reaches a
savegame.

---

# The population representation

There is no Python `Critter` object instantiated once per individual.

Each lineage owns several parallel NumPy structures:

```text
lineage
│
├── pool      [N, GENOME_SIZE] float32
├── agents    [N, AGENT_COLUMNS] float32
├── ids       [N] int64
└── field     [WORLD_WIDTH, WORLD_HEIGHT] int16
```

The invariant is:

```text
len(pool) == len(agents) == len(ids)
```

Row `i` in all three individual structures refers to the same critter.

---

# Why parallel arrays?

When critters die, arrays are compacted:

```python
agents = agents[alive]
pool = pool[alive]
ids = ids[alive]
```

The arrays remain aligned. That alignment is a fundamental runtime
invariant.

---

# The agent matrix

Each living individual occupies one row of a `float32 [N, 36]` matrix.

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

This one matrix contains body, location, life history, short-term
neural memory and selection metrics.

The neural hot path also uses `float32`. A silent promotion to
`float64` would still produce mathematically valid output. It would
just make the hottest part of the simulation considerably more
expensive.

`brain.evaluate_batch()` explicitly asserts the `float32` contract for
important inputs and weight matrices.

---

# Stable identity

Array position is not identity.

When critters die, arrays are compacted. If `ID 101` dies:

```text
before compaction:  index 0 → 100, index 1 → 101, index 2 → 102
after compaction:   index 0 → 100, index 1 → 102
```

Therefore `(lineage index, array index)` is a temporary locator, not a
persistent identity.

Each lineage maintains `ids: int64 [N]` parallel to `agents` and
`pool`.

Every new critter receives a global stable integer ID, allocated from
`state.next_critter_id`, which increases monotonically during a run.

Death does not reuse an ID.

## Resolving identity

When code needs the current array position of `critter #1847`, it calls
the identity-resolution path in `world.py`:

```text
stable ID
   ↓
search lineage ID arrays
   ↓
(lineage index, current row)
```

## Discovery uses positions; observation uses identity

This is an intentional boundary.

Discovery functions search the current arrays and naturally return
`(lineage_index, agent_index)`. Observation converts that temporary
result into a stable critter ID before storing the selection.

So changing discovery criteria cannot accidentally cause an observation
to drift after array compaction.

---

# World representation

`world.py` owns the spatial representation.

Every lineage contains a density field:

```text
field[world_width, world_height] int16
```

The field answers: how many individuals from this lineage currently
occupy this cell?

It is not the population itself. It is a spatial projection of the
population.

## Rebuilding fields

After movement:

```text
move everyone → fill_fields() → new spatial state
```

Newborns created later in the tick are inserted incrementally rather
than forcing another complete field rebuild.

## Environmental zones

Zones are represented separately as a boolean mask
`zones[world_width, world_height]`. Zone generation uses toroidal
distance.

---

# Perception

Perception lives in `senses.py`.

For each lineage, the module builds a batch of neural inputs:

```text
density fields + agent positions + agent internal state
        ↓
[N, NETWORK_INPUTS]
```

With the current configuration: `[N, 367]`.

## Toroidal vision

For each critter, perception samples the `11 × 11` neighborhood around
its current position. Array indices wrap around the world.

The result is three lineage-density channels plus four internal-state
inputs.

## Scratch buffers

Perception is called every tick. Allocating large temporary arrays every
time would create avoidable memory churn.

`senses.py` maintains reusable per-lineage input buffers sized up to
`MAX_POPULATION_PER_LINEAGE × NETWORK_INPUTS`.

Only the active prefix is used for the current population.

---

# Neural evaluation

Neural computation lives in `brain.py`.

The genome is a flat vector. `split_weights()` interprets it as `W1,
W2, W3, b1, b2, R`.

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

## Batched evaluation

The main entry point is `evaluate_batch(...)`.

```text
inputs              [N, 367]
weights             [N, 10245]
previous hidden     [N, 25]
        ↓
movement outputs    [N, 9]
new hidden state    [N, 25]
```

The new hidden state is stored back in the agent matrix for the next
tick.

## Why batch instead of one critter at a time?

The simulation does not normally execute:

```python
for critter in critters:
    evaluate_network(critter)
```

Instead, each lineage is evaluated as an array batch. That allows NumPy
to perform the heavy matrix operations in compiled code.

The main neural operations use matrix multiplication through `@` rather
than `np.einsum` for the current batched matrix-vector shapes because it
measured better throughput in the tested NumPy builds.

---

# Genetics

Genetic operators live in `genetics.py`.

A population genome pool is stored as `float32 [N, GENOME_SIZE]`, not
`list[np.ndarray]`.

This matters because neural evaluation can consume the matrix directly.
There is no need to stack all genomes on every tick.

## Crossover

Supports `uniform`, `blocks`, `two_points`.

```text
parent A ─┐
          ├─ crossover mask ─→ offspring batch
parent B ─┘
```

Parental genomes are broadcast as read-only views. Only the offspring
matrices need to be materialized.

## Mutation

Mutation operates in-place on offspring batches.

The dispatcher selects between `surgical` and `two_scales` based on
static configuration.

For `two_scales`:

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

Gene sampling uses `argpartition` rather than looping over each mutant
with repeated `np.random.choice()` calls.

---

# Movement

Movement lives in `movement.py`.

The neural output is reduced to one of nine actions. The position update
is toroidal:

```text
new_x = (x + dx) mod width
new_y = (y + dy) mod height
```

No wall collision handling. No edges. Only modulo arithmetic.

---

# Evolution

The life-cycle mechanics live primarily in `evolution.py`.

Two important high-level responsibilities:

```text
evaluate_and_move()
punish_reward_and_reproduce()
```

The first handles perception, neural evaluation, hidden-state update,
movement choice, movement, exploration accounting.

The second handles interactions, HP changes, age, encounters, death,
score computation, parent selection, reproduction.

`simulation.py` does not implement every biological rule itself. It
defines **when** the major subsystems run.

`step()` is the central semantic boundary of the simulation. If you need
to understand one function before modifying the runtime: understand
`step()`.

---

# One tick

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

## Why movement happens before ecological consequences

All lineages first make their movement decision from the current spatial
state. Then all movements happen. Then density fields are rebuilt. Only
afterward are ecological consequences evaluated.

This avoids processing order creating an artificial ecological
advantage.

---

# Rendering is not part of a tick

`step()` explicitly does **not** render.

This allows:

```text
for _ in range(256):
    step()

draw()
```

instead of `step / draw / step / draw / ...` when accelerated simulation
is requested.

The simulation clock and rendering clock are separate concepts.

This is also what makes the same core step usable headlessly.

---

# Graphical driver

The graphical loop in `simulation.py`:

```text
bootstrap world
      ↓
reset UI state
      ↓
register default panels
      ↓
initialize renderer
      ↓
register adapters and global accelerators
      ↓
draw first frame
      ↓
┌────────────────────────────┐
│ process_events()           │
│   → DispatchResult         │
│                            │
│ if result.flow == EXIT:    │
│   shutdown and return      │
│                            │
│ if not paused:             │
│   step N times             │
│                            │
│ if redraw needed:          │
│   draw once                │
│                            │
│ limit display FPS          │
└───────────↺────────────────┘
```

Event translation lives in `input_dispatcher.py`.

Panel grammar lives in `panels.py`.

Concrete panels and their items live in `panels_defs.py`.

Reusable domain actions live in `controls.py`.

Pygame drawing lives in `rendering.py`.

A consequence of this split is that **handlers do not call `draw()`**.
They return a `DispatchResult` with `redraw=True` when the display should
be refreshed, and the graphical loop keeps the authority over when a
frame is actually rendered.

---

# Input routing is translation, not simulation

The input boundary is split into three layers.

## `input_dispatcher.py`

The single point that turns raw pygame events into either a global
command, a panel focus change, or a contextual navigation action.

Its contract is to return `DispatchResult` values and never to call
`rendering.draw()`.

## `panels.py`

The generic grammar of the interface: `Panel`, `Item`, `ItemKind`,
`DispatchResult`, `Flow`, and the registry of panels.

It does not know what a concrete panel does.

## `panels_defs.py`

Concrete composition of `Inspection`, `Configuration`, `Metrics`,
`Session`, `Tools`, binding each item to a real operation.

## `controls.py`

Reusable domain/UI actions (`action_recreate`, `action_save`,
`action_load`, `action_toggle_zones`, `action_toggle_recording`,
`action_cycle_save_slot`, `action_print_state`, `action_heal_all`) shared
by panel handlers and by global accelerators.

`controls.py` is not the only input boundary anymore: it provides
operations, while `input_dispatcher.py` decides how events reach them.

---

# Headless driver

The headless path uses `run_headless(...)`.

It shares `bootstrap_new_world()`, `step()`, `persistence.save()`,
`persistence.load()` with the rest of the application.

There is no separate "headless simulation" with different physics.

A graphical experiment and a headless experiment differ by observation
and execution interface, not by evolutionary rules.

## Headless tick contract

`run_headless()` normalizes `ticks=None` to `0` before entering the
stepping loop:

```python
ticks_to_run = 0 if ticks is None else ticks
if ticks_to_run > 0:
    ...
```

So:

```text
ticks=None → 0 ticks
ticks=0    → 0 ticks
ticks=N>0  → exactly N ticks
```

The CLI normally never passes `None`: `-d/--duration` requires an
explicit non-negative integer, and `cli.main()` rejects `-d` without
`-l/--load` or `--new`.

Coverage: `tests/test_headless_ticks.py`.

---

# CLI boundary

`cli.py` decides whether execution should be graphical or headless.

Pygame is imported only on the graphical branch.

See [Headless](headless.md).

---

# Recreate boundary

The graphical **R** path deliberately begins with:

```python
state.reset_counters()
```

before allocating the new population.

This ordering is important because stable IDs are allocated during
placement. If reset happened afterward, runtime identity would become
inconsistent.

This lifecycle is covered by tests.

---

# Rendering

`rendering.py` owns Pygame visualization.

Its responsibilities include window initialization, world
rasterization, floating HUD, charts, panel rendering, discovery marker,
observation marker, death marker, trail, brain heatmaps, fullscreen
scaling and frame presentation.

Rendering reads simulation state. It does not define evolutionary rules.

## Discovery is recomputed as a view

The current discovery candidate is not stored as an authoritative
individual identity. It is derived from the current population,
discovery criterion and lineage filter when needed.

## Observation is persistent UI state

Observation stores `inspected_critter_id` as a stable ID.

The state helper `set_inspection_selection(...)` is the single
transition point responsible for maintaining selection, trail and death
snapshot coherently.

## Death snapshot boundary

When the observed critter is about to disappear during population
compaction, `evolution.py` captures its final agent row, genome,
identity, lineage and death tick before removal.

## Trail ownership

The trail is not part of the critter. It is part of the observation
session.

`simulation._update_trail()` resolves the stable observed ID after
movement and appends the current position.

---

# Persistence boundary

`persistence.py` is the boundary between the optimized in-memory
representation and the stable serialized representation.

Internally: `pool = float32 ndarray`. In the save format: `list[list[float]]`.

That allows hot-path optimization to evolve independently from file
representation where possible.

## Canonical persistence language

Internal English-code dictionary keys do not dictate the save schema.
The persistence layer writes the canonical Portuguese save keys.

Translation is explicit at the persistence boundary. The UI language
has no authority over persistence identifiers.

## Transactional loading

Loading follows a strong architectural rule:

```text
PARSE
validate everything locally
do not mutate live state

        ↓

COMMIT
replace runtime state only after validation succeeds
```

A malformed save should produce `old runtime state + error`, not a half
old world plus half corrupted save.

## Failed loads and randomness

A rejected load must also avoid consuming random draws.

Reproducibility includes failure paths.

---

# Internationalization

`i18n.py` translates presentation strings.

The architecture distinguishes canonical identifiers from display
labels. Metric identifiers such as `populacao`, `hp_medio`,
`geracao_maxima` remain stable. English and Portuguese interfaces render
different labels for them.

Important for saves, CSVs, tests and cross-language compatibility.

---

# Recording

`recording.py` owns GIF recording.

The authoritative recording lifecycle is held there.
`state.recording` is a lightweight mirror.

Pillow is imported lazily. Users who never record GIFs do not need the
recording path active during normal simulation.

Rendering captures complete frames after the frame has been assembled.

---

# Performance architecture

At maximum current population:

```text
333 critters / lineage × 3 lineages = 999 critters
```

Each genome contains `10,245 float32` values. So a full population near
the configured ceiling can represent more than 10 million genome values
before considering agent state, fields and temporary arrays.

## Rules

**Arrays over Python objects.** Hot-path data lives primarily in NumPy
arrays.

**Keep genomes stacked.** The genome pool is already `[N, 10245]` in
memory. The save boundary performs conversion only when serialization
is actually needed.

**Reuse scratch memory.** `senses.py` reuses per-lineage neural-input
buffers.

**Vectorize where N is large.** Vision sampling, neural evaluation,
field construction, HP changes, alive/dead filtering, composite-score
calculation, mutation sampling operate over population-sized arrays.

**Do not vectorize tiny work blindly.** Two-point crossover keeps a
small Python loop for dependent cut generation. The relevant `n` there
is approximately the number of offspring in one reproductive event, not
the whole population.

**Do not render every simulation tick.** Simulation acceleration is
implemented by executing several `step()` calls before one `draw()`.

---

# Core invariants

```text
pool.shape[0] == agents.shape[0] == ids.shape[0]
pool.shape[1] == GENOME_SIZE
agents.shape[1] == AGENT_COLUMNS
all stable IDs are unique
next_critter_id > every living ID
fields match derived world geometry
```

Violating these should be treated as a bug, not as a condition to
silently repair.

Why strict invariants? Suppose `agents = 50 rows`, `pool = 49 rows`,
`ids = 50 rows`. Which critter owns the missing genome? There is no
principled answer. Trying to truncate, pad, guess or reconstruct would
fabricate simulation history.

The architecture therefore prefers **fail loudly** over **repair
creatively**.

Persistence follows the same philosophy.

---

# Tests

The suite is organized by responsibility rather than by file count.

Broad areas currently covered:

```text
CLI / headless
    argument parsing contract, mutual exclusion of --new and --load,
    tick semantics of run_headless

identity / inspection
    stable IDs, compaction, save/load of IDs, discovery vs observation,
    click selection, death snapshots, trail lifecycle

input dispatcher
    full-queue processing, redraw accumulation, Shift+Tab using
    event.mod, panel cursor initialization, ESC hierarchy, adapter
    registration, structural-key protection

rendering / UI
    Telemetry HUD composition, Command Dock anchoring, floating HUD
    gate, vision heatmaps per subject state, panel viewport clip and
    scroll, language-reactive labels

persistence
    atomicity of load rejection (no mutation, no RNG consumption),
    semantic ranges of scalar fields, bool strictness, malformed
    payloads

runtime configuration
    local mutation scale reaching the effective mutation path,
    reproduction HP bonus applied once per event

i18n
    presence and content of HUD keys across all languages, dynamic
    lineage header localization

continuation
    checkpoint == exact continuation of the simulation, including the
    reproductive scheduler and both RNG states
```

The suite evolves with the codebase. This document intentionally does
not enumerate test modules by filename.

---

# Dependency philosophy

The project is not organized into formal architectural layers enforced
by package boundaries. Instead, it uses disciplined module
responsibilities.

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

with `persistence`, `i18n`, `recording`, `ui_state`, `panels`,
`panels_defs`, `input_dispatcher` serving cross-cutting boundaries.

Because the system uses centralized state, some dependencies are
necessarily less linear than this diagram. The important rule is
semantic ownership.

---

# Semantic ownership

```text
"What are the constants?"             → config.py
"What are the derived dimensions?"    → layout.py
"What changes during a run?"          → state.py
"What is graphical navigation?"       → ui_state.py
"What does a critter row mean?"       → world.py
"What does a critter perceive?"       → senses.py
"How does the neural network eval?"   → brain.py
"How does position change?"           → movement.py
"How are genomes created/recombined?" → genetics.py
"How are life, death and reproduction applied?" → evolution.py
"In what order does a tick happen?"   → simulation.py
"What does a key or click mean?"      → input_dispatcher.py
"What does a panel contain?"          → panels_defs.py
"What is the generic UI grammar?"     → panels.py
"What reusable action exists?"        → controls.py
"How is state drawn?"                 → rendering.py
"How does automation start the simulation?" → cli.py
"How is state serialized?"            → persistence.py
"How is text translated?"             → i18n.py
"How are rendered frames recorded?"   → recording.py
```

If a change seems to belong to three of these simultaneously, that is a
useful signal to reconsider the boundary.

---

# Keep simulation and presentation separate

One of the strongest current architectural properties is:

```text
step() does not render
```

Likewise:

```text
rendering should not determine evolutionary outcomes
inspection discovery should not mutate simulation state
```

This separation allows headless runs, accelerated simulation,
reproducible testing, independent visualization changes, clearer
experimental semantics.

Preserve it.

---

# Keep persistence at the edge

In-memory representation is optimized for execution. Save representation
is optimized for compatibility.

Do not redesign the hot path merely because pickle currently stores
lists. Do not silently alter persistence merely because NumPy
representation changed.

The conversion belongs at the boundary.

---

# Keep identity separate from position

```text
array index = temporary location
stable ID   = identity
```

Anything long-lived should use the second.

Do not store positional indices across operations that can compact
population arrays.

---

# Keep views out of domain state

Discovery is a query over the current population. The simulation does
not store "the oldest critter" as authoritative state.

Analytical tooling does not become hidden evolutionary input.

---

# Avoid silent repair

Invalid stable IDs, incompatible array shapes, failed loads, missing
discovery candidates should all fail loudly rather than silently
accommodate.

In a simulation used for experiments, silently changing the data can be
worse than crashing.

---

# How to add a new simulation mechanic

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

The important question is not "where is it easiest to insert this line?".
It is "which module owns this concept?".

---

# How to change the neural architecture

Changing vision dimensions, hidden-layer sizes, recurrent size or output
count changes the genome layout.

That means several contracts move together:

```text
config → GENOME_SIZE → brain.split_weights
       → population genome matrices → persistence compatibility
```

Treat it as a versioned architecture change.

---

# How to change the agent record

Adding a new per-critter state column affects `world.py` agent layout,
possibly `senses.py`, `evolution.py`, `rendering.py`, `persistence.py`,
tests, version contracts.

The 36-column matrix is an internal compatibility boundary.

---

# How to change save behavior

Do not make persistence changes only in `save()` or only in `load()`.

A persistence change involves serialization, validation, compatibility,
commit semantics, tests, versioning, metrics sidecar.

See [Persistence](persistence.md).

---

# How to change inspection

Preserve the separation:

```text
Discovery = query over current population
Observation = stable selected identity
```

New discovery criteria belong in the population-query side. New
observation behavior should operate through `set_inspection_selection()`.

Do not bypass that helper and assign `state.inspected_critter_id`
directly.

---

# In one sentence

Primordial Soup is a NumPy-first, module-oriented simulation in which
static laws live in configuration, mutable experiment state is
centralized in `state.py`, transient graphical navigation state is
separated in `ui_state.py`, critters are represented as aligned
numerical matrices with stable external identity, `simulation.step()`
defines the authoritative tick order, and graphical, headless,
inspection and persistence features all operate around that same
simulation core.

The architecture is small enough to understand. That is an architectural
feature worth protecting.

---

# Related documentation

→ [Simulation](simulation.md)
→ [Evolution](evolution.md)
→ [Inspection](inspection.md)
→ [Configuration](configuration.md)
→ [Headless](headless.md)
→ [Persistence](persistence.md)
