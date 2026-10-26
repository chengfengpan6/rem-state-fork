"""Auditable state-fork engine. No provider SDK, subprocess, or network here."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from itertools import permutations, product
import json
import hashlib
from pathlib import Path
import platform
import re
import random
from statistics import mean
import time
from typing import Callable, Protocol

from .data import (CONTEXTS, SOURCES, DGP_VERSION, generate_tape, evidence_map,
                   history_metrics, oracle_probability, brier, conditional_brier_regret,
                   render_map, planted_evidence_map, planted_map_diagnostics)
from .models import (State, actor_ids, canonical, digest, median_map, unknown_map,
                     default_config, validate_config, expected_calls, is_v2, expected_call_breakdown)
from .schemas import (MAP_SCHEMA, MAP_RECALL_SCHEMA, PROBABILITY_SCHEMA, message_schema,
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
        self.v2 = is_v2(self.config)
        if getattr(provider, "is_live", False):
            if not self.config["live_allowed"]:
                raise ValueError("This configuration is offline-only")
            if self.config["probes"]["enabled"] and self.config["probes"]["mode"] == "single":
                raise ValueError("Independent full-profile probes are offline-only in this prototype")
            if self.v2:
                if (self.config["purpose"] != "smoke_noninferential"
                        or len(self.config["seeds"]) != 1
                        or self.config["formation_rounds"] > 3
                        or self.config["post_rounds"] > 2
                        or self.config["per_branch_call_cap"] > 20
                        or self.config["formation_call_cap"] > 32
                        or self.config["max_calls"] > 300):
                    raise ValueError("V2 live is bounded to one diagnostic seed, formation<=3, post<=2, "
                                     "20 attempts per branch, 32 formation, and 300 total")
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
        self._attempts_by_scope = {}
        self._map_origins = {}
        self._readout_replicates = {}
        self._served_model_ids = set()
        self._replayed_calls = 0
        self._physical_calls = 0
        self._physical_by_scope = {}

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
        if self.v2:
            scope = (self._seed, self._branch)
            cap = self.config["formation_call_cap"] if self._branch == "formation" else self.config["per_branch_call_cap"]
            used = self._attempts_by_scope.get(scope, 0)
            if used >= cap:
                raise BudgetExceeded(f"Call cap {cap} reached for seed {self._seed}, scope {self._branch}")
            self._attempts_by_scope[scope] = used + 1
        self.calls += 1  # Count an attempt even if provider or parsing fails.
        call_id = f"call-{self.calls:06d}"
        payload = deepcopy(payload)
        # Call IDs are researcher metadata only. Exposing sequential IDs would
        # create a non-map input difference between matched H and R0 branches.
        self._record("call_request", call_id=call_id, kind=kind, payload=payload, schema=schema,
                     state_hash=digest(state.to_dict()), visible_state_hash=digest(payload["slots"]),
                     requested_model=getattr(self.provider, "requested_model", "unspecified"))
        try:
            if self.v2:
                # Research metadata for durable-prefix resume and physical
                # budgets. It is never placed in the actor-visible payload.
                self.provider.call_context = {"seed": self._seed, "branch": self._branch,
                                              "logical_call_id": call_id}
            response = self.provider.complete(kind, deepcopy(payload), deepcopy(schema))
            # Record the provider response before strict validation; never repair it.
            trace = self._provider_trace()
            if self.v2:
                self._account_dispatch(trace)
            self._record("call_response", call_id=call_id, kind=kind, response=response, provider_trace=trace)
            validate_response(response, schema)
        except Exception as error:
            if self.v2 and 'trace' not in locals():
                self._account_dispatch(self._provider_trace())
            self._record("call_error", call_id=call_id, kind=kind,
                         error_type=type(error).__name__, message=safe_error(error), retry=False,
                         provider_trace=self._provider_trace())
            raise
        self._check_cancel()
        return deepcopy(response)

    def _account_dispatch(self, trace):
        if trace.get("resumed_from_call_id") is not None or trace.get("source_call_id") is not None:
            self._replayed_calls += 1
        elif trace.get("physical_dispatch", True):
            self._physical_calls += 1
            key = f"{self._seed}:{self._branch}"
            self._physical_by_scope[key] = self._physical_by_scope.get(key, 0) + 1
        served = trace.get("served_model_id")
        if served:
            self._served_model_ids.add(str(served))

    def _provider_trace(self):
        trace = getattr(self.provider, "last_trace", {}) or {}
        safe_keys = {"system_prompt", "system_template", "user_prompt", "prompt", "raw_response", "parsed_response",
                     "usage", "model", "requested_model", "finish_reason", "backend", "transport", "provider",
                     "cli_version", "auth", "reasoning_effort", "schema_sha256", "elapsed_seconds", "events",
                     "returncode", "transport_note", "replay_index", "source_call_id"}
        if self.v2:
            safe_keys.update({"served_model_id", "model_identity_status", "raw_cli_events_hash",
                              "effective_config", "host_context_scope", "resumed_from_call_id", "resume_source",
                              "physical_dispatch", "cumulative_physical_attempts"})
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
        if self.v2:
            payload["slots"]["H"] = render_map(state.H[actor])
            stage = current["stage"]
            payload["task"].pop("map_instruction")
            if stage in ("map", "audit_map"):
                payload["task"]["map_instruction"] = (
                    "Report your own nine source-reliability estimates and subjective 90% uncertainty intervals "
                    "using the supplied evidence. These are your current estimates, not a transcription request. "
                    "Do not include rankings or instructions.")
            elif stage == "audit_recall":
                payload["task"]["map_instruction"] = (
                    "Transcribe exactly the nine displayed cells from slot H, including the displayed estimates "
                    "and interval endpoints. This is recall of the supplied map, not your own reliability estimate.")
            payload["task"]["map_provenance"] = self._map_origins.get(
                (self._seed, self._branch), "No persistent reliability table is supplied in this call.")
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
        options = {"H": h0, "E": e0, "R0": None, "RU": unknown_map()}
        if self.v2:
            options["P"] = planted_evidence_map(e0, self.config["planted_map"]["contexts"])
        selected = options[condition]
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
        replicates = {}
        for actor in actor_ids(architecture):
            current = {"stage": kind, "round_index": len(state.LE), "post_round": post_round}
            count = self.config.get(architecture + "_map_readouts", 1) if self.v2 else 1
            schema = MAP_RECALL_SCHEMA if kind == "audit_recall" else MAP_SCHEMA
            individual = [self._call(kind, self._payload(frozen, architecture, actor, current), schema, frozen)
                          for _ in range(count)]
            reads[actor] = median_map(individual) if count > 1 else individual[0]
            replicates[actor] = individual
        if self.v2:
            self._readout_replicates = replicates
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
        extra = {}
        if self.v2:
            if architecture == "nominal":
                source = ("each independent actor's own post-feedback elicitation; no cross-actor merge"
                          if self.config["nominal_map_readouts"] == 1 else
                          "a coordinatewise median of three independent post-feedback readouts per actor; no cross-actor merge")
            elif architecture == "solo":
                source = ("the single actor's post-feedback elicitation" if self.config["solo_map_readouts"] == 1
                          else "the coordinatewise median of three independent post-feedback readouts from the single actor")
            else:
                source = "the coordinatewise median of three independent actors' post-feedback elicitations"
            provenance = f"The current reliability table was generated by {source}. It is an elicited estimate, not known truth."
            self._map_origins[self._seed, self._branch] = provenance
            extra = {"readout_replicates": self._readout_replicates, "map_provenance": provenance}
        self._record("map_updated", post_round=post_round, aggregation=rule, individual_maps=reads,
                     H=state.H, state_hash_before=before, state_hash_after=digest(state.to_dict()),
                     ordering="post_feedback_after_readonly_measurement", **extra)

    def audit(self, state, architecture, post_round):
        if self.v2:
            return self._audit_v2(state, architecture, post_round)
        before = digest(state.to_dict())
        reads = self._map_reads(state, architecture, "audit_map", post_round)
        after = digest(state.to_dict())
        if before != after:
            raise AssertionError("Read-only audit altered live state")
        self._record("readonly_audit", post_round=post_round, maps=reads, state_hash_before=before,
                     state_hash_after=after, ordering="post_feedback_pre_update")
        return reads

    def _audit_v2(self, state, architecture, post_round):
        before = digest(state.to_dict())
        mode = self.config["audit"]["mode"]
        if mode == "none" or architecture not in self.config["audit"]["architectures"]:
            return {}
        recall, recall_replicates, recall_status = {}, {}, {}
        if mode == "split":
            frozen = state.clone()
            for actor in actor_ids(architecture):
                visible = render_map(frozen.H[actor])
                numeric = visible is not None and all(
                    cell[key] is not None for cell in visible["cells"] for key in ("estimate", "lower", "upper"))
                if not numeric:
                    recall_status[actor] = "not_applicable_no_numeric_map"
                    recall[actor] = None
                    continue
                current = {"stage": "audit_recall", "round_index": len(frozen.LE), "post_round": post_round}
                count = self.config.get(architecture + "_map_readouts", 1)
                individual = [self._call("audit_recall", self._payload(frozen, architecture, actor, current),
                                         MAP_RECALL_SCHEMA, frozen) for _ in range(count)]
                recall[actor] = median_map(individual) if count > 1 else individual[0]
                recall_replicates[actor] = individual
                recall_status[actor] = "measured"
        # A fresh clone of the ORIGINAL live state: no recall result is an
        # input to the belief elicitation or to any subsequent live call.
        reads = self._map_reads(state.clone(), architecture, "audit_map", post_round)
        after = digest(state.to_dict())
        if before != after:
            raise AssertionError("Read-only audit altered live state")
        self._record("readonly_audit", post_round=post_round, mode=mode, maps=reads,
                     recall_maps=recall, recall_status=recall_status,
                     recall_replicates=recall_replicates, belief_replicates=self._readout_replicates,
                     state_hash_before=before, state_hash_after=after,
                     ordering="post_feedback_pre_update", independent_snapshot_clones=True)
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
        if (not self.v2 or (a["mode"] != "none" and architecture in a["architectures"])) and ((post_round == 0 and a["at_fork"]) or (post_round > 0 and post_round % a["interval"] == 0)):
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
        if self.v2:
            return self._seed_run_v2(seed, tape)
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

    def _initial_provenance(self, condition):
        if condition == "H":
            return ("The initial reliability table is the coordinatewise median of three independent founder-team "
                    "elicitation calls after the common historical task. The same table is supplied to each actor "
                    "in this branch; it is an elicited estimate, not known truth.")
        if condition in ("E", "P"):
            # Matched neutral wording: do not reveal which table was planted.
            return ("The initial reliability table was prepared by the researcher in association with the common "
                    "historical records. It is a reference table and is not guaranteed to be correct.")
        if condition == "RU":
            return "The supplied table has labeled cells but no numeric reliability estimates or intervals."
        return "No persistent reliability table was restored at the fork."

    def _seed_run_v2(self, seed, tape):
        self._seed, self._branch = seed, "formation"
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
        h0, e0 = median_map(list(reads.values())), evidence_map(state.LE)
        p0 = planted_evidence_map(e0, self.config["planted_map"]["contexts"])
        metrics, diagnostics = history_metrics(state.LE), planted_map_diagnostics(e0, p0)
        cp.update(H0=h0, H0_individual_maps=reads, E0=e0, P0=p0,
                  history_metrics=metrics, planted_map_diagnostics=diagnostics)
        result.update(history_metrics=metrics, planted_map_diagnostics=diagnostics)
        self._record("formation_completed", H0=h0, E0=e0, P0=p0, history_metrics=metrics,
                     planted_map_diagnostics=diagnostics,
                     aggregation="coordinatewise_median_of_three_independent_map_calls",
                     subjective_interval_level=.9, implementation_choice=True)
        specs = {spec["id"]: spec for spec in self.config["branches"]}
        branches = {}
        for branch_id, spec in specs.items():
            fork = self.fork_state(state, h0, e0, spec["architecture"], spec["condition"])
            branches[branch_id] = fork
            provenance = self._initial_provenance(spec["condition"])
            self._map_origins[seed, branch_id] = provenance
            cp["forks"][branch_id] = fork.to_dict()
            cp["branches"][branch_id] = {"completed_post_rounds": 0, "state": fork.to_dict(),
                                         "map_provenance": provenance}
            result["branches"][branch_id] = {"architecture": spec["architecture"], "condition": spec["condition"],
                                              "rounds": [], "completed": False}
        # Schedule generation consumes a separate RNG, never the DGP stream.
        # The seed, branch labels, schedule and source hashes are not actor input.
        rng = random.Random(f"rem-schedule:{self.config['schedule']['seed']}:{seed}")
        fork_order = list(specs)
        rng.shuffle(fork_order)
        rounds = []
        for post_round in range(1, self.config["post_rounds"] + 1):
            order = list(specs)
            rng.shuffle(order)
            rounds.append({"post_round": post_round, "branch_order": order})
        schedule = {"mode": "round_interleaved", "fork_order": fork_order, "rounds": rounds}
        cp["schedule"] = schedule
        self._record("execution_schedule", schedule=schedule, schedule_hash=digest(schedule))
        self._save_checkpoint()
        future_hash = digest([e.observed_record() for e in tape[f:]])
        for branch_id in fork_order:
            self._branch = branch_id
            spec, branch = specs[branch_id], branches[branch_id]
            self._record("branch_started", architecture=spec["architecture"], condition=spec["condition"],
                         initial_state_hash=digest(branch.to_dict()), future_tape_hash=future_hash,
                         map_provenance=self._map_origins[seed, branch_id])
            self._measure(branch, spec["architecture"], 0)
        for planned, event in zip(rounds, tape[f:]):
            post_round = planned["post_round"]
            for branch_id in planned["branch_order"]:
                self._branch = branch_id
                spec, branch = specs[branch_id], branches[branch_id]
                architecture = spec["architecture"]
                rows = result["branches"][branch_id]["rounds"]
                rows.append(self._round(branch, architecture, event, "postfork", post_round))
                cp["branches"][branch_id].update(completed_post_rounds=post_round, state=branch.to_dict())
                self._save_checkpoint()
                self._measure(branch, architecture, post_round)
                if self.config["lifecycle"] == "initialized_update" and post_round % self.config["map_update_interval"] == 0:
                    self._update_maps(branch, architecture, post_round)
                    cp["branches"][branch_id].update(state=branch.to_dict(),
                        map_provenance=self._map_origins[seed, branch_id])
                    self._save_checkpoint()
                if post_round == self.config["post_rounds"]:
                    result["branches"][branch_id].update(completed=True, mean_cBR=mean(r["cBR"] for r in rows),
                                                        mean_brier=mean(r["brier"] for r in rows))
                    self._record("branch_completed", final_state_hash=digest(branch.to_dict()), rounds=len(rows))
        self._summarize_v2_contrasts(result)

    def _summarize_v2_contrasts(self, result):
        branches = result["branches"]
        contrasts = (("primary_team_P_minus_E", "team_P", "team_E"),
                     ("secondary_team_H_minus_R0", "team_H", "team_R0"),
                     ("secondary_team_H_minus_E", "team_H", "team_E"),
                     ("secondary_team_RU_minus_R0", "team_RU", "team_R0"),
                     ("diagnostic_team_R0rep_minus_R0", "team_R0rep", "team_R0"))
        result["paired_cBR_differences"] = {
            label: branches[a]["mean_cBR"] - branches[b]["mean_cBR"]
            for label, a, b in contrasts if a in branches and b in branches}
        interval = self.config["map_update_interval"]
        windows = {"whole_trajectory": (1, self.config["post_rounds"])}
        if self.config["lifecycle"] == "initialized_update":
            windows["before_first_update"] = (1, min(interval, self.config["post_rounds"]))
            if self.config["post_rounds"] > interval:
                windows["after_first_update"] = (interval + 1, self.config["post_rounds"])
        result["windowed_paired_cBR"] = {}
        for window, (first, last) in windows.items():
            differences = {}
            for label, a, b in contrasts:
                if a in branches and b in branches:
                    differences[label] = (mean(r["cBR"] for r in branches[a]["rounds"] if first <= r["post_round"] <= last)
                                          - mean(r["cBR"] for r in branches[b]["rounds"] if first <= r["post_round"] <= last))
            result["windowed_paired_cBR"][window] = {"first_post_round": first, "last_post_round": last,
                                                    "differences": differences}

    def _source_hashes(self):
        package = Path(__file__).parent
        files = {f"rem_harness/{p.name}": hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(package.glob("*.py"))}
        return {"files": files, "combined_sha256": digest(files),
                "scope": "Package Python source bytes at run start; configuration has its own canonical hash."}

    def run(self):
        if self._used:
            raise RuntimeError("Engine instances cannot be reused")
        self._used = True
        if self.output_dir.exists() and any(self.output_dir.iterdir()):
            raise FileExistsError("Output directory must be new or empty; existing results are not overwritten")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        cfg = self.config
        tapes = {s: generate_tape(s, cfg["formation_rounds"], cfg["post_rounds"], allow_partial_post=self.v2) for s in cfg["seeds"]}
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
        if self.v2:
            manifest.update(schema_version="manifest-v2", source_hashes=self._source_hashes(),
                            call_plan=expected_call_breakdown(cfg),
                            formation_call_cap_per_seed=cfg["formation_call_cap"],
                            call_cap_per_branch_per_seed=cfg["per_branch_call_cap"],
                            map_display_decimals=2)
            manifest["deviations_and_choices"].extend([
                "V2 allows an engineering prefix within a context block; a short prefix is not context-balanced",
                "P swaps full E0 cells between true best/worst labels in configured contexts; manipulation checks are researcher-only",
                "Only map and audit stages contain map-specific instructions; recall and own estimates use independent clones",
                "Absent and all-null map recall is NA with no dispatch; own-estimate readouts remain applicable",
                "Branch rounds are interleaved in a deterministic randomized schedule using a separate hidden seed",
                "Actor-visible map values have two-decimal numerical precision; research-side source maps retain full precision",
                "Solo/nominal map and audit readouts may be replicated three times per actor; these are not independent actors",
                "Audit architecture subsets are explicit configuration choices, not equivalent measurement coverage"])
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
        if self.v2:
            accounting = {"calls_attempted_by_scope": {
                str(seed): {branch: count for (s, branch), count in self._attempts_by_scope.items() if s == seed}
                for seed in cfg["seeds"]}, "replayed_calls": self._replayed_calls,
                "physical_dispatches_this_execution": self._physical_calls,
                "new_dispatches": getattr(self.provider, "new_dispatches", self._physical_calls),
                "cumulative_physical_attempts_by_branch": deepcopy(getattr(self.provider, "physical", self._physical_by_scope)),
                "served_model_ids": sorted(self._served_model_ids)}
            summary.update(accounting)
            manifest.update(accounting)
        self._write_json("summary.json", summary)
        manifest.update({"status": status, "ended_utc": utc_now(), "calls_attempted": self.calls, "error": error_info})
        self._write_json("manifest.json", manifest)
        return summary
