# 🔍 Inspection

Populations are useful for statistics. Individuals are useful for
understanding what the statistics are hiding.

The inspection system lets you follow one critter through the
simulation, examine its state and neural genome, watch where it goes,
and preserve its final state if it dies.

Two central ideas:

```text
DISCOVERY
"Who looks interesting?"

OBSERVATION
"Who am I actually watching?"
```

These are deliberately different things.

Changing your search does not move your microscope.

---

# Focusing Inspection

Press:

```text
I
```

to focus the Inspection panel.

The lateral panel is always drawn on the right side of the window: its
horizontal strip is structurally reserved by the layout, so it never
covers part of the simulated habitat.

Focusing Inspection does **not** automatically observe any critter, and
does **not** replace an existing observation.

Observation is always an explicit action. Triggered by:

* selecting **Observe candidate** in the Inspection panel and pressing
  **Enter**;
* clicking a critter directly in the world.

Leaving Inspection — with **ESC**, with **Tab**, or by focusing another
panel — does **not** end the active observation either. The stable
critter ID remains selected, and the trail keeps being updated while
the observed critter is alive.

Only the visual overlay specific to Inspection — candidate marker,
observed/death marker and trail — is drawn when Inspection is the
focused panel.

To end an observation explicitly:

```text
Inspection
↓
Clear observation
↓
Enter
```

---

# 🔭 Discovery

Discovery answers:

> Given this criterion and lineage filter, which living critter is the
> current candidate?

It is a query over the current population. It does not create persistent
simulation state.

```text
current population
       +
criterion
       +
lineage filter
       ↓
discovery candidate
```

There is exactly **one** discovery candidate at a time. Or none.

## Criterion — ENUM

Select **Criterion** with **↑ / ↓**, change with **← / →**.

Current criteria:

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

Changing the criterion recalculates the candidate. It does **not**
change the observed individual.

## Lineage filter — ENUM

Select **Lineage filter** with **↑ / ↓**, change with **← / →**.

Values cycle through `all, R, G, B`.

With `criterion = oldest` and `filter = B`, the candidate is the oldest
living blue critter.

If the selected lineage is extinct, there may be **no candidate**. Your
current observation remains untouched.

## Candidate — read-only

The **Candidate** item displays the current candidate. It is read-only:
it does not participate in the navigation cycle for **Enter**, and it
does not change anything.

## 🟡 The yellow marker

The discovery candidate is marked in the world with a **yellow
Moore-neighborhood outline**.

There is exactly one yellow candidate marker.

```text
yellow marker
=
candidate shown in the panel
=
critter Observe candidate + Enter will observe
```

## 👁️ Observe candidate — action

Select **Observe candidate** and press **Enter** to replace the current
observation with the discovery candidate.

```text
DISCOVERY

criterion: most offspring
lineage:   G
candidate: G #903

          │ Observe candidate + Enter
          ▼

OBSERVING

G #903
```

This is an explicit transition.

If discovery has no candidate, the action does nothing to the current
observation.

## 🖱️ Click — observe directly

Left-click near an individual.

If the click hits a critter:

```text
clicked critter
      ↓
becomes observed
Inspection panel is focused
```

The lookup includes a small spatial tolerance because each critter
occupies very little screen space. The current tolerance is four world
cells.

Clicks are accepted regardless of pause state and regardless of which
panel is focused.

If the click misses every critter, it is a no-op: the existing
observation remains unchanged.

---

# 👁️ Observation

Observation represents the specific individual currently under study.

Unlike discovery, observation is based on a **stable critter ID**.

For example:

```text
R #1847
```

does not mean "the critter currently at position 1847 in an array". It
means the individual whose permanent identity is 1847.

## Why stable identity matters

Population arrays change as critters die and newborns are added.

Imagine a population array:

```text
index 0 → #40
index 1 → #41
index 2 → #42
index 3 → #43
```

Then critter `#41` dies. After compaction:

```text
index 0 → #40
index 1 → #42
index 2 → #43
```

If inspection stored `index = 2`, you would suddenly be observing
`#43`. Instead Primordial Soup stores `critter_id = 42` and resolves
its current position when needed.

Arrays may move. Identity stays put.

## 🔷 The cyan marker

The observed critter is marked in **cyan**.

Living observed critter:

```text
cyan Moore outline
```

So:

```text
yellow = discovery candidate
cyan   = observed critter
```

If both refer to the same individual, cyan is rendered on top. You see
only cyan. That means "the critter I am observing is also the current
discovery candidate". Not "yellow mysteriously disappeared".

## ☠️ What happens when the observed critter dies

Nothing is automatically selected in its place.

```text
observed critter dies
        ↓
capture final snapshot
        ↓
freeze observation
        ↓
do NOT auto-select replacement
```

Death ends the individual's simulation. It does not end your inspection
session.

## The death snapshot

Immediately before the observed individual is removed from the living
population, Primordial Soup captures:

* stable critter ID;
* lineage;
* death tick;
* final agent state;
* final genome.

These are actual copies. They are not references to array rows that may
later be reused or compacted.

So after death:

```text
living population changes
        ↓
snapshot remains intact
```

The autopsy survives the cleanup crew.

## ✚ The cyan death marker

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

The shape, rather than the color, communicates the state.

This works across the toroidal boundary. A critter dying at the world's
edge does not receive half a gravestone.

## Status in the panel

The observation section shows whether the individual is `alive` or
`dead at tick N`.

For a living critter, panel values are read from its current state. For
a dead critter, the preserved body state and genome come from the death
snapshot.

## ⚠️ Vision after death

The death snapshot preserves the critter and its genome, but it does
not capture an entire historical copy of the surrounding world.

For a dead observed individual, the vision panel is reconstructed
around its **last known position using the current world state**. It
should not be interpreted as "exactly what the critter saw at the
instant of death".

Capturing historical world perception would require a different
snapshot contract.

## 🧵 The trail

While a living critter is being observed, Primordial Soup records its
position after each tick.

The trail shows where that individual has traveled since the observation
began.

```text
oldest                                   newest

· · · · · · · · ●
dark                 →                 bright
```

Grayscale. Older positions are darker, newer positions are brighter.

The trail is not a continuous geometric line. In the toroidal world,
two adjacent cells can appear on opposite sides of the screen. The
trail records points, not a connected line.

## When does the trail reset

The trail belongs to the **observation session**, not permanently to
the critter.

It is cleared when observation changes:

```text
nothing → #42
fresh trail

#42 → #91
fresh trail

#91 → nothing
trail cleared
```

Selecting the same ID again does not discard its trail.

Changing only **Criterion** or **Lineage filter** also does not reset
the trail — discovery did not change who you are observing.

## Trail across panels

The trail is preserved across panel focus changes. If you focus another
panel and return to Inspection later, the trail is still there.

Only the drawing is gated by the focused panel. The trail keeps being
appended while the observed critter is alive.

## Trail after death

Once the observed individual dies, its stable ID no longer resolves to
a living population entry. No new trail points are added.

The trail remains frozen at the path accumulated before death, paired
with the cyan death marker at its final position.

---

# 🧠 Vision panel and brain heatmaps

The inspection panel includes an **11 × 11** view centered on the
observed critter's position. This mirrors the local spatial information
used by the neural controller.

The world contains three lineage density channels. The panel converts
them into an RGB representation so you can inspect the local ecological
context.

This shows inputs. It does not tell you which features the neural
network considered important.

Below it, the panel displays heatmaps representing parts of the
observed critter's genome.

| Heatmap | Meaning                            |
| ------- | ---------------------------------- |
| **W1**  | Input → first hidden layer         |
| **W2**  | First hidden → second hidden layer |
| **W3**  | Second hidden → output             |
| **b1**  | First hidden-layer biases          |
| **b2**  | Second hidden-layer biases         |
| **R**   | Recurrent weights                  |

These are useful for comparing individuals, comparing generations,
spotting very different genomic structures, and inspecting a dead
individual's final inherited controller.

A colored stripe is not an explanation. Neural networks rarely provide
subtitles.

---

# 🧪 A useful inspection workflow

```text
1. pause
2. focus Inspection (I)
3. select a discovery criterion
4. select a lineage filter
5. select Observe candidate, press Enter
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

Ask: Does it survive unusually well? Does it cluster near allies? Does
it move frequently? Does it avoid certain regions? How old is it? How
many encounters? Has it reproduced? What happens immediately before it
loses HP?

Inspection turns population statistics into individual case studies.

---

# 🔬 Discovery as a scientific lens

Each criterion asks a different question about the same population.

```text
oldest              → who has survived longest?
highest generation  → who sits deepest in the genealogy?
most encounters     → who has experienced the most contact?
most explored       → who accumulated the most movement?
lowest HP           → who is closest to ecological trouble?
```

No single lens defines "the best critter".

---

# Observation does not affect evolution

Inspection is a **view** over the simulation.

Changing criterion, filter, observed critter or panel state does not
alter the critter's neural network, HP, reproduction eligibility or
ecological interactions.

The trail itself is also visualization state.

The organisms do not know they are being watched.

---

# No automatic replacement

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

For exploratory visualization that might seem convenient. For analysis
it is misleading.

Primordial Soup prefers:

```text
#100 dies
↓
freeze #100
↓
you decide what to observe next
```

The same rule applies when focusing Inspection: focusing the panel does
not change the observed critter.

---

# The inspection state machine

```text
                I / focus Inspection
                         │
                         ▼
               ┌─────────────────┐
               │ DISCOVERY QUERY │
               │ (criterion +    │
               │  lineage filter)│
               └────────┬────────┘
                        │
                        ▼
                discovery candidate
                        │
                        ├───────────────┐
                        │               │
                 Observe candidate    click
                     + Enter            │
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
                     Observe candidate + Enter,
                     or click
                              │
                              ▼
                    observe another ID
```

At any point:

```text
Inspection
↓
Clear observation
↓
Enter
```

ends the observation.

Changing the focused panel does not.

---

# Visual language

| Visual                           | Meaning                                |
| -------------------------------- | -------------------------------------- |
| **Yellow outline**               | Current discovery candidate            |
| **Cyan outline**                 | Living observed critter                |
| **Cyan cross**                   | Dead observed critter at last position |
| **Dark → light grayscale trail** | Observed movement history              |
| **R / G / B colors**             | Lineage presence                       |
| **Brain heatmaps**               | Neural genome components               |

The important relationship:

```text
YELLOW
"What would Observe candidate choose?"

CYAN
"What am I watching?"
```

All of these overlays are drawn only when the Inspection panel is the
focused panel. The underlying observation state is preserved when
another panel is focused.

---

# Common misunderstandings

**"I pressed → and my observed critter didn't change."**

Correct. You changed discovery. Select **Observe candidate** and press
**Enter** to observe the new candidate.

**"The yellow and cyan markers are on different critters."**

Correct. You are observing one individual while discovery recommends
another.

**"I only see cyan, but there should also be a yellow candidate."**

If the observed individual **is** the discovery candidate, cyan is drawn
over yellow. One critter, two roles, one visible marker.

**"The observed critter died but the panel still shows it."**

Correct. You are looking at its death snapshot.

**"Why didn't inspection move to another critter after death?"**

Because that would change the subject of your observation without
permission. Use **Observe candidate + Enter**, or click another
individual, when you are ready.

**"I changed the lineage filter and nothing happened to observation."**

Exactly. The filter belongs to discovery.

**"I focused another panel and the trail disappeared."**

The trail's drawing is gated by the focused panel: it is only rendered
when Inspection is focused. The trail itself is preserved, and it keeps
being appended while the observed critter is alive. Return to Inspection
with **I** to see it again.

**"I closed inspection and lost the trail."**

There is no "close inspection" action in the current interface. The
Inspection panel is always present in the right sidebar. What changes is
which panel is focused. To end an observation and discard its trail, use
**Clear observation**.

---

# Why this design

Four principles:

```text
identity must be stable
selection changes must be explicit
discovery must not mutate observation
death must not fake continuity
```

The interface can answer two questions independently:

```text
Who is interesting?
Who was I studying?
```

Those questions often have different answers. That is not a bug. That is
the reason the inspection system exists.

---

# Related documentation

→ [Simulation](simulation.md)
→ [Controls](controls.md)
→ [Evolution](evolution.md)
→ [Experiments](experiments.md)
→ [Architecture](architecture.md)
