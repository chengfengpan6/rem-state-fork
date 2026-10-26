> Historical bounded v2 overview, preserved before the targeted 30-history release.

# REM: shared interpretation with a common factual record

**Current OS revision: 25 October 2026.**

[Readable artifact overview](index.html) · [Scientific question and task](scenario_and_identification.md) · [V2 technical appendix](technical_appendix_v2.md) · [Validation and limits](validation_v2.md)

When factual records remain available, does an inherited shared interpretation
of which sources are reliable change subsequent evidence use and collective
judgment? This research prototype separates factual, behavioral, personal, and
map state, then branches from a shared history under matched future evidence.
Its contribution is an inspectable organizational experiment, not model-score
optimization or a completed study of human organizational memory.

## What was actually run

The new bounded diagnostic completed **219 successful responses**, all requesting
GPT-5.6 Luna: 30 in shared formation and 189 across 12 branches, each using
9–18 calls under a hard cap of 20. It includes Team P/E/H/R0/RU and a separately executed R0 replicate,
Solo H/R0, no-peer-message H/R0, and nominal H/R0. There were no failed calls
or retries. The old 342-response record remains unchanged and separate.

This is one selected history, 3 formation rounds and 1 future round. P is a
full-cell permutation of E0, matched in precision and provenance. Its displayed
change is only in Y; the actual future context is X. Thus this record verifies
delivery and execution, **not behavioral positive-control sensitivity**. Updates
are terminal; no post-update decision was observed. No p-values, power, real-agent
weight recovery or population organizational effects are claimed.

Requested model and transport are unchanged: `gpt-5.6-luna`, Codex CLI
`0.162.0-alpha.17.2`, ChatGPT login, low reasoning. The CLI did not expose a
served-model ID. Alias consistency is not immutable weight identity.

## Install and verify without any model calls

```sh
python -m venv .venv
# Activate the environment using the platform's standard command.
python -m pip install -r requirements-lock.txt
python -m unittest discover -s tests -v
python tools/verify_recording.py evidence/luna-v2-bounded --output runs/v2-verification.json
python tools/analyze_diagnostics.py evidence/luna-v2-bounded --baseline evidence/luna-smoke --output runs/v2-diagnostics.json
python -m rem_harness replay --config configs/bounded_v2_smoke.json --recording evidence/luna-v2-bounded/calls.jsonl --output runs/v2-replay
```

Create `runs` first if needed (`mkdir runs`). Output paths must be new. Replay
validates complete ordered requests and schemas before using saved responses;
the semantic verifier reconstructs state and independently checks scoring.
Fault-injection tests reject wrong-map and wrong-personal-record payloads even
after their visible hashes are recomputed. These checks establish specified
properties, not a complete causal interpretation.

## Configuration and guarded live use

```sh
python -m rem_harness plan --config configs/bounded_v2_smoke.json
```

The current configuration is a diagnostic, not a formal study. Live entry is
explicit, requires an existing authorized ChatGPT login, and is capped in both
CLI and Engine at one history, <=3 formation rounds, <=2 future rounds, <=20
attempts per branch and <=32 shared formation. The recorded config used 219
planned responses and a 272 total ceiling. No API key is used by this adapter.
Do not rerun live merely to inspect evidence. Fresh access can fail or drift.

Interrupted v2 runs can use explicit `resume --recording RUN_DIRECTORY --output
NEW_DIRECTORY`. Successful prefixes must match exactly; schema failures are
not silently repaired. Persisted cumulative attempts include earlier failed
dispatches. Completed runs and unverifiable recovery histories are refused.

## Research interpretation

P−E is the primary planned content contrast; H−E connects to naturally formed
maps. Keeping records available makes R0 removal of one external object, not
erasure of experience. Recall, own estimates, cue use and outcomes are distinct.
Architecture contrasts change several features and do not isolate a purely
social mechanism. The future study needs independent histories, relevant
post-update decisions, measurement validation and a justified sample size.

The source and adaptation matrix cites organizational learning, expertise,
knowledge integration and judgment research and states its actual reading
scope. Technical neighbors are compared separately. See the
[special-issue positioning](os_positioning_and_submission.md).

## Evidence and rights

[New raw evidence](../evidence/luna-v2-bounded/) · [New provenance](../evidence/luna-v2-bounded/provenance.json) · [Old raw evidence](../evidence/luna-smoke/) · [Historical v1 README](legacy_v1_readme.md)

The run-source snapshot preserves exact package bytes; Git checkout line-ending
normalization need not preserve those bytes. Offline replay checks semantics.
Code is licensed under MIT within [the stated scope](NOTICE.md). Third-party
materials, model weights/services and manuscript publication rights are separate.
Private correspondence, credentials, recordings and unpublished attachments are
excluded. A named development repository is not the anonymous submission link.
