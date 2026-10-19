# Scientific protocol and implementation choices

Protocol identifier: `rem-prototype-0.1-iid-initialized-median90`.

This repository implements an experimental instrument for studying inherited reliability maps. It does not establish that inherited maps help, harm, or persist in language-model teams. A successful live smoke run establishes a narrower fact: a specified model executed the declared sequence, produced the recorded outputs, and passed the reported engineering checks. Consult the run manifest for actual coverage and completion; a configured branch is not necessarily a completed branch.

## 1. Research question

The proposed study asks whether initializing an external memory with a team's interpretation of earlier evidence changes subsequent probabilistic judgments when the underlying observations and future evidence are held fixed. The memory object is a small context-by-source reliability map. It is not a complete transactive memory system, all organizational knowledge, or an instruction about whose advice must be followed.

Three links require separate evidence:

1. Early random histories produce differences in the maps actors actually form.
2. Inherited maps affect reported reliability beliefs, enacted cue use, or subsequent map updates.
3. Those changes affect prediction quality.

Agreement is not accuracy, recall is not behavioral use, and a performance difference does not identify a unique psychological mechanism. These distinctions draw on research on transactive memory, organizational learning, and forecast evaluation [1–7, 10]. The experiment provides a controlled synthetic setting; it does not by itself establish effects in human organizations or deployed agent systems.

## 2. Research-design provenance and changes

The earlier research design specified three role-bearing actors, a 24-round common history, an 84-round future, and matched Team/Solo contrasts between an inherited map and an `unknown` map. The present prototype makes several previously unspecified choices and adds controls. These are transparent implementation decisions, not parameters established as optimal by the cited literature.

| Element | Earlier design | Prototype choice and limitation |
|---|---|---|
| Map lifecycle | Frozen fork map; subsequent reconstruction mentioned but underspecified | Default: initialized, mutable block memory; separate standing mode |
| Baseline | Nine-cell `unknown` object | Distinguish `RU` from `R0`, which has no map object |
| Mechanical map | Not a principal treatment | `E` initializes the map from the same observed ledger's Beta posterior |
| Truth sequence | Truth and contexts balanced in 12-round macroblocks | IID Bernoulli(.5) truth; contexts balanced in groups of three |
| Map formation | A team produces a fixed-schema map | Three independent map responses, followed by a coordinate-wise median |
| Confidence | Confidence values, without a complete operational definition | A point estimate and subjective 90% uncertainty limits |
| Communication | Bounded message per actor, then revision | Synchronous messages; actors cannot see peers' messages while generating their own |
| No-message control | Suggested removal of peer messaging | Private memo in the same response stage, preserving the number of calls |
| Solo/nominal | One full-information Solo; additional nominal benchmark proposed | Independent Solo plus three independently maintained full-information nominal actors |
| Smoke horizon | Not part of the scientific design | Three formation rounds and three future rounds; noninferential |

The context/truth change matters. If a fixed truth quota is known and past truths are observed, the prior for a later round can depend on the remaining quota. IID truth makes the .5 prior unambiguous. It sacrifices exact truth balance and is therefore not a literal replication of the earlier sequence design. The 24+84 configuration remains an **offline candidate**, not an authorization or validation of a full live study.

## 3. Synthetic task and oracle

Each round has a binary truth, a context, and three role-labelled binary signals. Conditional on truth and context, signal correctness is independent across sources. Reliability is stationary:

| Context | Source A | Source B | Source C |
|---|---:|---:|---:|
| X | .85 | .65 | .50 |
| Y | .50 | .85 | .65 |
| Z | .65 | .50 | .85 |

Each source has the same average reliability over balanced contexts. No source is best everywhere. A source's reliability is a property of its signal channel, not proof that the actor assigned to that channel is intrinsically more capable.

The generator fixes the complete event tape before actor calls. It samples independent Bernoulli(.5) truths and independent correctness draws under the matrix. Contexts occur once each in a shuffled three-round block. At the formal candidate horizon, this gives eight observations per context before the fork and 28 afterward.

The oracle computes the posterior probability of truth using the true reliability matrix and current signal vector. The matrix, oracle probability, future events, misleadingness statistic, branch labels, and researcher diagnostics are excluded from actor payloads. Actors know the task's IID truth rule and that reliability is stationary and context-dependent; they do not receive the reliability values.

## 4. State and information boundaries

Calls are stateless. The assembler supplies the permitted state explicitly:

| Slot | Content | Important boundary |
|---|---|---|
| `LE` | Observed contexts, role-labelled signals, and revealed truths | No future outcomes or true reliability matrix |
| `LB` | Forecasts and scores generated in the branch | These are endogenous; they may differ after treatment |
| `Pi` | The actor's own records and, where applicable, labelled founder records | A new solo does not claim to have personally made the founders' predictions |
| `H` | Current reliability map, unknown-valued map, or null | Its lifecycle is part of the intervention |

Past messages and private memos are archived but not restored into the next round. Forecast and score histories can nevertheless carry effects of earlier map exposure. Removing a named map field does not remove every possible causal carrier of that map's influence [5–7].

Matched branches begin with the same permitted pre-fork history. They reuse the same future exogenous tape and scoring rules. They are **not** required to have identical subsequent forecasts, scores, or updated maps: such divergence can be the treatment effect. Isolation checks must distinguish unplanned input differences from legitimate endogenous changes.

The no-peer-message architecture still has shared observations, shared branch behavior records, and a shared map. It is not an absence of every communication or social-information channel.

## 5. One round in each architecture

### Interactive Team

1. Each of three actors predicts privately using its current private signal and permitted history.
2. The program discloses all three labelled signals mechanically.
3. Each actor generates one bounded message without seeing the other actors' messages from that stage.
4. Each revises its probability after receiving all three messages.
5. The program takes the unweighted mean of the revised probabilities.
6. Truth is revealed, scores are computed, and records are updated.

This entails nine successful model calls per round. It studies interpretation after mechanical disclosure, not voluntary information search or strategic withholding. Equal aggregation fixes the explicit weights on final actor forecasts; it does not fix how each actor uses the three sources [2].

### No-peer-message

Roles, initial private signals, mechanical disclosure, revision, and final averaging remain. The middle stage produces a private memo instead of a peer-visible message. Revision receives only the actor's own memo. This preserves nine calls per round, but does not guarantee equal realized tokens or equal cognitive effort.

The private-memo substitution is an implementation choice. A literal deletion of the middle calls would be a different computational control. Neither comparison independently identifies common knowledge that the map is shared.

### Full-information Solo

A separate single actor receives the complete signal vector from its first forecast stage. It produces an initial forecast, private memo, and final forecast: three calls per round. It is not three roles simulated inside one discussion, nor an average of three outputs.

At the fork, founder records from A/B/C remain explicitly labelled as historical records. The solo starts its own trajectory. Its exact information path and computation differ from the Team; the comparison is an architectural boundary, not a pure treatment of interaction.

### Nominal team

Three full-information solo actors run separately, each with initial forecast, private memo, and revision. They share the exogenous tape and initial evidence, but cannot read one another's post-fork memos, predictions, or private map updates. Their final probabilities are averaged for scoring.

The implementation uses an independent Solo branch rather than reusing a nominal constituent. Nominal averaging entails nine calls per round. Score the average forecast itself; averaging the three individual losses answers a different question [8–9]. Separate instances are operationally isolated, but shared model and evidence can still produce correlated errors.

## 6. Map construction and treatments

### Schema and formation

There are exactly nine `(context, source)` cells. Each numeric cell has:

```text
estimate: a probability in [0, 1]
lower: lower subjective 90% uncertainty limit
upper: upper subjective 90% uncertainty limit
constraint: lower <= estimate <= upper
```

The uncertainty refers to source reliability, not an interval for the next binary outcome. A valid response contains no ranking instruction, deference rule, or prose lesson. The implementation does not claim that subjective intervals are calibrated confidence intervals.

The formation phase begins without a persistent public map. After the common history and its final feedback, the three actors independently report maps. The program computes the median of the three estimates, lower limits, and upper limits in each cell. This creates `H0` without adding a model-based editor. It is a reproducible aggregation rule, not evidence that the actors reached consensus. The original individual reports remain available for analysis.

### Four initial map conditions

| Condition | Fork input | Meaning |
|---|---|---|
| `H` | Agent-generated `H0` | Inherit the team's summary |
| `E` | Code-computed map from the observed ledger | Initialize using a reproducible evidence summary |
| `RU` | The same nine-cell object with null estimates and limits | Expose the actor to an unavailable-estimate object |
| `R0` | `H: null` | No map object, while retaining the explicit state-slot interface |

For `E`, each cell has a Beta(1 + correct count, 1 + incorrect count) posterior. The displayed point is its mean; limits are its .05 and .95 quantiles. It does not contain the true reliability matrix. Finite evidence can make this map inaccurate about the environment.

The point/interval schema aligns the display format across `H` and `E`, but subjective uncertainty and a specified Bayesian posterior are not psychologically equivalent. Their contrast initially identifies a **summary-policy difference**. Calling it pure interpretive distortion requires stronger evidence about display, provenance, confidence, and use.

**Current limitation:** `R0` uses a null slot and no token-matching padding. `RU` is a larger structured object. The smoke therefore does not establish a length-controlled absence-versus-unknown effect. Token length, placement, and padding sensitivity require explicit validation before a confirmatory claim. Null is not converted to .50; any actual model response to it must be observed.

## 7. Two lifecycle modes

### Default: `initialized_update`

The selected fork object initializes the current map. Subsequent calls read that current state. At update points, actors can reconstruct it from their allowed current state and accumulated evidence. Archived `H0` is retained for researcher comparisons but is not separately replayed to actors.

This is **mutable block memory**, not strict one-time exposure. Before the first update, a numeric current map remains equal to its initial value and is repeatedly available. The prototype's scientific target is an initial-condition intervention in an external memory system.

All four map conditions have the same update opportunities. `R0` and `RU` can acquire numeric maps at the first update; `E` is not automatically replaced by a fresh code posterior each round. Comparing a frozen `H` with continually refreshed `E` would combine different policies and would not isolate initial summary content.

The smoke updates after three future rounds. The offline 24+84 candidate updates every 12 future rounds. These intervals are explicit implementation choices, informed by cost and inspectability, not literature-derived optima [13].

### Alternative: `standing`

The fork map remains unchanged throughout the future and no live map updates occur. `R0` remains null. This mode tests continuously available fixed summaries and can support implementation checks against frozen-map reduced forms. It is a different policy from initialized-update, not proof of memory after the stimulus disappears.

### Checkpoint ordering

At a scheduled checkpoint:

1. Finish the round, reveal truth, and update event/behavior records.
2. Clone the **pre-update** state for audits and probes.
3. Run readonly measurements with no feedback or writeback.
4. In initialized-update mode, independently obtain live map-update responses.
5. Team/no-message: median-combine the three updates into one current map. Solo: use its own update. Nominal: keep each actor's update separately.

Measuring before the new shared median is displayed avoids treating immediate common exposure as evidence of independently shared beliefs. Audit responses are not reused as live updates. Updated maps and individual update responses are stored separately. Literature on temporal specification motivates explicit ordering, but does not prescribe this particular schedule [1, 4, 13].

## 8. Branch scope, probes, and execution status

The standard smoke configuration contains ten branches: Team H/R0/E/RU and Solo, no-message, and nominal H/R0. It is not a full four-by-four factorial. The presence of ten entries is a plan; actual successful branches must be read from the resulting run files.

The smoke uses three formation and three future rounds. It audits at the final future checkpoint. Its probe default batches the eight signal profiles for **context X** into one response per actor. A batch is a convenient diagnostic of schema and measurement routing. It is **not** eight independent interventions: the model sees the profiles together, and no complete three-context behavioral-weight claim follows.

The offline candidate requests fork and 12-round checkpoints and separate calls for all eight profiles in each of three contexts. Each independent profile starts from the same unchanged checkpoint state. That mode is restricted to offline execution in the current prototype. A configuration requesting it is not evidence that it has been run with live actors.

Source-list, actor-call, and message ordering use a seed-linked role permutation. This does not guarantee all occurrences of role labels are position-balanced: canonical JSON keys and map-cell ordering can remain fixed. A full positional-bias control needs additional prompt-level inspection and validation.

## 9. Outcomes and recommended analysis

The implementation stores realized Brier score `(p-y)^2` and conditional Brier regret:

```text
cBR = (p - p_oracle)^2
```

cBR is not the realized difference between two Brier losses on every outcome. The connection holds in the relevant conditional expectation under the oracle model. Proper scores evaluate probabilistic quality; they do not by themselves identify how relative source weights changed [10].

The recommended future primary direct estimand is the matched-seed difference in mean post-fork cBR between Team H and Team R0 under initialized-update. Team H−E and RU−R0 are key secondary policy contrasts. This is a recommendation, not a preregistered analysis or a result of the smoke. Primary/secondary families, inferential procedure, smallest relevant effect, missingness handling, and confirmatory sample size require a separate locked study plan.

Map error against the true matrix, divergence from the evidence-only posterior, adherence to initial `H0`, between-actor dispersion, and behavioral response surfaces answer different questions. No effect or no significant effect does not prove map non-use. The earlier sharedness prediction additionally required lower dispersion, greater proximity to `H0`, and greater distance from the evidence map after a corrective opportunity. Histories without such an opportunity must not simply be removed from performance analysis.

The signed history statistic `M` is computed from exogenous prehistory evidence, not from actor output. It is a candidate moderator and stratification variable, not a substitute for measuring the actual map. Both historical reference quintile means are negative, approximately −.713 and −.267; the latter is a less diagnostic region, not guaranteed overall misleading evidence or a guaranteed harmful map.

Fixed-map pseudo-weight models can be checked in standing mode. Their parameters cannot be carried unchanged into a model with endogenous `Ht` updates. Ledger-based estimation can also inherit uncertainty from a noisy first-stage estimate of ledger reading. Recovery under a scripted generating model is not identification in real actors [11–12, 14].

Behavioral analyses should preserve raw profile probabilities and separate overall response scale, relative cue profile, and interactions. Batched X-only smoke probes do not validate that measurement model. A future complete probe implementation should assess rounding, degenerate probabilities, additive-model fit, interactions, and whether reported reliability corresponds to enacted cue use.

## 10. Failure and reproducibility rules

Responses are strictly validated. The current implementation does not coerce malformed JSON, clip invalid probabilities, repair intervals, substitute .50, or silently retry failed model calls. The first error stops the run and must be represented as failure or partial completion. Researchers should not discard failures merely because they occur in a theoretically inconvenient condition.

Successful-path call counts exclude failures and any later policy changes. The same stage count does not establish equal realized tokens, cost, or reasoning effort. Runtime limits, actual model identity, backend metadata available to the adapter, raw responses, state hashes, and completion status should be reported from artifacts rather than inferred from a model name or configuration.

Evidence levels remain separate:

- **Scripted verification:** known-answer checks of computation, routing, and state isolation.
- **Live smoke:** a short execution of the declared workflow with a real model.
- **Technical pilot:** enough complete trajectories to diagnose measurement, formation, errors, and cost.
- **Confirmatory research:** a locked study with justified sampling, estimands, inference, and independent units.

A smoke cannot determine whether 180 histories are sufficient, validate a map-error mechanism, or estimate a reliable crossover. Sample planning should address both power and precision, with the actual dependence and error-control procedure [12]. The independent experimental unit is the matched prehistory realization, not the number of actors, cells, rounds, or probes.

## 11. Published foundations and access boundaries

These 14 journal sources supported the bounded design review. FT50 eligibility was cross-checked through current institutional lists; the AJG/CABS entries below include public and institutional secondary evidence rather than an authenticated ratings export. A journal's ranking does not make it a source of REM-specific numeric settings. Access descriptions distinguish inspected text from unobtained full articles.

1. **Brandon, D. P., & Hollingshead, A. B. (2004).** Transactive Memory Systems in Organizations: Matching Tasks, Expertise, and People. *Organization Science*, 15(6), 633–644. [DOI](https://doi.org/10.1287/orsc.1040.0069). FT50; publisher abstract inspected. Supports distinguishing accuracy, sharedness, and participation; no claim to full-text verification.
2. **Hollenbeck, J. R., et al. (1995).** Multilevel theory of team decision making: Decision performance in teams incorporating distributed expertise. *Journal of Applied Psychology*, 80(2), 292–316. [DOI](https://doi.org/10.1037/0021-9010.80.2.292). FT50; abstract and original-page/figure previews inspected. Supports careful separation of information, recommendations, and aggregation; detailed original operationalization is not claimed as fully reviewed.
3. **Lewis, K., Belliveau, M., Herndon, B., & Keller, J. (2007).** Group cognition, membership change, and performance: Investigating the benefits and detriments of collective knowledge. *Organizational Behavior and Human Decision Processes*, 103(2), 159–178. [DOI](https://doi.org/10.1016/j.obhdp.2007.01.005). FT50; abstract and section extracts inspected. A human-team precedent for inherited structures and process mismatch, not direct evidence of REM effects.
4. **March, J. G. (1991).** Exploration and Exploitation in Organizational Learning. *Organization Science*, 2(1), 71–87. [DOI](https://doi.org/10.1287/orsc.2.1.71). FT50; original pp.74–76 inspected. Supports separating an organizational code from individual beliefs; its feedback assumptions differ from this task.
5. **Levitt, B., & March, J. G. (1988).** Organizational Learning. *Annual Review of Sociology*, 14. [DOI](https://doi.org/10.1146/annurev.so.14.080188.001535). AJG 4* in cross-checked public/institutional records; original pp.319–320 and 323–327 inspected. Supports separating experience, interpretation, and memory carriers. Original pagination 319–340 differs from current publisher metadata 319–338.
6. **de Holan, P. M., & Phillips, N. (2004).** Remembrance of Things Past? The Dynamics of Organizational Forgetting. *Management Science*, 50(11), 1603–1613. [DOI](https://doi.org/10.1287/mnsc.1040.0273). FT50; author-posted original-text transcription inspected. Supports defining what is removed and what remains; does not establish that resetting is beneficial.
7. **Tsang, E. W. K., & Zahra, S. A. (2008).** Organizational unlearning. *Human Relations*, 61(10), 1435–1462. [DOI](https://doi.org/10.1177/0018726708095710). CABS 4 journal statement and public-record cross-check; original-text transcription inspected. Supports the distinction between representation replacement and discarding action routines. The journal is not labelled current FT50 here.
8. **Larrick, R. P., & Soll, J. B. (2006).** Intuitions About Combining Opinions: Misappreciation of the Averaging Principle. *Management Science*, 52(1), 111–127. [DOI](https://doi.org/10.1287/mnsc.1050.0459). FT50; author manuscript, particularly manuscript p.26, and publisher abstract inspected. Supports scoring mechanical aggregation as a comparator. A published erratum concerns figure/table labels; those numerical displays are not used here.
9. **Sniezek, J. A., & Henry, R. A. (1989).** Accuracy and confidence in group judgment. *Organizational Behavior and Human Decision Processes*, 43(1), 1–28. [DOI](https://doi.org/10.1016/0749-5978(89)90055-1). FT50; publisher abstract only. Supports distinguishing interactive judgment and statistical combination; no claim to replication of the article's detailed procedure.
10. **Gneiting, T., & Raftery, A. E. (2007).** Strictly Proper Scoring Rules, Prediction, and Estimation. *Journal of the American Statistical Association*, 102(477), 359–378. [DOI](https://doi.org/10.1198/016214506000001437). AJG 4 public-record cross-check; original pp.359 and 362–365 inspected. Supports proper probability evaluation and distinctions among forecast-quality concepts.
11. **Edwards, J. R. (2001).** Ten Difference Score Myths. *Organizational Research Methods*, 4(3), 265–287. [DOI](https://doi.org/10.1177/109442810143005). AJG 4 public-record cross-check; original pp.265–268 inspected. Supports explicit measurement-error reasoning; it does not invalidate a randomized paired treatment difference.
12. **Maxwell, S. E., Kelley, K., & Rausch, J. R. (2008).** Sample Size Planning for Statistical Power and Accuracy in Parameter Estimation. *Annual Review of Psychology*, 59, 537–563. [DOI](https://doi.org/10.1146/annurev.psych.59.103006.093735). AJG 4 public-record cross-check; original pp.537–546 inspected. Supports planning for the intended effect, precision, and analysis rather than inheriting an arbitrary sample count.
13. **Mitchell, T. R., & James, L. R. (2001).** Building Better Theory: Time and the Specification of When Things Happen. *Academy of Management Review*, 26(4), 530–547. [DOI](https://doi.org/10.5465/amr.2001.5393889). FT50; original pp.532–533 and 536–537 inspected. Supports explicit exposure, change, and measurement timing; it does not prescribe a 12-round interval.
14. **Davis, J. P., Eisenhardt, K. M., & Bingham, C. B. (2007).** Developing Theory Through Simulation Methods. *Academy of Management Review*, 32(2), 480–499. [DOI](https://doi.org/10.5465/amr.2007.24351453). FT50; Table 1 and verification/validation passages inspected. Supports separating computational representation and checks from empirical validation.

The cited theories motivate distinctions and tests. They do not prove novelty, prescribe the model provider, or establish that this prototype's behavior generalizes beyond its synthetic task.
