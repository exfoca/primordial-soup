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

**This is the single authority for panels, controls, inspection, and interaction.** The ecological rules being observed live in [World Rules](world-rules.md); the HOT rules being changed live in [Runtime Configuration](runtime-config.md).

---

# Interface model

The graphical interface has two conceptual areas:

```text
world
+
right sidebar
```

The sidebar contains five panels:

| Key | Panel         | Purpose                                     |
| --- | ------------- | ------------------------------------------- |
| `I` | **Inspection**    | Find and observe individual critters        |
| `C` | **Configuration** | Change runtime rules                        |
| `M` | **Metrics**       | Inspect population and evolutionary metrics |
| `S` | **Session**       | Save, load, or create a world               |
| `T` | **Tools**         | Language, audio, recording and diagnostics  |

Pressing a panel key focuses it. The tabs at the top of the sidebar can also be clicked.

---

## World focus

`world` is a UI state, not a sixth panel.

When the world has focus, no sidebar panel receives contextual keyboard input — but the sidebar does not disappear. The last focused panel remains visible in an unfocused state.

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

When any panel is focused, `Esc` returns focus to the world.

When the world already has focus, `Esc` opens the exit confirmation instead.

Hierarchical Escape:

```text
panel
  ↓ Esc
world
  ↓ Esc
exit confirmation
```

One key. Increasingly serious consequences.

---

## Panel navigation

Panels cycle in this order:

```text
Inspection → Configuration → Metrics → Session → Tools → Inspection
```

Cycling wraps around.

### From a focused panel

```text
Tab         → next panel
Shift+Tab   → previous panel
```

### From the world

`Tab` and `Shift+Tab` also work while the world is focused. They are structural panel navigation and are routed before the "panel-focused" check.

With the default registry:

```text
world + Tab         → Inspection  (first registered panel)
world + Shift+Tab   → Tools       (last registered panel)
```

The destination is derived from the registry order, not from the last visible panel.

`last_panel` controls which panel remains visible while world is focused. It is **not** the Tab destination.

Each panel remembers its own cursor position.

Leaving Configuration halfway through the selection controls and returning later does not send you back to the top.

Civilization has invented memory.

The sidebar has adopted some of it.

---

# ⌨️ Contextual navigation

Two distinct categories of input live here.

## Structural panel cycling

```text
Tab         → next panel
Shift+Tab   → previous panel
```

These work from any focus state, including `world`.

## Panel-local input

| Key       | Action                                |
| --------- | ------------------------------------- |
| **↑ / ↓** | Move the cursor within the panel      |
| **← / →** | Adjust the selected VALUE / ENUM      |
| **Enter** | Activate the selected ACTION / TOGGLE |
| **ESC**   | Return focus to the world             |

Panel-local input requires a focused panel. When focus returns to the world, the lateral panel still shows the last focused panel, but without contextual navigation.

---

# 🌍 Global controls

Always active, regardless of which panel is focused.

| Key        | Action                              |
| ---------- | ----------------------------------- |
| `SPACE`    | Play / pause                        |
| `=` or `+` | Advance exactly one tick            |
| `F11`      | Toggle fullscreen                   |
| `R`        | Create a fresh run                  |
| `N`        | Cycle the active save slot          |
| `P`        | Print simulation state              |
| `Z`        | Toggle environmental zones          |
| `G`        | Start / stop GIF recording          |
| `H`        | Show / hide floating HUD            |
| `Ctrl+S`   | Save                                |
| `Ctrl+L`   | Load                                |
| `Ctrl+wheel` | Zoom world at cursor              |
| `Ctrl+0`   | Reset world zoom                    |
| `ESC`      | Return to world focus, or quit      |

Panel activation keys require no modifier. For example, `S` focuses Session; `Ctrl+S` saves.

The keyboard does not consider those equivalent requests.

---

## `SPACE` — pause / resume

Toggles the simulation between running and paused. The simulation starts paused.

While paused, the world is frozen; you can inspect, change parameters, save, load, or advance one tick manually.

---

## `=` / `+` — advance one tick

Advances exactly one simulation tick. Works even while paused.

---

## `R` — new run

Creates a fresh run: new population, new genomes, new positions, new canonical zone centers and derived zone mask, new nests, fresh counters, fresh identity sequence, and a fresh reproductive cycle. Discards the current run.

Cleared as part of the new-run lifecycle: recent death archive, active Observation, inspection trail, and Birth Waves from the previous world.

`controls.recreate()` explicitly preserves the complete current `RuntimeRules`, simulation speed, and paused state. Operator/session preferences not owned by fresh-world bootstrap also remain in place, including language, active save slot, discovery settings, floating HUD, and audio preferences.

`zones_active` is different: new-run counter reset restores it from the declarative `DEFAULT_ZONES_ACTIVE` OPERATOR baseline.

---

## `Ctrl+L` — load active slot

Loads the currently active save slot. On success, the simulation is paused.

On success: checkpoint state is restored, recent death archive is restored from the checkpoint, active Observation is cleared, inspection trail is cleared, Birth Waves are cleared, simulation is paused.

On failure: running world remains intact, recent death archive remains intact, active Observation remains intact, RNG state remains intact.

If validation fails, the current runtime state is not replaced by a partially loaded world.

See [Persistence](persistence.md).

---

## `N` — cycle save slot

Cycles the active save slot. Does not save or load anything by itself. Only changes the destination/source.

---

## `P` — print state

Prints a textual snapshot of the current simulation state to the terminal. The graphical world is unchanged.

---

## `Z` — toggle environmental zones

Enables or disables environmental zones. Affects both visualization and mechanics. Turning zones off does not destroy the mask or the canonical centers. Turning them back on restores the same geometry.

See [Runtime Configuration](runtime-config.md) for the toggle-vs-law distinction.

---

## `G` — GIF recording

Starts recording frames. Press again to stop. When recording ends, writes the GIF to the configured file.

Requires the optional Pillow dependency.

---

## `H` — show / hide floating HUD

Toggles the visibility of the floating HUD elements drawn over the world: the Telemetry HUD, the Command Dock, and the RPS tip.

`H` does **not** hide map overlays (zone HP labels, Birth Waves, death markers) and does **not** affect the right sidebar. The lateral panel occupies a structurally reserved strip of the window and remains visible regardless of this toggle.

`H` does not change simulation state.

---

## `F11` — fullscreen

Toggles fullscreen mode. Presentation only. Does not rebuild the world geometry and does not start a new run.

---

## `Ctrl+wheel` / `Ctrl+0` — camera

`Ctrl+wheel` zooms the world anchored at the cursor. `Ctrl+0` resets the camera to the canonical state.

Zoom is a presentation-only operator choice. It is not `RuntimeRules`, does not persist in checkpoints, and does not alter world geometry.

---

# 🔍 Inspection

Inspection has two related but separate concepts:

```text
DISCOVERY   → "Who looks interesting?"
OBSERVATION → "Who am I actually following?"
```

They are deliberately independent. Changing your search does not move your microscope.

Inspection can target living individuals and recent dead individuals. A recent dead individual is selected by clicking its death marker on the map. Its `DeathSnapshot` was captured at the moment of death and preserved for the retention window.

---

## Discovery

Discovery answers: given this criterion and lineage filter, which living critter is the current candidate?

It is a query over the **living** population. Recent deaths do **not** participate in Discovery. Dead individuals are selected directly by clicking their death marker.

There is exactly **one** discovery candidate at a time. Or none.

Criteria include most evolved, oldest, youngest, most offspring, most encounters, most explored, highest HP, lowest HP, and highest generation.

Lineage filter cycles through `all`, `R`, `G`, `B`.

The discovery candidate is marked in the world with a **yellow Moore-neighborhood outline**.

---

## Observation

Observation represents the specific individual currently under study, based on a **stable critter ID**, not on an array position.

Arrays may move. Identity stays put.

The observed critter is marked in **cyan**.

Living observed critter: cyan outline. Dead observed critter: cyan cross centered on its last known position.

The shape, rather than the color, communicates the state.

---

## Focusing Inspection

Pressing `I` focuses the panel but does **not** automatically observe any critter and does **not** replace an existing observation.

Observation is always an explicit action, triggered by:

```text
Observe candidate + Enter
click a living critter
click a recent death marker
```

Leaving Inspection — with `ESC`, `Tab`, or another panel key — does **not** end the active observation. The stable critter ID remains selected, and the trail keeps being updated while the observed critter is alive.

Only the visual overlay — candidate marker, observed/death marker, trail — is drawn when Inspection is the focused panel.

To end an observation explicitly, select **Clear observation** and press `Enter`.

---

## The yellow and cyan markers

```text
yellow = discovery candidate
cyan   = observed critter
```

If both refer to the same individual, cyan is rendered on top. You see only cyan. That means "the critter I am observing is also the current discovery candidate". Not "yellow mysteriously disappeared".

---

## Death snapshot and inspection

When the observed critter dies, its final state is frozen. The panel keeps showing the death snapshot, including the critter's final genome and lifetime state.

**Vision is unavailable after death.** The `DeathSnapshot` preserves the final agent row and genome, but not a historical perception tensor. The simulation does not reconstruct a plausible vision from the current world either: doing so would present data the critter never actually consumed.

The vision panel therefore reports that vision is unavailable for dead individuals.

**Neural heatmaps remain available.** The genome is preserved in the snapshot, so the brain parameters can still be inspected after death.

This is a deliberate asymmetry:

```text
vision         → unavailable after death
brain weights  → still inspectable
```

---

## The recent death archive

Every death feeds a chronological archive called `recent_deaths`, regardless of whether the individual was being observed.

The archive is:

```text
unbounded by count
bounded by simulation time
```

A death at tick `D` remains discoverable from `D` through `D + TTL - 1`. It expires at `D + TTL`. While the simulation is paused, no new ticks are produced, so the age of every marker is frozen.

A left click near a recent death marker selects that snapshot and focuses Inspection. The click search uses a small spatial tolerance. When both a recent death marker and a living critter are within tolerance, the death marker is found first.

The archive is persisted in the checkpoint. After a save/load cycle, death markers still inside their window reappear; expired deaths are not restored. The current inspected critter, its trail, and its active dead selection are **not** persisted.

After a successful load, no critter or death snapshot is automatically selected. The operator must choose one explicitly.

---

## The trail

While a living critter is being observed, Primordial Soup records its position after each tick.

The trail shows where that individual has traveled since the observation began. Older positions are darker, newer positions are brighter. Grayscale on purpose: it does not compete with the R/G/B lineage colors.

The trail is a sequence of points, not a connected line. In the toroidal world, two adjacent cells can appear on opposite sides of the screen.

The trail is cleared when observation changes. It is preserved across panel focus changes: the drawing is gated by the focused panel, but the underlying data keeps being appended while the observed critter is alive.

Once the observed individual dies, its stable ID no longer resolves to a living population entry. No new trail points are added. The trail remains frozen at the path accumulated before death, paired with the cyan death marker at its final position.

---

## Vision panel and brain heatmaps

The Inspection panel includes an **11 × 11** view centered on the observed critter's position. This mirrors the local spatial information used by the neural controller.

The world contains three lineage density channels. The panel converts them into an RGB representation so you can inspect the local ecological context.

Below it, the panel displays heatmaps representing parts of the observed critter's genome: input-to-hidden, hidden-to-hidden, hidden-to-output weights, hidden biases, and recurrent weights.

These are useful for comparing individuals, comparing generations, spotting very different genomic structures, and inspecting a dead individual's final inherited controller.

A colored stripe is not an explanation. Neural networks rarely provide subtitles.

---

## Observation does not affect evolution

Inspection is a **view** over the simulation. Changing criterion, filter, observed critter, or panel state does not alter the critter's neural network, HP, reproduction eligibility, or ecological interactions.

The trail itself is also visualization state.

The organisms do not know they are being watched.

---

## No automatic replacement

The observed critter is never silently replaced because it died.

Why? Because *observe #100 → #100 dies → automatically observe #237* creates a false continuity. For exploratory visualization that might seem convenient. For analysis it is misleading.

Primordial Soup prefers:

```text
#100 dies
↓
freeze #100
↓
you decide what to observe next
```

---

# ⚙️ Configuration

Configuration contains live experiment controls. Its major sections are simulation speed, genetics, ecology, reproduction, and selection.

The panel edits active HOT `RuntimeRules` and also exposes selected operator/execution controls and actions. HOT changes become effective through validated rule replacement; operator controls follow their own state paths.

The Configuration panel does **not** edit NON_HOT `.env` values, replace `ConfigSnapshot`, or write the user configuration file. It changes the environment and selection pressure; it does not manually steer individual critters.

The actual rules, defaults, ranges, and semantics are documented in [Runtime Configuration](runtime-config.md).

---

## Heal all critters

Configuration also provides **Heal all critters**. This is an operator intervention, not a runtime law.

It resets the HP of every living critter to the initial HP. It does not revive dead organisms, reset genomes, reset age, reset generation, reset neural memory, reset encounters, reset offspring, or restart the run.

Critters above the target HP are also brought back down to the target. So technically "heal" is a friendly name for centralized HP normalization.

The ethics committee has not yet responded.

---

# 📊 Metrics

Metrics is a dashboard rather than a form.

It contains no selectable items. All tracked metrics are displayed as small charts: population, average HP, longest lifetime, maximum generation, average composite score, and mutation rate.

Because there is no cursor, arrow-key item navigation has no effect. `Tab`, `Shift+Tab`, `Esc`, and the mouse wheel still work.

The mouse wheel scrolls sidebar content when the pointer is over the sidebar.

---

# 💾 Session

Session contains world lifecycle operations: save slot selection, save now, load, and new world.

Save and load results appear as short transient notices in the sidebar. Notices expire according to interface time, not simulation ticks.

They therefore disappear normally even while the world is paused.

Time may stop for the organisms.

The notification system remains employed.

---

# 🧰 Tools

Tools contains operator utilities that are not part of the simulated ecology: language, music, sound effects, GIF recording, and print state.

The graphical interface supports **English** and **Portuguese (Brazil)**. Localization affects display text only. It does not alter simulation identifiers or checkpoint semantics.

Music and Sound effects are independent operator preferences stored separately from simulation checkpoints. Saving or loading a world does not change them.

---

# 🔊 Audio

Audio is presentation only. It does not affect HP, ecology, genetics, selection, or reproduction.

The background track follows the simulation's paused/running state. Sound effects cover world generation, birth activity, menu feedback, successful save/load, and shutdown.

Birth activity is aggregated per graphical batch: one or many births occurring inside the same batch produce at most one birth feedback event. This matters most at high simulation speeds, where a single frame may advance many ticks.

Audio is best-effort. A mixer failure does not abort the simulation. An individual missing or broken WAV does not disable unrelated sounds.

Audio exists only in graphical mode. Headless execution does not initialize the audio backend.

---

# 📡 Floating HUD

Several overlays float over the world: the Telemetry HUD, the Command Dock, and the RPS tip.

Press `H` to hide or show them.

The right sidebar remains visible because it is structural UI, not a floating overlay.

`H` does not hide map overlays (zone HP labels, Birth Waves, death markers). Those elements belong to the world, not to the floating HUD.

The floating HUD summarizes current operating state without requiring a panel change.

---

# 🌍 Map overlays

Three classes of overlay are drawn on the world itself, independently of panel focus:

```text
zone HP labels     — one per active zone, at canonical centers
Birth Waves        — brief lineage-colored rings from nests
death markers      — lineage-colored X for every recent death
```

## Zone HP labels

Each active environmental zone displays its current HP effect at its canonical center:

```text
+N HP   beneficial
 0 HP   neutral
-N HP   harmful
```

The format never produces `+0 HP`. The displayed value is derived from the current runtime rule, not from a static config constant.

Labels are drawn only when zones are active. The label **position** follows the world-space center of each zone, but the glyphs are drawn in screen-space, so they remain readable at any zoom.

## Birth Waves

When a lineage reproduces successfully, a brief lineage-colored wave expands outward from that lineage's nest.

The wave is graphical feedback only. It does not grant HP, change metabolism, alter perception, influence selection, modify genetics, or act as a physical shockwave.

It communicates one fact: **birth activity occurred for this lineage**.

Wave lifetime uses wall-clock time, not simulation ticks. Consequences: changing simulation speed does not shorten or lengthen the perceived animation; pausing the simulation does not freeze an already-visible wave.

The ring geometry lives in world-space, so waves zoom together with the world and wrap toroidally. This is the opposite of zone HP labels.

Birth Waves are transient presentation state. They are not checkpoint state, are not restored on load, and are cleared on new world / recreate.

## Recent death markers

Every death produces a lineage-colored diagonal X drawn at the final position of the snapshot.

Markers persist for a bounded number of **simulation ticks**, not wall-clock seconds. Pausing the simulation freezes the age of every marker, because no new ticks are produced.

This is deliberately the opposite of Birth Waves.

A left click near a recent death marker selects that snapshot and focuses Inspection.

The general death marker is independent of which panel is focused. When a dead critter is currently selected in Inspection, its Inspection marker is cyan — identifying the current selection, while the lineage color identifies the general marker.

---

# 🚪 Exit confirmation

Closing the window or pressing `Esc` while the world has focus does not terminate immediately.

Instead: the simulation pauses and the exit modal opens.

Then `Enter` exits; `Esc` cancels.

Cancelling restores the previous pause state: if the simulation was running before the modal, it resumes; if it was paused, it stays paused.

While the modal is open, other input is blocked. No save shortcut. No panel navigation. No mouse selection. No desperate last-second mutation-rate adjustment.

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

This prevents the same key or click from accidentally triggering multiple meanings. A click on a tab is a tab click. It does not also select whatever organism happens to be geometrically behind the sidebar.

We have chosen not to evolve quantum user interfaces.

---

# 🧱 UI state is not world state

Navigation belongs to the interface. It does not influence simulation mechanics.

UI-only state includes the focused panel, the last visible panel, panel cursors, scroll offsets, the exit modal, transient notices, and floating HUD visibility.

Changing panels cannot alter HP, move critters, change genomes, affect reproduction, modify score, or change ecological resolution.

Observation is intended to be observational.

A surprisingly difficult property for scientific software.

---

# 🔒 Interface invariants

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
zoom in on a suspicious red dot
```

But one power remains deliberately absent:

```text
control this critter
```

You may change the world around them.

What they do with it is still their problem.
