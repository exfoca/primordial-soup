# 🌍 The Simulation

Primordial Soup is a small artificial universe populated by autonomous
neural critters.

They are born. They look around. They make decisions. They collide with
other critters. They gain and lose HP. Some survive long enough to
reproduce. Their descendants inherit modified versions of their neural
networks. Eventually everyone dies.

The interesting part is everything that happens in between.

This document explains the **simulation itself**. No Python knowledge is
required. For implementation details, see [Architecture](architecture.md).

---

# What are we actually simulating?

Primordial Soup is an **artificial-life simulation**.

It does not attempt to reproduce real biology in detail. Instead, it
builds a deliberately small evolutionary system containing several
ingredients associated with adaptive processes:

```text
individual variation
        +
environmental pressure
        +
competition and cooperation
        +
differential survival
        +
reproduction
        +
inheritance
        +
mutation
        ↓
evolutionary dynamics
```

Each individual behaves according to its own inherited neural network.

There is no script saying "if enemy nearby: run away". There is no
handcrafted rule saying "if zone is dangerous: avoid it".

Good strategy is not defined directly. It emerges — if evolution
manages to find one.

---

# 🦠 The critter

The basic unit of Primordial Soup is the **critter**.

A critter has:

* a lineage;
* a unique identity;
* a position;
* HP;
* an age;
* a generation;
* a neural-network genome;
* a short-term neural state;
* a record of exploration;
* a record of encounters;
* an offspring count;
* and a composite score used by selection.

It is deliberately a small model. There are no organs, no hunger
variable, no stomach, no immune system, no taxes. We had to draw the
line somewhere.

---

# 🪪 Identity

Every critter receives a unique, stable ID.

This matters because the population is constantly changing. Critters
die. New ones are born. Internal data structures are compacted.
Positions change every tick.

A critter cannot safely be identified by "the fifth red critter"
because five ticks later the fifth red critter may be someone else.

Instead:

```text
critter #1847
```

continues to mean **critter #1847** for its entire life.

This stable identity is important for inspection and persistence.

---

# 🧬 The three lineages

The world contains three lineages:

```text
R — Red
G — Green
B — Blue
```

For each lineage, one other lineage behaves as an ally and one as an
enemy:

```text
R:  ally → G    enemy → B
G:  ally → B    enemy → R
B:  ally → R    enemy → G
```

Visually:

```text
R → G → B → R
↑           ↓
└───────────┘
```

From the perspective of hostility:

```text
B harms R
R harms G
G harms B
```

This is a **non-transitive relationship**.

There is no universally strongest lineage. If one lineage becomes
extremely common, the ecological conditions experienced by the others
change.

That can create oscillations, temporary dominance, population crashes,
recoveries, spatial segregation, or extinction.

Rock beats scissors. Scissors beats paper. Paper beats rock. And then
someone puts all three inside NumPy.

---

# 🌐 The world is a torus

No hard borders. The world wraps around itself horizontally and
vertically.

If a critter walks beyond the right edge, it appears on the left. If it
leaves through the bottom, it returns from the top.

Mathematically, the world behaves like a **2D torus**.

Every position has a continuous neighborhood. There are no privileged
corners and no walls.

If you ever find yourself saying "the blue lineage has migrated east",
remember that east eventually becomes west.

---

# 👁️ What can a critter perceive?

Critters do not see the whole world.

Each one receives a local view around its current position.

Vision radius is five cells, producing an:

```text
11 × 11
```

observation window.

For every position in that window, the critter receives information
about the density of all three lineages.

```text
11 × 11 spatial cells
        ×
3 lineage channels
        =
363 visual inputs
```

The critter is not asking "is Bob standing at coordinate 42,17?". It
sees something closer to "how much red, green and blue presence exists
around me?".

Perception wraps around the toroidal world.

## Internal perception

Vision is not the entire neural input. The critter also receives
information about itself:

```text
HP
age
previous action
low-HP state
```

Together:

```text
363 visual inputs
+
4 internal inputs
=
367 neural inputs
```

Two critters can see exactly the same external scene and still make
different decisions because their genomes, HP, age, previous neural
state and previous action may differ.

---

# 🧠 The brain

Every critter carries an inherited neural network.

Current architecture:

```text
367 inputs
        ↓
25 neurons (first hidden layer)
        ↓
12 neurons (second hidden layer)
        ↓
9 outputs
```

The first hidden layer also receives a recurrent contribution from its
own previous state.

```text
                    previous hidden state
                           │
                           ▼
input → hidden layer 1 → hidden layer 2 → movement outputs
             ▲
             │
          recurrence
```

This gives the critter a limited form of short-term memory.

It is not memory in the human sense. The critter does not remember
"yesterday I met a green individual named Steve". It carries forward a
numerical neural state that can influence its next decision.

---

# 🧬 The genome is the brain

The network weights are encoded directly in the critter's genome.

No training phase. No gradient descent. No backpropagation during life.
No optimizer updates weights after a mistake.

```text
genome
   ↓
neural network
   ↓
behavior
   ↓
survival and reproduction
   ↓
descendants
```

The genome changes between generations through crossover and mutation.

The individual's neural weights remain its inherited weights during
life.

```text
machine learning:  improve the model
Primordial Soup:   kill the model and let its children try again
```

---

# 🚶 Movement

Every tick, the neural network produces nine outputs.

They correspond to the Moore neighborhood:

```text
↖  ↑  ↗
←  •  →
↙  ↓  ↘
```

The center action means "stay where you are".

The highest network output determines the chosen action. A small
built-in impulse favors the stay-still action slightly.

Movement itself has no strategic meaning imposed by the simulator.

---

# ❤️ HP: the currency of survival

Each critter is born with HP.

Current default:

```text
initial HP = 10,000
```

Every tick applies a small baseline decay:

```text
-1 HP
```

A critter living in complete isolation cannot survive forever.

A critter dies when:

```text
HP <= 0
```

Death is permanent.

The operator can reset HP for surviving individuals through the
Configuration panel:

```text
C
↓
Configuration
↓
Heal all critters
↓
Enter
```

That is an operator intervention, not part of natural simulation
dynamics.

The global **H** accelerator has no effect on HP. It toggles the
floating HUD, which is purely visual.

---

# 🤝 Allies

Sharing a position with an ally grants an HP benefit.

Current default:

```text
ally present → +100 HP
```

This creates a cooperative pressure. A lineage may benefit from
remaining spatially close to its allied lineage.

But the ecology is cyclic. Your ally is someone else's enemy.

So large cooperative clusters may also create opportunities for another
lineage.

Ecology rarely leaves a free lunch unattended.

---

# ⚔️ Enemies

Sharing a position with an enemy causes damage.

By default:

```text
enemy present → -100 HP
```

If an ally is present at the same time, enemy damage is reduced.

The effects are combined algebraically rather than choosing exactly one
interaction.

For example, ignoring environmental zones:

```text
alone             → -1 HP
ally              → +99 HP
enemy             → -101 HP
ally + enemy      → +49 HP
```

The base metabolic decay is included in those totals.

---

# 👥 Overcrowding

Critters are penalized for sharing a cell with members of their own
lineage.

Current default:

```text
own-lineage overcrowding → -100 HP
```

This creates pressure against unlimited stacking.

Without it, a lineage could discover that the world's greatest
evolutionary strategy is "everyone stand on the same pixel".

Nature has produced stranger strategies, but we do not need to encourage
this one.

Overcrowding is independent of ally and enemy effects.

---

# 🌍 Environmental zones

The world contains spatial environmental zones.

A zone is a region where HP is modified while a critter is inside it.

```text
positive effect → refuge
zero effect     → neutral geography
negative effect → hazard
```

The zone effect can be changed while the simulation is running.

A population may evolve under beneficial zones and suddenly find that
yesterday's refuge is today's toxic swamp.

The critters are not informed. They must experience the consequences.

Evolution does not ship release notes.

---

# 🧮 Several effects can happen at once

A critter may simultaneously experience:

* baseline HP decay;
* ally benefit;
* enemy damage;
* overcrowding damage;
* environmental-zone effects.

The final HP change is the combination of those effects.

A single location might be beneficial for one lineage, harmful for
another, survivable only with allies, disastrous under overcrowding, or
excellent until the zone effect changes.

The rules themselves are simple. Their combinations are not.

---

# ⏱️ What happens during one tick?

Order matters.

```text
1. perceive
2. decide
3. move
4. rebuild the spatial state
5. interact
6. gain / lose HP
7. age
8. die if necessary
9. reproduce if this lineage has the turn
10. record metrics
```

Two ordering decisions are especially important.

## Everyone perceives before ecological consequences

Critters decide based on the current spatial world. They do not receive
information from a halfway-updated universe where one lineage has
already been punished and another has not.

## Interaction happens after movement

All movement occurs before HP consequences are calculated.

Otherwise, processing order would become part of the ecology. The first
lineage updated could receive an accidental advantage simply because
Python reached it first.

That would not be evolution. That would be a scheduling bug wearing a
lab coat.

---

# 🧓 Age

Every surviving tick increases an individual's age.

Age matters for longevity measurement, evaluation, reproductive
eligibility, inspection, and distinguishing genuine long-term survival
from temporary population growth.

An old critter is not necessarily a good critter. It may simply have
been lucky.

That is why selection considers several dimensions instead of relying
only on longevity.

---

# 🗺️ Exploration

The simulation tracks whether a critter moves through the world.

Exploration contributes to its life history and can influence composite
selection.

This creates a potential evolutionary tension. Remaining in a safe
location may help immediate survival. Exploring may expose the critter
to enemies, overcrowding, hazardous zones — but may also lead toward
allies, beneficial zones, more useful spatial behavior, better
composite fitness.

Evolution is not told which strategy is correct.

---

# 🤝 Encounters

A critter accumulates encounters when it occupies a cell containing
another lineage.

Encounters reflect ecological contact rather than mere movement.

A creature that lives a very long time by avoiding absolutely everything
may survive well while performing poorly on other evolutionary
dimensions.

The simulator distinguishes surviving from being reproductively
successful. Those are related. They are not identical.

---

# 🏆 Composite score

The current composite score combines longevity, exploration, encounters
and reproduction.

```text
score =
    0.5 × normalized longevity
  + 0.3 × normalized exploration
  + 0.3 × normalized encounters
  + 0.3 × normalized reproduction
```

Each component is normalized relative to the individual's own lineage.

This is important. Suppose one lineage has only a few surviving members
while another has hundreds. A globally normalized score could cause the
small lineage to become meaningless simply because another lineage
currently dominates.

Per-lineage normalization preserves meaningful competition **within**
each lineage.

The composite score is not an absolute universal measure of
intelligence.

A score of 0.7 does not mean "this critter is 70% intelligent". It
means: under the current scoring rules and relative lineage context,
this individual performs well across the measured dimensions.

---

# 🧬 Reproduction is not automatic

Being alive is not enough to reproduce.

Default eligibility gates:

```text
age        >= 5,555 ticks
HP         <  10,000
score      >= 0.6
encounters >= 6
```

All gates must pass.

A critter can be very old but insufficiently interactive. Highly
interactive but too young. High-scoring but too healthy. Wounded but
evolutionarily unimpressive.

None of those conditions alone guarantees reproduction.

This deliberately separates existence from eligibility to pass genes
forward.

See [Evolution](evolution.md) for the full model.

---

# 🔄 Reproduction happens in turns

Reproduction is a global scheduled event.

The opportunity rotates:

```text
R → G → B → R → ...
```

Default interval: every `150` ticks.

When a lineage receives its turn, eligible individuals may be selected
as parents. The other lineages still perceive, move, interact, gain or
lose HP, age, die. They simply do not reproduce during that turn.

The universe has mating season. It is maintained by an integer counter.

Romance remains undefeated.

---

# 👨‍👩‍👧 Parent selection

Passing the eligibility gates does not automatically make an individual
a parent.

Eligible individuals are ranked. The strongest subset forms the
reproductive pool. Parents are drawn from that pool.

```text
population
    │
    ▼
eligibility gates
    │
    ▼
eligible individuals
    │
    ▼
ranking
    │
    ▼
reproductive pool
    │
    ▼
parent pair
```

Two distinct filters: Can you reproduce? Among those who can, who gets
the opportunity?

---

# 👶 Birth

A newborn receives:

* a new stable ID;
* full initial HP;
* a random position in the world;
* generation number derived from its parents;
* a new genome produced from parental genomes;
* zero age;
* zero encounters;
* zero offspring;
* zero exploration history;
* zero recurrent neural state.

New generation is:

```text
max(parent A generation, parent B generation) + 1
```

Generation measures genealogical depth.

---

# 🧠 Memory is not inherited

A newborn inherits neural structure and weights through its genome.

It does not inherit its parents' temporary neural state.

At birth:

```text
recurrent memory = 0
```

A parent can pass along a brain capable of producing a useful behavior.
It cannot pass along "what it was thinking three ticks ago".

Genes are inherited. Experience is not.

At least not in this universe.

---

# 🧬 Crossover and mutation

A child's genome is not simply a clone of one parent.

Genetic material from two parents is combined through crossover.
Offspring may then mutate.

Conceptually:

```text
parent A genome ─┐
                 ├── crossover ── child genome
parent B genome ─┘
                        │
                        ▼
                     mutation
```

Crossover rearranges existing genetic material. Mutation creates new
variation.

There is no universally correct mutation rate. That is one of the things
worth experimenting with.

See [Evolution](evolution.md).

---

# ☠️ Death

After ecological effects are applied, a critter dies if:

```text
HP <= 0
```

Dead individuals are removed from the living population.

Their descendants remain. Their evolutionary effects remain.

If the individual was being observed, Primordial Soup preserves a
snapshot of its final state.

The simulation moves on. The microscope does not.

See [Inspection](inspection.md).

---

# 📉 Extinction

A lineage is extinct when it has no living individuals left.

The simulation does not automatically repopulate it.

Extinction may result from ecological pressure, poor inherited behavior,
unfavorable spatial distribution, excessive mutation, reproductive
failure, environmental change, population collapse, stochastic history,
or several of these at once.

Because ecological relations are cyclic, losing one lineage can also
radically alter the environment experienced by the remaining two.

Removing one participant from a non-transitive system changes the game
itself.

---

# 📈 What does "evolution is working" mean?

Evolution is not equivalent to "population goes up". Nor to "score goes
up forever".

Observable signals include lineage population, lifetime, generation
depth, HP, composite score, encounters, exploration, reproductive
success, spatial organization, behavioral patterns.

A population may adapt by becoming longer-lived, more reproductively
successful, better at finding allies, better at avoiding enemies, better
at exploiting environmental zones, less prone to overcrowding, or some
combination.

But stochastic variation can also produce temporary trends.

One run is a story. Repeated controlled runs are evidence.

See [Experiments](experiments.md).

---

# 🧪 Emergence

No rule explicitly says "form a colony" or "avoid blue" or "stay near
environmental zones". Yet patterns resembling those strategies may
appear.

That is what makes artificial-life systems interesting.

But there is an important warning.

Humans are extremely good at seeing intention.

If a critter repeatedly moves toward green individuals, it is tempting
to say "it likes green". The simulation supports a more careful
statement: "its inherited neural dynamics currently produce movement
correlated with local green density".

Less romantic. Much harder to misinterpret.

---

# 🔬 What this simulation is not

Primordial Soup is not a realistic model of biological evolution, animal
cognition, real genetics or real ecosystems.

It is not evidence that neural networks resemble biological brains in
detail, that an observed behavior is intentional, or a universal
definition of evolutionary fitness.

Its abstractions are intentionally compact.

HP stands in for survival pressure. Genome stores neural parameters.
Crossover combines numerical genomes. Mutation perturbs those
parameters. Composite score implements a configurable selection
pressure.

These constructs borrow vocabulary and ideas from biology, artificial
life and evolutionary computation. They should not be confused with
biological equivalence.

---

# 🧭 The complete lifecycle

```text
                     ┌───────────────┐
                     │     BIRTH     │
                     │               │
                     │ new identity  │
                     │ inherited DNA │
                     │ memory = 0    │
                     └───────┬───────┘
                             │
                             ▼
                     ┌───────────────┐
                     │   PERCEIVE    │
                     │               │
                     │ local world   │
                     │ internal state│
                     └───────┬───────┘
                             │
                             ▼
                     ┌───────────────┐
                     │     THINK     │
                     │               │
                     │ neural net    │
                     │ + recurrence  │
                     └───────┬───────┘
                             │
                             ▼
                     ┌───────────────┐
                     │     MOVE      │
                     │               │
                     │ 9 choices     │
                     └───────┬───────┘
                             │
                             ▼
                     ┌───────────────┐
                     │   INTERACT    │
                     │               │
                     │ allies        │
                     │ enemies       │
                     │ crowding      │
                     │ zones         │
                     └───────┬───────┘
                             │
                             ▼
                     ┌───────────────┐
                     │  HP CHANGES   │
                     └───────┬───────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                 HP > 0            HP <= 0
                    │                 │
                    ▼                 ▼
             ┌─────────────┐   ┌─────────────┐
             │   SURVIVE   │   │     DIE     │
             └──────┬──────┘   └─────────────┘
                    │
                    ▼
            reproductive turn?
                    │
              ┌─────┴─────┐
              │           │
             no          yes
              │           │
              │           ▼
              │    eligibility gates
              │           │
              │      ┌────┴────┐
              │      │         │
              │    fail       pass
              │      │         │
              │      │         ▼
              │      │      ranking
              │      │         │
              │      │         ▼
              │      │      parents
              │      │         │
              │      │         ▼
              │      │     crossover
              │      │         │
              │      │         ▼
              │      │      mutation
              │      │         │
              │      │         ▼
              │      │       BIRTH
              │      │
              └──────┴───────────────→ next tick
```

A small set of explicit rules. A large number of possible histories. And
absolutely no guarantee that the critters will behave sensibly.

---

# Where to go next

→ [Evolution](evolution.md) — selection, gates, crossover and mutation
→ [Inspection](inspection.md) — following individual critters
→ [Experiments](experiments.md) — controlled comparisons
→ [Configuration](configuration.md) — changing the laws described here
→ [Architecture](architecture.md) — the Python and NumPy machinery
