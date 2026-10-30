# REM — intervening on shared reliability representations

REM studies an organizational question: when the factual record remains
available, does changing a supplied interpretation of source reliability alter
collective judgment? It separates factual, behavioral and private records from
a public reliability table, then forks a synthetic team from a common recorded
state. The contribution is an inspectable research instrument.

This 30 October review release consolidates the completed Luna diagnostic and
the supplied Claude/Gemini replications. It adds restricted score-tolerance
verification, explicit provenance, complete offline replay and an independent
response-level calculation. **It adds no experimental model observations.**

[Visual overview](docs/index.html) · [Release notes](docs/release_2026-10-30.md) ·
[API archive provenance](docs/API_REPLICATION_PROVENANCE.md) ·
[Frozen protocol](docs/targeted_protocol_2026-10-25.md) ·
[Frozen analysis plan](docs/targeted_analysis_plan_2026-10-25.md)

## What was observed

Each route used the same 30 selected exogenous three-event histories. Every
history supplied five Team conditions (P, E, H, R0, R0rep), with two isolated
conflicting-signal Y profiles and no feedback or updates. There were 3,600
accepted logical responses per route. These are 30 history units per route,
not 10,800 independent observations or 90 unrelated exogenous histories.

| Route | P−E mean cBR | 95% t interval | Two-sided p | Positive histories |
|---|---:|---|---:|---:|
| Requested gpt-5.6-luna / Codex | .210029 | [.178524, .241533] | 3.8328e−14 | 30/30 |
| Returned claude-opus-5-5 / API | .075866 | [.045844, .105889] | 1.5891e−5 | 28/30 |
| Returned gemini-3.8-flash / API | .117669 | [.085744, .149594] | 2.6114e−8 | 30/30 |

cBR is the conditional expected excess Brier loss `(p-q)^2`. P swaps the
complete Y:A/B cells of E; E summarizes the observed records. Positive P−E
means increased loss under the planted table. H−E is near zero on Luna,
positive on Claude and negative on Gemini. These bounded diagnostic results
do not establish naturally harmful memory, the original H1–H4, a Team/Solo
mechanism, correction after updates or human-organizational validity.

## Review a clean copy without model access

Use Python 3.12 and the locked dependencies; the supplied original Mac receipt
used Python 3.13. Set up and activate a fresh virtual environment using your
platform's usual commands, then run from this repository root:

```sh
python -m pip install -r requirements-lock.txt
python tools/review_all_archives.py --output runs/complete-offline-review
```

The output directory must be new. This single command runs the unit tests,
strict and bounded verification, bounded recorded-response replay, verification
of each replay, frozen analysis and separate-code arithmetic for all three
archives. It makes **zero model calls** and needs no API key or model account.
It retains strict failures if a platform needs the explicitly bounded mode,
and stops if bounded verification/replay fails. Read `review_receipt.json`
and the individual logs; completion is not inferred from merely starting it.

For a narrower arithmetic-only check:

```sh
python tools/recompute_replications.py --output runs/independent-arithmetic.json
```

The semantic CLI accepts `--float-tolerance 1e-12` for `verify` and `replay`.
The default is strict zero tolerance. Only specified recomputed LB/Pi Brier
scores and cBR summaries can differ within the limit. Predictions, signals,
maps, types, schemas and messages remain exact; changed derived state hashes
require a path-level explanation tied to those scores. A failed verification
is never labeled a successful tolerance replay. See
[current validation receipts](validation/2026-10-30/).

## Evidence and execution provenance

- [Luna archive](evidence/luna-targeted-30histories/)
- [Claude archive](evidence/claude-opus55-30histories/)
- [Gemini archive](evidence/gemini38flash-30histories/)
- [Historical API adapter sources](replication_adapters/README.md)

All 450 supplied API files and four adapter sources are preserved byte for
byte, with source manifests. Gemini recovery reuses 132 saved response rows;
the independent script checks those prefixes and does not count them as new
observations. API logical-response counts are not complete physical attempt
or billing counts. Missing rejected responses and service metadata cannot be
reconstructed. The provenance document specifies these limits.

Templates, exogenous records and scheduled cases are shared; complete
downstream prompts differ with each model's own records and responses.
Returned API model names are recorded identifiers, not immutable-weight
attestations. Luna's CLI did not expose a served-model identifier. Explicit
client text does not reveal every provider-internal input.

The original execution commit and exact source snapshot remain preserved with
the Luna archive. The current verifier is a later tool, not a replacement
claim about what code generated the historical data. Earlier 342-response and
219-response engineering executions remain separate and are not pooled.

## Scope of this release

The supported cross-provider path is offline inspection. Historical adapters
are archived for provenance and **are not a validated new live-study command**.
A future API dispatcher needs explicit authorization/configuration and durable
per-attempt budgeting, tracing and recovery. The original Luna live command
retains its prior guards; inspection must not use a live/run/resume command.

The MIT license applies within [NOTICE.md](NOTICE.md)'s scope. Provider models,
third-party dependencies and separately submitted manuscripts are not covered
by a blanket software license. Private correspondence, credentials and
unpublished proposal documents are excluded from this repository. This named
development repository is not the external anonymous-review entry point.
