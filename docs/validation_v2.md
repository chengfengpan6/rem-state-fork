# V2 execution and verification, 25 October 2026

## Actual model use

The bounded configuration completed 219 logical requests and 219 successful
responses, with 219 new physical dispatches, zero recorded failures, zero
automatic retries and zero prefix-reused responses. Twelve branches completed.
Shared formation used 30 calls; branches used 9–18 each under a hard cap of 20.
The overall configured cap was 272. These counts include map and audit responses.

All requests used `gpt-5.6-luna`, Codex CLI `0.162.0-alpha.17.2`, low reasoning,
and a ChatGPT login. Returned served-model identity was not exposed. There was
no API route or automatic model substitution, and no extra setup model call in
this revision. Matching the requested alias is not a guarantee of identical
model weights across dates.

## Recording checks and replay

- The saved v2 record passed **2,232 checks, zero failures**. See
  [verification.json](../evidence/luna-v2-bounded/verification.json).
- Checks bind recorded payloads to actual serialized prompts, require live
  trace fields, validate schemas, reconstruct expected actor views, compare
  checkpoints and tape, and independently recompute scores from joint masses.
- Strict offline replay consumed all 219 responses, dispatched zero models,
  and reproduced checkpoints, tapes and seed results exactly. Whole summaries
  correctly differ in live/replay accounting. See
  [replay comparison](../evidence/luna-v2-bounded/replay_comparison.json).
- The archived v1 run was also replayed: its summary, checkpoint and tape were
  exactly equal, with 342 replayed responses and no new model calls. Its original
  saved records remain unchanged; its legacy verifier passed 5,018 checks.
- Fault-injection tests reject a wrong map or another actor's personal record
  after corresponding visible hashes have been recomputed. Missing actual
  transport prompts and reintroduced non-map instructions are also tested.

Reconstruction uses the engine and is not an independent proof of every state
transition. Independent score arithmetic and targeted semantic mutation tests
provide additional checks. None verifies hidden provider context, constructs,
causal mechanisms or fresh model-response reproducibility.

The verifier checks logical budgets within the supplied recording. Cumulative
physical attempt reservations across interrupted runs are enforced by the
runtime and its durable recovery ledger, with offline interruption tests. The
present live run did not exercise a failed-call recovery path.

## Descriptive diagnostics and limits

[diagnostics.json](../evidence/luna-v2-bounded/diagnostics.json) is produced by a
separate reader that does not invoke Engine or a provider. It independently
computes source/posterior differences, recall and own-estimate deviations,
forecast grids, scores and update-window availability. It fits no w or lambda
and reports no p-value, formal power or population effect.

The selection rule examined seeds 20261025 and 20261026 using formation data
only. The first failed the strict displayed-MSE-increase condition; the second
was retained. Displayed P/E differences are only in context Y. The single
future context is X, so this is **not a within-context behavioral positive-control
validation**. Complete tables were visible, making cross-context influences
possible. No replacement history was selected after observing responses.

All 15 applicable recall responses transcribed their 27 displayed numeric
fields exactly. Own estimates were elicited on separate clones. The one R0
repeat is a descriptive difference, not a noise distribution. All updates were
terminal; no forecast used an updated map. Nine manually inspected R0/RU/R0rep
messages contained no complete numerical nine-cell map, but all discussed source
history or reliability. This is not a randomized old-versus-new-prompt test.

## Clean-copy check

A fresh local Git clone (`--no-local`) at commit `20b75be` and a newly created
Python environment installed `requirements-lock.txt`. **All 76 tests passed**.
The archived live record again passed 2,232 checks; offline replay consumed all
219 responses with zero new model calls and exactly reproduced the checkpoint,
tape and seed results. All seven executed-package snapshot hashes matched.
No working-tree or untracked files were copied into that checkout. This was a
new checkout/environment on the same Windows machine, not a second-machine or
fresh-provider replication. See [the clean-copy record](clean_validation.json).

The dependency lock specifies the packages; the run-source snapshot preserves
package bytes separately from Git checkout line endings. The documented replay
path requires no account, key, live model or private file. Subsequent release
edits are documentation and packaging only, without changes to validated code.

## Artifact provenance

Operational code was frozen at `0af0368` before live dispatch. Core package files
were not edited during the run. The final repository adds analysis tools,
documentation and evidence without rewriting original responses. The saved
[provenance](../evidence/luna-v2-bounded/provenance.json) binds raw records to the
configuration and executed package snapshot. Software rights are explained in
[NOTICE.md](../NOTICE.md); a public development repository is distinct from a
separately prepared anonymous review export.
