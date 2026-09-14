# 🐣 Getting Started

Install → run → unpause → watch → inspect → experiment.

You can learn what everything means afterward.

The interface separates **global commands** (always active), **panel
activation** (each key focuses a panel), and **contextual navigation**
(inside the focused panel). This guide uses that model.

---

## 1. Requirements

* Python 3.12+
* NumPy
* Pygame

GIF recording additionally uses Pillow.

With Nix, the development environment handles dependencies.

---

## 2. Install

### Python

```bash
pip install .
python -m primordial_soup
```

GIF recording optional:

```bash
pip install .[recording]
```

### Nix

```bash
nix develop .
python -m primordial_soup
```

Or:

```bash
nix run .
```

---

## 3. Nothing is moving. Good.

The simulation starts **paused**.

Press:

```text
SPACE
```

Critters begin moving.

You have created an ecosystem and immediately abandoned it to natural
selection.

---

## 4. Watch before touching anything

For your first run, resist changing parameters.

Let the simulation run for a while. Watch where populations concentrate,
whether lineages spread or cluster, whether some regions become crowded,
whether population sizes rise or fall, whether the charts begin
developing trends.

A useful first run is a few thousand ticks.

---

## 5. Pause time

```text
SPACE
```

again freezes the world.

To advance carefully:

```text
=
```

or:

```text
+
```

Each press advances exactly one simulation tick.

---

## 6. Inspect a critter

Press:

```text
I
```

to focus the Inspection panel.

Focusing the panel does not automatically observe a critter. The panel
shows the current Discovery candidate and lets you choose who to
follow explicitly.

You can also click a critter with the mouse. A click on the world
focuses Inspection as a side effect.

The panel lets you examine an individual rather than treating the
population as anonymous colored pixels. Depending on its state, you can
inspect identity, lineage, HP, age, generation, offspring, encounters,
composite score, position, neural state, and local perception.

---

## 7. Discovery and observation

**Discovery** decides which critter currently looks interesting.

**Observation** decides which critter you are actually following.

Inside the Inspection panel:

* **Criterion** is an ENUM. Select with **↑ / ↓** and change with
  **← / →**.
* **Lineage filter** is an ENUM. Same.
* **Candidate** shows the discovery candidate. Read-only.
* **Observe candidate** is an ACTION. Select and press **Enter** to
  make the candidate the observed critter.

Changing discovery does not silently replace your observation.

To end an observation, select **Clear observation** and press **Enter**.

---

## 8. Follow one life

A good first experiment is following one critter:

1. Pause the simulation.
2. Press **I** to focus Inspection.
3. Choose a criterion and lineage filter, then select **Observe
   candidate** and press **Enter** (or click a critter directly).
4. Resume with **SPACE**.
5. Watch its trail and statistics.
6. Pause occasionally.
7. Advance individual ticks with **=**.

The observed individual has a stable identity. Its internal position may
change as other critters die; its identity does not. If it dies, its
final state remains available for inspection.

---

## 9. Look at the charts

Press:

```text
M
```

to focus the Metrics panel. Then select **Metric** and use **← / →**.

Different metrics answer different questions. Population size is not
the score of evolution. A small population can contain highly adapted
individuals. A large one can be unremarkable.

---

## 10. Change one thing

Runtime parameters go through the Configuration panel:

```text
C
↓
Configuration
↓
↑ / ↓ to select the item
↓
← / → to adjust
```

Available items:

```text
Simulation speed
Mutation rate
Local mutation scale
Environmental zones
Zone HP effect
Heal all critters
```

For your first experiment, change **only one parameter**. Otherwise, if
something interesting happens, you will have no idea why.

---

## 11. Try mutation

```text
C
↓
Configuration
↓
↑ / ↓ até Mutation rate
↓
← / →
```

Try three different worlds: low, medium, high mutation.

Watch for differences in survival, generation depth, behavioral
stability, population volatility, composite score.

Do not assume more mutation means faster evolution. Mutation creates
variation; selection decides whether it survives.

---

## 12. Turn refuges into traps

```text
C
↓
Configuration
↓
↑ / ↓ até Zone HP effect
↓
← / →
```

Adjust until the zone effect becomes negative. The same regions that
were beneficial become dangerous.

Toggle zones on or off with:

```text
Z
```

or through **Configuration → Environmental zones**.

---

## 13. Save an interesting world

```text
S
↓
Session
↓
Save now
↓
Enter
```

The current world is saved to the active save slot.

Cycle slots with the global:

```text
N
```

Load the active slot with the global:

```text
L
```

A simple experiment:

```text
world_a → low mutation
world_b → medium mutation
world_c → high mutation
```

---

## 14. Start over

```text
R
```

creates a fresh run. The current population is discarded. Operator
tunings (mutation, speed, language, pause) are preserved.

A useful habit:

```text
change one condition
      ↓
R
      ↓
run experiment
      ↓
record observations
```

---

## 15. Record what happened

```text
G
```

starts GIF recording. Press **G** again to stop.

Requires Pillow:

```bash
pip install .[recording]
```

---

## 16. Speed things up

Speed is adjusted through the Configuration panel:

```text
C
↓
Configuration
↓
Simulation speed
↓
← / →
```

Fast execution is useful for long evolutionary periods. Slow execution
is useful for observation. Single-step execution is useful when you
have stopped trusting reality.

---

## 17. Your first structured experiment

### Question

Does mutation rate affect how quickly the population reaches deeper
generations?

### Run A

1. New run with **R**.
2. Set a low mutation rate via Configuration.
3. Run for a fixed number of ticks.
4. Record maximum generation and population.

### Run B

1. New run with **R**.
2. Increase mutation.
3. Run for the same number of ticks.
4. Record the same metrics.

### Compare

Ask which run reached deeper generations, which maintained a larger
population, which had higher average scores, whether either lineage
went extinct, whether behavior appeared more stable.

Do not draw strong conclusions from two runs. Random systems enjoy
humiliating small sample sizes.

For reproducible experiments, use the headless mode with a fixed seed.

See [Headless](headless.md).

---

## 18. Headless mode in one minute

```bash
python -m primordial_soup --new -d 10000 -s world_a --seed 42
```

This creates a fresh world, uses random seed `42`, runs 10,000 ticks,
saves to `world_a`, exits.

Load that world graphically later and inspect the population.

See [Headless](headless.md) for the complete guide.

---

## 19. Controls you should remember

### Global commands

| Key       | Remember this              |
| --------- | -------------------------- |
| **SPACE** | Start / stop time          |
| **= / +** | One tick                   |
| **R**     | New world                  |
| **L**     | Load the active save slot  |
| **N**     | Change save slot           |
| **P**     | Print state                |
| **Z**     | Toggle zones               |
| **G**     | Record GIF                 |
| **H**     | Show / hide floating HUD   |
| **F11**   | Fullscreen                 |
| **ESC**   | Back to world or quit      |

### Panel activation

| Key   | Focus         |
| ----- | ------------- |
| **I** | Inspection    |
| **C** | Configuration |
| **M** | Metrics       |
| **S** | Session       |
| **T** | Tools         |

### Inside a focused panel

| Key           | Remember this                          |
| ------------- | -------------------------------------- |
| **Tab**       | Next panel                             |
| **Shift+Tab** | Previous panel                         |
| **↑ / ↓**     | Move the cursor                        |
| **← / →**     | Adjust the selected VALUE / ENUM       |
| **Enter**     | Activate the selected ACTION / TOGGLE  |

### Mouse

| Input          | Remember this                       |
| -------------- | ----------------------------------- |
| **Left click** | Observe the critter under the cursor |
| **Wheel**      | Scroll the lateral panel            |

For every control and its exact behavior, see [Controls](controls.md).

---

## 20. Where to go next

→ [Simulation](simulation.md) — what the creatures are
→ [Evolution](evolution.md) — selection, reproduction, mutation
→ [Inspection](inspection.md) — the inspection tools
→ [Experiments](experiments.md) — proper experiments
→ [Configuration](configuration.md) — laws of the universe
→ [Architecture](architecture.md) — the NumPy machinery

---

## One final warning

After a while you may catch yourself saying things like:

> "Red seems to have developed a preference for the northern refuge."

At that point, remember:

* the world is toroidal;
* there is no north;
* the critters have no idea you exist;
* and you have probably been watching them for too long.

Welcome to Primordial Soup.
