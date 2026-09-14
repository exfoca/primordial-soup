# 💾 Persistence

Primordial Soup can stop a world and reconstruct it later.

A valid save preserves enough state that:

```text
save → process ends → load → the same population continues
```

while refusing to invent missing genomes, repair corrupted identities or
silently reshape an incompatible world.

When continuity and integrity conflict, Primordial Soup prefers
integrity. A rejected save is better than a successfully loaded fiction.

---

# The persistence model

Each save slot can produce two files:

```text
world state       .pkl
metric export     _metricas.csv
```

For the graphical slot `world_a`:

```text
genome_pool_world_a.pkl
genome_pool_world_a_metricas.csv
```

The two files have different responsibilities.

The `.pkl` file contains the state required to reconstruct the world.
The `.csv` file is an export of recorded metrics for analysis.

The CSV is not required to load the world. The pickle does not depend on
the CSV.

---

# Save slots

The graphical interface cycles through `default`, `world_a`, `world_b`,
`world_c` with **N**.

Headless mode accepts arbitrary slot names. See [Headless](headless.md).

---

# Saving in the graphical application

There is no direct global accelerator to save.

```text
S
↓
Session
↓
Save now
↓
Enter
```

**S** focuses the Session panel; it does not save by itself.

The Session panel exposes:

```text
Save slot    ENUM
Save now     ACTION
Load         ACTION
New world    ACTION
```

Global accelerators that remain available independently:

```text
N → cycle save slot
L → load active slot
```

Once triggered, the operation is always the same:

```text
runtime state
      ↓
build canonical payload
      ↓
pickle payload to temp file
      ↓
atomic rename
      ↓
export current metric history
      ↓
write companion CSV
```

The world-state file is the authoritative continuation artifact. The
CSV is an analytical sidecar.

The `.pkl` write is atomic: the payload is written to a `.tmp` file in
the same directory and moved into place with `os.replace()`. An
interrupted write cannot corrupt a previously valid save.

---

# Current persistence versions

```text
SAVE_VERSION         = 11
ARCHITECTURE_VERSION = "mlp-1x25x12-rec"
GENOME_VERSION       = "layout-v4"
```

These identify different compatibility boundaries.

**Save version** describes the save schema and semantic persistence
contract.

**Architecture version** identifies the neural architecture expected by
the saved world.

**Genome version** identifies the expected internal genome layout.

The version history:

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
v11  exact continuation state: reproductive scheduler phase
     and the states of both random-number generators
```

---

# Compatibility contract

The current policy is deliberately strict:

```text
save version < current       → reject
save version > current       → reject
save version != current      → reject
version metadata missing     → reject
architecture metadata missing → reject
architecture mismatch        → reject
genome metadata missing      → reject
genome mismatch              → reject
mandatory state field missing → reject
```

The v11 contract is strict: it does not accept partial payloads,
reconstruct missing state, or apply historical fallbacks.

There is no automatic migration from an older semantic save version.
Synthesizing missing state would produce a world that never existed.

---

# The v11 payload

A canonical save contains:

```text
versao                      SAVE_VERSION = 11
arquitetura                 architecture contract
genoma                      genome layout contract
mutation                    runtime mutation rate
mutategen                   runtime mutated-gene count
escala_local                runtime local-scale value
tick                        current simulation tick
proximo_id                  next globally available critter ID
nascimentos                 cumulative births
mortes                      cumulative deaths
reproduction_cooldown       ticks until next reproductive turn
reproduction_turn           lineage index owning the next turn
rng_python_state            random.getstate() snapshot
rng_numpy_state             np.random.get_state() snapshot
modificadores_ambientais    environmental-model marker
zonas                       environmental-zone mask
zonas_ativas                runtime zone toggle
efeito_hp_zonas             runtime HP effect of zones
linhagens                   serialized lineage populations
```

All of these fields are mandatory. Absence of any of them is a
rejection, not a fallback.

---

# Lineage records

Each entry under `linhagens` contains:

```text
id
cor
pools
agentes
ids
```

Runtime requires:

```text
pool.shape   = (N, GENOME_SIZE)
agents.shape = (N, AGENT_COLUMNS)
ids.shape    = (N,)
```

All three must contain the same number of individuals.

At the persistence boundary, `pool` and `agents` are converted from
`float32` matrices to nested lists, and `ids` to an `int64` list.

The spatial density field is not stored. It is reconstructed during
load from the individual coordinates.

---

# Validation

Structural:

* pool rank must be 2;
* pool, agents and ids must agree on `N`;
* pool width must be `GENOME_SIZE`;
* agents width must be `AGENT_COLUMNS`;
* ids must be 1-D.

Numeric:

* genome and agent payloads must be numeric;
* X/Y coordinates must be finite, integral, and inside current world
  bounds.

Semantic ranges:

```text
mutation                [0, 100]
mutategen               [1, 50]
escala_local            [1, 100]
efeito_hp_zonas         [-100, +100]
reproduction_cooldown   [0, REPRODUCTION_INTERVAL]
reproduction_turn       [0, TOTAL_LINEAGES - 1]
tick                    >= 0
nascimentos             >= 0
mortes                  >= 0
```

`zonas_ativas` requires strict Python `bool`. Strings, ints and
`np.bool_` are rejected.

Values outside a range are rejected, not clamped.

Identity:

```text
per lineage: ids.dtype == int64, all IDs > 0
globally:    no duplicated IDs
             proximo_id > 0
             proximo_id > max(existing IDs)
```

---

# Atomic loading

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

A malformed save produces:

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

If parsing fails, the following remain as they were before the load
attempt: population, runtime scalar values, zones, zone toggle, zone HP
effect, next stable ID, inspection session, metrics history.

A rejected load also does not consume randomness. The loader defers
RNG-dependent reconstruction until commit. A failed load cannot consume
random draws and cause a subsequent seeded run to diverge from an
identical run that never attempted the failed load.

A headless load failure aborts the process without saving. Failure does
not silently become initialization.

---

# Exact continuation

The v11 save format is a **world checkpoint plus continuation state**.

It guarantees that:

```text
N ticks → save → M ticks
```

and:

```text
N ticks → save → perturb runtime → load → M ticks
```

produce the same world state, provided configuration, code and
environment are otherwise identical.

This is verified by `tests/test_continuation.py`.

## RNG state

Both random-number generators used by the simulation are serialized and
restored:

```text
random.getstate()          (Python stdlib)
np.random.get_state()      (NumPy global legacy RNG)
```

After a load, the next draws from both generators match the draws that
an uninterrupted run would have produced at the same point.

When `--seed` is passed to `--load`, the restored RNG state is then
deliberately overwritten with the seed. This is *stochastic branching*:
same starting world, deliberately different future.

## Reproductive scheduler state

Both `state.reproduction_cooldown` and `state.reproduction_turn` are
serialized and restored.

## Stable critter identity

`ids` per lineage and the global `proximo_id` are serialized and
restored.

## Runtime mutation parameters

```text
mutation         state.mutation_rate
mutategen        state.mutated_genes
escala_local     state.local_scale_fraction
```

These are restored on successful load. The two-scale mutation path
consumes `state.local_scale_fraction` via the runtime call chain, so the
restored value is authoritative.

## Environmental zones

```text
zonas              zone mask
zonas_ativas       runtime toggle
efeito_hp_zonas    runtime HP effect per tick
```

## Birth and death counters

```text
nascimentos
mortes
```

## Tick count

`state.tick_count` and `state.last_print` are set to the saved tick.

---

# What is deliberately not persisted

Interface or observation state is not world state. Examples:

```text
inspection session
observed critter
death snapshot
inspection trail
discovery criterion / filter
chart selection
language
simulation speed
pause state
recording state
graphical navigation (ui_state)
```

---

# Inspection is cleared after load

A successful load resets the observation selection. The observed ID,
death snapshot and trail are cleared.

Even if the newly loaded world contains the same numerical critter ID,
the loader does not treat that as continuation of the old inspection
session.

---

# Metric history is not loaded

The `.pkl` payload does not contain `state.metrics_history`. After a
successful load it is cleared. The graphical charts start a fresh
in-memory history from the loaded checkpoint.

---

# The CSV is an export, not restoration state

The companion metrics file has the format:

```csv
tick,metrica,valores
10,populacao,50;50;50
10,hp_medio,9999;9999;9999
10,taxa_de_mutacao,5
```

Per-lineage values are separated by `;`. Scalar metrics contain only one
value.

Canonical metric names:

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

# Language does not affect saves

Switching the interface language changes displayed labels. It does not
alter save keys, metric identifiers, CSV headers, genome data, lineage
IDs.

---

# Security note

The world-state format is Python pickle.

Pickle is appropriate for a local Python application because it
conveniently represents structured Python data, but it is not a safe
interchange format for untrusted files.

Treat Primordial Soup saves as trusted local artifacts.

---

# Persistence invariants

```text
A successful load must produce exactly the configured lineage structure.
pool, agents and ids must remain aligned.
Every living stable ID must be unique.
proximo_id must be greater than every existing ID.
Coordinates must be valid before density fields are rebuilt.
The zone mask must match the derived world geometry.
A failed load must not partially modify the live runtime.
A failed load must not consume randomness.
```

---

# In one sentence

Primordial Soup v11 persistence stores the population, genomes, stable
identities, core runtime parameters, environmental state, reproductive
scheduler phase and both RNG states in a versioned, atomically-written
pickle; validates the complete candidate world before a single
transactional commit; and exports metrics separately to CSV.

Save the world. The universe that comes back is the same universe that
went in.

---

# Related documentation

→ [Architecture](architecture.md)
→ [Configuration](configuration.md)
→ [Headless](headless.md)
→ [Inspection](inspection.md)
→ [Experiments](experiments.md)
