"""Independently verify saved REM records; never dispatch a model call.

Usage: python tools/verify_recording.py RUN_DIRECTORY [--output PATH]
Exit codes: 0 verified complete, 1 invalid, 2 incomplete. A running recording
can be inspected, but cannot be certified complete. All calculations use saved
responses/tapes; posterior and loss calculations below do not call the engine.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
import json
from math import isclose
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rem_harness.data import REL
from rem_harness.models import actor_ids, digest
from rem_harness.schemas import validate_response


def nested_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from nested_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from nested_keys(item)


def exact_posterior(context, signals):
    """Independent direct joint-mass calculation for this IID-truth DGP."""
    weights = []
    for truth in (0, 1):
        weight = .5
        for source, signal in signals.items():
            reliability = REL[context][source]
            weight *= reliability if truth == signal else 1-reliability
        weights.append(weight)
    return weights[1]/sum(weights)


def count_plan(config):
    # Deliberately independent of models.expected_calls.
    total = 9*config["formation_rounds"]+3
    for b in config["branches"]:
        n = 1 if b["architecture"] == "solo" else 3
        total += 3*n*config["post_rounds"]
        if config["lifecycle"] == "initialized_update":
            total += n*(config["post_rounds"]//config["map_update_interval"])
        a,p = config["audit"],config["probes"]
        total += n*(int(a["at_fork"])+config["post_rounds"]//a["interval"])
        if p["enabled"]:
            per = 1 if p["mode"] == "batch" else 8*len(p["contexts"])
            total += n*per*(int(p["at_fork"])+config["post_rounds"]//p["interval"])
    return total*len(config["seeds"])


def close(a,b):
    return isinstance(a,(int,float)) and isinstance(b,(int,float)) and isclose(a,b,rel_tol=1e-11,abs_tol=1e-12)


def same_scored_rows(recomputed, saved):
    if not isinstance(saved,list) or len(recomputed)!=len(saved):return False
    numeric={"probability","brier","oracle_probability","cBR"}
    return all(set(a)==set(b) and all(close(a[k],b[k]) if k in numeric else a[k]==b[k] for k in a)
               for a,b in zip(recomputed,saved))


def verify(recording):
    recording = Path(recording)
    folder = recording if recording.is_dir() else recording.parent
    checks=[]
    snapshots={}

    def check(name, passed, detail=""):
        checks.append({"check":name,"passed":bool(passed),"detail":str(detail)})

    def read(name, required=True):
        p=folder/name
        if not p.is_file():
            if required: check("file:"+name,False,"Missing required recording file")
            return None
        raw=p.read_bytes();snapshots[name]=sha256(raw).hexdigest()
        try:return json.loads(raw.decode("utf-8-sig"))
        except Exception as error:
            check("json:"+name,False,type(error).__name__)
            return None

    manifest=read("manifest.json")
    if manifest and manifest.get("protocol_version", "").startswith("rem-prototype-0.2"):
        # Keep the original v1 verifier unchanged for historical evidence.
        import importlib.util
        module_spec = importlib.util.spec_from_file_location("rem_verify_v2", Path(__file__).with_name("verify_v2.py"))
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module.verify_v2(folder)
    complete=bool(manifest and manifest.get("status")=="completed")
    summary=read("summary.json",required=complete)
    checkpoint=read("checkpoint.json")
    tapes=read("tapes.json")

    def read_lines(name):
        p=folder/name
        if not p.is_file():
            check("file:"+name,False,"Missing required recording file")
            return []
        raw=p.read_bytes();snapshots[name]=sha256(raw).hexdigest()
        lines=raw.decode("utf-8-sig").splitlines()
        rows=[]
        for i,line in enumerate(lines):
            if not line.strip():continue
            try:rows.append(json.loads(line))
            except Exception:
                if not complete and i==len(lines)-1 and not raw.endswith(b"\n"):
                    break  # Writer may be in the middle of its last line.
                check("jsonl:"+name,False,f"Malformed line {i+1}")
        return rows

    events=read_lines("events.jsonl")
    call_file=read_lines("calls.jsonl")
    if not manifest or not checkpoint or not tapes:
        return {"status":"invalid","recording":folder.name,"checks":checks,"source_hashes":snapshots}
    config=manifest["config"]
    expected=count_plan(config)
    check("configuration_hash",digest(config)==manifest.get("config_hash"))
    check("expected_call_plan",expected==manifest.get("expected_successful_calls"),f"Computed {expected}")
    check("event_index_sequence",[e.get("event_index") for e in events]==list(range(1,len(events)+1)))
    recorded_calls=[e for e in events if e.get("event","").startswith("call_")]
    # When files are live, compare only the common complete prefix.
    if complete:
        check("calls_mirror_events",recorded_calls==call_file)
    else:
        length=min(len(recorded_calls),len(call_file))
        check("calls_mirror_common_prefix",recorded_calls[:length]==call_file[:length])
    requests=[];responses=[];pairs=[];pending=None
    request_ids=set();response_ids=set()
    for event in recorded_calls:
        kind=event["event"]
        if kind=="call_request":
            check("request_order:"+event.get("call_id","missing"),pending is None)
            pending=event
            requests.append(event)
            check("unique_request:"+event.get("call_id","missing"),event.get("call_id") not in request_ids)
            request_ids.add(event.get("call_id"))
        elif kind=="call_response":
            responses.append(event)
            check("unique_response:"+event.get("call_id","missing"),event.get("call_id") not in response_ids)
            response_ids.add(event.get("call_id"))
            paired=pending is not None and all(pending.get(k)==event.get(k) for k in ("call_id","kind","seed","branch"))
            check("response_pair:"+event.get("call_id","missing"),paired)
            if paired:pairs.append((pending,event))
            pending=None
        elif kind=="call_error":
            if complete:check("completed_without_call_error",False,event.get("call_id"))
    check("sequential_call_ids",[e.get("call_id") for e in requests]==[f"call-{i:06d}" for i in range(1,len(requests)+1)])
    check("global_budget",len(requests)<=config["max_calls"])
    if complete:
        check("completed_call_count",len(requests)==len(responses)==expected and pending is None,
              f"requests={len(requests)}, responses={len(responses)}, expected={expected}")
        check("manifest_call_count",manifest.get("calls_attempted")==len(requests))
        check("summary_completed",bool(summary and summary.get("status")=="completed"))
        check("summary_call_count",bool(summary and summary.get("calls_attempted")==len(requests)))

    forbidden={"oracle","oracle_probability","conditional_brier_regret","cBR","condition","branch","call_id","reliability_matrix","true_reliabilities"}
    historical_message_keys={"message","messages","own_private_memo","private_memo"}
    for req in requests:
        ident=req["call_id"];payload=req.get("payload",{})
        check("payload_forbidden_keys:"+ident,not (set(nested_keys(payload))&forbidden))
        slots=payload.get("slots",{})
        check("visible_slot_hash:"+ident,digest(slots)==req.get("visible_state_hash"))
        check("slot_names:"+ident,set(slots)=={"LE","LB","Pi","H"})
        check("no_historical_messages:"+ident,not (set(nested_keys(slots))&historical_message_keys))
        current=payload.get("current",{})
        check("no_current_or_future_truth:"+ident,"truth" not in set(nested_keys(current)) and
              "truth" not in set(nested_keys(payload.get("profiles",[]))))
        if req.get("kind") in ("forecast_initial","forecast_revision","message","private_memo"):
            check("history_precedes_forecast:"+ident,all(r["round_index"]<current.get("round_index",0) for r in slots.get("LE",[])))
    for req,res in pairs:
        try:
            validate_response(res["response"],req["schema"])
            check("schema:"+req["call_id"],True)
        except Exception as error:check("schema:"+req["call_id"],False,type(error).__name__)
        trace=res.get("provider_trace",{})
        if "raw_response" in trace:
            check("raw_response_matches:"+req["call_id"],trace["raw_response"]==res["response"])
        if "schema_sha256" in trace:
            check("provider_schema_hash:"+req["call_id"],trace["schema_sha256"]==digest(req["schema"]))

    # Verify the state hash chain independently of response-text generation.
    state_hashes={}
    for seed in config["seeds"]:
        empty={"LE":[],"LB":[],"Pi":{a:{"founder_records":{},"own_records":[]} for a in "ABC"},"H":{a:None for a in "ABC"}}
        state_hashes[seed,"formation"]=digest(empty)
    readonly_counts=Counter()
    starts={}
    for e in events:
        key=e.get("seed"),e.get("branch")
        if e["event"]=="branch_started":
            seedcp=checkpoint.get("seeds",{}).get(str(e["seed"]),{})
            fork=seedcp.get("forks",{}).get(e["branch"])
            check("branch_fork_hash:"+str(key),fork is not None and digest(fork)==e["initial_state_hash"])
            state_hashes[key]=e["initial_state_hash"]
            starts[key]=e
        elif e["event"]=="call_request" and key in state_hashes:
            check("call_state_chain:"+e["call_id"],e["state_hash"]==state_hashes[key])
        elif e["event"] in ("round_completed","map_updated"):
            check("state_transition:"+str(e["event_index"]),e["state_hash_before"]==state_hashes.get(key))
            state_hashes[key]=e["state_hash_after"]
        elif e["event"] in ("readonly_audit","readonly_probes"):
            readonly_counts[key+(e["event"],)]+=1
            check("readonly_state:"+str(e["event_index"]),e["state_hash_before"]==e["state_hash_after"]==state_hashes.get(key))
            check("readonly_preupdate:"+str(e["event_index"]),e.get("ordering")=="post_feedback_pre_update")
            if e.get("post_round",0)>0:
                at_checkpoint=[x for x in events if (x.get("seed"),x.get("branch"),x.get("post_round"))==
                               (e["seed"],e["branch"],e["post_round"])]
                feedback=[x["event_index"] for x in at_checkpoint if x["event"]=="round_completed"]
                updates=[x["event_index"] for x in at_checkpoint if x["event"]=="map_updated"]
                check("measurement_event_order:"+str(e["event_index"]),
                      len(feedback)==1 and feedback[0]<e["event_index"] and all(e["event_index"]<x for x in updates))

    # Reconstruct final predictions from response records, then recompute scores.
    final_predictions=defaultdict(dict)
    for req,res in pairs:
        if req["kind"]=="forecast_revision":
            p=req["payload"]
            final_predictions[req["seed"],req["branch"],p["current"]["round_index"]][p["actor"]["id"]]=res["response"].get("probability")
    recomputed=defaultdict(list)
    for e in events:
        if e["event"]!="round_completed":continue
        key=e["seed"],e["branch"],e["round_index"]
        tape=tapes.get(str(e["seed"]),[])
        if not 1<=e["round_index"]<=len(tape):
            check("round_in_tape:"+str(key),False);continue
        row=tape[e["round_index"]-1]
        forecasts=final_predictions.get(key,{})
        if not forecasts or any(not isinstance(v,(int,float)) for v in forecasts.values()):
            check("round_has_forecasts:"+str(key),False);continue
        probability=mean(forecasts.values())
        oracle=exact_posterior(row["context"],row["signals"])
        values={"probability":probability,"brier":(probability-row["truth"])**2,
                "oracle_probability":oracle,"cBR":(probability-oracle)**2}
        check("round_forecasts:"+str(key),forecasts==e.get("actor_forecasts"))
        check("round_truth_context:"+str(key),row["truth"]==e.get("truth") and row["context"]==e.get("context"))
        check("round_scores:"+str(key),all(close(e.get(k),v) for k,v in values.items()))
        recomputed[e["seed"],e["branch"]].append({"round_index":e["round_index"],"post_round":e["post_round"],
            "context":row["context"],"truth":row["truth"],"actor_forecasts":forecasts,**values})

    if complete and summary:
        f,post=config["formation_rounds"],config["post_rounds"]
        check("configured_seed_set",set(checkpoint["seeds"])==set(tapes)==set(map(str,config["seeds"])))
        branch_ids={b["id"] for b in config["branches"]}
        for seed in config["seeds"]:
            cp=checkpoint["seeds"][str(seed)]
            tape=tapes[str(seed)]
            check("frozen_tape_hash:"+str(seed),digest(tape)==manifest["tape_hashes"].get(str(seed)))
            check("tape_horizon:"+str(seed),len(tape)==f+post)
            check("formation_history:"+str(seed),cp["formation"]["LE"]==tape[:f] and len(recomputed[seed,"formation"])==f)
            check("all_configured_branches:"+str(seed),set(cp["forks"])==set(cp["branches"])==branch_ids)
            for architecture in {b["architecture"] for b in config["branches"]}:
                ids=[b["id"] for b in config["branches"] if b["architecture"]==architecture]
                baseline=None
                for branch in ids:
                    fork={k:v for k,v in cp["forks"][branch].items() if k!="H"}
                    if baseline is None:baseline=fork
                    check("map_only_fork:"+str(seed)+":"+branch,fork==baseline)
            future_hash=digest(tape[f:])
            check("matched_future_hashes:"+str(seed),all(starts.get((seed,b),{}).get("future_tape_hash")==future_hash for b in branch_ids),
                  f"{len(branch_ids)} configured branches share one future tape")
            seedsummary=summary["seed_results"][str(seed)]
            means={}
            for spec in config["branches"]:
                branch=spec["id"];state=cp["branches"][branch]["state"]
                values=recomputed[seed,branch]
                saved=seedsummary["branches"][branch]
                check("post_horizon:"+branch,len(values)==post and [v["post_round"] for v in values]==list(range(1,post+1)) and cp["branches"][branch]["completed_post_rounds"]==post)
                check("same_observed_future:"+branch,state["LE"]==tape)
                check("final_state_hash:"+branch,digest(state)==state_hashes.get((seed,branch)))
                check("summary_rounds:"+branch,same_scored_rows(values,saved.get("rounds")))
                cb=mean(v["cBR"] for v in values) if values else float("nan")
                bs=mean(v["brier"] for v in values) if values else float("nan")
                means[branch]=cb
                check("summary_means:"+branch,saved.get("completed") is True and close(saved.get("mean_cBR"),cb) and close(saved.get("mean_brier"),bs))
                a,p=config["audit"],config["probes"]
                check("audit_count:"+branch,readonly_counts[seed,branch,"readonly_audit"]==int(a["at_fork"])+post//a["interval"])
                expected_probes=(int(p["at_fork"])+post//p["interval"]) if p["enabled"] else 0
                check("probe_count:"+branch,readonly_counts[seed,branch,"readonly_probes"]==expected_probes)
            for label,pos,ref in (("primary_team_H_minus_R0","team_H","team_R0"),
                                  ("secondary_team_H_minus_E","team_H","team_E"),
                                  ("secondary_team_RU_minus_R0","team_RU","team_R0")):
                if pos in means and ref in means:
                    check("paired_difference:"+str(seed)+":"+label,close(seedsummary.get("paired_cBR_differences",{}).get(label),means[pos]-means[ref]))
    failed=[x for x in checks if not x["passed"]]
    status="invalid" if failed else "verified_complete" if complete and summary and summary.get("status")=="completed" else "incomplete"
    return {"verification_version":"1", "verified_at_utc":datetime.now(timezone.utc).isoformat(),
            "recording":folder.name,"status":status,"recorded_run_status":manifest.get("status"),
            "calls":{"requests":len(requests),"responses":len(responses),"expected":expected,"hard_cap":config["max_calls"]},
            "configured_horizons":{"formation":config["formation_rounds"],"post":config["post_rounds"]},
            "configured_branches":len(config["branches"]),"checks_total":len(checks),"checks_failed":len(failed),
            "failures":failed,"checks":checks,"source_hashes":snapshots,
            "scope":"Saved-record integrity and independent score recomputation only. No model calls, population inference or verification of hidden provider context."}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording",help="Run directory, calls.jsonl, or events.jsonl")
    parser.add_argument("--output",help="JSON verification destination; default RUN/verification.json")
    args=parser.parse_args()
    recording=Path(args.recording)
    output=Path(args.output) if args.output else (recording if recording.is_dir() else recording.parent)/"verification.json"
    try:report=verify(recording)
    except Exception as error:
        report={"status":"invalid","failure":"Verification could not parse the recording structure", "error_type":type(error).__name__}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("checks","source_hashes")},ensure_ascii=False,indent=2))
    raise SystemExit(0 if report["status"]=="verified_complete" else 2 if report["status"]=="incomplete" else 1)


if __name__=="__main__":
    if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8")
    main()
