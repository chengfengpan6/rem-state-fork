> Historical document. For the current three-route diagnostic and offline review instructions, start with [the repository README](../README.md) and [the 30 October release notes](release_2026-10-30.md). The historical design and results below are retained; they are not instructions for a new live run.

# Technical appendix for the targeted REM map-content diagnostic

*Review draft updated 26 October 2026. Protocol `rem-prototype-0.2-targeted-Y-v1`. This document describes the implemented design, unchanged prospective analysis and completed 30-history diagnostic. It asserts no author approval or journal submission.*

## A1 Purpose and version boundary

The instrument separates a common factual record from a public interpretation of source reliability. Its immediate question is whether a prespecified replacement of that interpretation changes collective forecasts and their conditional expected excess Brier loss when the underlying observations remain available. This is a content intervention in an artificial team workflow, not a complete transactive-memory manipulation or an estimate for human organizations.

The current targeted version uses 30 selected formation histories, five Team arms and two fixed conflicting-signal profiles. It differs from two preserved engineering executions. The 19 October baseline contained 342 responses from one history, three formation and three continuation rounds, ten branches, tied E-map cells and a terminal update. The bounded 25 October revision separately completed 219 responses from one selected history, three formation rounds and one continuation event, twelve branches, split audits and a terminal update. Its 2,232 checks and exact replay support specified recording properties. Its displayed P/E difference occurred in Y, while the single future event was X. Neither old run establishes immediate sensitivity in the changed context, an average treatment effect or behavior after a map update.

The new protocol directly presents two Y cases from isolated copies of each fork. It does not extend either historical tape or pool old observations with the new sample. Its source entry points are `rem_harness/targeted.py`, `tools/run_targeted.py`, `tools/prepare_targeted_histories.py` and `tools/analyze_targeted.py`; configuration and the complete selection log are in `configs/targeted_30histories.json`. The operational source was frozen at commit `358b4eb7f4796437d19de3640ab2f04fac620c2a` before the first new live response. The configuration hash is `4c3cf95715e100156417a7a90d0ece114b415a0d091e8d0bdc2c9d7bef02674e`. Exact execution bytes and the local prospective records are preserved separately from later documentation changes.

## A2 Task and source of ground truth

Each formation event contains a context, a binary outcome and three labeled binary signals. Contexts X, Y and Z occur once each in a shuffled block of three. Outcomes are independent Bernoulli(.5). Given context and outcome, source correctness is independent and stationary:

| Context | Source A | Source B | Source C |
|---|---:|---:|---:|
| X | .85 | .65 | .50 |
| Y | .50 | .85 | .65 |
| Z | .65 | .50 | .85 |

These are investigator-chosen task parameters, not field estimates. There is no globally best source across balanced contexts. Actors know the independent .5 truth process and that reliability varies by context, but do not receive the true matrix. A source is an externally controlled signal channel. The analyst actor initially assigned that source is not intrinsically an expert; its own forecast can differ from the signal's correctness.

The IID process differs from an earlier manuscript's exact truth quotas. Its posterior must not be substituted for a quota-aware benchmark in that older task. The present target cases are fixed hypothetical profiles under the same source-likelihood model. They are not additional generated outcomes. No realized truth is invented for a profile, and no realized Brier score is reported for it.

## A3 Formation and explicit state

Each of the three formation rounds has nine model requests. First, each actor receives its assigned current private signal and produces a probability. Second, all current signals are mechanically disclosed and each actor writes one public message. Third, each actor revises after receiving the messages. Within a stage, actors do not see unfinished responses from other actors. Messages are limited by the response schema to 600 characters; this is not a guarantee of equal tokens or computation. The three revised probabilities receive equal arithmetic weight. Truth and scores enter the historical record only after the forecasts finish.

The archived state separates four objects:

| Object | Stored content | Access and interpretation |
|---|---|---|
| LE | Contexts, signals and realized truths from completed formation events | The common factual ledger; no future truth is present. |
| LB | Formation forecasts, aggregate outcomes and scores | Behavioral history, distinct from source correctness. |
| Pi | Actor-specific signals and decision records | The corresponding actor's historical record. |
| H | A nine-cell reliability map or null | The experimentally replaced external interpretation. |

After formation, each actor reports nine reliability estimates and subjective 90% limits from the frozen state. Three map requests bring formation cost to 30 responses per history. Their coordinatewise median is H0; the individual maps remain saved. This aggregation is a declared measurement operation, not direct observation of spontaneous consensus. The complete LE and LB and each actor's corresponding Pi remain available after the fork. Historical discussion transcripts are saved in traces but are not restored as a continuing conversation.

Forecast and message instructions do not require nine-cell map reporting. That requirement is limited to map elicitation stages. Spontaneous reconstruction or rejection of the supplied map remains possible; R0 is not a prohibition on reliability reasoning.

## A4 Prospective selection and its restricted support

The selector examines integer RNG seeds in ascending order starting at 20261027 and stops at the first 30 eligible seeds, with a maximum of 10,000 candidates. These integers are identifiers, not calendar dates. Previously used seeds 20261019, 20261025 and 20261026 are explicitly excluded, although already below the new lower bound.

For every candidate, only its three exogenous formation rows are used. With one independent Beta(1,1) prior per context/source cell, E0's mean after s correct and f incorrect observations is (s+1)/(s+f+2). Limits are the equal-tail 90% Beta posterior interval. P0 exchanges the complete estimate/lower/upper values of Y:A and Y:B, retaining their destination labels. The other contexts are unchanged. Eligibility is checked on the two-decimal actor-visible version using rational arithmetic on those decimals.

| Fixed eligibility condition | Interpretation |
|---|---|
| E[Y,B] estimate strictly exceeds E[Y,A] | The available evidence ranks the truly better Y source above the worse one. |
| P differs from E at displayed precision in Y | The intended numerical intervention survives rendering. |
| P has strictly greater Y point-estimate MSE against the true matrix | The assigned replacement worsens this declared map-accuracy measure. |
| No X or Z cell changes | The intervention is limited to Y. |

The frozen selection examined 75 candidates and retained 30 seeds. Accepted and rejected ledgers, rendered maps, rational comparisons, hashes and decisions are stored. The retained observable ledgers have distinct hashes; that fact was recorded rather than imposed as a second selection rule. No H readout, model response, future truth or effect sign enters selection. The runtime preflight recomputes the candidate decisions before dispatch.

One observation per context sharply restricts what the selected sample means. In Y, A must have been incorrect and B correct. E therefore displays .33/.67 for A/B and P .67/.33. C is either .33 or .67, producing two Y point-estimate configurations. The 30 histories are not 30 arbitrary maps. Other observations, context order and generated formation behavior vary. The estimand concerns the history distribution induced by this selection and the fixed profiles, not the prevalence or consequences of naturally misleading history in general.

## A5 Five arms and treatment delivery

| Branch | Recorded condition | Initial map |
|---|---|---|
| team_P | P | E0 with Y:A/Y:B complete cells exchanged |
| team_E | E | Unmodified E0 |
| team_H | H | Three-actor median H0 |
| team_R0 | R0 | Null |
| team_R0rep | R0 | A separate copy of the same null-map state |

All branches receive deep copies of the same non-map state. P/E schema, two-decimal display, field structure and neutral provenance match. Condition IDs, planted-error labels, the true matrix and the scoring oracle are not actor inputs. H receives an accurate statement about its formation by the earlier team and common availability. Its comparison with E therefore retains a provenance component; it is not a pure manipulation of endogenous map error.

The repeat branch is distinguished by its research identifier, not by telling actors that they are a repeat. Separate executions are not proof of independent provider random streams. R0 removes only the supplied external table at the fork. Facts, personal records and inference remain available, so H−R0 combines content, format, availability and possible reconstruction effects.

E is an estimate from the available evidence rather than oracle knowledge. Its uncertainty limits are Bayesian credible intervals, while H's limits are model-reported subjective uncertainty. Shared schema does not make these semantics identical. P manipulates estimates and uncertainty together; the primary contrast is not a point-estimate-only treatment.

## A6 Fixed profiles and no carryover

| Profile | Context | A | B | C | Researcher-only posterior |
|---|---|---:|---:|---:|---:|
| Y100 | Y | 1 | 0 | 0 | 21/242 = .0867768595 |
| Y011 | Y | 0 | 1 | 1 | 221/242 = .9132231405 |

The cases place A against B and C; the second complements every signal. Both start from independent state copies of the identical arm-specific fork. “Independent copy” means isolated state, not a statistical guarantee about model sampling. No feedback, score, forecast, message or inferred map from one case enters the other. H is not updated. Both use current round index four because each follows the same three-row formation history.

Each case uses the same nine-call sequence as a formation round, but without appending an event or any post-case feedback. Initial forecasts see the corresponding private signal; messages see all current signals and their author's initial forecast; final revisions additionally see the current messages. Initial and revised responses and full messages are preserved. The result stores final actor forecasts, their mean, the oracle, cBR, and before/after state hashes. The frozen fork must be unchanged after the profile finishes.

At Y100, the true-model likelihood for outcome 1 is .50×.15×.35, and for outcome 0 it is .50×.85×.65; the equal prior cancels on normalization. The resulting posterior is 21/242. Complementation gives 221/242. These values are researcher-side scoring quantities, never actor instructions. The case set is a designed conflict battery, not a natural-frequency sample of all signal patterns or contexts.

## A7 Scheduling and budget

The role/source-list order is selected deterministically by history seed from the six permutations. Profile order and branch order within each profile are shuffled using an independent scheduler with the frozen seed 20261027 and the history identifier. Exact order is archived. This rotates the implemented orderings, not every JSON field position. Two histories were processed concurrently under one coordinator. Branches within a profile remained sequential requests rather than simultaneous model calls.

| Component | Per history | Planned total |
|---|---:|---:|
| Three formation rounds | 27 | 810 |
| Three H0 readouts | 3 | 90 |
| Five arms × two profiles × nine requests | 90 | 2,700 |
| Successful path | 120 | 3,600 |

The formation cap is 32 attempts per history, the branch cap 20 attempts per arm/history and the cumulative global cap 3,660 reservations. Successful execution uses only 30 formation and 18 per-arm responses. The extra budget is not an instruction to spend the cap, add cases or repeat unfavorable results.

A durable ledger, thread-safe within one coordinator process, reserves a dispatch before it is made and preserves earlier attempts through explicit recovery. It has no cross-process lock: operation requires one coordinator, and the earlier process must have stopped before manual recovery. The reservation count is conservative: a reserved attempt can precede an interruption before the provider receives it. Automatic model retries are disabled. A transport, schema or other execution failure stops the affected run, preserving its error. Resume creates a new output root, reuses the compatible saved prefix rather than regenerating completed responses, and carries cumulative attempt accounting. No replacement history or changed treatment is introduced because of observed results. File replacement retries for Windows I/O are distinct from model retries.

## A8 Model transport and observable provenance

The declared live route requests `gpt-5.6-luna` through a ChatGPT-authenticated Codex CLI at low reasoning effort. The provider refuses API-key login and removes inherited API-key variables from the child environment. It does not establish another account's access or API entitlement. Each response uses an ephemeral invocation and a temporary working directory; the adapter requests ignored user rules/configuration, read-only operation, zero project-document bytes, disabled tools/web/apps/skill discovery, and no persistent session.

The record preserves explicit system and user prompts, schemas and their hashes, responses, elapsed time, available usage, CLI version and relevant transport events. These controls reduce extraneous input but cannot attest to the absence of unexposed host/server context. Unexpected action events stop execution. All 3,600 archived responses report `codex-cli 0.162.0-alpha.17.2`; none exposes a served-model ID, and all record the reason `not_exposed_by_cli`. The requested `gpt-5.6-luna` alias is not substituted for that missing identity. Even a returned version string would not prove immutable weights.

Source fingerprints identify the recorded Python and runner/selector files, while the source commit identifies the broader checkout. They do not fingerprint provider weights or all installed binaries. The analysis separately hashes its own source, plan and input files. The project lock specifies dependencies; the frozen environment-validation record supplies the checked local environment, and response traces contain CLI-version metadata. Targeted manifests do not independently enumerate every runtime or dependency version.

The concrete prospective alternative is an OpenAI Responses API adapter requesting the same identifier, subject to verified availability, model/version access, pricing and funding. That route is not configured or tested in this record and will not activate automatically. A later model or transport change requires its own versioned validation and analysis stratum.

## A9 Outcomes and prospective statistical analysis

For history h, arm a and profile j, p[h,a,j] is the mean revised forecast and q[j] the true-DGP posterior. The primary score and contrast are:

```text
cBR[h,a,j] = (p[h,a,j] - q[j])^2
d[h] = mean over Y100 and Y011 of (cBR[h,P,j] - cBR[h,E,j])
Delta = mean across eligible histories of d[h]
```

cBR equals conditional expected excess Brier loss relative to the Bayesian posterior. It is not a realized loss difference after an observed profile outcome. Profiles receive equal weight within a history; histories receive equal weight in the estimate. The statistical sample has at most 30 independent history/fork families, not 60 profiles, 150 arms or 3,600 responses.

The locally archived prospective plan specifies one primary two-sided t test on d[h] against zero at alpha .05, with sample SD, SE, n−1 degrees of freedom and a 95% t interval. The history-level t approximation requires adequate independent sampling and is not guaranteed by N=30. The report gives every difference, median, quartiles, sign counts, extrema and leave-one-history-out mean range. No outlier is deleted or winsorized.

A prespecified 10,000-resample percentile bootstrap of complete history differences uses NumPy PCG64 with seed 20261025 and linear 2.5th/97.5th percentiles. It accompanies rather than replaces the t interval; differing conclusions about inclusion of zero are flagged. Constant differences are labeled degenerate, with no spurious finite t statistic or perfect-population-precision claim. No inferential quantities are produced with fewer than two complete histories or while the execution is nonterminal.

Two exploratory secondary contrasts, H−E and H−R0, use the same nested averaging and two-sided t calculation. Their p values receive Holm adjustment together. Their ordinary 95% intervals are marginal, not simultaneous. Unavailable tests remain members of the two-comparison adjustment family with bookkeeping p=1, while their actual p values remain unavailable. Neither replaces the primary test.

R0rep−R0 is described through the history-level signed discrepancy, SD, mean absolute difference, root mean square and full distribution, plus absolute forecast differences. It combines response variation, schedule effects and potential drift; it is not a universal noise floor or a pure provider variance component. No nonsignificance-as-equivalence test is performed.

For a separate direction diagnostic, the analyzer calculates Bayesian plug-in forecasts using the displayed E and P point estimates as reliabilities. It multiplies each actual P−E probability change by the sign of that profile's ideal P−E change, then averages within history. This prevents complementary profiles from canceling. Positive alignment describes movement toward the replacement's implied direction. It does not show Bayesian reasoning, map endorsement or a latent weight; no p value is assigned.

Each contrast requires both profiles and both relevant conditions. Contrast-specific complete pairs can be retained even if another arm fails, with their actual n and missing IDs reported. Failed histories are not replaced and outcomes are not imputed. For m complete histories out of N=30 with observed difference sum S, the report additionally gives [(S−(N−m))/N, (S+(N−m))/N]. These follow from the missing contrast range [−1,1] and are conservative logical bounds, not confidence intervals. Conditional-on-completion inference does not establish the full planned mean when missingness is informative.

The independent analyzer recomputes aggregate probabilities, the posterior, cBR and branch means rather than accepting a stored score. It rejects duplicate histories/profiles, wrong fixed signals, nonfinite values, malformed actor sets and contradictory completion claims. Its offline unit tests check arithmetic, nesting, multiplicity, missingness, degeneration, repeatability and interim suppression. They do not demonstrate significance or validate artificial actors as social-science constructs.

## A10 Verification, replay and artifacts

The root manifest contains the full configuration, protocol, source fingerprints and execution status. The root summary preserves every planned history, including unstarted or incomplete histories, and points to its actual attempt folder. Each history records formation observations, checkpoint, profile definitions, manifest, summary, call log and event log. A checkpoint contains formation state, the three original H0 readouts, H0/E0/P0, history diagnostics, forks and schedule. Failures and recovery attempts remain distinct records.

| Artifact | Role |
|---|---|
| Root manifest and configuration | Planned sample, treatments, exact profiles, source provenance and limits |
| Root summary | All planned history statuses, attempt paths and final accounting |
| physical_attempts.json | Cumulative transport reservations and budget scopes |
| Per-history formation_tape.json | Three actual exogenous formation events |
| Per-history checkpoint.json | Formation maps, immutable forks and execution order |
| Per-history calls.jsonl and events.jsonl | Requests, responses, errors and semantic event sequence |
| Verification output | Explicit checks and failures for the exact recording |
| Analysis output | History-level effects, uncertainty, missingness, diagnostics and input hashes |

The targeted verifier reconstructs fixed profiles, expected maps, permitted state and requested tasks. It checks that P changes only Y, that no oracle or condition identity enters actor inputs, and that the profile clone does not change or contaminate another case. It recalculates means and scoring and reconstructs the run from stored responses. Semantic replay must match actual requests and regenerate checkpoints and branch results, not merely produce internally consistent hashes. Nine offline fault tests passed before the live execution, including challenges involving missing or wrong maps and histories with recomputed visible hashes. The complete pre-execution suite passed 114 tests; a fresh clone and environment on the same machine also passed. These checks are separate from terminal verification of the live recording.

The independent arithmetic checks and replay share some source components with execution. They are not a cryptographic attestation of the remote provider or proof against coordinated changes to code, configuration and records. Source preservation and external review address a different layer. A completed replay consumes saved responses without new model calls; it does not imply that fresh responses will match. Its transport-accounting fields legitimately differ from live execution.

Illustrative offline review commands are:

```text
python -m pip install -r requirements-lock.txt
python -m unittest discover -s tests -v
python tools/run_targeted.py plan --config configs/targeted_30histories.json
python tools/run_targeted.py verify --recording <targeted-recording> --output <new-verification.json>
python tools/run_targeted.py replay --recording <targeted-recording> --output <new-replay-directory>
python tools/analyze_targeted.py <targeted-recording> --output <new-analysis.json>
```

No command above requests fresh model responses. A new live or recovery invocation is a separate authorized action. Paths in the final anonymous package must match its included files, and transformed exports require their own manifest rather than claims of byte identity with an unmodified original.

## A11 Current evidence and interpretation limits

**Completed on 26 October 2026:** all 30 planned histories and all 3,600 successful responses, with 3,600 physical dispatches and cumulative reservations, zero error rows, zero reused-prefix responses and no retries or replacement histories. Every contrast has 30 complete history pairs and no missing IDs. The final verifier passed 16,568 checks with zero failures and an inventory-bound verification receipt. Offline replay consumed 3,600 stored responses and exactly reproduced request/payload/schema/response records, checkpoints, formation tapes, profiles and branch results, with zero new model calls. Transport accounting necessarily differs between live execution and replay. The final validation status is `validated_complete`; fresh-model replication was not performed.

The frozen analyzer produced the following history-level results. All intervals are ordinary marginal 95% t intervals; the primary p value is unadjusted, while the two exploratory p values are Holm-adjusted together.

| Contrast | Mean cBR difference | 95% t interval | p value | Inferential role |
|---|---:|---|---|---|
| P−E | .21002870 | [.17852399, .24153340] | 3.8328e−14 | Sole primary |
| H−E | −.00025395 | [−.01115678, .01064889] | .96233212 | Exploratory, Holm |
| H−R0 | −.05509228 | [−.07152750, −.03865705] | 3.1400e−7 | Exploratory, Holm |

For P−E, SD=.08437115, SE=.01540399, t(29)=13.63469 and median=.20892608. All 30 history differences are positive, ranging from .02936455 to .38917929; the first and third quartiles are .15530445 and .25010581. The fixed 10,000-resample bootstrap interval is [.18027339, .23987733], agreeing with the t interval about exclusion of zero. Leave-one-history-out means range from .20385109 to .21625850; no observation was removed. Mean cBR by condition is P=.25478708, E=.04475838, H=.04450444, R0=.09959671 and R0rep=.08482445. All-30 missing-outcome bounds collapse to the observed means because no pair is missing; these logical bounds do not replace the confidence intervals.

The mean direction-aligned forecast shift is .29916667 (SD=.10726909); all 30 history averages are positive, with range [.06000000, .52500000]. This is descriptive movement in the replacement-implied direction, not a separately tested mechanism. R0rep−R0 has mean cBR difference −.01477226, SD=.03094520, mean absolute difference .02615442 and RMS .03382167; its range is [−.10081800, .04091570]. Mean absolute profile-level forecast discrepancy, averaged within history, is .05442778. These nonzero repeat discrepancies do not establish equivalence or a universal noise floor.

The primary result supports increased expected excess loss under the specified planted replacement in this selected setting. It does not establish that naturally elicited H is harmful: the exploratory H−E estimate is near zero without proving equivalence, and H has lower loss than R0 on this battery. Provenance, table availability, finite-history estimation and reconstruction remain relevant to those secondary comparisons. Independent arithmetic recomputed actor averages and scoring from the terminal summary and matched the primary test, sensitivity interval and secondary estimates. That arithmetic check does not establish provider independence or construct validity.

The protocol does not test the earlier representative-versus-misleading-history crossover, correction after allowed updates, persistence across a future horizon, an architecture interaction, or recovery of w/lambda from real responses. The deliberately selected Y pattern cannot establish how often natural H becomes harmful. A positive planted contrast is compatible with numerical copying or attention effects; a null contrast can be compatible with correct resistance to the supplied error. These possibilities require delivery evidence and the separate measures, rather than relabeling whichever result occurs.

Future work may broaden histories, validate the formation link, observe post-update forecasts and add matched exchange controls. Each change requires a separately frozen target and analysis. The current code's ability to represent a larger design is not evidence that it has been executed, and 30 histories do not retroactively power that future study.

## A12 Disclosure, access and rights

Inputs are synthetic and actors artificial. This does not invent an institutional ethics exemption or approval number. AI used as an experimental system is distinguished from AI assistance with code, analysis, source review and writing in the proposal and submission preparation. Authors remain responsible for the final statements; this appendix is not their signed attestation.

The review artifact should contain original software, tests, configurations and shareable synthetic research traces, with private correspondence, recordings, third-party manuscript attachments and credentials excluded. The repository's MIT scope applies to original software, tests, configurations, schemas and original software documentation. It does not claim ownership of model weights, third-party services or all model outputs, and it does not license the separately submitted manuscript. Existing dependency notices remain intact.

Anonymous review copies require removal of identifying development links and metadata without falsifying attribution or claims of byte identity. A local ZIP does not establish anonymous external access. The final artifact should specify any unavailable provider dependency and retain a usable offline review path. The related SIGDSA work, actual overlap, funding, conflicts, ethics and unrecorded AI use require accurate final author disclosure.

The organizational rationale and source-reading limits are in `docs/scenario_and_identification.md` and `docs/targeted_protocol_2026-10-25.md`; the exact prospective statistical commitments and official method references are in `docs/targeted_analysis_plan_2026-10-25.md`. None of those references supplies a universal N=30, the three-round horizon or the numerical signal matrix.
