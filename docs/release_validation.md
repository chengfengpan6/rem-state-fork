# Release validation, 19 October 2026

The real run used operational code `577026a4556178863697f20e11eb6f3b9b225d4e`.
It ran from 00:51:09 to 01:23:29 UTC and returned all **342 experimental responses**
from the requested GPT-5.6 Luna alias. Ten branches completed; no model-call
retry, schema repair, or live-run error occurred. Two setup handshakes are disclosed
separately in [transport_setup.md](transport_setup.md).

The released code/evidence checkpoint is
`9c1255f718bedc2de1c21345cda9fee9b88fde4b`. It includes the post-live file-I/O
correction `c355af56790a87c316773afe95b06439ff49eda1`. The first offline replay's
Windows replacement failure is retained in the evidence directory. Subsequent
replay used all 342 archived responses and made no model calls.

## Checks performed

- **38 offline tests passed** in the development environment and the public clone.
- **5,018 independent saved-record checks passed** in both copies.
- A clean public clone used a fresh Python 3.12.4 environment with the lock file.
- Strict replay from that clone reproduced `summary.json`, `checkpoint.json` and
  `tapes.json` exactly as parsed JSON; all six raw evidence file hashes matched
  the original provenance.
- [GitHub Actions for the code/evidence commit](https://github.com/chengfengpan6/rem-state-fork/actions/runs/39185458449)
  passed tests, independent record verification and replay on Linux.
- Complete explicit prompt/schema/response reconstruction matched all 342 records.
  A release-file scan found no credential patterns, private source paths or
  private correspondence. This is a bounded audit, not a guarantee about
  unobservable host/server context.

The tag `v0.1.0-smoke` adds the static review report to this checked code/evidence
checkpoint. Its additional files are documentation; the experimental records and
engine are unchanged. Scientific interpretation remains limited to a one-history,
3+3-round execution. No full pilot or confirmatory study was run.

The Pages deployment succeeded, but the inherited `pcf.codes` entry presents a
human-verification gate. The body beyond that gate was not verified in this
session. The standalone HTML is included in the repository and local delivery.
