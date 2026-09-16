# 🏗️ Architecture

Primordial Soup is a small simulation, but it has one architectural problem common to much larger systems:

```text
everything affects everything
```

Critters move. Movement changes spatial density. Spatial density changes ecology. Ecology changes survival. Survival changes reproduction. Reproduction changes populations. Populations change perception. And then the next tick starts.

The architecture exists to keep those relationships explicit without turning the codebase into one enormous `simulation.py` with opinions about Pygame, genetics, persistence, theology, and CSV files.

**This is the single authority for module boundaries, ownership, the tick lifecycle, and architectural invariants.** The rules being implemented live in [World Rules](world-rules.md); the HOT configuration boundary in [Runtime Configuration](runtime-config.md); the checkpoint contract in [Persistence](persistence.md).

---

# Architectural model

At a high level, Primordial Soup is divided into four concerns:

```text
┌──────────────────────────────────────────────┐
│                 Presentation                 │
│ UI · input · rendering · feedback · audio    │
└──────────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│           Orchestration             │
│ simulation · bootstrap · controls   │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│          Simulation model           │
│ world · ecology · evolution         │
│ senses · brain · movement · genetics│
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│             State                   │
│ state · runtime rules · geometry    │
└─────────────────────────────────────┘
```

Persistence crosses these layers deliberately because a checkpoint must serialize the complete continuation state of the world.

The important rule is not strict theoretical layering.

It is **clear ownership**.

---

# 🧭 Entry points

Execution begins with `python -m primordial_soup`. The path is `__main__.py → cli.main()`.

The CLI chooses between two execution modes: **graphical** and **headless**. Both eventually use the same `simulation.step()`.

This is a central architectural invariant.

There is one simulation. There are two ways to operate it.

---

## Graphical mode

The graphical composition path is approximately:

```text
cli.main()
    ↓
simulation.run()
    ↓
bootstrap_new_world()
    ↓
reset UI state
    ↓
load operator preferences
    ↓
register panels
    ↓
initialize rendering
    ↓
initialize audio
    ↓
apply Music/SFX preferences
    ↓
register audio.handle_feedback as feedback sink
    ↓
emit WORLD_GENERATED
    ↓
register input adapters
    ↓
event loop
```

Audio preferences are applied before `WORLD_GENERATED` is emitted. A world with SFX disabled in preferences therefore does not play `generate_world.wav` at graphical boot. This ordering is a real composition decision, not an accident.

`simulation.run()` is the graphical **composition root**. It is where otherwise independent pieces are connected. That is why dispatcher callbacks and concrete panels are registered there instead of appearing through import-time side effects.

---

## Headless mode

Headless execution uses `simulation.run_headless()`. Its lifecycle is simpler:

```text
create or load world
    ↓
optionally seed RNGs
    ↓
run N × step()
    ↓
optionally save
    ↓
return status
```

Headless mode does not initialize the graphical interface or operator preferences. Pygame-dependent modules are imported lazily only by the graphical path.

This boundary is intentional:

```text
simulation core ≠ graphical application
```

A batch experiment should not require a display server merely because somewhere in the repository a rectangle needs drawing.

`run_headless()` does not initialize the audio backend and does not register a graphical feedback sink.

---

# ⏱️ `simulation.step()` is the clock

`simulation.step()` is the canonical owner of tick ordering. One call means exactly one simulation tick.

Current lifecycle:

```text
1. perceive → decide → move
        │
        ▼
2. rebuild spatial fields
        │
        ▼
3. compute ecology
        │
        ▼
4. apply ecology + mortality
        │
        ▼
5. reproductive scheduler
        │
        ▼
6. reproduce eligible lineage
        │
        ▼
7. rebuild spatial fields
        │
        ▼
8. collect metrics when due
```

`step()` does not render. `step()` also does not emit audio and does not know the audio backend.

The simulation decides **what happens**. The caller decides **when humans get to see it**.

The sequence above is part of the model. Moving reproduction before ecology, for example, would allow newborns to participate in ecological resolution during their own birth tick. Moving mortality before all ecological deltas were known could make lineage iteration order influence survival.

Changing tick ordering is therefore not a refactor unless behavior remains identical.

Sometimes moving three lines of code is architecture. Sometimes it is creating a different universe.

---

# 🌍 World representation

`world.py` owns the concrete representation of populations and spatial state.

Each lineage is represented by a structure conceptually equivalent to:

```text
lineage
├── id
├── color
├── pool       → [N, GENOME_SIZE] float32
├── agents     → [N, AGENT_COLUMNS] float32
├── ids        → [N] int64
└── field      → [WORLD_WIDTH, WORLD_HEIGHT]
```

The critical population invariant is:

```text
len(pool) == len(agents) == len(ids)
```

The three arrays describe the same organisms by row. If row 17 is removed because that critter dies, row 17 must disappear from all three structures.

Ecology performs this compaction in lockstep.

---

## Stable identity

Array position is not organism identity.

`world.py` owns ID allocation and resolution. Stable IDs survive population compaction.

This allows Observation, persistence, and death snapshots to refer to an organism without depending on its current row inside an ndarray.

```text
stable ID   → identity
array index → current storage location
```

Confusing the two eventually results in observing the wrong corpse.

---

## Spatial fields

Each lineage maintains a density field. `fill_fields()` rebuilds these fields from current positions.

The fields are snapshots of how many critters of this lineage occupy each world cell. They are consumed by perception and ecology.

`fill_fields()` is deliberately called twice during a tick: after movement (to establish the ecology snapshot) and after mortality + reproduction (to establish the final spatial state for the next tick).

---

# 👁️ Perception → brain → movement

Individual behavior is orchestrated by `evolution.evaluate_and_move()`, which owns the per-lineage cognitive pipeline: senses → brain → action selection → movement.

Ecology does not belong here. That responsibility has its own module.

## `senses.py`

Transforms world state into neural input.

The module performs perception in batches and uses reusable scratch buffers to avoid allocating large temporary arrays every tick.

It does not decide behavior. It describes what the brain receives.

One deliberate mutation exists: when sensing a real agent matrix, the calculated low-HP flag is written back into the corresponding lifetime-state column so stored state matches what the network actually consumed.

## `brain.py`

Owns neural evaluation.

Input: neural inputs, genomes, previous recurrent hidden state. Output: action scores, new recurrent hidden state.

The brain does not know about predators, nests, reproduction, Pygame, save files, or panels. It performs numerical evaluation of the neural architecture encoded by the genome.

That ignorance is useful.

## `movement.py`

Converts the selected action into toroidal position changes.

It owns the mapping from action index to wrapped position. It does not decide which action is best. It does not calculate ecological consequences.

Moving into a predator is somebody else's department.

---

# 🩸 Ecology

`ecology.py` is the authority for ecological semantics. It owns base metabolism, environmental zone effects, same-lineage overcrowding, predation, nest protection, encounters, triad resolution, mortality, population compaction, and post-ecology composite score.

The design deliberately separates ecology into two phases: **compute** and **apply**.

## Compute phase

`compute_ecology_resolution()` reads a frozen post-movement world snapshot and produces an `EcologyResolution`.

It does not mutate HP, age, encounters, population arrays, birth/death counters, or density fields.

The one deliberate side effect is NumPy RNG consumption when triad cells require random relation selection. That RNG is part of persisted simulation history. So the function is deterministic relative to complete simulation state, but it is not mathematically pure.

## Apply phase

`apply_ecology_resolution()` applies the resolution globally:

```text
A. apply HP / encounter deltas and age
B. determine all alive masks
C. capture death snapshots and count deaths
D. compact ids / pool / agents in lockstep
E. recompute composite scores
```

Mortality is therefore determined only after all ecological effects for the snapshot are known.

This is what prevents iteration order from becoming an undocumented law of nature.

> If Red survives because its array happened to be processed first, natural selection has been replaced by Python iteration semantics.

---

# 🧬 Evolution and reproduction

`evolution.py` owns reproductive orchestration.

The reproductive scheduler itself lives in `state`: `reproduction_cooldown` and `reproduction_turn`.

When `simulation.step()` grants a lineage its turn, `reproduce_lineage(lineage)` handles eligibility, ranking, parent-pool construction, parent selection, genetic recombination, mutation, child construction, nest spawning, stable-ID allocation, parent HP reward, and population append.

`reproduce_lineage(index)` returns the number of newborns actually appended in that call. Zero covers an extinct lineage, no eligible parents, exhausted attempts, and no reproducible pool.

The function does not emit UI events and does not draw.

Reproduction does **not** rebuild density fields. New organisms are appended and become spatially visible when `simulation.step()` performs its final `fill_fields()`.

That keeps the tick boundary explicit.

---

# 🧬 Genetics

`genetics.py` owns transformations of genomes: random genome generation, random population generation, crossover, and mutation.

It knows genetic layout through structural configuration. It does not know HP, age, fitness gates, nests, population scheduling, UI, or persistence.

Those decisions belong to higher-level orchestration.

The distinction is:

```text
genetics.py   → How do two genomes produce descendants?
evolution.py  → Which organisms reproduce, when, and where?
```

---

# 🪺 Geometry

World geometry is deliberately split.

## `layout.py`

Derives physical dimensions from display/world configuration: screen size, sidebar width, pixel scale, world width, world height.

The world and sidebar occupy separate regions. Rendering should consume this geometry rather than independently inventing dimensions.

## `nest_geometry.py`

A low-level geometry module with no global state, no config dependency, no world dependency, and no Pygame dependency.

Dimensions and radii are passed explicitly. It is the canonical authority for toroidal distance, nest disks, nest rings, coordinate wrapping, nest membership, nest overlap, and nest ↔ zone intersection.

This allows the same geometry functions to operate on the active world and on an uncommitted checkpoint being validated, without temporarily corrupting global state.

Geometry should be boring.

Boring geometry prevents exciting persistence bugs.

---

# ⚙️ Configuration architecture

Configuration has three distinct levels:

```text
config.py → runtime_rules.py → state.runtime_rules
```

## `config.py`

Structural constants, defaults, and validation limits: neural dimensions, genome size, population ceilings, nest radius, world structure, default runtime values, min/max limits, save format versions.

Changing a structural constant may change the model itself.

## `runtime_rules.py`

Defines the immutable `RuntimeRules` contract. It does not import state, does not know the UI, does not know Pygame, and does not own global state.

A rule update follows: current rules → create candidate → validate candidate → return candidate.

Invalid candidates never mutate the original object.

## `state.runtime_rules`

`state.py` owns the currently active `RuntimeRules` reference.

Replacing active laws follows: validate → commit reference.

Consumers read the current object. They do not maintain shadow copies of runtime configuration.

This gives one authoritative answer to: **what are the laws of this universe right now?**

---

# 🧠 Shared state

`state.py` contains shared runtime state required across simulation modules. Major categories include population, runtime rules, zones, zone centers, nests, tick counters, birth/death counters, the stable-ID allocator, the reproduction scheduler, metrics history, observation state, the recent death archive, runtime execution controls, and selected operator preferences.

Not all of these have the same persistence semantics. That distinction is intentional.

For example:

```text
population            → checkpoint state
RNG scheduler phase   → checkpoint state
runtime rules         → checkpoint state

language              → operator preference
active save slot      → operator preference
Music/SFX enabled     → operator preference
inspection trail      → view state
recording             → tool state
```

Music and SFX are operator preferences. They do not belong to `RuntimeRules`, they do not affect physics, ecology, genetics, selection, or reproduction, and they are not serialized in world checkpoints.

The persistence boundary decides what belongs to the universe.

---

# 👁️ Observation as a bridge

Observation is slightly special. The graphical navigation state lives in `ui_state.py`, but the identity of the observed critter and its death snapshot live in `state.py`.

This is deliberate. Observation must survive array compaction, panel changes, organism death, and simulation ticks.

Ecology captures **every** death into a `DeathSnapshot` before the population arrays are compacted, regardless of whether the organism was observed. The same snapshot is installed on the active Inspection when the dead organism is the one currently being followed.

Therefore Observation crosses the simulation/presentation boundary through a very narrow contract: stable critter ID, death snapshot, trail.

It does not affect ecological outcomes.

---

# 🧭 Application versioning

Primordial Soup separates several independent version axes. They evolve on their own schedules and must not be conflated.

```text
Application release    → _version.py
Checkpoint schema      → SAVE_VERSION
Neural architecture    → ARCHITECTURE_VERSION
Genome layout          → GENOME_VERSION
Preferences schema     → PREFS_VERSION
```

The application version has exactly one manual source: `_version.py`.

Everything else derives from it: the package re-export, `config.WORLD_VERSION`, the CLI `--version`, and setuptools' dynamic metadata.

Documentation materializes the current release for the reader, but is not derived at runtime.

A normal release bump does not require editing `config.py`, `cli.py`, `pyproject.toml`, or tests. They follow the canonical module.

These versions are independent by design:

```text
software release          → bump _version.py only
checkpoint incompatibility → bump SAVE_VERSION
neural-network contract   → bump ARCHITECTURE_VERSION
genome layout change      → bump GENOME_VERSION
prefs.json schema change  → bump PREFS_VERSION
```

A release may ship without a new `SAVE_VERSION`. A `SAVE_VERSION` may change during development without representing a semantic application release by itself.

---

# 💾 Persistence

`persistence.py` is the checkpoint boundary. It serializes the state required for exact continuation and validates it on load.

The important architectural pattern is:

```text
SAVE:  runtime state → validate → serialize temp → atomic replace
LOAD:  file → parse locally → validate everything → single commit boundary
```

A rejected load must not partially modify the running universe.

Persistence also does not regenerate missing world geometry.

Zones and nests are restored from the checkpoint.

See [Persistence](persistence.md) for the full contract.

---

# 👤 Operator preferences

`prefs.py` is deliberately separate from world persistence.

There are two different forms of persistence:

```text
checkpoint (.pkl)  → the universe
prefs.json         → the operator
```

Preferences include interface choices such as language, active save slot, discovery settings, and floating HUD visibility.

Architectural invariants:

```text
preferences do not change simulation physics
savegame load does not overwrite preferences
headless execution does not read or write preferences
```

A universe should not change language because somebody loaded a dinosaur-era checkpoint.

---

# 🖥️ Presentation architecture

The graphical interface is split into several smaller responsibilities:

```text
Pygame events → input_dispatcher → panels / controls → domain state
domain state + ui_state → rendering → screen
```

## `ui_state.py`

Owns transient graphical-navigation state: active panel, last panel, panel cursors, scroll positions, modal state, transient notices, floating HUD visibility.

It is presentation state. Simulation modules must not depend on it. Nothing in `ui_state.py` belongs in a world checkpoint.

## `panels.py`

Defines the UI grammar: `Panel`, `Item`, `ItemKind`, `DispatchResult`, `Flow`, and the panel registry.

It does not implement domain-specific panel behavior. Think of it as the vocabulary from which the interface is constructed.

## `panels_defs.py`

Composes the concrete panels: Inspection, Configuration, Metrics, Session, Tools.

This is intentionally where panel definitions meet domain operations. Unlike `panels.py`, this module is allowed to know about state, world, persistence, recording, preferences, and i18n.

Importing it does not automatically register panels. Registration is explicit during graphical bootstrap.

## `input_dispatcher.py`

Owns input-routing policy. It translates Pygame events into actions but does not render.

Its routing order is broadly: exit request → modal → global command → panel activation → Tab / Shift+Tab structural cycling → panel-local input → world interaction.

`Tab` and `Shift+Tab` are routed before the "panel-focused" gate, so they work from any focus state, including world.

The dispatcher is intentionally ignorant of graphical geometry. Tab hit-testing is injected from rendering. This prevents input routing from becoming a second, slightly wrong copy of layout logic.

## `controls.py`

Contains reusable operator actions such as new world, save, load, heal all, toggle zones, toggle recording, cycle save slot, and print state.

These actions are shared by panel handlers and global accelerators, so orchestration is not duplicated in two UI paths. Actions return `DispatchResult`; the graphical loop decides when to redraw.

## `rendering.py`

Owns pixels. It reads simulation and UI state and renders world, zones, nests, critters, inspection overlays, HUD, command dock, sidebar, charts, and modals. It also owns screen-space geometry such as clickable panel-tab rectangles.

Rendering does not own simulation progression. Calling `draw()` must not advance the universe.

### Camera and world viewport

The renderer owns two distinct concepts: the **world viewport** (screen-space rectangle where the world is displayed) and the **camera** (world-space description of which logical region is observed).

The viewport answers *where to draw*. The camera answers *what region to draw*. They change independently: a resize alters the viewport and leaves the camera alone.

Camera state is presentation state. It is not simulation state, not `RuntimeRules`, not checkpoint state, and not preference persistence.

Zoom never changes logical world dimensions, pixel scale, or layout. Rendering the camera must never advance the simulation.

---

# 🌐 Internationalization

`i18n.py` translates display strings. Canonical internal values remain stable.

Examples:

```text
mutation mode → canonical identifier
panel label   → localized display value
```

Persistence formats and internal semantics are not rewritten when the UI language changes. Localization happens at the presentation boundary.

---

# 🎥 Recording

Recording is a tool, not simulation state. Frames are captured only after the complete graphical frame has been rendered. The resulting GIF therefore contains what the operator saw: world, HUD, sidebar, charts, and other visible overlays.

Recording does not participate in headless simulation.

---

# 🆕 New-world construction

`bootstrap.py` is the sole authority for building a fresh run.

Graphical startup, headless startup, and UI recreate operations ultimately delegate to `bootstrap_new_world()`.

Its responsibilities include resetting run counters, creating lineage structures, generating initial genomes, placing founders, building density fields, generating zones and nests, installing runtime rules, and resetting execution speed.

This construction sequence must not be duplicated elsewhere.

`bootstrap.py` deliberately does not depend on simulation, controls, rendering, panels, or Pygame.

Dependency in the opposite direction would make world construction depend on one of its operators.

---

# 🔄 Important data flows

## One organism decision

```text
state.agents
     │
     ├──── density fields ───→ senses
     │                           │
     └──── lifetime state ───────┘
                                 ↓
                            neural inputs
                                 ↓
genome pool ─────────────────→ brain
                                 ↓
                         recurrent outputs
                                 ↓
                            action argmax
                                 ↓
                              movement
                                 ↓
                         updated position
```

## One ecological resolution

```text
post-movement positions
        ↓
fill_fields()
        ↓
frozen density snapshot
        ↓
compute_ecology_resolution()
        ↓
EcologyResolution
        ↓
apply_ecology_resolution()
        ↓
HP / age / encounters → death masks → lockstep compaction → updated scores
```

## One reproductive event

```text
scheduler → lineage turn → eligibility gates → ranking → parent pool
        → two parents → genetics → two children → nest spawn
        → new stable IDs → append pool / agents / ids
        → final fill_fields()
```

---

# 🚧 Architectural boundaries

Several boundaries should be treated as contracts.

**Simulation must remain render-independent.** `step()` must not call `draw()`, `pygame.display.*`, panel rendering, or any other presentation entry point. Headless execution depends on this.

**Ecology owns ecology.** Predation, overcrowding, metabolism, zones, nest protection, encounters, and mortality belong in `ecology.py`. Do not distribute parts of the same ecological law across movement, rendering, or reproduction.

**Bootstrap owns fresh-world construction.** Do not create parallel world initialization sequences in controls, CLI, tests, GUI, headless runner, or anywhere else.

**Nest geometry has one mathematical authority.** Toroidal nest geometry belongs in `nest_geometry.py`. Do not reimplement distance or membership formulas elsewhere.

**Runtime rules are replaced, not mutated.** Never partially edit fields inside the active `RuntimeRules`. Use the validated replacement path.

**Population arrays move together.** Whenever population membership changes, `pool`, `agents`, and `ids` must change in lockstep.

**Rendering is observational.** Rendering may inspect the world. It may not advance it.

**UI navigation does not alter physics.** Changing panel, cursor, scroll position, language, or HUD visibility must not alter simulation outcomes.

---

# 🧪 Testability as architecture

Several boundaries exist specifically because they make behavior independently testable.

Examples:

```text
nest_geometry      → pure geometry without active-world state
RuntimeRules       → validate candidate without mutating runtime
ecology compute    → inspect ecological result before applying it
input_dispatcher   → route input without rendering
bootstrap          → construct worlds without graphical dependencies
headless mode      → execute full simulation without a Pygame window
```

These are not incidental conveniences. They are architectural seams.

---

# 📁 Responsibility map

| Module                | Primary responsibility                                           |
| --------------------- | ---------------------------------------------------------------- |
| `config.py`           | Structural constants, defaults and limits                        |
| `layout.py`           | Derived world/display geometry                                   |
| `runtime_rules.py`    | Immutable HOT-rule contract and validation                       |
| `state.py`            | Shared runtime state                                             |
| `bootstrap.py`        | Fresh-world construction                                         |
| `world.py`            | Population representation, IDs, density fields, world generation |
| `nest_geometry.py`    | Pure toroidal nest geometry                                      |
| `senses.py`           | Neural perception                                                |
| `brain.py`            | Neural evaluation                                                |
| `movement.py`         | Toroidal movement                                                |
| `genetics.py`         | Genome creation, crossover and mutation                          |
| `evolution.py`        | Behavior pipeline and reproduction                               |
| `ecology.py`          | Ecological resolution and mortality                              |
| `simulation.py`       | Tick orchestration and execution loops                           |
| `persistence.py`      | World checkpoints                                                |
| `prefs.py`            | Operator preferences                                             |
| `ui_state.py`         | Transient graphical navigation                                   |
| `panels.py`           | Generic panel grammar                                            |
| `panels_defs.py`      | Concrete panel/domain composition                                |
| `input_dispatcher.py` | Input routing                                                    |
| `controls.py`         | Reusable operator actions                                        |
| `rendering.py`        | Graphical presentation                                           |
| `i18n.py`             | Display localization                                             |
| `recording.py`        | GIF capture                                                      |
| `audio.py`            | Music and sound effects                                          |
| `feedback.py`         | Semantic presentation events                                     |
| `cli.py`              | Graphical/headless command-line entry                            |

---

# 🔒 Architectural invariants

The current architecture depends on these rules:

```text
simulation.step is the canonical tick
graphical and headless execution use the same step()
simulation progression does not depend on rendering
Pygame is not required by headless simulation
bootstrap_new_world is the single fresh-world constructor
ecological effects are computed from one frozen spatial snapshot
ecology is applied globally before mortality compaction
newborns do not participate in their birth-tick ecology
pool / agents / ids remain in lockstep
critter identity is stable and independent of array position
RuntimeRules is immutable and validated before replacement
state.runtime_rules is the active authority for HOT laws
nest_geometry is the single authority for nest mathematics
failed checkpoint loads do not partially mutate runtime
operator preferences are separate from world checkpoints
ui_state does not influence simulation physics
rendering does not advance simulation
simulation model does not depend on audio
evolution does not emit audio events
feedback does not depend on audio
audio does not mutate biological state
headless does not initialize audio
normal runtime never waits for audio
channel saturation drops sound instead of blocking
operator audio preferences are not checkpoint state
```

Violating one of these should be treated as an architectural change, not a local implementation detail.

---

## Final note

Primordial Soup intentionally contains global state. This is a simulation with one active universe, not a request/response service pretending every tick is an isolated transaction.

The goal is therefore not to eliminate state. The goal is to make ownership and mutation boundaries obvious.

```text
state is allowed
mysterious state is not
```

The critters already provide enough emergent behavior. The architecture does not need to join them.
