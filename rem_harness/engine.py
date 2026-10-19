"""Auditable state-fork engine. No provider SDK, subprocess, or network here."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from itertools import permutations, product
import json
from pathlib import Path
import platform
import re
from statistics import mean
import time
from typing import Callable, Protocol

from .data import (CONTEXTS, SOURCES, DGP_VERSION, generate_tape, evidence_map,
                   history_metrics, oracle_probability, brier, conditional_brier_regret)
from .models import (State, actor_ids, canonical, digest, median_map, unknown_map,
                     default_config, validate_config, expected_calls)
from .schemas import (MAP_SCHEMA, PROBABILITY_SCHEMA, message_schema,
                      batch_probe_schema, validate_response)


class Provider(Protocol):
    name: str
    requested_model: str
    is_live: bool

    def complete(self, kind: str, payload: dict, schema: dict) -> dict: ...


class BudgetExceeded(RuntimeError):
    pass


class RunCancelled(RuntimeError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_error(error):
    message = str(error)[:600]
    message = re.sub(r"[A-Za-z]:[\\/][^\s'\"]+", "[local-path]", message)
    message = re.sub(r"(?i)bearer\s+\S+|sk-[A-Za-z0-9_-]+", "[redacted]", message)
    return message


class Engine:
    def __init__(self, provider: Provider, config: dict | None, output_dir: Path | str,
                 cancel_requested: Callable[[], bool] | None = None):
        self.provider = provider
        self.config = deepcopy(validate_config(config if config is not None else default_config()))
        if getattr(provider, "is_live", False):
            if not self.config["live_allowed"]:
                raise ValueError("This configuration is offline-only")
            if self.config["probes"]["enabled"] and self.config["probes"]["mode"] == "single":
                raise ValueError("Independent full-profile probes are offline-only in this prototype")
        self.output_dir = Path(output_dir)
        self.cancel_requested = cancel_requested or (lambda: False)
        self.cancelled = False
        self.calls = 0
        self._event_index = 0
        self._events = None
        self._calls_log = None
        self._seed = None
        self._branch = None
        self._checkpoints = {"schema_version": "state-slots-v1", "seeds": {}}
        self._results = {}
        self._role_order = list(SOURCES)
        self._used = False
        self._checkpoint_write_failed = False

    def cancel(self):
        self.cancelled = True

    def _check_cancel(self):
        if self.cancelled or self.cancel_requested():
            raise RunCancelled("Cancellation requested; no further calls dispatched")

    def _write_json(self, filename, value):
        path = self.output_dir / filename
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        # Windows scanners/readers can briefly deny atomic replacement. Retry
        # only this file operation: five attempts, at most 0.50 seconds of sleep.
        # Never retry serialization, provider calls, or other I/O exceptions.
        for attempt in range(5):
            try:
                temporary.replace(path)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(.05 * (attempt + 1))

    def _record(self, event_type, **fields):
        self._event_index += 1
        record = {"event_index": self._event_index, "timestamp_utc": utc_now(), "event": event_type,
                  "seed": self._seed, "branch": self._branch, **fields}
        if self._events is not None:
            self._events.write(canonical(record) + "\n")
            self._events.flush()
            if event_type.startswith("call_"):
                self._calls_log.write(canonical(record) + "\n")
                self._calls_log.flush()
        return record

    def _call(self, kind, payload, schema, state):
        self._check_cancel()
        if self.calls >= self.config["max_calls"]:
            raise BudgetExceeded(f"Global call cap {self.config['max_calls']} reached")
        self.calls += 1  # Count an attempt even if provider or parsing fails.
        call_id = f"call-{self.calls:06d}"
        payload = deepcopy(payload)
        # Call IDs are researcher metadata only. Exposing sequential IDs would
        # create a non-map input difference between matched H and R0 branches.
        self._record("call_request", call_id=call_id, kind=kind, payload=payload, schema=schema,
                     state_hash=digest(state.to_dict()), visible_state_hash=digest(payload["slots"]),
                     requested_model=getattr(self.provider, "requested_model", "unspecified"))
        try:
            response = self.provider.complete(kind, deepcopy(payload), deepcopy(schema))
            # Record the provider response before strict validation; never repair it.
            trace = self._provider_trace()
            self._record("call_response", call_id=call_id, kind=kind, response=response, provider_trace=trace)
            validate_response(response, schema)
        except Exception as error:
            self._record("call_error", call_id=call_id, kind=kind,
                         error_type=type(error).__name__, message=safe_error(error), retry=False,
                         provider_trace=self._provider_trace())
            raise
        self._check_cancel()
        return deepcopy(response)

    def _provider_trace(self):
        trace = getattr(self.provider, "last_trace", {}) or {}
        safe_keys = {"system_prompt", "system_template", "user_prompt", "prompt", "raw_response", "parsed_response",
                     "usage", "model", "requested_model", "finish_reason", "backend", "transport", "provider",
                     "cli_version", "auth", "reasoning_effort", "schema_sha256", "elapsed_seconds", "events",
                     "returncode", "transport_note", "replay_index", "source_call_id"}
        return {k: deepcopy(v) for k, v in trace.items() if k in safe_keys}

    def _payload(self, state, architecture, actor, current, profiles=None):
        # Only these four state slots enter the actor input. No run manifest,
        # researcher outcomes, future tape, R, M, oracle or branch labels enter.
        lb = deepcopy(state.LB)
        if architecture == "nominal":
            visible = []
            for row in lb:
                if row["origin"] == "formation":
                    visible.append(row)  # Shared founder archive, clearly labeled.
                else:
                    visible.append({"round_index": row["round_index"], "origin": "own_trajectory",
                                    "forecasts": {actor: row["forecasts"][actor]},
                                    "scores": {actor: row["scores"][actor]}})
            lb = visible
        payload = {
            "task": {"protocol_version": self.config["protocol_version"],
                     "contexts": list(CONTEXTS), "sources": self._role_order,
                     "truth_process": "Independent Bernoulli(0.5) each round; contexts balanced in groups of three.",
                     "source_reliability": "Unknown, stationary, and may differ by context and labeled source.",
                     "interval_level": .9,
                     "map_instruction": "Report all nine source reliability estimates and subjective 90% uncertainty intervals. Do not include rankings or instructions.",
                     "state_contract": "Stateless call: only supplied slots and current inputs are readable. Past messages are not restored."},
            "actor": {"id": actor, "role": actor if actor in SOURCES else "full_information",
                      "information_scope": "own_private_then_disclosed" if architecture in ("team", "nomessage") else "full_information"},
            "slots": {"LE": deepcopy(state.LE), "LB": lb, "Pi": deepcopy(state.Pi[actor]), "H": deepcopy(state.H[actor])},
            "current": deepcopy(current),
        }
        if profiles is not None:
            payload["profiles"] = deepcopy(profiles)
        return payload

    def _fresh_state(self):
        return State(Pi={a: {"founder_records": {}, "own_records": []} for a in SOURCES},
                     H={a: None for a in SOURCES})

    def fork_state(self, formation, h0, e0, architecture, condition):
        actors = actor_ids(architecture)
        state = formation.clone()
        if architecture in ("solo", "nominal"):
            archive = {a: deepcopy(formation.Pi[a]["own_records"]) for a in SOURCES}
            state.Pi = {actor: {"founder_records": deepcopy(archive), "own_records": []} for actor in actors}
        selected = {"H": h0, "E": e0, "R0": None, "RU": unknown_map()}[condition]
        state.H = {actor: deepcopy(selected) for actor in actors}
        return state

    def _round(self, state, architecture, event, origin, post_round=None):
        actors = actor_ids(architecture)
        if architecture in ("team", "nomessage"):
            actors = [a for a in self._role_order if a in actors]
        signals = {a: event.signal_dict()[a] for a in self._role_order}
        before_hash = digest(state.to_dict())
        initial = {}
        notes = {}
        revised = {}
        # Synchronous stages: no actor observes another actor's same-stage output.
        for actor in actors:
            current = {"stage": "forecast_initial", "round_index": event.round_index, "context": event.context}
            if architecture in ("team", "nomessage"):
                current["private_signal"] = signals[actor]
            else:
                current["signals"] = signals
            initial[actor] = self._call("forecast_initial", self._payload(state, architecture, actor, current),
                                        PROBABILITY_SCHEMA, state)["probability"]
        for actor in actors:
            kind = "message" if architecture == "team" else "private_memo"
            current = {"stage": kind, "round_index": event.round_index, "context": event.context,
                       "signals": signals, "own_initial_probability": initial[actor],
                       "communication_scope": "public_same_round" if kind == "message" else "private_to_self"}
            notes[actor] = self._call(kind, self._payload(state, architecture, actor, current),
                                      message_schema(self.config["max_message_chars"]), state)["message"]
        for actor in actors:
            current = {"stage": "forecast_revision", "round_index": event.round_index, "context": event.context,
                       "signals": signals, "own_initial_probability": initial[actor]}
            if architecture == "team":
                current["messages"] = [{"actor": a, "message": notes[a]} for a in actors]
            else:
                current["own_private_memo"] = notes[actor]
            revised[actor] = self._call("forecast_revision", self._payload(state, architecture, actor, current),
                                        PROBABILITY_SCHEMA, state)["probability"]
        probability = mean(revised.values())
        scores = {actor: brier(p, event.truth) for actor, p in revised.items()}
        # Truth is disclosed only after ALL forecasts in this round complete.
        state.LE.append(event.observed_record())
        state.LB.append({"round_index": event.round_index, "origin": origin,
                         "forecasts": revised, "scores": scores,
                         "aggregate_probability": probability, "aggregate_brier": brier(probability, event.truth)})
        for actor in actors:
            own = {"round_index": event.round_index, "context": event.context,
                   "initial_probability": initial[actor], "probability": revised[actor],
                   "truth": event.truth, "brier": scores[actor]}
            if architecture in ("team", "nomessage"):
                own["private_signal"] = signals[actor]
            else:
                own["signals"] = deepcopy(signals)
            state.Pi[actor]["own_records"].append(own)
        oracle = oracle_probability(event.context, signals)
        row = {"round_index": event.round_index, "post_round": post_round, "context": event.context,
               "probability": probability, "truth": event.truth,
               "brier": brier(probability, event.truth), "oracle_probability": oracle,
               "cBR": conditional_brier_regret(probability, oracle), "actor_forecasts": revised}
        self._record("round_completed", **row, state_hash_before=before_hash, state_hash_after=digest(state.to_dict()))
        return row

    def _map_reads(self, state, architecture, kind, post_round):
        frozen = state.clone()
        reads = {}
        for actor in actor_ids(architecture):
            current = {"stage": kind, "round_index": len(state.LE), "post_round": post_round}
            reads[actor] = self._call(kind, self._payload(frozen, architecture, actor, current), MAP_SCHEMA, frozen)
        return reads

    def _update_maps(self, state, architecture, post_round):
        before = digest(state.to_dict())
        reads = self._map_reads(state, architecture, "map", post_round)
        if architecture == "nominal":
            state.H = deepcopy(reads)
            rule = "each_independent_solo_own_map"
        else:
            combined = median_map(list(reads.values()))
            state.H = {actor: deepcopy(combined) for actor in actor_ids(architecture)}
            rule = "coordinatewise_median" if len(reads) > 1 else "single_actor_map"
        self._record("map_updated", post_round=post_round, aggregation=rule, individual_maps=reads,
                     H=state.H, state_hash_before=before, state_hash_after=digest(state.to_dict()),
                     ordering="post_feedback_after_readonly_measurement")

    def audit(self, state, architecture, post_round):
        before = digest(state.to_dict())
        reads = self._map_reads(state, architecture, "audit_map", post_round)
        after = digest(state.to_dict())
        if before != after:
            raise AssertionError("Read-only audit altered live state")
        self._record("readonly_audit", post_round=post_round, maps=reads, state_hash_before=before,
                     state_hash_after=after, ordering="post_feedback_pre_update")
        return reads

    def probe(self, state, architecture, post_round):
        before = digest(state.to_dict())
        frozen = state.clone()
        profiles = [{"profile_id": c+":"+"".join(map(str, bits)), "context": c,
                     "signals": dict(zip(SOURCES, bits))}
                    for c in self.config["probes"]["contexts"] for bits in product((0, 1), repeat=3)]
        results = {}
        for actor in actor_ids(architecture):
            current = {"stage": "probe", "round_index": len(state.LE), "post_round": post_round,
                       "measurement_only": True, "outcome_feedback": False}
            if self.config["probes"]["mode"] == "batch":
                schema = batch_probe_schema([p["profile_id"] for p in profiles])
                result = self._call("probe_batch", self._payload(frozen, architecture, actor, current, profiles), schema, frozen)
                results[actor] = result["predictions"]
            else:
                results[actor] = []
                for profile in profiles:
                    p_current = {**current, "context": profile["context"], "signals": profile["signals"]}
                    result = self._call("probe", self._payload(frozen, architecture, actor, p_current), PROBABILITY_SCHEMA, frozen)
                    results[actor].append({"profile_id": profile["profile_id"], **result})
        after = digest(state.to_dict())
        if before != after:
            raise AssertionError("Read-only probes altered live state")
        self._record("readonly_probes", post_round=post_round, mode=self.config["probes"]["mode"],
                     independent_calls=self.config["probes"]["mode"] == "single", predictions=results,
                     state_hash_before=before, state_hash_after=after, ordering="post_feedback_pre_update",
                     inferential_status="diagnostic_only" if self.config["purpose"] == "smoke_noninferential" else "offline_candidate")
        return results

    def _measure(self, state, architecture, post_round):
        a, p = self.config["audit"], self.config["probes"]
        if (post_round == 0 and a["at_fork"]) or (post_round > 0 and post_round % a["interval"] == 0):
            self.audit(state, architecture, post_round)
        if p["enabled"] and ((post_round == 0 and p["at_fork"]) or (post_round > 0 and post_round % p["interval"] == 0)):
            self.probe(state, architecture, post_round)

    def _save_checkpoint(self):
        try:
            self._write_json("checkpoint.json", self._checkpoints)
        except Exception:
            # Do not repeat an exhausted checkpoint write during finalization.
            self._checkpoint_write_failed = True
            raise
        self._checkpoint_write_failed = False

    def _seed_run(self, seed, tape):
        self._seed = seed
        self._branch = "formation"
        self._role_order = list(list(permutations(SOURCES))[seed % 6])
        cp = {"formation": {}, "forks": {}, "branches": {}, "role_order": self._role_order}
        self._checkpoints["seeds"][str(seed)] = cp
        result = {"branches": {}, "history_metrics": None}
        self._results[str(seed)] = result
        state = self._fresh_state()
        f = self.config["formation_rounds"]
        for event in tape[:f]:
            self._round(state, "team", event, "formation")
            cp["formation"] = state.to_dict()
            self._save_checkpoint()
        reads = self._map_reads(state, "team", "map", 0)
        h0 = median_map(list(reads.values()))
        e0 = evidence_map(state.LE)
        metrics = history_metrics(state.LE)
        cp.update({"H0": h0, "H0_individual_maps": reads, "E0": e0, "history_metrics": metrics})
        result["history_metrics"] = metrics
        self._record("formation_completed", H0=h0, E0=e0, history_metrics=metrics,
                     aggregation="coordinatewise_median_of_three_independent_map_calls",
                     subjective_interval_level=.9, implementation_choice=True)
        # Construct every independent branch before executing any of them.
        branches = {}
        for spec in self.config["branches"]:
            fork = self.fork_state(state, h0, e0, spec["architecture"], spec["condition"])
            branches[spec["id"]] = fork
            cp["forks"][spec["id"]] = fork.to_dict()
            cp["branches"][spec["id"]] = {"completed_post_rounds": 0, "state": fork.to_dict()}
        self._save_checkpoint()
        for spec in self.config["branches"]:
            self._branch = spec["id"]
            architecture = spec["architecture"]
            branch = branches[spec["id"]]
            rows = []
            result["branches"][spec["id"]] = {"architecture": architecture, "condition": spec["condition"], "rounds": rows, "completed": False}
            self._record("branch_started", architecture=architecture, condition=spec["condition"],
                         initial_state_hash=digest(branch.to_dict()), future_tape_hash=digest([e.observed_record() for e in tape[f:]]))
            self._measure(branch, architecture, 0)
            for post_round, event in enumerate(tape[f:], 1):
                rows.append(self._round(branch, architecture, event, "postfork", post_round))
                cp["branches"][spec["id"]] = {"completed_post_rounds": post_round, "state": branch.to_dict()}
                self._save_checkpoint()
                # Critical: measurement occurs before shared map aggregation.
                self._measure(branch, architecture, post_round)
                if self.config["lifecycle"] == "initialized_update" and post_round % self.config["map_update_interval"] == 0:
                    self._update_maps(branch, architecture, post_round)
                    cp["branches"][spec["id"]]["state"] = branch.to_dict()
                    self._save_checkpoint()
            result["branches"][spec["id"]].update({"completed": True, "mean_cBR": mean(r["cBR"] for r in rows),
                                                    "mean_brier": mean(r["brier"] for r in rows)})
            self._record("branch_completed", final_state_hash=digest(branch.to_dict()), rounds=len(rows))
        differences = {}
        b = result["branches"]
        for label, positive, reference in (("primary_team_H_minus_R0", "team_H", "team_R0"),
                                            ("secondary_team_H_minus_E", "team_H", "team_E"),
                                            ("secondary_team_RU_minus_R0", "team_RU", "team_R0")):
            if positive in b and reference in b:
                differences[label] = b[positive]["mean_cBR"]-b[reference]["mean_cBR"]
        result["paired_cBR_differences"] = differences

    def run(self):
        if self._used:
            raise RuntimeError("Engine instances cannot be reused")
        self._used = True
        if self.output_dir.exists() and any(self.output_dir.iterdir()):
            raise FileExistsError("Output directory must be new or empty; existing results are not overwritten")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        cfg = self.config
        tapes = {s: generate_tape(s, cfg["formation_rounds"], cfg["post_rounds"]) for s in cfg["seeds"]}
        saved_tapes = {str(s): [e.observed_record() for e in tape] for s, tape in tapes.items()}
        self._write_json("tapes.json", saved_tapes)
        manifest = {"schema_version": "manifest-v1", "protocol_version": cfg["protocol_version"],
                    "config": cfg, "config_hash": digest(cfg), "status": "running", "started_utc": utc_now(),
                    "provider": {"name": getattr(self.provider, "name", type(self.provider).__name__),
                                 "requested_model": getattr(self.provider, "requested_model", "unspecified"),
                                 "is_live": bool(getattr(self.provider, "is_live", False))},
                    "python": platform.python_version(), "dgp_version": DGP_VERSION,
                    "tape_hashes": {s: digest(t) for s, t in saved_tapes.items()},
                    "expected_successful_calls": expected_calls(cfg), "global_call_cap": cfg["max_calls"],
                    "retry_policy": "none; first provider/schema failure stops the run",
                    "scope": "Executable prototype choices; not a frozen or preregistered confirmatory study",
                    "deviations_and_choices": ["IID truth instead of the manuscript's exact truth balancing",
                        "Context-balanced blocks of 3; horizons and interval are configuration-specific",
                        "H0 and shared map updates use coordinatewise median of three independent actor maps",
                        "90% subjective map intervals; E uses equal-tail Beta credible intervals",
                        "Initialized-update is mutable block memory: inherited H remains until first update",
                        "Standing mode retains each fork map unchanged and performs no map updates",
                        "Checkpoint measurements occur post-feedback and before map update",
                        "No-message/solo/nominal use private memos for three-stage compute opportunity",
                        "Nominal members have no access to one another's post-fork behavior or maps",
                        "Solo/nominal founder records are provenance-labeled, not claimed as personal history",
                        "Batch probes are diagnostic and not independent profile interventions",
                        "No fitted w/lambda or confirmatory inference in this implementation"],
                    "files": ["manifest.json", "tapes.json", "events.jsonl", "calls.jsonl", "checkpoint.json", "summary.json"]}
        self._write_json("manifest.json", manifest)
        status, error_info = "completed", None
        with (self.output_dir/"events.jsonl").open("w", encoding="utf-8") as events, (self.output_dir/"calls.jsonl").open("w", encoding="utf-8") as calls:
            self._events, self._calls_log = events, calls
            try:
                self._save_checkpoint()
                self._check_cancel()
                for seed, tape in tapes.items():
                    self._seed_run(seed, tape)
            except Exception as error:
                status = "budget_exhausted" if isinstance(error, BudgetExceeded) else "cancelled" if isinstance(error, RunCancelled) else "error"
                error_info = {"type": type(error).__name__, "message": safe_error(error)}
                self._record("run_stopped", status=status, error=error_info)
            finally:
                try:
                    if not self._checkpoint_write_failed:
                        self._save_checkpoint()
                except Exception as checkpoint_error:
                    details = {"type": type(checkpoint_error).__name__, "message": safe_error(checkpoint_error)}
                    self._record("checkpoint_write_failed", error=details)
                    # Preserve the initiating failure, if one already exists.
                    if error_info is None:
                        status, error_info = "error", details
                        self._record("run_stopped", status=status, error=error_info)
                finally:
                    self._events = self._calls_log = None
        summary = {"status": status, "purpose": cfg["purpose"], "calls_attempted": self.calls,
                   "expected_successful_calls": expected_calls(cfg), "max_calls": cfg["max_calls"],
                   "seed_results": self._results, "error": error_info,
                   "interpretation": "Pipeline verification only; no population inference, causal conclusion, or parameter-recovery claim.",
                   "measurement_policy": "post_feedback_pre_update; disposable clones; no outcome feedback or writeback"}
        self._write_json("summary.json", summary)
        manifest.update({"status": status, "ended_utc": utc_now(), "calls_attempted": self.calls, "error": error_info})
        self._write_json("manifest.json", manifest)
        return summary
