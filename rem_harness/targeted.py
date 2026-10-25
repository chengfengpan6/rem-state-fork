"""Targeted Y-profile experiment with distinct histories and durable budgets.

The v1/v2 engine is unchanged. This module reuses its request/response contract
and state projection, but never fabricates outcomes for hypothetical profiles.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from copy import deepcopy
from hashlib import sha256
from fractions import Fraction
from functools import lru_cache
from itertools import permutations
import json
from pathlib import Path
import random
import shutil
from statistics import mean
import tempfile
import threading
import time

from .data import (SOURCES, REL, generate_tape, evidence_map, history_metrics,
                   planted_evidence_map, planted_map_diagnostics, render_map,
                   oracle_probability)
from .engine import Engine, BudgetExceeded, RunCancelled, safe_error, utc_now
from .models import default_v2_config, digest, median_map
from .providers import PrefixResumeProvider, ReplayProvider, build_prompt
from .schemas import MAP_SCHEMA, PROBABILITY_SCHEMA, message_schema, validate_response

VERSION = "rem-prototype-0.2-targeted-Y-v1"
ARM_CONDITIONS = {"team_P": "P", "team_E": "E", "team_H": "H", "team_R0": "R0", "team_R0rep": "R0"}
PROFILES = [{"id": "Y100", "context": "Y", "signals": {"A": 1, "B": 0, "C": 0}},
            {"id": "Y011", "context": "Y", "signals": {"A": 0, "B": 1, "C": 1}}]


def atomic_json(path, value):
    """Retry only Windows atomic replacement, never a provider call."""
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for attempt in range(5):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.05 * (attempt + 1))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def package_sources():
    files = {"rem_harness/" + p.name: sha256(p.read_bytes()).hexdigest()
             for p in sorted(Path(__file__).parent.glob("*.py"))}
    for name in ("run_targeted.py", "prepare_targeted_histories.py"):
        path = Path(__file__).parent.parent / "tools" / name
        if path.exists():
            files["tools/" + name] = sha256(path.read_bytes()).hexdigest()
    return {"files": files, "combined_sha256": digest(files)}


@lru_cache(maxsize=8)
def _preflight_selection(serialized):
    """Check every candidate using formation data only, before any dispatch."""
    selection = json.loads(serialized)
    candidates = selection["candidates"]
    if (not candidates or selection["version"] != "formation-only-Y-distortion-v1"
            or selection["formation_only"] is not True or selection["display_decimals"] != 2
            or selection["target_count"] != 30 or selection["start_seed"] != 20261027
            or selection["excluded_seeds"] != [20261019, 20261025, 20261026]
            or selection["candidate_count"] != len(candidates)
            or selection["candidate_records_sha256"] != digest(candidates)):
        raise ValueError("Frozen formation selection metadata is inconsistent")
    eligible = []
    for offset, candidate in enumerate(candidates):
        seed = selection["start_seed"] + offset
        tape = [e.observed_record() for e in generate_tape(seed, 3, 3)[:3]]
        e = render_map(evidence_map(tape))
        p = render_map(planted_evidence_map(evidence_map(tape), ["Y"]))
        ei = {(x["context"], x["source"]): x for x in e["cells"]}
        pi = {(x["context"], x["source"]): x for x in p["cells"]}
        changed = [f"{c}:{s}" for c, s in ei if ei[c, s] != pi[c, s]]
        def mse(index):
            return sum((Fraction(str(index["Y", s]["estimate"])) - Fraction(str(REL["Y"][s]))) ** 2
                       for s in SOURCES) / 3
        em, pm = mse(ei), mse(pi)
        checks = {"E_Y_B_gt_A": ei["Y", "B"]["estimate"] > ei["Y", "A"]["estimate"],
                  "Y_map_changed": any(x.startswith("Y:") for x in changed),
                  "no_other_context_change": all(x.startswith("Y:") for x in changed),
                  "changed_cells": changed, "Y_mse_strictly_increased": pm > em}
        accepted = seed not in selection["excluded_seeds"] and all(v for k, v in checks.items() if k != "changed_cells")
        rational = lambda v: {"numerator": v.numerator, "denominator": v.denominator, "decimal": float(v)}
        expected = {"seed": seed, "eligible": accepted, "excluded_previous_seed": seed in selection["excluded_seeds"],
                    "formation_ledger": tape, "formation_sha256": digest(tape), "rendered_E": e, "rendered_P": p,
                    "checks": checks, "rendered_Y_E_mse": rational(em), "rendered_Y_P_mse": rational(pm),
                    "rendered_Y_mse_increase": rational(pm - em)}
        if candidate != expected:
            raise ValueError(f"Frozen selection differs from deterministic formation evidence for seed {seed}")
        if accepted:
            eligible.append(seed)
        if len(eligible) == 30 and offset != len(candidates) - 1:
            raise ValueError("Selection did not stop at the thirtieth eligible history")
    if len(eligible) != 30 or eligible != selection["selected_seeds"] or selection["eligible_count"] != 30:
        raise ValueError("Selected histories are not the first30 eligible candidates")
    return tuple(eligible)


def validate_plan(config, live=False):
    required = {"protocol_version", "purpose", "seeds", "formation_rounds", "profiles", "branches",
                "planted_map", "max_message_chars", "schedule_seed", "formation_call_cap",
                "per_branch_call_cap", "max_calls", "expected_calls", "max_workers",
                "requested_model", "live_allowed", "selection"}
    if set(config) != required:
        raise ValueError(f"Targeted config fields differ: {sorted(set(config) ^ required)}")
    if config["protocol_version"] != VERSION or config["purpose"] != "targeted_mechanism_diagnostic":
        raise ValueError("Unsupported targeted protocol")
    seeds = config["seeds"]
    if (not isinstance(seeds, list) or not seeds or len(set(seeds)) != len(seeds)
            or any(type(seed) is not int for seed in seeds) or len(seeds) > 30):
        raise ValueError("Use 1..30 distinct integer formation seeds; live requires all30")
    if live and (len(seeds) != 30 or not config["live_allowed"]):
        raise ValueError("Live targeted execution requires exactly30 prespecified histories and live_allowed")
    if config["formation_rounds"] != 3 or config["profiles"] != PROFILES:
        raise ValueError("Targeted protocol fixes three formation rounds and the Y100/Y011 profiles")
    branches = config["branches"]
    if (len(branches) != 5 or {b.get("id"): b.get("condition") for b in branches} != ARM_CONDITIONS
            or any(set(b) != {"id", "architecture", "condition"} or b["architecture"] != "team" for b in branches)):
        raise ValueError("Exactly the five prespecified Team conditions are required")
    if config["planted_map"] != {"contexts": ["Y"]}:
        raise ValueError("Only the Y best/worst cells may be swapped")
    if config["requested_model"] != "gpt-5.6-luna" or type(config["live_allowed"]) is not bool:
        raise ValueError("Model request must remain gpt-5.6-luna, and live_allowed must be boolean")
    expected = 120 * len(seeds)
    if config["expected_calls"] != expected:
        raise ValueError("Successful path is120 calls per independent history")
    for key, low, high in (("formation_call_cap", 30, 32), ("per_branch_call_cap", 18, 20),
                           ("max_calls", expected, min(3660, expected + 60)),
                           ("max_message_chars", 1, 600), ("max_workers", 1, 2)):
        if type(config[key]) is not int or not low <= config[key] <= high:
            raise ValueError(f"{key} must be an integer in [{low},{high}]")
    if type(config["schedule_seed"]) is not int or not isinstance(config["selection"], dict):
        raise ValueError("Invalid scheduling seed or selection metadata")
    eligible = _preflight_selection(json.dumps(config["selection"], sort_keys=True, separators=(",", ":")))
    if any(seed not in eligible for seed in seeds) or (live and list(eligible) != seeds):
        raise ValueError("Histories differ from the frozen prospective selection")
    return config


def history_config(plan, seed):
    cfg = deepcopy(plan)
    cfg.update(seeds=[seed], expected_calls=120, global_plan_hash=digest(plan),
               global_max_calls=plan["max_calls"], max_calls=plan["formation_call_cap"] + 5 * plan["per_branch_call_cap"])
    return cfg


class TargetedEngine(Engine):
    """One independent formation history; all ten cases are isolated forks."""
    def __init__(self, provider, plan, seed, output_dir, cancel_requested=None):
        validate_plan(plan, live=bool(getattr(provider, "is_live", False)))
        if getattr(provider, "is_live", False) and not isinstance(provider, BudgetedProvider):
            raise ValueError("Live targeted histories require the shared durable global budget wrapper")
        if seed not in plan["seeds"]:
            raise ValueError("History seed is not in the frozen plan")
        base = default_v2_config()
        base.update(seeds=[seed], branches=deepcopy(plan["branches"]), lifecycle="standing",
                    formation_call_cap=plan["formation_call_cap"], per_branch_call_cap=plan["per_branch_call_cap"],
                    max_calls=plan["formation_call_cap"] + 5 * plan["per_branch_call_cap"],
                    max_message_chars=plan["max_message_chars"], live_allowed=plan["live_allowed"])
        super().__init__(provider, base, output_dir, cancel_requested)
        self.plan = deepcopy(plan)
        self.config = history_config(plan, seed)
        self._seed = seed
        self._profile_id = None

    def _record(self, event_type, **fields):
        return super()._record(event_type, diagnostic_profile_id=self._profile_id, **fields)

    def _provider_trace(self):
        trace = super()._provider_trace()
        marker = getattr(self.provider, "last_trace", {}).get("targeted_transport_reserved")
        if marker is not None:
            trace["targeted_transport_reserved"] = bool(marker)
        return trace

    def _payload(self, state, architecture, actor, current, profiles=None):
        payload = super()._payload(state, architecture, actor, current, profiles)
        payload["task"]["truth_process"] = (
            "Formation truths were independent Bernoulli(0.5), with contexts balanced in groups of three. "
            "Diagnostic cases are fixed hypothetical signal profiles with the same Bernoulli(0.5) prior; "
            "there is no outcome feedback or continuing history between diagnostic cases.")
        return payload

    def _profile(self, fork, profile):
        state = fork.clone()
        before = digest(state.to_dict())
        actors = self._role_order
        signals = {a: profile["signals"][a] for a in actors}
        initial, messages, revised = {}, {}, {}
        common = {"round_index": len(state.LE) + 1, "context": profile["context"]}
        for actor in actors:
            current = {**common, "stage": "forecast_initial", "private_signal": signals[actor]}
            initial[actor] = self._call("forecast_initial", self._payload(state, "team", actor, current), PROBABILITY_SCHEMA, state)["probability"]
        for actor in actors:
            current = {**common, "stage": "message", "signals": signals,
                       "own_initial_probability": initial[actor], "communication_scope": "public_same_round"}
            messages[actor] = self._call("message", self._payload(state, "team", actor, current),
                                         message_schema(self.config["max_message_chars"]), state)["message"]
        for actor in actors:
            current = {**common, "stage": "forecast_revision", "signals": signals,
                       "own_initial_probability": initial[actor],
                       "messages": [{"actor": a, "message": messages[a]} for a in actors]}
            revised[actor] = self._call("forecast_revision", self._payload(state, "team", actor, current), PROBABILITY_SCHEMA, state)["probability"]
        after = digest(state.to_dict())
        if before != after or digest(fork.to_dict()) != before:
            raise AssertionError("Diagnostic profile altered its frozen fork")
        probability = mean(revised.values())
        oracle = oracle_probability(profile["context"], profile["signals"])
        result = {"profile_id": profile["id"], "context": profile["context"], "signals": profile["signals"],
                  "actor_forecasts": revised, "probability": probability, "oracle_probability": oracle,
                  "cBR": (probability - oracle) ** 2, "fork_state_hash": before,
                  "state_hash_after": after, "outcome_feedback": False, "writeback": False}
        self._record("profile_completed", **result)
        return result

    def _execute(self, tape, checkpoint, result):
        self._branch = "formation"
        self._role_order = list(list(permutations(SOURCES))[self._seed % 6])
        checkpoint["role_order"] = self._role_order
        state = self._fresh_state()
        for event in tape:
            self._round(state, "team", event, "formation")
            checkpoint["formation"] = state.to_dict()
            self._save_checkpoint()
        reads = self._map_reads(state, "team", "map", 0)
        h0, e0 = median_map(list(reads.values())), evidence_map(state.LE)
        p0 = planted_evidence_map(e0, ["Y"])
        metrics, diagnostic = history_metrics(state.LE), planted_map_diagnostics(e0, p0)
        indexed = {(c["context"], c["source"]): c for c in render_map(e0)["cells"]}
        if (not diagnostic["rendered_nonzero"] or not diagnostic["rendered_mse_strictly_increased"]
                or indexed["Y", "B"]["estimate"] <= indexed["Y", "A"]["estimate"]):
            raise ValueError("Frozen seed fails the prespecified Y manipulation check; do not replace it after responses")
        checkpoint.update(H0=h0, H0_individual_maps=reads, E0=e0, P0=p0,
                          history_metrics=metrics, planted_map_diagnostics=diagnostic)
        result.update(history_metrics=metrics, planted_map_diagnostics=diagnostic)
        self._record("formation_completed", H0=h0, E0=e0, P0=p0, history_metrics=metrics,
                     planted_map_diagnostics=diagnostic)
        forks = {}
        for branch in self.plan["branches"]:
            label = branch["id"]
            forks[label] = self.fork_state(state, h0, e0, "team", branch["condition"])
            checkpoint["forks"][label] = forks[label].to_dict()
            self._map_origins[self._seed, label] = self._initial_provenance(branch["condition"])
            result["branches"][label] = {"condition": branch["condition"], "profiles": [], "complete": False}
        rng = random.Random(f"targeted:{self.plan['schedule_seed']}:{self._seed}")
        profile_order = deepcopy(self.plan["profiles"])
        rng.shuffle(profile_order)
        schedule = []
        for profile in profile_order:
            order = list(forks)
            rng.shuffle(order)
            schedule.append({"profile_id": profile["id"], "branch_order": order})
        checkpoint["schedule"] = schedule
        self._record("execution_schedule", schedule=schedule)
        self._save_checkpoint()
        for entry in schedule:
            profile = next(p for p in self.plan["profiles"] if p["id"] == entry["profile_id"])
            self._profile_id = profile["id"]
            for label in entry["branch_order"]:
                self._branch = label
                branch = result["branches"][label]
                branch["profiles"].append(self._profile(forks[label], profile))
                branch["profiles"].sort(key=lambda row: [p["id"] for p in self.plan["profiles"]].index(row["profile_id"]))
                if len(branch["profiles"]) == 2:
                    branch.update(complete=True, mean_cBR=mean(row["cBR"] for row in branch["profiles"]))
        self._save_checkpoint()

    def run(self):
        if self._used or (self.output_dir.exists() and any(self.output_dir.iterdir())):
            raise FileExistsError("Each history attempt needs a new empty output directory")
        self._used = True
        self.output_dir.mkdir(parents=True, exist_ok=True)
        tape = generate_tape(self._seed, 3, 3)[:3]
        observed = [e.observed_record() for e in tape]
        self._write_json("formation_tape.json", observed)
        self._write_json("profiles.json", self.plan["profiles"])
        checkpoint = {"formation": {}, "forks": {}}
        self._checkpoints = checkpoint
        result = {"seed": self._seed, "status": "running", "branches": {}, "expected_calls": 120,
                  "history_metrics": None, "planted_map_diagnostics": None, "error": None}
        manifest = {"protocol_version": VERSION, "config": self.config, "config_hash": digest(self.config),
                    "status": "running", "seed": self._seed, "started_utc": utc_now(),
                    "expected_successful_calls": 120, "formation_tape_hash": digest(observed),
                    "source_hashes": package_sources(),
                    "provider": {"name": self.provider.name, "requested_model": self.provider.requested_model,
                                 "is_live": self.provider.is_live},
                    "scope": "One distinct formation history; two fixed hypothetical Y profiles per condition. No profile feedback, updates, or live audits."}
        self._write_json("manifest.json", manifest)
        with (self.output_dir / "events.jsonl").open("w", encoding="utf-8") as events, (self.output_dir / "calls.jsonl").open("w", encoding="utf-8") as calls:
            self._events, self._calls_log = events, calls
            try:
                self._save_checkpoint()
                self._execute(tape, checkpoint, result)
                result["status"] = "completed"
            except Exception as error:
                result["status"] = "budget_exhausted" if isinstance(error, BudgetExceeded) else "cancelled" if isinstance(error, RunCancelled) else "error"
                result["error"] = {"type": type(error).__name__, "message": safe_error(error)}
                self._record("run_stopped", status=result["status"], error=result["error"])
            finally:
                if not self._checkpoint_write_failed:
                    try:
                        self._save_checkpoint()
                    except Exception as error:
                        if result["error"] is None:
                            result.update(status="error", error={"type": type(error).__name__, "message": safe_error(error)})
                self._events = self._calls_log = None
        result.update(calls_attempted=self.calls, replayed_calls=self._replayed_calls,
                      physical_dispatches_this_execution=self._physical_calls,
                      attempts_by_branch={branch: count for (seed, branch), count in self._attempts_by_scope.items()},
                      served_model_ids=sorted(self._served_model_ids))
        manifest.update(status=result["status"], ended_utc=utc_now(), calls_attempted=self.calls,
                        error=result["error"], cumulative_physical_attempts_by_branch=deepcopy(getattr(self.provider, "physical", self._physical_by_scope)))
        self._write_json("summary.json", result)
        self._write_json("manifest.json", manifest)
        return result


class BudgetLedger:
    """Single-process thread-safe global reservation ledger persisted BEFORE calls."""
    def __init__(self, plan, path, inherited=None):
        self.plan, self.path, self.lock = deepcopy(plan), Path(path), threading.Lock()
        self.counts = deepcopy(inherited or {})
        allowed = {f"{seed}:{branch}" for seed in plan["seeds"] for branch in ("formation", *ARM_CONDITIONS)}
        if any(k not in allowed or type(v) is not int or v < 0 for k, v in self.counts.items()):
            raise ValueError("Invalid inherited cumulative budget ledger")
        if sum(self.counts.values()) > plan["max_calls"]:
            raise ValueError("Inherited global budget already exceeds its cap")
        for key, value in self.counts.items():
            cap = plan["formation_call_cap"] if key.endswith(":formation") else plan["per_branch_call_cap"]
            if value > cap:
                raise ValueError("Inherited scope budget exceeds its cap")
        self._persist()

    def _persist(self):
        atomic_json(self.path, {"config_hash": digest(self.plan), "attempts_by_scope": self.counts,
                               "total_reserved": sum(self.counts.values()), "planned_calls": self.plan["expected_calls"],
                               "hard_cap": self.plan["max_calls"],
                               "basis": "Conservative cumulative transport reservations including failures; persisted before dispatch."})

    def reserve(self, seed, branch):
        with self.lock:
            if seed not in self.plan["seeds"] or branch not in ("formation", *ARM_CONDITIONS):
                raise ValueError("Unknown budget scope")
            key = f"{seed}:{branch}"
            cap = self.plan["formation_call_cap"] if branch == "formation" else self.plan["per_branch_call_cap"]
            if self.counts.get(key, 0) >= cap or sum(self.counts.values()) >= self.plan["max_calls"]:
                raise BudgetExceeded("Cumulative targeted attempt budget exhausted; no transport dispatch")
            self.counts[key] = self.counts.get(key, 0) + 1
            self._persist()

    def snapshot(self):
        with self.lock:
            return deepcopy(self.counts)


class BudgetedProvider:
    def __init__(self, provider, ledger, stop):
        self.provider, self.ledger, self.stop = provider, ledger, stop
        self.name, self.requested_model, self.is_live = provider.name, provider.requested_model, provider.is_live
        self.call_context, self.last_trace = {}, {}
        self.new_dispatches = 0

    @property
    def physical(self):
        seed = self.call_context.get("seed")
        return {key: value for key, value in self.ledger.snapshot().items() if key.startswith(str(seed) + ":")}

    def complete(self, kind, payload, schema):
        self.last_trace = {"physical_dispatch": False, "targeted_transport_reserved": False}
        if self.stop.is_set():
            raise RunCancelled("Another history stopped; no new targeted calls dispatched")
        self.provider.call_context = self.call_context
        reusing = isinstance(self.provider, PrefixResumeProvider) and self.provider.index < len(self.provider.prefix)
        if not reusing:
            self.ledger.reserve(self.call_context["seed"], self.call_context["branch"])
            self.new_dispatches += 1
        try:
            return self.provider.complete(kind, payload, schema)
        finally:
            self.last_trace = deepcopy(getattr(self.provider, "last_trace", {}))
            self.last_trace["targeted_transport_reserved"] = not reusing
            if not reusing:
                self.last_trace.setdefault("physical_dispatch", bool(self.is_live))
            if not self.is_live:
                self.last_trace["physical_dispatch"] = False


def recorded_reservations(root):
    """Lower bound from all original attempts; resumed responses are not new calls."""
    counts = {}
    for path in sorted(Path(root).glob("histories/*/attempt_*/calls.jsonl")):
        recorded = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("event") not in ("call_response", "call_error"):
                continue
            trace = row.get("provider_trace", {})
            marked = trace.get("targeted_transport_reserved")
            if marked is not None and type(marked) is not bool:
                raise ValueError("Invalid transport reservation marker")
            resumed = trace.get("resumed_from_call_id") is not None or trace.get("source_call_id") is not None
            if resumed and (marked or trace.get("physical_dispatch") is True):
                raise ValueError("Replayed prefix falsely marked as a new transport dispatch")
            if marked or (trace.get("physical_dispatch") is True and not resumed):
                key = f"{row['seed']}:{row['branch']}"
                recorded[row["call_id"]] = key  # Invalid schema can have response AND error.
        for key in recorded.values():
            counts[key] = counts.get(key, 0) + 1
    return counts


def reconcile_ledger(root, plan, saved):
    """Reject any ledger that could restore spent budget after a failure."""
    counts = saved["attempts_by_scope"]
    allowed = {f"{s}:{b}" for s in plan["seeds"] for b in ("formation", *ARM_CONDITIONS)}
    if (saved["config_hash"] != digest(plan) or any(k not in allowed or type(v) is not int or v < 0 for k, v in counts.items())
            or saved["total_reserved"] != sum(counts.values()) or sum(counts.values()) > plan["max_calls"]):
        raise ValueError("Global recovery ledger is invalid")
    for key, value in counts.items():
        cap = plan["formation_call_cap"] if key.endswith(":formation") else plan["per_branch_call_cap"]
        if value > cap:
            raise ValueError("Cumulative scope cap exceeded")
    lower = recorded_reservations(root)
    if any(counts.get(k, 0) < v for k, v in lower.items()):
        raise ValueError("Cumulative ledger is below recorded transport attempts")
    # A crash may occur after reservation and before a trace. Keep that charge.
    for path in Path(root).glob("histories/*/attempt_*/physical_attempts.json"):
        historical = read_json(path).get("attempts_by_branch", {})
        if any(counts.get(k, 0) < v for k, v in historical.items()):
            raise ValueError("Global ledger is below a durable per-history reservation")
    return lower


def _latest_attempt(root, seed):
    folder = root / "histories" / str(seed)
    attempts = sorted(folder.glob("attempt_*")) if folder.exists() else []
    return attempts[-1] if attempts else None


def run_plan(plan, output_dir, provider_factory, workers=1, resume_from=None):
    """No automatic retries. Explicit resume creates a new run root and new attempts."""
    validate_plan(plan)
    if type(workers) is not int or not 1 <= workers <= plan["max_workers"]:
        raise ValueError("Invalid independent-history worker count")
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Targeted output directory must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    inherited, source = {}, Path(resume_from) if resume_from else None
    if source:
        old = read_json(source / "manifest.json")
        if digest(old["config"]) != digest(plan) or old["status"] == "completed":
            raise ValueError("Resume requires an interrupted run with the exact same plan")
        if old["package_sources"] != package_sources():
            raise ValueError("Source changed since the interrupted run; investigate before recovery")
        saved = read_json(source / "physical_attempts.json")
        if saved["config_hash"] != digest(plan):
            raise ValueError("Global recovery ledger does not match the frozen plan")
        reconcile_ledger(source, plan, saved)
        inherited = saved["attempts_by_scope"]
        if (source / "histories").exists():
            shutil.copytree(source / "histories", output / "histories")
    ledger = BudgetLedger(plan, output / "physical_attempts.json", inherited)
    stop = threading.Event()
    manifest = {"protocol_version": VERSION, "config": plan, "config_hash": digest(plan),
                "status": "running", "started_utc": utc_now(), "package_sources": package_sources(),
                "expected_calls": plan["expected_calls"], "hard_call_cap": plan["max_calls"],
                "maximum_extra_attempts": plan["max_calls"] - plan["expected_calls"],
                "workers": workers, "resume_source": source.name if source else None,
                "scope": "Distinct prespecified formation histories, with paired isolated profiles; no automatic retry or replacement histories."}
    result = {"status": "running", "expected_calls": plan["expected_calls"],
              "history_results": {str(s): {"seed": s, "status": "not_started", "branches": {}} for s in plan["seeds"]},
              "history_paths": {}, "error": None}
    atomic_json(output / "manifest.json", manifest)
    atomic_json(output / "summary.json", result)

    def work(seed):
        previous = _latest_attempt(output, seed)
        if previous and (previous / "summary.json").exists():
            old_summary = read_json(previous / "summary.json")
            if old_summary["status"] == "completed":
                return old_summary, previous
        attempts = len(list((output / "histories" / str(seed)).glob("attempt_*"))) if previous else 0
        folder = output / "histories" / str(seed) / f"attempt_{attempts + 1:03d}"
        if stop.is_set():
            return {"seed": seed, "status": "not_started", "branches": {}}, None
        provider = provider_factory()
        if provider.is_live:
            validate_plan(plan, live=True)
            if provider.requested_model != plan["requested_model"]:
                raise ValueError("Live provider would substitute the prespecified requested model")
        if previous:
            provider = PrefixResumeProvider(previous, provider, history_config(plan, seed), output_dir=folder)
        budgeted = BudgetedProvider(provider, ledger, stop)
        summary = TargetedEngine(budgeted, plan, seed, folder, stop.is_set).run()
        if summary["status"] != "completed":
            stop.set()
        return summary, folder

    pending_seeds = iter(plan["seeds"])
    futures = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        try:
            for _ in range(workers):
                seed = next(pending_seeds, None)
                if seed is not None:
                    futures[executor.submit(work, seed)] = seed
            while futures:
                completed, _ = wait(futures, return_when=FIRST_COMPLETED)
                for future in completed:
                    seed = futures.pop(future)
                    try:
                        history, path = future.result()
                    except Exception as error:
                        stop.set()
                        history, path = {"seed": seed, "status": "error", "branches": {},
                                         "error": {"type": type(error).__name__, "message": safe_error(error)}}, None
                    result["history_results"][str(seed)] = history
                    if path:
                        result["history_paths"][str(seed)] = path.relative_to(output).as_posix()
                    atomic_json(output / "summary.json", result)
                    if not stop.is_set():
                        next_seed = next(pending_seeds, None)
                        if next_seed is not None:
                            futures[executor.submit(work, next_seed)] = next_seed
        except KeyboardInterrupt:
            # Set cancellation BEFORE the executor waits for current calls.
            stop.set()
            result["error"] = {"type": "KeyboardInterrupt", "message": "Explicit interruption; no automatic retry"}
        except Exception as error:
            stop.set()
            result["error"] = {"type": type(error).__name__, "message": safe_error(error)}
        finally:
            if result["error"]:
                stop.set()
            # Preserve any worker result completed while cancellation propagated.
            for future, seed in list(futures.items()):
                try:
                    history, path = future.result()
                    result["history_results"][str(seed)] = history
                    if path:
                        result["history_paths"][str(seed)] = path.relative_to(output).as_posix()
                except Exception as error:
                    stop.set()
                    result["history_results"][str(seed)] = {"seed": seed, "status": "error", "branches": {},
                        "error": {"type": type(error).__name__, "message": safe_error(error)}}
    completed_count = sum(r["status"] == "completed" for r in result["history_results"].values())
    result.update(status="completed" if completed_count == len(plan["seeds"]) else "cancelled" if result["error"] else "error",
                  completed_histories=completed_count, planned_histories=len(plan["seeds"]),
                  cumulative_transport_reservations=sum(ledger.snapshot().values()))
    manifest.update(status=result["status"], ended_utc=utc_now(),
                    cumulative_transport_reservations=result["cumulative_transport_reservations"])
    atomic_json(output / "summary.json", result)
    atomic_json(output / "manifest.json", manifest)
    return result


def replay_plan(recording, output_dir):
    recording, output = Path(recording), Path(output_dir)
    manifest, original = read_json(recording / "manifest.json"), read_json(recording / "summary.json")
    plan = validate_plan(manifest["config"])
    if original["status"] != "completed":
        raise ValueError("Exact full replay requires a completed root recording")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Replay output must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    results, paths = {}, {}
    for seed in plan["seeds"]:
        source = recording / original["history_paths"][str(seed)]
        destination = output / "histories" / str(seed) / "attempt_001"
        provider = ReplayProvider(source / "calls.jsonl")
        result = TargetedEngine(provider, plan, seed, destination).run()
        if result["status"] != "completed" or provider.index != 120:
            raise ValueError(f"Exact targeted replay failed for history {seed}: {result.get('error')}")
        results[str(seed)], paths[str(seed)] = result, destination.relative_to(output).as_posix()
    summary = {"status": "completed", "expected_calls": plan["expected_calls"], "history_results": results,
               "history_paths": paths, "physical_dispatches_this_execution": 0}
    atomic_json(output / "summary.json", summary)
    atomic_json(output / "manifest.json", {**manifest, "status": "completed", "replay_only": True, "source_recording": recording.name})
    return summary


def verify_plan(recording):
    """Independent exposure/count/scoring checks plus exact engine reconstruction."""
    root = Path(recording)
    manifest, summary = read_json(root / "manifest.json"), read_json(root / "summary.json")
    plan = validate_plan(manifest["config"])
    failures, checks = [], 0
    def check(name, passed):
        nonlocal checks
        checks += 1
        if not passed:
            failures.append(name)
    check("config_hash", digest(plan) == manifest["config_hash"])
    check("exact_planned_history_set", set(summary["history_results"]) == {str(s) for s in plan["seeds"]})
    complete = manifest["status"] == summary["status"] == "completed"
    if not manifest.get("replay_only"):
        ledger = read_json(root / "physical_attempts.json")
        check("budget_ledger_config", ledger["config_hash"] == digest(plan))
        amounts = ledger["attempts_by_scope"]
        check("global_physical_cap", sum(amounts.values()) <= plan["max_calls"] and sum(amounts.values()) == ledger["total_reserved"])
        for key, count in amounts.items():
            seed, branch = key.split(":", 1)
            check("physical_scope:" + key, int(seed) in plan["seeds"] and branch in ("formation", *ARM_CONDITIONS)
                  and type(count) is int and 0 <= count <= (plan["formation_call_cap"] if branch == "formation" else plan["per_branch_call_cap"]))
        try:
            lower = reconcile_ledger(root, plan, ledger)
            check("ledger_not_below_recorded_attempts", True)
            if complete:
                check("completed_minimum_reservations", sum(amounts.values()) >= plan["expected_calls"])
                check("completed_minimum_recorded_reservations", sum(lower.values()) >= plan["expected_calls"])
                attempts = list(root.glob("histories/*/attempt_*"))
                if len(attempts) == len(plan["seeds"]):
                    check("failure_free_exact_reservations", sum(amounts.values()) == plan["expected_calls"]
                          and amounts == lower)
        except Exception:
            check("ledger_not_below_recorded_attempts", False)
    for seed in plan["seeds"]:
        history = summary["history_results"].get(str(seed))
        if history is None:
            continue
        if history["status"] != "completed":
            check(f"incomplete_not_claimed:{seed}", not complete)
            continue
        path = summary["history_paths"].get(str(seed))
        check(f"history_path:{seed}", isinstance(path, str))
        if not isinstance(path, str):
            continue
        folder = root / path
        cp, tape = read_json(folder / "checkpoint.json"), read_json(folder / "formation_tape.json")
        rows = [json.loads(x) for x in (folder / "calls.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        events = [json.loads(x) for x in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        req = [r for r in rows if r["event"] == "call_request"]
        response = {r["call_id"]: r for r in rows if r["event"] == "call_response"}
        check(f"count120:{seed}", len(req) == len(response) == 120)
        check(f"call_order:{seed}", all(r["event"] == ("call_request" if i % 2 == 0 else "call_response")
              and r["call_id"] == f"call-{i // 2 + 1:06d}" for i, r in enumerate(rows)))
        check(f"call_event_mirror:{seed}", rows == [r for r in events if r["event"].startswith("call_")])
        check(f"formation_length:{seed}", len(tape) == 3 and cp["formation"]["LE"] == tape)
        check(f"seed_tape:{seed}", tape == [e.observed_record() for e in generate_tape(seed, 3, 3)[:3]])
        for branch in ("formation", *ARM_CONDITIONS):
            check(f"logical_count:{seed}:{branch}", sum(r["branch"] == branch for r in req) == (30 if branch == "formation" else 18))
        for request in req:
            ident = f"{seed}:{request['call_id']}"
            answer = response.get(request["call_id"], {}).get("response")
            try:
                validate_response(answer, request["schema"])
                valid = True
            except Exception:
                valid = False
            check("schema:" + ident, valid)
            if request["branch"] != "formation":
                payload = request["payload"]
                fork = cp["forks"][request["branch"]]
                actor = payload["actor"]["id"]
                expected_slots = {"LE": fork["LE"], "LB": fork["LB"], "Pi": fork["Pi"][actor], "H": render_map(fork["H"][actor])}
                check("frozen_profile_exposure:" + ident, payload["slots"] == expected_slots)
                check("no_map_directive:" + ident, "map_instruction" not in payload["task"])
                check("no_profile_feedback:" + ident, payload["current"]["round_index"] == 4 and len(payload["slots"]["LE"]) == 3)
            trace = response.get(request["call_id"], {}).get("provider_trace", {})
            hm = read_json(folder / "manifest.json")
            if hm["provider"]["is_live"]:
                system, user = build_prompt(request["kind"], request["payload"], request["schema"])
                check("actual_prompt:" + ident, trace.get("system_template") == system and trace.get("user_prompt") == user
                      and trace.get("schema_sha256") == digest(request["schema"]))
        check(f"exact_branch_set:{seed}", set(history["branches"]) == set(ARM_CONDITIONS))
        for branch, branch_result in history["branches"].items():
            check(f"two_profiles:{seed}:{branch}", {r["profile_id"] for r in branch_result["profiles"]} == {p["id"] for p in plan["profiles"]})
            scores = []
            for row in branch_result["profiles"]:
                profile = next(p for p in plan["profiles"] if p["id"] == row["profile_id"])
                masses = []
                for truth in (0, 1):
                    mass = .5
                    for source, signal in profile["signals"].items():
                        reliability = REL[profile["context"]][source]
                        mass *= reliability if signal == truth else 1 - reliability
                    masses.append(mass)
                q = masses[1] / sum(masses)
                p = sum(row["actor_forecasts"].values()) / 3
                score = (p - q) ** 2
                scores.append(score)
                check(f"score:{seed}:{branch}:{profile['id']}", set(row["actor_forecasts"]) == set(SOURCES)
                      and abs(p - row["probability"]) < 1e-12 and abs(q - row["oracle_probability"]) < 1e-12
                      and abs(score - row["cBR"]) < 1e-12 and row["signals"] == profile["signals"]
                      and not row["outcome_feedback"] and not row["writeback"]
                      and row["fork_state_hash"] == row["state_hash_after"] == digest(cp["forks"][branch]))
            check(f"mean_score:{seed}:{branch}", abs(mean(scores) - branch_result["mean_cBR"]) < 1e-12)
        try:
            with tempfile.TemporaryDirectory(prefix="rem-targeted-verify-") as temporary:
                provider = ReplayProvider(folder / "calls.jsonl")
                replay = TargetedEngine(provider, plan, seed, Path(temporary) / "replay").run()
                check(f"semantic_replay:{seed}", replay["status"] == "completed" and provider.index == 120)
                check(f"replay_branches:{seed}", replay["branches"] == history["branches"])
                check(f"replay_checkpoint:{seed}", read_json(Path(temporary) / "replay/checkpoint.json") == cp)
        except Exception:
            check(f"semantic_replay:{seed}", False)
    return {"status": "invalid" if failures else "verified_complete" if complete else "incomplete",
            "protocol_version": VERSION, "checks_total": checks, "checks_failed": len(failures), "failures": failures,
            "planned_histories": len(plan["seeds"]), "expected_calls": plan["expected_calls"],
            "scope": "Independent recorded-exposure/count/scoring checks plus shared-engine semantic reconstruction; no model calls or inference."}
