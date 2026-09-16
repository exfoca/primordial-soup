# 💾 Persistence

A Primordial Soup checkpoint is not a population export.

It is a **continuation point for a stochastic universe**.

The contract is simple:

> **Save the world. The universe that comes back is the same universe that went in.**

That requires more than genomes. It requires enough state for the next tick after loading to belong to the same history.

**This is the single authority for checkpoint format, contents, atomicity, and versioning.** The rules being persisted live in [World Rules](world-rules.md); the HOT rules in [Runtime Configuration](runtime-config.md); the identity model in [Critters and Brains](critters-and-brains.md).

---

## Current format

| Property      | Value             |
| ------------- | ----------------- |
| Format        | Python `pickle`   |
| Save version  | `23`              |
| Architecture  | `mlp-1x25x12-rec` |
| Genome layout | `layout-v4`       |
| Default slot  | `default`         |

Available slots:

```text
default
world_a
world_b
world_c
```

Checkpoint filenames follow `genome_pool_{slot}.pkl`. Metrics use a separate companion file `genome_pool_{slot}_metricas.csv`.

> ⚠️ Pickle files must be treated as trusted local data.
>
> Do not load checkpoints from untrusted sources.

---

# 📦 What a checkpoint contains

## Population

For each lineage: lineage ID, color, genome pool, agent state, and stable critter IDs.

The three population structures are logically parallel: the same `N` must apply to all three. This is a hard invariant.

No truncation, padding, guessing, or "close enough" recovery occurs during load.

---

## Runtime rules

The complete active evolutionary rule set is persisted: genetic operators, mutation parameters, behavior parameters, mortality, ecological pressure, predation, overcrowding, reproduction, selection, and composite-score weights.

Loading therefore restores the laws under which the saved population was evolving. A checkpoint does not silently replace them with current defaults.

That would be less *continue experiment* and more *change constitution during unconsciousness*.

---

## World clock and counters

The checkpoint preserves the tick counter, birth count, death count, and next stable critter ID.

`next_critter_id` matters because identity allocation must continue monotonically after loading. A new child cannot accidentally reuse the identity of a long-dead ancestor.

Genealogy has enough complications already.

---

## Reproduction scheduler

Reproduction has phase. The checkpoint therefore stores both the cooldown and the current turn.

Saving only the configured interval would be insufficient. Example: a checkpoint taken with `cooldown = 17, turn = Blue` must, after loading, still be 17 ticks away from Blue's turn.

It must not restart the scheduler from Red merely because the process restarted.

---

## Randomness is state

Primordial Soup uses two global random-number generators: Python's `random` and NumPy's global RNG.

Both RNG states are persisted. This is essential for deterministic continuation.

Without them:

```text
same population
+ same rules
+ same tick
≠ same future
```

Random nest-related behavior, reproduction, crossover, mutation, triad resolution, and other stochastic events would consume a different sequence. The world might look identical at load time and diverge immediately afterward.

That is not continuation.

That is cloning.

---

## Environment

The environmental zone mask is persisted directly. The checkpoint also preserves the canonical zone centers, the zones-active toggle, and the zone HP effect.

Zones are **not regenerated during load**. Regeneration would consume randomness and could create different geography.

The environment is part of history.

---

## Canonical zone centers

The current schema stores both the mask and its centers, and enforces coherence: the zone mask must equal the mask deterministically rebuilt from canonical centers.

Save validates this coherence before writing. Load validates it before committing. A payload whose mask and centers disagree is rejected. It is not repaired.

`load()` never calls `generate_zones()`. Neither the mask nor the centers are re-sampled. This preserves both the saved geometry and the RNG continuation contract.

---

## Nests

Nest geometry is part of the checkpoint contract. The checkpoint stores one center for each canonical lineage.

Only the centers are persisted. Derived properties such as nest radius, protection masks, and spawn offsets come from the current structural model and are not redundantly serialized.

Before saving, nest geometry is validated. A valid checkpoint requires exactly one center per lineage, valid coordinates, no nest overlap, and no nest intersection with environmental zones.

If nest geometry is invalid, the save is aborted.

Primordial Soup refuses to create a checkpoint that it would later refuse to load.

A surprisingly useful standard.

---

## Recent death history

The recent-death archive is part of the checkpoint contract. Each death record contains the stable critter ID, the canonical lineage ID, the death tick, the final agent row, and the final genome.

Two natural fields are **not** stored: `lineage_index` (derived from the canonical lineage ID) and `x`/`y` (derived from the final agent row). There is no `remaining_ttl`: expiration is computed from the death tick and the current simulation tick.

The agent row and genome are stored as NumPy `float32` arrays directly in the pickle. Living population pools still use the historical list-of-lists format; the new death records do not.

Load rejects a checkpoint if the archive violates any of its invariants: death ticks must be non-decreasing, dead stable IDs must be unique and must not collide with living IDs, the agent and genome shapes must match the current model, coordinates must be finite and in-world, and each snapshot must still be inside the retention window.

The parser does not repair a non-compliant archive. It rejects the whole checkpoint.

---

## Stable identity

Every saved organism carries its stable integer ID.

On load, identity is validated globally: all IDs must be positive, use `int64`, be unique across lineages, and be strictly less than `next_critter_id`.

Population arrays may be rebuilt in memory.

Identity may not be reinvented.

---

# ✍️ Atomic save

The checkpoint is not written directly over the existing file. The write path is:

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

The previous checkpoint remains untouched until serialization completes. If writing fails, the temporary file is removed when possible, and `save()` returns failure.

This protects an already valid checkpoint from common failures such as serialization errors, I/O failures, disk exhaustion during write, and process interruption before replacement.

The important invariant is:

> A failed save must not turn the previous good checkpoint into half a checkpoint.

---

# 📥 Transactional load

Loading is stricter. It uses two conceptual phases:

```text
PARSE
  ↓
validate everything locally
  ↓
COMMIT
  ↓
replace runtime state
```

During PARSE, the active simulation is not modified. Population, rules, environment, scheduler, RNGs, counters, identity state, and geometry are reconstructed into temporary local structures.

Only after every validation succeeds does the loader cross the commit point.

---

## Failed loads are non-destructive

If validation fails, `load()` returns `False` and the existing world remains unchanged.

That includes population, genomes, stable IDs, runtime rules, tick, birth and death counters, next critter ID, zones, zone centers, nests, zone toggle, reproduction scheduler, both RNG states, the recent-death archive, the inspection session, and the metric history.

Even the RNG state is preserved.

This matters because merely *attempting* to load a bad checkpoint must not change the future of the currently running experiment.

A corrupted file does not get one free butterfly effect.

---

# ✅ Strict validation

The current version uses a strict checkpoint contract. A load is rejected if, among other things:

```text
save version differs
architecture differs
genome layout differs

lineage count differs
lineage identities differ

population shapes disagree
IDs are invalid or duplicated
coordinates are invalid

runtime rules are invalid
scheduler state is invalid
RNG state is invalid

zone geometry is invalid
nest geometry is invalid
required state is missing
```

The loader does not attempt structural repair. It does not sample, truncate, regenerate, infer, or migrate an incompatible world.

---

# 🔢 Compatibility policy

Compatibility metadata must match the running model exactly: save version, architecture version, and genome layout version.

A newer save is rejected. An older save is rejected.

Historical predecessors (v21 → nests + current ecological contract; v22 → canonical zone centers; v23 → persistent recent-death archive) are incompatible with the current schema.

There is currently no migration path. This is deliberate.

A checkpoint is accepted only when the runtime can prove that it understands the stored world.

> "I can probably figure out what this old array meant" is not a persistence strategy.

---

# 🏗️ Load does not regenerate the world

A successful load restores saved state. It does not call world-generation logic to recreate missing pieces.

In particular:

```text
zone mask is restored
canonical zone centers are restored
nests are restored
recent death archive is restored
RNG states are restored
population is restored
```

They are not regenerated. This avoids two problems:

```text
different geometry
+
unexpected RNG consumption
```

Both would violate deterministic continuation.

---

# 👁️ What is intentionally not restored

Not everything visible in the application belongs to the simulated universe. The following are operator or view state rather than checkpoint state:

| State                              | Restored from checkpoint? |
| ---------------------------------- | ------------------------- |
| Active inspected critter           | No                        |
| Active Inspection dead selection   | No                        |
| Inspection trail                   | No                        |
| Recent death archive               | Yes                       |
| Discovery criterion                | No                        |
| Discovery lineage filter           | No                        |
| Active panel                       | No                        |
| Language                           | No                        |
| Active save slot                   | No                        |
| Recording state                    | No                        |
| Simulation speed                   | No                        |
| Metrics chart history              | No                        |
| Birth Waves                        | No                        |

The distinction is intentional:

```text
simulation state → persisted
operator/view state → not persisted
```

After a successful load, the active inspection selection is cleared. An ID numerically equal to the previously observed ID may exist in the loaded world, but automatically treating it as the same observation session would be misleading.

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

Per-lineage values are separated with `;`. The metric identifiers and CSV header are canonical format identifiers and are not localized.

The CSV is rewritten on save when metric history exists. If CSV export fails, the checkpoint itself remains valid.

This distinction is important:

```text
.pkl → continuation state
.csv → analytical sidecar
```

The metrics sidecar can fail without destroying the universe.

A reasonable division of responsibilities.

---

# 🌐 Canonical persistence language

Internal code increasingly uses English identifiers. The save format does not follow UI localization.

Existing checkpoint keys are stable schema identifiers and may include Portuguese and historical English names. Display language is irrelevant.

Changing the interface from English to Portuguese does not alter checkpoint semantics.

Persistence speaks schema.

The UI speaks to humans.

---

# 🧭 Application version versus save version

The application release and the checkpoint schema are independent axes.

```text
Primordial Soup application version  → _version.py
Checkpoint compatibility schema      → SAVE_VERSION
```

A reader looking for the current save format should consult `config.SAVE_VERSION`. A reader looking for the software release should consult `_version.py`.

They are not the same axis.

---

# 🔒 Persistence invariants

```text
save writes atomically
load parses before committing
failed save preserves the previous checkpoint
failed load preserves the current runtime
population arrays remain in lockstep
stable IDs remain globally unique
runtime rules are restored
scheduler phase is restored
both RNG states are restored
zone geometry is restored
nest geometry is restored
world geometry is never regenerated during load
inspection is not inherited
metric history is analytical, not continuation state
only the exact current save contract is accepted
```

---

## Final note

Persistence in Primordial Soup is not primarily about keeping data.

It is about preserving causality.

At tick `T`, the world contains a population, rules, geography, identities, scheduler phase, and random sequence. After loading, tick `T + 1` must continue from exactly that state.

Otherwise the checkpoint merely preserved appearances.

> 💾 **Save the world.**
>
> **The universe that comes back is the same universe that went in.**
