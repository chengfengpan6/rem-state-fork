"""Strict structural replay comparison with a small, explicit score allowance.

No tolerance applies to observations, predictions, maps, types, schemas, or
hashes. A caller may separately prove that a changed hash is the digest of a
state whose only accepted differences are the score fields listed here.
"""
from __future__ import annotations

from copy import deepcopy
import math

MAX_SCORE_TOLERANCE = 1e-12


def validate_tolerance(value=0.0):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or not 0 <= value <= MAX_SCORE_TOLERANCE):
        raise ValueError("Score tolerance must be finite, between 0 and 1e-12; booleans are invalid")
    return float(value)


def _state_score(path):
    # Paths below start at an actual state, not an arbitrary similarly named key.
    if len(path) == 4 and path[0] == "LB" and type(path[1]) is int:
        return path[2] == "scores" and path[3] in ("A", "B", "C", "S", "N1", "N2", "N3")
    if len(path) == 3 and path[0] == "LB" and type(path[1]) is int:
        return path[2] == "aggregate_brier"
    if len(path) == 5 and path[0] == "Pi" and path[2] == "own_records":
        return type(path[3]) is int and path[4] == "brier"
    if len(path) == 6 and path[0] == "Pi" and path[2] == "founder_records":
        return type(path[4]) is int and path[5] == "brier"
    return False


def score_path(path, scope):
    if scope == "state":
        return _state_score(path)
    if scope == "payload" and path[:1] == ("slots",):
        p = path[1:]
        # Visible Pi has already been projected to one actor.
        if p[:1] == ("Pi",):
            p = ("Pi", "visible_actor", *p[1:])
        return _state_score(p)
    if scope == "checkpoint":
        if path[:1] == ("formation",):
            return _state_score(path[1:])
        if len(path) > 2 and path[0] == "forks":
            return _state_score(path[2:])
    if scope == "branches":
        return ((len(path) == 2 and path[1] == "mean_cBR") or
                (len(path) == 4 and path[1] == "profiles"
                 and type(path[2]) is int and path[3] == "cBR"))
    return scope == "score" and path == ()


def json_path(path):
    return "$" + "".join(f"[{p}]" if type(p) is int else "." + p for p in path)


def compare(recorded, recomputed, *, tolerance=0.0, scope="strict", prefix=""):
    """Return every mismatch and accepted score difference; never coerce types."""
    tolerance = validate_tolerance(tolerance)
    differences, failures = [], []

    def visit(left, right, path):
        label = prefix + json_path(path)
        if type(left) is not type(right):
            failures.append({"path": label, "reason": "type_mismatch",
                             "recorded_type": type(left).__name__, "recomputed_type": type(right).__name__})
            return
        if isinstance(left, dict):
            if left.keys() != right.keys():
                failures.append({"path": label, "reason": "object_keys_differ"})
            for key in sorted(left.keys() & right.keys()):
                visit(left[key], right[key], (*path, key))
        elif isinstance(left, list):
            if len(left) != len(right):
                failures.append({"path": label, "reason": "list_length_differs"})
            for index, (a, b) in enumerate(zip(left, right)):
                visit(a, b, (*path, index))
        elif type(left) is float:
            if not math.isfinite(left) or not math.isfinite(right):
                failures.append({"path": label, "reason": "nonfinite_number"})
            elif left == right == 0.0 and math.copysign(1.0, left) != math.copysign(1.0, right):
                failures.append({"path": label, "reason": "signed_zero_representation_differs"})
            elif left != right:
                delta = abs(left - right)
                entry = {"path": label, "recorded": left, "recomputed": right, "absolute_difference": delta}
                if tolerance > 0 and score_path(path, scope) and delta <= tolerance:
                    differences.append({**entry, "reason": "bounded_recomputed_score_difference"})
                else:
                    failures.append({**entry, "reason": "score_tolerance_exceeded" if score_path(path, scope) else "exact_value_required"})
        elif left != right:
            failures.append({"path": label, "reason": "exact_value_required"})

    visit(recorded, recomputed, ())
    return {"equal": not failures, "score_differences": differences, "failures": failures}


def request_state(checkpoint, request):
    """Reconstruct archived state without recomputing any platform-dependent score."""
    if request["branch"] != "formation":
        return deepcopy(checkpoint["forks"][request["branch"]])
    state = deepcopy(checkpoint["formation"])
    current = request["payload"]["current"]
    completed = len(state["LE"]) if request["kind"] == "map" else current["round_index"] - 1
    state["LE"] = state["LE"][:completed]
    state["LB"] = state["LB"][:completed]
    for actor in state["Pi"]:
        state["Pi"][actor]["own_records"] = state["Pi"][actor]["own_records"][:completed]
    return state
