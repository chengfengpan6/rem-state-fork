"""Field-specific replay tolerance and historical non-live API integrity tests."""
from copy import deepcopy
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest

from rem_harness.data import render_map
from rem_harness.models import digest
from rem_harness.providers import build_prompt
from rem_harness.replay_validation import compare, request_state, validate_tolerance
from rem_harness.targeted import replay_plan, run_plan, verify_plan
from test_protocol_v2 import V2FixtureProvider
from test_targeted import make_plan


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, allow_nan=False) + "\n", encoding="utf-8")


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def write_lines(path, rows):
    path.write_text("".join(json.dumps(r, allow_nan=False) + "\n" for r in rows), encoding="utf-8")


class LegacyAPITraceFixture(V2FixtureProvider):
    name = "historical_api_fixture"
    requested_model = "archived-api-model"
    is_live = False  # Reproduce the historical adapter classification error.

    def complete(self, kind, payload, schema):
        answer = super().complete(kind, payload, schema)
        system, user = build_prompt(kind, payload, schema)
        self.last_trace.update(system_template=system, user_prompt=user,
                               schema_sha256=digest(schema), requested_model=self.requested_model,
                               served_model_id="returned-version", model_identity_status="returned_by_provider",
                               raw_response=deepcopy(answer))
        return answer


class ScoreComparisonTests(unittest.TestCase):
    def test_tolerance_is_finite_bounded_nonboolean(self):
        for value in (True, False, -1, float("nan"), float("inf"), 1.0001e-12, "1e-12"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_tolerance(value)
        self.assertEqual(validate_tolerance(0), 0.0)
        self.assertEqual(validate_tolerance(1e-12), 1e-12)

    def test_score_allowance_never_coerces_type_or_nonfinite(self):
        for a, b in ((True, 1), (1, 1.0), (0.0, -0.0), (float("nan"), float("nan")), (float("inf"), float("inf"))):
            self.assertFalse(compare(a, b, scope="score", tolerance=1e-12)["equal"])
        self.assertFalse(compare(.25, .25 + 2e-12, scope="score", tolerance=1e-12)["equal"])

    def test_small_prediction_map_signal_changes_are_never_scores(self):
        pairs = [({"current": {"own_initial_probability": .5}}, {"current": {"own_initial_probability": .5 + 5e-13}}),
                 ({"slots": {"H": {"cells": [{"estimate": .5}]}}}, {"slots": {"H": {"cells": [{"estimate": .5 + 5e-13}]}}}),
                 ({"current": {"private_signal": 1}}, {"current": {"private_signal": True}}),
                 ({"slots": {"LB": [{"forecasts": {"A": .5}}]}}, {"slots": {"LB": [{"forecasts": {"A": .5 + 5e-13}}]}}),
                 ({"slots": {"Pi": {"own_records": [{"probability": .5}]}}}, {"slots": {"Pi": {"own_records": [{"probability": .5 + 5e-13}]}}})]
        for a, b in pairs:
            self.assertFalse(compare(a, b, scope="payload", tolerance=1e-12)["equal"])


class ScoreReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.base = cls.root / "base"
        cls.plan = make_plan()
        cls.summary = run_plan(cls.plan, cls.base, LegacyAPITraceFixture)
        assert cls.summary["status"] == "completed", cls.summary
        cls.seed = str(cls.plan["seeds"][0])
        cls.relative = cls.summary["history_paths"][cls.seed]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def copy(self):
        root = self.root / self._testMethodName
        shutil.copytree(self.base, root)
        return root, root / self.relative

    def mirror(self, folder, rows, refresh_prompts=True):
        by_id = {r["call_id"]: r for r in rows if r["event"] == "call_request"}
        for r in rows:
            if r["event"] == "call_response" and refresh_prompts:
                req = by_id[r["call_id"]]
                system, user = build_prompt(req["kind"], req["payload"], req["schema"])
                r["provider_trace"].update(system_template=system, user_prompt=user, schema_sha256=digest(req["schema"]))
        lookup = {(r["event"], r["call_id"]): r for r in rows}
        events = [lookup[(r["event"], r["call_id"])] if r["event"].startswith("call_") else r for r in lines(folder / "events.jsonl")]
        write_lines(folder / "calls.jsonl", rows)
        write_lines(folder / "events.jsonl", events)

    def mutate_archived_score(self, root, folder):
        cp = read(folder / "checkpoint.json")
        for state in [cp["formation"], *cp["forks"].values()]:
            value = math.nextafter(state["LB"][0]["scores"]["A"], math.inf)
            state["LB"][0]["scores"]["A"] = value
            state["Pi"]["A"]["own_records"][0]["brier"] = value
        write(folder / "checkpoint.json", cp)
        rows = lines(folder / "calls.jsonl")
        for r in rows:
            if r["event"] == "call_request":
                state = request_state(cp, r)
                actor = r["payload"]["actor"]["id"]
                r["payload"]["slots"] = {"LE": state["LE"], "LB": state["LB"], "Pi": state["Pi"][actor], "H": render_map(state["H"][actor])}
                r["state_hash"] = digest(state)
                r["visible_state_hash"] = digest(r["payload"]["slots"])
        self.mirror(folder, rows)
        summary = read(root / "summary.json")
        history = summary["history_results"][self.seed]
        for branch, item in history["branches"].items():
            for row in item["profiles"]:
                row["fork_state_hash"] = row["state_hash_after"] = digest(cp["forks"][branch])
        write(root / "summary.json", summary)
        write(folder / "summary.json", history)

    def test_nonlive_api_prompt_is_checked(self):
        report = verify_plan(self.base)
        self.assertEqual(report["status"], "verified_complete", report)
        self.assertEqual(report["actual_prompt_checks_by_history"][self.seed], 120)
        root, folder = self.copy()
        rows = lines(folder / "calls.jsonl")
        rows[1]["provider_trace"]["user_prompt"] += " altered"
        self.mirror(folder, rows, refresh_prompts=False)
        report = verify_plan(root, float_tolerance=1e-12)
        self.assertEqual(report["status"], "invalid")
        self.assertTrue(any(x.startswith("actual_prompt:") for x in report["failures"]))
        self.assertEqual(report["replay_exactness"], "failed")

    def test_trace_requested_model_cannot_be_imputed(self):
        root, folder = self.copy()
        rows = lines(folder / "calls.jsonl")
        del rows[1]["provider_trace"]["requested_model"]
        self.mirror(folder, rows)
        report = verify_plan(root)
        self.assertEqual(report["status"], "invalid")
        self.assertTrue(any(x.startswith("trace_model_metadata:") for x in report["failures"]))

    def test_historical_returned_metadata_label_requires_returned_id(self):
        root, folder = self.copy()
        rows = lines(folder / "calls.jsonl")
        rows[1]["provider_trace"]["model_identity_status"] = "returned_metadata_not_weight_attestation"
        del rows[1]["provider_trace"]["served_model_id"]
        self.mirror(folder, rows)
        report = verify_plan(root)
        self.assertEqual(report["status"], "invalid")
        self.assertTrue(any(x.startswith("returned_model_present:") for x in report["failures"]))

    def test_ulp_score_difference_accepts_only_explicit_tolerance_and_proves_hashes(self):
        root, folder = self.copy()
        self.mutate_archived_score(root, folder)
        strict = verify_plan(root)
        self.assertEqual(strict["status"], "invalid")
        self.assertEqual(strict["replay_exactness"], "failed")
        tolerant = verify_plan(root, float_tolerance=1e-12)
        self.assertEqual(tolerant["status"], "verified_complete", tolerant)
        self.assertEqual(tolerant["replay_exactness"], "within_score_tolerance")
        receipt = tolerant["replay_by_history"][self.seed]
        self.assertTrue(receipt["score_differences"])
        self.assertTrue(receipt["proven_state_hash_differences"])
        self.assertTrue(all("path" in row for row in receipt["score_differences"]))
        json.dumps(tolerant, allow_nan=False)

    def test_replay_metadata_is_persisted_identically_and_trace_allowance_is_visible(self):
        root, folder = self.copy()
        self.mutate_archived_score(root, folder)
        out = self.root / "replayed-tolerant"
        result = replay_plan(root, out, float_tolerance=1e-12)
        self.assertEqual(result["status"], "completed", result)
        history_path = out / result["history_paths"][self.seed]
        self.assertEqual(result["history_results"][self.seed], read(history_path / "summary.json"))
        self.assertEqual(result["history_results"][self.seed]["replay_validation"], read(history_path / "manifest.json")["replay_validation"])
        responses = [r for r in lines(history_path / "calls.jsonl") if r["event"] == "call_response"]
        self.assertTrue(any(r["provider_trace"].get("replay_score_differences") for r in responses))
        self.assertEqual(verify_plan(out)["status"], "verified_complete")

    def test_failed_replay_never_labels_within_tolerance(self):
        root, folder = self.copy()
        rows = lines(folder / "calls.jsonl")
        request = next(r for r in rows if r["event"] == "call_request" and "own_initial_probability" in r["payload"]["current"])
        request["payload"]["current"]["own_initial_probability"] += 5e-13
        self.mirror(folder, rows)
        out = self.root / "replayed-invalid"
        result = replay_plan(root, out, float_tolerance=1e-12)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["replay_exactness"], "failed")
        local = read(out / result["history_paths"][self.seed] / "summary.json")
        self.assertEqual(local, result["history_results"][self.seed])
        json.dumps(result, allow_nan=False)

    def test_replay_manifest_metadata_corruption_is_rejected(self):
        out = self.root / "replayed-metadata"
        result = replay_plan(self.base, out)
        history = out / result["history_paths"][self.seed]
        manifest = read(history / "manifest.json")
        manifest["replay_validation"]["replay_exactness"] = "within_score_tolerance"
        write(history / "manifest.json", manifest)
        report = verify_plan(out)
        self.assertEqual(report["status"], "invalid")
        self.assertTrue(any(x.startswith("history_replay_metadata:") for x in report["failures"]))

    def test_hash_only_change_has_no_tolerance_escape(self):
        root, folder = self.copy()
        rows = lines(folder / "calls.jsonl")
        rows[0]["state_hash"] = "0" * 64
        self.mirror(folder, rows)
        report = verify_plan(root, float_tolerance=1e-12)
        self.assertEqual(report["status"], "invalid")
        self.assertTrue(any(x.startswith("archived_state_hash:") for x in report["failures"]))


if __name__ == "__main__":
    unittest.main()
