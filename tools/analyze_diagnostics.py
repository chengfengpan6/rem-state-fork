"""Descriptive diagnostics from a COMPLETE saved v2 recording, never a model.

Usage: python tools/analyze_diagnostics.py RUN_DIRECTORY --output PATH
       [--baseline COMPLETE_V1_DIRECTORY]

This reader independently recomputes differences, means, oracle scores, and
ledger posterior means. It does not call Engine, import a provider, fit a model,
or certify recording integrity. Run the semantic verifier separately first.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
from statistics import mean, median, pstdev


# Explicitly the known experimental DGP, not an estimate from agent responses.
RELIABILITY = {"X": {"A": .85, "B": .65, "C": .50},
               "Y": {"A": .50, "B": .85, "C": .65},
               "Z": {"A": .65, "B": .50, "C": .85}}
FIELDS = ("estimate", "lower", "upper")


def _load(folder):
    folder = Path(folder)
    names = ("manifest.json", "summary.json", "checkpoint.json", "tapes.json")
    data = {n[:-5]: json.loads((folder / n).read_text(encoding="utf-8")) for n in names}
    for name in ("calls", "events"):
        data[name] = [json.loads(line) for line in (folder / (name + ".jsonl")).read_text(encoding="utf-8").splitlines()
                      if line.strip()]
    if data["manifest"]["status"] != "completed" or data["summary"]["status"] != "completed":
        raise ValueError("Diagnostics require a completed recording; an incomplete run is not a completed outcome")
    requests = [r for r in data["calls"] if r["event"] == "call_request"]
    responses = [r for r in data["calls"] if r["event"] == "call_response"]
    if (len(requests) != len(responses) or len({r["call_id"] for r in requests}) != len(requests)
            or [r["call_id"] for r in requests] != [r["call_id"] for r in responses]
            or len(requests) != data["manifest"]["expected_successful_calls"]
            or any(r["event"] == "call_error" for r in data["calls"])):
        raise ValueError("Completed diagnostics require unique one-to-one successful response records")
    data["requests"] = requests
    data["responses"] = {r["call_id"]: r for r in responses}
    data["input_sha256"] = {n: sha256((folder / n).read_bytes()).hexdigest()
                            for n in (*names, "calls.jsonl", "events.jsonl")}
    return data


def _index(mapping, displayed=False):
    if mapping is None:
        return {}
    result = {}
    for cell in mapping["cells"]:
        result[cell["context"], cell["source"]] = {
            k: round(cell[k], 2) if displayed and cell[k] is not None else cell[k] for k in FIELDS}
    if set(result) != {(c, s) for c in RELIABILITY for s in ("A", "B", "C")}:
        raise ValueError("A map must contain the nine distinct context/source cells")
    return result


def _differences(answer, reference, fields=FIELDS):
    """Raw response minus reference, with exact numeric NA handled explicitly."""
    common = sorted(set(answer) & set(reference))
    rows, values = [], []
    for key in common:
        delta = {field: answer[key][field] - reference[key][field] for field in fields
                 if answer[key].get(field) is not None and reference[key].get(field) is not None}
        if delta:
            values.extend(delta.values())
            rows.append({"context": key[0], "source": key[1], "differences": delta,
                         "any_nonzero": any(abs(v) > 1e-10 for v in delta.values())})
    if not values:
        return {"status": "not_applicable_no_numeric_reference", "numeric_fields_compared": 0,
                "cells": [], "mae": None, "mse": None, "max_absolute_difference": None}
    return {"status": "compared", "numeric_fields_compared": len(values),
            "mae": mean(abs(v) for v in values), "mse": mean(v * v for v in values),
            "max_absolute_difference": max(abs(v) for v in values),
            "by_field": {field: {"mae": mean(abs(row["differences"][field]) for row in rows if field in row["differences"]),
                                  "mse": mean(row["differences"][field] ** 2 for row in rows if field in row["differences"])}
                         for field in fields if any(field in row["differences"] for row in rows)},
            "cells_with_any_difference": sum(row["any_nonzero"] for row in rows), "cells": rows}


def _known_map():
    return {(c, s): {"estimate": r} for c, sources in RELIABILITY.items() for s, r in sources.items()}


def _ledger_means(ledger):
    result = {}
    for context in RELIABILITY:
        rows = [r for r in ledger if r["context"] == context]
        for source in ("A", "B", "C"):
            correct = sum(row["signals"][source] == row["truth"] for row in rows)
            result[context, source] = {"estimate": (1 + correct) / (2 + len(rows))}
    return result


def _posterior(context, signals):
    masses = []
    for truth in (0, 1):
        weight = .5
        for source, signal in signals.items():
            r = RELIABILITY[context][source]
            weight *= r if signal == truth else 1 - r
        masses.append(weight)
    return masses[1] / sum(masses)


def _coarseness(probabilities):
    if not probabilities:
        return {"count": 0, "distinct_values": [], "minimum_positive_spacing": None}
    unique = sorted(set(probabilities))
    steps = [b - a for a, b in zip(unique, unique[1:])]
    return {"count": len(probabilities), "distinct_count": len(unique), "distinct_values": unique,
            "minimum_positive_spacing": min(steps) if steps else None,
            "fractions_on_numeric_grids": {
                str(step): mean(abs(p / step - round(p / step)) <= 1e-9 for p in probabilities)
                for step in (.1, .05, .01)},
            "interpretation": "Finite-output description only; a grid match does not establish rounding policy or response resolution."}


def _map_intervention(cp, future, swapped_contexts):
    e, p = _index(cp["E0"], True), _index(cp["P0"], True)
    rows = []
    for key in sorted(e):
        changes = {k: p[key][k] - e[key][k] for k in FIELDS}
        rows.append({"context": key[0], "source": key[1], "displayed_E": e[key], "displayed_P": p[key],
                     "P_minus_E": changes, "changed_fields": [k for k in FIELDS if e[key][k] != p[key][k]]})
    changed_contexts = sorted({r["context"] for r in rows if r["changed_fields"]})
    expected = {key: dict(value) for key, value in _index(cp["E0"]).items()}
    for context in swapped_contexts:
        best = max(RELIABILITY[context], key=RELIABILITY[context].get)
        worst = min(RELIABILITY[context], key=RELIABILITY[context].get)
        expected[context, best], expected[context, worst] = expected[context, worst], expected[context, best]
    def mse(mapping):
        return sum((Fraction(str(v["estimate"])) - Fraction(str(RELIABILITY[c][s]))) ** 2
                   for (c, s), v in mapping.items()) / len(mapping)
    e_mse, p_mse = mse(e), mse(p)
    coverage = [{"round_index": row["round_index"], "context": row["context"],
                 "has_changed_displayed_cells": row["context"] in changed_contexts} for row in future]
    return {"display_decimals": 2, "cells": rows,
            "raw_P0_matches_prespecified_full_cell_swap": _differences(_index(cp["P0"]), expected)["max_absolute_difference"] <= 1e-10,
            "changed_cells": [r["context"] + ":" + r["source"] for r in rows if r["changed_fields"]],
            "changed_contexts": changed_contexts, "rendered_E_mse_vs_truth": float(e_mse),
            "rendered_P_mse_vs_truth": float(p_mse), "rendered_mse_increase": float(p_mse - e_mse),
            "strict_mse_increase_exact": p_mse > e_mse,
            "future_context_coverage": coverage,
            "future_rounds_in_changed_contexts": sum(x["has_changed_displayed_cells"] for x in coverage),
            "interpretation": "Display manipulation and task-context coverage; neither guarantees a forecast-effect sign."}


def _formation(cp):
    h, e = _index(cp["H0"]), _index(cp["E0"])
    reads = {actor: _index(mapping) for actor, mapping in cp["H0_individual_maps"].items()}
    cells = []
    for key in sorted(h):
        values = {actor: mapping[key]["estimate"] for actor, mapping in reads.items()}
        cells.append({"context": key[0], "source": key[1], "raw_readout_estimates": values,
                      "range": max(values.values()) - min(values.values()), "population_sd_descriptive": pstdev(values.values()),
                      "raw_H0": h[key], "displayed_H0": _index(cp["H0"], True)[key],
                      "raw_E0": e[key], "known_reliability": RELIABILITY[key[0]][key[1]]})
    recomputed = {key: {field: median(read[key][field] for read in reads.values()) for field in FIELDS} for key in h}
    pairs = [{"readout_a": a, "readout_b": b,
              "estimate_mse_between_readouts": _differences(reads[a], reads[b], ("estimate",))["mse"]}
             for a, b in combinations(reads, 2)]
    return {"readout_count": len(reads), "cells": cells, "pairwise_readout_disagreement": pairs,
            "H0_matches_coordinatewise_median": _differences(h, recomputed)["max_absolute_difference"] <= 1e-10,
            "H0_estimate_vs_raw_E0": _differences(h, e, ("estimate",)),
            "H0_estimate_vs_known_truth": _differences(h, _known_map(), ("estimate",)),
            "E0_estimate_vs_ledger_recalculation": _differences(e, _ledger_means(cp["formation"]["LE"]), ("estimate",)),
            "individual_readouts": {actor: {
                "estimate_vs_E0": _differences(mapping, e, ("estimate",)),
                "estimate_vs_known_truth": _differences(mapping, _known_map(), ("estimate",))}
                for actor, mapping in reads.items()},
            "interpretation": "Readout dispersion is descriptive; three related actors are not three independent formation histories."}


def _audit_diagnostics(data, seed):
    recall, own = [], []
    for request in data["requests"]:
        if request["seed"] != seed or request["kind"] not in ("audit_recall", "audit_map"):
            continue
        payload = request["payload"]
        answer = _index(data["responses"][request["call_id"]]["response"])
        displayed = _index(payload["slots"]["H"])
        common = {"call_id": request["call_id"], "branch": request["branch"],
                  "actor": payload["actor"]["id"], "post_round": payload["current"]["post_round"],
                  "state_hash": request["state_hash"], "visible_state_hash": request["visible_state_hash"]}
        if request["kind"] == "audit_recall":
            recall.append({**common, "recall_error_vs_displayed_H": _differences(answer, displayed)})
        else:
            own.append({**common, "own_estimate_deviation_vs_displayed_H": _differences(answer, displayed),
                        "own_estimate_vs_current_ledger_mean": _differences(answer, _ledger_means(payload["slots"]["LE"]), ("estimate",)),
                        "own_estimate_vs_known_truth": _differences(answer, _known_map(), ("estimate",))})
    skipped = []
    for event in data["events"]:
        if event["event"] == "readonly_audit" and event["seed"] == seed:
            for actor, status in event.get("recall_status", {}).items():
                if status != "measured":
                    skipped.append({"branch": event["branch"], "actor": actor,
                                    "post_round": event["post_round"], "status": status})
    recall_error_calls = sum(r["recall_error_vs_displayed_H"]["max_absolute_difference"] > 1e-10 for r in recall)
    return {"recall": {"response_count": len(recall), "responses_with_any_error": recall_error_calls,
                       "responses": recall, "skipped_not_applicable": skipped},
            "own_estimate": {"response_count": len(own), "responses": own},
            "interpretation": "Recall error measures transcription. Own-estimate deviation measures elicited disagreement, not observed cue weight or map-use causation. Replicate readouts are separately reported, not independent histories."}


def _branch(data, seed, branch, formation_rounds):
    requests = [r for r in data["requests"] if r["seed"] == seed and r["branch"] == branch]
    responses = [data["responses"][r["call_id"]] for r in requests]
    revisions = defaultdict(list)
    for req in requests:
        if req["kind"] == "forecast_revision":
            revisions[req["payload"]["current"]["round_index"]].append(req)
    updates = [e for e in data["events"] if e["event"] == "map_updated" and e["seed"] == seed and e["branch"] == branch]
    first_update = min((e["event_index"] for e in updates), default=None)
    rounds, raw_probabilities = [], []
    for round_index, reqs in sorted(revisions.items()):
        row = data["tapes"][str(seed)][round_index - 1]
        forecasts = {r["payload"]["actor"]["id"]: data["responses"][r["call_id"]]["response"]["probability"] for r in reqs}
        raw_probabilities.extend(forecasts.values())
        probability = mean(forecasts.values())
        oracle = _posterior(row["context"], row["signals"])
        rounds.append({"round_index": round_index, "post_round": round_index - formation_rounds,
                       "context": row["context"], "signals": row["signals"], "truth": row["truth"],
                       "actor_final_probabilities": forecasts, "aggregate_probability": probability,
                       "oracle_probability": oracle, "cBR": (probability - oracle) ** 2,
                       "brier": (probability - row["truth"]) ** 2,
                       "after_first_map_update": first_update is not None and min(r["event_index"] for r in reqs) > first_update})
    before = sum(not r["after_first_map_update"] for r in rounds)
    return {"logical_attempt_count": len(requests), "response_count": len(responses),
            "cumulative_transport_reservations_in_manifest": data["manifest"].get("cumulative_physical_attempts_by_branch", {}).get(f"{seed}:{branch}"),
            "attempt_count_basis": "Logical attempts are this recording's requests. Cumulative transport reservations, when present, include prior failures; replayed successful responses are not new physical calls.",
            "calls_by_kind": dict(Counter(r["kind"] for r in requests)),
            "physical_dispatch_flags_true": sum(r.get("provider_trace", {}).get("physical_dispatch") is True for r in responses),
            "replayed_response_count": sum(r.get("provider_trace", {}).get("resumed_from_call_id") is not None
                                           or r.get("provider_trace", {}).get("source_call_id") is not None for r in responses),
            "rounds": rounds, "actor_final_probability_coarseness": _coarseness(raw_probabilities),
            "aggregate_probability_coarseness": _coarseness([r["aggregate_probability"] for r in rounds]),
            "mean_cBR": mean(r["cBR"] for r in rounds) if rounds else None,
            "mean_brier": mean(r["brier"] for r in rounds) if rounds else None,
            "map_update_post_rounds": [e["post_round"] for e in updates],
            "forecast_window_availability": {"rounds_before_any_map_update": before,
                "rounds_after_first_map_update": len(rounds) - before,
                "terminal_update_only": bool(updates) and len(rounds) == before,
                "interpretation": "An update with no subsequent forecast supplies no behavioral correction outcome."}}


def _baseline(folder):
    data = _load(folder)
    cfg = data["manifest"]["config"]
    batches = [r for r in data["requests"] if r["kind"] == "probe_batch"]
    singles = [r for r in data["requests"] if r["kind"] == "probe"]
    ties = {}
    for seed, cp in data["checkpoint"]["seeds"].items():
        e, h = _index(cp["E0"], True), _index(cp["H0"], True)
        ties[seed] = {"displayed_E_estimate_distinct_values_per_context": {
            c: sorted({e[c, s]["estimate"] for s in ("A", "B", "C")}) for c in RELIABILITY},
            "displayed_H_estimate_distinct_values_per_context": {
            c: sorted({h[c, s]["estimate"] for s in ("A", "B", "C")}) for c in RELIABILITY}}
    windows = {str(seed): {b["id"]: _branch(data, seed, b["id"], cfg["formation_rounds"])["forecast_window_availability"]
                          for b in cfg["branches"]} for seed in cfg["seeds"]}
    return {"recording": Path(folder).name, "protocol_version": cfg["protocol_version"],
            "input_sha256": data["input_sha256"], "formation_history_count": len(cfg["seeds"]),
            "displayed_map_rank_variation": ties, "batch_probe_call_count": len(batches),
            "profiles_per_batch": dict(Counter(str(len(r["payload"]["profiles"])) for r in batches)),
            "separate_profile_probe_call_count": len(singles), "forecast_windows": windows,
            "interpretation": "Tied map entries supply no within-context map ranking contrast. Multiple predictions in one batch are joint outputs of one prompt, not independent profile interventions. These facts and a single history do not validate empirical recovery of latent ledger/map weights."}


def analyze(folder, baseline=None):
    data = _load(folder)
    cfg = data["manifest"]["config"]
    if cfg["protocol_version"] != "rem-prototype-0.2-iid-planted-split-audit" or cfg["truth_design"] != "iid_bernoulli_0.5":
        raise ValueError("This diagnostic implementation supports the specified v2 IID-truth protocol only")
    seeds = {}
    for seed in cfg["seeds"]:
        cp = data["checkpoint"]["seeds"][str(seed)]
        branches = {b["id"]: _branch(data, seed, b["id"], cfg["formation_rounds"]) for b in cfg["branches"]}
        aa = {"available": "team_R0" in branches and "team_R0rep" in branches,
              "independent_history_count": 1, "variance_estimate": None,
              "interpretation": "One same-history pair is a descriptive A/A difference, not a run-to-run variance estimate or evidence of independent backend random streams."}
        if aa["available"]:
            a, b = branches["team_R0rep"], branches["team_R0"]
            aa.update(mean_cBR_R0rep_minus_R0=a["mean_cBR"] - b["mean_cBR"],
                      mean_brier_R0rep_minus_R0=a["mean_brier"] - b["mean_brier"],
                      round_probability_differences=[{"post_round": x["post_round"],
                        "R0rep_minus_R0": x["aggregate_probability"] - y["aggregate_probability"]}
                        for x, y in zip(a["rounds"], b["rounds"])])
        formation_requests = [r for r in data["requests"] if r["seed"] == seed and r["branch"] == "formation"]
        seeds[str(seed)] = {"formation_logical_attempt_count": len(formation_requests),
                           "formation_successful_response_count": len(formation_requests),
                           "branches": branches, "A_A": aa,
                           "displayed_E_P_intervention": _map_intervention(cp, data["tapes"][str(seed)][cfg["formation_rounds"]:], cfg["planted_map"]["contexts"]),
                           "formation_maps": _formation(cp), "audits": _audit_diagnostics(data, seed)}
    no_after = all(b["forecast_window_availability"]["rounds_after_first_map_update"] == 0
                   for s in seeds.values() for b in s["branches"].values())
    probes = Counter(r["kind"] for r in data["requests"] if r["kind"] in ("probe", "probe_batch"))
    limitations = [
        {"issue": "sampling_unit", "observed": {"formation_histories": len(seeds), "future_rounds_per_branch": cfg["post_rounds"]},
         "consequence": "Actors, branches, rounds, and cells share formation history. They do not multiply the number of independent sampled histories."},
        {"issue": "parameter_identification", "observed": {"future_profiles_per_branch": cfg["post_rounds"], "separate_profile_calls": probes["probe"], "batch_profile_calls": probes["probe_batch"]},
         "consequence": "No ledger/map weighting equation is fitted here. A single realized signal profile cannot separately recover three cue weights and ledger/map influence; elicited maps are not behavioral weight observations. More rounds alone do not establish identification without a specified model and a recovery design."},
        {"issue": "post_update_response", "observed": {"no_branch_has_after_update_forecasts": no_after},
         "consequence": "Terminal map updates demonstrate state writes only; correction or adaptation requires later forecasts that actually consume the updated state."},
        {"issue": "readout_interpretation", "observed": {"solo_map_readouts": cfg["solo_map_readouts"], "nominal_map_readouts": cfg["nominal_map_readouts"], "audited_architectures": cfg["audit"]["architectures"]},
         "consequence": "Repeated readouts from one actor and distinct actor readouts differ scientifically. Recall, subjective endorsement, cue sensitivity and task consequences are separate measurements; unaudited architectures have no recall/own-estimate comparison."},
        {"issue": "empirical_recovery", "observed": {"weight_fit_performed": False, "ground_truth_agent_weights_available": False},
         "consequence": "A scripted policy with known weights can validate a fitting pipeline under its assumptions, but cannot establish recovery of unknown real-agent weights. Batch predictions, tied maps, or low-dimensional/coarse outputs do not by themselves resolve this gap."},
    ]
    critical_limits = []
    for seed, result in seeds.items():
        intervention = result["displayed_E_P_intervention"]
        if not intervention["changed_cells"]:
            critical_limits.append({"seed": seed, "issue": "no_displayed_map_intervention",
                "consequence": "E and P are identical at displayed precision; this history cannot provide a content-distortion challenge."})
        elif intervention["future_rounds_in_changed_contexts"] == 0:
            critical_limits.append({"seed": seed, "issue": "no_within_context_distorted_cell_challenge",
                "changed_map_contexts": intervention["changed_contexts"],
                "actual_future_contexts": sorted({r["context"] for r in intervention["future_context_coverage"]}),
                "positive_control_sensitivity_certified": False,
                "consequence": "The actual future forecast never uses a context whose E/P cells differ. The complete altered table is still exposed, so cross-context spillovers are possible. Any observed P-minus-E number cannot certify sensitivity to a within-context planted distortion. Formation-only eligibility was applied as declared; this coverage limitation is not a reason to select a replacement history after observing responses."})
    report = {"analysis_version": "v2-descriptive-1", "status": "complete_recording_described",
              "recording": Path(folder).name, "protocol_version": cfg["protocol_version"],
              "critical_design_limits": critical_limits,
              "input_sha256": data["input_sha256"], "logical_attempt_count": len(data["requests"]),
              "successful_response_count": len(data["responses"]), "seeds": seeds,
              "measurement_and_identifiability_limits": limitations,
              "scope": "Independent descriptive arithmetic on recorded evidence; not an integrity certificate, population inference, causal effect claim, p-value, power estimate, or parameter-recovery demonstration."}
    if baseline is not None:
        report["archived_baseline_comparison"] = _baseline(baseline)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording")
    parser.add_argument("--baseline")
    parser.add_argument("--output", help="New output file; existing evidence is never overwritten")
    args = parser.parse_args()
    report = analyze(args.recording, args.baseline)
    encoded = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.output:
        output = Path(args.output)
        # Exclusive creation also protects source evidence from an accidental
        # --output manifest.json or calls.jsonl argument.
        with output.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
        print(str(output.resolve()))
    else:
        print(encoded)


if __name__ == "__main__":
    main()
