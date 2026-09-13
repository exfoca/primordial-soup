# 💾 Persistence

Primordial Soup can stop a world and reconstruct it later.

That sounds simple.

It is not.

A valid save must preserve enough state that:

```text
save
 ↓
process ends
 ↓
load
 ↓
the same population still exists
```

while refusing to invent missing genomes, repair corrupted identities or silently reshape an incompatible world.

Persistence therefore has two goals:

```text
continuity
+
integrity
```

When those goals conflict, Primordial Soup prefers integrity.

A rejected save is better than a successfully loaded fiction.

---

# The persistence model

Each save slot can produce two files:

```text
world state
.pkl

        +

metric export
_metricas.csv
```

For the graphical slot:

```text
world_a
```

the default paths are:

```text
genome_pool_world_a.pkl
genome_pool_world_a_metricas.csv
```

The two files have different responsibilities.

```text
.pkl
=
state required to reconstruct the world

.csv
=
export of recorded metrics for analysis
```

The CSV is not required to load the world.

The pickle does not depend on the CSV.

---

# Save slots

The graphical interface currently cycles through:

```text
default
world_a
world_b
world_c
```

using:

```text
N
```

The configured filename templates are:

```text
genome_pool_{slot}.pkl
```

and:

```text
genome_pool_{slot}_metricas.csv
```

The default graphical slot therefore produces:

```text
genome_pool_default.pkl
genome_pool_default_metricas.csv
```

---

# S — save

Press:

```text
S
```

to serialize the current world into the active slot.

At a high level:

```text
runtime state
      ↓
build canonical payload
      ↓
pickle payload
      ↓
write .pkl
      ↓
export current metric history
      ↓
write companion CSV
```

The world-state file is the authoritative continuation artifact.

The CSV is an analytical sidecar.

---

# L — load

Press:

```text
L
```

to load the active slot.

Loading is intentionally much stricter than:

```text
pickle.load()
```

The raw object must pass:

```text
format validation
version validation
architecture validation
genome validation
lineage validation
shape validation
coordinate validation
identity validation
```

before it is allowed to replace the current runtime.

---

# Current persistence versions

Primordial Soup currently uses:

```text
SAVE_VERSION         = 10
ARCHITECTURE_VERSION = "mlp-1x25x12-rec"
GENOME_VERSION       = "layout-v4"
```

These identify different compatibility boundaries.

---

# Save version

```text
SAVE_VERSION
```

describes the save schema and semantic persistence contract.

Current:

```text
10
```

Version history recorded by the project:

```text
v2   original save format
v3   versioning
v4   internal state became neural input
v5   recurrence
v6   second hidden layer
v7   block crossover
v8   two-scale mutation
v9   composite selection
v10  stable individual identity
```

---

# Architecture version

```text
ARCHITECTURE_VERSION
```

identifies the neural architecture expected by the saved world.

Current:

```text
mlp-1x25x12-rec
```

A world created for a different network architecture is rejected.

Otherwise a flat genome might be interpreted using the wrong matrix shapes.

Those bytes would still be numbers.

They would no longer be the same brain.

---

# Genome version

```text
GENOME_VERSION
```

identifies the expected internal genome layout.

Current:

```text
layout-v4
```

This protects the meaning and ordering of the:

```text
10,245
```

genes currently stored for each critter.

---

# Compatibility policy

The current policy is deliberately strict.

```text
save version < current
→ reject

save version > current
→ reject

architecture mismatch
→ reject

genome mismatch
→ reject
```

There is no automatic migration from an older semantic save version into v10.

This is intentional.

Network topology, mutation, recombination and selection rules have changed across historical versions.

Attempting to synthesize missing state would produce a world that never actually existed.

For experimental software, that is worse than saying:

```text
incompatible save
```

---

# `_migrate()` does not currently migrate old versions

The loader has a single compatibility function named:

```python
_migrate(...)
```

but the current policy is:

```text
older semantic version
→ reject
```

The function centralizes compatibility decisions.

It is not currently an old-save upgrade engine.

The name describes the architectural extension point more than the present behavior.

---

# Missing version

If a payload has no:

```text
versao
```

field, it is treated as:

```text
version 1
```

and therefore rejected by the current v10 policy.

This recognizes historical pre-versioned saves without pretending they are compatible.

---

# Legacy filename fallback

There is one historical filename:

```text
genome_pool.pkl
```

If:

```text
genome_pool_default.pkl
```

does not exist while the active slot is:

```text
default
```

the loader may try that legacy filename.

This is only a **path fallback**.

It is not format compatibility.

A legacy file found there must still pass the v10 version contract.

Usually an old-version file will therefore be found and then correctly rejected.

For non-default slots there is no such fallback.

---

# Canonical save language

The save schema uses canonical Portuguese keys.

For example:

```text
versao
arquitetura
genoma
linhagens
agentes
zonas
nascimentos
mortes
```

This remains true even when the graphical interface is displayed in English.

That separation is deliberate.

```text
display language
≠
data language
```

The UI may say:

```text
Population
```

while persisted metric identifiers remain:

```text
populacao
```

Changing language must never change the storage contract.

---

# English-key compatibility

The loader accepts English aliases for a number of historical fields.

For example, it can read either conceptual spelling of fields such as:

```text
zonas / zones
agentes / agents
linhagens / lineages
```

Canonical new saves are still written using Portuguese keys.

So:

```text
load
→ tolerant at the language boundary

save
→ canonical
```

This allows historical English-produced data to be read without allowing the format to split into two competing schemas.

---

# The v10 payload

A canonical save currently contains top-level fields equivalent to:

```text
{
    versao
    arquitetura
    genoma

    mutation
    mutategen
    escala_local

    tick
    proximo_id
    nascimentos
    mortes

    modificadores_ambientais
    zonas
    zonas_ativas
    efeito_hp_zonas

    linhagens
}
```

The `linhagens` entry contains the population data.

---

# Top-level fields

| Key                        | Meaning                            |
| -------------------------- | ---------------------------------- |
| `versao`                   | Save schema version                |
| `arquitetura`              | Neural architecture contract       |
| `genoma`                   | Genome-layout contract             |
| `mutation`                 | Current runtime mutation rate      |
| `mutategen`                | Runtime mutated-gene count         |
| `escala_local`             | Runtime local-scale value          |
| `tick`                     | Current simulation tick            |
| `proximo_id`               | Next globally available critter ID |
| `nascimentos`              | Cumulative births                  |
| `mortes`                   | Cumulative deaths                  |
| `modificadores_ambientais` | Environmental-model marker         |
| `zonas`                    | Environmental-zone mask            |
| `zonas_ativas`             | Runtime zone toggle                |
| `efeito_hp_zonas`          | Runtime HP effect of zones         |
| `linhagens`                | Serialized lineage populations     |

Not all static configuration constants are duplicated into the save.

Compatibility is instead partly protected by version identifiers.

---

# Lineage records

Each entry under:

```text
linhagens
```

currently contains:

```text
id
cor
pools
agentes
ids
```

Conceptually:

```text
LINEAGE
│
├── id
├── color
├── genomes
├── agent records
└── stable identities
```

---

# The three parallel population arrays

For a lineage containing `N` individuals, the runtime requires:

```text
pool.shape
=
(N, GENOME_SIZE)

agents.shape
=
(N, AGENT_COLUMNS)

ids.shape
=
(N,)
```

With the current architecture:

```text
pool.shape
=
(N, 10245)

agents.shape
=
(N, 36)

ids.shape
=
(N,)
```

All three must contain the same number of individuals.

This is non-negotiable.

---

# Why save lists instead of raw runtime matrices?

In memory:

```text
pool
```

and:

```text
agents
```

are NumPy `float32` matrices.

At the persistence boundary they are converted using:

```python
.tolist()
```

before serialization.

The save representation therefore remains the historical nested-list structure even though the execution representation has been optimized.

On load, the lists become NumPy arrays again.

This keeps two concerns separate:

```text
runtime representation
optimized for simulation

save representation
kept stable for persistence
```

---

# The spatial field is not saved

Each lineage also has a runtime density field:

```text
field[WORLD_WIDTH, WORLD_HEIGHT]
```

That field is derived from individual coordinates.

It is therefore not stored as part of each lineage record.

During load, after validating all X/Y coordinates, the loader reconstructs the field locally.

Conceptually:

```text
saved agents
    ↓
validated X/Y
    ↓
rebuild density field
```

Derived state should be rebuilt when it can be reproduced exactly.

There is no reason to serialize another large matrix merely to store information already contained in coordinates.

---

# Stable IDs are mandatory in v10

Version 10 introduced explicit stable identity.

Every lineage must therefore contain:

```text
ids
```

and the top-level payload must contain:

```text
proximo_id
```

There is no attempt to fabricate IDs when those fields are absent.

A v10 save without them is invalid.

---

# Identity validation

The loader verifies several properties.

Per lineage:

```text
ids.dtype == int64

all IDs > 0
```

Globally:

```text
no duplicated IDs

proximo_id > 0

proximo_id > max(existing IDs)
```

This final condition prevents future births from colliding with a living individual's identity.

For example:

```text
largest living ID = 813

proximo_id = 814
→ valid
```

but:

```text
largest living ID = 813

proximo_id = 100
→ reject
```

The second save would eventually allocate an already-used identity.

---

# Stable identity and compaction

Population arrays change position when individuals die.

Stable IDs do not.

The persistence contract therefore saves both:

```text
array-aligned population state
```

and:

```text
identity sequence state
```

This makes it possible to restore a population without losing individual identity.

See [Inspection](inspection.md).

---

# Exact lineage count

A valid v10 save must contain exactly:

```text
TOTAL_LINEAGES
```

lineage records.

Currently:

```text
3
```

A payload containing:

```text
2
```

or:

```text
4
```

lineages is rejected.

The loader does not:

* invent the missing lineage;
* discard an extra lineage;
* merge populations.

The saved model must match the runtime model.

---

# Lineage ordering and identity

Lineages are validated against configured order.

Current expected IDs are:

```text
R
G
B
```

The record at each position must contain the expected lineage ID.

A save cannot reorder its lineages and expect the loader to guess.

This protects the ecological and reproductive semantics attached to lineage ordering.

---

# Saved color is not authoritative

Canonical saves currently include:

```text
cor
```

inside each lineage record.

However, reconstruction uses the configured lineage color after validating the lineage ID.

The current loader does not use the serialized color as authoritative runtime state.

This is sensible because color belongs to the configured lineage definition rather than an individual's evolutionary history.

The field remains part of the historical save representation.

---

# Shape validation

The loader rejects malformed population shapes.

Examples:

```text
pool = (50, 10245)
agents = (49, 36)
ids = (50,)
```

→ reject.

```text
pool = (50, 10000)
agents = (50, 36)
ids = (50,)
```

→ reject.

```text
pool = (50, 10245)
agents = (50, 35)
ids = (50,)
```

→ reject.

There is no:

```text
truncate to smallest array
```

and no:

```text
pad missing rows
```

because either action would fabricate relationships between genomes, bodies and identities.

---

# Numeric conversion

Genome and agent payloads are reconstructed as:

```text
float32
```

arrays.

Stable IDs are reconstructed as:

```text
int64
```

arrays.

Invalid numeric structures are rejected rather than allowed to raise unpredictably later in the simulation.

The goal is:

```text
bad payload
→ load failure
```

rather than:

```text
bad payload
→ successful load
→ mysterious crash 200 ticks later
```

---

# Coordinate validation

X/Y coordinates receive additional validation before population state can be committed.

They must be:

```text
finite
```

then:

```text
integral
```

then:

```text
inside current world bounds
```

Only after those checks are they converted to integer indices.

This avoids silently doing:

```text
3.7 → 3
```

or attempting to index the world with:

```text
NaN
infinity
-17
```

Simulation history should not be repaired by numeric truncation.

---

# World dimensions and zone masks

The environmental zone mask has shape:

```text
(WORLD_WIDTH, WORLD_HEIGHT)
```

A saved mask must match the world dimensions derived by the current runtime.

If it does not, loading is rejected.

For example:

```text
saved zone mask
800 × 540

current derived world
640 × 480

→ reject
```

The loader does not generate replacement zones in this case.

That would preserve the critters while silently replacing their environment.

The resulting world would not be the saved experiment.

---

# Consequence: static screen geometry can affect compatibility

World geometry is derived from settings such as:

```text
SCREEN_WIDTH
SCREEN_HEIGHT
TARGET_PIXEL_SCALE
INSPECTION_PANEL_WIDTH
```

Changing these can change:

```text
WORLD_WIDTH
WORLD_HEIGHT
```

and therefore make the saved zone mask incompatible.

Fullscreen does not cause this problem because fullscreen does not re-derive world geometry.

Changing the static layout configuration can.

---

# Missing zones

There is a different rule when the:

```text
zonas
```

key is entirely absent.

In that case the loader may generate a new zone mask.

Importantly, that generation happens only **after all validation succeeds**, during commit.

Why?

Because zone generation consumes randomness.

A rejected save must not alter future random sequences merely because the loader tried to inspect it.

This is a subtle but important reproducibility rule.

---

# Zone runtime state

The current save also preserves:

```text
zonas_ativas
```

and:

```text
efeito_hp_zonas
```

So a world saved with:

```text
zones OFF
```

or:

```text
zone effect = -20
```

can restore those runtime conditions.

If the zone-toggle key is absent, load defaults it to:

```text
True
```

If the zone HP effect is absent, load defaults to:

```text
cfg.HP_EFFECT_IN_ZONE
```

---

# Birth and death counters

The current payload contains:

```text
nascimentos
mortes
```

These are cumulative counters for the run.

If either key is absent, the loader uses:

```text
0
```

because historical values cannot be reconstructed.

Their absence does not invalidate the save format.

Inventing a lifetime birth count would be worse than admitting:

```text
unknown historical count
```

---

# Runtime mutation parameters

The save currently preserves:

```text
mutation
mutategen
escala_local
```

corresponding to:

```text
state.mutation_rate
state.mutated_genes
state.local_scale_fraction
```

These are restored on successful load.

Remember the current implementation caveat described in [Configuration](configuration.md):

```text
local_scale_fraction
```

is persisted but the default two-scale mutation path does not currently consume that runtime value.

Persistence faithfully restores the knob.

The engine currently ignores where the knob points.

---

# Tick count

The save preserves:

```text
tick
```

On successful load:

```text
state.tick_count = saved tick
```

and:

```text
state.last_print = saved tick
```

This prevents diagnostic logging from behaving as though the run had restarted from tick zero.

The simulation timeline therefore continues numerically from the save.

---

# What is deliberately not persisted

Not everything in `state.py` belongs to the world.

Several values are interface or observation state and are not restored as part of a save.

Examples include:

```text
inspection session
observed critter
death snapshot
inspection trail
discovery criterion/filter state
chart selection
language
simulation speed
pause state
recording state
active runtime parameter
```

Those belong to the operator session rather than the evolutionary population.

A save is primarily a world checkpoint.

Not a screenshot of every UI decision.

---

# Inspection is cleared after load

A successful load explicitly calls the observation-selection reset.

Therefore:

```text
observed ID
death snapshot
trail
```

are cleared.

This is intentional.

Even if the newly loaded world happens to contain the same numerical critter ID as the previous runtime, the loader does not treat that as continuation of the old inspection session.

After load:

```text
world continuation
≠
inspection-session continuation
```

Choose a critter again.

---

# Metric history is not loaded

This is an important distinction.

The `.pkl` payload does **not** contain:

```text
state.metrics_history
```

and the CSV is not imported by `load()`.

After a successful load:

```text
metrics_history
```

is cleared.

So the graphical charts start a fresh in-memory history from the loaded checkpoint.

The saved world continues.

The chart history does not.

---

# The CSV is an export, not restoration state

The companion metrics file has the format:

```csv
tick,metrica,valores
10,populacao,50;50;50
10,hp_medio,9999;9999;9999
10,taxa_de_mutacao,5
```

Per-lineage values are separated by:

```text
;
```

inside the third CSV column.

Scalar metrics contain only one value.

Canonical metric names include:

```text
populacao
hp_medio
maior_tempo_de_vida
geracao_maxima
score_composto_medio
taxa_de_mutacao
```

The header and metric names are intentionally not translated.

---

# CSV export order

The exporter iterates metrics in:

```text
cfg.ADVANCED_METRICS
```

order and then writes the available historical samples for each metric.

The file is rewritten on each save when metric history exists.

It is not an append-only event log.

---

# No history means no CSV write

If there is no metric history in memory:

```text
_export_metrics_csv()
```

returns without creating a new CSV.

This matters after a load because metric history is cleared.

A loaded world that is immediately re-saved without collecting new metrics does not produce a fresh analytical history from the old CSV.

The old CSV is not read back into memory.

---

# Continuing a loaded run and metrics

Suppose:

```text
run to tick 50,000
save
```

The CSV contains the recent in-memory metric history.

Then:

```text
load at tick 50,000
continue to tick 60,000
save again
```

The new metric history contains samples collected **after the load**.

When saving with history present, the CSV is rewritten from that new in-memory history.

So the sidecar should not currently be treated as a complete append-only lifetime record across repeated load/continue cycles.

For rigorous long-running experiments, preserve or aggregate exported CSVs externally.

---

# Strong transactional loading

The most important loader property is:

```text
validation first
mutation second
```

The implementation is divided into:

```text
PARSE
   ↓
COMMIT
```

There is exactly one conceptual commit boundary.

---

# Parse phase

During parse, the loader:

* reads the pickle;
* checks versions;
* coerces scalar values into locals;
* validates zones;
* validates lineage count;
* builds local genome matrices;
* builds local agent matrices;
* builds local ID arrays;
* validates shapes;
* validates coordinates;
* reconstructs local density fields;
* validates global identity.

The live runtime is not modified during this phase.

---

# Commit phase

Only after every validation passes does the loader assign the parsed state into the runtime.

Conceptually:

```text
disk
 ↓
temporary candidate world
 ↓
validate everything
 ↓
──────────────────
   COMMIT POINT
──────────────────
 ↓
replace live world
```

There is no intended early-return path after commit begins.

---

# Why transactional loading matters

Imagine the current valid world contains:

```text
150 living critters
```

and you attempt to load a damaged save.

Without transactional loading:

```text
mutation rate restored
zones replaced
first lineage loaded
second lineage corrupt
→ failure
```

The runtime would now contain pieces of two different worlds.

Instead:

```text
damaged save
      ↓
validation failure
      ↓
return False
      ↓
existing world remains untouched
```

That is the correct failure mode.

---

# Rejected loads preserve runtime state

The transactional contract covers state such as:

```text
population
runtime scalar values
zones
zone toggle
zone HP effect
next stable ID
inspection session
metrics history
```

If parsing fails, those remain as they were before the load attempt.

This makes **L** safe to use against a malformed file without first destroying the current world.

Saving before experimentation is still recommended.

Humans remain part of the threat model.

---

# Rejected loads do not consume simulation randomness

The loader also avoids RNG-dependent reconstruction before commit.

This protects a less obvious invariant.

Consider two identical seeded experiments.

Run A:

```text
seed 42
start experiment
```

Run B:

```text
seed 42
attempt invalid load
load fails
start experiment
```

If the failed load generated random zones during validation, Run B would consume random draws and diverge.

The loader therefore defers random zone generation until a successful commit.

A failed operation should not alter future stochastic history.

---

# Load failure is non-destructive

Headless mode adds another protection.

If the user asks:

```bash
python -m primordial_soup \
    --load important_world \
    --duration 50000
```

and loading fails, headless execution aborts instead of:

```text
creating a fresh world
running it
overwriting important_world
```

Failure does not silently become initialization.

That distinction protects experiment checkpoints.

---

# Structural strictness vs scalar semantics

The v10 loader is particularly strict about:

```text
save version
architecture
genome layout
lineage count
matrix shapes
coordinates
identity
numeric convertibility
```

However, not every scalar is currently revalidated against every configuration range during load.

For example, several persisted integer runtime fields are coerced to integers and then committed without repeating all of the range assertions that apply to normal UI-controlled values.

So the loader should be described as:

```text
strong structural validator
```

not:

```text
complete semantic validator of every possible hand-edited scalar
```

Normal saves produced by the application already contain controlled runtime values.

Hand-editing pickle payloads is outside the normal persistence contract.

And also an unusual hobby.

---

# Missing vs invalid scalar keys

For several historical-compatible scalar fields, the loader distinguishes:

```text
key absent
```

from:

```text
key present but invalid
```

For example:

```text
mutation key absent
→ allowed fallback

mutation = None
→ invalid

mutation = non-convertible value
→ invalid
```

This is deliberate.

Absence may represent an older legitimate payload shape.

Presence with malformed content represents corrupted or invalid data.

---

# Mandatory and optional state

A useful way to think about the v10 payload is:

```text
STRUCTURALLY MANDATORY

current version compatibility
lineage list
population matrices
stable IDs
next stable ID

        +

COMPATIBILITY-OPTIONAL FIELDS

some runtime scalars
zone toggle
zone HP effect
birth/death counters
historical zone presence
```

Optional does not mean unimportant.

It means the loader has a defined fallback when the field is absent.

---

# ⚠️ Current persistence gap: reproductive scheduler state

The current runtime has two global fields:

```text
state.reproduction_cooldown
state.reproduction_turn
```

They determine:

```text
how many ticks remain before the next reproductive opportunity
```

and:

```text
which lineage owns that opportunity
```

These fields are genuine simulation state.

They are reset for a new run.

However, the current v10 `save()` payload does **not** serialize them.

And the current `load()` path does **not** restore them.

---

# Why this matters

Suppose a save is created while:

```text
reproduction_turn = G
reproduction_cooldown = 73
```

Loading that save does not reconstruct those values from disk.

Therefore the spatial population, genomes, ages, HP and tick count can be restored while the reproductive scheduler resumes from some other phase.

That means:

```text
save at tick N
load
continue
```

is not yet an exact continuation of reproductive timing.

---

# What value does the scheduler have after load?

Because the values are neither parsed nor committed by `load()`, the runtime retains whatever scheduler state already existed in memory.

In a normal fresh process that generally begins from:

```text
reproduction_turn = R
reproduction_cooldown = 0
```

In an already-running process, it can instead retain the previous world's scheduler state.

Neither behavior reconstructs the scheduler state that actually existed when the save was written.

This is a real persistence debt.

For exact continuation semantics, these fields should become part of the saved simulation state.

---

# ⚠️ RNG state is also not persisted

Primordial Soup uses random-number generators for operations such as:

* parent selection;
* crossover;
* mutation;
* newborn placement;
* zone generation.

The current save payload does not persist the internal state of Python's or NumPy's random-number generators.

Therefore:

```text
save
load
continue
```

does not promise bit-for-bit continuation of the random sequence that would have occurred had the process never stopped.

The world state is restored.

The stochastic stream is not.

---

# Seeds and loaded checkpoints

Headless mode allows:

```bash
--seed N
```

before continuing a loaded checkpoint.

That gives an explicit random stream for the continuation.

This can be useful experimentally.

For example:

```text
same saved checkpoint
+
seed 1
```

versus:

```text
same saved checkpoint
+
seed 2
```

creates controlled alternate stochastic futures.

But this is different from preserving the exact original RNG state.

---

# What “restore the same world” means today

Under the current persistence contract, load restores core world state such as:

```text
population
genomes
body state
stable identities
tick count
birth/death counters
zone geometry
zone runtime state
runtime mutation values
```

It does not fully restore:

```text
reproductive scheduler phase
RNG state
historical metric buffers
inspection session
UI preferences
```

So the current save format is a strong **world checkpoint**.

It is not yet a complete bit-exact process snapshot.

That distinction matters most for reproducibility work.

---

# Save itself is not transactional on disk

The loader is transactional in memory.

The writer currently is not an atomic rename-based persistence mechanism.

The `.pkl` target is opened directly and written using:

```python
pickle.dump(...)
```

So an interruption during writing could theoretically leave a partial or corrupted file.

The loader will reject many corrupted files.

It cannot resurrect bytes that were never successfully written.

For particularly valuable experiment checkpoints, preserving copies or using distinct slot names is sensible.

---

# Save and CSV do not form one atomic transaction

The world pickle is written first.

The metrics CSV is exported afterward.

CSV write failures are caught and logged separately.

That means this state is possible:

```text
.pkl saved successfully
.csv export failed
```

The world checkpoint is still usable.

Its analytical sidecar may be missing or stale.

This is intentional separation, but it means the pair should not be treated as an all-or-nothing database transaction.

---

# Security note: pickle files must be trusted

The world-state format is:

```text
Python pickle
```

Pickle is appropriate here for a local Python application because it conveniently represents structured Python data.

It is not a safe interchange format for untrusted files.

Do not load arbitrary `.pkl` save files received from an untrusted source.

Treat Primordial Soup saves as trusted local artifacts.

The critters are dangerous enough without hostile serialization.

---

# Save portability

A save is portable only when the receiving runtime satisfies its compatibility contract.

Important requirements include:

```text
same SAVE_VERSION
compatible architecture
compatible genome layout
same lineage model
compatible derived world geometry
```

So copying:

```text
genome_pool_world_a.pkl
```

to another machine does not automatically guarantee it can be loaded there if static configuration differs.

---

# GUI and headless use the same persistence path

There is no separate headless save format.

Both modes call the same:

```text
persistence.save()
persistence.load()
```

This allows:

```text
GUI
→ save
→ headless continuation
```

and:

```text
headless
→ save
→ graphical inspection
```

when the normal compatibility requirements are satisfied.

That is an important architecture property.

There is one world format.

Not one format for watching and another for science.

---

# Language does not affect saves

Switching the interface using:

```text
T
```

changes displayed labels.

It does not alter:

```text
save keys
metric identifiers
CSV headers
genome data
lineage IDs
```

English and Portuguese UI sessions therefore share the same persistence contract.

---

# Loading does not create a new evolutionary identity

When a save is restored:

```text
existing stable IDs
```

are preserved.

The global:

```text
proximo_id
```

is restored as well.

Future newborns continue from that sequence.

For example:

```text
largest saved ID = 5,812
proximo_id       = 5,813
```

After load, the next allocated individual begins at:

```text
5,813
```

not:

```text
1
```

This keeps identity continuous across process boundaries.

---

# A fresh run is different

Pressing:

```text
R
```

creates an entirely new world.

Stable identity resets:

```text
next_critter_id = 1
```

and founder IDs begin again.

That is safe because the old world no longer exists in the runtime.

ID uniqueness is scoped to one evolutionary run, not to every universe ever created on the machine.

---

# Recreate ordering matters

The recreation path resets the ID counter **before** constructing the new founder population.

The correct order is:

```text
reset run counters
      ↓
next_critter_id = 1
      ↓
create founders
      ↓
allocate founder IDs
```

Reversing those steps would create founders with fresh IDs and then reset the allocator back to `1`.

The next save would correctly be rejected later because:

```text
proximo_id <= max(ids)
```

A regression test protects this lifecycle.

---

# Load does not silently repair identity

If a save contains:

```text
duplicate IDs
```

the loader does not assign new ones.

If:

```text
proximo_id
```

is missing from a v10 save, the loader does not infer it from:

```text
max(ids) + 1
```

If an ID is invalid, it is not renumbered.

Why?

Because identity is part of simulation history.

Rebuilding identity would make the file loadable by changing what it means.

Primordial Soup prefers rejection.

---

# Load does not silently repair population shape

The same philosophy applies to genomes and agents.

If:

```text
50 bodies
49 genomes
50 IDs
```

are present, there is no valid way to know:

> Which individual lost its genome?

So the loader does not guess.

This is the core persistence principle:

```text
validate
do not invent
```

---

# Save lifecycle

A normal graphical lifecycle is:

```text
new world
   ↓
simulation runs
   ↓
S
   ↓
.pkl checkpoint
+
.csv metrics export
   ↓
continue running
   ↓
S again
   ↓
slot is rewritten with current checkpoint
```

A slot is a checkpoint destination.

It is not an append-only history of every saved state.

If several historical checkpoints matter, preserve them under distinct names or files.

---

# Load lifecycle

A normal load follows:

```text
choose slot
    ↓
L
    ↓
read pickle
    ↓
check format/version
    ↓
parse temporary values
    ↓
validate population
    ↓
validate coordinates
    ↓
validate identity
    ↓
COMMIT
    ↓
replace world
    ↓
clear inspection
    ↓
clear metric history
    ↓
pause graphical execution
```

The loaded population is then ready to continue.

---

# Recommended experimental checkpoint pattern

Instead of repeatedly overwriting one important save:

```text
experiment
```

prefer checkpoints such as:

```text
experiment_t050k
experiment_t100k
experiment_t150k
```

or:

```text
baseline_seed_42
baseline_seed_42_branch_a
baseline_seed_42_branch_b
```

This makes the lineage of the experiment explicit.

Files also reproduce.

Mostly by copying.

---

# A persistence checklist

Before relying on a save for an experiment, know what question you are asking.

If you need:

```text
population/genome checkpoint
```

the current format is strong.

If you need:

```text
stable individual identity
```

v10 preserves it.

If you need:

```text
same environmental-zone geometry
```

the zone mask is persisted and validated.

If you need:

```text
exact reproductive scheduler continuation
```

the current format is incomplete.

If you need:

```text
exact RNG continuation
```

the current format is incomplete.

If you need:

```text
complete lifetime metric history
```

preserve CSV outputs externally; load does not restore the in-memory history.

If you need:

```text
inspection continuity
```

that is intentionally not persisted.

---

# Known persistence debts

The current implementation is substantially stricter than earlier versions, but several areas remain clear candidates for improvement.

### 1. Reproductive scheduler persistence

Add:

```text
reproduction_cooldown
reproduction_turn
```

to save/load state so continuation preserves the reproductive phase.

### 2. RNG-state persistence

If exact process continuation becomes a requirement, serialize and restore the random-generator states.

This should be designed deliberately because headless `--seed` also provides useful controlled branching semantics.

### 3. Metric-history continuation

Decide whether the CSV remains a pure export or whether long-running checkpointed experiments need explicit history import/append semantics.

### 4. Atomic file replacement

For stronger crash safety:

```text
write temporary file
fsync if required
atomic rename
```

would be safer than writing directly over the target checkpoint.

### 5. Scalar semantic validation

A future hardening pass could validate persisted runtime scalars against the same legal ranges enforced during normal interactive operation.

None of these requires weakening the current strict structural loader.

The general direction should remain:

```text
explicit state
+
strict validation
+
single commit point
```

---

# Persistence invariants

The important rules can be summarized as:

```text
A successful load must produce exactly
the configured lineage structure.
```

```text
pool, agents and ids must remain aligned.
```

```text
Every living stable ID must be unique.
```

```text
next_critter_id must be greater
than every existing ID.
```

```text
Coordinates must be valid before
density fields are rebuilt.
```

```text
The zone mask must match
the derived world geometry.
```

```text
A failed load must not partially
modify the live runtime.
```

```text
A failed load must not consume
randomness through fallback reconstruction.
```

These are more important than making every historical file load.

---

# In one sentence

Primordial Soup v10 persistence stores the current population, genomes, stable identities, core runtime parameters and environmental state in a versioned pickle, validates the complete candidate world before a single transactional commit, and exports metrics separately to CSV — while currently leaving reproductive scheduler phase, RNG state, metric-history restoration and UI/inspection state outside the checkpoint contract.

Save the world.

But know exactly which parts of the universe went into the box.

---

# Related documentation

For the runtime structures being serialized:

→ [Architecture](architecture.md)

For static persistence versions and file templates:

→ [Configuration](configuration.md)

For automated checkpoint workflows:

→ [Headless](headless.md)

For stable individual identity:

→ [Inspection](inspection.md)

For designing reproducible experiments:

→ [Experiments](experiments.md)
