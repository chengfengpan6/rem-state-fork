# Gemini Flash API replication archive

This directory contains **233 supplied files copied without byte changes**:
the completed 30-history recording, earlier interrupted attempts, original
analysis, supplied verification report and execution log. `SOURCE_MANIFEST.json`
maps every original logical path to its archived name and SHA-256. Original
metadata retain `gemini38flash_low_30seeds`; contents have not been rewritten
to match this directory name.

The final analysis uses 3,600 distinct successful logical responses. Across
all attempt files there are 3,732 response rows because 132 successful prefix
rows were copied into two resumed attempts. One HTTP 400 error is preserved.
Eight complete earlier histories (960 responses), the recovered 132-response
prefix, and 2,508 new accepted responses account for the final 3,600. The
`standin_usage.json` and execution log cover the resumed 2,508-response segment
and report two transport retries; they are not full-run physical-API ledgers.

Accepted response metadata report `gemini-3.8-flash`. This does not attest
immutable weights. The historical stand-in flags `is_live=False` and
`physical_dispatch=False` are misleading as physical-dispatch measurements;
they are preserved unchanged for provenance.

`verification_supplied.json` reports 12,967 checks and zero failures. It is
not a separate complete exact-replay receipt. The archive retains old error,
cancelled and completed attempts; do not sum every response row as a new
experimental observation. Missing individual internal retries and rejected
outputs have not been retroactively recovered.

From the repository root:

```sh
python tools/recompute_replications.py --output runs/replication-arithmetic.json
```

The command is offline and checks all three providers. See
[API replication provenance](../../docs/API_REPLICATION_PROVENANCE.md) for
limitations, source bindings and safe review commands.
