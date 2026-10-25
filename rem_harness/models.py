"""Configuration, JSON state slots, and canonical hashes."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from statistics import median

from .data import CONTEXTS, SOURCES, TRUTH_DESIGN

PROTOCOL_VERSION = "rem-prototype-0.1-iid-initialized-median90"
PROTOCOL_V2 = "rem-prototype-0.2-iid-planted-split-audit"
BRANCHES = [{"id": f"{architecture}_{condition}", "architecture": architecture, "condition": condition}
            for architecture, conditions in [("team", ("H", "R0", "E", "RU")),
                                             ("solo", ("H", "R0")),
                                             ("nomessage", ("H", "R0")),
                                             ("nominal", ("H", "R0"))]
            for condition in conditions]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


@dataclass
class State:
    LE: list = field(default_factory=list)
    LB: list = field(default_factory=list)
    Pi: dict = field(default_factory=dict)
    # H is the map slot keyed by actor. Team/nomessage copies share the same map
    # values; nominal maps can evolve independently, with no cross-actor merge.
    H: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    def clone(self):
        return deepcopy(self)


def actor_ids(architecture):
    return {"team": ["A", "B", "C"], "nomessage": ["A", "B", "C"],
            "solo": ["S"], "nominal": ["N1", "N2", "N3"]}[architecture]


def unknown_map():
    return {"cells": [{"context": c, "source": s, "estimate": None, "lower": None, "upper": None}
                      for c in CONTEXTS for s in SOURCES]}


def median_map(maps):
    """Implementation choice: coordinate-wise median of independent map reads."""
    indexed = [{(v["context"], v["source"]): v for v in m["cells"]} for m in maps]
    return {"cells": [{"context": c, "source": s,
                       **{k: median(v[c, s][k] for v in indexed) for k in ("estimate", "lower", "upper")}}
                      for c in CONTEXTS for s in SOURCES]}


def default_config():
    return {"protocol_version": PROTOCOL_VERSION, "purpose": "smoke_noninferential",
            "seeds": [20261019], "formation_rounds": 3, "post_rounds": 3,
            "truth_design": TRUTH_DESIGN, "context_block": 3,
            "lifecycle": "initialized_update", "map_update_interval": 3,
            "max_message_chars": 600, "branches": deepcopy(BRANCHES),
            "audit": {"at_fork": False, "interval": 3},
            "probes": {"enabled": True, "at_fork": False, "interval": 3,
                       "mode": "batch", "contexts": ["X"]},
            "max_calls": 500, "live_allowed": True}


def is_v2(config):
    return config["protocol_version"] == PROTOCOL_V2


def default_v2_config():
    """Conservative engineering defaults; not a confirmatory protocol."""
    cfg = default_config()
    cfg.update(protocol_version=PROTOCOL_V2, post_rounds=2,
               schedule={"mode": "round_interleaved", "seed": 20261025},
               per_branch_call_cap=20, formation_call_cap=30,
               planted_map={"contexts": list(CONTEXTS)}, solo_map_readouts=1, nominal_map_readouts=1)
    cfg["audit"] = {"mode": "none", "at_fork": False, "interval": 3,
                    "architectures": ["team", "solo", "nomessage", "nominal"]}
    cfg["probes"]["enabled"] = False
    return cfg


def validate_config(config):
    v2 = is_v2(config)
    allowed = set(default_v2_config() if v2 else default_config())
    if set(config) != allowed:
        raise ValueError(f"Configuration fields differ: {sorted(set(config)^allowed)}")
    if config["protocol_version"] not in (PROTOCOL_VERSION, PROTOCOL_V2) or config["truth_design"] != TRUTH_DESIGN:
        raise ValueError("Unsupported protocol or truth design; exact truth quotas are not implemented")
    if config["context_block"] != 3:
        raise ValueError("This version balances contexts in groups of three")
    for key in ("formation_rounds", "post_rounds", "map_update_interval"):
        value = config[key]
        requires_block = not v2 or key == "formation_rounds"
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0 or (requires_block and value % 3):
            raise ValueError(f"{key} must be a positive integer" + (" multiple of 3" if requires_block else ""))
    if not config["seeds"] or len(set(config["seeds"])) != len(config["seeds"]):
        raise ValueError("Seeds must be nonempty and unique")
    if any(isinstance(s, bool) or not isinstance(s, int) for s in config["seeds"]):
        raise ValueError("Seeds must be integers")
    if config["lifecycle"] not in ("initialized_update", "standing"):
        raise ValueError("Unsupported lifecycle")
    if config["purpose"] not in ("smoke_noninferential", "formal_candidate_offline"):
        raise ValueError("Unsupported purpose")
    if config["purpose"] == "formal_candidate_offline" and config["live_allowed"]:
        raise ValueError("Formal candidate configuration cannot authorize live calls")
    for field in ("max_calls", "max_message_chars"):
        if isinstance(config[field], bool) or not isinstance(config[field], int) or config[field] <= 0:
            raise ValueError(f"{field} must be a positive integer")
    if not isinstance(config["live_allowed"], bool):
        raise ValueError("live_allowed must be boolean")
    branches = config["branches"]
    if not branches or len({b["id"] for b in branches}) != len(branches):
        raise ValueError("Branches must be nonempty with unique IDs")
    for branch in branches:
        if set(branch) != {"id", "architecture", "condition"}:
            raise ValueError("Invalid branch fields")
        if branch["architecture"] not in ("team", "solo", "nomessage", "nominal"):
            raise ValueError("Invalid architecture")
        if branch["condition"] not in (("H", "R0", "E", "RU", "P") if v2 else ("H", "R0", "E", "RU")):
            raise ValueError("Invalid map condition")
        if not branch["id"] or not all(c.isalnum() or c in "_-" for c in branch["id"]):
            raise ValueError("Branch IDs must be simple nonempty labels")
    if set(config["audit"]) != ({"at_fork", "interval", "mode", "architectures"} if v2 else {"at_fork", "interval"}):
        raise ValueError("Invalid audit configuration")
    if set(config["probes"]) != {"enabled", "at_fork", "interval", "mode", "contexts"}:
        raise ValueError("Invalid probe configuration")
    for key in ("audit", "probes"):
        interval = config[key]["interval"]
        if isinstance(interval, bool) or not isinstance(interval, int) or interval <= 0:
            raise ValueError("Measurement interval must be a positive integer")
        if not isinstance(config[key]["at_fork"], bool):
            raise ValueError("at_fork must be boolean")
    p = config["probes"]
    if not isinstance(p["enabled"], bool) or p["mode"] not in ("batch", "single"):
        raise ValueError("Invalid probe mode")
    if not p["contexts"] or len(set(p["contexts"])) != len(p["contexts"]) or not set(p["contexts"]) <= set(CONTEXTS):
        raise ValueError("Probe contexts must be unique known contexts")
    if v2:
        if config["audit"]["mode"] not in ("none", "belief", "split"):
            raise ValueError("V2 audit mode must be none, belief, or split")
        schedule = config["schedule"]
        if set(schedule) != {"mode", "seed"} or schedule["mode"] != "round_interleaved":
            raise ValueError("V2 requires a round-interleaved schedule")
        if isinstance(schedule["seed"], bool) or not isinstance(schedule["seed"], int):
            raise ValueError("Schedule seed must be an integer")
        for field in ("per_branch_call_cap", "formation_call_cap"):
            if isinstance(config[field], bool) or not isinstance(config[field], int) or config[field] <= 0:
                raise ValueError(f"{field} must be a positive integer")
        for key in ("solo_map_readouts", "nominal_map_readouts"):
            if type(config[key]) is not int or config[key] not in (1, 3):
                raise ValueError(f"{key} must be 1 or 3 independent reads")
        architectures = config["audit"]["architectures"]
        if (not isinstance(architectures, list) or len(set(architectures)) != len(architectures)
                or not set(architectures) <= {"team", "solo", "nomessage", "nominal"}):
            raise ValueError("Audit architectures must be a unique subset of supported architectures")
        planting = config["planted_map"]
        if (set(planting) != {"contexts"} or not planting["contexts"]
                or len(set(planting["contexts"])) != len(planting["contexts"])
                or not set(planting["contexts"]) <= set(CONTEXTS)):
            raise ValueError("Planted map contexts must be unique known contexts")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text(encoding="utf-8-sig")))


def expected_calls(config):
    """Exact successful-path count, excluding failures (never retried)."""
    if is_v2(config):
        return expected_call_breakdown(config)["total"]
    f, post = config["formation_rounds"], config["post_rounds"]
    cost = f*9 + 3  # Common team history and three independent H0 elicitation calls.
    for branch in config["branches"]:
        a = branch["architecture"]
        n = len(actor_ids(a))
        cost += post*{"team": 9, "nomessage": 9, "solo": 3, "nominal": 9}[a]
        if config["lifecycle"] == "initialized_update":
            cost += (post//config["map_update_interval"])*n
        cost += (int(config["audit"]["at_fork"]) + post//config["audit"]["interval"])*n
        p = config["probes"]
        if p["enabled"]:
            per = 1 if p["mode"] == "batch" else 8*len(p["contexts"])
            cost += (int(p["at_fork"]) + post//p["interval"])*n*per
    return cost*len(config["seeds"])


def expected_call_breakdown(config):
    """V2 logical attempts on the successful path, per seed and per branch.

    A no-map/unknown-map recall is NA and costs zero until a model update has
    supplied numeric cells. Measurements at an update round occur BEFORE it.
    """
    if not is_v2(config):
        raise ValueError("Detailed call planning is available for protocol v2")
    post = config["post_rounds"]
    formation = config["formation_rounds"] * 9 + 3
    branches = {}
    for branch in config["branches"]:
        n = len(actor_ids(branch["architecture"]))
        reps = config.get(branch["architecture"] + "_map_readouts", 1)
        cost = {"forecast_and_memo": post * n * 3, "map_updates": 0,
                "belief_audits": 0, "recall_audits": 0, "probes": 0}
        updating = config["lifecycle"] == "initialized_update"
        update_interval = config["map_update_interval"]
        if updating:
            cost["map_updates"] = (post // update_interval) * n * reps
        audit = config["audit"]
        if audit["mode"] != "none" and branch["architecture"] in audit["architectures"]:
            checkpoints = ([0] if audit["at_fork"] else []) + list(range(audit["interval"], post + 1, audit["interval"]))
            cost["belief_audits"] = len(checkpoints) * n * reps
            if audit["mode"] == "split":
                cost["recall_audits"] = sum(n * reps for r in checkpoints
                    if branch["condition"] in ("H", "E", "P") or (updating and r > update_interval))
        probes = config["probes"]
        if probes["enabled"]:
            per = 1 if probes["mode"] == "batch" else 8 * len(probes["contexts"])
            cost["probes"] = (int(probes["at_fork"]) + post // probes["interval"]) * n * per
        cost["total"] = sum(cost.values())
        branches[branch["id"]] = cost
    per_seed = formation + sum(b["total"] for b in branches.values())
    return {"formation_per_seed": formation, "branches_per_seed": branches,
            "per_seed": per_seed, "total": per_seed * len(config["seeds"]),
            "meaning": "Successful-path logical calls; includes replayed calls, excludes skipped NA recall."}
