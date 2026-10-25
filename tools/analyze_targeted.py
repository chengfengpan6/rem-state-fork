"""Prospective history-level analysis of the targeted Y-profile diagnostic.

Reads saved JSON only. Never imports Engine or a provider and never calls a model.
Semantic integrity must be checked separately. Output is exclusively created.
See docs/targeted_analysis_plan_2026-10-25.md for the frozen analysis choices.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import isfinite, sqrt
from pathlib import Path
from statistics import fmean, median, stdev

import numpy as np
from scipy.stats import t as student_t


VERSION = "targeted-analysis-1"
PROTOCOL = "rem-prototype-0.2-targeted-Y-v1"
PLANNED_N = 30
ALPHA = .05
BOOTSTRAP_DRAWS = 10000
BOOTSTRAP_SEED = 20261025
ARMS = {"P": "team_P", "E": "team_E", "H": "team_H",
        "R0": "team_R0", "R0rep": "team_R0rep"}
PROFILES = {"Y100": {"A": 1, "B": 0, "C": 0},
            "Y011": {"A": 0, "B": 1, "C": 1}}
REL = {"X": {"A": .85, "B": .65, "C": .50},
       "Y": {"A": .50, "B": .85, "C": .65},
       "Z": {"A": .65, "B": .50, "C": .85}}
CONTRASTS = {"P_minus_E": ("P", "E"), "H_minus_E": ("H", "E"),
             "H_minus_R0": ("H", "R0"), "R0rep_minus_R0": ("R0rep", "R0")}
TERMINAL = {"completed", "error", "cancelled"}
HISTORY_STATUSES = {"completed", "error", "budget_exhausted", "cancelled", "running", "not_started"}


def number(value, name, lower=None, upper=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if lower is not None and value < lower or upper is not None and value > upper:
        raise ValueError(f"{name} is outside its admissible range")
    return float(value)


def _same(actual, expected, name, tolerance=1e-10):
    if abs(number(actual, name) - expected) > tolerance:
        raise ValueError(f"{name} does not match independently recomputed value")


def posterior(reliabilities, signals):
    """Independent .5-prior conditional-independence calculation, no engine call."""
    masses = []
    for truth in (0, 1):
        mass = .5
        for source in ("A", "B", "C"):
            r = number(reliabilities[source], "reliability", 0, 1)
            mass *= r if signals[source] == truth else 1-r
        masses.append(mass)
    if sum(masses) == 0:
        raise ValueError("Map implies zero likelihood for the fixed profile")
    return masses[1] / sum(masses)


def sign(value):
    return int(value > 0) - int(value < 0)


def describe(values):
    values = [number(x, "description value") for x in values]
    if not values:
        return {"n": 0, "mean": None, "sd": None, "median": None,
                "min": None, "max": None, "q25": None, "q75": None,
                "positive": 0, "negative": 0, "exact_zero": 0,
                "mean_absolute": None, "root_mean_square": None}
    return {"n": len(values), "mean": fmean(values),
            "sd": stdev(values) if len(values) > 1 else None,
            "median": median(values), "min": min(values), "max": max(values),
            "q25": float(np.quantile(values, .25, method="linear")),
            "q75": float(np.quantile(values, .75, method="linear")),
            "positive": sum(x > 0 for x in values), "negative": sum(x < 0 for x in values),
            "exact_zero": sum(x == 0 for x in values),
            "mean_absolute": fmean(abs(x) for x in values),
            "root_mean_square": sqrt(fmean(x*x for x in values))}


def mean_test(values, allow_inference=True):
    """One-sample t on history differences, with explicit degenerate handling."""
    result = describe(values)
    result.update({"method": "two_sided_one_sample_t_on_history_differences",
                   "alpha": ALPHA, "confidence_level": .95, "df": None,
                   "se": None, "t": None, "p_two_sided": None,
                   "ci95": None, "reject_zero_at_05": None})
    n = result["n"]
    if not allow_inference:
        result["inference_status"] = "withheld_while_execution_nonterminal"
    elif n < 2:
        result["inference_status"] = "insufficient_complete_histories"
    elif result["sd"] == 0:
        result["inference_status"] = "degenerate_sample_variance"
        result["se"], result["df"] = 0.0, n-1
    else:
        se = result["sd"] / sqrt(n)
        statistic = result["mean"] / se
        pvalue = float(2 * student_t.sf(abs(statistic), n-1))
        halfwidth = float(student_t.ppf(.975, n-1)) * se
        result.update({"inference_status": "calculated_under_history_sampling_assumptions",
                       "df": n-1, "se": se, "t": statistic, "p_two_sided": pvalue,
                       "ci95": [result["mean"]-halfwidth, result["mean"]+halfwidth],
                       "reject_zero_at_05": pvalue < ALPHA})
    return result


def bootstrap_mean(values, allow_inference=True):
    result = {"method": "history_percentile_bootstrap", "confidence_level": .95,
              "resamples": BOOTSTRAP_DRAWS, "rng": "numpy.PCG64",
              "seed": BOOTSTRAP_SEED, "quantile_method": "linear", "ci95": None,
              "role": "prespecified_sensitivity_not_second_primary_test"}
    if not allow_inference:
        result["status"] = "withheld_while_execution_nonterminal"
    elif len(values) < 2:
        result["status"] = "insufficient_complete_histories"
    else:
        data = np.asarray(values, dtype=float)
        if not np.isfinite(data).all():
            raise ValueError("Bootstrap values must be finite")
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        indices = rng.integers(0, len(data), size=(BOOTSTRAP_DRAWS, len(data)))
        means = data[indices].mean(axis=1)
        result["ci95"] = [float(x) for x in np.quantile(means, [.025, .975], method="linear")]
        result["status"] = "degenerate_empirical_distribution" if np.all(data == data[0]) else "calculated"
    return result


def holm_two(pvalues):
    """Two fixed secondary hypotheses; unavailable p counts as 1, never drops m."""
    if len(pvalues) != 2:
        raise ValueError("The exploratory Holm family must have exactly two members")
    values = [1.0 if p is None else number(p, "p value", 0, 1) for p in pvalues]
    order = sorted(range(2), key=lambda i: (values[i], i))
    adjusted, running = [None, None], 0.0
    for rank, i in enumerate(order):
        running = max(running, (2-rank) * values[i])
        adjusted[i] = min(1.0, running)
    return adjusted


def missing_bounds(values, total=PLANNED_N):
    if len(values) > total or total < 1:
        raise ValueError("Invalid planned sample size")
    missing = total-len(values)
    return {"planned_n": total, "complete_n": len(values), "missing_n": missing,
            "lower": (sum(values)-missing)/total, "upper": (sum(values)+missing)/total,
            "assumed_missing_contrast_range": [-1, 1],
            "interpretation": "logical_all_planned_history_mean_bounds_not_confidence_interval"}


def _display_estimates(mapping):
    if not isinstance(mapping, dict) or not isinstance(mapping.get("cells"), list):
        raise ValueError("Completed P/E diagnostics require a numeric map")
    indexed = {}
    for cell in mapping["cells"]:
        key = (cell["context"], cell["source"])
        if key in indexed:
            raise ValueError("Duplicate map cell")
        indexed[key] = round(number(cell["estimate"], "map estimate", 0, 1), 2)
    if set(indexed) != {(c, s) for c in REL for s in ("A", "B", "C")}:
        raise ValueError("Map must contain exactly nine context/source cells")
    return {s: indexed["Y", s] for s in ("A", "B", "C")}


def _read_profiles(branch, expected_condition):
    if branch is None:
        return {}
    if branch.get("condition") != expected_condition:
        raise ValueError("Branch condition mismatch")
    profiles = branch.get("profiles", [])
    if not isinstance(profiles, list):
        raise ValueError("Profiles must be a list")
    result = {}
    for row in profiles:
        pid = row.get("profile_id")
        if pid not in PROFILES or pid in result:
            raise ValueError("Unexpected or duplicate profile identifier")
        if (row.get("context") != "Y" or row.get("signals") != PROFILES[pid]
                or any(type(v) is not int for v in row["signals"].values())):
            raise ValueError("Profile does not match the fixed conflict battery")
        forecasts = row.get("actor_forecasts")
        if not isinstance(forecasts, dict) or set(forecasts) != {"A", "B", "C"}:
            raise ValueError("A completed profile requires exactly three actor forecasts")
        p = fmean(number(v, "actor forecast", 0, 1) for v in forecasts.values())
        q = posterior(REL["Y"], PROFILES[pid])
        loss = (p-q)**2
        _same(row["probability"], p, "aggregate probability")
        _same(row["oracle_probability"], q, "oracle probability")
        _same(row["cBR"], loss, "cBR")
        result[pid] = {"probability": p, "oracle_probability": q, "cBR": loss,
                       "actor_forecasts": forecasts}
    if branch.get("complete") is True and set(result) != set(PROFILES):
        raise ValueError("Branch marked complete is missing a fixed profile")
    if set(result) == set(PROFILES) and branch.get("mean_cBR") is not None:
        _same(branch["mean_cBR"], fmean(r["cBR"] for r in result.values()), "branch mean cBR")
    return result


def analyze_summary(summary, checkpoints, planned_seeds):
    """Analyze the core's saved schema; all inferential observations are histories."""
    seeds = [str(s) for s in planned_seeds]
    if len(seeds) != PLANNED_N or len(set(seeds)) != PLANNED_N:
        raise ValueError("This fixed plan requires exactly 30 distinct selected histories")
    if any(not s.isdecimal() for s in seeds):
        raise ValueError("History seed identifiers must be nonnegative integers")
    results = summary.get("history_results")
    if not isinstance(results, dict) or set(results) != set(seeds):
        raise ValueError("Every planned history, including not_started, must be explicitly recorded")
    status = summary.get("status")
    if status not in TERMINAL | {"running", "not_started"}:
        raise ValueError("Unrecognized execution status")
    terminal = status in TERMINAL
    histories = []
    effects = {name: [] for name in CONTRASTS}
    ids = {name: [] for name in CONTRASTS}
    alignments, alignment_ids, aa_abs_forecast = [], [], []
    for seed in seeds:
        data = results[seed]
        if str(data.get("seed")) != seed or data.get("status") not in HISTORY_STATUSES:
            raise ValueError("History identity or status mismatch")
        if terminal and data["status"] == "running":
            raise ValueError("Terminal recording cannot retain an in-flight history")
        branches = data.get("branches", {})
        if set(branches) - set(ARMS.values()):
            raise ValueError("Unexpected condition in the fixed five-arm study")
        arms = {arm: _read_profiles(branches.get(key), "R0" if arm == "R0rep" else arm)
                for arm, key in ARMS.items()}
        if data["status"] == "completed" and any(set(v) != set(PROFILES) for v in arms.values()):
            raise ValueError("Completed history does not contain the whole five-arm battery")
        h = {"seed": seed, "status": data["status"], "error": data.get("error"),
             "arms": arms, "contrasts": {}, "aligned_shift": None,
             "aa_mean_absolute_profile_forecast_difference": None}
        for name, (left, right) in CONTRASTS.items():
            if set(arms[left]) == set(PROFILES) and set(arms[right]) == set(PROFILES):
                per_profile = {pid: arms[left][pid]["cBR"]-arms[right][pid]["cBR"] for pid in PROFILES}
                value = fmean(per_profile.values())
                h["contrasts"][name] = {"mean": value, "by_profile": per_profile}
                effects[name].append(value)
                ids[name].append(seed)
            else:
                h["contrasts"][name] = None
        if h["contrasts"]["P_minus_E"] is not None:
            cp = checkpoints.get(seed)
            if cp is None:
                raise ValueError("A history with complete P/E outcomes requires its checkpoint")
            e, p = _display_estimates(cp["E0"]), _display_estimates(cp["P0"])
            directions = []
            for pid, signal in PROFILES.items():
                ideal_e, ideal_p = posterior(e, signal), posterior(p, signal)
                expected = ideal_p-ideal_e
                actual = arms["P"][pid]["probability"]-arms["E"][pid]["probability"]
                directions.append({"profile_id": pid, "ideal_E": ideal_e, "ideal_P": ideal_p,
                                   "ideal_change": expected, "direction": sign(expected),
                                   "actual_change": actual, "aligned_change": sign(expected)*actual})
            value = fmean(x["aligned_change"] for x in directions)
            h["aligned_shift"] = {"mean": value, "profiles": directions,
                                  "zero_direction_profiles": sum(x["direction"] == 0 for x in directions)}
            alignments.append(value)
            alignment_ids.append(seed)
        if h["contrasts"]["R0rep_minus_R0"] is not None:
            h["aa_mean_absolute_profile_forecast_difference"] = fmean(
                abs(arms["R0rep"][pid]["probability"]-arms["R0"][pid]["probability"]) for pid in PROFILES)
            aa_abs_forecast.append(h["aa_mean_absolute_profile_forecast_difference"])
        histories.append(h)
    if status == "completed" and any(h["status"] != "completed" for h in histories):
        raise ValueError("A completed study cannot contain incomplete histories")
    primary = mean_test(effects["P_minus_E"], terminal)
    primary["complete_history_ids"] = ids["P_minus_E"]
    primary["missing_history_ids"] = [s for s in seeds if s not in ids["P_minus_E"]]
    primary["all_planned_missing_bounds"] = missing_bounds(effects["P_minus_E"])
    boot = bootstrap_mean(effects["P_minus_E"], terminal)
    ci, bci = primary["ci95"], boot["ci95"]
    boot["disagrees_with_t_interval_on_zero_inclusion"] = (
        ((ci[0] <= 0 <= ci[1]) != (bci[0] <= 0 <= bci[1])) if ci is not None and bci is not None else None)
    if len(effects["P_minus_E"]) >= 2:
        values = effects["P_minus_E"]
        loo = [{"omitted_history": seed, "mean": fmean(values[:i]+values[i+1:])}
               for i, seed in enumerate(ids["P_minus_E"])]
        influence = {"minimum": min(loo, key=lambda x:x["mean"]),
                     "maximum": max(loo, key=lambda x:x["mean"]), "all": loo,
                     "role": "description_only_no_observations_removed"}
    else:
        influence = {"minimum": None, "maximum": None, "all": [], "role": "insufficient_histories"}
    secondary = {}
    for name in ("H_minus_E", "H_minus_R0"):
        secondary[name] = mean_test(effects[name], terminal)
        secondary[name].update({"complete_history_ids": ids[name],
                               "missing_history_ids": [s for s in seeds if s not in ids[name]],
                               "all_planned_missing_bounds": missing_bounds(effects[name]),
                               "ci_scope": "marginal_95_percent_not_simultaneous"})
    adjusted = holm_two([secondary[n]["p_two_sided"] for n in secondary])
    for (name, item), adjusted_p in zip(secondary.items(), adjusted):
        item["holm_adjusted_p_two_member_family"] = adjusted_p if terminal else None
        item["reject_holm_at_05"] = (adjusted_p < ALPHA if item["p_two_sided"] is not None else None)
    return {"analysis_version": VERSION, "protocol_version": PROTOCOL,
            "status": "terminal_complete_study" if status == "completed" else
                      "terminal_incomplete_complete_pair_analysis" if terminal else "interim_descriptive_only",
            "recorded_execution_status": status, "planned_n": PLANNED_N,
            "completed_history_count": sum(h["status"] == "completed" for h in histories),
            "statistical_unit": "formation_history_fork_family_equal_profile_weight",
            "primary_contrast": "P_minus_E", "primary": primary,
            "primary_bootstrap_sensitivity": boot, "primary_leave_one_out": influence,
            "exploratory_secondary_family": secondary,
            "aa_repeatability_descriptive": {
                "history_cBR_difference": describe(effects["R0rep_minus_R0"]),
                "history_mean_absolute_profile_forecast_difference": describe(aa_abs_forecast),
                "complete_history_ids": ids["R0rep_minus_R0"],
                "all_planned_missing_bounds": missing_bounds(effects["R0rep_minus_R0"]),
                "p_value": None, "equivalence_test_performed": False,
                "scope": "Repeat discrepancy includes sampling, order and drift; not a pure noise floor."},
            "aligned_shift_descriptive": {**describe(alignments), "complete_history_ids": alignment_ids,
                "p_value": None, "scope": "Direction implied by displayed-map plug-in predictions, not inferred model beliefs."},
            "histories": histories,
            "scope_limits": [
                "Selected synthetic histories and two fixed profiles, not all tasks or human organizations.",
                "Thirty histories are not a power guarantee; no observed/post-hoc power is calculated.",
                "No profile-to-profile learning, update trajectory, crossover or architecture inference.",
                "P/E content responsiveness, harm and natural-H formation are different propositions.",
                "History independence and stable provider response distributions remain assumptions.",
                "Complete-pair inference is conditional on completion; bounds are not confidence intervals.",
                "Arithmetic validation does not certify prompt integrity or absence of provider context."]}


def analyze(folder):
    folder = Path(folder).resolve()
    manifest_path, summary_path = folder/"manifest.json", folder/"summary.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    cfg = manifest["config"]
    if cfg.get("protocol_version") != PROTOCOL or manifest.get("protocol_version") != PROTOCOL:
        raise ValueError("Unsupported targeted protocol version")
    seeds = cfg["seeds"]
    checkpoints = {}
    hashes = {p.name: sha256(p.read_bytes()).hexdigest() for p in (manifest_path, summary_path)}
    for seed, relative in summary.get("history_paths", {}).items():
        if str(seed) not in {str(s) for s in seeds}:
            raise ValueError("An unplanned history path is present")
        path = (folder/relative).resolve()
        if not path.is_relative_to(folder):
            raise ValueError("History path escapes the recording directory")
        cp = path/"checkpoint.json"
        if cp.exists():
            checkpoints[str(seed)] = json.loads(cp.read_text(encoding="utf-8"))
            hashes[str(cp.relative_to(folder)).replace('\\', '/')] = sha256(cp.read_bytes()).hexdigest()
    report = analyze_summary(summary, checkpoints, seeds)
    report["input_sha256"] = hashes
    report["recording"] = folder.name
    report["recorded_config_hash"] = manifest.get("config_hash")
    report["analysis_source_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    plan = Path(__file__).resolve().parents[1]/"docs"/"targeted_analysis_plan_2026-10-25.md"
    report["analysis_plan_sha256"] = sha256(plan.read_bytes()).hexdigest() if plan.exists() else None
    report["software"] = {"numpy": np.__version__}
    import scipy
    report["software"]["scipy"] = scipy.__version__
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", help="Targeted run root with manifest/summary JSON")
    parser.add_argument("--output", help="New JSON output; existing evidence is never overwritten")
    args = parser.parse_args()
    encoded = json.dumps(analyze(args.recording), indent=2, ensure_ascii=False, allow_nan=False)+"\n"
    if args.output:
        with Path(args.output).open("x", encoding="utf-8") as handle:
            handle.write(encoded)
        print(str(Path(args.output).resolve()))
    else:
        print(encoded)


if __name__ == "__main__":
    main()
