> Historical document. For the current three-route diagnostic and offline review instructions, start with [the repository README](../README.md) and [the 30 October release notes](release_2026-10-30.md). The historical design and results below are retained; they are not instructions for a new live run.

# Proposed next measurement pilot: 7,314 responses, not run

The archived 3+3 smoke verifies a short execution. The next scientific need is to
observe behavior after map updates and diagnose measurement, before any
confirmatory study or 24+84 full design. The following is a concrete recommendation,
not an accepted budget, preregistration, or evidence of execution.

## Why the original budget cannot simply be inherited

The ten-branch, 24+84 offline candidate with fork and seven checkpoints, all map
audits and independent probes of all 24 context/signal profiles requires
**12,153 responses for one seed** under this implementation. Running six such
seeds would require 72,918 responses. A historical estimate of 6,000–8,000 total
pilot calls cannot support that whole design. Exact counts follow the declared
call graph; they exclude transport failures, repeated measurements, and any
later scope changes. Tokens and subscription limits are separate constraints.

## A bounded measurement design

Use six prespecified natural histories. Form each with 24 team rounds, then run
24 future rounds. Update maps after post rounds 12 and 24. This is a **shorter
measurement pilot**, not the proposed 84-round outcome horizon.

- All six histories: Team H and R0.
- Two histories fixed before outcomes are examined: additionally Team E and RU.
- Read-only map audits at fork, post 12, and post 24, before updates.
- Independent no-feedback probes for all 24 context/signal profiles at fork and
  post 24 only. Each profile receives a fresh unchanged state.
- The post-12 map update is followed by 12 real decision rounds.
- No new architecture factor in this pilot; the short smoke already checks
  those code paths. Their scientific comparisons remain a later module.

| Component | H/R0 history | H/R0/E/RU history |
|---|---:|---:|
| Formation 24×9 plus three initial map reads | 219 | 219 |
| Future decision stages | 432 | 864 |
| Map audits: three checkpoints | 18 | 36 |
| Map updates: two checkpoints | 12 | 24 |
| Independent probes: two checkpoints | 288 | 576 |
| Total per history | **969** | **1,719** |
| Histories of this type | 4 | 2 |
| Subtotal | **3,876** | **3,438** |

**Combined successful path: 7,314 calls.** The two files cap attempted calls at
3,876 and 3,438 respectively. Their sum is 7,314 for one execution of each file;
there is no persistent cross-run account counter preventing repeated launches.
A possible overall ceiling of 8,000 would leave 686 calls outside these configs,
with no automatic use of that reserve. The current runner stops at the first
error and does not resume. Both configurations remain disabled for live use.

The two saved configurations use proposed seeds 20261101–20261106, which cover
six source-list/message-order permutations. Their outcomes have not been
generated or screened for this recommendation. This does not balance every JSON
label position or guarantee informative misleading histories. The current smoke
runs whole branches in a fixed sequence, so branch differences may also reflect
backend changes over time. The next implementation should prespecify balanced
branch order across histories, with round-level interleaving where feasible; that
scheduler is not implemented in v0.1.

```sh
python -m rem_harness plan --config configs/pilot_pair_4seeds_offline.json
python -m rem_harness plan --config configs/pilot_fourarm_2seeds_offline.json
```

Both files have `live_allowed=false`. The schema's existing
`formal_candidate_offline` purpose value denotes a blocked longer-run
configuration; it does not make these pilot files confirmatory designs. The live
CLI also rejects horizons above three rounds and independent full-profile probes.
No script in this repository automatically lifts those guards.

## Model and execution continuity

For the first measurement pilot, retain the same requested GPT-5.6 Luna alias,
low reasoning setting, explicit templates, and documented official transport to
keep the comparison with the smoke interpretable. Record CLI version, execution
time, available backend metadata, and actual tokens for every response. This is
a recommendation, not a claim that an immutable model snapshot is available.
A transport or model change requires renewed validation and must not be silently
pooled with the earlier configuration. A call budget does not establish sufficient
subscription allowance: 24+24 states are longer than 3+3 states, so smoke token
usage must not be linearly extrapolated as an exact quota or cost estimate.

## What this would and would not answer

The pilot can expose map formation, parser failures, probability rounding,
post-update behavior, audit/probe consistency, practical token demand, and whether
the proposed measurement scheme has usable variation. Six histories are not a
defensible confirmatory sample or a well-powered test of M→H, mediation, crossover,
or architecture moderation. E/RU observations on two histories are diagnostics.
They must not be pooled with all six as if every condition had equal coverage.

Select no seeds by their model-generated maps or outcomes. Preserve all failures.
Use pilot evidence to decide whether a larger measurement/recovery phase is
needed, then separately plan the final 84-round study's independent sample size.
This sequencing follows the distinction between verification and validation
in [Davis et al. (2007)](https://doi.org/10.5465/amr.2007.24351453) and precision-based
planning in [Maxwell et al. (2008)](https://doi.org/10.1146/annurev.psych.59.103006.093735).
Neither paper prescribes six histories, these checkpoints, or this call budget.
