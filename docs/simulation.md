# 🌍 The Simulation

Primordial Soup is a small artificial universe populated by autonomous neural critters.

They are born.

They look around.

They make decisions.

They collide with other critters.

They gain and lose HP.

Some survive long enough to reproduce.

Their descendants inherit modified versions of their neural networks.

Eventually everyone dies.

The interesting part is everything that happens in between.

This document explains the **simulation itself**.

No Python knowledge is required.

If you are looking for implementation details, see [Architecture](architecture.md).

---

## What are we actually simulating?

Primordial Soup is an **artificial-life simulation**.

It does not attempt to reproduce real biology in detail.

Instead, it builds a deliberately small evolutionary system containing several ingredients associated with adaptive processes:

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

There is no script saying:

```text
if enemy nearby:
    run away
```

There is no handcrafted rule saying:

```text
if zone is dangerous:
    avoid it
```

The neural network receives information, produces movement decisions, and whatever consequences follow become part of the individual's evolutionary history.

Good strategy is therefore not defined directly.

It emerges — if evolution manages to find one.

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

Conceptually:

```text
CRITTER

identity
lineage

body
├── position
├── HP
└── age

brain
├── inherited neural weights
└── temporary recurrent state

life history
├── generation
├── cells explored
├── encounters
├── offspring
└── composite score
```

It is deliberately a small model.

There are no organs.

No hunger variable.

No stomach.

No immune system.

No taxes.

We had to draw the line somewhere.

---

# 🪪 Identity

Every critter receives a unique, stable ID.

This matters because the population is constantly changing.

Critters die.

New ones are born.

Internal data structures are compacted.

Positions change every tick.

A critter therefore cannot safely be identified by:

```text
"the fifth red critter"
```

because five ticks later the fifth red critter may be someone else.

Instead:

```text
critter #1847
```

continues to mean **critter #1847** for its entire life.

This stable identity is particularly important for inspection and persistence.

You can observe an individual while the rest of the population changes around it without accidentally switching to its neighbor because an array was reorganized.

It sounds obvious.

Computers occasionally require considerable engineering to achieve obvious things.

---

# 🧬 The three lineages

The world contains three lineages:

```text
R — Red
G — Green
B — Blue
```

They participate in a cyclic ecological relationship.

For each lineage, one other lineage behaves as an ally and one as an enemy:

```text
R:
    ally  → G
    enemy → B

G:
    ally  → B
    enemy → R

B:
    ally  → R
    enemy → G
```

Or visually:

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

There is no universally strongest lineage.

If one lineage becomes extremely common, the ecological conditions experienced by the others change.

That can create:

* oscillations;
* temporary dominance;
* population crashes;
* recoveries;
* spatial segregation;
* or extinction.

Rock beats scissors.

Scissors beats paper.

Paper beats rock.

And then someone puts all three inside NumPy.

---

# 🌐 The world is a torus

Primordial Soup has no hard borders.

The world wraps around itself horizontally and vertically.

If a critter walks beyond the right edge:

```text
┌───────────────────┐
│                   │
│ ← appears here    │ → leaves here
│                   │
└───────────────────┘
```

If it leaves through the bottom, it returns from the top.

Mathematically, the world behaves like a **2D torus**.

That means there are no privileged corners and no walls that creatures can exploit as artificial shelters.

Every position has a continuous neighborhood.

So if you ever find yourself saying:

> “The blue lineage has migrated east.”

Remember that east eventually becomes west.

---

# 👁️ What can a critter perceive?

Critters do not see the whole world.

Each one receives a local view around its current position.

The current vision radius is five cells, producing an:

```text
11 × 11
```

observation window.

For every position in that window, the critter receives information about the density of all three lineages.

Conceptually:

```text
11 × 11 spatial cells
        ×
3 lineage channels
        =
363 visual inputs
```

The critter is therefore not asking:

> “Is Bob standing at coordinate 42,17?”

It sees something closer to:

> “How much red, green and blue presence exists around me?”

The perception wraps around the toroidal world as well.

A critter near the right edge can therefore see individuals near the left edge.

There is no visual cliff at the boundary.

---

## Internal perception

Vision is not the entire neural input.

The critter also receives information about itself.

The current model includes four internal inputs related to:

* HP;
* age;
* previous action;
* low-HP state.

Together:

```text
363 visual inputs
+
4 internal inputs
=
367 neural inputs
```

This distinction matters.

Two critters can see exactly the same external scene and still make different decisions because:

* their genomes differ;
* their HP differs;
* their age differs;
* their previous neural state differs;
* their previous action differs.

Behavior is therefore a function of both:

```text
world
+
individual state
+
memory
+
genome
```

---

# 🧠 The brain

Every critter carries an inherited neural network.

The current network has:

```text
367 inputs

        ↓

25 neurons
first hidden layer

        ↓

12 neurons
second hidden layer

        ↓

9 outputs
```

The first hidden layer also receives a recurrent contribution from its own previous state.

Conceptually:

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

It is not memory in the human sense.

The critter does not remember:

> “Yesterday I met a green individual named Steve.”

It carries forward a numerical neural state that can influence its next decision.

Still, this means behavior can depend on recent history rather than only on the current frame.

---

# 🧬 The genome is the brain

The network weights are encoded directly in the critter's genome.

There is no training phase using gradient descent.

No backpropagation occurs during the critter's lifetime.

No optimizer updates its weights after a mistake.

Instead:

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

The genome changes between generations through:

* crossover;
* mutation.

The individual's neural weights remain its inherited weights during life.

In other words:

```text
machine learning:
    improve the model

Primordial Soup:
    kill the model and let its children try again
```

Evolution has strong opinions about checkpointing.

---

# 🚶 Movement

Every tick, the neural network produces nine outputs.

They correspond to the Moore neighborhood:

```text
↖  ↑  ↗

←  •  →

↙  ↓  ↘
```

The center action means:

```text
stay where you are
```

The highest network output determines the chosen action.

A small built-in impulse favors the stay-still action slightly.

This prevents movement from being automatically preferable simply because neural outputs happen to be noisy.

Movement itself has no strategic meaning imposed by the simulator.

Moving north is not intrinsically good.

Staying still is not intrinsically bad.

The consequences depend on what is around the critter.

---

# ❤️ HP: the currency of survival

Each critter is born with HP.

Under the current default configuration:

```text
initial HP = 10,000
```

Every tick applies a small baseline decay:

```text
-1 HP
```

So even a critter living in complete isolation cannot survive forever.

To extend its life, it must benefit from favorable interactions or environmental effects.

A critter dies when:

```text
HP <= 0
```

Death is permanent.

There are no resurrection mechanics in evolution.

The **H** control can reset HP for surviving individuals, but that is an operator intervention, not part of natural simulation dynamics.

Even artificial gods get debug commands.

---

# 🤝 Allies

Sharing a position with an ally grants an HP benefit.

Under the current default configuration:

```text
ally present → +100 HP
```

This creates a cooperative pressure.

A lineage may benefit from remaining spatially close to its allied lineage.

But the ecology is cyclic.

Your ally is someone else's enemy.

So large cooperative clusters may also create opportunities for another lineage.

Ecology rarely leaves a free lunch unattended.

---

# ⚔️ Enemies

Sharing a position with an enemy causes damage.

By default:

```text
enemy present → -100 HP
```

If an ally is present at the same time, enemy damage is reduced.

The ally therefore acts partly as protection during conflict.

The effects are combined algebraically rather than choosing exactly one interaction.

For example, ignoring environmental zones:

```text
alone
→ -1 HP

ally
→ +99 HP

enemy
→ -101 HP

ally + enemy
→ +49 HP
```

The base metabolic decay is included in those totals.

This means the same spatial location can produce very different survival outcomes depending on the local ecological composition.

---

# 👥 Overcrowding

Critters are also penalized for sharing a cell with members of their **own lineage**.

Under the current defaults:

```text
own-lineage overcrowding → -100 HP
```

This creates pressure against unlimited stacking.

Without it, a lineage could potentially discover that the world's greatest evolutionary strategy is:

```text
everyone stand on the same pixel
```

Nature has produced stranger strategies, but we do not need to encourage this one.

Overcrowding is independent of ally and enemy effects.

Several pressures may therefore apply during the same tick.

---

# 🌍 Environmental zones

The world contains spatial environmental zones.

A zone is a region where HP is modified while a critter is inside it.

Depending on the current configuration, a zone can behave as:

```text
positive effect → refuge

zero effect     → neutral geography

negative effect → hazard
```

The zone effect can be changed while the simulation is running.

That creates a useful experimental mechanism.

A population may evolve under beneficial zones and suddenly find that:

```text
yesterday's refuge
=
today's toxic swamp
```

The critters are not informed.

They must experience the consequences.

Evolution does not ship release notes.

---

# 🧮 Several effects can happen at once

The simulation does not treat ecological interactions as mutually exclusive states.

A critter may simultaneously experience:

* baseline HP decay;
* ally benefit;
* enemy damage;
* overcrowding damage;
* environmental-zone effects.

The final HP change is the combination of those effects.

So a single location might be:

* beneficial for one lineage;
* harmful for another;
* survivable only with allies;
* disastrous under overcrowding;
* or excellent until the zone effect changes.

This is one source of emergent complexity.

The rules themselves are simple.

Their combinations are not.

---

# ⏱️ What happens during one tick?

Order matters.

A simulation tick follows a defined sequence:

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

At a higher level:

```text
WORLD AT TIME T
      │
      ▼
   perceive
      │
      ▼
 neural decision
      │
      ▼
     move
      │
      ▼
WORLD AT TIME T+1 POSITIONALLY
      │
      ▼
ecological consequences
      │
      ├── survive
      ├── die
      └── possibly reproduce
```

Two ordering decisions are especially important.

---

## Everyone perceives before ecological consequences

Critters decide based on the current spatial world.

They do not receive information from some halfway-updated universe where one lineage has already been punished and another has not.

---

## Interaction happens after movement

All movement occurs before HP consequences are calculated.

Otherwise, processing order would become part of the ecology.

The first lineage updated could receive an accidental advantage simply because Python reached it first.

That would not be evolution.

That would be a scheduling bug wearing a lab coat.

---

# 🧓 Age

Every surviving tick increases an individual's age.

Age matters for several reasons:

* it measures longevity;
* it contributes to evaluation;
* it can affect reproductive eligibility;
* it is useful when inspecting individuals;
* it helps distinguish genuine long-term survival from temporary population growth.

An old critter is not necessarily a good critter.

It may simply have been lucky.

That is why selection can consider several dimensions instead of relying only on longevity.

---

# 🗺️ Exploration

The simulation tracks whether a critter moves through the world.

Exploration contributes to its life history and can influence composite selection.

This creates a potential evolutionary tension.

Remaining in a safe location may help immediate survival.

Exploring may expose the critter to:

* enemies;
* overcrowding;
* hazardous zones.

But exploration may also lead toward:

* allies;
* beneficial zones;
* more useful spatial behavior;
* better composite fitness.

Evolution is not told which strategy is correct.

That depends on the ecology that actually emerges.

---

# 🤝 Encounters

A critter accumulates encounters when it occupies a cell containing another lineage.

Encounters therefore reflect ecological contact rather than mere movement.

They matter because interaction is part of the current selection model.

A creature that lives a very long time by avoiding absolutely everything may survive well while performing poorly on other evolutionary dimensions.

Whether that matters depends on the configured selection pressure.

The simulator distinguishes:

```text
surviving
```

from:

```text
being reproductively successful
```

Those are related.

They are not identical.

---

# 🏆 Composite score

Primordial Soup can evaluate individuals using several aspects of their life history.

The current composite score combines:

* longevity;
* exploration;
* encounters;
* reproduction.

Conceptually:

```text
fitness =
    longevity contribution
  + exploration contribution
  + interaction contribution
  + reproduction contribution
```

Each component is normalized relative to the individual's own lineage.

This is important.

Suppose one lineage has only a few surviving members while another has hundreds.

A globally normalized score could cause the small lineage to become meaningless simply because another lineage currently dominates the world.

Per-lineage normalization preserves meaningful competition **within** each lineage.

The composite score is therefore not an absolute universal measure of intelligence.

A score of:

```text
0.7
```

does not mean:

> “This critter is 70% intelligent.”

It means:

> “Under the current scoring rules and relative lineage context, this individual performs well across the measured dimensions.”

Evolutionary fitness is contextual.

So are most performance reviews.

---

# 🧬 Reproduction is not automatic

Being alive is not enough to reproduce.

A potential parent must currently pass several eligibility gates.

Under the current default rules, it must be:

```text
old enough
AND
below the reproductive HP gate
AND
above the minimum composite score
AND
experienced enough in encounters
```

Currently those defaults are:

```text
minimum age      = 5,555 ticks
HP               < 10,000
composite score >= 0.6
encounters      >= 6
```

All gates must pass.

A critter can therefore be:

* very old but insufficiently interactive;
* highly interactive but too young;
* high-scoring but too healthy;
* wounded but evolutionarily unimpressive.

None of those conditions alone guarantees reproduction.

This deliberately separates:

```text
existence
```

from:

```text
eligibility to pass genes forward
```

For the full model, see [Evolution](evolution.md).

---

# 🔄 Reproduction happens in turns

Reproduction is a global scheduled event.

The lineages do not all reproduce simultaneously.

The opportunity rotates:

```text
R → G → B → R → ...
```

Under the current defaults, a reproductive turn becomes available every:

```text
150 ticks
```

When a lineage receives its turn, eligible individuals may be selected as parents.

The other lineages still:

* perceive;
* move;
* interact;
* gain or lose HP;
* age;
* die.

They simply do not reproduce during that turn.

This prevents reproduction from becoming an uncontrolled continuous flood and gives the reproductive process a clear temporal structure.

The universe has mating season.

It is maintained by an integer counter.

Romance remains undefeated.

---

# 👨‍👩‍👧 Parent selection

Passing the eligibility gates does not automatically make an individual a parent.

Eligible individuals are ranked according to the configured reproductive criterion.

The strongest subset forms the reproductive pool.

Parents are then drawn from that pool.

Conceptually:

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

This creates two distinct filters:

```text
Can you reproduce?
```

and then:

```text
Among those who can, who gets the opportunity?
```

That distinction matters when interpreting selection pressure.

---

# 👶 Birth

When two parents reproduce, their genomes are combined and mutated to generate offspring.

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

The new generation is:

```text
max(parent A generation, parent B generation) + 1
```

So generation measures genealogical depth.

---

# 🧠 Memory is not inherited

A newborn inherits neural **structure and weights** through its genome.

It does not inherit its parents' temporary neural state.

At birth:

```text
recurrent memory = 0
```

This is an important distinction.

A parent can pass along a brain capable of producing a useful behavior.

It cannot pass along:

```text
what it was thinking three ticks ago
```

Genes are inherited.

Experience is not.

At least not in this universe.

---

# 🧬 Crossover

A child's genome is not simply a clone of one parent.

Genetic material from two parents is combined through crossover.

Depending on configuration, crossover may operate using different strategies.

The current system supports mechanisms designed to mix parental information while retaining some structure.

Conceptually:

```text
parent A genome ─┐
                 ├── crossover ── child genome
parent B genome ─┘
```

This produces variation even before mutation occurs.

See [Evolution](evolution.md) for the crossover strategies.

---

# ☢️ Mutation

After crossover, offspring may mutate.

Mutation introduces new genetic variation.

Depending on configuration, mutations can be:

* local and relatively small;
* broader and more disruptive.

This creates the classic exploration/exploitation tension.

Too little variation can cause a population to converge around mediocre solutions.

Too much variation can continually destroy useful inherited structure.

Conceptually:

```text
very low mutation
    ↓
stable inheritance
    ↓
possible stagnation


moderate mutation
    ↓
variation + inheritance
    ↓
adaptive search


extreme mutation
    ↓
constant disruption
    ↓
useful structure may not survive
```

There is no universally correct mutation rate.

That is one of the things worth experimenting with.

---

# ☠️ Death

After ecological effects are applied, a critter dies if:

```text
HP <= 0
```

Dead individuals are removed from the living population.

Their descendants remain.

Their evolutionary effects remain.

Their genes may already exist throughout later generations.

If the individual was being observed, however, Primordial Soup preserves a snapshot of its final state.

The inspection system freezes:

* identity;
* lineage;
* final body state;
* final genome;
* death tick.

This allows you to continue examining the individual after death.

The simulation moves on.

The microscope does not.

See [Inspection](inspection.md).

---

# 📉 Extinction

A lineage is extinct when it has no living individuals left.

The simulation does not automatically repopulate it.

Extinction may result from:

* ecological pressure;
* poor inherited behavior;
* unfavorable spatial distribution;
* excessive mutation;
* reproductive failure;
* environmental change;
* population collapse;
* stochastic history;
* or several of these at once.

Because ecological relations are cyclic, losing one lineage can also radically alter the environment experienced by the remaining two.

Removing one participant from a non-transitive system changes the game itself.

Extinction is therefore not just:

```text
population = 0
```

It can be an ecosystem-level transition.

---

# 📈 What does “evolution is working” mean?

This question deserves care.

Evolution is not equivalent to:

```text
population goes up
```

Nor is it equivalent to:

```text
score goes up forever
```

The simulation contains several observable signals:

* lineage population;
* lifetime;
* generation depth;
* HP;
* composite score;
* encounters;
* exploration;
* reproductive success;
* spatial organization;
* behavioral patterns.

A population may adapt by becoming:

* longer-lived;
* more reproductively successful;
* better at finding allies;
* better at avoiding enemies;
* better at exploiting environmental zones;
* less prone to overcrowding;
* or some combination of these.

But stochastic variation can also produce temporary trends.

One run is a story.

Repeated controlled runs are evidence.

This distinction becomes important once you begin treating Primordial Soup as an experimental system rather than an animated screensaver.

See [Experiments](experiments.md).

---

# 🧪 Emergence

No rule explicitly says:

```text
form a colony
```

or:

```text
avoid blue
```

or:

```text
stay near environmental zones
```

Yet patterns resembling those strategies may appear.

That is what makes artificial-life systems interesting.

Simple local rules can produce complicated population-level outcomes.

But there is an important warning.

Humans are extremely good at seeing intention.

If a critter repeatedly moves toward green individuals, it is tempting to say:

> “It likes green.”

The simulation supports a more careful statement:

> “Its inherited neural dynamics currently produce movement correlated with local green density.”

Less romantic.

Much harder to misinterpret.

Emergent behavior should be measured whenever possible rather than explained only through visual intuition.

---

# 🔬 What this simulation is not

Primordial Soup is not:

* a realistic model of biological evolution;
* a model of animal cognition;
* a model of real genetics;
* a model of real ecosystems;
* evidence that neural networks resemble biological brains in detail;
* evidence that an observed behavior is intentional;
* a universal definition of evolutionary fitness.

Its abstractions are intentionally compact.

For example:

```text
HP
```

stands in for survival pressure.

```text
genome
```

stores neural parameters.

```text
crossover
```

combines numerical genomes.

```text
mutation
```

perturbs those parameters.

```text
composite score
```

implements a configurable selection pressure.

These constructs borrow vocabulary and ideas from biology, artificial life and evolutionary computation.

They should not be confused with biological equivalence.

---

# 🧠 Then what is Primordial Soup useful for?

Primordial Soup is useful as a compact laboratory for exploring questions such as:

* How does selection pressure change population behavior?
* How much mutation is too much?
* Can simple neural controllers evolve useful movement policies?
* What happens when cooperation and competition coexist?
* What happens when an environment changes after adaptation?
* Can spatial structure protect populations?
* How does reproductive gating change evolutionary dynamics?
* What patterns emerge from non-transitive interactions?
* How stable are apparent adaptations across random seeds?
* How does inherited neural structure interact with short-term recurrent state?

It is also useful for studying the engineering of simulations themselves:

* reproducibility;
* state persistence;
* vectorized computation;
* deterministic experimentation;
* visualization;
* inspection tooling;
* evolutionary metrics.

So the project sits somewhere between:

```text
simulation
+
software engineering
+
evolutionary computation
+
artificial life
+
“what happens if I change this number?”
```

The final category is historically responsible for a significant amount of science.

---

# 🧭 The complete lifecycle

Putting everything together:

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

That is Primordial Soup.

A small set of explicit rules.

A large number of possible histories.

And absolutely no guarantee that the critters will behave sensibly.

---

## Where to go next

To understand how selection, reproductive gates, crossover and mutation work in detail:

→ [Evolution](evolution.md)

To understand how to follow individual critters:

→ [Inspection](inspection.md)

To design controlled comparisons:

→ [Experiments](experiments.md)

To change the laws described here:

→ [Configuration](configuration.md)

To understand how all of this maps onto Python and NumPy:

→ [Architecture](architecture.md)
