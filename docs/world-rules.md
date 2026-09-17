# 🌍 World Rules

Primordial Soup is governed by a small set of deterministic rules, plus carefully placed randomness.

The critters may behave unpredictably.

The universe should not.

**This is the single authority for the laws of the world.** Other documents may reference these rules, but the definitions live here.

---

## 1. The world

The simulation contains three permanent lineages:

```text
R — Red
G — Green
B — Blue
```

The world uses toroidal geometry. Cross the left edge and you reappear on the right. Cross the top and you return from the bottom.

There are no walls.

Only consequences.

---

## 2. Population

With the packaged baseline, a fresh world starts with 50 critters per lineage. The fresh-world population is NON_HOT configuration. Each lineage has its own population ceiling.

Founders are placed randomly across the world. Every living critter has a stable ID, a lineage, a genome, HP, age, generation, position, neural state, and lifetime counters.

Stable IDs survive array compaction caused by deaths.

A critter is an organism. Not an index.

---

## 3. Movement

Every tick, each living critter evaluates its neural network and chooses one of nine actions:

```text
↖ ↑ ↗
← • →
↙ ↓ ↘
```

The center action means **stay still**.

Movement wraps around world boundaries. Changing cells increases the critter's exploration count. Remaining still does not.

---

## 4. Tick lifecycle

One tick follows this order:

```text
1. perceive
2. decide
3. move
4. rebuild spatial fields
5. compute ecology
6. apply HP, encounters and deaths
7. run reproduction if scheduled
8. rebuild spatial fields
9. collect metrics when due
```

Ecology is computed from a frozen post-movement snapshot. HP effects are accumulated before mortality is resolved.

This prevents lineage order from deciding who lives.

> If changing a `for` loop changes natural selection, you have not implemented ecology.
>
> You have implemented bureaucracy.

Newborns appear after ecological resolution and therefore do **not** participate in the ecology of their own birth tick.

---

# 🩸 Ecology

## 5. Basal metabolism

Every living critter loses a configurable amount of HP every tick.

Default: 1 HP / tick.

Survival therefore requires more than simply avoiding predators forever.

Doing absolutely nothing is a viable strategy only until arithmetic notices.

---

## 6. Predation cycle

Predation follows one canonical cycle:

```text
Red   → Green
Green → Blue
Blue  → Red
```

The reverse direction does not apply.

Predation occurs only when predator and prey occupy the same cell.

For example, `R + G` in the same cell means R may attack G, but G does not attack R.

---

## 7. HP transfer

Predation transfers HP from prey to predator.

The prey loses up to the configured transfer amount; the predator gains the transferred HP.

Damage cannot exceed the prey's HP snapshot. If prey has 37 HP and transfer is 100, prey loses 37 and predator gains 37.

The universe does not permit extracting 100 HP from 37 HP.

It has standards.

---

## 8. Multiple predators

If several predators of the same lineage occupy the prey's cell, the reward is divided between them:

```text
reward per predator = floor(effective_damage / N)
```

The prey still loses the full effective damage. Any remainder is discarded.

One HP disappears into numerical administration.

---

## 9. Multiple prey

A predator can receive HP from multiple eligible prey occupying the same cell.

Example with transfer 100: 1 Red and 2 Green on the same cell means each Green loses 100 HP and Red gains 200.

Other effects (overcrowding, metabolism) are applied independently.

---

## 10. No HP ceiling

There is no maximum HP. Initial HP is 10,000, but that is a starting condition, not a cap.

A successful predator may accumulate substantially more.

Primordial Soup deliberately permits this.

Evolution has enough regulations already.

---

# 👥 Overcrowding

## 11. Same-lineage collisions

Several critters from the same lineage may occupy the same cell. When at least two do so, every member of that lineage in the cell receives overcrowding damage proportional to the count:

```text
damage per critter = F × N
```

Example: three Red critters in one cell, with F=10, means 30 HP damage to each Red.

Overcrowding does not depend on enemies.

Sometimes natural selection is mostly about personal space.

---

# 🤝 Encounters

## 12. Encounter counting

A critter gains **one** encounter for a tick if at least one member of another lineage occupies the same cell.

The count is binary per tick. The number of opponents does not multiply the increment.

Encounter count records exposure to other lineages, not attendance.

---

# 🔺 Triad cells

## 13. Red + Green + Blue

When all three lineages occupy the same cell, all three predator-prey relations would normally be possible:

```text
R → G
G → B
B → R
```

Primordial Soup does **not** apply all three simultaneously. Exactly one eligible predation relation is selected for that cell during the tick; the other two are suppressed.

This is called **triad resolution**. The selected relation is random, using the simulation's persisted NumPy RNG state — so seeded or restored runs remain reproducible.

> Three lineages enter a cell.
>
> Ecology chooses one argument to settle first.

---

# 🪺 Nests

## 14. One nest per lineage

Each lineage owns exactly one nest. Total: three nests.

Nest geometry remains fixed for the lifetime of a run. Centers are part of the persisted world state.

---

## 15. What a nest does

A nest has exactly two ecological roles:

```text
predator refuge
+
birthplace for descendants
```

Nothing more.

A nest does **not** add HP, remove HP, modify metabolism, change neural perception, alter composite score, modify genetics, boost reproduction probability, or prevent same-lineage overcrowding.

A nest is not a buff. It is geography.

---

## 16. Predator protection

A critter inside **its own lineage's nest** cannot be damaged by predation. The protection applies to the prey; it does not make the nest owner offensive.

It does not protect against overcrowding.

Your family can still ruin the neighborhood.

---

## 17. Nest geometry

The functional protection area is a toroidal disk: a point belongs to the nest when its toroidal squared distance from the center is within the configured radius. World wrapping therefore also applies to nest geometry.

---

## 18. Birth location

Founders are distributed randomly across the world.

Descendants are different: every newborn appears inside the discrete spawn disk around the nest of its own lineage. Spawn offsets wrap toroidally. Two siblings may spawn in the same cell.

That is valid. Natural selection may comment on the arrangement shortly afterward.

---

# 🌱 Environmental zones

## 19. Zones

The world contains environmental zones. When zones are active, a critter inside a zone receives the configured HP delta once per tick.

The value is runtime-configurable and may be positive, zero, or negative:

```text
positive → refuge
zero     → neutral geometry
negative → hazard
```

Zones can be toggled on or off without destroying their geometry. Turning them off suppresses their ecological effect; it does not regenerate the world.

The mask and canonical centers are preserved across the toggle.

---

# ☠️ Death

## 20. Mortality

After all ecological HP deltas for the tick have been applied, death is evaluated:

```text
HP <= death_hp_threshold
```

Deaths from different lineages are resolved in the same ecological application phase.

Before any dead critter is removed, a `DeathSnapshot` is captured for **every** death, regardless of whether the individual was being observed:

```text
stable critter ID
lineage
death tick
final agent row
final genome
```

The snapshot enters the recent-death archive. With the packaged baseline, it remains discoverable for 2000 simulation ticks; `DEATH_MARKER_TTL_TICKS` is NON_HOT and checkpoint-relevant. When the dead individual was the one currently being observed, the same snapshot is used by Inspection; there is no separate parallel snapshot.

Dead critters are then removed from agent records, genome pools, and stable-ID arrays in lockstep.

No corpse remains inside the active population arrays.

The memory allocator has no mourning period. The archive keeps a snapshot for a while.

---

# 🧬 Reproduction

## 21. Reproduction is scheduled

Reproduction does not run independently for all lineages every tick. A global scheduler rotates through R → G → B → R → … and only the lineage owning the current turn may reproduce.

The interval is runtime-configurable.

This sequencing is part of persisted simulation state.

---

## 22. Parent eligibility

A critter must pass all four gates before becoming eligible:

```text
age        >= minimum age
HP         <  HP gate
score      >= minimum score
encounters >= minimum encounters
```

All four conditions are conjunctive. Being exceptional in one metric does not compensate for failing another.

Evolution is perfectly capable of inventing bureaucracy too.

---

## 23. Parent ranking

Eligible individuals are ranked using one of two criteria: `composite` or `longevity`.

Only a configurable top fraction enters the reproductive pool. Parents are selected from that pool.

The composite score uses normalized lineage-relative components — longevity, exploration, encounters, and offspring — with runtime-configurable weights.

See [Evolution](evolution.md) for the full selection model.

---

## 24. Two parents, two children

A successful reproductive event uses exactly two parents and produces exactly two children. The two descendant genomes are complementary crossover results, and each child may then mutate independently.

> Reproduction with one parent was considered.
>
> The theological implications exceeded the project's scope.

---

## 25. Generation

The generation of a child is:

```text
max(parent A generation, parent B generation) + 1
```

Founders begin at generation 0. Generation follows ancestry, not simulation time.

---

## 26. Parent reward

After successful reproduction, both parents receive a configurable HP reward, applied once per reproductive event.

It is not multiplied by the number of children.

Apparently reproduction is considered work.

---

# 🧬 Genetics

## 27. Crossover

Available crossover modes:

```text
blocks
uniform
two_points
```

- **blocks** — the genome is divided into contiguous blocks whose parental source is selected independently.
- **uniform** — every gene independently chooses a parent according to a configurable probability.
- **two_points** — two crossover positions define a contiguous exchanged segment.

---

## 28. Mutation

Mutation supports two modes:

```text
two_scales
surgical
```

- **surgical** — a mutating child receives replacement values in a fixed number of randomly selected genes.
- **two_scales** — a mutating child receives either a local or a global mutation. Local affects a smaller portion of the genome with lower Gaussian noise; global affects a larger portion with stronger noise.

Conceptually: local refines, global explores. Both operate directly on inherited neural parameters.

See [Evolution](evolution.md) for the full genetic model.

---

# ⚙️ Runtime rules

## 29. HOT configuration

Many evolutionary pressures can be changed while the simulation is running. These include crossover mode and tuning, mutation mode and tuning, low-HP perception threshold, stay-still bias, mortality threshold, zone HP effect, basal decay, predation transfer, overcrowding factor, reproduction interval, reproductive gates, parent reward, selection criterion, reproductive-pool fraction, reproduction pressure, and composite-score weights.

Changes are validated before replacing the active rule set. Invalid configurations are rejected rather than silently corrected.

The universe may be cruel. It should not be ambiguous.

See [Runtime Configuration](runtime-config.md) for the complete HOT rule set.

---

# 🔒 Core invariants

The current simulation assumes:

```text
exactly 3 canonical lineages
R → G → B → R predation cycle
9 movement actions
4 internal neural inputs
1 nest per lineage
2 parents per reproductive event
2 children per successful pair
stable critter identities
simultaneous ecological resolution
no maximum HP
```

These are structural rules, not incidental defaults.

Changing them means changing the model itself.

---

## Final note

Primordial Soup is intentionally simple at the level of individual rules. The complexity is supposed to emerge from their interaction.

```text
movement
+ neural decisions
+ metabolism
+ predation
+ spatial pressure
+ reproduction
+ inheritance
+ mutation
+ time
```

No single rule is particularly intelligent. That is the point.

> They are born.
> They look around.
> They make decisions.
> They collide with other creatures.
> They gain and lose HP.
> Some survive long enough to reproduce.
> Their descendants inherit modified neural networks.
> Eventually they all die.
>
> The interesting part is everything that happens in between.
