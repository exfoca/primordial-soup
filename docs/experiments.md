# 🧪 Experiments

Watching Primordial Soup is entertaining. Experimenting with it is more useful.

The difference is whether you can answer:

> What changed, what stayed constant, and would the result happen again?

A colorful population explosion is an observation. A controlled comparison across repeated runs is evidence.

**This is the single authority for experimental methodology.** The mechanics being measured live in [World Rules](world-rules.md); the evolutionary model in [Evolution](evolution.md); the CLI in [Headless](headless.md).

---

# Start with a question

Do not begin an experiment by randomly adjusting parameters.

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

The last one is still fun. It is simply difficult to publish.

---

## One variable at a time

The safest experimental rule:

```text
change one thing
measure several things
```

If Red becomes dominant after you simultaneously changed mutation rate, zone HP effect, selection weights, and reproductive age, you know that something caused something.

For a controlled comparison, change one independent variable while keeping the rest fixed.

---

## Use repeated runs

Primordial Soup is stochastic. Two identical configurations can produce different histories.

Never treat one run as proof.

```text
configuration A     configuration B
seed 1              seed 1
seed 2              seed 2
seed 3              seed 3
seed 4              seed 4
seed 5              seed 5
```

More runs produce stronger evidence. Five runs are much better than one. Twenty are much better than five.

---

## Fix the duration

Comparisons should normally use the same number of simulation ticks.

Do not compare a 5,000-tick run to an 80,000-tick run and conclude that the longer one produced deeper generations.

---

## Prefer headless runs for measurements

GUI is better for observing behavior, inspecting individuals, forming hypotheses, and discovering unexpected patterns.

Headless is better for repeated trials, fixed-duration runs, fixed seeds, parameter sweeps, automation, and reproducible comparisons.

A basic run:

```bash
python -m primordial_soup --new -d 10000 -s world_a --seed 42
```

See [Headless](headless.md).

---

# What can be measured

| Metric                      | What it helps answer                                |
| --------------------------- | --------------------------------------------------- |
| **Population**              | Growing, stable, declining or extinct?              |
| **Average HP**              | How healthy is the surviving population?            |
| **Longest lifetime**        | Are individuals surviving longer?                   |
| **Maximum generation**      | How deep has reproduction progressed?               |
| **Average composite score** | How well is the lineage performing under selection? |
| **Mutation rate**           | What mutation regime was active?                    |

Metrics are sampled periodically. The in-memory history is bounded; saved metrics are more useful for longer analysis.

---

## Metrics answer different questions

Population alone is not enough.

```text
Run A: population 300, maximum generation 7
Run B: population 120, maximum generation 24
```

Which evolved "better"? Cannot be answered from population alone.

A high composite score reflects the **selection function you designed**. It is not an external measure of intelligence.

---

## Record the experimental conditions

For every serious experiment, record:

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

### A simple template

```text
QUESTION
HYPOTHESIS
INDEPENDENT VARIABLE
CONTROL
TREATMENT
CONSTANTS
SEEDS
DURATION
OBSERVABLES
RESULT
INTERPRETATION
LIMITATIONS
```

That last field prevents a surprising amount of nonsense.

---

# Experiments worth running

## Mutation rate

### Question

How does mutation probability affect evolutionary progress?

### Hypothesis

Very low mutation may preserve successful genomes but reduce novelty. Moderate mutation may balance inheritance and exploration. Very high mutation may repeatedly damage useful inherited structure.

### Setup

Compare several rates through the Configuration panel, or through repeated headless runs. Use the same seed set and duration for every condition.

### Observe

Maximum generation, population trajectories, average composite score, longest lifetime, extinction frequency.

### Interpretation

Do not expect a monotonic result. *More mutation = more evolution* is not generally valid. Mutation supplies variation. Selection decides whether that variation persists.

---

## Mutation-free inheritance

Set mutation rate to zero.

Descendants can still differ through crossover, but no new numerical variation is introduced.

### Question

How much evolutionary change can occur through recombination of founder genetic material alone?

A population can continue changing without mutation because crossover reshuffles existing genes. But its accessible genetic search space is restricted to material already present among founders and their recombinations.

This is a useful control condition. It is **not** equivalent to turning evolution off.

---

## Mutation overload

Set mutation rate to maximum.

### Question

Can useful inherited neural structure remain stable when every descendant mutates?

### Observe

Compare against the default mutation regime: population stability, maximum generation, score, extinction, run-to-run variance.

High variance between seeds is itself an interesting result. Chaos can be data. Just not necessarily adaptation.

---

## Beneficial zones

Keep environmental zones active with a positive HP effect.

### Question

Do lineages develop spatial distributions associated with beneficial regions?

### Observe

Look for clustering near zones, population differences, long-lived individuals near zones, repeated occupation patterns.

Use inspection to study individuals inside and outside those regions.

### Caveat

Seeing a cluster inside a beneficial zone does not prove the critters evolved *knowledge that zones are good*. Several mechanisms can generate clustering. Individuals that randomly remain in beneficial regions may simply survive longer.

To claim behavioral adaptation, compare repeated runs and inspect whether evolved controllers systematically produce different movement relative to the environment.

---

## Turn refuges into traps

Begin with beneficial zones. Run long enough for the population to experience them. Then change the zone HP effect from positive to negative.

### Question

How does a population respond when an environmental condition reverses?

The geography remains the same. Only its ecological consequence changes.

### Observe

Population collapse, extinction, changes in spatial distribution, changes across later generations, individual movement near zones.

This separates adaptation to a location from adaptation to what that location does.

Yesterday's paradise becomes today's toxic swamp.

---

## Zones on vs off

Compare zones active against zones inactive while keeping everything else identical.

### Question

Does geographic heterogeneity materially change evolutionary dynamics?

Compare population stability, maximum generations, lifetimes, extinction frequency, spatial clustering.

---

## Selection pressure

The default composite score weights longevity, exploration, interaction, and reproduction.

Changing them changes what evolutionary success means.

### Questions

- Longevity-heavy: do populations evolve toward more conservative behavior?
- Exploration-heavy: do movement rates, encounters, or mortality change?
- Interaction-heavy: does stronger ecological contact emerge, and at what survival cost?
- Reproduction-heavy: does reproductive success become increasingly concentrated?

These require configuration changes. See [Runtime Configuration](runtime-config.md).

---

## Reproductive age

The minimum reproductive age determines how much life history must accumulate before parenthood is even possible.

### Question

How does generation turnover affect adaptation and population stability?

A lower threshold may produce faster generations, more reproductive opportunities, and less lifetime evaluation before reproduction.

A higher threshold may produce slower generations, stronger survival filtering, and fewer eligible parents.

A system producing generations rapidly is not necessarily producing better descendants.

---

## Encounter gate

The minimum encounter count determines how much ecological contact is required before reproduction.

### Question

Does stronger reproductive pressure toward inter-lineage interaction change ecology?

Possible outcomes: more ecological contact, higher mortality, greater clustering, fewer eligible parents, slower population recovery.

A sufficiently strict gate may reduce reproduction dramatically.

---

## Crossover strategy

Primordial Soup supports `blocks`, `uniform`, and `two_points`.

Run the same seed set and duration for each. Do not change mutation simultaneously.

### Question

Which crossover strategy better preserves or recombines useful neural structures?

Because genomes encode neural parameters, contiguous gene structure may matter. Or it may not. That is precisely why this is an experiment rather than an opinion.

---

## Long-run evolution

Run 100,000 ticks or more in headless mode.

### Question

Do metrics continue improving, stabilize, oscillate, or collapse over long periods?

Watch for plateaus, population cycles, repeated extinctions, score stabilization, generation growth, and long-term lineage imbalance.

A long run can expose dynamics invisible at 5,000 ticks. It can also produce a very long example of random history.

Repeat the experiment.

---

## Same configuration, different seeds

Do not change any parameter. Run several seeds.

### Question

How much of the observed outcome is configuration, and how much is stochastic history?

This is one of the most important baseline experiments in the entire project. If identical settings produce dramatically different outcomes, later comparisons need enough repetitions to separate signal from variance.

Before asking *"Does parameter X matter?"*, first learn *"How noisy is this universe when X does not change?"*.

---

## Same seed, changed parameter

Use one seed repeatedly while changing exactly one parameter.

This can help isolate treatment effects. But do not use only one seed. A parameter may interact unusually with one particular random history.

The best design combines both ideas: multiple treatments × multiple shared seeds.

---

## Near-extinction intervention

Let a lineage approach extinction. Then use **Heal all critters** from the Configuration panel.

This resets the HP of all surviving critters to the configured initial HP.

This is not a clean natural-evolution experiment. It is an **intervention experiment**. That distinction should be recorded explicitly.

Note that the global `H` accelerator does not perform this intervention. `H` toggles the floating HUD and has no effect on the simulation. Heal All remains exclusively available through the Configuration panel.

### Question

What happens when accumulated genomes are preserved but immediate survival pressure is suddenly reset?

This can be useful for studying whether a population under severe ecological stress recovers when immediate mortality pressure is temporarily relieved.

Do not compare this directly with untouched runs without labeling the intervention. You played god. Write it in the methods section.

---

## Individual case study

Run a population for a substantial period. Use inspection.

For example, criterion = highest generation, lineage = Red.

Observe the candidate. Follow its trail. Pause and single-step around interesting encounters.

Record HP, age, generation, encounters, offspring, composite score, local vision, and movement pattern.

### Question

Can population-level performance be associated with recognizable individual behavior?

This is exploratory analysis. It is useful for generating hypotheses. It is not sufficient to establish a population-wide evolutionary strategy.

---

## Extinction frequency

Choose one treatment variable. For every seed, record whether each lineage survives to the target duration.

### Question

Does this treatment change lineage survival rates?

Extinction can be treated as an outcome variable. Twenty runs with 2 extinctions is a very different result from twenty runs with 11 extinctions.

Much stronger than *"everyone seemed to die faster"*.

---

# Methodology

## Separate exploratory and confirmatory work

```text
EXPLORATORY   watch, poke, inspect, notice something strange, form a hypothesis
CONFIRMATORY  define treatment, fix seeds, fix duration, repeat, measure, compare
```

The GUI is excellent for the first. Headless runs are excellent for the second.

---

## Save interesting worlds

Use the graphical save slots to preserve memorable worlds.

But save slots are not a substitute for repeated experimentation. Four memorable worlds can still be four anecdotes.

---

## Use GIFs as evidence carefully

Recording is useful for showing behavior, documenting a visual phenomenon, comparing spatial organization, and communicating results.

It is poor as the only quantitative evidence.

A GIF can show *"this pattern occurred"*. It usually cannot establish *"this treatment produces this pattern more often"*.

Use recordings alongside metrics.

---

## Beware survivor bias

Inspection naturally focuses attention on living individuals, especially oldest, highest generation, and best score. These are survivors by definition.

If you study only them, you may miss the much larger collection of genomes that failed.

The most impressive surviving critter is interesting. The thousands of dead relatives are also part of the experiment.

---

## Beware retrospective storytelling

Artificial-life systems are excellent at producing visual patterns that invite explanation.

Treat intuitive explanations as hypotheses. Then ask what measurable prediction follows.

Evolution does not become more scientific because its story sounds plausible.

---

# A recommended first study

### Question

Does mutation probability affect genealogical depth and lineage survival?

### Treatments

Low, medium, high — adjusted through the Configuration panel or across separate headless runs.

### Seeds

10 shared seeds.

### Duration

50,000 ticks.

That produces 3 treatments × 10 seeds = 30 runs.

### Record

For each lineage: final population, maximum generation, longest lifetime, average composite score, extinct yes/no.

Compare treatment distributions rather than individual runs.

No lab coat necessary. Spreadsheet recommended.

---

## What not to conclude

Primordial Soup can support statements such as:

> Under this simulation configuration, treatment A produced higher maximum generation than treatment B across these seeds.

It does not automatically support statements such as:

> This proves high mutation is bad in nature.

Or:

> Neural organisms prefer cooperation.

Primordial Soup studies the consequences of **its own rules**.

---

# The experimental loop

```text
OBSERVE → QUESTION → HYPOTHESIS → DESIGN
   → CONTROL VARIABLES → CHOOSE SEEDS → RUN
   → MEASURE → COMPARE → INTERPRET → REPEAT
```

If the result surprises you: good.

If the result survives repetition: better.

If the result disappears when you repeat it: also useful. You just learned that the first result was probably history rather than mechanism.

---

# Related documentation

→ [World Rules](world-rules.md) — the mechanics being measured
→ [Evolution](evolution.md) — selection, gates, crossover and mutation
→ [Runtime Configuration](runtime-config.md) — every HOT rule you can vary
→ [Headless](headless.md) — running controlled batches
→ [User Interface](ui.md) — observing individuals
→ [Persistence](persistence.md) — saving worlds for later inspection
