# Targeted Y-profile map-content diagnostic

Execution status: **completed**. Completed histories: **30/30**.
Planned successful path: 3,600 calls; cumulative recorded transport reservations: 3600.
The requested model remains `gpt-5.6-luna` through the official Codex CLI,
ChatGPT login, low reasoning. A requested alias is not immutable weight attestation.

The prospective primary history-level P−E cBR estimate is 0.21002870,
95% t interval [0.1785239938919171, 0.2415334012718417], two-sided p=3.83281e-14, complete-pair n=30.
See analysis.json for the prespecified bootstrap, Holm-adjusted secondary
comparisons, A/A descriptions, direction diagnostic, all history outcomes and
missing-history bounds. This is a targeted conditional diagnostic, not the
original H1–H4 hypothesis study or a general estimate for human organizations.

Each eligible history has three formation rounds, one per context. Eligibility
uses only exogenous formation observations; in Y it implies A wrong and B right.
P swaps the complete Y:A/Y:B E-map cells. Both fixed Y profiles independently
clone the same fork. There is no profile feedback, update, or cross-profile
writeback. Records remain accessible in every arm, including R0/R0rep.

Original request/response/event files, all attempts, checkpoints, schedules and
manifests are unchanged. Source bytes from the pre-execution freeze are under
source_snapshot. Provenance hashes identify copied and derived files separately.
The frozen code commit is `358b4eb7f4796437d19de3640ab2f04fac620c2a`. Earlier v1
and v2 evidence remains separate; it is not pooled into this diagnostic.

## Offline review

From the repository root after installing requirements-lock.txt:

```sh
python tools/run_targeted.py verify --recording evidence/luna-targeted-30histories --output runs/targeted-verification.json
python tools/run_targeted.py replay --recording evidence/luna-targeted-30histories --output runs/targeted-replay
python tools/analyze_targeted.py evidence/luna-targeted-30histories --output runs/targeted-analysis.json
```

Create runs first. Output paths must be new. Full replay requires all histories
complete. An incomplete archive instead retains the failed or unfinished states
and its conditional complete-pair analysis. Never run live to inspect an archive.
See [the targeted protocol](../../docs/targeted_protocol_2026-10-25.md) and
[the frozen analysis plan](../../docs/targeted_analysis_plan_2026-10-25.md).

## Secondary contrasts

| Comparison | Mean cBR difference | Marginal 95% t interval | Holm-adjusted p |
|---|---:|---|---:|
| H − E | -0.00025395 | [-0.011156782529559563, 0.010648890212449077] | 0.962332 |
| H − R0 | -0.05509228 | [-0.07152750081601268, -0.03865705204594018] | 3.14003e-07 |

These two comparisons form a separately adjusted exploratory family; their intervals are marginal, not simultaneous. Positive differences indicate greater prediction loss. The observed H-versus-R0 improvement and P-versus-E harm concern different interventions. The near-zero H-versus-E estimate does not establish equivalence. A/A repetition remains descriptive and is not an equivalence test.
