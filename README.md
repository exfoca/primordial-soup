# 🧬 Primordial Soup

<p align="center">
  <img src="primordial_soup/icon.png" alt="Primordial Soup" width="128">
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-0.5.0-blue">
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg">
  <img alt="Python" src="https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white">
  <img alt="Idioma" src="https://img.shields.io/badge/🇧🇷_code-PT--BR-009C3B">
</p>

![Primordial Soup](primordial_soup.gif)

**An artificial-life aquarium where tiny neural critters see, move, interact, reproduce, mutate, and occasionally make terrible evolutionary decisions.**

You do not control them.

You build the universe, define its rules, press **SPACE**, and watch what happens.

Sometimes evolution looks clever.

Sometimes an entire lineage walks into a hazardous zone.

Science is like that.

---

## What is Primordial Soup?

**Primordial Soup** is an artificial-life simulation populated by autonomous critters with small neural networks.

Each critter can:

* perceive the local world around it;
* process that information through its own neural network;
* decide where to move;
* interact with allies and enemies;
* gain or lose HP;
* explore the environment;
* reproduce when eligible;
* pass its genome to descendants;
* accumulate mutations across generations;
* and, eventually, die.

There is no player-controlled creature and no predefined winning strategy.

The interesting part is watching behavior emerge from simple rules, inheritance, environmental pressure, and a lot of numerical linear algebra.

> 🧠 The critters do not learn through backpropagation. Their neural networks are inherited. Evolution does the optimization — slowly, noisily, and without reading the documentation.

---

## The universe in 20 seconds

Every simulation tick roughly follows this cycle:

```text
        perceive
           ↓
          think
           ↓
          move
           ↓
        interact
           ↓
    gain / lose HP
           ↓
      survive / die
           ↓
       reproduce
      when eligible
           ↓
        inherit
           ↓
         mutate
```

The world is **toroidal**. Walk through the right edge and you return on the left. Leave through the bottom and you reappear at the top.

Three lineages — **R**, **G**, **B** — coexist in a non-transitive ecological cycle. No lineage has a permanent universal advantage.

Add environmental zones, mutation, selection pressure and finite populations, and the result becomes surprisingly difficult to predict.

Which is precisely the point.

---

## 🐣 Run it

### Python

```bash
pip install .
python -m primordial_soup
```

GIF recording is optional:

```bash
pip install .[recording]
```

### Nix

```bash
nix develop .
nix run .
```

The simulation starts **paused**.

Press:

```text
SPACE
```

Life begins.

---

## 🎮 Essential controls

The graphical interface has three layers:

* **global commands** — always active;
* **panel activation** — each key focuses a panel;
* **contextual navigation** — operates inside the focused panel.

### Global commands

| Key       | Action                              |
| --------- | ----------------------------------- |
| **SPACE** | Pause / resume                      |
| **= / +** | Advance exactly one tick            |
| **R**     | Create a completely new run         |
| **L**     | Load the active save slot           |
| **N**     | Cycle the active save slot          |
| **P**     | Print the current simulation state  |
| **Z**     | Toggle environmental zones          |
| **G**     | Start / stop GIF recording          |
| **H**     | Show / hide floating HUD            |
| **F11**   | Fullscreen                          |
| **ESC**   | Return to world focus, or quit      |

### Panel activation

Each key focuses the corresponding panel. It does not toggle the panel and it does not perform the panel's action directly.

| Key   | Panel         |
| ----- | ------------- |
| **I** | Inspection    |
| **C** | Configuration |
| **M** | Metrics       |
| **S** | Session       |
| **T** | Tools         |

### Inside a focused panel

| Key           | Action                                |
| ------------- | ------------------------------------- |
| **Tab**       | Next panel                            |
| **Shift+Tab** | Previous panel                        |
| **↑ / ↓**     | Move the cursor                       |
| **← / →**     | Adjust the selected VALUE / ENUM      |
| **Enter**     | Activate the selected ACTION / TOGGLE |
| **ESC**       | Return focus to the world             |

### Mouse

| Input          | Action                                       |
| -------------- | -------------------------------------------- |
| **Left click** | Observe the critter under the cursor, if any |
| **Wheel**      | Scroll the lateral panel                     |

See [Controls](docs/controls.md) for the complete reference.

---

## 🔍 Watch a critter

Press **I** to focus the Inspection panel.

The panel shows a **Discovery** candidate and lets you decide who to follow.

Two distinct ideas:

```text
DISCOVERY
"Who looks interesting right now?"

OBSERVATION
"Who am I actually following?"
```

You change **Discovery** by selecting **Criterion** or **Lineage filter** and using **← / →**.

You choose who to **Observe** by selecting **Observe candidate** and pressing **Enter**, or by clicking a critter in the world.

Changing discovery does not silently replace your observation.

Leaving Inspection does not end your observation either. The stable critter ID stays selected and the trail keeps accumulating. Only the visual overlay — candidate marker, observed marker, death marker, trail — is drawn when Inspection is focused.

To end an observation explicitly, use **Clear observation** in the Inspection panel.

If the observed critter dies, its final state is preserved. Death ends the critter. It does not end the autopsy.

See [Inspection](docs/inspection.md) for the full model.

---

## 🧠 Tiny brains, large consequences

Each critter carries its own neural-network genome.

Its inputs include information about:

* nearby lineage densities;
* its own internal state;
* its recent neural state.

Its outputs represent possible movements in the local neighborhood.

The network also carries a lightweight recurrent state, giving the critter a small amount of short-term memory.

There is no central controller telling individuals what to do.

Two genetically different critters standing in the same place may make completely different decisions.

See [Architecture](docs/architecture.md) for the implementation.

---

## 🧬 Evolution

Reproduction is not simply "alive → have children".

Individuals must satisfy reproductive conditions before they can become candidate parents. Selection takes survival, exploration, interaction and reproductive success into account.

Eligible parents contribute genomes to offspring through crossover, followed by mutation.

Over many generations this creates a feedback loop:

```text
behavior → ecological outcome → selection → reproduction
   → inheritance → mutation → new behavior
```

Populations can converge, specialize, oscillate, get stuck, or go extinct with impressive efficiency.

See [Evolution](docs/evolution.md).

---

## 🌍 Ecology

Three interacting lineages:

```text
R
G
B
```

Their relationships form a non-transitive cycle.

Environmental zones can be beneficial, neutral or harmful. A refuge can become a trap while the simulation is running.

Evolution receives no advance notice.

---

## 📈 What should I watch?

Do not look only at population size.

Useful signals: population by lineage, average HP, longest lifetime, maximum generation, average composite score, spatial clustering, extinction events, changes in the individuals selected by different inspection criteria.

A population surviving for a long time does not necessarily mean it is evolving in an interesting way.

Charts tell part of the story. Inspection tells another. Repeated experiments tell much more.

---

## 🧪 Try breaking evolution scientifically

A few good starting experiments:

* **Low mutation** — does the population stabilize around a small set of strategies?
* **High mutation** — does diversity help adaptation, or does inheritance become too noisy?
* **Environmental traps** — can populations evolve behavior that reduces exposure to dangerous regions?
* **Long runs** — do metrics keep improving, or does the system plateau?
* **Same seed, different rule** — was the difference caused by the parameter or by random history?

See [Experiments](docs/experiments.md).

---

## 🤖 Headless experiments

Primordial Soup can run without opening the graphical interface.

```bash
python -m primordial_soup --new -d 10000 -s world_a --seed 42
```

Continue an existing run:

```bash
python -m primordial_soup -l world_a -d 5000
```

A save produced headlessly can be opened later in the graphical simulation.

See [Headless experiments](docs/headless.md).

---

## 💾 Save, kill the universe, restore it

Four graphical save slots: `default`, `world_a`, `world_b`, `world_c`.

Cycled with **N**.

Save through **S → Session → Save now → Enter**.

Load the active slot with **L**.

Savegames are versioned because genomes, neural architectures and simulation state evolve together with the project. When the format changes incompatibly, Primordial Soup prefers rejecting an invalid world over quietly resurrecting it incorrectly.

See [Persistence](docs/persistence.md).

---

## 🧪 Primordial Soup is an experiment, not a biological model

The simulation borrows ideas from artificial life, evolutionary algorithms, neural networks, ecology, inheritance, mutation, selection, spatial interaction.

But it is intentionally simplified.

A critter is not an organism. HP is not metabolism. A neural matrix is not a biological brain. A few thousand generations in NumPy do not settle evolutionary biology.

The value of the project is a compact environment where complex population-level behavior can emerge from explicit rules that are easy to inspect, modify and experiment with.

---

## 📚 Documentation

| Document                                   | What it answers                                                 |
| ------------------------------------------ | --------------------------------------------------------------- |
| [Getting started](docs/getting-started.md) | How do I start without reading a textbook?                      |
| [Simulation](docs/simulation.md)           | What exactly is this universe and how does it work?             |
| [Controls](docs/controls.md)               | What does every key and runtime control do?                     |
| [Inspection](docs/inspection.md)           | How do discovery, observation, trails and death snapshots work? |
| [Evolution](docs/evolution.md)             | How do selection, reproduction, crossover and mutation work?    |
| [Experiments](docs/experiments.md)         | What interesting experiments can I run?                         |
| [Headless](docs/headless.md)               | How do I run reproducible batch simulations?                    |
| [Configuration](docs/configuration.md)     | Which laws of the universe can I change?                        |
| [Architecture](docs/architecture.md)       | How is the simulation implemented?                              |
| [Persistence](docs/persistence.md)         | What is saved, restored and versioned?                          |

A useful rule of thumb:

```text
README          → Why should I care?
Getting started → How do I run it?
Simulation      → What is happening?
Evolution       → Why does it change?
Experiments     → What should I test?
Architecture    → How is it implemented?
```

---

## 🛠️ Want to modify the universe?

Start with `docs/architecture.md` and `docs/configuration.md`.

The codebase separates the laws of the simulation from the machinery that executes them.

Otherwise you may accidentally discover a new law of nature called `regression`.

---

## In one sentence

**Primordial Soup is an artificial-life simulation where populations of tiny inherited neural networks perceive a toroidal world, interact, survive, reproduce and mutate while you observe the evolutionary consequences.**

Now go poke the soup.

🥣🧬

---

## 📜 License

Primordial Soup is licensed under the **MIT License**.

See [LICENSE](LICENSE).
