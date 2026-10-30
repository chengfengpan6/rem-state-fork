"""Independently reconstruct three-provider statistics from archived call responses.

Offline only: no harness, adapter, SDK or network imports. Requires the repository
requirements-lock.txt (NumPy, SciPy and jsonschema). Existing outputs are refused.
Example: python tools/recompute_replications.py --output runs/replication-arithmetic.json
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import statistics
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inside(root, relative):
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()) and path.is_file(), "Invalid archive path: " + str(relative))
    return path


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def describe(values, student_t, infer=False):
    n = len(values)
    require(n >= 2, "At least two history differences are required")
    mean, sd = statistics.mean(values), statistics.stdev(values)
    se = sd / math.sqrt(n)
    result = {"n": n, "mean": mean, "sd": sd, "se": se,
              "median": statistics.median(values), "min": min(values), "max": max(values),
              "positive": sum(x > 0 for x in values), "negative": sum(x < 0 for x in values),
              "exact_zero": sum(x == 0 for x in values),
              "mean_absolute": statistics.mean(abs(x) for x in values),
              "root_mean_square": math.sqrt(statistics.mean(x*x for x in values))}
    if infer:
        require(sd > 0, "Degenerate variance: inferential quantities must not be invented")
        statistic, critical = mean / se, float(student_t.ppf(.975, n-1))
        result.update(t=statistic, df=n-1, p_two_sided=float(2*student_t.sf(abs(statistic), n-1)),
                      ci95=[mean-critical*se, mean+critical*se])
    return result


def reconstruct(label, root, np, student_t, Validator, tolerance):
    root = root.resolve()
    manifest, summary, reference = (read(root / name) for name in ("manifest.json", "summary.json", "analysis.json"))
    require(manifest["status"] == summary["status"] == "completed", label + ": incomplete recording")
    seeds = [str(x) for x in manifest["config"]["seeds"]]
    require(len(seeds) == len(set(seeds)) == 30, label + ": expected the frozen 30 distinct histories")
    require(seeds == [x["seed"] for x in reference["histories"]], label + ": analysis seed order differs")
    require(reference["recorded_config_hash"] == manifest["config_hash"], label + ": configuration hash differs")
    bound = {}
    for relative, expected in reference["input_sha256"].items():
        value = sha(inside(root, relative))
        require(value == expected, label + ": analysis input differs: " + relative)
        bound[relative] = value
    archive_manifest = root / "SOURCE_MANIFEST.json"
    archive_files = 0
    if archive_manifest.exists():
        for entry in read(archive_manifest)["files"]:
            require(sha(inside(root, entry["archived_path"])) == entry["sha256"], "Archive byte mismatch")
            archive_files += 1

    # Derive each oracle from the documented matrix with exact rational arithmetic.
    profiles = {"Y100": (1, 0, 0), "Y011": (0, 1, 1)}
    reliability = (Fraction(1, 2), Fraction(17, 20), Fraction(13, 20))
    q = {}
    for name, signal in profiles.items():
        one = math.prod(r if s else 1-r for r, s in zip(reliability, signal))
        zero = math.prod(1-r if s else r for r, s in zip(reliability, signal))
        q[name] = float(one/(one+zero))
    arms = ("P", "E", "H", "R0", "R0rep")
    pairs = {"P_minus_E": ("P", "E"), "H_minus_E": ("H", "E"),
             "H_minus_R0": ("H", "R0"), "R0rep_minus_R0": ("R0rep", "R0"),
             "E_minus_R0": ("E", "R0")}
    differences = {key: [] for key in pairs}
    arm_scores, forecast_values, aligned, aa_forecast, histories = defaultdict(list), defaultdict(list), [], [], []
    validators, count, models, trace_fields = {}, Counter(), Counter(), Counter()
    stored, selected_traces, all_response_keys, source_hashes = {}, [], [], Counter()
    schema_count, max_difference, final_forecasts = 0, 0.0, 0
    plugin_matches, plugin_distance, plugin_pull, h_error = [], [], [], []
    resumed_checks = []

    # Count every attempt, including failed/cancelled attempts and duplicate prefixes.
    for path in sorted(root.glob("histories/*/attempt_*/calls.jsonl")):
        raw = rows(path)
        stored[path.parent] = raw
        requests = {x["call_id"]: x for x in raw if x["event"] == "call_request"}
        count.update(x["event"] for x in raw)
        for item in raw:
            if item["event"] != "call_response":
                continue
            trace_fields.update(item["provider_trace"].keys())
            key = json.dumps(requests[item["call_id"]]["schema"], sort_keys=True)
            if key not in validators:
                validators[key] = Validator(json.loads(key))
            validators[key].validate(item["response"])
            if "raw_response" in item["provider_trace"]:
                require(item["provider_trace"]["raw_response"] == item["response"], "Raw/accepted response differs")
            schema_count += 1
        hm = read(path.parent / "manifest.json")
        source_hashes[hm["source_hashes"]["combined_sha256"]] += 1

    for seed, old in zip(seeds, reference["histories"]):
        directory = inside(root, summary["history_paths"][seed] + "/manifest.json").parent
        history_summary = read(directory / "summary.json")
        require(history_summary == summary["history_results"][seed], "Per-history and root summaries differ")
        raw = stored[directory]
        requests = {x["call_id"]: x for x in raw if x["event"] == "call_request"}
        responses = [x for x in raw if x["event"] == "call_response"]
        require(len(requests) == len(responses) == 120, "Completed history must contain 120 request/response pairs")
        cp = read(directory / "checkpoint.json")
        H = {(x["context"], x["source"]): x["estimate"] for x in cp["H0"]["cells"]}
        E = {(x["context"], x["source"]): x["estimate"] for x in cp["E0"]["cells"]}
        h_error.append(statistics.mean(abs(H[k]-E[k]) for k in H))
        if directory.name != "attempt_001":
            previous = stored[directory.parent / "attempt_001"]
            previous_q = {x["call_id"]: x for x in previous if x["event"] == "call_request"}
            previous_r = {x["call_id"]: x for x in previous if x["event"] == "call_response"}
            for item in responses:
                call_id = item["call_id"]
                if call_id in previous_r:
                    require(item["response"] == previous_r[call_id]["response"], "Recovered prefix response differs")
                    require(all(requests[call_id][k] == previous_q[call_id][k] for k in ("kind", "branch", "diagnostic_profile_id", "payload", "schema")), "Recovered prefix request differs")
            resumed_checks.append({"seed": seed, "reused_prefix_responses": len(previous_r), "exact": True})
        final = defaultdict(dict)
        for item in responses:
            request, trace = requests[item["call_id"]], item["provider_trace"]
            selected_traces.append(trace)
            models[(trace.get("provider"), trace.get("requested_model"), trace.get("served_model_id"))] += 1
            payload, probability = request["payload"], item["response"].get("probability")
            if item["branch"] in ("team_P", "team_E", "team_H") and item["kind"] == "forecast_initial":
                cell = next(c for c in payload["slots"]["H"]["cells"] if c["source"] == payload["actor"]["id"] and c["context"] == payload["current"]["context"])
                ideal = cell["estimate"] if payload["current"]["private_signal"] else 1-cell["estimate"]
                plugin_matches.append(abs(probability-ideal) < 1e-9)
                plugin_distance.append(abs(probability-ideal))
                if ideal != .5:
                    plugin_pull.append((probability-.5)/(ideal-.5))
            if item["branch"] != "formation" and item["kind"] == "forecast_revision":
                key = (item["branch"][5:], item["diagnostic_profile_id"])
                actor = payload["actor"]["id"]
                require(actor not in final[key], "Duplicate final actor response")
                final[key][actor] = probability
                final_forecasts += 1
        probability, scores = {}, {}
        for arm in arms:
            for profile in profiles:
                key = (arm, profile)
                require(set(final[key]) == set("ABC"), "Three final actors required")
                probability[key] = statistics.mean(final[key].values())
                scores[key] = (probability[key]-q[profile])**2
                source = old["arms"][arm][profile]
                require(final[key] == source["actor_forecasts"], "Analysis actor forecasts differ from responses")
                max_difference = max(max_difference, abs(probability[key]-source["probability"]), abs(scores[key]-source["cBR"]))
                forecast_values[key].append(probability[key])
            arm_scores[arm].append(statistics.mean(scores[arm, p] for p in profiles))
        row = {"seed": seed}
        for name, (left, right) in pairs.items():
            value = statistics.mean(scores[left, p]-scores[right, p] for p in profiles)
            differences[name].append(value)
            row[name] = value
            if name in old["contrasts"]:
                max_difference = max(max_difference, abs(value-old["contrasts"][name]["mean"]))
        aligned.append(((probability["P", "Y100"]-probability["E", "Y100"])-(probability["P", "Y011"]-probability["E", "Y011"]))/2)
        aa_forecast.append(statistics.mean(abs(probability["R0rep", p]-probability["R0", p]) for p in profiles))
        histories.append(row)
    stats = {k: describe(v, student_t, k in ("P_minus_E", "H_minus_E", "H_minus_R0")) for k, v in differences.items()}
    ranked = sorted(("H_minus_E", "H_minus_R0"), key=lambda k: stats[k]["p_two_sided"])
    adjusted = 0.0
    for index, key in enumerate(ranked):
        adjusted = max(adjusted, min(1.0, (2-index)*stats[key]["p_two_sided"]))
        stats[key]["holm_adjusted_p"] = adjusted
    rng = np.random.default_rng(20261025)
    resampled = rng.choice(np.asarray(differences["P_minus_E"]), size=(10000, 30), replace=True).mean(axis=1)
    bootstrap = np.quantile(resampled, [.025, .975], method="linear").tolist()
    loo = [statistics.mean(differences["P_minus_E"][:i]+differences["P_minus_E"][i+1:]) for i in range(30)]
    for name, old in [("P_minus_E", reference["primary"]), *reference["exploratory_secondary_family"].items()]:
        for key in ("mean", "sd", "se", "t", "p_two_sided"):
            max_difference = max(max_difference, abs(stats[name][key]-old[key]))
        max_difference = max(max_difference, *(abs(x-y) for x, y in zip(stats[name]["ci95"], old["ci95"])))
        if name != "P_minus_E":
            max_difference = max(max_difference, abs(stats[name]["holm_adjusted_p"]-old["holm_adjusted_p_two_member_family"]))
    max_difference = max(max_difference, *(abs(x-y) for x, y in zip(bootstrap, reference["primary_bootstrap_sensitivity"]["ci95"])))
    for key in ("mean", "sd", "mean_absolute", "root_mean_square"):
        max_difference = max(max_difference, abs(stats["R0rep_minus_R0"][key]-reference["aa_repeatability_descriptive"]["history_cBR_difference"][key]))
    require(max_difference <= tolerance, label + ": recomputation exceeds numerical tolerance")
    return {"label": label, "status": "raw_response_arithmetic_verified", "config_hash": manifest["config_hash"],
            "configured_model_field": manifest["config"]["requested_model"], "models_in_selected_traces": [{"provider": k[0], "requested_model": k[1], "served_model_id": k[2], "count": v} for k, v in models.items()],
            "seeds": seeds, "all_attempt_event_counts": dict(count), "accepted_response_schema_checks": schema_count,
            "final_actor_probabilities_reconstructed": final_forecasts, "resumed_prefix_checks": resumed_checks,
            "archival_files_hash_checked": archive_files, "analysis_input_files_hash_checked": len(bound),
            "analysis_reference_sha256": sha(root/"analysis.json"), "runtime_source_hashes_recorded": dict(source_hashes),
            "available_trace_fields_all_success_rows": dict(trace_fields), "statistics": stats, "primary_bootstrap_ci95": bootstrap,
            "primary_leave_one_out_mean_range": [min(loo), max(loo)], "aligned_shift": describe(aligned, student_t),
            "aa_mean_absolute_profile_forecast_difference": statistics.mean(aa_forecast),
            "arm_mean_cBR": {k: statistics.mean(v) for k, v in arm_scores.items()},
            "arm_mean_forecasts": {a: {p: statistics.mean(forecast_values[a, p]) for p in profiles} for a in arms},
            "initial_own_cell_plugin": {"n": len(plugin_matches), "matches": sum(plugin_matches), "criterion": "absolute difference < 1e-9", "mean_absolute_difference": statistics.mean(plugin_distance), "median_pull": statistics.median(plugin_pull), "mean_pull": statistics.mean(plugin_pull)},
            "H0_E0_mean_absolute_nine_cell_difference_unrounded": statistics.mean(h_error),
            "maximum_absolute_difference_from_reference": max_difference, "history_contrasts": histories,
            "new_model_calls": 0, "scope": "Independent arithmetic and archive binding, not a complete semantic verifier or new-model replication. E-R0 is supplementary descriptive output; no additional primary test."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True, help="New JSON file, never inside evidence")
    parser.add_argument("--absolute-tolerance", type=float, default=1e-12)
    args = parser.parse_args(argv)
    require(math.isfinite(args.absolute_tolerance) and 0 <= args.absolute_tolerance <= 1e-12, "Tolerance must be finite in [0,1e-12]")
    require(not args.output.exists(), "Output already exists")
    require(not args.output.resolve().is_relative_to((args.repo_root/"evidence").resolve()), "Do not write into evidence")
    try:
        import numpy as np
        from scipy.stats import t as student_t
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise RuntimeError("Install requirements-lock.txt in a fresh environment for offline arithmetic") from exc
    paths = {"gpt_luna": "luna-targeted-30histories", "claude_opus55": "claude-opus55-30histories", "gemini38flash": "gemini38flash-30histories"}
    adapter_root = args.repo_root / "replication_adapters" / "historical_2026_10_29"
    adapter_manifest = read(adapter_root / "SOURCE_MANIFEST.json")
    for entry in adapter_manifest["files"]:
        path = inside(adapter_root, entry["archived_path"])
        require(path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"], "Historical adapter byte mismatch")
    result = {"schema": "rem-independent-replication-arithmetic-1", "new_model_calls": 0, "absolute_tolerance": args.absolute_tolerance,
              "software": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": version("scipy"), "jsonschema": version("jsonschema")}, "tool_sha256": sha(Path(__file__)),
              "historical_adapter_files_hash_checked": len(adapter_manifest["files"]),
              "results": {label: reconstruct(label, args.repo_root/"evidence"/name, np, student_t, Draft202012Validator, args.absolute_tolerance) for label, name in paths.items()}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": "all_three_archives_arithmetic_verified", "output": str(args.output), "new_model_calls": 0,
                      "primary_means": {k: v["statistics"]["P_minus_E"]["mean"] for k, v in result["results"].items()}}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print("Offline recomputation failed: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
