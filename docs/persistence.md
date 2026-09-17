# 💾 Persistence

A Primordial Soup checkpoint is not a population export.

It is a **continuation point for a stochastic universe**.

The contract is simple:

> **Save the world. The universe that comes back is the same universe that went in.**

That requires more than genomes. It requires enough state for the next tick after loading to belong to the same history.

**This is the single authority for checkpoint format, contents, compatibility, atomicity, and versioning.** The rules being persisted live in [World Rules](world-rules.md); configuration lifecycle and HOT rules are defined in [Runtime Configuration](runtime-config.md); the identity model lives in [Critters and Brains](critters-and-brains.md).

---

## Current format

| Property | Value |
| --- | --- |
| Format | Python `pickle` |
| Save version | `25` |
| Architecture | `mlp-2hidden-h1rec-v1` |
| Genome layout | `layout-v4` |
| Default slot | `default` |

The current contract is strict and current-schema-only. A v25 checkpoint contains **49 canonical top-level keys**.

Available graphical slots:

```text
default
world_a
world_b
world_c
```

Checkpoint filenames follow:

```text
genome_pool_{slot}.pkl
```

Metrics use the companion filename:

```text
genome_pool_{slot}_metricas.csv
```

Calling `load()` without an explicit path resolves only the canonical filename for the active slot. There is no implicit discovery fallback for an older single-file save convention.

> ⚠️ Pickle files must be treated as trusted local data.
>
> Do not load checkpoints from untrusted sources.

---

# 🧭 Three persistence axes

Primordial Soup now has three separate persistence concepts:

```text
declarative .env
    → startup/process baselines

prefs.json
    → operator preferences

checkpoint .pkl
    → universe continuation
```

None is a substitute for another.

The declarative configuration defines what a process starts with. `prefs.json` stores selected operator choices. The checkpoint stores the stochastic universe that must continue.

---

# 📦 What a checkpoint contains

## Population

Each canonical lineage record stores exactly these current fields:

```text
id
pools
agentes
ids
```

`id` is the canonical lineage identifier. `pools` stores genomes, `agentes` stores lifetime agent state, and `ids` stores stable critter IDs.

Lineage color is **not** serialized in the v25 lineage record. Color comes from the process's canonical lineage definition.

The three population arrays are logically parallel. The same `N` must apply to genome pool, agent state, and stable IDs.

```text
len(pools) == len(agentes) == len(ids)
```

No truncation, padding, guessing, or “close enough” recovery occurs during load.

---

## Runtime rules

The complete active `RuntimeRules` object is checkpoint state.

That includes genetic operators, mutation parameters, behavior parameters, mortality, ecological pressure, predation, overcrowding, reproduction, selection, and composite-score weights.

Loading restores the laws under which the saved population was evolving. Current HOT defaults from the process's `.env` do not overwrite the saved rules.

A checkpoint therefore means:

```text
continue this universe
```

not:

```text
load its organisms and apply today's defaults
```

That would be less *continue experiment* and more *change constitution during unconsciousness*.

---

## NON_HOT compatibility metadata

The current checkpoint contains:

```text
config_non_hot
```

This payload was introduced in v24 and remains part of v25. It is not a full `.env`, not a complete `ConfigSnapshot`, not `RuntimeRules`, and not operator preferences.

It contains exactly the **17 NON_HOT fields** whose current values participate in checkpoint continuation:

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

Membership is schema-driven through `ConfigFieldSpec.checkpoint_relevant` and materialized by `config_compatibility.py`.

These values must match the current process exactly in both type and value before the checkpoint is accepted.

Not all NON_HOT configuration belongs to checkpoint identity. Presentation colors, audio calibration, recording parameters, `INITIAL_POPULATION_PER_LINEAGE`, `MAX_NEST_PLACEMENT_ATTEMPTS`, and similar startup-only values do not redefine continuation of a world that already exists.

See [Runtime Configuration](runtime-config.md) for the lifecycle model.

---

## World clock and counters

The checkpoint preserves the tick counter, birth count, death count, and next stable critter ID.

`next_critter_id` matters because identity allocation must continue monotonically after loading. A new child cannot reuse the identity of a long-dead ancestor.

Genealogy has enough complications already.

---

## Reproduction scheduler

Reproduction has phase. The checkpoint stores both the cooldown and the current lineage turn.

Saving only the configured interval would be insufficient. If a world is saved with `cooldown = 17` and Blue owns the next turn, loading must continue exactly 17 ticks away from that Blue turn.

The scheduler is continuation state, not something reconstructed from current HOT defaults.

---

## Randomness is state

Primordial Soup uses Python's global `random` generator and NumPy's global RNG.

Both RNG states are persisted.

Without them:

```text
same population
+ same rules
+ same tick
≠ same future
```

World generation, reproduction, crossover, mutation, triad resolution, and other stochastic events consume those sequences. A world that looks identical at load time but has different RNG state is not the same continuation.

That is cloning.

---

## Environment

The environmental zone mask is persisted directly. The checkpoint also stores canonical zone centers, the zones-active toggle, and all other environment state required by the current schema.

Zones are not regenerated during load. Regeneration would change geography and consume randomness.

The environment is part of history.

---

## Canonical zone centers

The checkpoint stores both zone mask and canonical centers and requires them to agree.

Save validates coherence before writing. Load validates it before commit. A payload whose mask disagrees with the mask deterministically derived from the saved centers is rejected rather than repaired.

`load()` does not call `generate_zones()`.

---

## Nests

Nest centers are checkpoint state: one center for each canonical lineage.

The current process supplies the compatible NON_HOT geometry parameters such as `NEST_RADIUS` and `NEST_SPAWN_RADIUS`; those values are also protected by `config_non_hot`.

Save/load validates nest geometry, including canonical lineage count, valid coordinates, overlap rules, and interaction with environmental zones. Missing or invalid geometry is not regenerated during load.

Primordial Soup refuses to create a checkpoint that it would later refuse to load.

A surprisingly useful standard.

---

## Recent death history

The recent-death archive is current checkpoint state. The feature entered the checkpoint contract in v23 and remains part of v25.

Each death record contains the stable critter ID, canonical lineage ID, death tick, final agent row, and final genome.

Derived fields such as lineage index and display coordinates are not redundantly stored. Expiration is derived from death tick, current simulation tick, and the configured retention contract.

The archive is validated strictly: ordering, ID uniqueness, collision with living IDs, shapes, coordinates, finiteness, and retention-window validity must all hold.

The parser does not repair a non-compliant archive. It rejects the checkpoint.

---

## Stable identity

Every living organism carries a stable integer ID.

On load, identity is validated globally: IDs must satisfy the current type/range contract, remain unique across lineages, and stay below `next_critter_id`.

Population arrays may be reconstructed in memory.

Identity may not be reinvented.

---

# 🔐 Compatibility gate

Compatibility is checked before the remaining checkpoint body is allowed to become runtime state.

Conceptually:

```text
SAVE_VERSION
    ↓
ARCHITECTURE_VERSION
    ↓
GENOME_VERSION
    ↓
config_non_hot
    ↓
remaining checkpoint parse
```

A mismatch at any stage rejects the load. The currently running world remains unchanged.

The architecture identifier is:

```text
mlp-2hidden-h1rec-v1
```

It describes the structural family:

```text
MLP
two hidden layers
first hidden layer recurrent
family v1
```

Concrete widths such as the packaged baseline's `25` and `12` are not encoded into that architecture string. They are protected separately by the checkpoint-relevant NON_HOT configuration.

The genome layout identifier is:

```text
layout-v4
```

---

# 🌐 Canonical persistence language

The checkpoint format contains identifiers with mixed historical linguistic origins. In v25, however, each field has exactly one **current canonical spelling**.

There is no PT/EN alias fallback.

A key being Portuguese does not imply that an English synonym is accepted. A key being English does not imply that an older Portuguese synonym is accepted.

Persistence speaks schema.

The UI speaks to humans.

---

# ✍️ Atomic save

The checkpoint is not written directly over the existing file.

```text
serialize
   ↓
target.pkl.tmp
   ↓
successful write?
   ↓
os.replace()
   ↓
target.pkl
```

The previous checkpoint remains untouched until serialization completes. If writing fails, the temporary file is removed when possible and `save()` reports failure.

The checkpoint writer guarantees temporary-file replacement semantics. This document does not claim a directory `fsync` that the implementation does not perform.

The important invariant is:

> A failed save must not turn the previous good checkpoint into half a checkpoint.

---

# 📥 Transactional load

Loading is organized as two conceptual phases:

```text
PARSE
  ↓
validate everything locally
  ↓
COMMIT
  ↓
replace runtime state once
```

During PARSE, the active simulation is not modified. Population, rules, scheduler, geometry, RNGs, counters, identity state, and recent-death history are reconstructed into temporary local values.

Only after every check succeeds does the loader cross the commit boundary.

---

## Failed loads are non-destructive

A rejected load preserves the existing world.

That includes:

```text
population
RuntimeRules
RNG states
reproduction scheduler
zone geometry
nest geometry
recent-death archive
inspection state
metrics history
```

The precise operator/view cleanup associated with a **successful** load occurs only after commit.

Even the RNG state survives a failed load attempt. Merely trying to open a bad checkpoint must not alter the future of the current experiment.

A corrupted file does not get one free butterfly effect.

---

# ✅ Strict validation

The current loader rejects, among other failures:

```text
save version mismatch
architecture mismatch
genome layout mismatch
config_non_hot mismatch
missing or extra canonical fields
lineage count or identity mismatch
population shape mismatch
invalid or duplicate stable IDs
invalid coordinates
invalid RuntimeRules
invalid scheduler state
invalid RNG state
invalid zone geometry
invalid nest geometry
invalid recent-death archive
```

RuntimeRule semantic validation uses the shared configuration contract. Persistence is responsible for checkpoint representation, wire coercion, structural validation, and transactional commit; it is not a second owner of HOT ranges or choices.

The loader does not sample, truncate, regenerate, infer, alias, or migrate an incompatible world.

---

# 🔢 Compatibility history

The current format is v25. Earlier versions are historical context, not accepted schemas.

```text
v21  current ecology + nests
v22  canonical zone centers
v23  persistent recent-death archive
v24  NON_HOT compatibility payload
v25  canonical-only persistence cleanup
```

All predecessors are incompatible with current v25. There is no migration path.

A newer save is rejected. An older save is rejected.

A checkpoint is accepted only when the runtime can prove that it understands the stored world.

> “I can probably figure out what this old array meant” is not a persistence strategy.

---

# 🏗️ Load does not regenerate the world

A successful load restores saved state rather than calling fresh-world generation for missing pieces.

In particular:

```text
population is restored
RuntimeRules are restored
scheduler phase is restored
RNG states are restored
zone mask is restored
canonical zone centers are restored
nest centers are restored
recent-death archive is restored
```

They are not regenerated.

This avoids both different geometry and unexpected RNG consumption.

---

# 👁️ What is intentionally not restored from the checkpoint

Not everything visible in the application belongs to the universe.

| State | Restored from checkpoint? |
| --- | :---: |
| Living populations / genomes / stable IDs | Yes |
| Active `RuntimeRules` | Yes |
| RNG states | Yes |
| Scheduler phase | Yes |
| Zones-active run state | Yes |
| Recent death archive | Yes |
| Active inspected critter | No |
| Inspection dead selection | No |
| Inspection trail | No |
| Discovery criterion | No |
| Discovery lineage filter | No |
| Active panel | No |
| Language | No |
| Active save slot | No |
| Recording state | No |
| Simulation speed | No |
| Metrics chart history | No |
| Birth Waves | No |

After a successful load, the active inspection selection is cleared. An ID numerically equal to the previously observed ID may exist in the loaded world, but automatically treating it as the same observation session would create false continuity.

---

# 👤 `prefs.json`

Operator preferences are stored separately with:

```text
PREFS_VERSION = 1
```

Current persisted fields are:

```text
language
active_save_slot
discovery_criterion
discovery_lineage_filter
floating_hud_visible
music_enabled
sfx_enabled
```

`simulation_speed`, `paused`, and `zones_active` are not stored in `prefs.json`.

Headless execution does not load preferences.

The config and prefs directories are not deliberately normalized to identical platform spelling in every case. Each subsystem uses its current implementation-defined path; this document does not invent a unification that the code does not provide.

---

# 📊 Metrics sidecar

Metrics are exported separately as CSV.

Format:

```text
tick,metrica,valores
10,populacao,50;49;50
10,hp_medio,9980;9972;10004
10,taxa_de_mutacao,5
```

Per-lineage values use `;`. Metric identifiers and CSV headers are canonical format identifiers and are not localized.

The CSV is rewritten on save when metric history exists. Failure to export the analytical sidecar does not retroactively invalidate an already valid checkpoint.

```text
.pkl → continuation state
.csv → analytical sidecar
```

Disk space is cheaper than regret.

---

# 🧭 Application version versus save version

Application release and checkpoint schema are independent axes.

```text
Primordial Soup application version  → _version.py
Checkpoint compatibility schema      → SAVE_VERSION
Neural architecture family           → ARCHITECTURE_VERSION
Genome layout                         → GENOME_VERSION
Operator preferences                  → PREFS_VERSION
```

The current application version is `0.8.0`; the current checkpoint version is `25`. A normal application release does not automatically imply a new checkpoint schema, and a checkpoint schema change is not itself an application release number.

---

# 🔒 Persistence invariants

```text
v25 is the only accepted checkpoint schema
canonical checkpoint keys only
no historical key-alias fallback
no implicit legacy single-file discovery
save replaces atomically through a temporary file
load parses and validates before one commit
failed save preserves the previous checkpoint
failed load preserves the current runtime
population arrays remain in lockstep
stable IDs remain globally unique
active RuntimeRules are restored
17 checkpoint-relevant NON_HOT values must match
scheduler phase is restored
both RNG states are restored
zone geometry is restored
nest geometry is restored
recent-death history is restored
world geometry is never regenerated during load
operator preferences are separate from checkpoint state
```

---

## Final note

Persistence in Primordial Soup is not primarily about keeping data.

It is about preserving causality.

At tick `T`, the world contains a population, live rules, compatible model geometry, identities, scheduler phase, and random sequence. After loading, tick `T + 1` must continue from exactly that history.

Otherwise the checkpoint merely preserved appearances.

> 💾 **Save the world.**
>
> **The universe that comes back is the same universe that went in.**
