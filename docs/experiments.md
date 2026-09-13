# 🧪 Experiments

Watching Primordial Soup is entertaining.

Experimenting with it is more useful.

The difference is whether you can answer:

> What changed, what stayed constant, and would the result happen again?

A colorful population explosion is an observation.

A controlled comparison across repeated runs is evidence.

This guide explains how to move from:

```text
"Blue did something weird."
```

to:

```text
"Under these conditions, Blue repeatedly did something weird."
```

That is progress.

---

# Start with a question

Do not begin an experiment by randomly adjusting parameters.

Begin with a question.

Good:

```text
Does mutation rate affect maximum generation depth?
```

Better:

```text
Does increasing mutation from 5% to 20%
change maximum generation depth after 50,000 ticks?
```

Poor:

```text
What happens if I press everything?
```

The last one is still fun.

It is simply difficult to publish.

---

# One variable at a time

The safest experimental rule in Primordial Soup is:

```text
change one thing
measure several things
```

Suppose you simultaneously change:

```text
mutation rate
zone HP effect
selection weights
reproductive age
```

and Red becomes dominant.

You now know that:

```text
something caused something
```

which is scientifically underwhelming.

For a controlled comparison, change one independent variable while keeping the rest fixed.

---

# Use repeated runs

Primordial Soup is stochastic.

Randomness affects founder genomes, positions, zones, parent pairing, crossover, mutation and newborn placement.

Two identical configurations can therefore produce different histories.

Never treat one run as proof.

A useful pattern is:

```text
configuration A
seed 1
seed 2
seed 3
seed 4
seed 5

versus

configuration B
seed 1
seed 2
seed 3
seed 4
seed 5
```

Using the same seed set helps compare conditions under similar random starting sequences.

More runs produce stronger evidence.

Five runs are much better than one.

Twenty are much better than five.

One hundred is when your laptop begins participating in the research discussion.

---

# Fix the duration

Comparisons should normally use the same number of simulation ticks.

For example:

```text
10,000 ticks
```

or:

```text
50,000 ticks
```

Do not compare:

```text
run A = 5,000 ticks
run B = 80,000 ticks
```

and conclude that B produced deeper generations.

It had considerably more time to do so.

---

# Prefer headless runs for measurements

The graphical interface is excellent for:

* observing behavior;
* inspecting individuals;
* forming hypotheses;
* discovering unexpected patterns.

Headless mode is better for:

* repeated trials;
* fixed-duration runs;
* fixed seeds;
* parameter sweeps;
* automation;
* reproducible comparisons.

A basic run is:

```bash
python -m primordial_soup --new -d 10000 -s world_a --seed 42
```

This creates a fresh world, runs 10,000 ticks with seed `42`, and saves the result.

See [Headless](headless.md) for the complete CLI reference.

---

# What can be measured?

The current simulation records six advanced metrics:

| Metric                      | What it helps answer                                                     |
| --------------------------- | ------------------------------------------------------------------------ |
| **Population**              | Is the lineage growing, stable, declining or extinct?                    |
| **Average HP**              | How healthy is the surviving population?                                 |
| **Longest lifetime**        | Are individuals surviving longer?                                        |
| **Maximum generation**      | How deep has reproduction progressed?                                    |
| **Average composite score** | How well is the lineage performing under the configured selection model? |
| **Mutation rate**           | What mutation regime was active?                                         |

Metrics are currently sampled every:

```text
10 ticks
```

and the in-memory history keeps up to:

```text
600 samples
```

The graphical charts are therefore useful for recent dynamics.

Saved metrics are more useful for longer analysis.

---

# Metrics answer different questions

Population alone is not enough.

Suppose:

```text
Run A:
population = 300
maximum generation = 7

Run B:
population = 120
maximum generation = 24
```

Which evolved “better”?

That question cannot be answered from population alone.

Run A may be excellent at short-term survival.

Run B may have much faster genealogical turnover.

Likewise, a high composite score reflects the **selection function you designed**.

It is not an external measure of intelligence.

Always interpret metrics in relation to the mechanism that produced them.

---

# Record the experimental conditions

For every serious experiment, record at least:

```text
experiment name
code version / commit
random seed
duration
changed parameter
control value
experimental value
relevant fixed configuration
final populations
maximum generations
lifetimes
composite scores
extinctions
unexpected observations
```

If you cannot reconstruct the experiment later, you did not really preserve the experiment.

You preserved a memory of it.

Human memory does not support `--seed`.

---

# A simple experiment template

Use this structure when designing a run.

```text
QUESTION
What am I trying to learn?

HYPOTHESIS
What do I expect, and why?

INDEPENDENT VARIABLE
What exactly will change?

CONTROL
What is the baseline value?

TREATMENT
What alternative value will be tested?

CONSTANTS
What must remain identical?

SEEDS
Which random seeds will be used?

DURATION
How many ticks per run?

OBSERVABLES
Which metrics will be compared?

RESULT
What happened?

INTERPRETATION
What does the evidence support?

LIMITATIONS
What does the experiment not establish?
```

That last field prevents a surprising amount of nonsense.

---

# Experiment 1 — Mutation rate

## Question

How does mutation probability affect evolutionary progress?

## Hypothesis

Very low mutation may preserve successful genomes but reduce novelty.

Moderate mutation may balance inheritance and exploration.

Very high mutation may repeatedly damage useful inherited structure.

## Setup

Keep the simulation configuration unchanged.

Compare several runtime mutation rates, for example:

```text
0%
5%
20%
50%
100%
```

Use the same seed set and duration for every condition.

For a first experiment:

```text
5 seeds
50,000 ticks each
```

is enough to begin seeing whether a pattern deserves further investigation.

## Observe

Compare:

```text
maximum generation
population trajectories
average composite score
longest lifetime
extinction frequency
```

## Important interpretation

Do not expect a monotonic result.

This:

```text
more mutation
=
more evolution
```

is not generally valid.

Mutation supplies variation.

Selection decides whether that variation persists.

---

# Experiment 2 — Mutation-free inheritance

Set:

```text
mutation rate = 0%
```

Now descendants can still differ through crossover, but mutation introduces no new numerical variation.

## Question

How much evolutionary change can occur through recombination of founder genetic material alone?

## Observe

Watch:

```text
generation depth
score trajectories
population stability
behavioral convergence
```

A population can continue changing without mutation because crossover reshuffles existing genes.

But its accessible genetic search space is now restricted to material already present among founders and their recombinations.

This is a useful control condition.

It is **not** equivalent to turning evolution off.

---

# Experiment 3 — Mutation overload

Set:

```text
mutation rate = 100%
```

Every child now enters the mutation path.

## Question

Can useful inherited neural structure remain stable when every descendant mutates?

## Hypothesis

Selection may still preserve successful structures when mutations are sufficiently local, but inheritance should become noisier.

## Observe

Compare against the default mutation regime:

```text
population stability
maximum generation
score
extinction
run-to-run variance
```

High variance between seeds is itself an interesting result.

Chaos can be data.

Just not necessarily adaptation.

---

# ⚠️ Do not currently use the runtime local-scale control as an experimental variable

The interface exposes:

```text
O
↑ / ↓
```

for runtime local mutation scale.

However, in the current implementation the active `two_scales` mutation path still reads the configured local fraction directly rather than the runtime value.

So an experiment such as:

```text
local scale 5%
vs
local scale 50%
```

performed only through the graphical `O` control would currently be invalid.

The HUD value would change.

The effective mutation breadth would not.

Until this discrepancy is corrected, change the underlying configuration if you genuinely want to compare local mutation fractions.

A knob that is not connected to the machine is not an independent variable.

It is decoration.

---

# Experiment 4 — Beneficial zones

Keep environmental zones active and use a positive HP effect.

For example:

```text
zone HP effect = +20
```

## Question

Do lineages develop spatial distributions associated with beneficial regions?

## Observe

Use the graphical interface after a long run.

Look for:

```text
clustering near zones
population differences
long-lived individuals near zones
repeated occupation patterns
```

Use inspection to study individuals inside and outside those regions.

## Important caveat

Seeing a cluster inside a beneficial zone does not prove the critters evolved:

> “knowledge that zones are good.”

Several mechanisms can generate clustering.

For example, individuals that randomly remain in beneficial regions may simply survive longer.

To claim behavioral adaptation, compare repeated runs and inspect whether evolved controllers systematically produce different movement relative to the environment.

---

# Experiment 5 — Turn refuges into traps

Begin with beneficial zones.

Allow the simulation to run long enough for the population to experience them.

Then change:

```text
zone HP effect > 0
```

to:

```text
zone HP effect < 0
```

For example:

```text
+20
→
-20
```

## Question

How does a population respond when an environmental condition reverses?

This is particularly interesting because the geography remains the same.

Only its ecological consequence changes.

## Observe

Watch:

```text
population collapse
extinction
changes in spatial distribution
changes across later generations
individual movement near zones
```

This experiment separates:

```text
adaptation to a location
```

from:

```text
adaptation to what that location does
```

Yesterday's paradise becomes today's toxic swamp.

No migration advisory is issued.

---

# Experiment 6 — Zones on vs zones off

Compare two configurations:

```text
A: zones active
B: zones inactive
```

Keep everything else identical.

## Question

Does geographic heterogeneity materially change evolutionary dynamics?

## Observe

Compare:

```text
population stability
maximum generations
lifetimes
extinction frequency
spatial clustering
```

This is cleaner than changing zone strength repeatedly during one run because each treatment has a stable environmental regime.

---

# Experiment 7 — Selection pressure

The default composite score weights are:

```text
longevity     = 0.5
exploration   = 0.3
interaction   = 0.3
reproduction = 0.3
```

These values influence reproductive ranking.

Changing them changes what evolutionary success means.

## Longevity-heavy treatment

Increase the relative importance of longevity.

Question:

> Do populations evolve toward more conservative behavior?

## Exploration-heavy treatment

Increase the relative importance of exploration.

Question:

> Do movement rates, encounters or mortality change?

## Interaction-heavy treatment

Increase the importance of encounters.

Question:

> Does stronger ecological contact emerge, and at what survival cost?

## Reproduction-heavy treatment

Increase the importance of reproductive history.

Question:

> Does reproductive success become increasingly concentrated among already successful lineages of individuals?

These experiments require configuration changes rather than graphical runtime controls.

See [Configuration](configuration.md).

---

# Experiment 8 — Reproductive age

The current minimum reproductive age is:

```text
5,555 ticks
```

Compare lower and higher thresholds.

## Question

How does generation turnover affect adaptation and population stability?

A lower threshold may produce:

```text
faster generations
more reproductive opportunities
less lifetime evaluation before reproduction
```

A higher threshold may produce:

```text
slower generations
stronger survival filtering
fewer eligible parents
```

Measure more than maximum generation.

A system producing generations rapidly is not necessarily producing better descendants.

It may simply be reproducing sooner.

---

# Experiment 9 — Encounter gate

The current minimum is:

```text
6 encounters
```

Raise it.

## Question

Does stronger reproductive pressure toward inter-lineage interaction change ecology?

Possible outcomes include:

```text
more ecological contact
higher mortality
greater clustering
fewer eligible parents
slower population recovery
```

A sufficiently strict gate may reduce reproduction dramatically.

Selection pressure can become reproductive paralysis if configured aggressively enough.

---

# Experiment 10 — Crossover strategy

Primordial Soup supports:

```text
blocks
uniform
two_points
```

Run the same seed set and duration for each.

Do not change mutation simultaneously.

## Question

Which crossover strategy better preserves or recombines useful neural structures?

Compare:

```text
maximum generation
average composite score
longest lifetime
extinction frequency
between-run variance
```

Because genomes encode neural parameters, contiguous gene structure may matter.

Or it may not.

That is precisely why this is an experiment rather than an opinion.

---

# Experiment 11 — Long-run evolution

Run:

```text
100,000 ticks
```

or more in headless mode.

## Question

Do metrics continue improving, stabilize, oscillate or collapse over long periods?

Watch for:

```text
plateaus
population cycles
repeated extinctions
score stabilization
generation growth
long-term lineage imbalance
```

A long run can expose dynamics invisible at 5,000 ticks.

It can also produce a very long example of random history.

Repeat the experiment.

Long does not automatically mean statistically meaningful.

---

# Experiment 12 — Same configuration, different seeds

Do not change any parameter.

Run several seeds.

For example:

```text
42
43
44
45
46
```

## Question

How much of the observed outcome is configuration, and how much is stochastic history?

This is one of the most important baseline experiments in the entire project.

If identical settings produce dramatically different outcomes, then later comparisons between treatments need enough repetitions to separate signal from variance.

Before asking:

> Does parameter X matter?

first learn:

> How noisy is this universe when X does not change?

---

# Experiment 13 — Same seed, changed parameter

Now invert the previous design.

Use one seed repeatedly while changing exactly one parameter.

For example:

```text
seed 42
mutation 1%

seed 42
mutation 5%

seed 42
mutation 20%
```

This can help isolate treatment effects.

But do not use only one seed.

A parameter may interact unusually with one particular random history.

The best design combines both ideas:

```text
multiple treatments
×
multiple shared seeds
```

---

# Experiment 14 — Near-extinction intervention

Let a lineage approach extinction.

Then press:

```text
H
```

to reset the HP of all surviving critters.

This is not a clean natural-evolution experiment.

It is an **intervention experiment**.

That distinction should be recorded explicitly.

## Question

What happens when accumulated genomes are preserved but immediate survival pressure is suddenly reset?

The intervention keeps surviving individuals' genomes and life histories while resetting their HP.

It does not revive extinct individuals.

This can be useful for studying whether a population under severe ecological stress recovers when immediate mortality pressure is temporarily relieved.

Do not compare this directly with untouched runs without labeling the intervention.

You played god.

Write it in the methods section.

---

# Experiment 15 — Individual case study

Not every useful experiment must begin with population statistics.

Run a population for a substantial period.

Then use inspection.

For example:

```text
criterion = highest generation
lineage   = R
```

Observe the candidate.

Follow its trail.

Pause and single-step around interesting encounters.

Record:

```text
HP
age
generation
encounters
offspring
composite score
local vision
movement pattern
```

## Question

Can population-level performance be associated with recognizable individual behavior?

This is exploratory analysis.

It is useful for generating hypotheses.

It is not sufficient to establish a population-wide evolutionary strategy.

One clever critter does not constitute a species-level paper.

---

# Experiment 16 — Extinction frequency

Choose one treatment variable, such as mutation rate or zone damage.

For every seed, record whether each lineage survives to the target duration.

Example:

```text
condition A
20 runs
R extinct in 2
G extinct in 5
B extinct in 3

condition B
20 runs
R extinct in 11
G extinct in 13
B extinct in 9
```

Now you have something much stronger than:

> “Everyone seemed to die faster.”

Extinction can be treated as an outcome variable.

---

# Separate exploratory and confirmatory work

A productive workflow has two modes.

```text
EXPLORATORY

watch
poke
inspect
notice something strange
form a hypothesis
```

then:

```text
CONFIRMATORY

define treatment
fix seeds
fix duration
repeat
measure
compare
```

The GUI is excellent for the first.

Headless runs are excellent for the second.

Do not confuse discovery of a phenomenon with confirmation of a phenomenon.

---

# Save interesting worlds

The four slots are:

```text
default
world_a
world_b
world_c
```

They are useful for preserving representative runs.

For example:

```text
world_a → low mutation
world_b → default mutation
world_c → high mutation
```

But save slots are not a substitute for repeated experimentation.

Four memorable worlds can still be four anecdotes.

For large comparisons, automate headless runs and preserve the resulting metrics externally.

---

# Use GIFs as evidence carefully

GIF recording is useful for:

```text
showing behavior
documenting a visual phenomenon
comparing spatial organization
communicating results
```

It is poor as the only quantitative evidence.

A GIF can show:

> This pattern occurred.

It usually cannot establish:

> This treatment produces this pattern more often.

Use recordings alongside metrics.

Pretty pixels are excellent witnesses.

Terrible statisticians.

---

# Beware survivor bias

Inspection naturally focuses attention on living individuals.

Especially:

```text
oldest
highest generation
best score
```

These individuals are survivors by definition.

If you study only them, you may miss the much larger collection of genomes that failed.

For evolutionary interpretation, population-level outcomes matter alongside champion case studies.

The most impressive surviving critter is interesting.

The thousands of dead relatives are also part of the experiment.

---

# Beware retrospective storytelling

Artificial-life systems are excellent at producing visual patterns that invite explanation.

You may observe:

> “Green discovered the zones.”

Or:

> “Red learned to protect Blue.”

Treat those as hypotheses.

Then ask what measurable prediction follows.

For example:

```text
If Green adapted to beneficial zones,
later-generation Green critters should
occupy or approach those zones more often
than appropriate controls.
```

Now you have something testable.

Evolution does not become more scientific because its story sounds plausible.

---

# A recommended first study

If you want one experiment that exercises most of the system without changing source code, use mutation rate.

## Question

Does mutation probability affect genealogical depth and lineage survival?

## Treatments

```text
1%
5%
20%
```

## Seeds

```text
10 shared seeds
```

## Duration

```text
50,000 ticks
```

That produces:

```text
3 treatments
×
10 seeds
=
30 runs
```

## Record

For each lineage:

```text
final population
maximum generation
longest lifetime
average composite score
extinct: yes/no
```

Then compare treatment distributions rather than individual runs.

That is already a legitimate small computational experiment.

No lab coat necessary.

Spreadsheet recommended.

---

# What not to conclude

Primordial Soup can support statements such as:

> Under this simulation configuration, treatment A produced higher maximum generation than treatment B across these seeds.

It does **not** automatically support statements such as:

> This proves high mutation is bad in nature.

Or:

> Neural organisms prefer cooperation.

Or:

> Evolution always converges toward intelligence.

Primordial Soup studies the consequences of **its own rules**.

Those rules can illuminate concepts from evolutionary computation and artificial life.

They are not a shortcut to universal biological claims.

---

# The experimental loop

A good working pattern is:

```text
OBSERVE
   ↓
QUESTION
   ↓
HYPOTHESIS
   ↓
DESIGN
   ↓
CONTROL VARIABLES
   ↓
CHOOSE SEEDS
   ↓
RUN
   ↓
MEASURE
   ↓
COMPARE
   ↓
INTERPRET
   ↓
REPEAT
```

If the result surprises you:

```text
good
```

If the result survives repetition:

```text
better
```

If the result disappears when you repeat it:

```text
also useful
```

You just learned that the first result was probably history rather than mechanism.

That is still science.

---

# Related documentation

For the mechanics behind the hypotheses:

→ [Simulation](simulation.md)

For selection, crossover and mutation:

→ [Evolution](evolution.md)

For following individual behavior:

→ [Inspection](inspection.md)

For automated reproducible runs:

→ [Headless](headless.md)

For changing experimental laws:

→ [Configuration](configuration.md)

For understanding saved worlds and metric files:

→ [Persistence](persistence.md)
