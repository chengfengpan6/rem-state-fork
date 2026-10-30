# Claude Opus API replication archive

This directory contains **217 supplied files copied without byte changes**:
the completed 30-history recording, original analysis, supplied verification
report and execution log. `SOURCE_MANIFEST.json` maps every original logical
path to its archived name and SHA-256. Original metadata retain the source run
name `opus55_low_30seeds`; the directory name is only a packaging choice.

There are 3,600 accepted responses. The adapter's aggregate usage report adds
one transport retry and five over-length-message resamples. Thus 3,600 is not
the total number of physical API attempts. The successful records report
requested and returned identifier `claude-opus-5-5`; that metadata is not an
immutable model-weight attestation. The historical `is_live=False` and
`physical_dispatch=False` flags do not mean the API was never called.

`verification_supplied.json` is the original report: 12,968 checks, zero
failures. It is not a separate exact-replay receipt. `analysis.json` retains
the original input hashes. Missing rejected-response and per-attempt trace
details have not been reconstructed or repaired.

From the repository root, the independent offline arithmetic command is:

```sh
python tools/recompute_replications.py --output runs/replication-arithmetic.json
```

This checks all three archived providers. Read the
[provenance note](../../docs/API_REPLICATION_PROVENANCE.md) before interpreting
the contrast or executing any historical adapter source. No new model calls
are necessary for review.
