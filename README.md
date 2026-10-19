# REM state-fork prototype

The archived GPT-5.6 Luna smoke completed on 19 October 2026: **342 successful
experimental responses**, one shared history and ten branches of three future
rounds. All 5,018 recording checks passed, and strict replay reproduced the
summary, checkpoint and event tape exactly. This is execution evidence, not a
confirmatory result. See the [run provenance](evidence/luna-smoke/provenance.json)
and [recorded replay failure and correction](docs/technical_appendix.md#8-post-smoke-file-io-correction).

An executable instrument for comparing inherited reliability summaries while
holding an agent system's observed history and future signal stream fixed.
This repository contains newly implemented code, synthetic tasks, and small
real-model execution records. It is a research prototype, not a completed study.

**Research status:** mutable external map memory is the default. This differs
from both a permanently frozen prompt and a genuinely one-time exposure. Read
[the protocol](docs/protocol.md) and [technical appendix](docs/technical_appendix.md)
before interpreting any output. The smoke does not test a hypothesis or establish
transactive memory, organizational learning, or a publication-ready contribution.

## What runs

- Three source agents form a history and independently generate reliability maps.
- The program compiles a nine-cell initial map using coordinatewise medians.
- A saved state forks into Team H/R0/E/RU, Solo H/R0, no-peer-message H/R0,
  and nominal-group H/R0: ten branches with the same future events.
- Each real-model branch has three post-fork rounds; the common formation has
  three rounds. Team rounds have nine model responses, Solo three, and nominal
  and no-peer-message rounds nine. Measurement and map updates add responses.
- The default smoke plans **342 responses**, with a hard cap of 500 attempted
  harness calls. It does not launch a 6,000–8,000-call pilot.
- Read-only map audits and one-context batch probes run before map updates.
  They never write into the continuing state. The batch probe is diagnostic,
  not an independently randomized counterfactual-profile experiment.
- Structured validation, exact rational pairwise Beta comparisons, state hashes,
  shared tape hashes, request/response logs, and strict offline replay support audit.

The program uses IID Bernoulli(0.5) truth and balances contexts in groups of
three. **Exact within-block truth quotas from the earlier manuscript are not
implemented.** This change keeps the supplied 0.5 prior and scoring oracle
consistent with the information available from past outcomes.

## Install and verify without any model calls

Python 3.12 was used for the archived run. Create a fresh environment:

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m unittest discover -s tests -v
python -m rem_harness plan --config configs/smoke.json
```

Use `requirements.txt` for the direct dependencies; `requirements-lock.txt`
records the exact packages installed for this release. No login is needed for
tests, plan, or replay. Test actors are explicitly scripted and are never
reported as real model responses.

## Replay the archived real responses

```sh
python -m rem_harness replay --config configs/smoke.json \
  --recording evidence/luna-smoke/calls.jsonl --output runs/replay
```

Replay checks the entire ordered request payload and schema before returning
each recorded response. It then rebuilds states and scores. This verifies a
recorded execution; it does not call the model or promise identical new answers.
Choose a new output directory each time; completed and failed results are never
overwritten. The evidence directory and validation report describe the actual
execution status, including any failures.

## Optional new live smoke: ChatGPT login, GPT-5.6 Luna only

Install a current [official Codex CLI](https://learn.chatgpt.com/docs/non-interactive-mode)
and sign in using `codex login`. The provider refuses API-key login and requests
exactly `gpt-5.6-luna`. It does not fall back to another model. An old CLI may
reject this model; use a current official executable.

```sh
python -m rem_harness live --config configs/smoke.json --output runs/new-live
# Optional: --codex-bin /absolute/path/to/codex
```

`REM_CODEX_BIN` can also point to the official executable. Credentials remain
with Codex; this package does not read, copy, or publish authentication files.
API-key environment variables are removed from the child process. The adapter
uses the account's Codex/ChatGPT allowance; it does not turn a subscription into
API billing credits. Availability and limits depend on the signed-in account.

Each response uses a fresh ephemeral CLI invocation with user configuration,
project instructions, plugins, shell, browser, and memory features disabled via
explicit settings. The harness rejects unexpected tool/action events. These
controls do **not** expose all host/server-added context. A successful request
establishes access to the requested model alias, not an immutable model-weight
snapshot. Provider seeds and temperature are not set by this transport.

There is no model-call retry or silent JSON repair. The first provider, schema, or
budget failure stops the run, preserving the completed trace. Codex itself is a
separate transport layer; its internal network handling is not fully controlled
or observed. A fresh run must not be mistaken for a continuation of a failed one.
Atomic file replacement has separate bounded recovery for transient Windows
`PermissionError`; it never redispatches a model request. See the technical
appendix for the recorded post-smoke correction.

## Files and interpretation

| File | Purpose |
|---|---|
| `rem_harness/data.py` | Synthetic event tape, exact pair comparison, evidence map, scoring oracle |
| `rem_harness/models.py` | Four slots, forks, map aggregation, configurations and planned call counts |
| `rem_harness/engine.py` | Synchronous stages, branch isolation, audits, updates, attempt budget |
| `rem_harness/providers.py` | Official Codex CLI transport and strict recorded-response replay |
| `configs/smoke.json` | 3+3 rounds, one seed, ten branches, mutable maps |
| `configs/smoke_standing.json` | Separately labeled frozen-map policy, for offline verification |
| `configs/formal_candidate_offline.json` | 24+84 design candidate; live execution deliberately disabled |
| `evidence/luna-smoke/` | Real-model smoke records, if successfully completed |
| `docs/` | Protocol, technical appendix, readiness boundaries and execution verification |

The main direct performance contrast proposed for a later study is seed-paired
Team H minus R0 conditional Brier regret. H minus E and RU minus R0 are secondary.
No significance tests, parameter estimates of `w`/`lambda`, or substantive effect
claims should be inferred from one seed. Full independent probes, correction
opportunities over two checkpoints, measurement validation, model recovery,
sample-size planning, and author-approved confirmatory analysis remain separate
research work. A longer offline configuration is not evidence of a live pilot.

The [proposed next measurement pilot](docs/pilot_plan.md) has an explicit
7,314-response plan. It uses six 24+24 histories, with H/R0 throughout and E/RU
on two histories. Its configurations are offline-only and it has not been run.
The full ten-branch 24+84 configuration would require 12,153 calls **per seed**;
it cannot be treated as a 6,000–8,000-call total pilot.

## Sharing and provenance

This repository excludes private correspondence, reviewer files, manuscript
attachments, copyrighted papers, inherited private code archives, and credentials.
The implementation was prepared with AI assistance and requires researcher
review. Literature and the distinction between source requirements and new
implementation choices are documented in the protocol.

The code is public for inspection. No redistribution license has yet been
selected; public visibility alone does not grant a general reuse license.
External dependency licenses remain those of their respective packages.
Journal submission, authorship, IP clearance for a reuse license, and the final
study design require the authors' decisions. Nothing here constitutes submission
to a journal or endorsement by an editor or reviewer.
