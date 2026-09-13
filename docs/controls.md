# 🎮 Controls

Primordial Soup is mostly autonomous.

The critters make their own decisions.

You control the laboratory.

That distinction is important.

The keyboard does not tell an individual where to move. Instead, it lets you:

* pause time;
* inspect individuals;
* alter experimental parameters;
* change environmental conditions;
* save worlds;
* record runs;
* and, when necessary, press **R** and pretend the previous ecosystem never happened.

---

## Quick reference

| Key            | Action                                  |
| -------------- | --------------------------------------- |
| **SPACE**      | Pause / resume                          |
| **= / +**      | Advance exactly one tick                |
| **R**          | Create a fresh run                      |
| **S**          | Save to the active slot                 |
| **L**          | Load the active slot                    |
| **N**          | Cycle the active save slot              |
| **P**          | Print the current simulation state      |
| **H**          | Reset every living critter's HP         |
| **I**          | Toggle inspection mode                  |
| **← / →**      | Cycle the discovery criterion           |
| **Tab**        | Cycle the discovery lineage filter      |
| **Enter**      | Observe the current discovery candidate |
| **Left click** | Observe a critter under the cursor      |
| **M**          | Cycle the chart metric                  |
| **U**          | Select mutation rate                    |
| **O**          | Select local mutation scale             |
| **E**          | Select environmental-zone HP effect     |
| **↑ / ↓**      | Adjust the selected parameter           |
| **, / .**      | Slow down / speed up                    |
| **Z**          | Toggle environmental zones              |
| **T**          | Change interface language               |
| **G**          | Start / stop GIF recording              |
| **F11**        | Toggle fullscreen                       |
| **ESC**        | Quit                                    |

If you remember only three keys:

```text
SPACE → control time
I     → inspect life
R     → admit the experiment got out of hand
```

---

# ⏯️ Time controls

## SPACE — pause / resume

Press:

```text
SPACE
```

to toggle the simulation between running and paused.

Primordial Soup starts paused.

When running, the simulation continually advances according to the current speed.

When paused, the world remains frozen while you:

* inspect individuals;
* change parameters;
* save;
* load;
* change the interface;
* or advance manually one tick at a time.

Pausing does not modify simulation state beyond stopping automatic advancement.

---

## = / + — advance one tick

Press:

```text
=
```

or:

```text
+
```

to advance exactly one simulation tick.

This works even while the simulation is paused.

It is especially useful for:

* inspecting neural state changes;
* following an individual near death;
* studying movement decisions;
* watching a reproductive event carefully;
* verifying environmental effects.

The operation is:

```text
current state
    ↓
one complete simulation tick
    ↓
redraw
```

Not half a tick.

Not one frame.

One full tick.

---

# ⏩ Simulation speed

Primordial Soup can execute multiple simulation ticks for each rendered frame.

Use:

```text
,
```

to slow down.

Use:

```text
.
```

to speed up.

Each press changes the speed multiplicatively:

```text
,  → ÷2
.  → ×2
```

The current allowed range is:

```text
1 to 256 ticks per frame
```

Typical progression:

```text
1
2
4
8
16
32
64
128
256
```

This changes **execution speed**, not simulation rules.

A tick at 256 ticks/frame obeys the same ecological mechanics as a tick at 1 tick/frame.

The difference is how many ticks are computed before the next rendered frame.

Use low speed when observing.

Use high speed when waiting for evolution to do something worth observing.

---

# 🔄 R — recreate the world

Press:

```text
R
```

to start a completely fresh run.

This discards the current population and constructs a new one.

A new run receives:

* a new initial population;
* new individual identities;
* new positions;
* new environmental zones;
* fresh simulation counters;
* a fresh reproductive-turn cycle.

This is **not** the same as loading a save.

Conceptually:

```text
R
↓
old evolutionary history discarded
↓
new run begins
```

Some operator preferences remain intact so that experiments can be repeated without reconfiguring the interface every time.

The previous organisms, however, are gone.

No memorial service is provided.

---

# 💾 Saving and loading

Primordial Soup provides four fixed save slots:

```text
default
world_a
world_b
world_c
```

The currently selected slot appears in the HUD.

---

## N — change save slot

Press:

```text
N
```

to cycle:

```text
default
   ↓
world_a
   ↓
world_b
   ↓
world_c
   ↓
default
```

Changing the slot does not save or load anything by itself.

It only changes the destination/source used by **S** and **L**.

Think of **N** as choosing the drawer.

**S** puts the universe into it.

**L** takes the universe back out.

---

## S — save

Press:

```text
S
```

to save the current simulation into the active slot.

A save captures persistent simulation state required to continue the run later.

For example:

```text
active slot = world_a

S
↓
save world_a
```

See [Persistence](persistence.md) for the exact save contract.

---

## L — load

Press:

```text
L
```

to load the active slot.

If loading succeeds:

* the saved world becomes the current world;
* the simulation is paused;
* the display is redrawn.

Pausing after load is intentional.

A restored ecosystem should not immediately run away while you are still trying to remember why you saved it.

If validation fails, the current runtime state is not replaced by a partially loaded world.

See [Persistence](persistence.md).

---

# 🖨️ P — print state

Press:

```text
P
```

to print a textual snapshot of the current simulation state to the terminal.

This is useful when:

* debugging;
* recording experiment conditions;
* comparing visible state with logs;
* working without staring exclusively at the HUD.

The graphical world remains unchanged.

---

# 💚 H — reset HP

Press:

```text
H
```

to reset the HP of **every living critter** to the configured initial HP.

This operation means:

```text
HP = INITIAL_HP
```

not:

```text
HP += INITIAL_HP
```

That distinction matters.

A critter below initial HP is healed.

A critter above initial HP is reduced back to the initial value.

The command does not modify:

* position;
* age;
* generation;
* genome;
* neural memory;
* encounter count;
* exploration count;
* offspring count.

It does not revive dead critters.

It does not recreate extinct lineages.

Once evolution deletes the last member of a lineage, **H** cannot manufacture genetics from nostalgia.

---

# 🔍 Inspection controls

Inspection has two separate concepts:

```text
DISCOVERY
Who looks interesting?

OBSERVATION
Who am I actually following?
```

Keeping these separate prevents changing a search criterion from silently replacing the individual under observation.

See [Inspection](inspection.md) for the full model.

---

## I — toggle inspection mode

Press:

```text
I
```

to open or close the inspection interface.

When inspection is enabled and no critter is currently observed, Primordial Soup automatically chooses an initial candidate.

Closing inspection removes the active observation session from the interface.

---

# 🔭 Discovery

Discovery controls select a **candidate**.

They do not automatically replace the critter currently being observed.

---

## ← / → — change discovery criterion

While inspection mode is active:

```text
←
```

selects the previous criterion.

```text
→
```

selects the next criterion.

The criteria currently cycle through:

```text
most evolved
oldest
youngest
most offspring
most encounters
most explored
highest HP
lowest HP
highest generation
best score
```

Conceptually:

```text
criterion
+
lineage filter
↓
discovery candidate
```

Changing the criterion asks a different question about the current population.

It does not move the microscope.

---

## Tab — change lineage filter

While inspection mode is active, press:

```text
Tab
```

to cycle:

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

The filter restricts discovery to the selected lineage.

For example:

```text
criterion = oldest
filter    = G
```

means:

> Find the oldest eligible green critter.

It does not mean:

> Immediately stop observing whoever I was watching and switch to green.

Discovery proposes.

Observation disposes.

---

## Enter — observe the candidate

Press:

```text
Enter
```

while inspection mode is active to adopt the current discovery candidate as the observed critter.

This is an explicit observation action.

```text
criterion + filter
        ↓
candidate #903
        ↓
      ENTER
        ↓
observe #903
```

If there is no candidate — for example because the selected lineage is extinct — no new observation is created.

---

# 🖱️ Mouse selection

A left click can directly select a critter under the cursor.

Clicks are accepted when:

* the simulation is paused; or
* inspection mode is already active.

The selection uses a small spatial tolerance, currently four world cells.

This makes it possible to select tiny individuals without requiring microsurgical mouse precision.

---

## First click

If inspection mode is off and the simulation is paused, the first accepted click enables inspection.

The system establishes its normal initial observation and then attempts to select the critter under the cursor.

If the click hits a critter:

```text
that critter becomes observed
```

If the click misses:

```text
the existing observation remains unchanged
```

A miss is not interpreted as:

> Please forget who I was studying.

---

## Clicking while running

When inspection mode is already active, clicks can select critters even while the simulation is running.

This is useful.

It is also substantially harder.

The critters move.

Your mouse does not evolve.

Pausing first is recommended when precision matters.

---

# 🧬 Runtime experiment parameters

Three simulation parameters can be adjusted interactively:

```text
mutation rate
local mutation scale
environmental-zone HP effect
```

The interface uses a two-stage control model:

```text
1. select parameter
2. adjust with ↑ / ↓
```

This avoids assigning a different pair of increase/decrease keys to every tunable variable.

---

# U — select mutation rate

Press:

```text
U
```

to make mutation rate the active parameter.

Then:

```text
↑ → +1 percentage point
↓ → -1 percentage point
```

Current range:

```text
0% to 100%
```

The initial mutation rate is:

```text
5%
```

Mutation is the active parameter when a new graphical run starts, so **↑ / ↓** already have a meaningful target before you press **U** manually.

At:

```text
0%
```

mutation is effectively disabled.

At:

```text
100%
```

every reproduction event eligible for mutation gets maximum probability of entering the mutation path.

Neither extreme is guaranteed to produce better adaptation.

One gives evolution very little novelty.

The other may give inheritance an identity crisis.

See [Evolution](evolution.md).

---

# O — select local mutation scale

Press:

```text
O
```

to make the local mutation scale the active parameter.

Then:

```text
↑ → increase by 1 percentage point
↓ → decrease by 1 percentage point
```

Current range:

```text
1% to 100%
```

This parameter controls how broad a local mutation is across the genome when the current mutation model uses local-scale mutation.

Roughly:

```text
small local scale
→ fewer genes affected
→ more surgical change

large local scale
→ more genes affected
→ broader perturbation
```

Mutation rate and mutation scale are different things.

One asks:

> How often does mutation happen?

The other asks:

> When it happens locally, how much of the genome does it touch?

Confusing those two variables is an excellent way to design an experiment whose results explain nothing.

---

# E — select environmental-zone HP effect

Press:

```text
E
```

to select the HP effect applied by environmental zones.

Then:

```text
↑ → +1 HP/tick
↓ → -1 HP/tick
```

Current range:

```text
-100 to +100 HP per tick
```

Interpretation:

```text
positive → beneficial zone
zero     → mechanically neutral zone
negative → hazardous zone
```

This can be changed during a running simulation.

For example:

```text
+20
```

turns zones into strong refuges.

Later:

```text
-20
```

turns the same geography into danger.

No creature receives advance warning.

---

# ↑ / ↓ — adjust active parameter

The arrow keys modify whichever parameter was most recently selected using:

```text
U
O
E
```

The HUD marks the currently active parameter.

So:

```text
U ↑ ↑ ↑
```

means:

```text
select mutation
increase mutation three times
```

while:

```text
E ↓ ↓ ↓
```

means:

```text
select zone HP effect
decrease it three times
```

The values stop at their configured limits.

Holding **↑** will not eventually produce:

```text
mutation = 847%
```

The universe retains some governance.

---

# 🌍 Z — toggle environmental zones

Press:

```text
Z
```

to enable or disable environmental zones.

This toggle affects both:

* visualization;
* mechanics.

When zones are off, their HP effect does not apply.

This is therefore not merely a display preference.

Conceptually:

```text
Z = OFF

zone geometry still exists
but
zone rendering disabled
and
zone HP effect disabled
```

Turning zones back on reactivates the existing zone geometry.

The zone mask is not destroyed by the toggle.

---

# 📈 M — change chart metric

Press:

```text
M
```

to cycle through the metrics shown by the chart.

The available metrics include measurements such as:

* population;
* average HP;
* longest lifetime;
* maximum generation;
* average composite score;
* mutation rate.

The chart is a view of simulation history.

Changing the displayed metric does not affect the ecosystem.

The critters remain blissfully unaware of analytics.

---

# 🌐 T — change language

Press:

```text
T
```

to cycle the user interface language:

```text
English ↔ Portuguese
```

The display redraws immediately, including while paused.

This changes presentation.

It does not translate the critters' thoughts.

There are no thoughts to translate.

Only matrices.

---

# 🎥 G — GIF recording

Press:

```text
G
```

to start recording frames.

Press:

```text
G
```

again to stop.

When recording ends, Primordial Soup writes the captured animation to the configured GIF file.

By default:

```text
primordial_soup.gif
```

Recording requires the optional Pillow dependency:

```bash
pip install .[recording]
```

Recording may also finish automatically when its configured frame budget is reached.

The simulation itself can continue after recording stops.

---

# 🖥️ F11 — fullscreen

Press:

```text
F11
```

to toggle fullscreen mode.

Fullscreen changes how the simulation is displayed.

It does not rebuild the world geometry or start a new run.

The existing world is scaled to fit while preserving its intended geometry.

Going fullscreen therefore does not create more habitat.

The critters do not receive free real estate because you bought a larger monitor.

---

# 🚪 ESC — quit

Press:

```text
ESC
```

to close the graphical simulation.

Unsaved state is not magically immortal.

If the current run matters:

```text
S first
ESC second
```

Civilizations have been lost to worse operational procedures.

---

# 🧪 Useful control sequences

Individual keys become more useful when thought of as small experimental workflows.

---

## Observe slowly

```text
SPACE    pause
I        inspect
click    choose critter
=        advance one tick
=        advance another
```

Useful for behavior analysis.

---

## Find an interesting individual

```text
I
→ →      choose criterion
Tab      choose lineage
Enter    observe candidate
```

Useful when searching by traits rather than position.

---

## Compare mutation regimes

```text
U
↓ / ↑   configure mutation
R       new run
.       accelerate
S       save result
```

Repeat under a different mutation setting.

---

## Turn a refuge into danger

```text
E
↓ ↓ ↓ ...
```

Continue until the zone HP effect becomes negative.

Then watch the ecology reconsider its life choices.

---

## Preserve three experimental conditions

```text
N → world_a
S

R
change parameter

N → world_b
S

R
change parameter

N → world_c
S
```

Now you have three worlds that can be revisited independently.

---

# 🧠 Controls vs simulation state

Not every control changes the same kind of state.

A useful mental model is:

| Category                | Examples        | Changes the simulation?        |
| ----------------------- | --------------- | ------------------------------ |
| Time                    | SPACE, =, +     | Yes                            |
| Experimental parameters | U/O/E + ↑/↓     | Yes                            |
| Environment             | Z               | Yes                            |
| Intervention            | H               | Yes                            |
| New run                 | R               | Replaces it                    |
| Persistence             | S, L, N         | Saves/restores/selects storage |
| Discovery               | ←, →, Tab       | No                             |
| Observation             | I, Enter, click | No                             |
| Analytics               | M               | No                             |
| Presentation            | T, F11          | No                             |
| Recording               | G               | No                             |

This distinction is useful when running controlled experiments.

For example:

```text
changing M
```

does not invalidate an experiment.

Changing:

```text
zone HP effect
```

certainly can.

---

# ⚠️ Common mistakes

## “I changed the criterion and the observed critter didn't change.”

Correct.

**← / →** change discovery.

Press **Enter** to observe the discovered candidate.

---

## “Tab doesn't switch my observed critter to another lineage.”

Also correct.

Tab changes the discovery filter.

Observation remains stable until an explicit observation action.

---

## “I pressed H and a strong critter lost HP.”

Correct.

**H resets HP to the initial value.**

It does not add HP.

---

## “I turned zones off but expected only the color to disappear.”

**Z disables the mechanic too.**

No zone HP effect is applied while zones are disabled.

---

## “I pressed N and nothing loaded.”

**N only changes the active slot.**

Use:

```text
L
```

after selecting the slot you want.

---

## “I increased the speed and evolution changed.”

The simulation rules did not change merely because rendering became less frequent.

However, if you manually intervene based on what you visually observe, running faster naturally changes how often *you* have an opportunity to intervene.

The critters are deterministic with respect to their simulation history.

The human operator is considerably less so.

---

# 📚 Related documentation

For the shortest introduction:

→ [Getting Started](getting-started.md)

For the distinction between discovery and observation:

→ [Inspection](inspection.md)

For mutation, crossover and reproduction:

→ [Evolution](evolution.md)

For save/load semantics:

→ [Persistence](persistence.md)

For every configurable law behind these controls:

→ [Configuration](configuration.md)
