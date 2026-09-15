# 🌍 World Rules

Primordial Soup is governed by a small set of deterministic rules, plus carefully placed randomness.

The critters may behave unpredictably.

The universe should not.

---

## 1. The world

The simulation contains three permanent lineages:

```text
R — Red
G — Green
B — Blue
```

The world uses toroidal geometry.

Cross the left edge and you reappear on the right.

Cross the top and you return from the bottom.

There are no walls.

Only consequences.

---

## 2. Population

A new world starts with:

```text
50 Red
50 Green
50 Blue
```

Each lineage has its own population ceiling.

Founders are placed randomly across the world.

Every living critter has:

* a stable ID;
* a lineage;
* a genome;
* HP;
* age;
* generation;
* position;
* neural state;
* encounter count;
* offspring count;
* exploration count;
* composite score.

Stable IDs survive array compaction caused by deaths.

A critter is an organism.

Not an index.

---

## 3. Movement

Every tick, each living critter evaluates its neural network and chooses one of nine actions:

```text
↖ ↑ ↗
← • →
↙ ↓ ↘
```

The center action means **stay still**.

Movement wraps around world boundaries.

Changing cells increases the critter's exploration count.

Remaining still does not.

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

Ecology is computed from a frozen post-movement snapshot.

HP effects are accumulated before mortality is resolved.

This prevents lineage order from deciding who lives.

> If changing a `for` loop changes natural selection, you have not implemented ecology.
>
> You have implemented bureaucracy.

Newborns appear after ecological resolution and therefore do **not** participate in the ecology of their own birth tick.

---

# 🩸 Ecology

## 5. Basal metabolism

Every living critter loses a configurable amount of HP every tick:

```text
HP -= base_decay_per_tick
```

Default:

```text
base decay = 1 HP / tick
```

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

For example:

```text
R + G in the same cell
```

means:

```text
R may attack G
G does not attack R
```

Predation occurs only when predator and prey occupy the same cell.

---

## 7. HP transfer

Predation transfers HP from prey to predator.

With configured transfer `X`:

```text
prey loses up to X HP
predator gains the transferred HP
```

Damage cannot exceed the prey's HP snapshot.

Therefore:

```text
prey HP = 37
predation transfer = 100
```

produces:

```text
prey:     -37 HP
predator: +37 HP
```

The universe does not permit extracting 100 HP from 37 HP.

It has standards.

---

## 8. Multiple predators

If several predators of the same lineage occupy the prey's cell, the reward is divided between them.

For effective damage `D` and `N` predators:

```text
reward per predator = floor(D / N)
```

The prey still loses the full effective damage.

Any remainder is discarded.

Example:

```text
3 Red predators
1 Green prey
transfer = 100
```

Each Red receives:

```text
floor(100 / 3) = 33 HP
```

Green loses:

```text
100 HP
```

One HP disappears into numerical administration.

---

## 9. Multiple prey

A predator can receive HP from multiple eligible prey occupying the same cell.

Example:

```text
1 Red
2 Green
```

with transfer `100`:

```text
each Green: -100 HP
Red:        +200 HP
```

Other ecological effects, such as overcrowding and metabolism, are applied independently.

---

## 10. No HP ceiling

There is no maximum HP.

Initial HP is:

```text
10,000
```

but it is an initial condition, not a cap.

A successful predator may accumulate substantially more.

Primordial Soup deliberately permits this.

Evolution has enough regulations already.

---

# 👥 Overcrowding

## 11. Same-lineage collisions

Several critters from the same lineage may occupy the same cell.

When at least two do so, every member of that lineage in the cell receives overcrowding damage.

For:

```text
N = number of same-lineage critters in the cell
F = overcrowding factor
```

damage per critter is:

```text
F × N
```

Default:

```text
F = 10
```

Example:

```text
3 Red critters in one cell
```

causes:

```text
30 HP damage to each Red
```

Overcrowding does not depend on enemies.

Sometimes natural selection is mostly about personal space.

---

# 🤝 Encounters

## 12. Encounter counting

A critter gains one encounter for a tick if at least one member of another lineage occupies the same cell.

The count is binary per tick:

```text
no other lineage present → +0
one or more present      → +1
```

Examples:

```text
R + G       → R +1, G +1

R + G + G   → R +1, each G +1

R + G + B   → every individual +1
```

The number of opponents does not multiply the encounter increment.

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

Primordial Soup does **not** apply all three simultaneously.

Instead, exactly one eligible predation relation is selected for that cell during the tick.

The other two are suppressed.

This is called **triad resolution**.

The selected relation is random, using the simulation's persisted NumPy RNG state.

Therefore seeded or restored runs remain reproducible.

> Three lineages enter a cell.
>
> Ecology chooses one argument to settle first.

---

# 🪺 Nests

## 14. One nest per lineage

Each lineage owns exactly one nest:

```text
R → 1 nest
G → 1 nest
B → 1 nest
```

Total:

```text
3 nests
```

Nest geometry remains fixed for the lifetime of a run.

The centers are part of the persisted world state.

---

## 15. What a nest does

A nest has exactly two ecological roles:

```text
predator refuge
+
birthplace for descendants
```

Nothing more.

A nest does **not**:

* add HP;
* remove HP;
* modify metabolism;
* change neural perception;
* alter composite score;
* modify genetics;
* boost reproduction probability;
* prevent same-lineage overcrowding.

A nest is not a buff.

It is geography.

---

## 16. Predator protection

A critter inside **its own lineage's nest** cannot be damaged by predation.

Example:

```text
Green inside Green nest
Red occupies same cell
```

Result:

```text
R → G predation is blocked
```

The protection applies to the prey.

It does not make the nest owner offensive.

And it does not protect against overcrowding.

Your family can still ruin the neighborhood.

---

## 17. Nest radius

The functional protection area is a toroidal disk:

```text
NEST_RADIUS = 20
```

A point belongs to the nest when its toroidal squared distance from the center is:

```text
distance² <= radius²
```

World wrapping therefore also applies to nest geometry.

---

## 18. Birth location

Founders are distributed randomly.

Descendants are different.

Every newborn appears inside the spawn region around the nest of its own lineage:

```text
NEST_SPAWN_RADIUS = 1
```

Two siblings may spawn in the same cell.

That is valid.

Natural selection may comment on the arrangement shortly afterward.

---

# 🌱 Environmental zones

## 19. Zones

The world contains environmental zones.

Default geometry:

```text
8 zones
radius = 27
```

When zones are active, a critter inside a zone receives the configured HP delta once per tick.

Default:

```text
+5 HP / tick
```

The value is runtime-configurable and may also be negative.

Zones can be toggled on or off without destroying their geometry.

Turning them off suppresses their ecological effect.

It does not regenerate the world.

---

# ☠️ Death

## 20. Mortality

After all ecological HP deltas for the tick have been applied, death is evaluated.

A critter dies when:

```text
HP <= death_hp_threshold
```

Default threshold:

```text
0
```

Deaths from different lineages are resolved in the same ecological application phase.

Dead critters are then removed from:

```text
agent records
genome pools
stable-ID arrays
```

in lockstep.

No corpse remains inside the active population arrays.

The memory allocator has no mourning period.

---

# 🧬 Reproduction

## 21. Reproduction is scheduled

Reproduction does not run independently for all lineages every tick.

A global scheduler rotates through:

```text
R → G → B → R → ...
```

Only the lineage owning the current reproductive turn may reproduce.

The interval is runtime-configurable.

Default:

```text
150 ticks
```

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

All four conditions are conjunctive.

Being exceptional in one metric does not compensate for failing another.

Evolution is perfectly capable of inventing bureaucracy too.

---

## 23. Parent ranking

Eligible individuals are ranked using one of two criteria:

```text
composite
longevity
```

Only a configurable top fraction enters the reproductive pool.

Parents are selected from that pool.

The composite score uses normalized lineage-relative components:

```text
longevity
exploration
encounters
offspring
```

with runtime-configurable weights.

---

## 24. Two parents, two children

A successful reproductive event uses:

```text
2 parents
```

and produces:

```text
2 children
```

The two descendant genomes are complementary crossover results.

Each child may then mutate independently.

> Reproduction with one parent was considered.
>
> The theological implications exceeded the project's scope.

---

## 25. Generation

The generation of a child is:

```text
max(parent A generation, parent B generation) + 1
```

Founders begin at the initial generation.

Generation therefore follows ancestry, not simulation time.

---

## 26. Parent reward

After successful reproduction, both parents receive a configurable HP reward.

Default:

```text
+50 HP per parent
```

The reward is applied once per reproductive event.

It is not multiplied by the number of children.

Apparently reproduction is considered work.

---

# 🧬 Genetics

## 27. Crossover

Available crossover modes are:

```text
blocks
uniform
two_points
```

### Blocks

The genome is divided into contiguous blocks whose parental source is selected independently.

### Uniform

Every gene independently chooses a parent according to a configurable probability.

### Two points

Two crossover positions define a contiguous exchanged segment.

---

## 28. Mutation

Mutation supports two modes:

```text
two_scales
surgical
```

### Surgical

A mutating child receives replacement values in a fixed number of randomly selected genes.

### Two scales

A mutating child receives either:

```text
local mutation
```

or:

```text
global mutation
```

Local mutation affects a smaller portion of the genome with lower Gaussian noise.

Global mutation affects a larger portion with stronger noise.

Conceptually:

```text
local  → refine
global → explore
```

Both operate directly on inherited neural parameters.

---

# ⚙️ Runtime rules

## 29. HOT configuration

Many evolutionary pressures can be changed while the simulation is running.

These include:

* crossover mode and tuning;
* mutation mode and tuning;
* low-HP perception threshold;
* stay-still bias;
* mortality threshold;
* zone HP effect;
* basal decay;
* predation transfer;
* overcrowding factor;
* reproduction interval;
* reproductive gates;
* parent reward;
* selection criterion;
* reproductive-pool fraction;
* reproduction pressure;
* composite-score weights.

Changes are validated before replacing the active rule set.

Invalid configurations are rejected rather than silently corrected.

The universe may be cruel.

It should not be ambiguous.

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

Primordial Soup is intentionally simple at the level of individual rules.

The complexity is supposed to emerge from their interaction.

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

No single rule is particularly intelligent.

That is the point.

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
