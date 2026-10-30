# Historical API adapters: provenance, not a live entry point

`historical_2026_10_29/` preserves the four supplied adapter/comparison scripts
without edits. `SOURCE_MANIFEST.json` records their original logical paths,
sizes and SHA-256 hashes. They document how the supplied Claude and Gemini
records were generated; their presence does not establish that these exact
adapter bytes were hash-bound to each historical API attempt.

**Do not use the historical runner as a validated future live-study command.**
The historical adapters declare `is_live=False` even though they call APIs;
retry/resampling requests were not individually reserved by the harness.
The Gemini source also includes an environment-file fallback. These features
are preserved for an honest historical record, not recommended configuration.
Importing the historical runner can execute its top-level program. No offline
review command imports these scripts, and no API key is required to inspect or
recompute the archived evidence.

For the supported offline path, from the repository root:

```sh
python tools/recompute_replications.py --output runs/replication-arithmetic.json
```

Install the repository's `requirements-lock.txt` in a suitable environment
first. The output must be new. The command independently derives forecasts,
scores and history-level statistics from original recorded response rows for
all three providers and verifies archived input hashes. It does not invoke
the harness, an SDK, a network client or a model.

See [API replication provenance](../docs/API_REPLICATION_PROVENANCE.md) for
record counts, missing trace fields and the distinction between provider
replication and independent implementation. Future live API execution needs
a separately versioned dispatcher: truthful live flags, environment-variable
credentials only, lazy SDK imports, per-physical-attempt budget reservation,
durable rejected-response/error traces, explicit recovery authorization,
and nonzero failure exits. No such live route is advertised by this archival
delivery. Applicable contributor and third-party rights remain as described
in [NOTICE.md](../NOTICE.md); archival inclusion does not establish rights in
proprietary model weights or services.
