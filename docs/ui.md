# 🖥️ User Interface

Primordial Soup is not a game about controlling critters.

The interface exists to do three things:

```text
observe
intervene
measure
```

The organisms remain autonomous.

You get the clipboard.

---

## Interface model

The graphical interface has two conceptual areas:

```text
world
+
right sidebar
```

The sidebar contains five panels:

| Key | Panel         | Purpose                          |
| --- | ------------- | -------------------------------- |
| `I` | Inspection    | Find and observe critters        |
| `C` | Configuration | Change runtime rules             |
| `M` | Metrics       | Monitor the experiment           |
| `S` | Session       | Save, load, or create a world    |
| `T` | Tools         | Language, recording, diagnostics |

Pressing a panel key focuses it.

The tabs at the top of the sidebar can also be clicked.

---

# 🌍 World focus

`world` is a UI state, not a sixth panel.

When the world has focus:

```text
no sidebar panel receives contextual keyboard input
```

but the sidebar does not disappear.

The last focused panel remains visible in an unfocused state.

This allows:

```text
inspect something
↓
Esc
↓
return control to the world
↓
keep the information visible
```

The interface remembers the last real panel independently from the current focus.

---

## Returning to the world

When any panel is focused:

```text
Esc
```

returns focus to the world.

It does not close the application.

When the world already has focus, `Esc` opens the exit confirmation instead.

Hierarchical Escape:

```text
panel
  ↓ Esc
world
  ↓ Esc
exit confirmation
```

One key.

Increasingly serious consequences.

---

# 🔄 Panel navigation

Panels cycle in this order:

```text
Inspection
    ↓
Configuration
    ↓
Metrics
    ↓
Session
    ↓
Tools
    ↓
Inspection
```

Use:

```text
Tab         → next panel
Shift+Tab   → previous panel
```

Cycling wraps around.

Each panel remembers its own cursor position.

Leaving Configuration halfway through the selection controls and returning later does not send you back to the top.

Civilization has invented memory.

The sidebar has adopted some of it.

---

# ⌨️ Navigating a panel

For panels containing interactive items:

| Input       | Action                         |
| ----------- | ------------------------------ |
| `↑` / `↓`   | Move between interactive items |
| `←` / `→`   | Change the selected value      |
| `Enter`     | Activate the selected item     |
| `Tab`       | Focus next panel               |
| `Shift+Tab` | Focus previous panel           |
| `Esc`       | Return focus to the world      |

Section headings and read-only content do not receive the cursor.

Navigation wraps around the interactive items.

---

# 🔬 Inspection

Inspection has two related but separate concepts:

```text
Discovery
+
Observation
```

Discovery answers:

> Which critter should I look at?

Observation answers:

> Which critter am I currently following?

They are deliberately independent.

---

## Discovery

Discovery searches the current living population using:

```text
criterion
+
lineage filter
```

Available criteria include:

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

The lineage filter can be:

```text
all
R
G
B
```

Use `←` and `→` to change either value.

The current candidate is displayed before Observation begins.

Press:

```text
Enter
```

to observe that candidate.

If no matching critter exists, the current observation is preserved and an informational notice is shown.

Failure to find someone interesting does not make the previous organism cease to exist.

---

## Observation

An observation tracks a critter by its **stable ID**.

It does not track an array position.

The panel may show information such as:

```text
lineage
stable ID
alive / dead status
HP
age
generation
offspring
encounters
composite score
last action
position
local vision
neural weights
trajectory
```

Observation continues even when another panel receives focus.

For example:

```text
observe critter #417
↓
open Metrics
↓
run another 500 ticks
↓
return to Inspection
↓
still observing #417
```

The session belongs to the observed organism, not to the currently visible tab.

---

## Inspection visibility

Observation may remain active in the background, but world overlays associated with it are shown only while Inspection is focused.

This includes:

```text
observation marker
discovery marker
trajectory trail
```

Changing to Configuration or Metrics therefore reduces visual clutter without terminating Observation.

The scientist looked away.

The specimen continued making decisions anyway.

---

## When the observed critter dies

Observation does not silently jump to another organism.

Its final state is captured and frozen.

The panel can continue showing the death snapshot, including the critter's final genome and lifetime state.

Vision is no longer available after death because there is no longer a living organism occupying the world.

Death ends perception.

Documentation survives.

---

## Changing observation

Selecting another critter starts a new observation session.

The previous trail is cleared.

Selecting the same critter again is a no-op and preserves its existing trail.

`Clear observation` explicitly ends the current session.

---

## Mouse selection

Left-clicking a living critter in the world:

```text
selects its stable ID
+
focuses Inspection
```

Clicking empty world space does nothing.

Clicking a sidebar tab focuses that panel instead and is never interpreted as a world click.

---

# ⚙️ Configuration

Configuration contains live experiment controls.

Its major sections are:

```text
simulation speed
genetics
ecology
reproduction
selection
```

The actual rules, defaults, ranges, and semantics are documented in:

```text
docs/runtime-config.md
```

Most changes become effective immediately.

No restart is required.

The Configuration panel changes the environment and selection pressure.

It does not manually steer individual critters.

---

## Heal all critters

Configuration also provides:

```text
Heal all critters
```

This is an operator intervention, not a runtime law.

It resets the HP of every living critter to:

```text
INITIAL_HP
```

It does not:

```text
revive dead organisms
reset genomes
reset age
reset generation
reset neural memory
reset encounters
reset offspring
restart the run
```

Critters above the target HP are also brought back down to the target.

So technically “heal” is a friendly name for centralized HP normalization.

The ethics committee has not yet responded.

---

# 📊 Metrics

Metrics is a dashboard rather than a form.

It contains no selectable items.

All six tracked metrics are displayed as small charts:

```text
population
average HP
longest lifetime
maximum generation
average composite score
mutation rate
```

Because there is no cursor, arrow-key item navigation has no effect.

These still work:

```text
Tab
Shift+Tab
Esc
mouse wheel
```

The mouse wheel scrolls sidebar content when the pointer is over the sidebar.

---

# 💾 Session

Session contains world lifecycle operations:

| Item      | Action                                               |
| --------- | ---------------------------------------------------- |
| Save slot | Select `default`, `world_a`, `world_b`, or `world_c` |
| Save now  | Write the current checkpoint                         |
| Load      | Restore the selected checkpoint                      |
| New world | Start a new run                                      |

Save and load results appear as short transient notices in the sidebar.

Notices expire according to interface time, not simulation ticks.

They therefore disappear normally even while the world is paused.

Time may stop for the organisms.

The notification system remains employed.

---

# 🧰 Tools

Tools contains operator utilities that are not part of the simulated ecology.

Current tools:

| Item        | Purpose                           |
| ----------- | --------------------------------- |
| Language    | Switch display language           |
| Recording   | Start or stop GIF capture         |
| Print state | Print diagnostic simulation state |

The graphical interface currently supports:

```text
English
Portuguese (Brazil)
```

Localization affects display text.

It does not alter simulation identifiers or checkpoint semantics.

---

# 📡 Floating HUD

Several overlays float over the world:

```text
Telemetry HUD
Command Dock
RPS tip
```

Press:

```text
H
```

to hide or show them.

The right sidebar remains visible because it is structural UI, not a floating overlay.

The floating HUD summarizes current operating state without requiring a panel change.

Status rows, in order:

```text
tick
speed
zoom
births
deaths
slot
```

`zoom` reflects the current camera factor. It is not a runtime rule and
is not persisted.

---

# 🎛️ Global controls

These shortcuts work independently of panel focus unless an exit modal is active.

| Key        | Action                              |
| ---------- | ----------------------------------- |
| `SPACE`    | Play / pause                        |
| `=` or `+` | Execute exactly one simulation tick |
| `F11`      | Toggle fullscreen                   |
| `R`        | Create a new world                  |
| `N`        | Cycle save slot                     |
| `P`        | Print simulation state              |
| `Z`        | Toggle environmental zones          |
| `G`        | Start / stop GIF recording          |
| `H`        | Toggle floating HUD                 |
| `Ctrl+S`   | Save                                |
| `Ctrl+L`   | Load                                |
| `I`        | Focus Inspection                    |
| `C`        | Focus Configuration                 |
| `M`        | Focus Metrics                       |
| `S`        | Focus Session                       |
| `T`        | Focus Tools                         |

Panel activation keys require no functional modifier.

For example:

```text
S       → Session
Ctrl+S  → Save
```

This is deliberate.

The keyboard does not consider those equivalent requests.

---

# ⏸️ Pause and single-step

`SPACE` toggles continuous simulation.

When paused:

```text
=
```

or:

```text
+
```

executes exactly one tick.

This is useful when observing:

```text
predation
death
reproduction
movement decisions
nest entry
ecological collisions
```

One tick at a time.

Evolution hates this feature because it makes witnesses considerably more reliable.

---

# 🚪 Exit confirmation

Closing the window or pressing `Esc` while the world has focus does not terminate immediately.

Instead:

```text
simulation pauses
↓
exit modal opens
```

Then:

```text
Enter → exit
Esc   → cancel
```

Cancelling restores the previous pause state.

If the simulation was running before the modal, it resumes.

If it was paused, it stays paused.

While the modal is open, other input is blocked.

No save shortcut.

No panel navigation.

No mouse selection.

No desperate last-second mutation-rate adjustment.

The modal has jurisdiction.

---

# 🧭 Input priority

When several kinds of input are possible, the interface follows a clear priority:

```text
exit request
↓
active modal
↓
global command
↓
panel activation
↓
focused-panel navigation
↓
world interaction
```

This prevents the same key or click from accidentally triggering multiple meanings.

A click on a tab is a tab click.

It does not also select whatever organism happens to be geometrically behind the sidebar.

We have chosen not to evolve quantum user interfaces.

---

# 🧱 UI state is not world state

Navigation belongs to the interface.

It does not influence simulation mechanics.

UI-only state includes things such as:

```text
focused panel
last visible panel
panel cursors
scroll offsets
exit modal
transient notices
floating HUD visibility
```

This state is kept separate from the simulated world.

Changing panels cannot:

```text
alter HP
move critters
change genomes
affect reproduction
modify score
change ecological resolution
```

Observation is intended to be observational.

A surprisingly difficult property for scientific software.

---

# 🔒 Interface invariants

The current UI contract is:

```text
five focusable panels

world means no panel has contextual focus

last panel remains visible while world is focused

Tab / Shift+Tab cycle panels

each panel preserves its own cursor

Esc from a panel returns to world

Esc from world requests exit

exit always requires explicit confirmation

Inspection focus does not automatically select a critter

Observation is tracked by stable ID

Observation survives panel changes

inspection overlays are visible only in Inspection

clicking a critter starts Observation and focuses Inspection

UI navigation does not affect simulation mechanics
```

---

## Final note

Primordial Soup gives the operator considerable power:

```text
change the laws
pause time
inspect brains
save universes
restore history
measure populations
heal everyone
```

But one power remains deliberately absent:

```text
control this critter
```

You may change the world around them.

What they do with it is still their problem.
