"""Offline targeted-design invariants; no subprocess or model transport."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from rem_harness.data import render_map
from rem_harness.engine import BudgetExceeded
from rem_harness.models import digest
from rem_harness.targeted import (ARM_CONDITIONS, BudgetLedger, TargetedEngine,
                                  read_json, reconcile_ledger, replay_plan, run_plan,
                                  validate_plan, verify_plan)
from test_protocol_v2 import V2FixtureProvider

ROOT = Path(__file__).resolve().parents[1]


def make_plan(seeds=None):
    config = read_json(ROOT / "configs" / "targeted_30histories.json")
    config["seeds"] = seeds or config["seeds"][:1]
    config["expected_calls"] = 120 * len(config["seeds"])
    config["max_calls"] = config["expected_calls"] + 2 * len(config["seeds"])
    config["live_allowed"] = False
    return config


class FailingFixture(V2FixtureProvider):
    def __init__(self, fail_at):
        super().__init__()
        self.fail_at = fail_at

    def complete(self, kind, payload, schema):
        if len(self.seen) + 1 == self.fail_at:
            self.last_trace = {"physical_dispatch": False}
            raise RuntimeError("Prespecified offline transport failure")
        return super().complete(kind, payload, schema)


class TargetedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="rem-targeted-unit-")
        cls.root = Path(cls.temp.name)
        cls.plan = make_plan()
        cls.provider = V2FixtureProvider()
        cls.recording = cls.root / "complete"
        cls.summary = run_plan(cls.plan, cls.recording, lambda: cls.provider)
        assert cls.summary["status"] == "completed", cls.summary
        cls.seed = cls.plan["seeds"][0]
        cls.history = cls.summary["history_results"][str(cls.seed)]
        cls.folder = cls.recording / cls.summary["history_paths"][str(cls.seed)]
        cls.checkpoint = read_json(cls.folder / "checkpoint.json")
        cls.rows = [json.loads(x) for x in (cls.folder / "calls.jsonl").read_text().splitlines()]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_cost_and_independent_profile_counts(self):
        self.assertEqual(self.history["calls_attempted"], 120)
        self.assertEqual(self.history["attempts_by_branch"], {"formation": 30, **{a: 18 for a in ARM_CONDITIONS}})
        self.assertEqual(self.summary["cumulative_transport_reservations"], 120)
        self.assertEqual(self.history["physical_dispatches_this_execution"], 0)
        self.assertTrue(all(b["complete"] and len(b["profiles"]) == 2 for b in self.history["branches"].values()))

    def test_both_profiles_have_exact_same_fork_exposures_and_no_feedback(self):
        for row in self.rows:
            if row["event"] != "call_request" or row["branch"] == "formation":
                continue
            payload = row["payload"]
            fork = self.checkpoint["forks"][row["branch"]]
            actor = payload["actor"]["id"]
            self.assertEqual(payload["slots"], {"LE": fork["LE"], "LB": fork["LB"],
                "Pi": fork["Pi"][actor], "H": render_map(fork["H"][actor])})
            self.assertEqual(payload["current"]["round_index"], 4)
            self.assertNotIn("condition", payload)
            self.assertNotIn("call_id", payload)
            self.assertNotIn("oracle_probability", payload)
            self.assertNotIn("map_instruction", payload["task"])
            self.assertNotIn("messages", payload["slots"])
            if row["kind"] != "forecast_revision":
                self.assertNotIn("messages", payload["current"])
        for branch in self.history["branches"].values():
            for row in branch["profiles"]:
                self.assertEqual(row["state_hash_after"], row["fork_state_hash"])
                self.assertFalse(row["outcome_feedback"])
                self.assertFalse(row["writeback"])
                self.assertNotIn("truth", row)
                self.assertNotIn("brier", row)

    def test_y_only_complete_cell_swap_and_matched_neutral_provenance(self):
        e = {(c["context"], c["source"]): c for c in self.checkpoint["E0"]["cells"]}
        p = {(c["context"], c["source"]): c for c in self.checkpoint["P0"]["cells"]}
        for field in ("estimate", "lower", "upper"):
            self.assertEqual(p["Y", "A"][field], e["Y", "B"][field])
            self.assertEqual(p["Y", "B"][field], e["Y", "A"][field])
        self.assertEqual({k: v for k, v in p.items() if k[0] != "Y"},
                         {k: v for k, v in e.items() if k[0] != "Y"})
        initial = {row["branch"]: row for row in self.rows if row["event"] == "call_request"
                   and row["kind"] == "forecast_initial" and row["diagnostic_profile_id"] == "Y100"}
        ep, pp = deepcopy(initial["team_E"]["payload"]), deepcopy(initial["team_P"]["payload"])
        ep["slots"].pop("H")
        pp["slots"].pop("H")
        self.assertEqual(ep, pp)
        self.assertEqual(self.checkpoint["forks"]["team_R0"], self.checkpoint["forks"]["team_R0rep"])

    def test_conditional_score_uses_independent_oracle_not_fake_outcome(self):
        for branch in self.history["branches"].values():
            for row in branch["profiles"]:
                q = 21 / 242 if row["profile_id"] == "Y100" else 221 / 242
                self.assertAlmostEqual(row["oracle_probability"], q, places=14)
                self.assertAlmostEqual(row["cBR"], (sum(row["actor_forecasts"].values()) / 3 - q) ** 2, places=14)

    def test_selection_corruption_fails_before_provider_creation(self):
        config = deepcopy(self.plan)
        config["selection"]["candidates"][0]["formation_ledger"][0]["truth"] ^= 1
        creations = []
        with self.assertRaises(ValueError):
            run_plan(config, self.root / "bad_selection", lambda: creations.append(True))
        self.assertEqual(creations, [])

    def test_nonselected_seed_and_small_live_plan_rejected(self):
        config = deepcopy(self.plan)
        config["seeds"] = [20261027]
        with self.assertRaises(ValueError):
            validate_plan(config)
        with self.assertRaises(ValueError):
            validate_plan(self.plan, live=True)

    def test_two_workers_make_distinct_formations_and_preserve_total_budget(self):
        config = make_plan([20261029, 20261030])
        summary = run_plan(config, self.root / "two_histories", V2FixtureProvider, workers=2)
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["cumulative_transport_reservations"], 240)
        tapes = [read_json(self.root / "two_histories" / summary["history_paths"][str(seed)] / "formation_tape.json")
                 for seed in config["seeds"]]
        self.assertNotEqual(tapes[0], tapes[1])

    def test_failed_call_is_charged_no_retry_and_explicit_resume_preserves_old_evidence(self):
        first = self.root / "failed"
        failure = FailingFixture(35)
        result = run_plan(self.plan, first, lambda: failure)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["cumulative_transport_reservations"], 35)
        self.assertEqual(len(failure.seen), 34)
        originals = {p.relative_to(first).as_posix(): p.read_bytes() for p in first.rglob("*") if p.is_file()}
        resumed = run_plan(self.plan, self.root / "resumed", V2FixtureProvider, resume_from=first)
        self.assertEqual(resumed["status"], "completed", resumed)
        self.assertEqual(resumed["cumulative_transport_reservations"], 121)
        self.assertEqual(resumed["history_results"][str(self.seed)]["replayed_calls"], 34)
        self.assertEqual(originals, {p.relative_to(first).as_posix(): p.read_bytes() for p in first.rglob("*") if p.is_file()})
        self.assertEqual(verify_plan(self.root / "resumed")["status"], "verified_complete")

    def test_resume_cannot_restore_spent_budget(self):
        folder = self.root / "underreported"
        run_plan(self.plan, folder, lambda: FailingFixture(35))
        ledger = read_json(folder / "physical_attempts.json")
        ledger.update(attempts_by_scope={}, total_reserved=0)
        (folder / "physical_attempts.json").write_text(json.dumps(ledger), encoding="utf-8")
        created = []
        with self.assertRaisesRegex(ValueError, "below recorded"):
            run_plan(self.plan, self.root / "refused_resume", lambda: created.append(True), resume_from=folder)
        self.assertEqual(created, [])

    def test_budget_reservation_atomic_under_worker_race(self):
        config = deepcopy(self.plan)
        ledger = BudgetLedger(config, self.root / "race_ledger.json")
        def attempt(_):
            try:
                ledger.reserve(self.seed, "team_E")
                return True
            except BudgetExceeded:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, range(30)))
        self.assertEqual(sum(outcomes), 20)
        self.assertEqual(read_json(self.root / "race_ledger.json")["total_reserved"], 20)

    def test_replay_exact_outputs_no_model_or_transport(self):
        replay = replay_plan(self.recording, self.root / "replay")
        self.assertEqual(replay["physical_dispatches_this_execution"], 0)
        history = replay["history_results"][str(self.seed)]
        self.assertEqual(history["branches"], self.history["branches"])
        folder = self.root / "replay" / replay["history_paths"][str(self.seed)]
        self.assertEqual(read_json(folder / "checkpoint.json"), self.checkpoint)
        self.assertEqual(read_json(folder / "formation_tape.json"), read_json(self.folder / "formation_tape.json"))
        self.assertEqual(verify_plan(self.root / "replay")["status"], "verified_complete")

    def test_verification_and_output_exclusivity(self):
        verified = verify_plan(self.recording)
        self.assertEqual(verified["status"], "verified_complete", verified)
        with self.assertRaises(FileExistsError):
            run_plan(self.plan, self.recording, V2FixtureProvider)

    def test_interrupt_sets_stop_before_waiting_for_worker_exit(self):
        import rem_harness.targeted as module
        real_wait = module.wait
        called = []
        def interrupt_once(*args, **kwargs):
            if not called:
                called.append(True)
                raise KeyboardInterrupt()
            return real_wait(*args, **kwargs)
        with patch.object(module, "wait", side_effect=interrupt_once):
            result = run_plan(self.plan, self.root / "interrupted", V2FixtureProvider)
        self.assertEqual(result["status"], "cancelled")
        self.assertLess(result["cumulative_transport_reservations"], 120)


if __name__ == "__main__":
    unittest.main()
