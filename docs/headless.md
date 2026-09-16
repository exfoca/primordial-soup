# 🤖 Headless Mode

Primordial Soup does not need a window to evolve.

The graphical interface is useful for watching, inspecting and experimenting interactively.

Headless mode is useful when you want to:

```text
run 100,000 ticks
repeat the experiment 20 times
use fixed random seeds
save the results
and not render 100,000 frames nobody will watch
```

The simulation core runs identically in both modes. Headless execution still produces every side effect that belongs to the model itself, including births and deaths, the recent-death archive, TTL expiration of death snapshots, and checkpoint persistence. Only the graphical and audio layers are skipped.

In other words:

```text
GUI      → exploration and observation
headless → automation and reproducibility
```

**This is the single authority for the CLI and headless execution.** The checkpoint format is defined in [Persistence](persistence.md); the simulation rules themselves are in [World Rules](world-rules.md).

---

# Quick start

A fresh reproducible run:

```bash
python -m primordial_soup --new -d 10000 -s world_a --seed 42
```

This means:

```text
--new      start from a fresh world
-d 10000   run 10,000 simulation ticks
-s world_a save the final world as world_a
--seed 42  seed the random generators
```

No Pygame window is opened.

At the end, the world is saved and the process exits.

---

## Graphical mode remains the default

Running `python -m primordial_soup` with no headless options opens the graphical interface normally.

Headless mode is activated when the command includes one of: `-l/--load`, `-d/--duration`, `-s/--save`, `--new`, `--seed`.

Pygame is imported only on the graphical branch. Headless execution does not require a display server.

Your evolutionary experiment does not need a monitor watching it back.

---

# CLI reference

| Option                   | Meaning                                                 |
| ------------------------ | ------------------------------------------------------- |
| `-l SLOT`, `--load SLOT` | Load a saved world before execution                     |
| `-d N`, `--duration N`   | Execute exactly N ticks                                 |
| `-s SLOT`, `--save SLOT` | Choose the final save slot                              |
| `--new`                  | Start a fresh world                                     |
| `--seed N`               | Seed the simulation RNGs                                |
| `-q`, `--quiet`          | Suppress periodic simulation logs during a headless run |
| `-v`, `--version`        | Print the application version and exit                  |

---

## `--new` — start from scratch

Constructs a completely fresh simulation before executing the requested ticks.

A fresh world initializes founder populations, random genomes, random positions, environmental zones, nest geometry, the tick counter, birth/death counters, the stable-ID sequence, reproductive-turn state, and runtime parameters.

This is the usual starting point for controlled experiments.

---

## `-d` / `--duration` — run a fixed number of ticks

Runs exactly `N` ticks before saving and exiting.

Duration must be `N >= 0`. Negative durations are rejected by the CLI.

### Duration requires an explicit starting state

This command is invalid:

```bash
python -m primordial_soup -d 10000
```

because it does not say whether the run should start fresh or continue an existing world.

The CLI deliberately refuses to guess. Use either `--new -d 10000` or `-l world_a -d 10000`.

An ambiguous experiment should fail loudly rather than quietly inventing its initial condition.

### `-d 0` is valid

Loading a world, running zero ticks, and saving is legal. Useful when you want to pass a save through the current persistence path — regenerating its companion metrics output — without advancing the simulation.

No evolution occurs. The universe wakes up, fills out paperwork, and goes back to sleep.

---

## `-l` / `--load` — continue a saved world

Loads the world, continues for `N` ticks, saves back, and exits.

When no explicit `-s` is provided, the loaded slot becomes the default output slot. This makes continuation concise.

### Load failure is fail-safe

If the requested save cannot be loaded successfully, the process aborts **without saving**.

Suppose `python -m primordial_soup -l important_experiment -d 50000` contains an invalid or incompatible save. The correct response is not:

```text
"Couldn't load it, so I created a new world
and overwrote important_experiment."
```

Primordial Soup aborts instead. There are mistakes evolution can fix. That is not one of them.

---

## `-s` / `--save` — choose the destination

Headless slot names are not restricted to the four slots cycled by the graphical `N` key. The persistence path resolves filenames from the slot name, so headless automation can use names such as `mutation_01_seed_001`, `zone_negative_seed_042`, and so on.

This is far more useful for experiment batches than four fixed names.

### Save-slot precedence

The final destination follows this order:

```text
1. explicit -s SLOT
2. otherwise, the -l SLOT
3. otherwise, default
```

This is useful when branching an experiment from a saved world.

### Branching from a save

Suppose `world_a` is an interesting population you want to preserve while continuing the experiment separately:

```bash
python -m primordial_soup -l world_a -d 10000 -s branch_a
```

Now `world_a` remains the original checkpoint and `branch_a` contains the continued world.

This is safer than repeatedly overwriting the source checkpoint.

---

## ⚠️ `--new` and `--load` together

Passing both flags is rejected by the CLI before any state is changed or any file is written. The source of the world is one; the flags are mutually exclusive.

Prefer being explicit:

```bash
python -m primordial_soup --new -d 10000 -s world_a
```

when you really mean to replace the slot with a fresh experiment.

---

## `--seed` — reproducible randomness

Primordial Soup uses two random-number sources: Python's standard `random` and NumPy's global RNG. The CLI seeds both.

This matters because different parts of the simulation consume randomness from different sources. Seeding only one would create a particularly irritating kind of reproducibility:

```text
same genomes
different geography
```

or:

```text
same geography
different genetics
```

`--seed` avoids that.

### Fresh worlds and seeds

For fresh runs with the same seed, identical configuration, and identical code, the runs begin from the same seeded random sequence, including randomness involved in world construction and subsequent simulation.

This makes seeds essential for controlled comparisons.

### Seed with a loaded world

Consider `python -m primordial_soup -l world_a -d 5000 --seed 42`.

The loaded population, genomes, positions and saved simulation state come from `world_a`. The save also carries the states of both random-number generators. Load restores them, so a load without `--seed` continues the exact stochastic sequence the original run would have produced.

When `--seed` is supplied alongside `--load`, the order is:

```text
load world_a
    ↓
restore RNG states from the checkpoint
    ↓
overwrite them with --seed 42   (deliberate branching)
    ↓
continue
```

This is the **stochastic branching** mode: the same starting world, a deliberately different future. It is the recommended way to compare alternate continuations from a common checkpoint.

If the load fails, no seed is applied and the process aborts. A failed load never consumes randomness.

### Reproducibility has boundaries

A seed is necessary for reproducibility. It is not magic.

A reproducible comparison should also keep constant: Primordial Soup version, configuration, save format, world geometry, starting state, duration, and execution path.

Changing code between two seeded runs can legitimately change their trajectories. The seed guarantees the random sequence. It does not freeze the laws of the universe.

Git commits remain useful.

---

## `-q` / `--quiet`

Long headless runs can produce periodic console logs. Use `-q` to suppress those periodic tick summaries.

The final save messages are still printed.

Quiet mode changes logging. It does not change simulation behavior.

`-q` alone does not activate headless mode. Headless detection is based on `-l`, `-d`, `-s`, `--new`, `--seed` — not on `-q`. Use it as a modifier for an already-headless command.

---

## `-v` / `--version`

Prints the current application version and exits.

The value comes from the canonical application version in `_version.py`. Useful when recording experiment provenance.

A result without its software version has already begun becoming archaeology.

---

# Edge cases and observations

## Headless commands without `-d`

The current CLI also permits headless-triggering options without a duration.

For example, `--new -s snapshot` constructs a fresh world and saves it immediately without advancing ticks. `-l world_a` loads and re-saves without stepping.

For actual evolutionary runs, prefer making duration explicit with `-d N`.

Explicit experiments are easier to understand months later.

---

## Graphical and headless saves are the same format

There is no separate headless save format. Both modes write and read the current schema.

Therefore `headless → save → GUI` works, and `GUI → save → headless` works, subject to normal save validation and compatibility rules.

See [Persistence](persistence.md).

---

## Inspecting a headless result graphically

A useful workflow is to evolve quickly headless, then open the graphical application and load the save.

If using a slot outside the four graphical UI slots, either continue analysis through the CLI or arrange the save under a graphical slot name before interactive loading.

This gives you the best of both modes:

```text
headless  → evolve quickly
graphical → inspect slowly
```

The critters experience no philosophical difficulty with the transition.

---

## Save files and metrics files

For a slot named `experiment_42`, the standard templates produce `genome_pool_experiment_42.pkl` and `genome_pool_experiment_42_metricas.csv`.

The `.pkl` file contains the saved world. The companion CSV contains recorded metrics. The `_metricas.csv` suffix is intentional and part of the persistence convention.

See [Persistence](persistence.md) for the complete format contract.

---

# Reproducible experiments

## A single experiment

```bash
python -m primordial_soup \
  --new \
  --duration 50000 \
  --seed 42 \
  --save mutation_default_seed_42 \
  --quiet
```

Record alongside it: commit, configuration, seed, duration, and treatment. Now the run has a reasonably clear provenance.

## Continue an experiment

Continuing a run that ended at tick 50,000:

```bash
python -m primordial_soup \
  --load mutation_default_seed_42 \
  --duration 50000
```

Because no `--save` is provided, the result is written back to the same slot.

## Preserve the checkpoint while continuing

If the tick-50,000 state matters:

```bash
python -m primordial_soup \
  --load mutation_default_seed_42 \
  --duration 50000 \
  --save mutation_default_seed_42_t100k
```

Now the original checkpoint and the continuation coexist.

Disk space is cheaper than regret.

---

## Running a seed sweep

A shell loop can automate repeated runs:

```bash
for seed in 1 2 3 4 5
do
    python -m primordial_soup \
        --new \
        --duration 50000 \
        --seed "$seed" \
        --save "baseline_seed_${seed}" \
        --quiet
done
```

Five independent seeded runs are already much stronger evidence than staring at one colorful world until it confirms your expectations.

---

## Comparing treatments

The ideal conceptual matrix is:

```text
             seed 1   seed 2   seed 3   seed 4   seed 5

control         ✓        ✓        ✓        ✓        ✓
treatment A     ✓        ✓        ✓        ✓        ✓
treatment B     ✓        ✓        ✓        ✓        ✓
```

The same seeds across treatments reduce one source of uncontrolled variation.

The CLI does not expose every simulation constant as an argument. That is deliberate. It is a runner, not a second configuration language.

See [Experiments](experiments.md) for methodology.

---

## CI smoke tests

Headless mode is also useful for simple runtime checks:

```bash
python -m primordial_soup \
    --new \
    --duration 100 \
    --seed 1 \
    --save ci_smoke \
    --quiet
```

A CI job can verify that the simulation boots, steps, reproduces its invariants, and serializes — without needing a graphical desktop session.

Headless execution is therefore useful for both science and *"did the latest refactor accidentally kill the universe?"*.

---

# Exit behavior

Useful current exit codes:

```text
0  normal successful CLI completion
1  requested load failed
2  invalid CLI use
```

A failure to load does not proceed to the final save. That makes exit status useful in shell automation.

---

## CLI language

The low-level CLI messages are currently written directly in English.

They do not follow the graphical interface language selected with `T`. Simulation logs that go through the normal translation layer remain separate from this.

This is intentional because the CLI is primarily an automation and scripting interface. Scripts generally prefer stable messages over multilingual existential crises.

---

# What headless mode does not do

Headless mode does not render the world, does not render Birth Waves, death markers, or Zone HP labels; does not open the inspection panel; does not record GIF frames; does not accept keyboard interaction; and does not visually show emergent behavior.

Birth Waves are presentation state owned by `ui_state.py` and are not created in headless execution. Death markers and Zone HP labels are likewise rendering-only artifacts. Their underlying data still exists in the simulation — the recent death archive is populated and persisted in both modes — but no marker is drawn because no window exists.

It executes the same simulation without the graphical observation layer.

That is precisely the point.

---

# Recommended workflow

For exploratory work:

```text
GUI → notice something interesting → form a hypothesis
```

Then:

```text
headless → run controlled seeds → save metrics → compare results
```

Finally:

```text
GUI → load representative worlds → inspect individual behavior
```

This gives you observation, measurement, and reproducibility — much stronger than any one of them alone.

---

## In one sentence

Headless mode runs the same Primordial Soup simulation without Pygame rendering, allowing fixed-duration, seeded, scriptable experiments that use the same world state and persistence format as the graphical application.

The soup does not need an audience to evolve.

---

# Related documentation

→ [Experiments](experiments.md) — designing the experiment
→ [Runtime Configuration](runtime-config.md) — tunable HOT laws
→ [Persistence](persistence.md) — save format and metrics CSV
→ [World Rules](world-rules.md) — the mechanics being executed
→ [Architecture](architecture.md) — implementation of the CLI and simulation loop
