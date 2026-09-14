# 🎮 Controls

Primordial Soup is mostly autonomous. The critters make their own
decisions. You control the laboratory.

The keyboard does three distinct things:

```text
global commands
    always active

panel activation
    focuses a specific panel

contextual navigation
    operates inside the focused panel
```

That division replaces the older model of "one key, one direct
action".

---

# 🌍 Global commands

Always active, regardless of which panel is focused.

| Key       | Action                              |
| --------- | ----------------------------------- |
| **SPACE** | Pause / resume                      |
| **= / +** | Advance exactly one tick            |
| **R**     | Create a fresh run                  |
| **L**     | Load the active save slot           |
| **N**     | Cycle the active save slot          |
| **P**     | Print the current simulation state  |
| **Z**     | Toggle environmental zones          |
| **G**     | Start / stop GIF recording          |
| **H**     | Show / hide floating HUD            |
| **F11**   | Toggle fullscreen                   |
| **ESC**   | Return to world focus, or quit      |

## SPACE — pause / resume

Toggles the simulation between running and paused.

The simulation starts paused.

While paused, the world is frozen; you can inspect, change parameters,
save, load, or advance one tick manually.

## = / + — advance one tick

Advances exactly one simulation tick. Works even while paused.

## R — new run

Creates a fresh run: new population, new genomes, new positions, new
environmental zones, fresh counters, fresh identity sequence, fresh
reproductive cycle. Discards the current run.

Operator tunings (mutation rate, local scale, speed, language, pause
state, zone HP effect) are preserved so experiments can be repeated
without reconfiguring.

Also clears any active observation session and the inspected trail.

## L — load active slot

Loads the currently active save slot. On success, the simulation is
paused.

If validation fails, the current runtime state is not replaced by a
partially loaded world.

See [Persistence](persistence.md).

## N — cycle save slot

Cycles the active save slot:

```text
default → world_a → world_b → world_c → default
```

Does not save or load anything by itself. Only changes the
destination/source.

## P — print state

Prints a textual snapshot of the current simulation state to the
terminal. The graphical world is unchanged.

Also available in the Tools panel as **Print state**.

## Z — toggle environmental zones

Enables or disables environmental zones.

This affects both visualization and mechanics. When zones are off, their
HP effect is not applied. The zone geometry is not destroyed; turning
them back on restores the existing mask.

Also available in the Configuration panel as **Environmental zones**.

## G — GIF recording

Starts recording frames. Press again to stop. When recording ends,
writes the GIF to the configured file (default: `primordial_soup.gif`).

Requires the optional Pillow dependency:

```bash
pip install .[recording]
```

Also available in the Tools panel as **Recording**.

## H — show / hide floating HUD

Toggles the visibility of the floating HUD elements drawn over the
world.

The floating HUD currently includes:

* the **Telemetry HUD** (top-left panel with status, parameters and
  the lineage table);
* the **Command Dock** (bottom-left panel with the command reference).

It does **not** affect the right sidebar. The lateral panel occupies a
structurally reserved strip of the window and remains visible
regardless of this toggle.

H does not change simulation state.

## F11 — fullscreen

Toggles fullscreen mode.

Presentation only. Does not rebuild the world geometry and does not
start a new run.

## ESC — back / quit

If a panel is focused, returns focus to the world.

If the world is already focused, exits the application.

---

# 📋 Panel activation

Each key focuses the corresponding panel. It does not toggle the panel
and it does not perform the panel's action directly.

| Key   | Panel         |
| ----- | ------------- |
| **I** | Inspection    |
| **C** | Configuration |
| **M** | Metrics       |
| **S** | Session       |
| **T** | Tools         |

The lateral panel is always present in the right sidebar. What changes
is which panel is focused.

---

# ⌨️ Contextual navigation

Active only when a panel is focused.

| Key           | Action                                |
| ------------- | ------------------------------------- |
| **Tab**       | Focus next panel                      |
| **Shift+Tab** | Focus previous panel                  |
| **↑ / ↓**     | Move the cursor within the panel      |
| **← / →**     | Adjust the selected VALUE / ENUM      |
| **Enter**     | Activate the selected ACTION / TOGGLE |
| **ESC**       | Return focus to the world             |

When focus returns to the world, the lateral panel still shows the last
focused panel, but without contextual navigation.

---

# 🔍 Inspection panel

Two separate concepts:

```text
DISCOVERY
"Who looks interesting?"

OBSERVATION
"Who am I actually following?"
```

## Discovery items

```text
Criterion          ENUM
Lineage filter     ENUM
Candidate          read-only
Observe candidate  action
```

**Criterion** cycles through:

```text
most evolved, oldest, youngest, most offspring,
most encounters, most explored, highest HP, lowest HP,
highest generation, best score
```

**Lineage filter** cycles through `all, R, G, B`.

**Candidate** displays the current discovery candidate. Read-only.

**Observe candidate** — select and press **Enter** to make the candidate
the observed critter. If there is no candidate, the action preserves the
current observation.

## Observation items

```text
Clear observation  action
```

**Clear observation** — select and press **Enter** to end the current
observation. Clears the selected critter ID, the trail and any death
snapshot.

## Focus behavior

Focusing Inspection does **not** auto-select or replace the observed
critter.

Leaving Inspection does **not** end the observation either. The stable
critter ID remains selected and the trail keeps being appended while the
observed critter is alive.

Only the visual overlay — candidate marker, observed/death marker and
trail — is drawn when Inspection is the focused panel.

See [Inspection](inspection.md) for the full model.

---

# ⚙️ Configuration panel

```text
Simulation speed          ENUM
Mutation rate             VALUE
Local mutation scale      VALUE
Environmental zones       TOGGLE
Zone HP effect            VALUE
Heal all critters         ACTION
```

**Simulation speed** cycles through `1, 2, 4, 8, 16, 32, 64, 128, 256`
ticks per rendered frame. Changes execution throughput, not rules.

**Mutation rate** — percent probability that an offspring undergoes
mutation. Range `0%` to `100%`. Default `5%`.

**Local mutation scale** — how broad local mutation is when the active
mutation model uses the local scale. Range `1%` to `100%`.

**Environmental zones** — toggles zone mechanics, same as the global
**Z**.

**Zone HP effect** — HP change per tick inside a zone. Range `-100` to
`+100`. Positive means a beneficial zone. Negative means a hazard.
Adjustable while the simulation is running.

**Heal all critters** — sets HP of every living critter to the initial
HP:

```text
HP = INITIAL_HP
```

not `HP += INITIAL_HP`. Does not modify position, age, generation,
genome, memory, counters. Does not revive dead critters. Does not
recreate extinct lineages.

This item has **no keyboard shortcut**. It is only reachable through
this panel.

---

# 📈 Metrics panel

```text
Metric  ENUM
```

Cycles through the available chart metrics. The corresponding chart is
drawn in the panel viewport.

Changing the displayed metric does not affect the ecosystem.

---

# 💾 Session panel

```text
Save slot   ENUM
Save now    ACTION
Load        ACTION
New world   ACTION
```

**Save slot** cycles the active save slot, same effect as the global
**N**.

**Save now** saves the current simulation to the active slot.

**Load** loads the active slot, same effect as the global **L**.

**New world** creates a fresh run, same effect as the global **R**.

There is **no global accelerator that saves directly**. Saving is
always:

```text
S → Session → Save now → Enter
```

---

# 🛠️ Tools panel

```text
Language    ENUM
Recording   TOGGLE
Print state ACTION
```

**Language** cycles the interface language (English ↔ Portuguese).

**Recording** toggles GIF recording, same as the global **G**.

**Print state** prints the state to the terminal, same as the global
**P**.

---

# 🖱️ Mouse

## Left click

Resolves the click to a world coordinate, looks up the critter under
the cursor, and — if any is found — makes it the observed critter. The
Inspection panel is focused as a side effect.

The lookup includes a small spatial tolerance, currently four world
cells.

Clicks are accepted regardless of pause state and regardless of which
panel is focused.

If the click misses every critter, it is a no-op: the existing
observation remains unchanged.

## Wheel

Scrolls the lateral panel.

If a panel is focused, the wheel scrolls that panel. If the world is
focused, the wheel scrolls the last focused panel — the one currently
shown in the lateral strip.

---

# ⚠️ Common mistakes

**"I changed the criterion and the observed critter didn't change."**

Correct. Criterion and Lineage filter change discovery. Select
**Observe candidate** and press **Enter** to observe the new candidate.

**"Tab doesn't switch the lineage filter."**

Correct. Tab cycles the focused panel. To change the lineage filter,
focus Inspection, select **Lineage filter**, and use **← / →**.

**"I pressed H and expected HP to be restored."**

H toggles the floating HUD. To heal the population, use
`C → Configuration → Heal all critters → Enter`.

**"I turned zones off but expected only the color to disappear."**

Z disables the mechanic too. No zone HP effect is applied while zones
are disabled.

**"I pressed N and nothing loaded."**

N only changes the active slot. Use **L** after selecting the slot.

**"I pressed S and nothing was saved."**

S focuses the Session panel. To save, use `S → Session → Save now →
Enter`.

**"I focused Inspection and my previous observation disappeared."**

Focusing Inspection does not change the observation. The inspection
overlay is only drawn when Inspection is focused, but the underlying
observation state is preserved. Use **Clear observation** to end it
explicitly.

---

# 📚 Related documentation

→ [Getting Started](getting-started.md)
→ [Inspection](inspection.md)
→ [Evolution](evolution.md)
→ [Persistence](persistence.md)
→ [Configuration](configuration.md)
