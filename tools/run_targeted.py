"""Plan, explicitly run/resume, or verify/replay the fixed targeted experiment.

Only the live and resume commands instantiate a model transport. All output
directories must be new; existing recordings are never overwritten.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rem_harness.targeted import (read_json, validate_plan, run_plan, replay_plan,
                                  verify_plan)
from rem_harness.providers import CodexProvider
from rem_harness.replay_validation import validate_tolerance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "live", "resume", "replay", "verify"))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, help="new run directory, or new verification JSON file")
    parser.add_argument("--recording", type=Path, help="existing immutable run root")
    parser.add_argument("--codex-bin", help="explicit Codex CLI executable; only live/resume")
    parser.add_argument("--workers", type=int, default=1, choices=(1, 2))
    parser.add_argument("--float-tolerance", type=float, default=0.0,
                        help="verify/replay only: absolute tolerance for recomputed score fields (0 to 1e-12); default strict")
    args = parser.parse_args(argv)
    try:
        validate_tolerance(args.float_tolerance)
    except ValueError as error:
        parser.error(str(error))
    if args.float_tolerance and args.command not in ("verify", "replay"):
        parser.error("--float-tolerance is only permitted for offline verify/replay")
    if args.command in ("verify", "replay", "resume") and args.recording is None:
        parser.error("--recording is required")
    if args.command in ("live", "resume", "replay") and args.output is None:
        parser.error("--output must name a new directory")
    if args.command == "verify":
        result = verify_plan(args.recording, float_tolerance=args.float_tolerance)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
                stream.write("\n")
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0 if result["status"] == "verified_complete" else 1
    if args.command == "replay":
        result = replay_plan(args.recording, args.output, float_tolerance=args.float_tolerance)
    else:
        config = (read_json(args.config) if args.config else
                  read_json(args.recording / "manifest.json")["config"] if args.command == "resume" else
                  read_json(ROOT / "configs" / "targeted_30histories.json"))
        validate_plan(config, live=args.command in ("live", "resume"))
        if args.command == "plan":
            print(json.dumps({"status": "validated_offline_plan", "protocol_version": config["protocol_version"],
                              "independent_histories": len(config["seeds"]), "formation_calls_per_history": 30,
                              "branches": 5, "isolated_profiles_per_branch": 2, "calls_per_profile": 9,
                              "branch_calls_per_history": 18, "successful_calls_per_history": 120,
                              "expected_calls": config["expected_calls"], "global_hard_cap": config["max_calls"],
                              "formation_cap": config["formation_call_cap"], "branch_cap": config["per_branch_call_cap"],
                              "automatic_retries": False, "requested_model": config["requested_model"],
                              "selection_candidates_recomputed": config["selection"]["candidate_count"]}))
            return 0
        result = run_plan(config, args.output, lambda: CodexProvider(args.codex_bin),
                          workers=args.workers, resume_from=args.recording if args.command == "resume" else None)
    print(json.dumps({"status": result["status"], "output": str(args.output),
                      "completed_histories": sum(h["status"] == "completed" for h in result["history_results"].values()),
                      "expected_calls": result["expected_calls"],
                      "cumulative_transport_reservations": result.get("cumulative_transport_reservations"),
                      "error": result.get("error")}, ensure_ascii=False))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
