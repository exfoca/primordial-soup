# 🧠 Critters and Brains

A critter is the smallest autonomous organism in Primordial Soup.

It has a body, a genome, a small recurrent neural network, a little memory, and absolutely no idea that any of this has been documented.

Its lifecycle is simple:

```text
perceive → think → move → survive → reproduce, maybe → die, eventually
```

The interesting behavior comes from repeating that loop across many organisms and generations.

---

## 🧬 What makes a critter?

Every living critter belongs to exactly one lineage:

```text
R — Red
G — Green
B — Blue
```

It also carries two different kinds of state.

**Inherited state** is the genome: the neural parameters received from its parents and potentially modified by mutation.

**Lifetime state** belongs only to the individual:

* HP;
* position;
* age;
* generation;
* last action;
* low-HP state;
* recurrent hidden state;
* explored cells;
* encounters;
* offspring count;
* composite score.

Most of this state is **not** visible to the neural network.

The organism knows considerably less about itself than the Inspection panel does.

---

## 👁️ Perception

Each critter observes an **11×11** square centered on its current position.

The world is toroidal, so vision wraps around its edges just like movement.

There are three visual channels:

```text
Red population
Green population
Blue population
```

Each cell contains the number of critters from that lineage occupying that position.

The visual input therefore contains:

```text
11 × 11 × 3 = 363 values
```

The critter can see population density around itself, including organisms sharing the same cell.

It does not receive a semantic label saying:

```text
that one is food
that one wants to eat you
```

It receives numbers.

Evolution may eventually discover the rest.

---

## 🫀 Internal state

Four additional values are appended to vision:

| Input         | Meaning                                                   |
| ------------- | --------------------------------------------------------- |
| `hp_norm`     | current HP / initial HP                                   |
| `time_norm`   | age / initial HP                                          |
| `action_norm` | previous action / 8                                       |
| `low_hp`      | `1` when HP is below the runtime threshold, otherwise `0` |

That gives:

```text
363 visual inputs
+ 4 internal inputs
---------------------
367 neural inputs
```

`INITIAL_HP` is used as a normalization scale, not as a maximum.

Because HP has no upper cap:

```text
hp_norm > 1
```

is perfectly valid.

A successful predator can therefore become healthier than the value historically known as “full health.”

The universe refuses to call this an error.

---

## 🚫 What the brain does not see

There are deliberately no direct neural inputs for:

```text
nest membership
environmental zones
generation
encounter count
offspring count
composite score
mutation rate
selection criterion
```

Nests and zones affect the world, but they are not announced directly to the neural network.

If a lineage develops behavior that exploits them, it must do so through consequences and inherited behavior rather than a convenient `YOU_ARE_INSIDE_NEST = 1` signal.

Primordial Soup provides an environment.

It does not provide tooltips.

---

# 🧠 Neural architecture

## The network

Every critter uses the same neural architecture:

```text
367 inputs
    │
    ▼
25 hidden neurons ──↺ recurrent state
    │
    ▼
12 hidden neurons
    │
    ▼
9 outputs
```

Both hidden layers use:

```text
tanh
```

The output layer is:

```text
linear
```

The recurrent connection exists on the first hidden layer.

This gives the organism a small amount of temporal memory: the current decision can depend not only on current perception, but also on hidden activity from the previous tick.

It is not consciousness.

But it is enough to make debugging behavior considerably more entertaining.

---

## 🧠 Memory

After each neural evaluation, the 25 values from the first hidden layer become the critter's recurrent state for the next tick.

Conceptually:

```text
current perception
      +
previous hidden state
      ↓
current decision
      +
new hidden state
```

The **recurrent weights are genetic**.

The **hidden state is not**.

Every newborn begins with its recurrent memory filled with zeros.

Children inherit the machinery capable of remembering.

They do not inherit their parents' memories.

That would make family therapy part of the simulation architecture.

---

# 🧬 The genome

## Neural parameters as genes

A genome is a flat `float32` vector containing all trainable parameters of the brain:

```text
input → hidden1 weights
hidden1 → hidden2 weights
hidden2 → output weights
hidden1 biases
hidden2 biases
recurrent weights
```

Current genome size:

```text
10,245 genes
```

Those genes are decoded into the neural network when the critter thinks.

There is no separate learned model stored elsewhere.

The genome **is** the model.

---

## No backpropagation

Critters never update their neural weights during life.

There is:

```text
no loss function
no gradient
no optimizer
no training epoch
```

A critter is born with a network and lives with it.

If that network produces useful behavior, the organism may survive long enough to reproduce.

Its descendants receive recombined and possibly mutated versions of the parental genomes.

If the behavior is terrible, another mechanism performs model retirement.

> **Primordial Soup does not train its creatures. It replaces them.**
>
> The death rate handles optimizer feedback with unusual finality.

---

# 🎯 Decision

For every living critter, each tick:

```text
perception
    ↓
recurrent neural network
    ↓
9 output values
    ↓
argmax
    ↓
movement action
```

The output with the highest value wins.

Before selection, the center output may receive the runtime-configurable:

```text
stay_still_impulse
```

This allows the experiment to bias organisms toward or away from remaining still without changing their genomes.

The network still decides among the resulting nine scores.

---

# 🧭 Movement

The nine actions correspond directly to the 3×3 Moore neighborhood:

```text
0  1  2
3  4  5
6  7  8
```

Spatially:

```text
↖  ↑  ↗
←  •  →
↙  ↓  ↘
```

Action `4` means:

```text
stay still
```

Movement wraps around world boundaries.

A critter leaving one edge enters from the opposite edge.

There are no corners to hide in because, topologically speaking, there are no corners.

---

## Exploration

Whenever the chosen action changes the critter's cell:

```text
cells_visited += 1
```

Choosing the center action does not count as exploration.

This is an activity counter, not a unique-cell set.

Returning to somewhere previously visited still counts as another movement event.

The simulation rewards movement history, not cartographic achievement.

---

# 🪪 Identity

Array positions are temporary.

Critter identity is not.

Every organism receives a globally allocated stable integer ID.

IDs are monotonically allocated from the world's next-ID counter:

```text
1
2
3
4
...
```

When organisms die, population arrays are compacted.

The survivors may move to different array indices, but their IDs remain unchanged.

Therefore:

```text
array index ≠ identity
```

This distinction matters for inspection, tracking, persistence, and death snapshots.

A selected critter is followed by ID, not by whichever unfortunate organism later occupies row 17.

---

## Founders and newborns

Founders begin with:

```text
generation      = 0
age             = 0
encounters      = 0
offspring       = 0
exploration     = 0
composite score = 0
hidden state    = 0
last action     = stay still
```

Their positions are random.

Newborns receive the same zeroed lifetime state, except for their inherited generation and their spawn position inside their lineage's nest.

Their genome comes from their parents.

Their memories do not.

---

# 🔬 Observation

Inspection deliberately sees more than the critter does.

An observed organism can expose information such as:

```text
stable ID
lineage
HP
age
generation
offspring
encounters
composite score
last action
position
vision
neural parameters
trajectory
```

Observation does not influence the organism.

Selecting a critter does not alter its decisions, score, perception, survival, or reproduction.

The scientist may stare.

The specimen remains gloriously indifferent.

If the observed critter dies, Primordial Soup captures its final state before population compaction removes it.

Death ends simulation activity.

It does not erase the last observation.

---

# 🔒 Core invariants

For the current critter model:

```text
367 neural inputs
25 recurrent hidden neurons
12 second-layer hidden neurons
9 movement outputs
10,245 genes

vision = 11 × 11 × 3
internal state = 4 inputs

hidden memory starts at zero
genome is inherited
lifetime neural state is not inherited

decision = argmax(outputs)
movement is toroidal
identity is stable across compaction
```

These values define the current cognitive architecture.

Changing them is not merely tuning the environment.

It changes the organism itself.

---

## Final note

A critter has no explicit concept of predator, prey, nest, environmental zone, fitness, lineage strategy, or evolutionary purpose.

It sees local populations and a tiny piece of itself.

Then a neural network emits a number between zero and eight.

Everything else is consequence.

> They are not told how to survive.
>
> They are given enough information to make a decision.
>
> The world grades the decision.
