# ⚙️ Runtime Configuration

Primordial Soup separates two kinds of configuration:

```text
structural configuration
        +
runtime rules
```

Structural configuration defines what the universe **is**. Runtime rules define how hostile, permissive, fertile, or genetically irresponsible that universe is **right now**.

**This is the single authority for what is HOT and how it can change.** The ecological semantics themselves live in [World Rules](world-rules.md); the evolutionary semantics live in [Evolution](evolution.md).

---

## 🔥 What does HOT mean?

A **HOT** rule can change while a run is active. No restart is required.

The current rules live in a single immutable `RuntimeRules` object. Conceptually:

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

There is no partial mutation. If one field is invalid, the old rules remain untouched.

> The universe accepts regime change.
>
> It does not accept malformed paperwork.

Active runtime rules are part of the checkpoint state. Loading a world restores the rules that belonged to that world.

---

# 🧱 What is not HOT

Some properties define the structure of the model itself and are **not** adjustable through `RuntimeRules`.

Examples include the canonical lineages, initial and maximum population per lineage, vision radius and window size, visual channels, internal neural input count, hidden layer sizes, movement output count, genome size, initial HP, number of zones and their radius, nests per lineage and nest radius, and the fixed parent/child counts per reproductive event.

Changing these is not tuning the current universe. It changes the model or its geometry.

See [Architecture](architecture.md) for the structural-versus-runtime boundary.

---

# 🧬 Genetics

## Crossover

| Rule                    | Default    | Meaning                                          |
| ----------------------- | ---------- | ------------------------------------------------ |
| `crossover_mode`        | `blocks`   | Genetic recombination strategy                   |
| `crossover_probability` | `0.50`     | Per-gene Parent A bias in `uniform` mode         |
| `block_size`            | `64`       | Block width in `blocks` mode                     |

Valid crossover modes: `blocks`, `uniform`, `two_points`.

- **`blocks`** — the genome is divided into contiguous blocks; each block chooses one parent. `block_size` matters only in this mode.
- **`uniform`** — each gene independently chooses between the two parents. `crossover_probability` controls the Parent A bias.
- **`two_points`** — two random crossover points define the exchanged region. Neither `block_size` nor `crossover_probability` controls this mode.

See [Evolution](evolution.md) for the full crossover model.

---

## Mutation

| Rule                    | Default      | Meaning                                       |
| ----------------------- | ------------ | --------------------------------------------- |
| `mutation_mode`         | `two_scales` | Mutation algorithm                            |
| `mutation_rate`         | `5%`         | Chance that each child mutates                |
| `mutated_genes`         | `1`          | Genes replaced in `surgical` mode             |
| `local_scale_fraction`  | `5%`         | Genome fraction affected by local mutation    |
| `local_scale_sigma`     | `0.10`       | Gaussian noise strength for local mutation    |
| `global_probability`    | `10%`        | Chance that a mutation uses the global branch |
| `global_scale_fraction` | `20%`        | Genome fraction affected by global mutation   |
| `global_scale_sigma`    | `1.00`       | Gaussian noise strength for global mutation   |

Valid mutation modes: `two_scales`, `surgical`.

`mutation_rate` is a probability **per child**, not per gene.

When a child is selected for mutation under `two_scales`, `global_probability` decides which branch runs:

```text
local  → smaller fraction, weaker noise
global → larger fraction, stronger noise
```

In `surgical` mode, exactly `mutated_genes` positions are selected for each mutating child and replaced with new gene values. The two-scale fraction and sigma controls are irrelevant to this mode.

Local mutation refines. Global mutation explores. Both occasionally produce something evolution will regret.

See [Evolution](evolution.md) for the full mutation model.

---

# 🧠 Behavior

| Rule                 | Default | Meaning                                    |
| -------------------- | ------- | ------------------------------------------ |
| `low_hp_threshold`   | `2000`  | Threshold used by the neural low-HP input  |
| `stay_still_impulse` | `1.0`   | Bias added to the stay-still neural output |
| `death_hp_threshold` | `0`     | Critters die at or below this HP           |

---

## Low-HP threshold

The brain receives `low_hp = 1` if HP is below the threshold, `0` otherwise.

Changing the threshold changes what the organism is told about its own condition. It does not directly change HP.

---

## Stay-still impulse

Before action selection, the stay-still output receives the configured impulse. Positive values favor remaining still. Negative values discourage it.

This is behavioral pressure, not a forced action. The neural network can still disagree.

---

## Death threshold

Mortality is evaluated after ecological HP effects: `HP <= death_hp_threshold` means death.

Raising the threshold makes the universe less forgiving. Evolution will receive the memo through personnel turnover.

---

# 🌍 Ecology

| Rule                          | Default | Meaning                                    |
| ----------------------------- | ------- | ------------------------------------------ |
| `base_decay_per_tick`         | `1`     | Basal metabolic cost per tick              |
| `predation_transfer`          | `100`   | Maximum HP transferred per predation event |
| `damage_per_own_overcrowding` | `10`    | Same-lineage overcrowding coefficient      |
| `zone_hp_effect`              | `+5`    | HP delta per tick inside active zones      |

---

## Base decay

Every living critter loses `base_decay_per_tick` HP every tick. Setting it to zero disables basal metabolism, but does not disable predation, overcrowding, zones, or any other ecological effect.

---

## Predation transfer

For an eligible predator-prey contact, the effective damage is the transfer value capped by the prey's HP snapshot. The prey loses that amount; the predator side receives the transferred HP according to the multiple-predator sharing rule.

Predation cannot be reduced to zero through HOT configuration.

The food chain has a minimum service level.

---

## Overcrowding

For two or more members of the same lineage occupying one cell, damage per critter scales with the population count and the configured coefficient.

Like predation, overcrowding cannot be disabled by setting its coefficient to zero.

Personal space is part of the constitution.

---

## Environmental zones

Inside an active zone, the critter's HP changes by `zone_hp_effect` per tick. The effect can be positive (refuge), zero (neutral geometry), or negative (hazard).

The current value is the authority for both the ecological delta applied next tick and the value displayed in the Telemetry HUD, the Configuration panel, and the on-map zone label.

Zone geometry itself is not HOT. Changing `zone_hp_effect` does not regenerate the mask or the canonical centers. The current zone mask and center tuple remain unchanged when this value changes.

---

## Zones ON / OFF

`zones_active` is a runtime toggle, not a `RuntimeRule`.

When zones are OFF:

```text
no zone HP delta is applied
no zone HP map label is drawn
zone mask and canonical centers remain stored
```

Toggling zones back on restores the same geography. The mask and centers are not regenerated by the toggle. Only ecological application and label rendering are suppressed.

---

# 🧬 Reproduction

## Eligibility and scheduling

| Rule                           | Default | Meaning                                       |
| ------------------------------ | ------- | --------------------------------------------- |
| `reproduction_interval`        | `150`   | Interval between global lineage turns         |
| `reproduction_min_age`         | `5555`  | Minimum parent age                            |
| `reproduction_hp_gate`         | `10000` | Parent HP must be strictly below this value   |
| `reproduction_min_encounters`  | `6`     | Minimum encounter count                       |
| `reproduction_parent_hp_bonus` | `50`    | Reward given to each successful parent        |

A parent must satisfy all four eligibility gates simultaneously. See [Evolution](evolution.md) for the gate semantics.

Note the HP comparison: `HP < gate`, not `HP <= gate`. A critter still at untouched full health does not qualify through this gate.

It must first experience life. Usually life handles that quickly.

---

## Reproduction interval

Reproduction uses one global rotating scheduler: `R → G → B → R → …`.

Changing `reproduction_interval` while the run is active also reconciles the current cooldown:

- If the interval is reduced below the remaining cooldown, the cooldown is clamped to the new interval.
- If the interval is increased, an already-near reproductive turn is **not** postponed.

Changing the law does not retroactively move an appointment that was already imminent.

---

# 🏁 Parent selection

| Rule                            | Default     | Meaning                                         |
| ------------------------------- | ----------- | ----------------------------------------------- |
| `reproduction_criterion`        | `composite` | Parent ranking strategy                         |
| `reproduction_pool_fraction`    | `0.88`      | Top ranked fraction admitted to the parent pool |
| `reproduction_attempts_divisor` | `50`        | Controls reproduction attempts per turn         |
| `reproduction_min_score`        | `0.60`      | Minimum composite score required                |
| `longevity_weight`              | `0.50`      | Longevity contribution                          |
| `exploration_weight`            | `0.30`      | Exploration contribution                        |
| `interaction_weight`            | `0.30`      | Encounter contribution                          |
| `reproduction_weight`           | `0.30`      | Offspring contribution                          |

---

## Selection criterion

`composite` ranks eligible critters by composite score. `longevity` ranks them by age.

The eligibility gates still apply first. Selecting `longevity` does not allow an ancient but otherwise ineligible organism to bypass them.

---

## Reproductive pool

After eligibility and ranking, the top fraction determined by `reproduction_pool_fraction` becomes the parent pool. The two actual parents are chosen from this subset.

Lower values increase selection pressure. Higher values increase genetic participation.

---

## Reproduction attempts

For the lineage that owns the current turn, the number of reproduction attempts is proportional to current population divided by `reproduction_attempts_divisor`.

A lower divisor produces more attempts. A higher divisor produces fewer.

Attempts stop early if reproduction cannot produce children or the lineage reaches its population ceiling.

This knob controls reproductive pressure without changing the two-parent/two-child reproductive contract.

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

The weights are **not probabilities**. They do not need to sum to `1.0`. With every weight at its configured maximum, the theoretical score ceiling is well above `1.0`.

Interpretation is available in [Evolution](evolution.md).

---

# 🎛️ Runtime controls that are not RuntimeRules

Not every live control represents a simulation law:

| Control                    | `RuntimeRules`? |
| -------------------------- | --------------- |
| Simulation speed           | no              |
| Pause / resume             | no              |
| Environmental zones ON/OFF | no              |
| Active save slot           | no              |
| Language                   | no              |
| GIF recording              | no              |
| Inspection criterion       | no              |
| Inspection lineage filter  | no              |

These control execution, presentation, or operator state.

## Simulation speed

The `Simulation speed` control selects a multiplier from a closed set of values. `1x` preserves the historical execution rate of one simulation tick per graphical frame.

The graphical target frame rate remains fixed. Fractional speeds are implemented by accumulated tick credit; slowing the simulation does not slow the UI.

Simulation speed is operator/execution state. It is not `RuntimeRules`, and it is not stored in checkpoints. Recreating the world preserves the operator-selected speed.

The distinction between `zone_hp_effect` (a `RuntimeRules` law) and `zones_active` (a runtime toggle) is deliberate.

---

## Presentation-only calibration

Some values affect the graphical interface but are neither structural config nor `RuntimeRules`. They are not HOT:

```text
Birth Wave visual calibration       → ui_state.py
Birth Wave duration                  → wall-clock seconds
Death-marker TTL                     → simulation ticks
Zone-label font and placement        → rendering.py
UI navigation state                  → ui_state.py
```

In particular, the death-marker retention window is a simulation-history / observation-retention constant. It governs how long a death snapshot remains discoverable in the archive, but it is not an ecological or behavioral law and is not adjustable through `RuntimeRules`.

Birth Wave lifetime uses wall-clock time, not simulation ticks. Pausing the simulation does not freeze an already-visible wave, and changing simulation speed does not shorten or lengthen the perceived animation.

---

# 💾 Checkpoints

Runtime rules belong to simulation state. A successful load restores the complete saved `RuntimeRules` object together with the reproductive scheduler state.

A checkpoint load is:

```text
restore the old universe
```

not:

```text
apply a new runtime intervention
```

For that reason, loading does not reinterpret a saved reproductive cooldown using the HOT interval-change rules. The saved scheduler phase is restored exactly.

> Change a rule and you are experimenting.
>
> Load a checkpoint and you are continuing history.
>
> Confusing the two is how alternate timelines acquire bugs.

See [Persistence](persistence.md) for the checkpoint contract.

---

# 🔒 Configuration invariants

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

Runtime configuration is intentionally powerful. It allows the operator to alter selection pressure without rewriting the organism:

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
