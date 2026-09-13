# 🐣 Getting Started

You found the primordial soup.

Now let's make something live in it.

This guide deliberately skips most of the theory. The goal is simple:

```text
install → run → unpause → watch → inspect → experiment
```

You can learn what everything means afterward.

Evolution will continue without waiting for you.

---

## 1. Requirements

Primordial Soup requires:

* Python 3.12+
* NumPy
* Pygame

GIF recording additionally uses Pillow.

If you use Nix, the development environment already handles the dependencies for you.

---

## 2. Install

### Python

From the project directory:

```bash
pip install .
```

If you also want GIF recording:

```bash
pip install .[recording]
```

Then run:

```bash
python -m primordial_soup
```

### Nix

Enter the development environment:

```bash
nix develop
```

Then run the simulation:

```bash
python -m primordial_soup
```

Or launch it directly:

```bash
nix run .
```

---

## 3. Nothing is moving. Good.

The simulation starts **paused**.

This is intentional.

Press:

```text
SPACE
```

The critters should begin moving.

Congratulations.

You have created an ecosystem and immediately abandoned it to natural selection.

---

## 4. Watch before touching anything

For your first run, resist the urge to change every parameter.

Let the simulation run for a while.

Watch:

* where populations concentrate;
* whether lineages spread or cluster;
* whether some regions become crowded;
* whether population sizes rise or fall;
* whether one lineage temporarily dominates;
* whether the charts begin developing visible trends.

You do not need to understand every number yet.

At first, just watch the system behave.

A useful first run is a few thousand ticks.

---

## 5. Pause time

Press:

```text
SPACE
```

again.

The world freezes.

If you want to advance carefully, one tick at a time:

```text
=
```

or:

```text
+
```

Each press advances exactly one simulation tick.

This is useful when inspecting individual behavior.

It is also useful when you want to stare intensely at a matrix of colored dots and call it research.

---

## 6. Inspect a critter

Press:

```text
I
```

The inspection panel opens.

Primordial Soup now selects a candidate for observation.

The panel lets you examine an individual rather than treating the population as anonymous colored pixels.

Depending on its current state, you can inspect information such as:

* identity;
* lineage;
* HP;
* age;
* generation;
* offspring;
* encounters;
* composite score;
* current position;
* neural state;
* local perception.

You can also click directly on a critter with the mouse to observe it.

---

## 7. Discovery and observation are different

This distinction is important.

**Discovery** decides which critter currently looks interesting.

**Observation** decides which critter you are actually following.

Use:

```text
← / →
```

to change the discovery criterion.

Use:

```text
Tab
```

to change the lineage filter.

These controls change the candidate.

They do **not** silently replace the individual you are already observing.

When you want to observe the current candidate, press:

```text
Enter
```

Conceptually:

```text
change criterion
      ↓
find candidate
      ↓
candidate highlighted
      ↓
press Enter
      ↓
observe that individual
```

Your microscope moves only when you tell it to.

---

## 8. Follow one life

A good first experiment is simply following one critter.

Try this:

1. Pause the simulation.
2. Press **I**.
3. Choose a critter.
4. Resume with **SPACE**.
5. Watch its trail and statistics.
6. Pause occasionally.
7. Advance individual ticks with **=** if something interesting happens.

The observed individual has a stable identity.

Its position inside internal arrays may change as other critters die, but its identity does not.

If the observed critter dies, Primordial Soup does not quietly replace it with someone healthier.

Its final state remains available for inspection.

Natural selection may be ruthless.

The debugger does not have to be.

---

## 9. Look at the charts

Press:

```text
M
```

to cycle through available chart metrics.

Do not treat one metric as “the score of evolution.”

Different metrics answer different questions.

Population might tell you:

> Is this lineage surviving?

Lifetime might tell you:

> Are individuals becoming better at staying alive?

Generation depth might tell you:

> Is reproduction continuing successfully?

Composite score might tell you:

> Are the traits rewarded by the current selection model improving?

A population can be large without being particularly interesting.

A small population can contain highly adapted individuals.

Context matters.

---

## 10. Change one thing

Now you are allowed to interfere.

Primordial Soup exposes several parameters that can be changed while the simulation is running.

The general pattern is:

```text
select parameter
      ↓
adjust with ↑ / ↓
```

For example:

* **U** selects mutation rate;
* **O** selects local mutation scale;
* **E** selects environmental-zone HP effect.

Then use:

```text
↑
↓
```

to change the selected value.

For your first experiment, change **only one parameter**.

Otherwise, if something interesting happens, you will have no idea why.

Scientists call this controlling variables.

Programmers call it avoiding a debugging nightmare.

---

## 11. Try mutation

Press:

```text
U
```

Mutation rate becomes the active parameter.

Use:

```text
↑ / ↓
```

to change it.

Try three different worlds:

```text
low mutation
medium mutation
high mutation
```

Observe whether you see differences in:

* survival;
* generation depth;
* behavioral stability;
* population volatility;
* composite score.

Do not assume that more mutation means faster evolution.

Mutation creates variation.

Selection decides whether that variation survives.

Too little mutation can reduce exploration.

Too much mutation can destroy useful inherited structure.

Evolution lives somewhere between boredom and chaos.

---

## 12. Turn refuges into traps

Environmental zones can affect HP.

Press:

```text
E
```

Then use:

```text
↓
```

until the zone effect becomes negative.

Now the same regions that may once have been beneficial become dangerous.

Watch whether populations:

* continue entering them;
* avoid them accidentally;
* eventually produce individuals that spend less time there;
* suffer population collapse.

You changed one environmental pressure.

Evolution gets the complaint form later.

Use:

```text
Z
```

to toggle environmental zones on or off.

---

## 13. Save an interesting world

If something worth keeping happens, press:

```text
S
```

The current world is saved to the active save slot.

Primordial Soup provides multiple slots.

Press:

```text
N
```

to cycle through them.

A simple experimental workflow is:

```text
world_a → low mutation
world_b → medium mutation
world_c → high mutation
```

Then use:

```text
L
```

to load the active slot.

This makes it possible to revisit interesting evolutionary histories instead of relying on:

> “I swear something amazing happened ten minutes ago.”

---

## 14. Start over

Press:

```text
R
```

to create a fresh run.

This is not the same as loading a save.

The current population is discarded and a new evolutionary history begins.

Use this frequently when comparing experiments.

A useful habit is:

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

Press:

```text
G
```

to begin GIF recording.

Press **G** again to stop.

The simulation writes:

```text
primordial_soup.gif
```

GIF recording requires the optional Pillow dependency:

```bash
pip install .[recording]
```

Useful for:

* documenting experiments;
* comparing runs;
* showing strange emergent behavior;
* proving that the blue lineage really did something ridiculous.

---

## 16. Speed things up

Use:

```text
.
```

to increase simulation speed.

Use:

```text
,
```

to decrease it.

Fast execution is useful for long evolutionary periods.

Slow execution is useful for observation.

Single-step execution is useful when you have stopped trusting reality.

---

## 17. Your first structured experiment

Try this before changing anything more complicated.

### Question

Does mutation rate affect how quickly the population reaches deeper generations?

### Run A

1. Start a new run with **R**.
2. Set a low mutation rate.
3. Let it run for a fixed number of ticks.
4. Record maximum generation and population.

### Run B

1. Start another new run.
2. Increase mutation.
3. Run for the same number of ticks.
4. Record the same metrics.

### Compare

Ask:

* Which run reached deeper generations?
* Which maintained a larger population?
* Which had higher average scores?
* Did either lineage go extinct?
* Did behavior appear more stable in one run?

Do not draw strong conclusions from two runs.

Random systems enjoy humiliating small sample sizes.

For reproducible experiments, use the headless mode with a fixed seed.

See [Headless experiments](headless.md).

---

## 18. Headless mode in one minute

You do not need the graphical interface for long experiments.

For example:

```bash
python -m primordial_soup --new -d 10000 -s world_a --seed 42
```

This:

* creates a fresh world;
* uses random seed `42`;
* runs 10,000 ticks;
* saves the result to `world_a`;
* exits.

Later, load that world graphically and inspect the population.

Headless execution is the preferred approach for reproducible experiments and parameter comparisons.

See [Headless](headless.md) for the complete guide.

---

## 19. The controls you should remember

If you forget everything else:

| Key           | Remember this               |
| ------------- | --------------------------- |
| **SPACE**     | Start / stop time           |
| **= / +**     | One tick                    |
| **I**         | Inspect                     |
| **Click**     | Observe this critter        |
| **Enter**     | Observe discovery candidate |
| **← / →**     | Change discovery criterion  |
| **Tab**       | Filter discovery by lineage |
| **M**         | Change chart                |
| **U / O / E** | Select adjustable parameter |
| **↑ / ↓**     | Change selected parameter   |
| **Z**         | Toggle zones                |
| **S / L / N** | Save / load / slot          |
| **R**         | New world                   |
| **G**         | Record GIF                  |
| **ESC**       | Quit                        |

For every control and its exact behavior, see [Controls](controls.md).

---

## 20. Where to go next

If you want to understand **what the creatures actually are**:

→ [Simulation](simulation.md)

If you want to understand **selection, reproduction and mutation**:

→ [Evolution](evolution.md)

If you want to master the inspection tools:

→ [Inspection](inspection.md)

If you want ideas for proper experiments:

→ [Experiments](experiments.md)

If you want to change the laws of the universe:

→ [Configuration](configuration.md)

If you want to understand the NumPy machinery underneath everything:

→ [Architecture](architecture.md)

---

## One final warning

After a while you may catch yourself saying things like:

> “Red seems to have developed a preference for the northern refuge.”

At that point, remember:

* the world is toroidal;
* there is no north;
* the critters have no idea you exist;
* and you have probably been watching them for too long.

Welcome to Primordial Soup.
