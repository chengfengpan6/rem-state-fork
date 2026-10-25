"""V2 semantic delivery verification, independent scoring, and exact replay.

Replay reconstructs intended prompts from config/tape/earlier responses, so
rehashing an altered map cannot make that alteration pass. Reconstruction uses
the engine and therefore is not an independent proof that the design is sound.
Separate checks below recompute scores directly and inspect the actual CLI text.
"""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
import tempfile

from rem_harness.data import REL
from rem_harness.models import digest, expected_calls, validate_config
from rem_harness.providers import ReplayProvider, build_prompt
from rem_harness.engine import Engine
from rem_harness.schemas import validate_response


def verify_v2(folder):
    folder = Path(folder)
    checks = []
    def check(name, passed, detail=""):
        checks.append({"check": name, "passed": bool(passed), "detail": str(detail)})
    def read(name):
        return json.loads((folder/name).read_text(encoding="utf-8"))
    manifest, summary, checkpoint, tapes = [read(n) for n in ("manifest.json", "summary.json", "checkpoint.json", "tapes.json")]
    config = validate_config(manifest["config"])
    events = [json.loads(l) for l in (folder/"events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    calls = [json.loads(l) for l in (folder/"calls.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    req = [e for e in calls if e["event"] == "call_request"]
    resp = [e for e in calls if e["event"] == "call_response"]
    complete = manifest["status"] == summary["status"] == "completed"
    if complete:
        check("strict_call_sequence", all(r.get("event") == ("call_request" if i%2==0 else "call_response")
              and r.get("call_id") == f"call-{i//2+1:06d}" for i,r in enumerate(calls)))
    check("config_hash", digest(config) == manifest["config_hash"])
    check("calls_mirror_events", calls == [e for e in events if e["event"].startswith("call_")])
    check("event_sequence", [e["event_index"] for e in events] == list(range(1, len(events)+1)))
    check("planned_call_count", manifest["expected_successful_calls"] == expected_calls(config))
    counts = Counter((r["seed"], r["branch"]) for r in req)
    for (seed, branch), n in counts.items():
        cap = config["formation_call_cap"] if branch == "formation" else config["per_branch_call_cap"]
        check(f"branch_budget:{seed}:{branch}", n <= cap, f"{n}/{cap}")
    check("global_budget", len(req) <= config["max_calls"])
    check("requested_model_consistent", len({r.get("requested_model") for r in req}) <= 1)
    forbidden = {"oracle_probability", "true_reliability", "REL", "history_metrics", "condition", "branch"}
    def keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k
                yield from keys(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from keys(v)
    responses_by_id = {r["call_id"]: r for r in resp}
    for request in req:
        ident = request["call_id"]
        payload = request["payload"]
        check("research_only_fields:"+ident, not(forbidden & set(keys(payload))))
        check("visible_hash:"+ident, digest(payload["slots"]) == request["visible_state_hash"])
        is_map = request["kind"] in ("map", "audit_map", "audit_recall")
        check("stage_map_instruction:"+ident, ("map_instruction" in payload["task"]) == is_map)
        visible_rounds = len(payload["slots"]["LE"])
        check("visible_ledger:"+ident, payload["slots"]["LE"] == tapes[str(request["seed"])][:visible_rounds])
        response = responses_by_id.get(ident)
        if response:
            try:
                validate_response(response["response"], request["schema"])
                valid = True
            except Exception:
                valid = False
            check("response_schema:"+ident, valid)
            trace = response.get("provider_trace", {})
            if manifest.get("provider", {}).get("is_live"):
                check("live_transport_trace_present:"+ident,
                      all(k in trace for k in ("user_prompt","system_template","schema_sha256","requested_model")))
                check("live_trace_requested_model:"+ident,
                      trace.get("requested_model") == manifest["provider"].get("requested_model"))
                check("live_trace_schema_hash:"+ident, trace.get("schema_sha256") == digest(request["schema"]))
            if "user_prompt" in trace:
                system, prompt = build_prompt(request["kind"], payload, request["schema"])
                check("transport_prompt:"+ident, trace["user_prompt"] == prompt and trace.get("system_template") == system)
            if trace.get("model_identity_status") == "not_exposed_by_cli":
                check("unknown_served_id_not_invented:"+ident, trace.get("served_model_id") is None)
    # Independent joint-mass calculation, not the engine scorer.
    round_events = [e for e in events if e["event"] == "round_completed"]
    for i, row in enumerate(round_events):
        tape_row = tapes[str(row["seed"])][row["round_index"]-1]
        mass = []
        for truth in (0, 1):
            weight = .5
            for source, signal in tape_row["signals"].items():
                r = REL[tape_row["context"]][source]
                weight *= r if signal == truth else 1-r
            mass.append(weight)
        q = mass[1]/sum(mass)
        p = sum(row["actor_forecasts"].values())/len(row["actor_forecasts"])
        check(f"independent_score:{i}", all((isclose(row["probability"], p, abs_tol=1e-13),
              isclose(row["oracle_probability"], q, abs_tol=1e-13),
              isclose(row["cBR"], (p-q)**2, abs_tol=1e-13),
              isclose(row["brier"], (p-tape_row["truth"])**2, abs_tol=1e-13))))
    if complete:
        check("complete_response_count", len(req) == len(resp) == expected_calls(config))
        check("no_recorded_failure", not any(r["event"] == "call_error" for r in calls))
        try:
            with tempfile.TemporaryDirectory(prefix="rem-semantic-") as tmp:
                provider = ReplayProvider(folder/"calls.jsonl")
                replayed = Engine(provider, config, Path(tmp)/"replay").run()
                check("reconstructed_semantic_requests", replayed["status"] == "completed", replayed.get("error"))
                check("all_responses_consumed", provider.index == len(resp))
                for name, original in (("checkpoint.json", checkpoint), ("tapes.json", tapes)):
                    restored = json.loads((Path(tmp)/"replay"/name).read_text(encoding="utf-8"))
                    check("reconstructed_"+name, restored == original)
                check("reconstructed_seed_results", replayed["seed_results"] == summary["seed_results"])
        except Exception as error:
            check("reconstructed_semantic_requests", False, type(error).__name__+": "+str(error)[:400])
    else:
        check("complete_not_claimed", manifest["status"] != "completed")
    failures = [c for c in checks if not c["passed"]]
    return {"verification_version": "2-semantic", "verified_at_utc": datetime.now(timezone.utc).isoformat(),
            "recording": folder.name, "status": "invalid" if failures else "verified_complete" if complete else "incomplete",
            "recorded_run_status": manifest["status"], "checks_total": len(checks), "checks_failed": len(failures),
            "checks": checks, "failures": failures,
            "calls": {"requests": len(req), "responses": len(resp), "expected": expected_calls(config)},
            "source_hashes": {n: sha256((folder/n).read_bytes()).hexdigest() for n in ("manifest.json","summary.json","tapes.json","calls.jsonl","events.jsonl","checkpoint.json")},
            "scope": "Reconstructed prompt semantics plus independent scores. No live model call, hidden-context verification, statistical inference or proof of organizational construct validity."}
