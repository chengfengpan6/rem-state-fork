"""Prepare the prospective targeted-history config; never invoke an LLM.

Only the three formation observations determine eligibility. Candidate order,
eligibility, profiles and count are fixed before any actor response is observed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rem_harness.data import (DGP_VERSION, REL, SOURCES, evidence_map,
                              generate_tape, planted_evidence_map, render_map)

START_SEED = 20261027
TARGET_COUNT = 30
MAX_CANDIDATES = 10000
# Prior live-history seeds; the prospective lower bound already excludes them.
EXCLUDED_SEEDS = (20261019, 20261025, 20261026)
PROFILES = [
    {"id": "Y100", "context": "Y", "signals": {"A": 1, "B": 0, "C": 0}},
    {"id": "Y011", "context": "Y", "signals": {"A": 0, "B": 1, "C": 1}},
]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def exact(value):
    return {"numerator": value.numerator, "denominator": value.denominator,
            "decimal": float(value)}


def evaluate_candidate(seed):
    # The generator also creates an unused continuation. Only this prefix is
    # retained or examined; no future event enters selection or the profiles.
    ledger = [event.observed_record() for event in
              generate_tape(seed, 3, 1, allow_partial_post=True)[:3]]
    e = render_map(evidence_map(ledger), digits=2)
    p = render_map(planted_evidence_map(evidence_map(ledger), contexts=("Y",)), digits=2)
    ei = {(cell["context"], cell["source"]): cell for cell in e["cells"]}
    pi = {(cell["context"], cell["source"]): cell for cell in p["cells"]}
    changed = [f"{c}:{s}" for c, s in ei if ei[c, s] != pi[c, s]]
    def y_mse(index):
        return sum((Fraction(str(index["Y", s]["estimate"])) -
                    Fraction(str(REL["Y"][s]))) ** 2 for s in SOURCES) / 3
    e_mse, p_mse = y_mse(ei), y_mse(pi)
    e_b_gt_a = (Fraction(str(ei["Y", "B"]["estimate"])) >
                Fraction(str(ei["Y", "A"]["estimate"])))
    y_changed = any(cell.startswith("Y:") for cell in changed)
    no_other_context_change = all(cell.startswith("Y:") for cell in changed)
    increase = p_mse - e_mse
    eligible = (seed not in EXCLUDED_SEEDS and e_b_gt_a and y_changed and
                no_other_context_change and increase > 0)
    return {"seed": seed, "eligible": eligible,
            "excluded_previous_seed": seed in EXCLUDED_SEEDS,
            "formation_ledger": ledger,
            "formation_sha256": sha256_bytes(canonical(ledger).encode("utf-8")),
            "rendered_E": e, "rendered_P": p,
            "checks": {"E_Y_B_gt_A": e_b_gt_a, "Y_map_changed": y_changed,
                       "no_other_context_change": no_other_context_change,
                       "changed_cells": changed,
                       "Y_mse_strictly_increased": increase > 0},
            "rendered_Y_E_mse": exact(e_mse),
            "rendered_Y_P_mse": exact(p_mse),
            "rendered_Y_mse_increase": exact(increase)}


def prepare():
    candidates, selected = [], []
    for seed in range(START_SEED, START_SEED + MAX_CANDIDATES):
        record = evaluate_candidate(seed)
        candidates.append(record)
        if record["eligible"]:
            selected.append(record)
        if len(selected) == TARGET_COUNT:
            break
    if len(selected) != TARGET_COUNT:
        raise RuntimeError("Prespecified candidate limit exhausted; no relaxed eligibility")
    seeds = [x["seed"] for x in selected]
    assert len(seeds) == len(set(seeds)) == TARGET_COUNT
    assert all(x["checks"]["changed_cells"] == ["Y:A", "Y:B"] for x in selected)
    duplicate_hashes = {h: n for h, n in Counter(x["formation_sha256"] for x in selected).items()
                        if n > 1}
    selection = {
        "version": "formation-only-Y-distortion-v1",
        "algorithm": "first 30 eligible ascending integer seeds; no LLM or future-response selection",
        "source_file": "tools/prepare_targeted_histories.py",
        "selector_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "data_source_sha256": sha256_bytes((ROOT / "rem_harness" / "data.py").read_bytes()),
        "dgp_version": DGP_VERSION,
        "start_seed": START_SEED, "target_count": TARGET_COUNT,
        "maximum_candidates": MAX_CANDIDATES,
        "excluded_seeds": list(EXCLUDED_SEEDS),
        "formation_only": True, "display_decimals": 2,
        "eligibility": ["rendered E[Y,B].estimate > E[Y,A].estimate",
                        "rendered P[Y] differs from E[Y]",
                        "Y point-estimate MSE(P) > MSE(E), exact rational comparison",
                        "P swaps complete A/B cells in Y; X/Z unchanged"],
        "stopping_rule": "stop after 30 eligible histories; never inspect H or forecast outcomes",
        "candidate_count": len(candidates),
        "eligible_count": len(selected),
        "selected_seeds": seeds,
        "candidate_records_sha256": sha256_bytes(canonical(candidates).encode("utf-8")),
        "selected_observable_history_duplicate_hashes": duplicate_hashes,
        "duplicate_policy": "unique seeds required; observable-tape duplicates recorded, not outcome-selected away",
        "candidates": candidates,
    }
    config = {
        "protocol_version": "rem-prototype-0.2-targeted-Y-v1",
        "purpose": "targeted_mechanism_diagnostic", "seeds": seeds,
        "formation_rounds": 3, "profiles": PROFILES,
        "branches": [{"id": "team_" + name, "architecture": "team",
                      "condition": "R0" if name == "R0rep" else name}
                     for name in ("P", "E", "H", "R0", "R0rep")],
        "planted_map": {"contexts": ["Y"]}, "max_message_chars": 600,
        "schedule_seed": 20261027, "formation_call_cap": 32,
        "per_branch_call_cap": 20, "max_calls": 3660,
        "expected_calls": 3600, "max_workers": 2,
        "requested_model": "gpt-5.6-luna", "live_allowed": True,
        "selection": selection,
    }
    audit = {"status": "prospective offline selection only; no model responses used",
             "config": config,
             "researcher_only_profile_oracles": {
                 "Y100": exact(Fraction(21, 242)), "Y011": exact(Fraction(221, 242))},
             "planned_calls": {"formation_per_history": 30, "per_arm_per_history": 18,
                               "per_history": 120, "total": 3600},
             "interpretation": "Conditional sensitivity diagnostic, not natural-history incidence or formal H1-H4"}
    return config, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "configs" / "targeted_30histories.json")
    parser.add_argument("--audit-output", type=Path)
    parser.add_argument("--check", action="store_true", help="compare existing config; do not write")
    args = parser.parse_args()
    config, audit = prepare()
    if args.check:
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing != config:
            raise SystemExit("Config differs from deterministic preparation")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.audit_output:
            args.audit_output.parent.mkdir(parents=True, exist_ok=True)
            args.audit_output.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"mode": "check" if args.check else "prepare",
                      "candidate_count": config["selection"]["candidate_count"],
                      "seeds": config["seeds"], "expected_calls": config["expected_calls"],
                      "observable_duplicate_histories": config["selection"]["selected_observable_history_duplicate_hashes"]}))


if __name__ == "__main__":
    main()
