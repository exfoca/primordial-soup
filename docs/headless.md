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

In other words:

```text
GUI      → exploration and observation
headless → automation and reproducibility
```

For serious repeated experiments, headless mode should usually do the heavy lifting.

---

# Quick start

A fresh reproducible run:

```bash
python -m primordial_soup --new -d 10000 -s world_a --seed 42
```

This means:

```text
--new
start from a fresh world

-d 10000
run 10,000 simulation ticks

-s world_a
save the final world as world_a

--seed 42
seed the random generators
```

No Pygame window is opened.

At the end, the world is saved and the process exits.

---

# Graphical mode remains the default

Run:

```bash
python -m primordial_soup
```

with no headless options and Primordial Soup opens normally in graphical mode.

Headless mode is activated when the command includes one of:

```text
-l / --load
-d / --duration
-s / --save
--new
--seed
```

Pygame is imported only on the graphical branch.

That means headless execution does not require opening or initializing a display.

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
| `-v`, `--version`        | Print the Primordial Soup version and exit              |

---

# --new — start from scratch

Use:

```bash
python -m primordial_soup --new -d 10000
```

to construct a completely fresh simulation before executing the requested ticks.

A fresh world initializes things such as:

```text
founder populations
random genomes
random positions
environmental zones
tick counter
birth/death counters
stable-ID sequence
reproductive-turn state
runtime parameters
```

This is the usual starting point for controlled experiments.

---

# -d / --duration — run a fixed number of ticks

Example:

```bash
python -m primordial_soup --new -d 50000
```

runs exactly:

```text
50,000 ticks
```

before saving and exiting.

Duration must be:

```text
N >= 0
```

Negative durations are rejected by the CLI.

---

# Duration requires an explicit starting state

This command is invalid:

```bash
python -m primordial_soup -d 10000
```

because it does not say whether the run should:

```text
start fresh
```

or:

```text
continue an existing world
```

The CLI deliberately refuses to guess.

Use either:

```bash
python -m primordial_soup --new -d 10000
```

or:

```bash
python -m primordial_soup -l world_a -d 10000
```

An ambiguous experiment should fail loudly rather than quietly inventing its initial condition.

---

# -d 0 is valid

This is legal:

```bash
python -m primordial_soup -l world_a -d 0
```

It means:

```text
load world_a
run zero ticks
save
exit
```

This can be useful when you want to pass a save through the current persistence path and regenerate its companion metrics output without advancing the simulation.

No evolution occurs.

The universe wakes up, fills out paperwork, and goes back to sleep.

---

# -l / --load — continue a saved world

Example:

```bash
python -m primordial_soup -l world_a -d 5000
```

The sequence is:

```text
load world_a
     ↓
continue for 5,000 ticks
     ↓
save back to world_a
     ↓
exit
```

When no explicit `-s` is provided, the loaded slot becomes the default output slot.

This makes continuation concise.

---

# Load failure is fail-safe

If the requested save cannot be loaded successfully:

```text
load
 ↓
validation fails
 ↓
abort
 ↓
DO NOT SAVE
```

This is important.

Suppose:

```bash
python -m primordial_soup -l important_experiment -d 50000
```

contains an invalid or incompatible save.

The correct response is not:

```text
"Couldn't load it, so I created a new world
and overwrote important_experiment."
```

Primordial Soup aborts instead.

There are mistakes evolution can fix.

That is not one of them.

---

# -s / --save — choose the destination

Use:

```bash
python -m primordial_soup --new -d 10000 -s experiment_01
```

to save the resulting world under:

```text
experiment_01
```

Headless slot names are not restricted to the four slots cycled by the graphical **N** key.

The graphical interface currently cycles:

```text
default
world_a
world_b
world_c
```

but the persistence path itself resolves filenames from the slot name.

So headless automation can use names such as:

```text
mutation_01_seed_001
mutation_01_seed_002
mutation_05_seed_001
zone_negative_seed_042
```

which is far more useful for experiment batches.

---

# Save-slot precedence

The final destination follows this order:

```text
1. explicit -s SLOT
2. otherwise, the -l SLOT
3. otherwise, default
```

Examples:

```bash
python -m primordial_soup --new -d 1000
```

saves to:

```text
default
```

while:

```bash
python -m primordial_soup -l world_a -d 1000
```

saves to:

```text
world_a
```

and:

```bash
python -m primordial_soup -l world_a -d 1000 -s world_b
```

loads:

```text
world_a
```

but saves the result to:

```text
world_b
```

This is useful when branching an experiment from a saved world.

---

# Branching from a save

Suppose `world_a` is an interesting population.

You want to preserve it and continue the experiment separately.

Use:

```bash
python -m primordial_soup -l world_a -d 10000 -s branch_a
```

Now:

```text
world_a
remains the original checkpoint

branch_a
contains the continued world
```

Conceptually:

```text
world_a
   │
   └── +10,000 ticks
          ↓
       branch_a
```

This is safer than repeatedly overwriting the source checkpoint.

---

# ⚠️ --new and --load together

This command is accepted:

```bash
python -m primordial_soup --new -l world_a -d 10000
```

But its semantics deserve attention.

`--new` wins when choosing the starting world.

So:

```text
world_a is NOT loaded
```

A fresh world is created.

However, unless `-s` is also supplied, the normal save-slot precedence still sees:

```text
-l world_a
```

and uses:

```text
world_a
```

as the output slot.

So the command effectively means:

```text
ignore the contents of world_a
start fresh
run 10,000 ticks
overwrite world_a
```

That may be intentional.

It may also ruin your afternoon.

For clarity, prefer:

```bash
python -m primordial_soup --new -d 10000 -s world_a
```

when you really mean to replace the slot with a fresh experiment.

---

# --seed — reproducible randomness

Example:

```bash
python -m primordial_soup --new -d 50000 --seed 42 -s run_42
```

Primordial Soup uses two random-number sources:

```text
Python stdlib random
+
NumPy global RNG
```

The CLI seeds both.

This matters because different parts of the simulation consume randomness from different sources.

Seeding only one would create a particularly irritating kind of reproducibility:

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

---

# Fresh worlds and seeds

For fresh runs:

```bash
python -m primordial_soup --new -d 10000 --seed 42 -s a
```

and:

```bash
python -m primordial_soup --new -d 10000 --seed 42 -s b
```

should begin from the same seeded random sequence when configuration and code are otherwise identical.

That includes randomness involved in world construction and subsequent simulation.

This makes seeds essential for controlled comparisons.

---

# Seed with a loaded world

Consider:

```bash
python -m primordial_soup -l world_a -d 5000 --seed 42
```

The loaded population, genomes, positions and saved simulation state come from:

```text
world_a
```

The save also carries the states of both random-number generators
(`random` and `np.random`). Load restores them, so a load without
`--seed` continues the exact stochastic sequence the original run
would have produced.

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

This is the *stochastic branching* mode: the same starting world, a
deliberately different future. It is the recommended way to compare
alternate continuations from a common checkpoint.

If the load fails, no seed is applied and the process aborts. A
failed load never consumes randomness.

---

# Reproducibility has boundaries

A seed is necessary for reproducibility.

It is not magic.

A reproducible comparison should also keep constant:

```text
Primordial Soup version
configuration
save format
world geometry
starting state
duration
execution path
```

Changing code between two seeded runs can legitimately change their trajectories.

The seed guarantees the random sequence.

It does not freeze the laws of the universe.

Git commits remain useful.

---

# -q / --quiet

Long headless runs can produce periodic console logs.

Use:

```bash
python -m primordial_soup --new -d 100000 -s marathon --seed 42 -q
```

to suppress those periodic tick summaries.

The final save messages are still printed.

Quiet mode changes logging.

It does not change simulation behavior.

---

# -q alone does not activate headless mode

This is a subtle current CLI behavior.

Headless detection is based on:

```text
-l
-d
-s
--new
--seed
```

but not on:

```text
-q
```

So `-q` should be treated as a modifier for an already-headless command.

Use:

```bash
python -m primordial_soup --new -d 100000 -q
```

not:

```bash
python -m primordial_soup -q
```

if your intention is headless execution.

---

# --version

Use:

```bash
python -m primordial_soup --version
```

or:

```bash
python -m primordial_soup -v
```

to print the current world version and exit.

For the current release:

```text
primordial_soup 0.4.0
```

This is useful when recording experiment provenance.

A result without its software version has already begun becoming archaeology.

---

# Headless commands without -d

The current CLI also permits headless-triggering options without a duration.

For example:

```bash
python -m primordial_soup --new -s snapshot
```

constructs a fresh world and saves it immediately without advancing simulation ticks.

Likewise:

```bash
python -m primordial_soup -l world_a
```

loads `world_a` and then saves it again without stepping the simulation.

And:

```bash
python -m primordial_soup --seed 42
```

creates a seeded fresh world and saves it to the default slot without advancing ticks.

For actual evolutionary runs, prefer making duration explicit:

```bash
-d N
```

Explicit experiments are easier to understand months later.

---

# Graphical and headless saves are the same format

There is no separate:

```text
headless save format
```

Headless execution calls the same persistence layer used by the graphical application.

Therefore:

```text
headless → save → GUI
```

works.

And:

```text
GUI → save → headless
```

works.

Subject, of course, to normal save validation and compatibility rules.

See [Persistence](persistence.md).

---

# Inspect a headless result graphically

A useful workflow is:

```bash
python -m primordial_soup --new -d 50000 -s evolved_42 --seed 42
```

Then launch the graphical application:

```bash
python -m primordial_soup
```

and load the corresponding save.

If using a slot outside the four graphical UI slots, either continue analysis through the CLI or arrange the save under a graphical slot name before interactive loading.

This gives you the best of both modes:

```text
headless
→ evolve quickly

graphical
→ inspect slowly
```

The critters experience no philosophical difficulty with the transition.

---

# Save files and metrics files

For a slot named:

```text
experiment_42
```

the standard templates produce:

```text
genome_pool_experiment_42.pkl
```

and:

```text
genome_pool_experiment_42_metricas.csv
```

The `.pkl` file contains the saved world.

The companion CSV contains recorded metrics.

The `_metricas.csv` suffix is intentional and part of the persistence convention.

See [Persistence](persistence.md) for the complete format contract.

---

# A reproducible single experiment

For example:

```bash
python -m primordial_soup \
  --new \
  --duration 50000 \
  --seed 42 \
  --save mutation_default_seed_42 \
  --quiet
```

Record alongside it:

```text
commit
configuration
seed = 42
duration = 50,000
treatment = default mutation
```

Now the run has a reasonably clear provenance.

---

# Continue an experiment

Suppose the first run ended at tick 50,000.

Continue another 50,000:

```bash
python -m primordial_soup \
  --load mutation_default_seed_42 \
  --duration 50000
```

Because no `--save` is provided, the result is written back to:

```text
mutation_default_seed_42
```

The simulation now advances from the saved tick rather than starting over.

---

# Preserve the checkpoint while continuing

If the tick-50,000 state matters:

```bash
python -m primordial_soup \
  --load mutation_default_seed_42 \
  --duration 50000 \
  --save mutation_default_seed_42_t100k
```

Now you have:

```text
mutation_default_seed_42
→ checkpoint at 50k

mutation_default_seed_42_t100k
→ continuation at 100k
```

This is usually a better experimental habit.

Disk space is cheaper than regret.

---

# Running a seed sweep

A shell loop can automate repeated runs.

For example:

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

Now you have five independent seeded runs.

This is already much stronger evidence than staring at one colorful world until it confirms your expectations.

---

# Comparing treatments

Suppose you want to compare several configurations.

The ideal conceptual matrix is:

```text
             seed 1   seed 2   seed 3   seed 4   seed 5

control         ✓        ✓        ✓        ✓        ✓
treatment A     ✓        ✓        ✓        ✓        ✓
treatment B     ✓        ✓        ✓        ✓        ✓
```

The same seeds across treatments reduce one source of uncontrolled variation.

Remember that configuration changes currently require changing the configuration itself unless the parameter has a runtime/CLI path.

The CLI does not expose every simulation constant as an argument.

That is deliberate.

It is a runner, not a second configuration language.

---

# CI smoke tests

Headless mode is also useful for simple runtime checks.

For example:

```bash
python -m primordial_soup \
    --new \
    --duration 100 \
    --seed 1 \
    --save ci_smoke \
    --quiet
```

A CI job can verify that the simulation:

```text
boots
steps
reproduces its invariants
and serializes
```

without needing a graphical desktop session.

Headless execution is therefore useful for both:

```text
science
```

and:

```text
"did the latest refactor accidentally kill the universe?"
```

---

# Exit behavior

Useful current exit codes include:

```text
0
normal successful CLI completion

1
requested load failed

2
invalid CLI use such as -d without --new or --load
```

Argument-parsing errors are also handled by `argparse` in the usual CLI manner.

A failure to load does not proceed to the final save.

That makes exit status useful in shell automation.

---

# CLI language

The low-level CLI messages are currently written directly in English.

They do not follow the graphical interface language selected with:

```text
T
```

Simulation logs that go through the normal translation layer remain separate from this.

This is intentional because the CLI is primarily an automation and scripting interface.

Scripts generally prefer stable messages over multilingual existential crises.

---

# What headless mode does not do

Headless mode does not:

* render the world;
* open the inspection panel;
* record GIF frames;
* accept keyboard interaction;
* visually show emergent behavior;
* automatically analyze experiment results;
* make one run statistically significant.

It executes the same simulation without the graphical observation layer.

That is precisely the point.

---

# Recommended workflow

For exploratory work:

```text
GUI
↓
notice something interesting
↓
form a hypothesis
```

Then:

```text
headless
↓
run controlled seeds
↓
save metrics
↓
compare results
```

Finally:

```text
GUI
↓
load representative worlds
↓
inspect individual behavior
```

This gives you:

```text
observation
+
measurement
+
reproducibility
```

which is much stronger than any one of them alone.

---

# In one sentence

Headless mode runs the same Primordial Soup simulation without Pygame rendering, allowing fixed-duration, seeded, scriptable experiments that use the same world state and persistence format as the graphical application.

The soup does not need an audience to evolve.

---

# Related documentation

For designing the experiment:

→ [Experiments](experiments.md)

For configuration and tunable laws:

→ [Configuration](configuration.md)

For the save format and metrics CSV:

→ [Persistence](persistence.md)

For the simulation mechanics being executed:

→ [Simulation](simulation.md)

For the implementation of the CLI and simulation loop:

→ [Architecture](architecture.md)
