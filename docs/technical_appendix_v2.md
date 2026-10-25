# Technical appendix for the REM research instrument

*Submission-facing review draft, 25 October 2026. Implementation reference: commit `0af0368`, protocol `rem-prototype-0.2-iid-planted-split-audit`. The bounded live run completed 219 responses and passed its recorded checks. This appendix accompanies the Stage-1 proposal and distinguishes implemented operations, this noninferential engineering execution, and the later scientific study.*

## A1 Purpose and version scope

The instrument asks whether changing an inherited, collectively accessible reliability interpretation changes subsequent judgment when the factual history remains available. It separates a source-observation ledger, behavioral records, personal records and an external map, branches from a common checkpoint, and provides matched future external evidence. The organizational object is a context-specific reliability representation. It is not a complete transactive memory system, a model of all human memory, or an estimate of effects in human organizations.

Three layers must remain separate. The historical version produced a 342-response real-model smoke on 19 October, using three formation and three future rounds over ten branches. The 25 October version adds P interventions, split audits, stage-specific instructions, scheduling, provenance, and stricter verification. A later adequately sized scientific study is proposed but has not been completed. Historical evidence is retained without rewriting its prompts or outputs to resemble the revised protocol.

The revision's selected configuration is `configs/bounded_v2_smoke.json`. Its configuration hash is `cb339b1b994b7f4bf869489db6f5391968c8347575723cdd10500752e4feaf06`; the run-start combined package-source hash is `5c9431920db705c149636c6c4fb84d139e57cb00a183edda303f0792f179d4d1`. The latter hashes the `rem_harness/*.py` files, not every repository file, installed dependency, CLI binary or provider-side component. The Git commit identifies the broader source snapshot. These identifiers should accompany the final review artifact and be reconciled if a later repair changes the implementation.

## A2 Task and researcher-side truth

Each event has a context X, Y or Z, a binary truth, and three labeled binary signals A, B and C. The generator shuffles one occurrence of each context within blocks of three. Truth is independently Bernoulli(.5) on every round. Conditional on truth and context, source correctness is independently drawn using the following stationary matrix.

| Context | Source A | Source B | Source C |
|---|---:|---:|---:|
| X | .85 | .65 | .50 |
| Y | .50 | .85 | .65 |
| Z | .65 | .50 | .85 |

There is no globally best source across balanced contexts. The cyclic structure makes reliability attribution context-dependent, while the finite formation history allows uncertainty. These numbers are design choices, not estimates from a field setting or values prescribed by organizational theory.

The true matrix and full future tape are researcher-side objects. Actors receive a stationary-but-unknown reliability description and the known .5 truth process. They do not receive the true matrix, oracle forecast, seed-selection diagnostics, condition labels or future truths. The current design uses IID truths rather than the earlier manuscript's exact truth quotas. This distinction matters because a quota can create a history-dependent prior; numerical results from that earlier generator are not transferred to the present task.

V2 permits a future horizon that ends inside a context block. Its one-future-round engineering run is a prefix of the same generator, not a balanced one-round experiment. The formation phase remains three rounds, one per context. A separate pseudorandom stream determines branch scheduling so that changing branch order does not change generated events.

## A3 State objects and actual information access

| Object | Stored content | Actor access and scientific meaning |
|---|---|---|
| `LE` | Completed contexts, disclosed source signals and realized truths | All completed factual events permitted by the protocol; no future outcomes. |
| `LB` | Final forecasts, Brier scores and aggregate outcomes | Shared pre-fork behavior; nominal members receive only their own post-fork behavioral records. |
| `Pi` | Own past forecasts and signals, plus labeled founder archives where applicable | Actor-specific records; solo and nominal actors receive the founders' pre-fork records as an archive, not as their own actions. |
| `H` | Current nine-cell map, absent object, or unknown-valued schema | The manipulated representation. An absent map does not erase the other state objects. |

The initial forks are deep copies. Within an architecture, conditions start with matched non-map history. Solo and nominal forks use explicitly documented projections of the founders' records, so across-architecture inputs are not described as literally identical. After treatment, forecasts, scores, messages and updates may diverge; matched future evidence does not require identical endogenous records.

Every live response is a fresh invocation supplied only the constructed payload and requested instructions, subject to the provider-context limitations in A9. Past messages are preserved in research traces but not restored as a continuing conversation. Team messages are available to teammates for the current round's revision; private memos are visible only to their author. Records are described as data rather than instructions.

The code's `independent_snapshot_clones` label denotes isolated state copies. Repeated calls on such copies are not asserted to draw independently from the provider's internal random process.

## A4 The round and four architectures

Within a branch, responses are collected synchronously by stage. All initial forecasts are collected before messages or memos, and all those texts precede final forecasts. Later actors at the same stage do not receive earlier same-stage responses. The outcome is appended only after every final forecast for that round has completed.

| Architecture | Initial evidence | Middle stage | Final forecast and aggregation | Calls per round |
|---|---|---|---|---:|
| Team | Own assigned source signal | All signals disclosed; each actor writes a peer-visible message | Three revisions, equal arithmetic mean | 9 |
| No-message | Own assigned source signal | All signals disclosed; each actor writes a private memo | Three revisions, equal arithmetic mean | 9 |
| Solo | All three signals | One private memo | One revised forecast | 3 |
| Nominal | All three signals for each of three separately maintained actors | Three separate private memos | Three revisions, equal arithmetic mean | 9 |

Messages and memos are limited to 600 characters by the response schema. This is not a token-equivalence guarantee. Mechanical disclosure fixes the availability of current signals before discussion, making interpretation after disclosure the focus. The task does not study endogenous information sharing or concealment.

No-message retains shared records and shared median map updates. It therefore removes within-round peer-message exchange, not every coordination mechanism. Solo changes the number of actors and the information path; nominal changes the number of full-information forecasts averaged and keeps post-fork maps private. These comparisons are not pure tests of sociality, common knowledge or interaction. The primary map-content comparison remains within Team.

## A5 Map definitions, display and provenance

Each cell contains `context`, `source`, `estimate`, `lower`, and `upper`. Numeric maps must include all nine cells exactly once, with finite numbers in [0,1] and lower ≤ estimate ≤ upper. Model-produced limits are requested as subjective 90% uncertainty limits. They are not treated as calibrated frequentist confidence intervals.

| Condition | Initial map at the fork | Interpretation |
|---|---|---|
| H | Coordinatewise median of three actual actor readouts after common formation | An elicited public object, not proof of negotiated agreement or common endorsement. |
| E | Same-ledger Beta posterior means and 5th/95th percentiles | A finite-sample evidence summary, not known source reliability. |
| P | Complete E-cell fields swapped between the truly best and worst sources in each selected context | Assigned distortion of estimate-and-uncertainty content; not a point-estimate-only treatment. |
| R0 | `null` | No restored external map at the fork; records and inference remain available. |
| RU | All nine cells present with unknown/null numeric fields | An explicit unknown schema, not a map of .5 estimates and not token-matched to R0. |
| R0rep | A separately executed R0 branch from the same checkpoint | A repeatability observation; the provider's random-stream independence is unknown. |

For a cell with s correct and f incorrect observations, E uses Beta(s+1,f+1). Its point estimate is (s+1)/(s+f+2), and its interval is the equal-tail 90% Bayesian credible interval. E's mathematically defined uncertainty and the models' subjective intervals have different semantics despite sharing fields.

V2 preserves full-precision source maps in research artifacts and rounds actor-visible map numbers to two decimals. Prompt serialization writes the numeric map fields with two decimal places, avoiding a difference such as `.67` versus `.666666…` between conditions. It does not round every historical forecast or ledger number. E and P share a neutral provenance description and field order; neither is described as verified truth or team endorsement. H's elicited origin is stated accurately, so H−E may retain a provenance component.

P is constructed from E₀, not from the true matrix. True rankings determine which cells are swapped; the actual values and intervals remain E-derived. A finite history can make the swap a no-op or improve map accuracy. Therefore a larger P error is an eligibility check, not a mathematical consequence of the label and not a guarantee of poorer forecasting.

## A6 Formation-only eligibility and the selected engineering history

Before model calls, the plan enumerates seeds in ascending order from 20261025, with a maximum of 100 candidates. It uses only three formation observations, computes E₀, swaps full best/worst cells within X, Y and Z, and checks the displayed version. Eligibility requires a nonzero displayed change and strictly higher nine-cell point-estimate mean squared error relative to the true matrix. Exact rational arithmetic prevents a numerical tie from becoming a small false positive. The selection log preserves every examined candidate.

| Candidate seed | Displayed E error | Displayed P error | Increase | Decision |
|---|---:|---:|---:|---|
| 20261025 | .0696777778 | .0696777778 | 0 | Reject: error did not increase. |
| 20261026 | .0583444444 | .0847888889 | .0264444444 = 119/4500 | First eligible history; selected. |

For the selected history, displayed values change in Y:A and Y:B; swapping other tied cells produces no displayed difference. The sole future event has context X. Thus this run can check the delivery of different P/E objects, split readouts and an actual continuation, but it does not directly challenge the changed context in a forecast. It is not a behavioral-sensitivity positive control. This is a selected diagnostic case, not an estimate of the natural frequency of misleading histories. H readouts, future-tape scores and model responses are excluded from selection. The selection file is `docs/bounded_v2_selection.json`; the task itself never exposes that file or its metrics to actors.

## A7 Measurement and map lifecycle

V2 limits the nine-cell-report instruction to map generation and audit stages. Initial forecasts, messages, private memos and final forecasts no longer receive the old generic map-report requirement. Natural reconstruction is not prohibited: an actor may infer source reliability from the ledger. The design records this possibility rather than interpreting all map-like text as noncompliance.

The split audit first measures displayed-map recall on disposable copies, then obtains own reliability estimates from separate copies of the original live state. Recall outputs are never inserted into own-estimate prompts or the continuation. For absent or wholly unknown maps, numerical recall is marked not applicable without a model call. Own estimates remain applicable because records exist. Individual responses and any median summaries are retained. These reports do not directly reveal latent beliefs.

In the selected run, fork audits cover Team, Solo and no-message. Nominal audits are omitted to respect the call cap, so live measurement coverage is not equal across architectures. Solo audits use three repeated readouts of the same actor state. Team/no-message audits use one readout per actor. State hashes before and after the audit check no writeback; they do not establish provider-level statistical independence.

In `initialized_update`, the inherited object is supplied until the scheduled update; it is not shown only once. After feedback, any scheduled read-only measurements occur before map update. Team/no-message updates combine one readout from each actor by coordinatewise median. Solo combines three repeated readouts of its own state. Each nominal actor separately combines three own-state readouts, without cross-actor merging; nominal therefore uses nine update calls for three map objects. Equalizing readouts per map object does not equalize actor count or total computation. After updating, R0/RU can contain numeric maps and E/P can be replaced by elicited maps.

The selected engineering schedule uses U=1 and one future round. Its update is terminal: no prediction follows it. Fork audit interval is three, so there is no additional audit after the one future round. Live shadow probes are disabled. Existing batch-probe and single-profile code paths are distinct measurement procedures; offline tests or the historical X-context batch probes do not establish new live validation of a full three-context probe battery.

`standing` instead preserves the assigned object throughout. It is useful for fixed-exposure diagnostics but cannot demonstrate failure to correct after an allowed update. A later mutable study is planned around 24 formation and 84 future rounds with U=12, not asserted to be power-validated or executed.

## A8 Planned and observed counts, attempts and execution schedule

The shared formation consists of 3 × 9 = 27 forecast/message/revision responses plus three formation map readouts, totaling 30 successful-path calls. Twelve continuations then contribute 189, for 219 planned successful responses. The completed run matched every count below with 219 physical attempts, zero errors, zero retries and zero replayed responses. These are response counts, not independent sample size, tokens, or a monetary estimate.

| Branch | Round | Own-estimate audit | Recall audit | Update | Planned total |
|---|---:|---:|---:|---:|---:|
| Team P | 9 | 3 | 3 | 3 | 18 |
| Team E | 9 | 3 | 3 | 3 | 18 |
| Team H | 9 | 3 | 3 | 3 | 18 |
| Team R0 | 9 | 3 | 0 | 3 | 15 |
| Team RU | 9 | 3 | 0 | 3 | 15 |
| Team R0rep | 9 | 3 | 0 | 3 | 15 |
| Solo H | 3 | 3 | 3 | 3 | 12 |
| Solo R0 | 3 | 3 | 0 | 3 | 9 |
| No-message H | 9 | 3 | 3 | 3 | 18 |
| No-message R0 | 9 | 3 | 0 | 3 | 15 |
| Nominal H | 9 | 0 | 0 | 9 | 18 |
| Nominal R0 | 9 | 0 | 0 | 9 | 18 |
| Continuation subtotal | 96 | 30 | 15 | 48 | 189 |
| Shared formation | 27 | 0 | 0 | 3 formation readouts | 30 |
| Entire successful path |  |  |  |  | 219 |

The hard cap is 20 attempts per continuation branch, 32 for shared formation, and 272 for the entire run (12 × 20 + 32). Failed physical dispatches consume budget. The successful plan never exceeds 18 calls within a continuation branch; spare attempts are not a requirement to spend the cap. No automatic model retry is configured. Errors stop the current execution.

Scheduling uses seed 20261025 in a separate scheduling stream. All forks are created before any continuation. Fork audits occur in a shuffled branch order; future rounds are interleaved across branches in a separately shuffled order for each round. This is round-level interleaving, not simultaneous requests, stage-level alternation, or control of provider randomness. With one future round it supplies only one realized round order and cannot diagnose long-run drift. Source/message order is also recorded; not every JSON field position is counterbalanced.

## A9 Transport, model identity and source provenance

The live adapter requests `gpt-5.6-luna` through a ChatGPT-authenticated Codex CLI at low reasoning effort. It refuses an API-key login and removes inherited `OPENAI_API_KEY` and `CODEX_API_KEY` values from the child environment. It does not implement a public API-key route, use a fallback model, or establish that another account can access the same alias. These are implementation statements, not claims about private account entitlements.

Each response uses a temporary working directory and an ephemeral invocation. The adapter requests ignored user configuration/rules, read-only operation, zero project-document bytes, disabled web/tools/apps/skills discovery and no persistent session. It archives the explicit system template, serialized user prompt, response schema hash, available usage, elapsed time, CLI version, selected effective settings and task-relevant CLI events. Unexpected action events stop the run. Host/server-added context remains unobservable, so the supplied instructions do not prove complete absence of outside influence.

Returned identity is read only from explicit CLI response/session metadata. Missing identity is preserved as null with `not_exposed_by_cli`; a request alias is not copied into the served-model field. Conflicting returned identifiers or a returned model family outside the requested one stop the run. Even a returned model string is metadata, not an attestation of immutable weights. A hash of raw CLI events is saved, while the full raw event stream is filtered rather than published; the hash alone does not make omitted contents inspectable. Timeouts preserve their failure note and elapsed time but not partial CLI output.

The run-start package hash, configuration hash, tape hashes and source snapshot distinguish inputs from subsequent repairs. They do not fingerprint dependencies or provider weights. The documented Python package requires Python ≥3.11, SciPy 1.15.3 and jsonschema 4.25.1; the current run manifest records Python 3.12.4. Environment-lock and CLI-version information must accompany the final artifact. No API fallback has been validated in this run.

## A10 Logical replay and explicit recovery

Exact replay matches every request kind, payload and schema before returning its archived response. It reruns deterministic state transitions and scoring without calling a model. Successful replay establishes that recorded inputs and outputs regenerate the checked artifacts; it does not imply that new live responses will match.

V2 additionally implements explicit prefix recovery for interrupted transport runs. The original directory remains immutable. A new execution reuses only the exact successful prefix and then makes new calls for the unfinished suffix. It requires the same configuration and requested model, rejects a completed run, rejects schema-invalid recorded answers and recorded validation failures, and refuses gaps in the successful prefix. In particular, recorded `ValidationError` and `ValueError` errors are rejected; other error classes are not categorically refused by that test. A mismatch in reconstructed request content stops recovery rather than approximating the old state.

Historical failed dispatches remain in cumulative physical-attempt counts. A durable sidecar reserves each additional physical attempt before dispatch and carries inherited counts across interrupted recoveries; absent required accounting causes refusal. This is conservative accounting and can count a reservation even if interruption occurred before the network request reached the provider. Logical calls, replayed calls, new dispatches and cumulative physical attempts are separate quantities. A completed recovered trace never turns an earlier unsuccessful attempt into a successful one.

Automatic model retries remain disabled. The separately documented atomic-file-replacement retries address a Windows file I/O error and do not regenerate model responses. Their existence must not be described as a model retry policy. The completed bounded live run required no recovery; its success does not validate unexercised recovery paths.

## A11 Scores and the analysis unit

For truth y and final aggregate probability p, realized Brier loss is (p−y)². Let r_s be the true reliability of source s in the current context and x_s its signal. The researcher computes:

```text
L1 = 0.5 × product_s [r_s if x_s = 1, otherwise 1 − r_s]
L0 = 0.5 × product_s [1 − r_s if x_s = 1, otherwise r_s]
q  = L1 / (L1 + L0)
cBR = (p − q)^2
```

Here cBR equals the conditional expected excess Brier loss relative to the true-DGP posterior. It is not the realized difference between two Brier scores for one outcome. The oracle is not actor input. Final team/no-message/nominal p is the equal mean of revised actor forecasts; solo p is its single revision. This scoring holds the factual information set fixed at all three current signals.

Within each history, descriptive contrasts include Team P−E, H−E, H−R0, RU−R0 and R0rep−R0. In the one-future-round engineering configuration, whole-trajectory and before-first-update windows are the same observation; there is no after-first-update window. Reporting both labels does not create independent evidence. A single R0 repeat gives one signed and absolute discrepancy, not a stable noise floor, equivalence test or distribution.

History diagnostics are calculated from the ledger, not from H. For each of nine context-specific source pairs (three pairs within each of three contexts), π is the Beta posterior probability that the truly better channel is better. M averages 1−2π; positive M indicates net misleadingness. Strict reversals count π<.5, with exact ties excluded. Exact rational calculations prevent equal counts from becoming spurious reversals. Actual H error, between-readout disagreement and future judgment remain separate measures. No current result fits or validates latent map weight w, ledger-reading parameter λ, mediation, correction half-life or a confirmatory population effect.

The later analysis unit is the formation history/fork family. Rounds, actors, cells and probes are nested observations; response repeats are nested within a history. A later study must define an eligible or natural-history population, justify sample size from relevant variability and a meaningful precision target, and prespecify pre-update, post-update and full-horizon comparisons. These future inference commitments are not executed merely because the code can produce windowed summaries.

## A12 Verification and known limits of the checker

V2 verifies configuration hashes, ordered event and call records, per-recording logical call budgets, stage-specific instructions, visible ledger prefixes, response schemas and absence of specified researcher-only fields. Runtime recovery enforces cumulative physical-attempt caps, but the standalone verifier does not independently certify that cumulative ledger. It reconstructs the exact live prompt from the recorded payload/schema and compares the stored transport trace. It independently recalculates Bayesian joint masses, aggregate probabilities, Brier loss and cBR rather than calling the engine's scoring function.

For a completed recording, it also reconstructs the execution from configuration and archived responses. Every regenerated request must match; final checkpoints, tapes and seed-level results must agree and every response must be consumed. Mutation tests should include map deletion and substitution with visible hashes recomputed, demonstrating that simple self-consistency does not suffice.

The historical standalone checker had accepted a semantically altered recording after its visible hashes were recalculated. That was a checker limitation, not evidence that the original research data were altered. The revised reconstruction addresses tested classes of semantic mismatch. Its reconstruction shares engine code and therefore is not a wholly independent implementation of the state machine. Independent scoring checks cover a narrower separate component. Consistent mutations of source, config, tape and logs are a different threat; source fingerprints and external preservation help, but the verifier is not a cryptographic attestation of the provider or proof of construct validity.

Verification status must be read from the report for the exact final directory. A running or incomplete recording is not a verified completed study. Passing offline fixtures, strict replay of the old release and live-response completion are separate achievements.

## A13 Artifact inventory and reproduction

| Artifact | Role |
|---|---|
| `manifest.json` | Config, hashes, source files, provider/requested model, start/end status, planned counts and final attempt accounting. |
| `tapes.json` | Researcher-side formation/future events; not an actor input file. |
| `events.jsonl` | Calls, rounds, forks, readouts, map updates, schedules and errors in event order. |
| `calls.jsonl` | Request/response/error subset, with explicit prompt and available transport evidence. |
| `checkpoint.json` | Formation state, original forks, latest branch states, H₀/E₀/P₀, history diagnostics and schedule. |
| `summary.json` | Terminal status, completed branches, descriptive scores, windows and logical/physical/replayed counts. |
| `physical_attempts.json` | Durable cumulative accounting when explicit prefix recovery is used. |
| Selection and validation records | Candidate histories, deterministic eligibility, test output, mutation checks and exact replay result. |

The engine requires a new or empty output directory. Canonical JSON hashes use sorted keys, compact separators and UTF-8 SHA256. Hashes of raw files separately bind the exported bytes. An anonymous or otherwise redacted export requires its own manifest and transformation record; it cannot truthfully retain a claim that its bytes match an unmodified original hash.

Offline review can install the declared dependencies, run tests, inspect the call plan, and replay a supplied completed recording. None of these requires model login. The code's default example may still be the historical v1 smoke, so the reviewer must specify the v2 config rather than infer version from the package version string. The executable commands should be tied to the final artifact paths; illustrative offline commands are:

```text
python -m pip install -r requirements-lock.txt
python -m unittest discover -s tests -v
python -m rem_harness plan --config configs/bounded_v2_smoke.json
python -m rem_harness replay --config configs/bounded_v2_smoke.json --recording <completed-v2-recording>/calls.jsonl --output <new-empty-directory>
python tools/verify_recording.py <completed-v2-recording>
```

Fresh live execution is a separate action requiring the specified transport, authorization and available account capacity. It is not needed to inspect archived responses. The concrete prospective alternative is the OpenAI Responses API requesting `gpt-5.6-luna`, subject to independent checks of current model/version availability, account access, pricing and funding. That adapter is not configured or tested here; ChatGPT-authenticated access does not establish API entitlement or API funding. It would need its own validation, metadata and study stratum. There is no automatic switch or authorization to invoke that route, and the identifier is not an immutable weight attestation.

## A14 Evidence status and later development

The v2 directory `runs/luna-v2-bounded-20261025` is completed: 219 successful responses, 219 physical attempts, zero errors, zero retries, zero reused responses, and twelve completed continuations. Shared formation used 30 calls; each continuation used 9–18, below its cap of 20. The requested model remained `gpt-5.6-luna`, with low reasoning effort, but returned served-model identity was not exposed. The historical 342-response run is a separate completed execution, not additional histories of this revised design.

`verification.json` reports `verified_complete`, 2,232 checks and zero failures. `replay_comparison.json` records exact checkpoint, tape and seed-result agreement after 219 replayed responses and zero new model calls. The whole live and replay summaries appropriately differ in transport accounting; they are not described as byte-identical. These checks support the stated recording properties, not population inference or complete provider isolation.

The observed continuation forecasts are reported below for transparency. Each row is one aggregate forecast in context X, with signals A=1, B=0, C=1 and realized truth 0. The true-DGP posterior is .753164557. Rounds, actors and rows are not independent histories; the P/E display changes lie in Y, so these numbers do not certify sensitivity to the manipulated context.

| Branch | Successful calls after formation | Aggregate forecast | cBR |
|---|---:|---:|---:|
| Team P | 18 | .596667 | .024492 |
| Team E | 18 | .570000 | .033549 |
| Team H | 18 | .390000 | .131888 |
| Team R0 | 15 | .593333 | .025546 |
| Team RU | 15 | .546667 | .042641 |
| Team R0rep | 15 | .623333 | .016856 |
| Solo H | 12 | .420000 | .110999 |
| Solo R0 | 9 | .520000 | .054366 |
| No-message H | 18 | .273333 | .230238 |
| No-message R0 | 15 | .616667 | .018632 |
| Nominal H | 18 | .290000 | .214521 |
| Nominal R0 | 18 | .473333 | .078306 |

All 15 applicable recall readouts exactly reproduced the 27 displayed numeric fields (nine estimates and eighteen interval limits) in their respective maps. This demonstrates transcription under the requested recall task, not endorsement. The three formation map readouts disagreed: two matched each other, while the third differed by .05 in eight cell estimates and .10 in one. Their median H₀ used .35 for the four observed-failure cells and .65 for the five observed-success cells. H₀ point-estimate MSE against the true matrix was .054166667. These are descriptive properties of one elicited object, not a demonstrated population mechanism or a natural prevalence estimate.

The single R0 repeat changed the aggregate forecast by .03 and cBR by −.008689873. This pair supplies neither a variance estimate nor evidence of independent backend random streams. Own-estimate readouts and cellwise deviations are preserved in `diagnostics.json`; they remain distinct from recall and behavior. Every map update was terminal, with zero subsequent forecasts. No post-update correction or latent weighting parameter was measured.

Already implemented operations include P construction, fixed displayed precision, stage-specific map instructions, split audits, scoped measurement coverage, repeated readouts for solo/nominal map objects, deterministic round scheduling, source hashing, bounded attempt accounting and explicit prefix recovery. The particular run can demonstrate only the code paths it actually reaches. Failure-path tests and unused feature support are not live execution evidence.

The later scientific work is to characterize response variability across histories, establish the link from historical evidence to actual H, measure forecast sensitivity on controlled profiles, observe decisions after allowed updates, and compare content effects across carefully aligned architectures. Formal sample size, real-response parameter recovery, field generalization and a verified alternative-provider route remain future work. The value of the current artifact is that these boundaries and its failures can be inspected and tested.

## A15 Ethics, disclosure and release scope

The experimental inputs are synthetic and the actors artificial; the baseline does not identify recruited human participants. Institutional ethics applicability is an author-level determination, not an approval number inferred by the software. AI use in the experiment and in code, analysis and manuscript preparation is disclosed separately in the submission materials.

The reviewer-facing artifact should include shareable original code, tests, configs and synthetic research traces, with private correspondence, recordings, third-party manuscripts, credentials and unrelated material excluded. `LICENSE` and `NOTICE.md` apply MIT to original software, tests, configurations, schemas and original software documentation under a collective REM contributors notice. They do not grant rights over model weights, third-party services, copied articles or all raw model output; the collective notice does not attest institutional or individual ownership. The manuscript's publishing agreement and the related SIGDSA work require their own accurate disclosure. This appendix is a technical review draft, not a signed compliance declaration or proof that an anonymous link has been uploaded and tested.

The detailed organizational literature and adaptations are in `docs/scenario_and_identification.md`; the Stage-1 proposal supplies the research argument and references. The relevant official call is [AI-Enabled Frontiers in Organizational Science](https://pubsonline.informs.org/pb-assets/filesorsc/CFP_AI-Enabled%20Frontiers%20in%20Organizational%20Science-1785685920943.pdf), with separate [submission](https://pubsonline.informs.org/page/orsc/submission-guidelines) and [transparency](https://pubsonline.informs.org/page/orsc/data-and-methods-transparency) policies. The anonymous package should preserve relative paths to included scientific files and clearly label unavailable external dependencies.
