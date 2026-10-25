"""Adversarial recording checks; all model responses are offline fixtures.

Mutations update mirrored logs and visible hashes where relevant. This checks
semantic reconstruction rather than relying only on stale-checksum detection.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from rem_harness.models import digest
from rem_harness.providers import build_prompt
from rem_harness.targeted import run_plan, verify_plan
from test_protocol_v2 import V2FixtureProvider


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def write_lines(path, rows):
    Path(path).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


class TracedFixture(V2FixtureProvider):
    def complete(self, kind, payload, schema):
        result = super().complete(kind, payload, schema)
        system, user = build_prompt(kind, payload, schema)
        self.last_trace.update(system_template=system, user_prompt=user, schema_sha256=digest(schema))
        return result


class TargetedVerifierFaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name) / "base"
        cls.plan = read(ROOT / "configs" / "targeted_30histories.json")
        cls.seed = cls.plan["seeds"][0]
        cls.plan.update(seeds=[cls.seed], expected_calls=120, max_calls=122, live_allowed=False)
        result = run_plan(cls.plan, cls.base, TracedFixture, workers=1)
        assert result["status"] == "completed", result
        cls.history_relative = Path(result["history_paths"][str(cls.seed)])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def copy_recording(self):
        destination = Path(self.tmp.name) / self._testMethodName
        shutil.copytree(self.base, destination)
        return destination, destination / self.history_relative

    def assert_invalid(self, folder):
        report = verify_plan(folder)
        self.assertEqual(report["status"], "invalid", report)
        self.assertGreater(report["checks_failed"], 0, report)
        return report

    def mutate_requests(self, history, mutate, fork_hashes=None):
        rows = read_lines(history / "calls.jsonl")
        requests = {}
        for row in rows:
            if row["event"] == "call_request":
                mutate(row)
                row["visible_state_hash"] = digest(row["payload"]["slots"])
                if fork_hashes and row["branch"] in fork_hashes:
                    row["state_hash"] = fork_hashes[row["branch"]]
                requests[row["call_id"]] = row
        for row in rows:
            if row["event"] == "call_response":
                request = requests[row["call_id"]]
                system, user = build_prompt(request["kind"], request["payload"], request["schema"])
                row["provider_trace"].update(system_template=system, user_prompt=user,
                                             schema_sha256=digest(request["schema"]))
        replacements = {(row["event"], row["call_id"]): row for row in rows}
        events = read_lines(history / "events.jsonl")
        events = [deepcopy(replacements[(row["event"], row["call_id"])])
                  if row["event"].startswith("call_") else row for row in events]
        write_lines(history / "calls.jsonl", rows)
        write_lines(history / "events.jsonl", events)

    def test_unmodified_recording_is_verified(self):
        report = verify_plan(self.base)
        self.assertEqual(report["status"], "verified_complete", report)
        self.assertEqual(report["checks_failed"], 0)

    def test_null_H_even_with_recomputed_visible_hash_is_rejected(self):
        folder, history = self.copy_recording()
        def mutate(row):
            if row["branch"] == "team_H":
                row["payload"]["slots"]["H"] = None
        self.mutate_requests(history, mutate)
        report = self.assert_invalid(folder)
        self.assertTrue(any("frozen_profile_exposure" in x or "semantic" in x for x in report["failures"]))

    def test_coordinated_null_H_checkpoint_prompts_and_hashes_rejected(self):
        folder, history = self.copy_recording()
        cp = read(history / "checkpoint.json")
        cp["H0"] = None
        cp["forks"]["team_H"]["H"] = {actor: None for actor in ("A", "B", "C")}
        write(history / "checkpoint.json", cp)
        def mutate(row):
            if row["branch"] == "team_H":
                row["payload"]["slots"]["H"] = None
        self.mutate_requests(history, mutate, {"team_H": digest(cp["forks"]["team_H"])})
        report = self.assert_invalid(folder)
        self.assertTrue(any("semantic" in x or "replay_checkpoint" in x or "expected" in x
                            for x in report["failures"]), report)

    def test_cross_profile_feedback_injection_is_rejected(self):
        folder, history = self.copy_recording()
        def mutate(row):
            if row["branch"] == "team_P" and row.get("diagnostic_profile_id") == "Y011":
                row["payload"]["slots"]["LE"].append(
                    {"round_index": 4, "context": "Y", "signals": {"A": 1, "B": 0, "C": 0}, "truth": 0})
        self.mutate_requests(history, mutate)
        report = self.assert_invalid(folder)
        self.assertTrue(any("no_profile_feedback" in x for x in report["failures"]), report)

    def test_coordinated_wrong_private_record_is_rejected(self):
        folder, history = self.copy_recording()
        cp = read(history / "checkpoint.json")
        cp["forks"]["team_E"]["Pi"]["A"]["own_records"] = []
        write(history / "checkpoint.json", cp)
        def mutate(row):
            if row["branch"] == "team_E" and row["payload"]["actor"]["id"] == "A":
                row["payload"]["slots"]["Pi"] = deepcopy(cp["forks"]["team_E"]["Pi"]["A"])
        self.mutate_requests(history, mutate, {"team_E": digest(cp["forks"]["team_E"])})
        self.assert_invalid(folder)

    def test_P_branch_copied_from_E_is_rejected(self):
        folder, history = self.copy_recording()
        cp = read(history / "checkpoint.json")
        cp["P0"] = deepcopy(cp["E0"])
        cp["forks"]["team_P"] = deepcopy(cp["forks"]["team_E"])
        write(history / "checkpoint.json", cp)
        def mutate(row):
            if row["branch"] == "team_P":
                actor = row["payload"]["actor"]["id"]
                row["payload"]["slots"]["H"] = deepcopy(cp["forks"]["team_E"]["H"][actor])
                for cell in row["payload"]["slots"]["H"]["cells"]:
                    for key in ("estimate", "lower", "upper"):
                        cell[key] = round(cell[key], 2)
        self.mutate_requests(history, mutate, {"team_P": digest(cp["forks"]["team_P"])})
        self.assert_invalid(folder)

    def test_missing_planned_history_is_invalid_not_certified_or_crash(self):
        folder, _ = self.copy_recording()
        summary = read(folder / "summary.json")
        del summary["history_results"][str(self.seed)]
        write(folder / "summary.json", summary)
        self.assert_invalid(folder)

    def test_corrupted_score_is_rejected(self):
        folder, history = self.copy_recording()
        summary = read(folder / "summary.json")
        summary["history_results"][str(self.seed)]["branches"]["team_P"]["profiles"][0]["cBR"] += .01
        write(folder / "summary.json", summary)
        local = read(history / "summary.json")
        local["branches"]["team_P"]["profiles"][0]["cBR"] += .01
        write(history / "summary.json", local)
        report = self.assert_invalid(folder)
        self.assertTrue(any(x.startswith("score:") for x in report["failures"]), report)

    def test_erased_attempt_ledger_is_rejected(self):
        folder, _ = self.copy_recording()
        ledger = read(folder / "physical_attempts.json")
        ledger["attempts_by_scope"] = {}
        ledger["total_reserved"] = 0
        write(folder / "physical_attempts.json", ledger)
        self.assert_invalid(folder)


if __name__ == "__main__":
    unittest.main()
