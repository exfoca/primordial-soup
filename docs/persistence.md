# 💾 Persistence

A Primordial Soup checkpoint is not a population export.

It is a **continuation point for a stochastic universe**.

The contract is simple:

> **Save the world. The universe that comes back is the same universe that went in.**

That requires more than genomes.

It requires enough state for the next tick after loading to belong to the same history.

---

## Current format

Primordial Soup currently uses:

| Property      | Value             |
| ------------- | ----------------- |
| Format        | Python `pickle`   |
| Save version  | `21`              |
| Architecture  | `mlp-1x25x12-rec` |
| Genome layout | `layout-v4`       |
| Default slot  | `default`         |

Available slots:

```text id="0u7jm5"
default
world_a
world_b
world_c
```

Checkpoint filenames follow:

```text id="a5d672"
genome_pool_{slot}.pkl
```

Metrics use a separate companion file:

```text id="jsxddo"
genome_pool_{slot}_metricas.csv
```

> ⚠️ Pickle files must be treated as trusted local data.
>
> Do not load checkpoints from untrusted sources.

---

# 📦 What a checkpoint contains

A checkpoint preserves the simulation state required for continuation.

## Population

For each lineage:

```text id="1x6iqv"
lineage ID
color
genome pool
agent state
stable critter IDs
```

The three population structures are logically parallel:

```text id="mkfyck"
pool.shape   == (N, 10245)
agents.shape == (N, 36)
ids.shape    == (N,)
```

The same `N` must apply to all three.

This is a hard invariant.

No truncation, padding, guessing, or “close enough” recovery occurs during load.

---

## Runtime rules

The complete active evolutionary rule set is persisted, including:

```text id="v8jvp0"
genetic operators
mutation parameters
behavior parameters
mortality
ecological pressure
predation
overcrowding
reproduction
selection
composite-score weights
```

Loading therefore restores the laws under which the saved population was evolving.

A checkpoint does not silently replace them with current defaults.

That would be less “continue experiment” and more “change constitution during unconsciousness.”

---

## World clock and counters

The checkpoint preserves:

```text id="td72zm"
tick
birth count
death count
next stable critter ID
```

`next_critter_id` matters because identity allocation must continue monotonically after loading.

A new child cannot accidentally reuse the identity of a long-dead ancestor.

Genealogy has enough complications already.

---

# 🧬 Reproduction scheduler

Reproduction has phase.

The checkpoint therefore stores both:

```text id="x61q8d"
reproduction_cooldown
reproduction_turn
```

Saving only the configured interval would be insufficient.

Example:

```text id="w0t2mg"
interval = 150
cooldown = 17
next lineage = Blue
```

After loading, the world must still be 17 ticks away from Blue's turn.

It must not restart the scheduler from Red merely because the process restarted.

---

# 🎲 Randomness is state

Primordial Soup uses two global random-number generators:

```text id="j60zrh"
Python random
NumPy random
```

Both RNG states are persisted.

This is essential for deterministic continuation.

The checkpoint therefore stores:

```text id="yxa6wk"
rng_python_state
rng_numpy_state
```

Without them:

```text id="43yo7h"
same population
+ same rules
+ same tick
≠ same future
```

Random nest-related behavior, reproduction, crossover, mutation, triad resolution, and other stochastic events would consume a different sequence.

The world might look identical at load time and diverge immediately afterward.

That is not continuation.

That is cloning.

---

# 🌍 Environment

The environmental zone mask is persisted directly.

The checkpoint also preserves:

```text id="ndgfc9"
zones active / inactive
zone HP effect
```

Zones are **not regenerated during load**.

Regeneration would consume randomness and could create different geography.

The environment is part of history.

---

# 🪺 Nests

Save version 21 makes nest geometry part of the checkpoint contract.

The checkpoint stores one center for each canonical lineage:

```text id="l07er4"
R → [x, y]
G → [x, y]
B → [x, y]
```

Only the centers are persisted.

Derived properties such as:

```text id="3t6i72"
nest radius
protection masks
spawn offsets
```

come from the current structural model and are not redundantly serialized.

Before saving, nest geometry is validated.

A valid checkpoint requires:

```text id="98jg7f"
exactly one center per lineage
valid coordinates
no nest overlap
no nest intersection with environmental zones
```

If nest geometry is invalid, the save is aborted.

Primordial Soup refuses to create a checkpoint that it would later refuse to load.

A surprisingly useful standard.

---

# 🪪 Stable identity

Every saved organism carries its stable integer ID.

On load, identity is validated globally.

The contract requires:

```text id="s7yydv"
all IDs > 0
IDs use int64
no duplicate IDs
next_critter_id > every existing ID
```

Population arrays may be rebuilt in memory.

Identity may not be reinvented.

---

# ✍️ Atomic save

The `.pkl` checkpoint is not written directly over the existing file.

The write path is:

```text id="xb75du"
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

The previous checkpoint remains untouched until serialization completes.

If writing fails, the temporary file is removed when possible and `save()` returns failure.

This protects an already valid checkpoint from common failures such as:

```text id="tqv12t"
serialization error
I/O failure
disk exhaustion during write
process interruption before replacement
```

The important invariant is:

> A failed save must not turn the previous good checkpoint into half a checkpoint.

---

# 📥 Transactional load

Loading is stricter.

It uses two conceptual phases:

```text id="s96mso"
PARSE
  ↓
validate everything locally
  ↓
COMMIT
  ↓
replace runtime state
```

During **PARSE**, the active simulation is not modified.

Population, rules, environment, scheduler, RNGs, counters, identity state, and geometry are reconstructed into temporary local structures.

Only after every validation succeeds does the loader cross the commit point.

---

## Failed loads are non-destructive

If validation fails:

```text id="xr1a0a"
load() → False
```

and the existing world remains unchanged.

That includes:

```text id="n9zocg"
population
genomes
stable IDs
runtime rules
tick
birth/death counters
next critter ID
zones
nests
zone toggle
reproduction scheduler
Python RNG
NumPy RNG
inspection session
metric history
```

Even the RNG state is preserved.

This matters because merely *attempting* to load a bad checkpoint must not change the future of the currently running experiment.

A corrupted file does not get one free butterfly effect.

---

# ✅ Strict validation

Version 21 uses a strict checkpoint contract.

A load is rejected if, among other things:

```text id="y3itnu"
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

The loader does not attempt structural repair.

It does not sample, truncate, regenerate, infer, or migrate an incompatible world.

---

# 🔢 Compatibility policy

Compatibility metadata must match the running model exactly:

```text id="03irvf"
SAVE_VERSION          = 21
ARCHITECTURE_VERSION  = mlp-1x25x12-rec
GENOME_VERSION        = layout-v4
```

A newer save is rejected.

An older save is rejected.

Version 20 is explicitly incompatible with version 21.

There is currently no migration path.

This is deliberate.

A checkpoint is accepted only when the runtime can prove that it understands the stored world.

> “I can probably figure out what this old array meant” is not a persistence strategy.

---

# 🏗️ Load does not regenerate the world

A successful load restores saved state.

It does not call world-generation logic to recreate missing pieces.

In particular:

```text id="9vt4c3"
zones are restored
nests are restored
RNG states are restored
population is restored
```

They are not regenerated.

This avoids two problems:

```text id="8mcg63"
different geometry
+
unexpected RNG consumption
```

Both would violate deterministic continuation.

---

# 👁️ What is intentionally not restored

Not everything visible in the application belongs to the simulated universe.

The following are operator or view state rather than checkpoint state:

| State                     | Restored from checkpoint? |
| ------------------------- | ------------------------- |
| Observed critter          | No                        |
| Inspection death snapshot | No                        |
| Inspection trail          | No                        |
| Discovery criterion       | No                        |
| Discovery lineage filter  | No                        |
| Active panel              | No                        |
| Language                  | No                        |
| Active save slot          | No                        |
| Recording state           | No                        |
| Simulation speed          | No                        |
| Metrics chart history     | No                        |

The distinction is intentional:

```text id="by181e"
simulation state → persisted
operator/view state → not persisted
```

After a successful load, the active inspection selection is cleared.

An ID numerically equal to the previously observed ID may exist in the loaded world, but automatically treating it as the same observation session would be misleading.

---

# 📊 Metrics sidecar

Metrics are exported separately as CSV.

Format:

```text id="uaxrmd"
tick,metrica,valores
10,populacao,50;49;50
10,hp_medio,9980;9972;10004
10,taxa_de_mutacao,5
```

Per-lineage values are separated with `;`.

The metric identifiers and CSV header are canonical format identifiers and are not localized.

The CSV is rewritten on save when metric history exists.

If CSV export fails, the checkpoint itself remains valid.

This distinction is important:

```text id="kgicox"
.pkl → continuation state
.csv → analytical sidecar
```

The metrics sidecar can fail without destroying the universe.

A reasonable division of responsibilities.

---

# 🌐 Canonical persistence language

Internal code increasingly uses English identifiers.

The save format does not follow UI localization.

Existing checkpoint keys are stable schema identifiers and may include Portuguese and historical English names.

Display language is irrelevant.

Changing the interface from English to Portuguese does not alter checkpoint semantics.

Persistence speaks schema.

The UI speaks to humans.

---

# 🔒 Persistence invariants

The current persistence contract can be summarized as:

```text id="xcuhh5"
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

At tick `T`, the world contains a population, rules, geography, identities, scheduler phase, and random sequence.

After loading, tick `T + 1` must continue from exactly that state.

Otherwise the checkpoint merely preserved appearances.

> 💾 **Save the world.**
>
> **The universe that comes back is the same universe that went in.**
