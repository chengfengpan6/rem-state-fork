# Targeted validation and scope

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
See [the targeted protocol](targeted_protocol_2026-10-25.md) and
[the frozen analysis plan](targeted_analysis_plan_2026-10-25.md).

## Secondary contrasts

| Comparison | Mean cBR difference | Marginal 95% t interval | Holm-adjusted p |
|---|---:|---|---:|
| H − E | -0.00025395 | [-0.011156782529559563, 0.010648890212449077] | 0.962332 |
| H − R0 | -0.05509228 | [-0.07152750081601268, -0.03865705204594018] | 3.14003e-07 |

These two comparisons form a separately adjusted exploratory family; their intervals are marginal, not simultaneous. Positive differences indicate greater prediction loss. The observed H-versus-R0 improvement and P-versus-E harm concern different interventions. The near-zero H-versus-E estimate does not establish equivalence. A/A repetition remains descriptive and is not an equivalence test.


## Validation record

```json
{
  "validation_schema": "targeted-final-validation-1",
  "status": "validated_complete",
  "validated_utc": "2026-10-26T01:00:44.345143+00:00",
  "recording": "luna-targeted-30histories-20261025",
  "protocol_version": "rem-prototype-0.2-targeted-Y-v1",
  "config_hash": "4c3cf95715e100156417a7a90d0ece114b415a0d091e8d0bdc2c9d7bef02674e",
  "operational_code_commit": "358b4eb7f4796437d19de3640ab2f04fac620c2a",
  "new_model_calls_by_validation": 0,
  "fresh_model_replication_performed": false,
  "execution": {
    "planned_histories": 30,
    "completed_histories": 30,
    "logical_successful_responses_latest_attempts": 3600,
    "all_attempt_successful_response_rows": 3600,
    "all_attempt_error_rows": 0,
    "reused_prefix_response_rows": 0,
    "observed_reserved_attempts": 3600,
    "observed_physical_dispatches": 3600,
    "cumulative_transport_reservations": 3600,
    "hard_global_cap": 3660,
    "per_history_formation_cap": 32,
    "per_history_arm_cap": 20,
    "cli_version_counts_all_archived_responses": {
      "codex-cli 0.162.0-alpha.17.2": 3600
    },
    "served_model_id_counts_all_archived_responses": {
      "None": 3600
    },
    "model_identity_status_counts_all_archived_responses": {
      "not_exposed_by_cli": 3600
    },
    "requested_model": "gpt-5.6-luna",
    "served_identity_not_inferred_from_alias": true
  },
  "verification": {
    "status": "verified_complete",
    "checks_total": 16568,
    "checks_failed": 0,
    "receipt_binds_exact_original_inventory": true,
    "recording_inventory_sha256": "36cf81529e62c4214191ea70a02727bade06b37c34ef54f6a0fc3ea2ae72662f",
    "report_sha256": "bc3074156482e7aacdbbd2f97a5e231bcc2b723f0b1f250b966822489b790e12",
    "receipt_sha256": "438d0419df3df6a58c148e0997e8acbfab3d46ffe0850e97b099df620a2f14f5"
  },
  "replay": {
    "status": "exact_recorded_response_replay",
    "histories": 30,
    "responses": 3600,
    "request_payload_schema_response_equality": true,
    "checkpoint_tape_profiles_branch_results_equality": true,
    "new_model_calls": 0,
    "replay_inventory_sha256": "f9491470b1b018edaed98f6de6456c5df04a6c54ff8ac09edf160af7e6ddf730"
  },
  "analysis": {
    "status": "terminal_complete_study",
    "primary_complete_histories": 30,
    "input_files_hash_validated": 32,
    "source_sha256": "51831cedefffd67fcfd5b04a383e3fc976c5871dda46ede0e30b08598977ab6a",
    "plan_sha256": "e6b702847db398f30f3621e4c8959c3d69e902ce3998ffd0e5756716ee70b66d",
    "source_matches_fixed_pre_execution_commit": true,
    "inference_recomputed_by_aggregator": false
  },
  "source_provenance": {
    "exact_frozen_files_validated": 14,
    "runtime_package_matches_freeze": true,
    "validation_source_matches_fixed_git_content": true,
    "allowed_git_normalization_only": "CRLF/LF; exact execution bytes remain separately frozen"
  },
  "pre_run_validation": {
    "tests_passed": 114,
    "tests_failed": 0,
    "same_machine_fresh_clone_and_environment": true,
    "new_model_calls": 0,
    "historical_record_not_rerun_by_aggregator": true
  },
  "input_files_sha256": {
    "verification": "bc3074156482e7aacdbbd2f97a5e231bcc2b723f0b1f250b966822489b790e12",
    "verification_receipt": "438d0419df3df6a58c148e0997e8acbfab3d46ffe0850e97b099df620a2f14f5",
    "analysis": "3cc19ef61d40c2389e1a849aba8d1451795aa2f5c62e26e0c2d4916dacbeaaf9",
    "freeze": "d62371f4d21546589290261c8a008b52e878cb4e13ef6beeb2eb80ca14040aee",
    "clean_validation_pre_run": "942c83a890c8d47e3d2e1a217f2fc67f40dbedcbb5a269f254a5e61a79ec7cd2",
    "preflight_test_log": "34edd059ce113189f6b8bad2d667f05122031b3ecb32c7aab5ee66f53e979b99",
    "clean_test_log": "04ba7838421aef84bafe4800b9d46791a7c5cb6a7e7114ff95a5fa73e6d73d0d",
    "private_inventory": "bed2cf5e9c5303a8758220875479b861d2d3c5e1e1ec8ab4abec99abba008832"
  },
  "raw_recording_file_count": 213,
  "replay_file_count": 212,
  "aggregator_source_sha256": "cd77f7ac09db6f435aa033b720dc12a39c2259b84e31cfbc06a2f9e41029efa5",
  "original_record_bytes_changed": false,
  "scope_limits": [
    "Exact replay consumes stored responses; it is not fresh-model replication.",
    "Requested alias does not independently identify served weights; hidden host/server context is unobservable.",
    "Verification shares execution components; hashes and replay do not establish scientific construct validity.",
    "This aggregation validates provenance and consistency, not the inferential assumptions or a scientific hypothesis."
  ]
}
```
