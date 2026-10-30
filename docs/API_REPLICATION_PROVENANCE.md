# API replication evidence and offline reproduction

This delivery preserves the supplied Claude and Gemini recordings and makes
their arithmetic independently reproducible. It does not amend historical
records, conceal failures, add model responses, or establish a new live API
execution route. The earlier GPT experiment remains a separate recording.

## Archives and exact source bindings

| Archive | Supplied files copied | Final accepted logical responses | All stored response rows |
|---|---:|---:|---:|
| `evidence/claude-opus55-30histories/` | 217 | 3,600 | 3,600 |
| `evidence/gemini38flash-30histories/` | 233 | 3,600 | 3,732 |

All **450 files, 163,420,292 bytes** from the supplied recording directory
were copied exactly. Each `SOURCE_MANIFEST.json` gives the original logical
path, current relative path, byte count and SHA-256. Root analysis,
verification and log files were renamed to `analysis.json`,
`verification_supplied.json` and `execution.log`; their bytes, internal run
names and historical metadata were not changed. Historical adapter source
and its separate manifest are under `replication_adapters/historical_2026_10_29/`.
Private correspondence and internal review documents are not part of these
archives.

The API recordings reuse the same 30 external formation ledgers, fixed
profiles, E/P maps, role order, history-level schedule, and harness schema as
the GPT recording. The system template and stage-instruction prefix agree.
The complete downstream prompts differ because each provider generated its
own behavioral records, elicited H and messages. "Same prompts byte for byte"
is therefore not an accurate description of the whole execution.

The ten harness source hashes recorded by the original runs agree. The
historical adapter files, SDK versions and actual request configurations were
not all bound into those original runtime hash inventories. Supplying the
adapter source now improves inspectability without retroactively establishing
its exact execution version. This is cross-provider repetition of the same
implemented design, not independent design or independent implementation
replication.

## Recompute from response rows without an API account

Create an environment using `requirements-lock.txt`. The independent tool
imports only standard-library code, NumPy, SciPy and jsonschema. It imports
neither the harness nor historical provider code and makes no network calls.

```sh
python -m pip install -r requirements-lock.txt
python tools/recompute_replications.py --output runs/replication-arithmetic.json
```

The output must be new and outside `evidence/`. `--repo-root <directory>`
allows checking a relocated source/evidence copy. Errors produce a nonzero
exit; the original records are never overwritten. The resulting receipt
includes the tool hash, reference-analysis hashes, archive hash-check counts,
all 30 history differences, accepted-response schema checks, resumed-prefix
comparisons, model metadata counts and numerical differences.

For each provider, the tool reconstructs 900 final individual probabilities
from `call_response`, matches them to `call_request`, averages three actors
within each condition/profile, derives the scoring oracle from the known
matrix, and calculates history-level differences. It recomputes the sole
P−E test, the two H contrasts with their Holm family, the fixed 10,000-resample
history bootstrap, repeat discrepancy and other declared descriptive values.
The two profiles receive equal weight within a history. There are 30 history
units per provider, not 3,600 independent observations. Reusing the same
histories across providers does not create 90 unrelated exogenous histories.

The numerical comparison allows an explicitly reported absolute error of
at most `1e-12`; raw responses, actor identity and recovered-prefix payloads
are compared exactly. This tolerance is for recomputed arithmetic, not altered
experimental inputs. The separate semantic verifier and its supported
comparison modes are documented in the repository's validation guidance.
This independent tool does not replace that semantic verifier.

The supported harness commands check recorded state and replay accepted
responses without contacting a model. All destinations below must be new:

```sh
python tools/run_targeted.py verify --recording evidence/luna-targeted-30histories --output runs/verify-gpt.json
python tools/run_targeted.py verify --recording evidence/claude-opus55-30histories --float-tolerance 1e-12 --output runs/verify-claude.json
python tools/run_targeted.py verify --recording evidence/gemini38flash-30histories --float-tolerance 1e-12 --output runs/verify-gemini.json
python tools/run_targeted.py replay --recording evidence/luna-targeted-30histories --output runs/replay-gpt
python tools/run_targeted.py replay --recording evidence/claude-opus55-30histories --float-tolerance 1e-12 --output runs/replay-claude
python tools/run_targeted.py replay --recording evidence/gemini38flash-30histories --float-tolerance 1e-12 --output runs/replay-gemini
```

The default comparison is strict. The explicit tolerance only permits
bounded floating-point differences in designated recomputed score fields;
it does not relax recorded probabilities, maps, signals, identities,
non-score state, schema or exposure. Original explicit prompt strings are
checked exactly against their original recorded payloads. A changed replay
state digest is accepted only when its underlying state is demonstrated to
differ solely in the allowed score fields. Review each newly emitted receipt for
the actual checks and discrepancies. Replay reuses the same implementation
with recorded outputs; it is not independent software replication or a
second live model experiment.

Expected primary results, conditional on the original selected population:

| Provider metadata | P−E mean | 95% t interval | Two-sided p | Positive histories |
|---|---:|---|---:|---:|
| GPT requested `gpt-5.6-luna` | .21002870 | [.17852399, .24153340] | 3.8328e−14 | 30/30 |
| Returned `claude-opus-5-5` | .07586630 | [.04584377, .10588884] | 1.5891e−5 | 28/30 |
| Returned `gemini-3.8-flash` | .11766906 | [.08574432, .14959381] | 2.6114e−8 | 30/30 |

These support a bounded response to the assigned content change. H−E is near
zero in the GPT recording, positive on Claude and negative on Gemini; its
direction is not universal. H−R0 improves in all three current recordings,
but its content, provenance and table-availability components are not isolated
by that contrast. Neither result establishes the original H1–H4, persistence
after updating, a uniquely social process, or human-organizational validity.

## Attempts, recovery and trace limitations

Claude has 3,600 accepted records, an aggregate report of one transport retry
and five over-length-message resamples. Gemini has one retained HTTP 400
failure, one concurrent cancellation, and two resumed histories. Its 132
duplicated prefix rows consist of 74 from seed 20261053 and 58 from seed
20261054. Eight complete histories supply another 960 earlier responses;
1,092 earlier successes plus 2,508 new successes yield 3,600 final responses.
The independent tool checks the 132 recovered payload/schema/response pairs.

The Gemini usage summary covers the resumed segment and reports two transport
retries and no length resamples. The harness ledger's 3,601 reservations do
not include every internal API retry. Claude's ledger similarly records
3,600 logical reservations, not its five discarded samples and retry.
Using the available aggregate counts gives at least 3,606 Claude and 3,603
Gemini API attempts; a complete independently reconciled provider-attempt or
billing ledger is unavailable. Rejected outputs and all failed internal
attempts cannot be reconstructed from the accepted rows.

Both historical adapters declare `is_live=False`, although they call external
APIs. The old wrapper consequently wrote `physical_dispatch=False`. Those
flags have not been retroactively corrected. Their semantics must not be used
to claim that these were scripted fixtures or that no external calls occurred.

The original successful traces retain requested/returned model names,
explicit system and user strings, parsed raw responses and token usage.
The old trace whitelist omitted the adapter's response identifier, effort,
stop reason, per-call retry/resample counts and API schema note. Low effort
is supported by the supplied runner and aggregate usage records, not by an
independently attested per-response service configuration. Returned model
identifiers improve provenance but are not immutable-weight attestations.
Explicit API prompt strings do not guarantee that all internal provider
context or transformations are observable.

Claude removed unsupported numeric/array constraints for the API grammar,
then used the full harness schema to validate accepted responses. Messages
over 600 characters were resampled, not truncated. All archived accepted
responses pass their full request schema and their parsed `raw_response`
equals `response`. This says nothing about the contents of discarded outputs.
The supplied Gemini adapter includes retry handling for HTTP 400 in addition
to other transient errors, while its fixed trace prose says only 429/5xx;
the source and actual retained 400 error take precedence over that stale prose.

## Verification claims and future execution

The supplied verification reports record 12,968 Claude and 12,967 Gemini
checks with zero failures. Their scope combines recorded-exposure/count/score
checks with shared-engine reconstruction. They are historical reports, not
separate full exact-replay receipts. A newly generated verification or replay
receipt must identify its current code and comparison mode; it must not be
presented as an original 28 October artifact or fresh-model replication.

Historical source is archival only. No new live API route is advertised here.
A future dispatcher requires truthful live flags, an explicit authorized
provider/model configuration, environment-variable credentials only, optional
SDK imports, per-physical-attempt durable reservation and tracing, retained
rejected/error payloads, strict failure exits and a stated recovery policy.
That development is separate from reproducing the recorded arithmetic.
None of these prospective improvements recovers missing historical metadata.
