> Historical v1 document. For the current OS revision, read [the v2 appendix](technical_appendix_v2.md), [scientific design](scenario_and_identification.md), and [actual validation](validation_v2.md). Earlier primary contrasts and budgets are not current-run instructions.

# Technical appendix: executable REM state-fork prototype

This appendix describes the implementation, not a completed confirmatory study. The authoritative specification for a particular run is its saved configuration and manifest. Small smoke runs test transport, state handling and traceability; they do not estimate population effects or establish a theory of team memory. See [protocol.md](protocol.md) for the scientific rationale and [readiness.md](readiness.md) for submission and evidence boundaries.

## 1. Task and data-generating process

Each round has a context X, Y or Z, a binary truth, and three labeled binary signals A, B and C. Contexts occur once each within shuffled blocks of three. Truth is independently Bernoulli(0.5) each round. Conditional on truth and context, signal errors are independent. The researcher-side reliability matrix is:

| Context | A | B | C |
|---|---:|---:|---:|
| X | 0.85 | 0.65 | 0.50 |
| Y | 0.50 | 0.85 | 0.65 |
| Z | 0.65 | 0.50 | 0.85 |

Respondents are told that reliability is unknown and stationary; the numerical matrix is not included in their task payloads. The deterministic generator uses a local pseudorandom stream seeded by the configuration. All branches of a seed receive the same future event tape. The full tape is a researcher artifact, not respondent input.

**This implementation uses independent truths, not exact within-block truth quotas.** It therefore must not inherit numerical results or oracle claims from another truth-balancing design. The known 0.5 prior remains appropriate conditional on past outcomes under this implemented generator.

## 2. State and information boundaries

The engine stores four slots and constructs an actor-specific view before each call:

| Slot | Meaning | Visibility |
|---|---|---|
| `LE` | Observed contexts, disclosed signals and realized truths | Completed rounds only; shared evidence |
| `LB` | Recorded final forecasts and scores | Shared team history; nominal respondents receive only their own post-fork behavioral records |
| `Pi` | Provenance-labeled personal/founder records | Actor-specific view; no other actor's current private record |
| `H` | Nine-cell source-reliability representation | The actor's current map; may be absent or contain unknown cells |

The map records an estimate and lower/upper subjective 90% uncertainty limits for each context/source cell. It contains no requested rankings or action recommendations. Valid map outputs must include every cell exactly once, with finite values in [0,1] and lower ≤ estimate ≤ upper.

All branches are deep-copied before any branch continuation executes. The engine constructs payloads from an explicit allowlist rather than serializing the whole run manifest. Branch labels, future outcomes, the true reliability matrix, history moderator M and oracle predictions are researcher-side objects. Hashes and saved checkpoints make the resulting states inspectable; their existence is not a substitute for an independent isolation check.

Solo and nominal respondents receive the common founders' pre-fork records as an explicitly labeled archive. Those records are not represented as the new respondent's own previous actions. Nominal respondents do not see one another's post-fork forecasts, private memos or evolving maps. Current messages are supplied only where the protocol allows them and are not appended to persistent conversation history.

## 3. A round and the architecture comparisons

Every round uses synchronous stages: all initial forecasts are collected, then all messages or private memos, then all final forecasts. Outputs from the same stage are not provided to later respondents in that stage. Truth is added to the observed ledger only after all final forecasts have been collected.

| Architecture | Initial information | Intermediate step | Final output | Calls per round |
|---|---|---|---|---:|
| `team` | Own labeled signal | All signals disclosed; each actor sends a peer message | Three revised forecasts, equal mean | 9 |
| `nomessage` | Own labeled signal | All signals disclosed; each actor writes a private memo | Three revised forecasts, equal mean | 9 |
| `solo` | All three signals | One private memo | One revised forecast | 3 |
| `nominal` | All three signals for each independent respondent | Three separate private memos | Three separate revised forecasts, equal mean | 9 |

`nomessage` removes peer-message exchange within the round. It still retains shared evidence and, in mutable mode, shared median map updates; it is not a removal of every coordination mechanism. Equal stage counts do not guarantee equal token use or computation. Solo versus nominal additionally changes the number of forecasts averaged. None of these contrasts alone identifies common knowledge or a uniquely social mechanism.

Source-list, message and execution orders are recorded. A seed selects one of the six A/B/C order permutations. This does not establish that every label position throughout every serialized map and prompt is counterbalanced.

## 4. Formation, fork conditions and map lifecycle

A common team generates the formation history. Three independent map elicitations then produce the initial map `H0` through coordinatewise medians of estimates and interval endpoints. This aggregation is an explicit prototype choice, not a validated psychological model of consensus.

The implemented fork conditions are:

- `H`: initialize with the respondents' aggregated `H0`.
- `R0`: initialize with an absent map, encoded as `null`.
- `E`: initialize with a map computed from exactly the observed ledger, using a Beta(1,1) prior separately for each cell. Its estimate is the posterior mean; its interval is the equal-tail 90% credible interval.
- `RU`: initialize with the nine-cell structure but unknown, null-valued entries.

`E` is an evidence-only finite-sample estimate, not the true reliability matrix. Its mathematical credible intervals and the models' subjective intervals share a schema but are not asserted to have equivalent semantics. `R0` and `RU` differ in content and structure; neither contrast is claimed to match token counts or formatting perfectly.

Two lifecycle options are implemented. In `standing` mode the fork map remains unchanged. In `initialized_update` mode it persists until the configured update checkpoint, after which fresh respondent map elicitations replace it. The team and no-message architectures aggregate those maps by coordinatewise median; a solo uses its own readout; nominal respondents update independently. Thus condition labels describe initialization, not a promise that the `R0` map stays absent indefinitely. Measurements occur after outcome feedback but before that checkpoint's map update.

The shipped short configuration uses three formation and three continuation rounds with a map update interval of three. Its terminal update is recorded, but no later forecast demonstrates the effect of that update. A longer design is needed to study repeated adaptation after updates. Other numerical settings must be read from the selected configuration, not inferred from this example.

## 5. Read-only measurement and scores

Map audits and hypothetical signal probes operate on disposable state copies. Their results are logged and are not written back into the running state. Before/after hashes check that the live state is unchanged. This is an engineering isolation property; it does not establish that the measurement perfectly captures the model's latent beliefs.

Batch probes present multiple signal profiles in a single call. They are diagnostics, not independent interventions on each profile. The short configuration probes the eight X-context binary profiles at its final checkpoint. A single-profile mode exists for offline exploration and is not enabled for live use in this prototype. No outcome feedback is provided for probes.

For forecast p and truth y, Brier loss is `(p - y)^2`. The researcher computes the exact conditional probability q from the known reliability matrix and the current signals. Conditional expected Brier regret is `(p - q)^2`; it is not the same as the realized difference between two Brier losses on one outcome. Recorded paired summaries are descriptive differences in mean regret within the same seed.

History metrics include M, strict reversal count and the worst pair concordance. Pairwise Beta ordering probabilities are computed as exact rational quantities for equal observation counts, so ties remain exactly one-half. M describes the sampled history; it does not measure the model's actual map error. This release does not fit w or lambda, perform causal mediation analysis, or produce confirmatory significance tests.

## 6. Model transport and replay

The live adapter requests `gpt-5.6-luna` through a ChatGPT-authenticated Codex CLI. It does not implement a public API-key transport. It checks subscription login and removes inherited OpenAI/Codex API-key environment variables from the child process. Availability, account limits and permitted access remain properties of that installed interface; the requested model name must not be presented as an independently verified server model fingerprint.

Each response uses a new ephemeral invocation in a temporary directory with task instructions and a JSON response schema. The adapter requests read-only execution, disables tools and host discovery features, and treats unexpected action events as failure. These measures reduce unintended local context and persistence. Host/server-added context is not fully observable, and subprocess isolation does not prove access to model internals or absence of provider-side state. The engine itself has no network or model SDK dependency.

The provider interface is `complete(kind, payload, schema) -> response`, with a trace exposed separately. Responses undergo strict validation. The harness does not clip probabilities, coerce values, repair malformed outputs or retry failed calls. A global cap counts dispatch attempts, including failed attempts. Cancellation prevents further dispatch; an already running provider invocation remains subject to its transport timeout.

Recorded replay feeds archived responses back to the engine and requires exact request-kind, payload and schema agreement. A successful replay establishes consistency of the saved inputs, responses and engine execution. It is not a fresh model run, and it does not establish that another account can access the same model or reproduce identical stochastic responses. Release verification should check request–response pairing, full consumption of the intended trace and equality of substantive outputs. Do not label replay as verified until that check actually succeeds.

## 7. Research artifacts and failure handling

| Artifact | Contents and role |
|---|---|
| `manifest.json` | Configuration, version, requested provider/model, timestamps, call cap, execution status and deviations |
| `tapes.json` | Researcher-side generated events for common-history and future-tape verification |
| `events.jsonl` | Ordered call, round, fork, measurement and update events |
| `calls.jsonl` | Model-request/response/error events selected from the event stream |
| `checkpoint.json` | Formation, initial forks and latest completed branch states |
| `summary.json` | Completion status, calls attempted, descriptive outcomes and any stopping error |

JSON hashes use sorted keys, compact separators and UTF-8 SHA256. Output directories must be new or empty; completed artifacts are not silently overwritten. Checkpoints are inspection artifacts, not a claim of resumable execution after interruption. An unsuccessful run must remain unsuccessful in the manifest even if some calls returned valid outputs.

The expected successful-path call count is computed from the selected horizon, architectures, measurements and updates. The provided ten-branch short configuration initially totals 342 responses, below its 500-attempt cap; `expected_calls(config)` and the saved manifest are authoritative if configuration changes. Counts are not monetary cost estimates or a power calculation. Public release should retain only synthetic-task research content and the metadata needed to audit it, excluding credentials, unrelated local context and private correspondence.

## 8. Post-smoke file-I/O correction

The 342-response live run completed before a Windows checkpoint-replacement
issue appeared during fast offline replay. That first replay stopped after
consuming 252 archived responses; it made no model calls. Its failure is retained
in `evidence/verification_attempts/local_replay_01_failure.json`.

The release adds at most five atomic-file replacement attempts when that specific
operation raises `PermissionError`, separated by 0.05, 0.10, 0.15 and 0.20 seconds.
Serialization, other exception types and model calls are not retried. Exhausted
checkpoint recovery stops further dispatch and preserves the original error when
failure reporting can still be written. The CLI reports the primary run error
instead of masking it with an unused-replay-response check.

This is an engineering correction after data collection. It changes file-failure
handling, not prompts, state transitions, outcomes or the experiment's scoring.
The provenance file distinguishes the actual live-run code commit from the
subsequent replay/release commit. Archived evidence bytes are exempt from Git line
ending conversion, so their saved SHA256 values remain portable.
