# 🧬 Primordial Soup

<p align="center">
  <img src="primordial_soup/icon.png" alt="Primordial Soup" width="128">
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-0.6.0-blue">
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white">
  <img alt="UI" src="https://img.shields.io/badge/UI-English%20%7C%20PT--BR-555555">
</p>

**An artificial-life aquarium where tiny neural critters perceive, move, hunt, reproduce, mutate, and occasionally make spectacularly poor evolutionary decisions.**

You do not control them.

You define the universe, press **SPACE**, and watch what happens.

Sometimes evolution looks clever.

Sometimes a promising lineage solves its problems by repeatedly walking into danger.

Science is like that.

---

<p align="center">
  <img src="primordial_soup.gif" alt="Primordial Soup running — critters moving, hunting, and evolving on the toroidal world" width="720">
</p>

---

## What is Primordial Soup?

**Primordial Soup** is an artificial-life simulation populated by autonomous critters whose behavior is controlled by small inherited recurrent neural networks.

Every critter can:

* perceive nearby members of all three lineages;
* sense part of its own internal state;
* choose one of nine movement actions;
* explore the world;
* encounter predators and prey;
* gain and lose HP;
* survive environmental pressure;
* reproduce when eligible;
* pass a recombined and potentially mutated genome to descendants;
* accumulate a measurable evolutionary history;
* and eventually die.

There is no player-controlled creature and no predefined winning strategy.

The experiment is the interaction between **neural behavior, inheritance, ecology, selection pressure, spatial structure, and time**.

> 🧠 **Primordial Soup does not train its critters. It replaces them.**
>
> No gradient descent is required. Selection, inheritance, mutation, and death handle the optimization.
>
> Being alive is merely the first interview.

---

## 📚 Documentation

The README is the quick introduction.

The actual rules of the universe live here:

| Document                                           | Purpose                                                                               |
| -------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [World Rules](docs/world-rules.md)                 | Ecology, predation, overcrowding, nests, zones, death, reproduction and genetic rules |
| [Critters and Brains](docs/critters-and-brains.md) | Perception, recurrent neural network, genome, movement and stable identity            |
| [Runtime Configuration](docs/runtime-config.md)    | HOT rules, defaults, limits and live experimental controls                            |
| [Persistence](docs/persistence.md)                 | Checkpoints, deterministic continuation, stable IDs, RNG state and compatibility      |
| [User Interface](docs/ui.md)                       | Panels, navigation, Inspection, controls and operator interaction                     |
| [Architecture](docs/architecture.md)               | Modules, state ownership, tick lifecycle, boundaries and architectural invariants     |

A useful reading order is:

```text
README
  ↓
World Rules
  ↓
Critters and Brains
  ↓
Runtime Configuration
  ↓
Persistence
  ↓
User Interface
  ↓
Architecture
```

If you only want to understand the experiment, start with **World Rules**.

If you want to modify the code without accidentally inventing a second universe, read **Architecture**.

---

## 🧠 The critter brain

Each critter sees an **11×11 local window** with one perception channel for each lineage:

```text
Red
Green
Blue
```

Four additional inputs describe internal state.

That produces:

```text
363 visual inputs
+ 4 internal inputs
---------------------
367 total inputs
```

The brain is a small recurrent neural network:

```text
367 inputs
    ↓
25 hidden neurons
    ↺ recurrent state
    ↓
12 hidden neurons
    ↓
9 movement outputs
```

The nine outputs correspond to the Moore neighborhood: eight directions plus staying in place.

All neural weights, biases, and recurrent weights live inside the critter's genome:

```text
10,245 genes
```

The network is evaluated during life.

It is **not trained during life**.

What changes across generations is the genome.

Machine learning:

```text
improve the model
```

Primordial Soup:

```text
let the model die
and give its children slightly different weights
```

For the complete organism model, see [Critters and Brains](docs/critters-and-brains.md).

---

## 🌍 One tick in the universe

Every simulation tick follows a fixed lifecycle:

```text
perceive
   ↓
decide
   ↓
move
   ↓
resolve ecology
   ↓
apply HP / encounters / deaths
   ↓
reproduce if a lineage owns this turn
   ↓
update the world
   ↓
record metrics
```

Ecological effects are resolved from the same post-movement world snapshot before deaths are applied.

This matters.

A critter does not get to survive an interaction merely because another array happened to be processed first.

That would not be evolution.

That would be a scheduling bug wearing a lab coat.

The complete ecological specification is in [World Rules](docs/world-rules.md).

---

## 🔴 🟢 🔵 Three lineages

The world contains three lineages:

| Predator | Prey     |
| -------- | -------- |
| 🔴 Red   | 🟢 Green |
| 🟢 Green | 🔵 Blue  |
| 🔵 Blue  | 🔴 Red   |

Predation occurs when predator and prey occupy the same cell.

The prey loses HP.

The predator gains the transferred HP.

If several predators share the cell, the reward is divided between them.

Same-lineage overcrowding is a separate pressure and damages organisms sharing a cell with too many members of their own lineage.

There is no HP ceiling.

Successful predators may accumulate considerably more HP than they started with.

Chaos is allowed to keep its earnings.

---

## 🪺 Nests

Each lineage owns exactly one persistent nest.

Nests have two jobs:

```text
predator refuge
+
birthplace for descendants
```

A critter inside its own nest is protected from predators.

It is **not** protected from overcrowding.

Nests do not:

* grant HP;
* change metabolism;
* alter perception;
* modify score;
* improve genetics;
* increase reproduction probability.

Founders begin at random positions.

Descendants are born near their lineage's nest.

A nest is geography.

Not a spa.

---

## 🧬 Reproduction and evolution

Reproduction is selective rather than automatic.

Potential parents must pass runtime-configurable gates involving:

```text
age
HP
composite score
encounters
```

Eligible organisms are ranked and a reproductive pool is formed.

Two parents are selected.

Their genomes undergo crossover, producing two complementary descendants, after which mutation may alter the inherited neural parameters.

Available crossover strategies include:

```text
blocks
uniform
two points
```

Mutation supports:

```text
two scales
surgical
```

The two-scale model allows smaller local perturbations and rarer, larger exploratory mutations.

New descendants receive stable IDs, begin a new generation, and spawn at their lineage's nest.

> Two parents are intentional.
>
> Sexual reproduction with only one parent would require considerably more theological documentation.

For exact reproduction, mutation and ecological rules, see [World Rules](docs/world-rules.md).

---

## ⚙️ Change the rules while it runs

A large part of the experiment can be modified without restarting the simulation.

The **Configuration** panel exposes HOT rules for:

* genetics;
* crossover;
* mutation;
* behavior;
* metabolism;
* predation;
* overcrowding;
* environmental zones;
* reproduction;
* parent selection;
* fitness scoring.

Runtime changes are validated before replacing the active rule set.

The point is not to discover one sacred configuration.

The point is to create different selection pressures and see what survives them.

Defaults, ranges and exact semantics are documented in [Runtime Configuration](docs/runtime-config.md).

---

## 🔬 Inspection and metrics

Primordial Soup is designed to be observed, not merely watched.

The interface contains five panels:

| Key | Panel             | Purpose                                     |
| --- | ----------------- | ------------------------------------------- |
| `I` | **Inspection**    | Find and observe individual critters        |
| `C` | **Configuration** | Change runtime rules                        |
| `M` | **Metrics**       | Inspect population and evolutionary metrics |
| `S` | **Session**       | Save, load, or create a world               |
| `T` | **Tools**         | Language, recording and diagnostics         |

Inspection tracks critters using stable IDs rather than array positions.

You can inspect information such as:

```text
HP
age
generation
encounters
offspring
score
position
vision
neural weights
trajectory
```

If the observed critter dies, its final inspection state is preserved.

Death terminates the organism.

It does not invalidate the paperwork.

The Metrics panel tracks:

```text
population
average HP
longest lifetime
maximum generation
average composite score
mutation rate
```

See [User Interface](docs/ui.md) for the complete interaction model.

---

## 🎮 Controls

| Key                 | Action                         |
| ------------------- | ------------------------------ |
| `SPACE`             | Play / pause                   |
| `=` or `+`          | Advance exactly one tick       |
| `F11`               | Toggle fullscreen              |
| `Ctrl+mouse wheel`  | Zoom world at cursor           |
| `Ctrl+0`            | Reset world zoom               |
| `I C M S T`         | Focus a panel                  |
| `Tab` / `Shift+Tab` | Cycle panels                   |
| `↑ ↓`               | Navigate panel items           |
| `← →`               | Change a value                 |
| `Enter`             | Activate / observe             |
| `Esc`               | Return to world / request exit |
| `R`                 | Create a new world             |
| `Z`                 | Toggle environmental zones     |
| `H`                 | Toggle floating HUD            |
| `G`                 | Start / stop GIF recording     |
| `N`                 | Cycle save slot                |
| `Ctrl+S`            | Save                           |
| `Ctrl+L`            | Load                           |
| `P`                 | Print simulation state         |

The graphical interface supports:

```text
English
Portuguese (Brazil)
```

---

## ▶️ Running Primordial Soup

Primordial Soup requires **Python 3.12 or newer**.

From the repository root:

```bash
python -m pip install -e .
python -m primordial_soup
```

No arguments means graphical mode.

Then press:

```text
SPACE
```

The universe has been informed.

### Nix / NixOS

A development flake is included:

```bash
nix develop
python -m primordial_soup
```

Or:

```bash
nix run .
```

---

## 🧪 Headless experiments

The same simulation can run without opening a Pygame window.

Create a deterministic world, simulate 10,000 ticks, and save it:

```bash
python -m primordial_soup \
  --new \
  --seed 42 \
  --duration 10000 \
  --save world_a
```

Continue the same world for another 5,000 ticks:

```bash
python -m primordial_soup \
  --load world_a \
  --duration 5000
```

Headless mode is useful for:

```text
batch experiments
reproducible seeds
parameter studies
CI smoke tests
long evolutionary runs
```

Graphical and headless execution use the same simulation core and checkpoint format.

---

## 💾 Persistence

Primordial Soup saves complete simulation checkpoints.

A checkpoint preserves the state required to continue the same stochastic history, including:

```text
critters
genomes
stable IDs
runtime rules
tick counters
reproduction scheduler
environmental zones
nest geometry
Python RNG state
NumPy RNG state
```

This is deliberate.

A checkpoint is supposed to continue the same universe — not reconstruct something that merely resembles it.

> 💾 **Save the world.**
>
> **The universe that comes back is the same universe that went in.**

The current checkpoint contract is:

```text
save version 21
```

For validation, compatibility and atomic load/save behavior, see [Persistence](docs/persistence.md).

---

## 🏗️ Architecture

Primordial Soup has one simulation core shared by graphical and headless execution.

The canonical tick is owned by:

```text
simulation.step()
```

Major responsibilities are intentionally separated:

```text
senses       → perception
brain        → neural evaluation
movement     → spatial movement
ecology      → ecological resolution
evolution    → reproduction
genetics     → crossover and mutation
world        → population and spatial representation
state        → active universe state
persistence  → checkpoints
rendering    → pixels
```

Some boundaries are treated as hard architectural invariants:

```text
rendering does not advance the simulation

UI state does not change physics

ecology is resolved from a frozen snapshot

population arrays remain in lockstep

stable identity is independent of array position

RuntimeRules is immutable

fresh-world construction has one authority
```

Developers should read [Architecture](docs/architecture.md) before changing lifecycle or module responsibilities.

The critters are already allowed to behave unpredictably.

The dependency graph is not.

---

## 🧪 Tests

Run the test suite with:

```bash
python -m pytest tests/ -v
```

On Nix:

```bash
nix flake check
```

Artificial life may be chaotic.

The test suite should not be.

---

## License

Primordial Soup is released under the **MIT License**.

---

## 🙏 Acknowledgements

Primordial Soup was inspired by
[**Neuroparticles**](https://github.com/xcontcom/neuroparticles)
by [Serhii Herasymov](https://github.com/xcontcom) — a smaller
artificial-life experiment that showed how far a 9-output neural
network, uniform crossover and random mutation can go on a toroidal
grid.

The idea of building a larger universe around those same principles
came directly from that project.

---

**Primordial Soup is not trying to prove that evolution is intelligent.**

It is providing a world where evolution has enough room to demonstrate whatever it has in mind.
