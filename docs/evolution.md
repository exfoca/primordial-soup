# 🧬 Evolution

Primordial Soup does not train its critters.

It replaces them.

Each individual carries a neural-network genome. That genome determines how its brain processes perception and produces movement.

Individuals live under ecological pressure.

Some survive.

Some reproduce.

Their descendants inherit recombined and mutated genomes.

Over many generations:

```text id="8w9rgk"
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

---

# The evolutionary cycle

At the population level:

```text id="6kp0bm"
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

The simulator therefore separates several questions that are easy to accidentally merge:

```text id="3xo1h9"
Did you survive?

Are you eligible to reproduce?

Are you among the better eligible individuals?

Were you actually selected as a parent?

Did your descendants survive?
```

Those are five different filters.

Being alive is merely the first interview.

---

# 🧬 What is inherited?

A critter's genome encodes the numerical parameters of its neural controller.

That includes:

* neural-network weights;
* neural biases;
* recurrent weights.

The genome therefore affects how sensory information becomes movement.

Conceptually:

```text id="jsl4ht"
GENOME
   ↓
neural controller
   ↓
movement behavior
   ↓
ecological consequences
```

The genome does **not** directly contain instructions such as:

```text id="igq4c1"
avoid red
seek green
enter safe zone
move north
```

Those behaviors, if they appear, must arise from the numerical network dynamics.

---

# What is not inherited?

A newborn does not inherit its parents':

* age;
* HP history;
* position;
* encounters;
* offspring count;
* exploration history;
* short-term recurrent neural state.

A child begins with a new life history.

In particular:

```text id="y44dfp"
genome        → inherited
neural memory → not inherited
```

The child may inherit a brain capable of producing a useful behavior.

It does not inherit the parent's experiences.

No ancestral memories.

No prenatal knowledge of where the dangerous blue cluster lives.

---

# 🐣 Founders

A fresh world starts with randomly generated genomes.

Each lineage begins with:

```text id="07us8n"
50 critters
```

under the current default configuration.

Their genome values are sampled within the configured gene range.

At this point there has been no selection.

Generation-zero critters are founders.

Their behavior is whatever their random neural controllers happen to produce.

Some founders are merely bad.

Others are impressively bad.

Evolution requires raw material.

---

# 🧓 Generation

Founders begin at:

```text id="aqzizj"
generation = 0
```

When two parents reproduce:

```text id="g9y8na"
child generation
=
max(parent A generation, parent B generation) + 1
```

For example:

```text id="5lbfqt"
parent A = generation 7
parent B = generation 10

child = generation 11
```

Generation therefore represents **genealogical depth**, not age.

A generation-30 critter may be young.

A generation-2 critter may be ancient.

Never confuse:

```text id="k08608"
age
```

with:

```text id="agq3es"
generation
```

One counts lived ticks.

The other counts ancestry.

---

# 🏆 Selection begins with measurement

The current default selection model uses a **composite score**.

It combines four aspects of an individual's life:

```text id="ffg8ko"
longevity
exploration
interactions
reproductive success
```

The current weights are:

```text id="f3guwi"
longevity     = 0.5
exploration   = 0.3
interactions  = 0.3
reproduction = 0.3
```

The formula is conceptually:

```text id="e3z2zy"
score =
    0.5 × normalized longevity
  + 0.3 × normalized exploration
  + 0.3 × normalized encounters
  + 0.3 × normalized reproduction
```

---

# Normalization happens within each lineage

Each component is divided by the maximum value currently found in that same lineage.

For longevity:

```text id="hlxpae"
critter age
──────────────
oldest age in lineage
```

For exploration:

```text id="be1rl6"
critter exploration
─────────────────────
maximum in lineage
```

The same principle applies to encounters and reproductive success.

This means the score measures an individual **relative to its lineage peers**.

---

## Why not normalize globally?

Imagine:

```text id="k5qf3x"
R population = 250
G population = 40
```

If every component were scaled against the strongest individual across the entire ecosystem, a small but internally successful lineage could become numerically insignificant.

Per-lineage normalization preserves meaningful selection inside each lineage.

Evolutionary competition still occurs between lineages ecologically.

Parent ranking happens among relatives.

Family politics remain local.

---

# The score is not a percentage

The weights currently sum to:

```text id="wao0df"
0.5 + 0.3 + 0.3 + 0.3 = 1.4
```

So the composite score is **not naturally bounded to 1.0**.

A score such as:

```text id="pe0mpb"
0.8
```

does not mean:

> 80% fitness.

And:

```text id="qn2pv2"
1.1
```

is not an error.

The theoretical maximum under the current weights is:

```text id="gfwrgu"
1.4
```

when an individual simultaneously matches the lineage maximum in all four components.

The score is a selection instrument.

Not a school grade.

---

# Why several dimensions?

Suppose selection used only longevity.

The system might favor individuals that survive by avoiding almost everything.

Suppose it used only encounters.

It might favor critters that enthusiastically throw themselves into ecological traffic.

Suppose it used only offspring.

Early reproductive accidents could dominate later selection.

The composite score attempts to balance several forms of success:

```text id="2rsffd"
stay alive
+
move through the world
+
participate in ecology
+
reproduce
```

Whether those weights produce desirable evolutionary pressure is itself an experimental question.

Nothing about `0.5 / 0.3 / 0.3 / 0.3` is a law of nature.

It is a law of this particular universe.

---

# 🚧 Four reproductive gates

A high score alone is not enough.

Before an individual can even enter parent ranking, it must pass **four gates simultaneously**.

Under the current defaults:

```text id="n4vobz"
age        >= 5,555 ticks
HP         < 10,000
score      >= 0.6
encounters >= 6
```

The logic is:

```text id="72zp7f"
AGE
 AND
HP
 AND
SCORE
 AND
ENCOUNTERS
        ↓
reproductively eligible
```

Fail one gate:

```text id="uxkuvd"
not eligible
```

There is no compensating with exceptional performance elsewhere.

---

# Gate 1 — age

The individual must be at least:

```text id="qaolgg"
5,555 ticks old
```

This prevents newborns and juveniles from immediately reproducing.

Without an age gate:

```text id="kcbpkh"
birth
↓
reproduce
↓
birth
↓
reproduce
```

could make genealogical turnover much faster than ecological evaluation.

The age threshold forces individuals to survive long enough for their behavior to have consequences.

---

# Gate 2 — HP

The current rule requires:

```text id="rza8se"
HP < 10,000
```

Notice the strict inequality.

A critter at exactly:

```text id="y1vhpc"
10,000 HP
```

does not pass.

Why have an upper HP gate at all?

Because reproduction is designed to occur after the individual has actually experienced some cost of living.

A pristine newborn at full health should not become reproductively eligible merely because some other metrics happen to look favorable.

The individual must have participated in the ecology enough to leave the untouched initial state.

In Primordial Soup, romance requires minor wear and tear.

---

# Gate 3 — composite score

The current minimum is:

```text id="osnktu"
score >= 0.6
```

This ensures that mere age and damage are not sufficient.

An individual can survive for a long time and still fail if its overall measured life history is weak relative to its lineage.

---

# Gate 4 — encounters

The individual needs at least:

```text id="u7cc9v"
6 encounters
```

An encounter is recorded when the critter occupies a cell with presence from another lineage.

This gate prevents extremely isolated individuals from reproducing without participating meaningfully in inter-lineage ecology.

The current reproductive model therefore rewards not merely:

```text id="b81bqk"
avoid everything forever
```

but some minimum amount of ecological contact.

---

# Passing the gates does not guarantee parenthood

Suppose a lineage contains:

```text id="w306ps"
100 living critters
```

and:

```text id="mpsoyx"
30 pass all four gates
```

Those 30 are only the **eligible set**.

They are then ranked.

With the current default:

```text id="qk63ly"
REPRODUCTION_CRITERION = composite
```

higher composite scores rank first.

Conceptually:

```text id="8r29gn"
living population
       ↓
four eligibility gates
       ↓
eligible population
       ↓
rank by composite score
       ↓
reproductive pool
```

---

# 👑 The reproductive pool

Only the top fraction of eligible individuals enters the parent pool.

Current default:

```text id="2hsbln"
top 1/3
```

For example:

```text id="11vaqi"
30 eligible
     ↓
ranked
     ↓
top 10 enter reproductive pool
```

The implementation guarantees a pool of at least two whenever at least two individuals are eligible.

That is useful because sexual reproduction with:

```text id="ktqbb6"
one parent
```

would require considerably more theological documentation.

---

# 🎲 Parent selection

Once the reproductive pool exists, two different parents are randomly drawn from it.

The draw is:

```text id="em65hr"
without replacement
```

so an individual cannot mate with itself in the same parent pair.

This creates a combination of:

```text id="bhiaxs"
deterministic pressure
+
stochastic pairing
```

The ranking determines **who is allowed into the privileged pool**.

Randomness determines which two members of that pool reproduce in a particular event.

This prevents parenthood from becoming a deterministic monopoly of exactly one highest-scoring pair.

---

# 🔄 Reproduction is turn-based

Reproduction is globally scheduled.

Only one lineage receives a reproductive opportunity at a time.

The order rotates:

```text id="hzps1m"
R → G → B → R → ...
```

There is one global reproductive turn state.

Not three independent lineage clocks.

A fresh world starts with:

```text id="a7mx0p"
turn = R
cooldown = 0
```

so the first lineage can receive a turn immediately.

After a turn, the global cooldown is reset using:

```text id="dqtlcx"
REPRODUCTION_INTERVAL = 150
```

and the next lineage waits for the cooldown cycle.

Meanwhile all lineages continue normal life:

```text id="pkj03b"
perceive
move
interact
gain / lose HP
age
die
```

Only reproduction is gated by the turn.

Green does not stop living merely because Red currently has the maternity ward.

---

# Why rotate reproductive turns?

If every lineage reproduced continuously whenever it had eligible parents, population growth could become extremely aggressive.

Turn-based reproduction provides:

* temporal structure;
* bounded reproductive opportunities;
* more gradual population growth;
* symmetry between lineages;
* easier experimental interpretation.

It also separates:

```text id="a1bbr0"
ecological time
```

from:

```text id="4m6g6t"
reproductive opportunity
```

Every tick matters ecologically.

Only selected ticks matter reproductively.

---

# 🎟️ Reproductive attempts

Receiving a lineage turn does not mean:

> Fill every available population slot immediately.

Instead, the number of reproduction attempts is bounded.

Current rule:

```text id="rkz09f"
attempts =
max(
    1,
    ceil(living population / 50)
)
```

Examples:

```text id="f6cfyo"
population 20
→ 1 attempt

population 50
→ 1 attempt

population 51
→ 2 attempts

population 150
→ 3 attempts

population 333
→ 7 attempts
```

Each successful attempt produces the configured offspring pair.

This makes population growth gradual across reproductive turns rather than explosive in a single event.

Evolution gets a throttle.

---

# Population ceiling

Each lineage currently has a maximum living population of:

```text id="w5iooy"
333
```

Reproduction stops before a successful birth would exceed that ceiling.

The ceiling does not kill existing critters.

It prevents additional births.

Population can still fall naturally through death and later create room for reproduction again.

Conceptually:

```text id="gx4owu"
population < ceiling
→ reproduction may add individuals

population near ceiling
→ births blocked

deaths
→ capacity becomes available again
```

Finite memory meets finite ecology.

---

# A reproductive attempt can fail

A lineage may receive its turn and still produce no children.

Reasons include:

* fewer than two eligible individuals;
* reproductive pool too small;
* population ceiling reached;
* another reproductive prerequisite failing.

Therefore:

```text id="9m3qc4"
reproductive turn
≠
guaranteed birth
```

A turn is an opportunity.

Not a reservation.

---

# 👨‍👩‍👧 Successful reproduction

When a pair successfully reproduces:

```text id="43zl9h"
parent A
+
parent B
     ↓
crossover
     ↓
mutation
     ↓
2 newborns
```

Under the current default:

```text id="7rjbpp"
OFFSPRING_PER_PAIR = 2
```

The two children receive complementary combinations of parental genes before mutation.

---

# Parent life-history update

Each successful reproductive event increments the reproduction counter of each selected parent by:

```text id="bitxb6"
+1
```

This is worth reading carefully.

The current counter behaves as a measure of **successful reproductive events per parent**, even though the event currently creates two children.

It is the value used by the reproductive-success component of composite score.

So:

```text id="p9u7ex"
parent reproduction counter
```

should not automatically be interpreted as a literal genealogical count of every child produced when `OFFSPRING_PER_PAIR > 1`.

---

# ❤️ Reproduction reward

Successful reproduction also gives each parent a small HP reward.

Current implementation:

```text id="dcgojs"
+50 HP
```

per parent, per successful reproductive event.

The reward is applied once to each parent.

It is not multiplied by the number of children.

Conceptually:

```text id="fnz61z"
successful parent A → +50 HP
successful parent B → +50 HP
```

This introduces another feedback:

```text id="lz53ej"
successful reproduction
       ↓
small survival benefit
       ↓
potentially more future reproductive opportunities
```

The reward is intentionally modest relative to the initial:

```text id="03tlz7"
10,000 HP
```

Reproduction helps.

It does not confer immortality.

---

# 🧬 Crossover

Before mutation, parental genomes are recombined.

Primordial Soup currently supports three crossover strategies:

```text id="m6zifr"
blocks
uniform
two_points
```

The active default is:

```text id="wh10ai"
blocks
```

---

# Blocks crossover

Current block size:

```text id="q4ltmt"
64 genes
```

The genome is divided into contiguous blocks.

For each block, the crossover mask chooses which parent contributes that block to one child.

The complementary child receives the opposite source.

Conceptually:

```text id="44zim8"
Parent A:
AAAA AAAA AAAA AAAA

Parent B:
BBBB BBBB BBBB BBBB

random block mask:
 A    B    B    A

Child 1:
AAAA BBBB BBBB AAAA

Child 2:
BBBB AAAA AAAA BBBB
```

The real genome is considerably larger than sixteen characters.

Fortunately Markdown has limits.

Block crossover preserves contiguous groups of neural parameters more readily than independent per-gene mixing.

Whether those contiguous numerical regions correspond to useful inherited structures is an empirical question.

---

# Uniform crossover

Uniform crossover treats each gene independently.

The current crossover probability is:

```text id="vbey2r"
0.5
```

So each location independently chooses between the two parents with equal probability.

Conceptually:

```text id="8wi6ev"
gene 1 → A
gene 2 → B
gene 3 → A
gene 4 → A
gene 5 → B
...
```

The complementary child receives the opposite choice at each position.

Uniform crossover mixes parental genomes much more finely than block crossover.

Excellent for genetic diversity.

Potentially terrible for preserving useful groups of coordinated weights.

Experiments exist to settle arguments like this.

---

# Two-point crossover

Two-point crossover selects two random cut positions.

The region between them is taken from one parent while the complementary child receives the opposite pattern.

Conceptually:

```text id="56zf69"
             cut 1        cut 2
               │            │
Parent A: AAAAA|AAAAAAAAAAAA|AAAAA
Parent B: BBBBB|BBBBBBBBBBBB|BBBBB

Child 1: BBBBB|AAAAAAAAAAAA|BBBBB
Child 2: AAAAA|BBBBBBBBBBBB|AAAAA
```

This preserves large contiguous regions.

It resembles a more traditional genetic-algorithm crossover.

---

# Complementary children

An important property of the crossover implementation is complementarity.

For a given crossover mask:

```text id="i9vl7l"
where child 1 takes A
child 2 takes B

where child 1 takes B
child 2 takes A
```

Before mutation, the pair therefore contains complementary parental contributions.

Mutation can subsequently break that symmetry.

Evolution appreciates siblings developing their own personalities.

---

# ☢️ Mutation

Crossover rearranges existing genetic material.

Mutation creates new variation.

The active mutation system is:

```text id="nu6m66"
two_scales
```

A second mode:

```text id="5cf4fq"
surgical
```

also exists, but is not the current default.

---

# Mutation probability

The runtime mutation rate represents the probability that an offspring will undergo mutation.

Default:

```text id="apzi7f"
5%
```

So for each generated child:

```text id="8l71fe"
random draw
   ↓
mutation?
├── no  → crossover genome survives unchanged
└── yes → mutation algorithm runs
```

The rate can be adjusted interactively with:

```text id="pkrpec"
U
↑ / ↓
```

from:

```text id="5j13fk"
0% to 100%
```

This controls **how often** children mutate.

It does not by itself determine how large each mutation is.

---

# Two-scale mutation

When a child is selected for mutation, the active algorithm chooses between:

```text id="7zzn0h"
LOCAL mutation
```

and:

```text id="x5qp8y"
GLOBAL mutation
```

Current probability:

```text id="v9zy2d"
global = 10%
local  = 90%
```

This creates two evolutionary scales:

```text id="j6o3lt"
local
→ small refinement

global
→ larger exploration
```

Most mutations are conservative.

A minority are deliberately more disruptive.

---

# Local mutation

Current configured local mutation:

```text id="4p4xsl"
5% of genome genes
sigma = 0.1
```

A subset of genes is selected randomly.

Gaussian noise centered at zero is **added** to those genes.

Conceptually:

```text id="87lfzh"
gene = 0.42

noise = -0.07

new gene = 0.35
```

Because the noise scale is small, local mutation tends to refine rather than completely rewrite the affected weights.

---

# Global mutation

Current global mutation:

```text id="nyktj8"
20% of genome genes
sigma = 1.0
```

This affects a much larger part of the genome with much stronger noise.

Conceptually:

```text id="50r8uc"
LOCAL
few genes
small perturbations

GLOBAL
more genes
larger perturbations
```

Global mutation explores.

Local mutation fine-tunes.

At least that is the intention.

Evolution is under no contractual obligation to cooperate.

---

# Gene sampling is without replacement

Within a single two-scale mutation event, the affected genes are selected **without replacement**.

That means a gene is not selected twice within the same mutation event.

If the algorithm decides to affect:

```text id="ampumu"
500 genes
```

then it affects 500 distinct positions.

Not 437 unique positions plus 63 accidental repeats.

This makes the configured mutation fraction meaningful.

---

# Gaussian mutation

Two-scale mutation uses additive Gaussian noise.

That matters because most sampled changes are near zero, while large changes are progressively rarer.

Roughly:

```text id="nxe89f"
many small changes
some medium changes
few large changes
```

This is different from replacing every mutated gene with a completely unrelated random value.

Local adaptation can therefore preserve much of the existing structure.

---

# Gene limits

After Gaussian mutation, values are clamped to:

```text id="pm722g"
-2.0 ≤ gene ≤ 2.0
```

This prevents repeated mutation from allowing weights to drift without bound.

For example:

```text id="nwswos"
old value = 1.9
noise     = +0.8
raw       = 2.7

stored    = 2.0
```

The universe has railings.

---

# Surgical mutation

The alternative mutation mode is:

```text id="q3b73c"
surgical
```

In this mode, mutant children have a configured exact number of gene positions selected.

Those positions are replaced with newly sampled values from the legal gene range.

So the semantics differ significantly.

Two-scale:

```text id="zcxope"
existing value
+
Gaussian perturbation
```

Surgical:

```text id="d6yhlv"
existing value
→ replaced
```

Surgical mutation is more discrete.

Two-scale mutation is the current default because it provides separate mechanisms for refinement and broader exploration.

---

# ⚠️ Current runtime local-scale caveat

The interface currently exposes a runtime:

```text id="cr15oq"
local scale %
```

selected with:

```text id="dxg9pe"
O
```

and stores that value in simulation state.

However, the active `two_scales` mutation implementation currently reads:

```text id="44mmij"
LOCAL_SCALE_FRACTION
```

directly from configuration.

It does **not** consume the runtime `local_scale_fraction` state.

Therefore, in the current code:

```text id="oj820k"
O + ↑/↓
```

changes the displayed and persisted runtime value, but does **not yet change the actual local mutation breadth**.

The effective local fraction remains the configured:

```text id="sbg7xh"
5%
```

until the runtime value is wired into the mutation path.

This is an implementation discrepancy, not intended evolutionary semantics.

It should either be corrected in code or the runtime control removed.

Documentation should not pretend a disconnected knob controls the universe.

---

# Newborn state

A successfully created child begins with:

```text id="3rplc6"
new stable ID
full initial HP
random world position
new generation
inherited/recombined/mutated genome
age = 0
encounters = 0
offspring = 0
exploration = 0
composite score = 0 initially
recurrent memory = 0
```

The child enters the same lineage as its parents.

Lineages do not mutate into other colors.

A green family cannot unexpectedly give birth to blue because crossover got creative.

---

# Newborn position is random

Children are not born beside their parents.

Their initial coordinates are sampled randomly across the world.

This design intentionally separates:

```text id="c6h5ml"
genetic inheritance
```

from:

```text id="vpn60b"
spatial inheritance
```

A useful genome therefore cannot rely on offspring being placed in the same local environment that made its parents successful.

That creates a stronger test of behavioral generality.

A strategy that only works on one lucky pixel has a difficult childhood.

---

# Population growth is not fitness

Suppose Red grows rapidly.

That does not necessarily prove Red has evolved a superior neural policy.

Population can be influenced by:

* current ecological composition;
* reproductive-turn timing;
* available population capacity;
* random parent pairing;
* spatial placement of newborns;
* mutation history;
* environmental zones;
* stochastic events.

Likewise, temporary population decline does not prove evolutionary failure.

Evolutionary claims should be based on repeated measurements.

Not merely:

> Red looked pretty strong around tick 8,000.

---

# Composite score is not evolution itself

The composite score is part of the **selection mechanism**.

That means something subtle:

```text id="lzv4vz"
we define what the score rewards
↓
the score influences who reproduces
↓
evolution may optimize toward that reward
```

If the weights heavily reward exploration, the population may evolve toward exploratory behavior.

If longevity dominates, behavior that supports survival may receive more reproductive representation.

The score is therefore not an objective observer.

It is part of the environment.

This is essential when interpreting experimental results.

---

# Selection pressure

Selection pressure emerges from several layers at once.

```text id="zhbflk"
ECOLOGICAL PRESSURE

HP decay
enemy damage
ally benefit
overcrowding
zones
death

        +

REPRODUCTIVE GATES

age
HP
score
encounters

        +

RANKING

composite score

        +

GENETIC OPERATORS

crossover
mutation
```

Changing any one of these can change evolutionary dynamics.

That is why controlled experiments should change one variable at a time whenever possible.

If you simultaneously change:

```text id="1t6ju8"
mutation
+
zone damage
+
selection weights
+
reproduction age
```

and population behavior changes, congratulations.

You have discovered that something happened.

---

# Mutation vs selection

Mutation does not improve genomes.

Mutation creates variation.

Selection filters consequences.

That distinction is fundamental.

```text id="ehdf5r"
mutation
→ variation

selection
→ differential inheritance
```

A mutation may be:

* beneficial;
* neutral;
* harmful.

The simulator does not label it at birth.

Its consequences emerge through the critter's behavior and ecological history.

---

# Crossover vs mutation

They also solve different evolutionary problems.

Crossover:

```text id="e53mq1"
recombines what already exists
```

Mutation:

```text id="kpx2ym"
introduces new numerical variation
```

Without crossover, successful genetic structures cannot be recombined between parents in the same way.

Without mutation, evolution eventually depends only on combinations of the initial random genetic material.

Together:

```text id="1m3baw"
inherit
+
recombine
+
perturb
```

provide the search mechanism.

---

# Exploration vs exploitation

The current mutation system embodies a classic optimization tradeoff.

```text id="5bm3o9"
EXPLOITATION
local mutation
small changes
refine existing structure

EXPLORATION
global mutation
large changes
search distant alternatives
```

Too much exploitation:

```text id="534o0e"
population may converge
around mediocre solutions
```

Too much exploration:

```text id="yv7nev"
useful inherited structure
may be repeatedly destroyed
```

The right balance depends on the landscape created by the simulation.

And because the ecological landscape changes as populations change, the target itself can move.

Evolutionary optimization is inconvenient like that.

---

# Reproduction changes survival too

Because successful parents receive an HP bonus, reproductive success has both:

```text id="1h0ic7"
genealogical effect
```

and:

```text id="e5q1e0"
immediate survival effect
```

A successful parent:

```text id="7c8rzr"
produces descendants
+
gains 50 HP
```

That can slightly increase its chance of surviving to another reproductive opportunity.

So reproduction participates in a feedback loop:

```text id="r9gjsb"
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

# Extinction stops evolution for that lineage

If a lineage reaches:

```text id="6ps0ni"
population = 0
```

it cannot reproduce.

There are:

* no parents;
* no genomes;
* no newborns.

The reproductive scheduler may later reach that lineage's turn, but there is nobody left to use it.

The simulator does not recreate extinct founders automatically.

Extinction is therefore absorbing for that lineage unless the operator starts or loads another world.

Evolution requires something alive to evolve.

---

# 🧪 What should you experiment with?

Useful evolutionary questions include:

### Mutation probability

```text id="cqcehx"
Does 1% behave differently from 5% or 20%?
```

Observe:

* maximum generation;
* population stability;
* score;
* extinction frequency.

---

### Selection weights

Increase longevity pressure.

Question:

> Does behavior become more conservative?

Increase exploration pressure.

Question:

> Do populations move more, and what does that cost them?

---

### Reproductive age

Lower the minimum age.

Question:

> Does faster generational turnover accelerate adaptation or merely amplify noise?

---

### Encounter gate

Raise the required number of encounters.

Question:

> Does this increase ecological participation, or simply eliminate too many otherwise successful parents?

---

### Reproductive pool size

Change the top-third rule.

Question:

> Does stronger elitism improve measured fitness faster, or collapse genetic diversity?

---

### Crossover strategy

Compare:

```text id="n5nh5t"
blocks
uniform
two_points
```

using the same random seeds and experimental protocol.

Question:

> Which strategy better preserves useful neural structures?

---

### Global mutation probability

Increase the chance that mutations use the global scale.

Question:

> Does broader genetic exploration help populations escape plateaus?

---

# What should count as evidence?

One successful lineage in one run is weak evidence.

Primordial Soup is stochastic.

Randomness enters through:

* founder genomes;
* initial positions;
* environmental zones;
* parent selection;
* crossover;
* mutation;
* newborn positions.

A stronger experimental pattern is:

```text id="h6qgfi"
same configuration
+
multiple seeds
+
same run duration
+
same measured outputs
```

Then compare distributions.

Not anecdotes.

The blue lineage does not become scientifically significant merely because you became emotionally invested in it.

See [Experiments](experiments.md).

---

# The evolutionary pipeline

Putting the reproductive process together:

```text id="fpx2lp"
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
      ├── random positions
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

Reproduction creates descendants.

It does not certify them.

---

# In one sentence

Primordial Soup evolves neural controllers by letting ecological life histories determine reproductive eligibility, ranking eligible individuals within each lineage, recombining selected parental genomes, introducing mutations at local and global scales, and then returning the descendants to the same hostile universe to see what happens.

No fitness oracle.

No training labels.

Just inheritance, pressure, randomness and consequences.

---

# Related documentation

For the ecological rules that produce survival pressure:

→ [Simulation](simulation.md)

For observing selected individuals and generations:

→ [Inspection](inspection.md)

For controlled evolutionary comparisons:

→ [Experiments](experiments.md)

For every configurable selection and mutation constant:

→ [Configuration](configuration.md)

For the NumPy implementation of scoring, crossover and mutation:

→ [Architecture](architecture.md)
