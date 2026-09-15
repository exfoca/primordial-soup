# 🏗️ Architecture

Primordial Soup is a small simulation, but it has one architectural problem common to much larger systems:

```text
everything affects everything
```

Critters move.

Movement changes spatial density.

Spatial density changes ecology.

Ecology changes survival.

Survival changes reproduction.

Reproduction changes populations.

Populations change perception.

And then the next tick starts.

The architecture exists to keep those relationships explicit without turning the codebase into one enormous `simulation.py` with opinions about Pygame, genetics, persistence, theology, and CSV files.

---

## Architectural model

At a high level, Primordial Soup is divided into four concerns:

```text
┌─────────────────────────────────────┐
│           Presentation              │
│ UI · input · rendering · tools      │
└─────────────────┬───────────────────┘
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

Execution begins with:

```text
python -m primordial_soup
```

The path is:

```text
__main__.py
    ↓
cli.main()
```

The CLI chooses between two execution modes:

```text
graphical
headless
```

Both eventually use the same:

```text
simulation.step()
```

This is a central architectural invariant.

There is one simulation.

There are two ways to operate it.

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
initialize UI
    ↓
register panels
    ↓
initialize rendering
    ↓
register input adapters
    ↓
event loop
```

The graphical loop then repeats:

```text
process input
    ↓
advance simulation if running
    ↓
redraw if necessary
    ↓
flush operator preferences
    ↓
limit frame rate
```

`simulation.run()` is the graphical **composition root**.

It is where otherwise independent pieces are connected.

That is why dispatcher callbacks and concrete panels are registered there instead of appearing through import-time side effects.

---

## Headless mode

Headless execution uses:

```text
simulation.run_headless()
```

Its lifecycle is simpler:

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

Headless mode does not initialize the graphical interface or operator preferences.

Pygame-dependent modules are imported lazily only by the graphical path.

This boundary is intentional:

```text
simulation core
≠
graphical application
```

A batch experiment should not require a display server merely because somewhere in the repository a rectangle needs drawing.

---

# ⏱️ `simulation.step()` is the clock

`simulation.step()` is the canonical owner of tick ordering.

One call means exactly one simulation tick.

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

In code terms:

```text
evaluate_and_move()
fill_fields()

compute_ecology_resolution()
apply_ecology_resolution()

take reproduction turn
reproduce_lineage()

fill_fields()

metrics
```

`step()` does not render.

The simulation decides **what happens**.

The caller decides **when humans get to see it**.

---

## Why the order matters

The sequence above is part of the model.

Moving reproduction before ecology, for example, would allow newborns to participate in ecological resolution during their own birth tick.

Moving mortality before all ecological deltas were known could make lineage iteration order influence survival.

Changing tick ordering is therefore not a refactor unless behavior remains identical.

Sometimes moving three lines of code is architecture.

Sometimes it is creating a different universe.

---

# 🌍 World representation

`world.py` owns the concrete representation of populations and spatial state.

Each lineage is represented by a structure conceptually equivalent to:

```text
lineage
├── id
├── color
├── pool
├── agents
├── ids
└── field
```

Where:

```text
pool    → [N, GENOME_SIZE] float32
agents  → [N, AGENT_COLUMNS] float32
ids     → [N] int64
field   → [WORLD_WIDTH, WORLD_HEIGHT]
```

The critical population invariant is:

```text
len(pool)
==
len(agents)
==
len(ids)
```

The three arrays describe the same organisms by row.

If row `17` is removed because that critter dies, row `17` must disappear from all three structures.

Ecology performs this compaction in lockstep.

---

## Stable identity

Array position is not organism identity.

`world.py` owns:

```text
allocate_critter_ids()
resolve_critter_id()
```

Stable IDs survive population compaction.

This allows Observation, persistence, and death snapshots to refer to an organism without depending on its current row inside an ndarray.

```text
stable ID → identity
array index → current storage location
```

Confusing the two eventually results in observing the wrong corpse.

---

## Spatial fields

Each lineage maintains a density field.

`fill_fields()` rebuilds these fields from current positions.

The fields are snapshots of:

```text
how many critters of this lineage
occupy each world cell
```

They are consumed by perception and ecology.

`fill_fields()` is deliberately called twice during a tick:

```text
after movement
```

to establish the ecology snapshot, and:

```text
after mortality + reproduction
```

to establish the final spatial state for the next tick.

---

# 👁️ Perception → brain → movement

Individual behavior is orchestrated by:

```text
evolution.evaluate_and_move()
```

Despite the module name, this function currently owns the per-lineage cognitive pipeline:

```text
senses
   ↓
brain
   ↓
action selection
   ↓
movement
```

Ecology no longer belongs here.

That responsibility has its own module.

---

## `senses.py`

`senses.py` transforms world state into neural input.

Conceptually:

```text
spatial fields
+
critter internal state
        ↓
367-value input vector
```

The module performs perception in batches and uses reusable scratch buffers to avoid allocating large temporary arrays every tick.

It does not decide behavior.

It describes what the brain receives.

One deliberate mutation exists: when sensing a real agent matrix, the calculated low-HP flag is written back into the corresponding lifetime-state column so stored state matches what the network actually consumed.

---

## `brain.py`

`brain.py` owns neural evaluation.

Input:

```text
neural inputs
genomes
previous recurrent hidden state
```

Output:

```text
9 action scores
new recurrent hidden state
```

The brain does not know about:

```text
predators
nests
reproduction
Pygame
save files
panels
```

It performs numerical evaluation of the neural architecture encoded by the genome.

That ignorance is useful.

---

## `movement.py`

`movement.py` converts the selected action into toroidal position changes.

It owns:

```text
action index
→
(dx, dy)
→
wrapped position
```

It does not decide which action is best.

It does not calculate ecological consequences.

Moving into a predator is somebody else's department.

---

# 🩸 Ecology

`ecology.py` is the authority for ecological semantics.

It owns:

```text
base metabolism
environmental zone effects
same-lineage overcrowding
predation
nest protection
encounters
triad resolution
mortality
population compaction
post-ecology composite score
```

The design deliberately separates ecology into two phases:

```text
compute
↓
apply
```

---

## Compute phase

```text
compute_ecology_resolution()
```

reads a frozen post-movement world snapshot and produces an `EcologyResolution`.

It does not mutate:

```text
HP
age
encounters
population arrays
birth/death counters
density fields
```

The one deliberate side effect is NumPy RNG consumption when triad cells require random relation selection.

That RNG is part of persisted simulation history.

So the function is deterministic relative to complete simulation state, but it is not mathematically pure.

---

## Apply phase

```text
apply_ecology_resolution()
```

applies the resolution globally:

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

The reproductive scheduler itself lives in simulation/state:

```text
reproduction_cooldown
reproduction_turn
```

When `simulation.step()` grants a lineage its turn:

```text
reproduce_lineage(lineage)
```

handles:

```text
eligibility
ranking
parent-pool construction
parent selection
genetic recombination
mutation
child construction
nest spawning
stable-ID allocation
parent HP reward
population append
```

Reproduction does **not** rebuild density fields.

New organisms are appended to:

```text
pool
agents
ids
```

and become spatially visible when `simulation.step()` performs its final:

```text
fill_fields()
```

That keeps the tick boundary explicit.

---

# 🧬 Genetics

`genetics.py` owns transformations of genomes.

Its responsibilities include:

```text
random genome generation
random population generation
crossover
mutation
```

It knows genetic layout through structural configuration.

It does not know:

```text
HP
age
fitness gates
nests
population scheduling
UI
persistence
```

Those decisions belong to higher-level orchestration.

The distinction is:

```text
genetics.py
    How do two genomes produce descendants?

evolution.py
    Which organisms reproduce, when, and where?
```

---

# 🪺 Geometry

World geometry is deliberately split.

## `layout.py`

`layout.py` derives physical dimensions from display/world configuration:

```text
screen size
sidebar width
pixel scale
world width
world height
```

The world and sidebar occupy separate regions.

Rendering should consume this geometry rather than independently inventing dimensions.

---

## `nest_geometry.py`

`nest_geometry.py` is a low-level geometry module.

It has:

```text
no global state
no config dependency
no world dependency
no Pygame dependency
```

Dimensions and radii are passed explicitly.

It is the canonical authority for:

```text
toroidal distance
nest disks
nest rings
coordinate wrapping
nest membership
nest overlap
nest ↔ zone intersection
```

This allows the same geometry functions to operate on:

```text
the active world
```

and on:

```text
an uncommitted checkpoint being validated
```

without temporarily corrupting global state.

Geometry should be boring.

Boring geometry prevents exciting persistence bugs.

---

# ⚙️ Configuration architecture

Configuration has three distinct levels:

```text
config.py
    ↓
runtime_rules.py
    ↓
state.runtime_rules
```

---

## `config.py`

`config.py` owns structural constants, defaults, and validation limits.

Examples:

```text
neural dimensions
genome size
population ceilings
nest radius
world structure
default runtime values
min/max limits
save format versions
```

Changing a structural constant may change the model itself.

---

## `runtime_rules.py`

`runtime_rules.py` defines the immutable `RuntimeRules` contract.

It:

```text
does not import state
does not know the UI
does not know Pygame
does not own global state
```

A rule update follows:

```text
current rules
    ↓
create candidate
    ↓
validate candidate
    ↓
return candidate
```

Invalid candidates never mutate the original object.

---

## `state.runtime_rules`

`state.py` owns the currently active `RuntimeRules` reference.

Replacing active laws follows:

```text
validate
↓
commit reference
```

Consumers read the current object.

They do not maintain shadow copies of runtime configuration.

This gives one authoritative answer to:

> What are the laws of this universe right now?

---

# 🧠 Shared state

`state.py` contains shared runtime state required across simulation modules.

Major categories include:

```text
population
runtime rules
zones
nests
tick counters
birth/death counters
stable-ID allocator
reproduction scheduler
metrics history
observation state
runtime execution controls
selected operator preferences
```

Not all of these have the same persistence semantics.

That distinction is intentional.

For example:

```text
population            → checkpoint state
RNG scheduler phase   → checkpoint state
runtime rules         → checkpoint state

language              → operator preference
active save slot      → operator preference
inspection trail      → view state
recording             → tool state
```

The persistence boundary decides what belongs to the universe.

---

# 👁️ Observation as a bridge

Observation is slightly special.

The graphical navigation state lives in:

```text
ui_state.py
```

but the identity of the observed critter and its death snapshot live in:

```text
state.py
```

This is deliberate.

Observation must survive:

```text
array compaction
panel changes
organism death
simulation ticks
```

Ecology must also know whether the organism being removed is currently observed so it can capture its final state.

Therefore Observation crosses the simulation/presentation boundary through a very narrow contract:

```text
stable critter ID
death snapshot
trail
```

It does not affect ecological outcomes.

---

# 💾 Persistence

`persistence.py` is the checkpoint boundary.

It serializes the state required for exact continuation and validates it on load.

The important architectural pattern is:

```text
SAVE
runtime state
    ↓
validate
    ↓
serialize temp file
    ↓
atomic replace
```

and:

```text
LOAD
file
    ↓
parse locally
    ↓
validate everything
    ↓
single commit boundary
    ↓
runtime state
```

A rejected load must not partially modify the running universe.

Persistence also does not regenerate missing world geometry.

Zones and nests are restored from the checkpoint.

For the full contract, see:

```text
docs/persistence.md
```

---

# 👤 Operator preferences

`prefs.py` is deliberately separate from world persistence.

There are two different forms of persistence:

```text
checkpoint (.pkl)
→ the universe

prefs.json
→ the operator
```

Preferences include interface choices such as:

```text
language
active save slot
discovery settings
floating HUD visibility
```

Architectural invariants:

```text
preferences do not change simulation physics
savegame load does not overwrite preferences
headless execution does not read or write preferences
```

A universe should not change language because somebody loaded a dinosaur-era checkpoint.

---

# 🖥️ Presentation architecture

The graphical interface is split into several smaller responsibilities.

```text
Pygame events
     ↓
input_dispatcher
     ↓
panels / controls
     ↓
domain state

domain state + ui_state
     ↓
rendering
     ↓
screen
```

---

## `ui_state.py`

`ui_state.py` owns transient graphical-navigation state:

```text
active panel
last panel
panel cursors
scroll positions
modal state
transient notices
floating HUD visibility
```

It is presentation state.

Simulation modules must not depend on it.

Nothing in `ui_state.py` belongs in a world checkpoint.

---

## `panels.py`

`panels.py` defines the UI grammar:

```text
Panel
Item
ItemKind
DispatchResult
Flow
panel registry
```

It does not implement domain-specific panel behavior.

Think of it as the vocabulary from which the interface is constructed.

---

## `panels_defs.py`

`panels_defs.py` composes the concrete panels:

```text
Inspection
Configuration
Metrics
Session
Tools
```

This is intentionally where panel definitions meet domain operations.

Unlike `panels.py`, this module is allowed to know about:

```text
state
world
persistence
recording
preferences
i18n
```

Importing it does not automatically register panels.

Registration is explicit during graphical bootstrap.

---

## `input_dispatcher.py`

`input_dispatcher.py` owns input-routing policy.

It translates Pygame events into actions but does not render.

Its routing order is broadly:

```text
exit request
↓
modal
↓
global command
↓
panel activation
↓
panel-local input
↓
world interaction
```

The dispatcher is intentionally ignorant of graphical geometry.

For example, tab hit-testing is injected from rendering.

This prevents input routing from becoming a second, slightly wrong copy of layout logic.

---

## `controls.py`

`controls.py` contains reusable operator actions.

Examples:

```text
new world
save
load
heal all
toggle zones
toggle recording
cycle save slot
print state
```

These actions are shared by:

```text
panel handlers
+
global accelerators
```

so orchestration is not duplicated in two UI paths.

`controls.py` does not own rendering.

Actions return `DispatchResult`; the graphical loop decides when to redraw.

---

## `rendering.py`

`rendering.py` owns pixels.

It reads simulation and UI state and renders:

```text
world
zones
nests
critters
inspection overlays
HUD
command dock
sidebar
charts
modals
```

It also owns screen-space geometry such as clickable panel-tab rectangles.

Rendering does not own simulation progression.

### Camera and world viewport

The renderer owns two distinct concepts.

```text
world viewport
    screen-space rectangle where the world is displayed

camera
    world-space description of which logical region is observed
```

The viewport answers **where to draw**. The camera answers **what
region to draw**. They change independently: a resize alters the
viewport and leaves the camera alone.

The camera has three fields:

```text
zoom
view_x
view_y
```

`zoom` is a magnification factor in `[MIN_ZOOM, MAX_ZOOM]`. `view_x`
and `view_y` are the top-left corner of the visible region, expressed
in logical world cells. All three are floats.

Fitting the world into the window is not the same as zooming. Window
fit is recomputed on every resize and derives purely from the window
size and the logical world dimensions. Zoom is a separate operator
choice that survives resize and fullscreen changes.

The rendering pipeline is:

```text
logical world
    ↓
_build_image()
    ↓
logical raster
    ↓
camera source rectangle
    ↓
crop
    ↓
scale to fixed viewport
    ↓
screen
```

The scale step always targets the physical viewport, regardless of
zoom. Zoom reduces the logical source region rather than enlarging
the destination Surface. This keeps the cost of the scale step
constant.

Camera state is presentation state. It is not:

* simulation state;
* `RuntimeRules`;
* checkpoint state;
* preference persistence.

`draw()` and `screen_to_world()` derive their transforms from the
same camera/viewport model, so the pixel the operator clicks always
matches the cell the simulation reads.

Zoom never changes logical world dimensions, `PIXEL_SCALE`, or
`layout.LAYOUT`. Rendering the camera must never advance the
simulation.

### Camera precision and raster discretization

Camera coordinates remain floating-point.

Raster extraction is necessarily discrete. The source rectangle uses
`floor`/`ceil` so the continuous camera view is completely contained
by the sampled logical raster. Cell interaction quantizes only at the
`screen_to_world()` boundary.

This means the source rectangle is not expected to equal the
continuous view exactly. Containment is the contract; sub-cell
differences introduced by rasterization are not bugs.

Calling:

```text
draw()
```

must not advance the universe.

---

# 🌐 Internationalization

`i18n.py` translates display strings.

Canonical internal values remain stable.

Examples:

```text
mutation mode → canonical identifier
panel label   → localized display value

metric key    → canonical identifier
chart label   → localized display value
```

Persistence formats and internal semantics are not rewritten when the UI language changes.

Localization happens at the presentation boundary.

---

# 🎥 Recording

Recording is a tool, not simulation state.

Frames are captured only after the complete graphical frame has been rendered.

The resulting GIF therefore contains what the operator saw:

```text
world
+
HUD
+
sidebar
+
charts
+
other visible overlays
```

Recording does not participate in headless simulation.

---

# 🆕 New-world construction

`bootstrap.py` is the sole authority for building a fresh run.

Graphical startup, headless startup, and UI recreate operations ultimately delegate to:

```text
bootstrap_new_world()
```

Its responsibilities include:

```text
reset run counters
create lineage structures
generate initial genomes
place founders
build density fields
generate zones
generate nests
install runtime rules
reset execution speed
```

A fresh bootstrap initializes `simulation_speed` to `1.0x`.

UI recreate is different: `controls.recreate()` captures the
operator-selected `simulation_speed`, delegates world
reconstruction to `bootstrap_new_world()`, and restores the selected
speed afterward.

This keeps bootstrap deterministic while preserving operator
execution state across `R`/recreate.

This construction sequence must not be duplicated elsewhere.

`bootstrap.py` deliberately does not depend on:

```text
simulation
controls
rendering
panels
Pygame
```

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

---

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
HP / age / encounters
        ↓
death masks
        ↓
lockstep compaction
        ↓
updated scores
```

---

## One reproductive event

```text
scheduler
   ↓
lineage turn
   ↓
eligibility gates
   ↓
ranking
   ↓
parent pool
   ↓
two parents
   ↓
genetics
   ↓
two children
   ↓
nest spawn
   ↓
new stable IDs
   ↓
append pool / agents / ids
   ↓
final fill_fields()
```

---

# 🚧 Architectural boundaries

Several boundaries should be treated as contracts.

### Simulation must remain render-independent

```text
step()
```

must not call:

```text
draw()
pygame.display.*
panel rendering
```

Headless execution depends on this.

### Ecology owns ecology

Predation, overcrowding, metabolism, zones, nest protection, encounters, and mortality belong in:

```text
ecology.py
```

Do not distribute parts of the same ecological law across movement, rendering, or reproduction.

### Bootstrap owns fresh-world construction

Do not create parallel world initialization sequences in:

```text
controls
CLI
tests
GUI
headless runner
```

### Nest geometry has one mathematical authority

Toroidal nest geometry belongs in:

```text
nest_geometry.py
```

Do not reimplement distance or membership formulas elsewhere.

### Runtime rules are replaced, not mutated

Never partially edit fields inside the active `RuntimeRules`.

Use the validated replacement path.

### Population arrays move together

Whenever population membership changes:

```text
pool
agents
ids
```

must change in lockstep.

### Rendering is observational

Rendering may inspect the world.

It may not advance it.

### UI navigation does not alter physics

Changing panel, cursor, scroll position, language, or HUD visibility must not alter simulation outcomes.

---

# 🧪 Testability as architecture

Several boundaries exist specifically because they make behavior independently testable.

Examples:

```text
nest_geometry
→ pure geometry without active-world state

RuntimeRules
→ validate candidate without mutating runtime

ecology compute
→ inspect ecological result before applying it

input_dispatcher
→ route input without rendering

bootstrap
→ construct worlds without graphical dependencies

headless mode
→ execute full simulation without Pygame window
```

These are not incidental conveniences.

They are architectural seams.

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
```

Violating one of these should be treated as an architectural change, not a local implementation detail.

---

## Final note

Primordial Soup intentionally contains global state.

This is a simulation with one active universe, not a request/response service pretending every tick is an isolated transaction.

The goal is therefore not to eliminate state.

The goal is to make ownership and mutation boundaries obvious.

```text
state is allowed

mysterious state is not
```

The critters already provide enough emergent behavior.

The architecture does not need to join them.
