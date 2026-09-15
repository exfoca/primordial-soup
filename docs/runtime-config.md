# ⚙️ Runtime Configuration

Primordial Soup separates two kinds of configuration:

```text
structural configuration
        +
runtime rules
```

Structural configuration defines what the universe **is**.

Runtime rules define how hostile, permissive, fertile, or genetically irresponsible that universe is **right now**.

This document covers the second category.

---

## 🔥 What does HOT mean?

A **HOT** rule can change while a run is active.

No restart is required.

The current rules live in a single immutable `RuntimeRules` object.

Conceptually:

```text
current rules
     ↓
create candidate
     ↓
validate everything
     ↓
valid?
 ┌───┴────┐
 yes      no
  ↓        ↓
commit    reject
```

There is no partial mutation.

If one field is invalid, the old rules remain untouched.

> The universe accepts regime change.
>
> It does not accept malformed paperwork.

The active runtime rules are also part of the checkpoint state. Loading a world restores the rules that belonged to that world.

---

# 🧬 Genetics

## Crossover

| Rule                    |  Default | Valid values                      | Meaning                                         |
| ----------------------- | -------: | --------------------------------- | ----------------------------------------------- |
| `crossover_mode`        | `blocks` | `blocks`, `uniform`, `two_points` | Genetic recombination strategy                  |
| `crossover_probability` |   `0.50` | `0.00–1.00`                       | Per-gene Parent A probability in `uniform` mode |
| `block_size`            |     `64` | `1–10245`                         | Block width in `blocks` mode                    |

### `blocks`

The genome is divided into contiguous blocks.

Each block chooses one parent.

`block_size` only matters in this mode.

### `uniform`

Each gene independently chooses between the two parents.

`crossover_probability` controls the Parent A bias:

```text
0.0 → always Parent B
0.5 → unbiased
1.0 → always Parent A
```

### `two_points`

Two random crossover points define the exchanged region.

Neither `block_size` nor `crossover_probability` controls this mode.

---

## Mutation

| Rule                    |      Default | Range / values           | Meaning                                       |
| ----------------------- | -----------: | ------------------------ | --------------------------------------------- |
| `mutation_mode`         | `two_scales` | `two_scales`, `surgical` | Mutation algorithm                            |
| `mutation_rate`         |         `5%` | `0–100%`                 | Chance that each child mutates                |
| `mutated_genes`         |          `1` | `1–50`                   | Genes replaced in `surgical` mode             |
| `local_scale_fraction`  |         `5%` | `1–100%`                 | Genome fraction affected by local mutation    |
| `local_scale_sigma`     |       `0.10` | `0.01–4.00`              | Gaussian noise strength for local mutation    |
| `global_probability`    |        `10%` | `0–100%`                 | Chance that a mutation uses the global branch |
| `global_scale_fraction` |        `20%` | `1–100%`                 | Genome fraction affected by global mutation   |
| `global_scale_sigma`    |       `1.00` | `0.01–4.00`              | Gaussian noise strength for global mutation   |

`mutation_rate` is a probability **per child**, not per gene.

### Two scales

When a child is selected for mutation:

```text
mutation
   │
   ├── local
   │     smaller fraction
   │     weaker noise
   │
   └── global
         larger fraction
         stronger noise
```

`global_probability` decides which branch is used.

The default configuration therefore roughly means:

```text
5% chance that a child mutates

if mutation happens:

90% → local mutation
      5% of genome
      sigma 0.10

10% → global mutation
      20% of genome
      sigma 1.00
```

Local mutation refines.

Global mutation explores.

Both occasionally produce something evolution will regret.

### Surgical

In `surgical` mode, exactly `mutated_genes` positions are selected for each mutating child and replaced with new gene values.

The two-scale fraction and sigma controls are irrelevant to this mode.

---

# 🧠 Behavior

| Rule                 | Default | Range            | Meaning                                    |
| -------------------- | ------: | ---------------- | ------------------------------------------ |
| `low_hp_threshold`   |  `2000` | `0–10000` HP     | Threshold used by the neural low-HP input  |
| `stay_still_impulse` |   `1.0` | any finite float | Bias added to the stay-still neural output |
| `death_hp_threshold` |     `0` | `0–10000` HP     | Critters die at or below this HP           |

---

## Low-HP threshold

The brain receives:

```text
low_hp = 1  if HP < threshold
low_hp = 0  otherwise
```

Changing the threshold changes what the organism is told about its own condition.

It does not directly change HP.

---

## Stay-still impulse

Before action selection:

```text
stay_still_output += stay_still_impulse
```

Positive values favor remaining still.

Negative values discourage it.

There is no configured numeric ceiling, but the value must be a finite float.

This is behavioral pressure, not a forced action.

The neural network can still disagree.

---

## Death threshold

Mortality is evaluated after ecological HP effects:

```text
HP <= death_hp_threshold
```

means death.

Default:

```text
0 HP
```

Raising the threshold makes the universe less forgiving.

Evolution will receive the memo through personnel turnover.

---

# 🌍 Ecology

| Rule                          | Default | Range          | Meaning                                    |
| ----------------------------- | ------: | -------------- | ------------------------------------------ |
| `base_decay_per_tick`         |     `1` | `0–10000` HP   | Basal metabolic cost per tick              |
| `predation_transfer`          |   `100` | `10–200` HP    | Maximum HP transferred per predation event |
| `damage_per_own_overcrowding` |    `10` | `10–200` HP    | Same-lineage overcrowding coefficient      |
| `zone_hp_effect`              |    `+5` | `-100–+100` HP | HP delta per tick inside active zones      |

---

## Base decay

Every living critter receives:

```text
HP -= base_decay_per_tick
```

Setting it to `0` disables basal metabolism.

This does not disable predation, overcrowding, zones, or any other ecological effect.

---

## Predation transfer

For an eligible predator-prey contact:

```text
effective_damage = min(predation_transfer, prey_HP_snapshot)
```

The prey loses that amount.

The predator side receives the transferred HP according to the multiple-predator sharing rule.

Allowed range:

```text
10–200 HP
```

Predation cannot be reduced to zero through HOT configuration.

The food chain has a minimum service level.

---

## Overcrowding

For `N >= 2` members of the same lineage occupying one cell:

```text
damage per critter =
damage_per_own_overcrowding × N
```

Allowed coefficient:

```text
10–200
```

Like predation, overcrowding cannot be disabled by setting its coefficient to zero.

Personal space is part of the constitution.

---

## Environmental zones

Inside an active zone:

```text
HP += zone_hp_effect
```

The effect can be:

```text
positive → beneficial zone
zero     → neutral geometry
negative → hazardous zone
```

Range:

```text
-100 ... +100 HP / tick
```

Zone geometry itself is not HOT.

The current zone mask remains unchanged when this value changes.

---

# 🧬 Reproduction

## Eligibility and scheduling

| Rule                           | Default | Range             | Meaning                                     |
| ------------------------------ | ------: | ----------------- | ------------------------------------------- |
| `reproduction_interval`        |   `150` | `1–100000` ticks  | Interval between global lineage turns       |
| `reproduction_min_age`         |  `5555` | `0–1000000` ticks | Minimum parent age                          |
| `reproduction_hp_gate`         | `10000` | `1–10000` HP      | Parent HP must be strictly below this value |
| `reproduction_min_encounters`  |     `6` | `0–1000000`       | Minimum encounter count                     |
| `reproduction_parent_hp_bonus` |    `50` | `0–10000` HP      | Reward given to each successful parent      |

A parent must satisfy all gates:

```text
age        >= reproduction_min_age
HP         <  reproduction_hp_gate
score      >= reproduction_min_score
encounters >= reproduction_min_encounters
```

Note the HP comparison:

```text
HP < gate
```

not:

```text
HP <= gate
```

With the default gate of `10000`, a founder at exactly `10000 HP` is not eligible on HP alone.

It must first experience life.

Usually life handles that quickly.

---

## Reproduction interval

Reproduction uses one global rotating scheduler:

```text
R → G → B → R
```

Changing `reproduction_interval` while the run is active also reconciles the current cooldown.

If the interval is reduced below the remaining cooldown:

```text
cooldown = new interval
```

If the interval is increased, an already-near reproductive turn is **not postponed**.

Example:

```text
current cooldown = 7

interval:
30 → 300

result:
cooldown remains 7
```

Changing the law does not retroactively move an appointment that was already imminent.

---

# 🏁 Parent selection

| Rule                            |     Default | Range / values           | Meaning                                         |
| ------------------------------- | ----------: | ------------------------ | ----------------------------------------------- |
| `reproduction_criterion`        | `composite` | `composite`, `longevity` | Parent ranking strategy                         |
| `reproduction_pool_fraction`    |      `0.88` | `0.01–1.00`              | Top ranked fraction admitted to the parent pool |
| `reproduction_attempts_divisor` |        `50` | `1–333`                  | Controls reproduction attempts per lineage turn |
| `reproduction_min_score`        |      `0.60` | `0.00–20.00`             | Minimum composite score required                |
| `longevity_weight`              |      `0.50` | `0.00–5.00`              | Longevity contribution                          |
| `exploration_weight`            |      `0.30` | `0.00–5.00`              | Exploration contribution                        |
| `interaction_weight`            |      `0.30` | `0.00–5.00`              | Encounter contribution                          |
| `reproduction_weight`           |      `0.30` | `0.00–5.00`              | Offspring contribution                          |

---

## Selection criterion

### Composite

Eligible critters are ranked by composite score.

### Longevity

Eligible critters are ranked by age.

The eligibility gates still apply first.

Selecting `longevity` does not allow an ancient but otherwise ineligible organism to bypass them.

---

## Reproductive pool

After eligibility and ranking:

```text
top reproduction_pool_fraction
```

becomes the parent pool.

Default:

```text
88%
```

The two actual parents are chosen from this subset.

Lower values increase selection pressure.

Higher values increase genetic participation.

---

## Reproduction attempts

For the lineage that owns the current turn:

```text
attempts =
max(
    1,
    ceil(population / reproduction_attempts_divisor)
)
```

Default divisor:

```text
50
```

Examples:

```text
population  50 → 1 attempt
population 100 → 2 attempts
population 200 → 4 attempts
```

A lower divisor produces more attempts.

A higher divisor produces fewer.

Attempts stop early if reproduction cannot produce children or the lineage reaches its population ceiling.

This knob therefore controls reproductive pressure without changing the two-parent/two-child reproductive contract.

---

# 📊 Composite score

The score combines four normalized lineage-relative components:

```text
score =
    longevity_weight    × normalized longevity
  + exploration_weight  × normalized exploration
  + interaction_weight  × normalized encounters
  + reproduction_weight × normalized offspring
```

The weights are **not probabilities**.

They do not need to sum to `1.0`.

Default:

```text
longevity     0.5
exploration   0.3
interaction   0.3
reproduction  0.3
```

Total:

```text
1.4
```

That is intentional.

With every weight at its maximum of `5.0`, the theoretical configured score ceiling is:

```text
20.0
```

Hence the valid range of `reproduction_min_score`:

```text
0.0–20.0
```

---

# 🎛️ Runtime controls that are not RuntimeRules

Not every live control represents a simulation law.

For example:

| Control                    | Runtime? | `RuntimeRules`? |
| -------------------------- | -------- | --------------- |
| Simulation speed           | yes      | no              |
| Pause / resume             | yes      | no              |
| Environmental zones ON/OFF | yes      | no              |
| Active save slot           | yes      | no              |
| Language                   | yes      | no              |
| GIF recording              | yes      | no              |
| Inspection criterion       | yes      | no              |
| Inspection lineage filter  | yes      | no              |

These control execution, presentation, or operator state.

They are not part of the immutable ecological/genetic rule set.

## Simulation speed

The `Simulation speed` control selects one of a closed set of
multipliers:

```text
0.25x
0.5x
1x
2x
4x
8x
16x
32x
64x
128x
256x
```

`1x` preserves the historical execution rate of one simulation tick
per graphical frame.

At the default `TARGET_FPS=60`:

```text
0.25x is nominally ~15 ticks/s
0.5x  is nominally ~30 ticks/s
1x    is nominally ~60 ticks/s
```

Actual ticks per second may be lower if the machine cannot sustain
the target frame rate.

The graphical target remains 60 FPS. Fractional speeds are
implemented by accumulated tick credit; slowing the simulation does
not slow the UI. At `0.25x`, for example, one tick is executed every
four active frames, while the window still redraws at the target
rate.

Simulation speed is operator/execution state. It is not
`RuntimeRules` and it is not stored in checkpoints. UI recreate
preserves the operator-selected speed across `R`.

In particular:

```text
zone_hp_effect
```

is a `RuntimeRules` law.

But:

```text
zones_active
```

is a runtime toggle.

The distinction is deliberate.

---

# 🧱 What is not HOT

Some properties define the structure of the model itself.

They are not adjustable through `RuntimeRules`.

Important examples:

| Structural property            | Current value |
| ------------------------------ | ------------: |
| Canonical lineages             | `R`, `G`, `B` |
| Initial population per lineage |          `50` |
| Maximum population per lineage |         `333` |
| Vision radius                  |           `5` |
| Vision window                  |       `11×11` |
| Visual channels                |           `3` |
| Internal neural inputs         |           `4` |
| First hidden layer             |          `25` |
| Second hidden layer            |          `12` |
| Movement outputs               |           `9` |
| Genome size                    |       `10245` |
| Initial HP                     |       `10000` |
| Environmental zones            |           `8` |
| Zone radius                    |          `27` |
| Nests per lineage              |           `1` |
| Nest radius                    |          `20` |
| Nest spawn radius              |           `1` |
| Parents per reproductive event |           `2` |
| Children per successful pair   |           `2` |

Changing these is not tuning the current universe.

It changes the model or its geometry.

---

# 💾 Checkpoints

Runtime rules belong to simulation state.

A successful load restores the complete saved `RuntimeRules` object together with the reproductive scheduler state.

This distinction matters.

A checkpoint load is:

```text
restore the old universe
```

not:

```text
apply a new runtime intervention
```

For that reason, loading does not reinterpret a saved reproductive cooldown using the HOT interval-change rules.

The saved scheduler phase is restored exactly.

> Change a rule and you are experimenting.
>
> Load a checkpoint and you are continuing history.
>
> Confusing the two is how alternate timelines acquire bugs.

---

# 🔒 Configuration invariants

The current runtime configuration contract is:

```text
RuntimeRules is immutable

all changes are validated before commit

invalid changes leave the previous rules untouched

HOT rules may change during a run

structural constants do not

saved worlds restore their own rules

percent fields use explicit percentage units

selection weights do not need to sum to 1

HP gate uses strict <
death gate uses <=

reproduction interval changes preserve scheduler coherence
```

---

## Final note

Runtime configuration is intentionally powerful.

It allows the operator to alter selection pressure without rewriting the organism:

```text
make food scarce
make collisions expensive
make predation stronger
make reproduction rare
change what counts as fitness
increase mutation
reduce mutation
reward exploration
reward longevity
turn safe zones into hazards
```

Then continue the same run and observe what happens.

The controls do not tell evolution what solution to find.

They merely change the exam.

> Evolution never complains that you changed the rules halfway through.
>
> It simply changes who dies.
