# 🔍 Inspection

Populations are useful for statistics.

Individuals are useful for understanding what the statistics are hiding.

The inspection system lets you follow one critter through the simulation, examine its state and neural genome, watch where it goes, and preserve its final state if it dies.

The central idea is simple:

```text
DISCOVERY
asks:
"Who looks interesting?"

OBSERVATION
asks:
"Who am I actually watching?"
```

These are deliberately different things.

Changing your search does not move your microscope.

---

# Opening inspection

Press:

```text
I
```

to enable inspection mode.

The inspection panel appears on the right side of the window.

That space is permanently reserved by the world layout, so the panel never covers part of the simulated habitat.

When inspection opens, Primordial Soup starts a new observation session:

```text
open inspection
      ↓
clear previous observation session
      ↓
find current discovery candidate
      ↓
observe that candidate
      ↓
start a fresh trail
```

The candidate is determined by the currently selected:

* discovery criterion;
* lineage filter.

On a normal fresh run, this means inspection begins with the default discovery lens.

Press **I** again to close inspection.

Closing the panel also ends the observation session and clears its trail.

---

# The two halves of inspection

The panel is conceptually divided into:

```text
┌────────────────────────────┐
│         INSPECTION         │
│                            │
│ DISCOVERY                  │
│ Who would I observe next?  │
│                            │
│ OBSERVING                  │
│ Who am I following now?    │
└────────────────────────────┘
```

The distinction is more important than it may initially appear.

Suppose you are observing:

```text
R #1847
```

Then you change discovery to:

```text
criterion = oldest
lineage   = G
```

Primordial Soup may find:

```text
candidate = G #903
```

But your observed critter remains:

```text
R #1847
```

until you explicitly choose otherwise.

That lets you search the population without losing the individual you were already studying.

---

# 🔭 Discovery

Discovery continuously answers:

> Given this criterion and lineage filter, which living critter is the current candidate?

It is a **view of the current population**.

It does not create persistent simulation state.

The model is:

```text
current population
       +
criterion
       +
lineage filter
       ↓
discovery candidate
```

There is exactly **one** discovery candidate at a time.

Or none.

---

# ← / → — choose a criterion

While inspection mode is active:

```text
←
```

moves to the previous discovery criterion.

```text
→
```

moves to the next.

The current set contains ten criteria.

| Criterion              | Candidate                  |
| ---------------------- | -------------------------- |
| **most evolved**       | Highest composite score    |
| **oldest**             | Greatest age               |
| **youngest**           | Lowest age                 |
| **most offspring**     | Greatest offspring count   |
| **most encounters**    | Greatest encounter count   |
| **most explored**      | Greatest exploration count |
| **highest HP**         | Highest HP                 |
| **lowest HP**          | Lowest HP                  |
| **highest generation** | Deepest generation         |
| **best score**         | Highest composite score    |

The panel displays the current position in the criterion cycle, for example:

```text
[4/10] most offspring
```

Changing the criterion recalculates the candidate.

It does **not** change the observed individual.

---

# Tab — filter by lineage

Press:

```text
Tab
```

to cycle the discovery filter:

```text
all
 ↓
R
 ↓
G
 ↓
B
 ↓
all
```

With:

```text
criterion = oldest
filter    = all
```

the candidate is the oldest critter across the entire population.

With:

```text
criterion = oldest
filter    = B
```

the candidate is the oldest living blue critter.

If the selected lineage has gone extinct, there may be:

```text
no candidate
```

Your current observation remains untouched.

Extinction does not automatically redirect the microscope toward the survivors.

---

# 🟡 The yellow marker

The discovery candidate is marked in the world with a **yellow Moore-neighborhood outline**.

Conceptually:

```text
· · ·
· X ·
· · ·
```

The eight surrounding cells form the outline around the candidate.

There is exactly one yellow candidate marker.

This gives the interface an important invariant:

```text
yellow marker
=
candidate shown in the panel
=
critter Enter will observe
```

What you see is what **Enter** selects.

No hidden second definition of “best.”

No three different champions competing for UI semantics.

Evolution is complicated enough already.

---

# 👁️ Observation

Observation represents the specific individual currently under study.

Unlike discovery, observation is based on a **stable critter ID**.

For example:

```text
R #1847
```

does not mean:

```text
the critter currently at position 1847 in an array
```

It means:

```text
the individual whose permanent identity is 1847
```

This distinction matters because population arrays change as critters die and newborns are added.

The internal position of an individual may change.

Its identity does not.

---

# Why stable identity matters

Imagine a population array:

```text
index 0 → #40
index 1 → #41
index 2 → #42
index 3 → #43
```

Then critter `#41` dies.

After compaction:

```text
index 0 → #40
index 1 → #42
index 2 → #43
```

If inspection stored:

```text
index = 2
```

you would suddenly be observing `#43`.

The microscope would have switched organisms without telling you.

Instead Primordial Soup stores:

```text
critter_id = 42
```

and resolves its current position when needed.

Arrays may move.

Identity stays put.

---

# Enter — observe the discovery candidate

Press:

```text
Enter
```

to replace the current observation with the discovery candidate.

For example:

```text
DISCOVERY

criterion: most offspring
lineage:   G
candidate: G #903

          │
          │ ENTER
          ▼

OBSERVING

G #903
```

This is an explicit transition.

If discovery has no candidate, **Enter** does nothing to the current observation.

---

# 🖱️ Click — observe directly

You can bypass discovery and choose a critter spatially.

Left-click near an individual.

If the click hits a critter:

```text
clicked critter
      ↓
becomes observed
```

The lookup includes a small spatial tolerance because each critter occupies very little screen space.

The current tolerance is four world cells.

Nobody should need competitive-FPS mouse accuracy to conduct artificial-life research.

---

## Clicking with inspection closed

If the simulation is paused, a click can open inspection automatically.

The sequence is:

```text
click
  ↓
open inspection session
  ↓
establish normal initial candidate
  ↓
try to select clicked critter
```

If the click successfully finds a critter, that individual becomes observed.

If the click misses, the automatically established observation remains.

An empty click does not mean:

```text
please forget everything
```

---

## Clicking while running

When inspection mode is already active, you may click critters while the simulation is running.

This works.

It is also a good way to discover that moving one-cell organisms are harder to click than expected.

Pause with **SPACE** when precision matters.

---

# 🔷 The cyan marker

The observed critter is marked in **cyan**.

For a living observed critter:

```text
cyan Moore outline
```

surrounds its current position.

So:

```text
yellow = discovery candidate
cyan   = observed critter
```

If both refer to the same individual, the cyan marker is rendered on top.

You then see only cyan.

That means:

> The critter I am observing is also the current discovery candidate.

Not:

> Yellow mysteriously disappeared.

---

# ☠️ What happens when the observed critter dies?

Nothing is automatically selected in its place.

This is deliberate.

Older inspection behavior could silently replace a dead observed individual with another candidate.

That makes continuous observation misleading.

You think you followed one life.

In reality the interface quietly handed you somebody else's biography.

The current rule is:

```text
observed critter dies
        ↓
capture final snapshot
        ↓
freeze observation
        ↓
do NOT auto-select replacement
```

Death ends the individual's simulation.

It does not end your inspection session.

---

# The death snapshot

Immediately before the observed individual is removed from the living population, Primordial Soup captures a snapshot containing:

* stable critter ID;
* lineage;
* death tick;
* final agent state;
* final genome.

The agent state includes values such as:

* HP;
* position;
* age;
* generation;
* last action;
* neural recurrent state;
* exploration;
* encounters;
* offspring;
* composite score.

The genome is copied as well.

These are actual copies.

They are not references to array rows that may later be reused or compacted.

So after death:

```text
living population changes
        ↓
snapshot remains intact
```

The autopsy survives the cleanup crew.

---

# ✚ The cyan death marker

A dead observed critter is shown differently from a living one.

Living:

```text
cyan outline
```

Dead:

```text
cyan cross
```

centered on its last known position.

Conceptually:

```text
  +
+ X +
  +
```

The shape, rather than the color, communicates the state.

This works even across the toroidal boundary.

A critter dying at the world's edge does not receive half a gravestone.

---

# Status in the panel

The observation section shows whether the individual is:

```text
alive
```

or:

```text
dead at tick N
```

For a living critter, panel values are read from its current state.

For a dead critter, the preserved body state and genome come from the death snapshot.

That means values such as final:

* HP;
* age;
* generation;
* offspring;
* encounters;
* score;
* last action;
* position;
* genome weights;

remain available after death.

---

# ⚠️ Vision after death

There is one subtle distinction.

The death snapshot preserves the **critter and its genome**, but it does not capture an entire historical copy of the surrounding world.

Therefore, for a dead observed individual, the vision panel is reconstructed around its **last known position using the current world state**.

It should not be interpreted as:

> exactly what the critter saw at the instant of death.

Its final body and genome are frozen.

The entire universe is not.

Capturing historical world perception would require a different snapshot contract.

---

# 🧵 The trail

While a living critter is being observed, Primordial Soup records its position after each tick.

The result is a trail showing where that individual has traveled since the observation began.

Conceptually:

```text
oldest                                   newest

· · · · · · · · ●
dark                 →                 bright
```

The trail uses grayscale.

Older positions are darker.

Newer positions are brighter.

This gives a rough visual indication of direction without introducing another lineage-like color into the world.

---

# Why grayscale?

The simulation already assigns semantic meaning to:

```text
red
green
blue
```

for lineages.

It also uses:

```text
amber
```

for environmental zones,

```text
yellow
```

for discovery,

and:

```text
cyan
```

for observation.

Making the trail purple, orange or radioactive pink would eventually turn the simulation into an evolutionary Christmas tree.

Neutral grayscale keeps it visually subordinate.

---

# The trail is not a continuous geometric line

The trail is a sequence of visited positions.

This matters because the world is toroidal.

Suppose a critter moves:

```text
x = world_width - 1
```

to:

```text
x = 0
```

Those cells are adjacent in the simulation.

They appear on opposite sides of the screen.

The trail therefore does not attempt to draw a giant line across the display.

It records points.

The torus remains mathematically continuous even when your monitor disagrees.

---

# When does the trail reset?

The trail belongs to the **observation session**, not permanently to the critter.

It is cleared when observation changes:

```text
nothing → #42
fresh trail

#42 → #91
fresh trail

#91 → nothing
trail cleared
```

Selecting the same ID again does not normally discard its trail.

Changing only:

* discovery criterion;
* discovery lineage filter;

also does not reset the trail.

Because discovery did not change who you are observing.

---

# Closing and reopening inspection

Pressing **I** to close inspection:

```text
ends observation
clears selection
clears trail
```

Opening inspection again starts a fresh analysis session.

Even if the same critter happens to become selected again:

```text
old trail is not resurrected
```

This prevents visual history from one inspection session leaking into another.

---

# Trail after death

Once the observed individual dies, its stable ID no longer resolves to a living population entry.

No new trail points are added.

The trail therefore remains frozen at the path accumulated before death.

This pairs naturally with the death marker:

```text
trail
   ↓
final position
   ↓
cyan cross
```

A small archaeological record of questionable neural decisions.

---

# 👁️ Vision panel

The inspection panel includes an:

```text
11 × 11
```

view centered on the observed critter's position.

This mirrors the local spatial information used by the neural controller.

The world contains three lineage density channels.

The panel converts them into an RGB representation so you can inspect the local ecological context around the critter.

This is useful for questions such as:

* Was an enemy nearby?
* Was the critter surrounded by allies?
* Was the area crowded?
* Was the behavior understandable from the local scene?
* Did two apparently similar decisions occur under different sensory conditions?

Remember, however:

```text
vision
≠
interpretation
```

The panel shows inputs.

It does not tell you which features the neural network considered important.

For that, things become considerably more neural-network-shaped.

---

# 🧠 Brain heatmaps

Below the individual state and vision window, the panel displays heatmaps representing parts of the observed critter's genome.

The current neural architecture contains:

| Heatmap | Meaning                            |
| ------- | ---------------------------------- |
| **W1**  | Input → first hidden layer         |
| **W2**  | First hidden → second hidden layer |
| **W3**  | Second hidden → output             |
| **b1**  | First hidden-layer biases          |
| **b2**  | Second hidden-layer biases         |
| **R**   | Recurrent weights                  |

These visualizations provide a compact fingerprint of the individual's inherited neural controller.

They are most useful for:

* comparing individuals;
* comparing generations;
* spotting very different genomic structures;
* inspecting a dead individual's final inherited controller.

They are not a direct explanation of behavior.

A colored stripe saying:

```text
large positive weight here
```

does not automatically translate to:

```text
this gene means "run from blue"
```

Neural networks rarely provide subtitles.

---

# What the observation panel reports

For the observed critter, the panel currently exposes:

```text
ID
lineage
status
HP
age / time
generation
offspring
encounters
composite score
last action
position
vision
brain heatmaps
```

This combines three levels of information.

---

## Identity

```text
ID
lineage
status
```

Answers:

> Who is this?

---

## Life history

```text
HP
age
generation
offspring
encounters
score
position
last action
```

Answers:

> What has happened to it?

---

## Controller

```text
vision
genome heatmaps
```

Answers:

> What information is around it, and what neural machinery is making decisions?

Together these let you move from:

> “That red dot is doing something weird.”

to:

> “Critter #1847, generation 12, low HP, high encounter count, currently surrounded by blue density, just chose action 7.”

Progress.

---

# 🧪 A useful inspection workflow

A good way to study behavior is:

```text
1. pause
2. open inspection
3. choose a discovery criterion
4. choose a lineage
5. press Enter
6. examine the critter
7. resume slowly
8. watch the trail
9. pause at interesting moments
10. single-step with =
```

For example:

```text
criterion = highest generation
lineage   = R
```

Then observe that candidate and ask:

* Does it survive unusually well?
* Does it cluster near allies?
* Does it move frequently?
* Does it avoid certain regions?
* How old is it?
* How many encounters has it accumulated?
* Has it reproduced?
* What happens immediately before it loses HP?

Inspection turns population statistics into individual case studies.

---

# 🔬 Discovery as a scientific lens

The criteria are not just convenient navigation.

They let you ask different questions about the same population.

For example:

```text
oldest
```

asks:

> Who has survived the longest?

```text
highest generation
```

asks:

> Which living individual sits deepest in the genealogy?

```text
most encounters
```

asks:

> Who has experienced the most inter-lineage contact?

```text
most explored
```

asks:

> Who accumulated the most movement-based exploration?

```text
lowest HP
```

asks:

> Who is currently closest to ecological trouble?

Each criterion creates a different lens.

No single lens defines “the best critter.”

---

# Most evolved vs best score

The current criterion list contains both:

```text
most evolved
```

and:

```text
best score
```

Both currently resolve through composite score.

This redundancy is part of the current interface contract.

They should not be interpreted as two independent fitness definitions.

If that semantic distinction changes in a future version, the documentation should change with it.

---

# Observation does not affect evolution

Inspection is designed as a **view** over the simulation.

Changing:

* criterion;
* lineage filter;
* observed critter;
* panel state;

does not alter the critter's neural network, HP, reproduction eligibility or ecological interactions.

The trail itself is also visualization state.

The organisms do not know they are being watched.

This is probably for the best.

---

# No automatic replacement

One design rule deserves repeating:

```text
THE OBSERVED CRITTER IS NEVER
SILENTLY REPLACED BECAUSE IT DIED
```

Why?

Because this:

```text
observe #100
#100 dies
automatically observe #237
```

creates a false continuity.

The panel still looks populated.

The trail may continue.

Statistics keep changing.

But the object of study changed.

For exploratory visualization that might seem convenient.

For analysis it is misleading.

Primordial Soup therefore prefers:

```text
#100 dies
↓
freeze #100
↓
you decide what to observe next
```

Explicit transitions are easier to reason about.

And considerably easier to debug.

---

# The inspection state machine

The system can be summarized as:

```text
                I / first valid session
                         │
                         ▼
               ┌─────────────────┐
               │ INSPECTION OPEN │
               └────────┬────────┘
                        │
                        ▼
                discovery candidate
                        │
                        ├───────────────┐
                        │               │
                      Enter           click
                        │               │
                        ▼               ▼
                 ┌─────────────────────────┐
                 │    OBSERVING ID #N      │
                 └────────────┬────────────┘
                              │
                      critter survives
                              │
                              ├──────────────→ continue
                              │
                         critter dies
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ DEATH SNAPSHOT FROZEN   │
                 └────────────┬────────────┘
                              │
                     Enter / valid click
                              │
                              ▼
                    observe another ID
```

At any point:

```text
I
```

can close the session.

---

# Visual language

A quick summary:

| Visual                           | Meaning                                |
| -------------------------------- | -------------------------------------- |
| **Yellow outline**               | Current discovery candidate            |
| **Cyan outline**                 | Living observed critter                |
| **Cyan cross**                   | Dead observed critter at last position |
| **Dark → light grayscale trail** | Observed movement history              |
| **R / G / B colors**             | Lineage presence                       |
| **Brain heatmaps**               | Neural genome components               |

The important relationship is:

```text
YELLOW
"What would Enter choose?"

CYAN
"What am I watching?"
```

Once that distinction is understood, the inspection interface becomes much easier to read.

---

# Common misunderstandings

## “I pressed → and my observed critter didn't change.”

Correct.

You changed discovery.

Press **Enter** if you want to observe the new candidate.

---

## “The yellow and cyan markers are on different critters.”

Also correct.

You are observing one individual while discovery currently recommends another.

That is the intended model.

---

## “I only see cyan, but there should also be a yellow candidate.”

If the observed individual **is** the discovery candidate, cyan is drawn over yellow.

One critter.

Two roles.

One visible marker.

---

## “The observed critter died but the panel still shows it.”

Correct.

You are looking at its death snapshot.

This is intentional.

---

## “Why didn't inspection move to another critter after death?”

Because that would change the subject of your observation without permission.

Press **Enter** or click another individual when you are ready.

---

## “I changed the lineage filter and nothing happened to observation.”

Exactly.

The filter belongs to discovery.

---

## “I closed inspection and lost the trail.”

Correct.

Closing inspection ends that analysis session.

Trails are not permanent biographies.

---

## “The dead critter's vision changed later.”

Possible.

The snapshot preserves its final body state and genome, not a historical copy of the entire surrounding world.

The vision display is reconstructed around its last position.

---

# Why this design?

Inspection follows four principles:

```text
identity must be stable
selection changes must be explicit
discovery must not mutate observation
death must not fake continuity
```

Together they make the system suitable for actual analysis rather than only visual entertainment.

The interface can now answer two questions independently:

```text
Who is interesting?
```

and:

```text
Who was I studying?
```

Those questions often have different answers.

That is not a bug.

That is the reason the inspection system exists.

---

# Related documentation

To understand what the observed fields mean biologically:

→ [Simulation](simulation.md)

To learn the keyboard controls:

→ [Controls](controls.md)

To understand composite score and reproduction:

→ [Evolution](evolution.md)

To design experiments using inspection:

→ [Experiments](experiments.md)

To understand stable IDs, snapshots and rendering internally:

→ [Architecture](architecture.md)
