"""Offline diagnostic arithmetic and measurement-boundary regressions."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_protocol_v2 import V2FixtureProvider, diagnostic_config
from test_core import FixtureProvider
from rem_harness.engine import Engine
from rem_harness.models import default_config, default_v2_config

spec = importlib.util.spec_from_file_location("diagnostics", Path(__file__).resolve().parents[1] / "tools/analyze_diagnostics.py")
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


class DiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.recording = cls.root / "v2"
        cls.summary = Engine(V2FixtureProvider(), diagnostic_config(), cls.recording).run()
        assert cls.summary["status"] == "completed", cls.summary
        cls.report = diagnostics.analyze(cls.recording)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_counts_scoring_changed_cells_and_terminal_window(self):
        self.assertEqual(self.report["logical_attempt_count"], 219)
        seed = self.report["seeds"]["42"]
        self.assertEqual(seed["formation_successful_response_count"], 30)
        self.assertEqual(seed["branches"]["team_E"]["response_count"], 18)
        intervention = seed["displayed_E_P_intervention"]
        self.assertEqual(intervention["changed_cells"], ["Y:A", "Y:B"])
        self.assertTrue(intervention["raw_P0_matches_prespecified_full_cell_swap"])
        self.assertAlmostEqual(intervention["rendered_mse_increase"], 119 / 4500)
        tape = json.loads((self.recording / "tapes.json").read_text())["42"]
        self.assertEqual(intervention["future_context_coverage"][0]["has_changed_displayed_cells"], tape[3]["context"] == "Y")
        for branch, output in seed["branches"].items():
            self.assertAlmostEqual(output["mean_cBR"], self.summary["seed_results"]["42"]["branches"][branch]["mean_cBR"])
            self.assertTrue(output["forecast_window_availability"]["terminal_update_only"])
            self.assertEqual(output["forecast_window_availability"]["rounds_after_first_map_update"], 0)
            self.assertEqual(output["rounds"][0]["actor_final_probabilities"],
                             self.summary["seed_results"]["42"]["branches"][branch]["rounds"][0]["actor_forecasts"])

    def test_recall_is_distinct_from_own_estimate_and_R0_is_NA(self):
        audit = self.report["seeds"]["42"]["audits"]
        self.assertEqual(audit["recall"]["responses_with_any_error"], 0)
        self.assertGreater(audit["recall"]["response_count"], 0)
        own_e = next(r for r in audit["own_estimate"]["responses"] if r["branch"] == "team_E")
        self.assertGreater(own_e["own_estimate_deviation_vs_displayed_H"]["mae"], 0)
        own_r0 = next(r for r in audit["own_estimate"]["responses"] if r["branch"] == "team_R0")
        self.assertEqual(own_r0["own_estimate_deviation_vs_displayed_H"]["status"], "not_applicable_no_numeric_reference")
        self.assertIsNone(own_r0["own_estimate_deviation_vs_displayed_H"]["mae"])
        self.assertTrue(any(r["branch"] == "team_R0" for r in audit["recall"]["skipped_not_applicable"]))
        self.assertFalse(any(r["branch"].startswith("nominal") for r in audit["own_estimate"]["responses"]))

    def test_one_changed_recall_field_produces_exact_error_diagnostic(self):
        changed = self.root / "changed-recall"
        shutil.copytree(self.recording, changed)
        rows = [json.loads(x) for x in (changed / "calls.jsonl").read_text().splitlines()]
        request = next(r for r in rows if r["event"] == "call_request" and r["kind"] == "audit_recall")
        response = next(r for r in rows if r["event"] == "call_response" and r["call_id"] == request["call_id"])
        response["response"]["cells"][0]["estimate"] += .01
        (changed / "calls.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        audit = diagnostics.analyze(changed)["seeds"]["42"]["audits"]["recall"]
        self.assertEqual(audit["responses_with_any_error"], 1)
        found = next(r for r in audit["responses"] if r["call_id"] == request["call_id"])
        self.assertEqual(found["recall_error_vs_displayed_H"]["cells_with_any_difference"], 1)
        self.assertAlmostEqual(found["recall_error_vs_displayed_H"]["max_absolute_difference"], .01)
        self.assertAlmostEqual(found["recall_error_vs_displayed_H"]["mae"], .01 / 27)

    def test_one_AA_pair_is_not_variance_and_H_dispersion_is_descriptive(self):
        seed = self.report["seeds"]["42"]
        self.assertEqual(seed["A_A"]["mean_cBR_R0rep_minus_R0"], 0)
        self.assertIsNone(seed["A_A"]["variance_estimate"])
        self.assertEqual(seed["A_A"]["independent_history_count"], 1)
        formation = seed["formation_maps"]
        self.assertTrue(formation["H0_matches_coordinatewise_median"])
        self.assertEqual(formation["E0_estimate_vs_ledger_recalculation"]["max_absolute_difference"], 0)
        self.assertAlmostEqual(formation["cells"][0]["range"], .02)
        self.assertGreater(formation["H0_estimate_vs_known_truth"]["mse"], 0)

    def test_actual_post_update_forecast_is_counted_only_after_consumption(self):
        cfg = default_v2_config()
        cfg.update(seeds=[42], post_rounds=2, map_update_interval=1, per_branch_call_cap=30)
        cfg["branches"] = [cfg["branches"][0]]
        folder = self.root / "two-round"
        summary = Engine(V2FixtureProvider(), cfg, folder).run()
        self.assertEqual(summary["status"], "completed", summary["error"])
        window = diagnostics.analyze(folder)["seeds"]["42"]["branches"]["team_H"]["forecast_window_availability"]
        self.assertEqual(window["rounds_before_any_map_update"], 1)
        self.assertEqual(window["rounds_after_first_map_update"], 1)
        self.assertFalse(window["terminal_update_only"])

    def test_incomplete_recording_is_not_reported_complete(self):
        folder = self.root / "incomplete"
        shutil.copytree(self.recording, folder)
        manifest = json.loads((folder / "manifest.json").read_text())
        manifest["status"] = "running"
        (folder / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "completed recording"):
            diagnostics.analyze(folder)

    def test_declared_seed_flags_actual_X_forecast_with_only_Y_distortion(self):
        cfg = diagnostic_config()
        cfg["seeds"] = [20261026]
        folder = self.root / "declared-seed"
        result = Engine(V2FixtureProvider(), cfg, folder).run()
        self.assertEqual(result["status"], "completed", result["error"])
        report = diagnostics.analyze(folder)
        issue = next(i for i in report["critical_design_limits"] if i["issue"] == "no_within_context_distorted_cell_challenge")
        self.assertEqual(issue["actual_future_contexts"], ["X"])
        self.assertEqual(issue["changed_map_contexts"], ["Y"])
        self.assertFalse(issue["positive_control_sensitivity_certified"])

    def test_optional_baseline_reports_actual_batch_and_ties(self):
        folder = self.root / "baseline"
        result = Engine(FixtureProvider(), default_config(), folder).run()
        self.assertEqual(result["status"], "completed", result["error"])
        baseline = diagnostics.analyze(self.recording, folder)["archived_baseline_comparison"]
        self.assertEqual(baseline["batch_probe_call_count"], 26)
        self.assertEqual(baseline["separate_profile_probe_call_count"], 0)
        self.assertEqual(baseline["profiles_per_batch"], {"8": 26})
        ties = baseline["displayed_map_rank_variation"]["20261019"]["displayed_E_estimate_distinct_values_per_context"]
        self.assertTrue(all(values == [.67] for values in ties.values()))


if __name__ == "__main__":
    unittest.main()
