# 🧬 Evolution

Primordial Soup does not train its critters. It replaces them.

Each individual carries a neural-network genome. That genome determines how its brain processes perception and produces movement. Individuals live under ecological pressure. Some survive. Some reproduce. Their descendants inherit recombined and mutated genomes.

Over many generations:

```text
genetic variation
       ↓
different neural networks
       ↓
different behavior
       ↓
different ecological outcomes
       ↓
different reproductive success
       ↓
different genes in future generations
```

That feedback loop is the evolutionary engine of Primordial Soup.

No gradient descent required.

Death handles optimization.

**This is the single authority for selection, reproduction, crossover, and mutation.** The ecological pressures that feed into selection are defined in [World Rules](world-rules.md).

Whenever this document says **default** or **current default**, it refers to the packaged declarative baseline. Active HOT values may differ in a running world; see [Runtime Configuration](runtime-config.md).

---

# The evolutionary cycle

At the population level:

```text
random founders
      ↓
   behavior
      ↓
ecological pressure
      ↓
survival / death
      ↓
reproductive eligibility
      ↓
selection
      ↓
parent pairing
      ↓
crossover
      ↓
mutation
      ↓
offspring
      ↓
new generation
      ↺
```

The simulator separates five questions that are easy to accidentally merge:

```text
Did you survive?
Are you eligible to reproduce?
Are you among the better eligible individuals?
Were you actually selected as a parent?
Did your descendants survive?
```

Those are five different filters.

Being alive is merely the first interview.

---

## What is inherited

A critter's genome encodes the numerical parameters of its neural controller: weights, biases, and recurrent weights. Conceptually:

```text
GENOME → neural controller → movement behavior → ecological consequences
```

The genome does **not** directly contain instructions such as "avoid red" or "seek green". Those behaviors, if they appear, must arise from the numerical network dynamics.

---

## What is not inherited

A newborn does not inherit its parents' age, HP history, position, encounters, offspring count, exploration history, or short-term recurrent neural state.

```text
genome        → inherited
neural memory → not inherited
```

The child may inherit a brain capable of producing a useful behavior. It does not inherit the parent's experiences.

No ancestral memories.

No prenatal knowledge of where the dangerous blue cluster lives.

---

## Founders

A fresh world starts with randomly generated genomes. Generation-zero critters are founders.

At this point there has been no selection. Their behavior is whatever their random neural controllers happen to produce.

Some founders are merely bad. Others are impressively bad.

Evolution requires raw material.

---

## Generation

Founders begin at generation 0. When two parents reproduce:

```text
child generation = max(parent A generation, parent B generation) + 1
```

Generation therefore represents **genealogical depth**, not age.

A generation-30 critter may be young. A generation-2 critter may be ancient.

Never confuse age with generation. One counts lived ticks. The other counts ancestry.

---

# 🏆 The composite score

The default selection model uses a **composite score** combining four aspects of an individual's life:

```text
longevity
exploration
interactions
reproductive success
```

Each component is **normalized within the individual's own lineage**, so a small but internally successful lineage is not numerically erased by a currently dominant one.

The composite score is not a percentage. The weights do not sum to 1.0, and the theoretical maximum is defined by the current weight values.

The score is a selection instrument. Not a school grade.

---

## Why not normalize globally?

If every component were scaled against the strongest individual across the entire ecosystem, a small but internally successful lineage could become numerically insignificant.

Per-lineage normalization preserves meaningful selection inside each lineage.

Evolutionary competition still occurs between lineages ecologically. Parent ranking happens among relatives.

Family politics remain local.

---

## Why several dimensions?

Suppose selection used only longevity. The system might favor individuals that survive by avoiding almost everything.

Suppose it used only encounters. It might favor critters that enthusiastically throw themselves into ecological traffic.

Suppose it used only offspring. Early reproductive accidents could dominate later selection.

The composite score attempts to balance several forms of success:

```text
stay alive
+
move through the world
+
participate in ecology
+
reproduce
```

Whether those weights produce desirable evolutionary pressure is itself an experimental question. Nothing about the current weights is a law of nature. It is a law of this particular universe.

---

# 🚧 Reproductive gates

A high score alone is not enough. Before an individual can enter parent ranking, it must pass **four gates simultaneously**:

```text
age        >= minimum age
HP         <  HP gate
score      >= minimum score
encounters >= minimum encounters
```

Fail one gate, and the critter is not eligible. There is no compensating with exceptional performance elsewhere.

The exact numeric thresholds are HOT rules; see [Runtime Configuration](runtime-config.md).

---

## Gate 1 — age

Prevents newborns and juveniles from immediately reproducing. Without an age gate, `birth → reproduce → birth → reproduce` could make genealogical turnover much faster than ecological evaluation.

The age threshold forces individuals to survive long enough for their behavior to have consequences.

---

## Gate 2 — HP

Requires the critter's HP to be **strictly below** the gate value. A critter at exactly the gate value does not pass.

Why have an upper HP gate at all?

Because reproduction is designed to occur after the individual has actually experienced some cost of living. A pristine newborn at full health should not become reproductively eligible merely because some other metrics happen to look favorable.

The individual must have participated in the ecology enough to leave the untouched initial state.

In Primordial Soup, romance requires minor wear and tear.

---

## Gate 3 — composite score

Ensures that mere age and damage are not sufficient. An individual can survive for a long time and still fail if its overall measured life history is weak relative to its lineage.

---

## Gate 4 — encounters

Requires a minimum amount of inter-lineage contact. This prevents extremely isolated individuals from reproducing without participating meaningfully in ecology.

The current model therefore rewards not merely *avoid everything forever*, but some minimum amount of ecological contact.

---

# 👑 The reproductive pool

Passing the gates does not guarantee parenthood.

Suppose a lineage contains 100 living critters and 30 pass all four gates. Those 30 are only the **eligible set**. They are then ranked.

With the default `composite` criterion, higher scores rank first:

```text
living population
       ↓
four eligibility gates
       ↓
eligible population
       ↓
rank by criterion
       ↓
reproductive pool (top fraction)
```

Only the top fraction of eligible individuals enters the parent pool.

The implementation guarantees a pool of at least two whenever at least two individuals are eligible.

That is useful because sexual reproduction with one parent would require considerably more theological documentation.

---

# 🎲 Parent selection

Two different parents are randomly drawn from the pool, **without replacement**, so an individual cannot mate with itself in the same parent pair.

This creates a combination of:

```text
deterministic pressure
+
stochastic pairing
```

The ranking determines **who is allowed into the privileged pool**. Randomness determines which two members of that pool reproduce in a particular event.

This prevents parenthood from becoming a deterministic monopoly of exactly one highest-scoring pair.

---

# 🔄 Reproduction is turn-based

Reproduction is globally scheduled. Only one lineage receives a reproductive opportunity at a time, rotating:

```text
R → G → B → R → ...
```

There is one global reproductive turn state, not three independent lineage clocks. A fresh world starts with turn = R and cooldown = 0, so the first lineage can receive a turn immediately. After a turn, the global cooldown is reset.

Meanwhile all lineages continue normal life: perceive, move, interact, gain or lose HP, age, die. Only reproduction is gated by the turn.

Green does not stop living merely because Red currently has the maternity ward.

---

## Why rotate reproductive turns?

If every lineage reproduced continuously whenever it had eligible parents, population growth could become extremely aggressive.

Turn-based reproduction provides temporal structure, bounded reproductive opportunities, more gradual population growth, symmetry between lineages, and easier experimental interpretation.

It also separates **ecological time** from **reproductive opportunity**.

Every tick matters ecologically. Only selected ticks matter reproductively.

---

## Reproductive attempts

Receiving a lineage turn does not mean *fill every available population slot immediately*. The number of reproduction attempts is bounded, proportional to current lineage population.

Each successful attempt produces the configured offspring pair.

This makes population growth gradual across reproductive turns rather than explosive in a single event.

Evolution gets a throttle.

---

## Population ceiling

Each lineage has a maximum living population. Reproduction stops before a successful birth would exceed that ceiling.

The ceiling does not kill existing critters. It prevents additional births. Population can still fall naturally through death and later create room for reproduction again.

Conceptually:

```text
population < ceiling → reproduction may add individuals
population near ceiling → births blocked
deaths → capacity becomes available again
```

Finite memory meets finite ecology.

---

## A reproductive attempt can fail

A lineage may receive its turn and still produce no children. Reasons include: fewer than two eligible individuals, reproductive pool too small, population ceiling reached, or another reproductive prerequisite failing.

Therefore:

```text
reproductive turn ≠ guaranteed birth
```

A turn is an opportunity. Not a reservation.

---

# 👨‍👩‍👧 Successful reproduction

When a pair successfully reproduces:

```text
parent A + parent B → crossover → mutation → 2 newborns
```

Under the current default, `OFFSPRING_PER_PAIR = 2`. The two children receive complementary combinations of parental genes before mutation.

---

## Parent life-history update

Each successful reproductive event increments the reproduction counter of each selected parent by 1.

This is worth reading carefully. The current counter behaves as a measure of **successful reproductive events per parent**, even though the event currently creates two children. It is the value used by the reproductive-success component of composite score.

So the parent reproduction counter should not automatically be interpreted as a literal genealogical count of every child produced when `OFFSPRING_PER_PAIR > 1`.

---

## Reproduction reward

Successful reproduction also gives each parent a small HP reward, applied once per parent per event. It is not multiplied by the number of children.

This introduces another feedback:

```text
successful reproduction
       ↓
small survival benefit
       ↓
potentially more future reproductive opportunities
```

The reward is intentionally modest relative to initial HP.

Reproduction helps. It does not confer immortality.

In graphical mode, the same successful event also triggers a brief lineage-colored wave from the lineage's nest. The wave is presentation only: it does not add HP, does not count toward the reward, and does not influence selection.

---

# 🧬 Crossover

Before mutation, parental genomes are recombined.

Primordial Soup currently supports three crossover strategies: `blocks`, `uniform`, and `two_points`. The active default is `blocks`.

---

## Blocks crossover

The genome is divided into contiguous blocks. For each block, a random mask chooses which parent contributes that block to one child. The complementary child receives the opposite source.

Conceptually:

```text
Parent A: AAAA AAAA AAAA AAAA
Parent B: BBBB BBBB BBBB BBBB

random block mask:  A    B    B    A

Child 1: AAAA BBBB BBBB AAAA
Child 2: BBBB AAAA AAAA BBBB
```

The real genome is considerably larger than sixteen characters.

Fortunately Markdown has limits.

Block crossover preserves contiguous groups of neural parameters more readily than independent per-gene mixing. Whether those contiguous numerical regions correspond to useful inherited structures is an empirical question.

---

## Uniform crossover

Uniform crossover treats each gene independently. Each location independently chooses between the two parents with equal probability.

The complementary child receives the opposite choice at each position.

Uniform crossover mixes parental genomes much more finely than block crossover. Excellent for genetic diversity. Potentially terrible for preserving useful groups of coordinated weights.

Experiments exist to settle arguments like this.

---

## Two-point crossover

Two-point crossover selects two random cut positions. The region between them is taken from one parent while the complementary child receives the opposite pattern.

Conceptually:

```text
             cut 1        cut 2
               │            │
Parent A: AAAAA|AAAAAAAAAAAA|AAAAA
Parent B: BBBBB|BBBBBBBBBBBB|BBBBB

Child 1: BBBBB|AAAAAAAAAAAA|BBBBB
Child 2: AAAAA|BBBBBBBBBBBB|AAAAA
```

This preserves large contiguous regions. It resembles a more traditional genetic-algorithm crossover.

---

## Complementary children

An important property of the crossover implementation is complementarity. For a given crossover mask:

```text
where child 1 takes A → child 2 takes B
where child 1 takes B → child 2 takes A
```

Before mutation, the pair therefore contains complementary parental contributions. Mutation can subsequently break that symmetry.

Evolution appreciates siblings developing their own personalities.

---

# ☢️ Mutation

Crossover rearranges existing genetic material. Mutation creates new variation.

The active mutation system is `two_scales`. A second mode, `surgical`, also exists but is not the current default.

---

## Mutation probability

The runtime mutation rate represents the probability that an offspring will undergo mutation.

So for each generated child:

```text
random draw
   ↓
mutation?
├── no  → crossover genome survives unchanged
└── yes → mutation algorithm runs
```

This controls **how often** children mutate. It does not by itself determine how large each mutation is.

The rate is HOT. See [Runtime Configuration](runtime-config.md).

---

## Two-scale mutation

When a child is selected for mutation, the active algorithm chooses between **local** mutation and **global** mutation:

```text
local  → small refinement
global → larger exploration
```

Most mutations are conservative. A minority are deliberately more disruptive.

Conceptually:

```text
local:  few genes, small perturbations
global: more genes, larger perturbations
```

At least that is the intention. Evolution is under no contractual obligation to cooperate.

---

## Gaussian mutation

Two-scale mutation uses additive Gaussian noise. That matters because most sampled changes are near zero, while large changes are progressively rarer.

This is different from replacing every mutated gene with a completely unrelated random value. Local adaptation can therefore preserve much of the existing structure.

After Gaussian mutation, values are clamped to the legal gene range to prevent repeated mutation from allowing weights to drift without bound.

The universe has railings.

---

## Gene sampling without replacement

Within a single two-scale mutation event, the affected genes are selected **without replacement**. A gene is not selected twice within the same mutation event.

If the algorithm decides to affect 500 genes, then it affects 500 distinct positions. Not 437 unique positions plus 63 accidental repeats.

This makes the configured mutation fraction meaningful.

---

## Surgical mutation

In `surgical` mode, mutant children have a configured exact number of gene positions selected. Those positions are replaced with newly sampled values from the legal gene range.

So the semantics differ significantly:

```text
two_scales: existing value + Gaussian perturbation
surgical:   existing value → replaced
```

Surgical mutation is more discrete. Two-scale mutation is the current default because it provides separate mechanisms for refinement and broader exploration.

---

# 👶 Newborn state

A successfully created child begins with:

```text
new stable ID
full initial HP
spawn position inside the lineage's nest area
new generation
inherited / recombined / mutated genome
age = 0
encounters = 0
offspring = 0
exploration = 0
composite score = 0 initially
recurrent memory = 0
```

The child enters the same lineage as its parents. Lineages do not mutate into other colors. A green family cannot unexpectedly give birth to blue because crossover got creative.

---

## Newborn position is in the lineage nest

Children are not born beside their parents. Their initial coordinates are sampled from the spawn disk around their lineage's nest center, wrapped toroidally.

This design intentionally separates **genetic inheritance** from **spatial inheritance**.

A useful genome therefore cannot rely on offspring being placed in the same local environment that made its parents successful. Descendants from the same lineage return to the lineage nest, not to wherever the parents happened to succeed.

A strategy that only works on one lucky pixel has a difficult childhood.

---

# ⚖️ Interpreting evolution

## Population growth is not fitness

Suppose Red grows rapidly. That does not necessarily prove Red has evolved a superior neural policy.

Population can be influenced by current ecological composition, reproductive-turn timing, available population capacity, random parent pairing, spatial placement of newborns, mutation history, environmental zones, and stochastic events.

Likewise, temporary population decline does not prove evolutionary failure.

Evolutionary claims should be based on repeated measurements. Not merely *Red looked pretty strong around tick 8,000*.

---

## Composite score is not evolution itself

The composite score is part of the **selection mechanism**. That means something subtle:

```text
we define what the score rewards
↓
the score influences who reproduces
↓
evolution may optimize toward that reward
```

If the weights heavily reward exploration, the population may evolve toward exploratory behavior. If longevity dominates, behavior that supports survival may receive more reproductive representation.

The score is therefore not an objective observer. It is part of the environment.

This is essential when interpreting experimental results.

---

## Mutation vs selection

Mutation does not improve genomes. Mutation creates variation. Selection filters consequences.

```text
mutation  → variation
selection → differential inheritance
```

A mutation may be beneficial, neutral, or harmful. The simulator does not label it at birth. Its consequences emerge through the critter's behavior and ecological history.

---

## Crossover vs mutation

They also solve different evolutionary problems:

```text
crossover → recombines what already exists
mutation  → introduces new numerical variation
```

Without crossover, successful genetic structures cannot be recombined between parents in the same way. Without mutation, evolution eventually depends only on combinations of the initial random genetic material.

Together they provide the search mechanism.

---

## Exploration vs exploitation

The current mutation system embodies a classic optimization tradeoff:

```text
EXPLOITATION    local mutation: small changes, refine existing structure
EXPLORATION     global mutation: large changes, search distant alternatives
```

Too much exploitation and the population may converge around mediocre solutions. Too much exploration and useful inherited structure may be repeatedly destroyed.

The right balance depends on the landscape created by the simulation. And because the ecological landscape changes as populations change, the target itself can move.

Evolutionary optimization is inconvenient like that.

---

## Reproduction changes survival too

Because successful parents receive an HP bonus, reproductive success has both a genealogical effect and an immediate survival effect.

So reproduction participates in a feedback loop:

```text
good life history
       ↓
eligible
       ↓
selected
       ↓
reproduce
       ↓
offspring counter rises
       +
small HP reward
       ↓
composite score / survival may improve
       ↓
possible future reproduction
```

Selection systems rarely remain politely linear.

---

# ☠️ Death and evolution

Every death in the simulation is captured before the population arrays are compacted. The capture is not restricted to currently observed individuals.

```text
every death → DeathSnapshot → recent_deaths (chronological archive)
```

The snapshot preserves the critter's stable ID, lineage, death tick, final agent row, and final genome. It remains discoverable for a bounded retention window and is part of the current checkpoint contract; persistent recent-death history was introduced in v23 and remains present in current v25.

If the dead individual was the one currently being observed, the same snapshot is installed on Inspection. There is no second snapshot for the observed case: the archive is the source of truth, and Inspection references the appropriate record.

This is orthogonal to evolution. It does not change which genomes survive, which lineages reproduce, or how selection ranks parents. It only guarantees that every organism leaves a final record of its state before its row is removed from the active population.

See [World Rules](world-rules.md) §20 for the mortality rule itself, and [Persistence](persistence.md) for the archive contract.

---

# 🪦 Extinction

If a lineage reaches population zero, it cannot reproduce. There are no parents, no genomes, no newborns.

The reproductive scheduler may later reach that lineage's turn, but there is nobody left to use it. The simulator does not recreate extinct founders automatically.

Extinction is therefore absorbing for that lineage unless the operator starts or loads another world.

Evolution requires something alive to evolve.

---

# 🧪 What to experiment with

Each of the following changes one evolutionary pressure without touching the others:

- **Mutation probability** — does a low rate behave differently from a high one? Watch maximum generation, population stability, score, and extinction frequency.
- **Selection weights** — increase longevity pressure; do behaviors become more conservative? Increase exploration pressure; do populations move more, and at what cost?
- **Reproductive age** — lower the minimum age; does faster generational turnover accelerate adaptation, or merely amplify noise?
- **Encounter gate** — raise it; does this increase ecological participation, or simply eliminate too many otherwise successful parents?
- **Reproductive pool size** — stronger elitism may improve measured fitness faster, or collapse genetic diversity.
- **Crossover strategy** — compare `blocks`, `uniform`, and `two_points` using the same seeds and protocol; which preserves useful neural structures better?
- **Global mutation probability** — increase the chance that mutations use the global scale; does broader genetic exploration help populations escape plateaus?

Every one of these is HOT. See [Runtime Configuration](runtime-config.md).

---

## What counts as evidence

One successful lineage in one run is weak evidence. Primordial Soup is stochastic. Randomness enters through founder genomes, initial positions, environmental zones, parent selection, crossover, mutation, and newborn positions.

A stronger experimental pattern is:

```text
same configuration
+
multiple seeds
+
same run duration
+
same measured outputs
```

Then compare distributions. Not anecdotes.

The blue lineage does not become scientifically significant merely because you became emotionally invested in it.

See [Experiments](experiments.md).

---

# The evolutionary pipeline

Putting the reproductive process together:

```text
LIVING LINEAGE
      │
      ▼
update life-history metrics
      │
      ▼
compute composite scores
      │
      ▼
is this the lineage's reproductive turn?
      │
      ├──────── no ───────→ continue living
      │
     yes
      │
      ▼
apply four eligibility gates
      │
      ▼
at least two eligible?
      │
      ├──────── no ───────→ no birth
      │
     yes
      │
      ▼
rank eligible individuals
      │
      ▼
take top reproductive fraction
      │
      ▼
randomly select two parents
      │
      ▼
crossover genomes
      │
      ▼
mutation lottery
      │
      ▼
create two newborns
      │
      ├── new IDs
      ├── random positions in lineage nest
      ├── full HP
      ├── new generation
      └── memory = 0
      │
      ▼
reward parents
      │
      ▼
future ticks decide whether any of this was useful
```

That last step is important.

Reproduction creates descendants. It does not certify them.

---

## In one sentence

Primordial Soup evolves neural controllers by letting ecological life histories determine reproductive eligibility, ranking eligible individuals within each lineage, recombining selected parental genomes, introducing mutations at local and global scales, and then returning the descendants to the same hostile universe to see what happens.

No fitness oracle. No training labels. Just inheritance, pressure, randomness and consequences.

---

# Related documentation

→ [World Rules](world-rules.md) — the ecological rules that produce survival pressure
→ [Critters and Brains](critters-and-brains.md) — the organism and its genome
→ [Runtime Configuration](runtime-config.md) — every HOT selection and mutation constant
→ [Inspection](ui.md) — observing selected individuals and generations
→ [Experiments](experiments.md) — controlled evolutionary comparisons
→ [Persistence](persistence.md) — checkpoints, RNG state, and deterministic continuation
