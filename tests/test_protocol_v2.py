"""Protocol-v2 engineering invariants. All responses are offline fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from rem_harness.data import (CONTEXTS, SOURCES, REL, generate_tape, evidence_map,
                              render_map, planted_evidence_map, planted_map_diagnostics)
from rem_harness.engine import Engine
from rem_harness.models import (PROTOCOL_VERSION, PROTOCOL_V2, default_config,
                                default_v2_config, expected_calls, expected_call_breakdown,
                                validate_config, digest, median_map)
from rem_harness.providers import ReplayProvider


class V2FixtureProvider:
    """No model, subprocess, network, or external state. Safe for integration QA."""
    name = "v2_unittest_fixture"
    requested_model = "none"
    is_live = False

    def __init__(self):
        self.seen = []
        self.contexts = []
        self.last_trace = {}
        self.read_counts = {}

    def complete(self, kind, payload, schema):
        self.seen.append((kind, deepcopy(payload)))
        self.contexts.append(deepcopy(getattr(self, "call_context", {})))
        self.last_trace = {"physical_dispatch": False, "served_model_id": None}
        actor = payload["actor"]["id"]
        if kind == "audit_recall":
            return deepcopy(payload["slots"]["H"])
        if kind in ("map", "audit_map"):
            key = (actor, len(payload["slots"]["LE"]), kind,
                   self.contexts[-1].get("branch"))
            index = self.read_counts.get(key, 0)
            self.read_counts[key] = index + 1
            # Distinct repeated readouts exercise the median, not a copy loop.
            offset = {"A": .01, "B": .02, "C": .03, "S": .02,
                      "N1": .01, "N2": .02, "N3": .03}[actor]
            estimate = .52 + len(payload["slots"]["LE"]) * .01 + offset + (0, .04, .02)[index % 3]
            return {"cells": [{"context": c, "source": s, "estimate": estimate,
                               "lower": estimate - .1, "upper": estimate + .1}
                              for c in CONTEXTS for s in SOURCES]}
        if kind in ("message", "private_memo"):
            return {"message": "Current-round evidence only."}
        h = payload["slots"]["H"]
        value = h["cells"][0]["estimate"] if h else None
        probability = .5 if value is None else value
        if kind == "probe_batch":
            return {"predictions": [{"profile_id": p["profile_id"], "probability": probability}
                                    for p in payload["profiles"]]}
        return {"probability": probability}


def diagnostic_config():
    cfg = default_v2_config()
    cfg.update(seeds=[42], post_rounds=1, map_update_interval=1,
               solo_map_readouts=3, nominal_map_readouts=3)
    cfg["branches"] += [
        {"id": "team_P", "architecture": "team", "condition": "P"},
        {"id": "team_R0rep", "architecture": "team", "condition": "R0"}]
    cfg["audit"].update(mode="split", at_fork=True, architectures=["team", "solo", "nomessage"])
    cfg["max_calls"] = 219
    cfg["live_allowed"] = False
    return cfg


class V2DataTests(unittest.TestCase):
    def test_direct_engine_live_entry_cannot_bypass_authorized_branch_cap(self):
        provider = V2FixtureProvider()
        provider.is_live = True  # Constructor check only: complete is never called.
        cfg = diagnostic_config()
        cfg["live_allowed"] = True
        cfg["per_branch_call_cap"] = 21
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "20 attempts per branch"):
                Engine(provider, cfg, directory)
        self.assertEqual(provider.seen, [])

    def test_partial_post_tape_is_exact_prefix_and_v1_stays_strict(self):
        full = generate_tape(42, 3, 3)
        for post in (1, 2):
            self.assertEqual(generate_tape(42, 3, post, allow_partial_post=True), full[:3 + post])
            with self.assertRaises(ValueError):
                generate_tape(42, 3, post)
        with self.assertRaises(ValueError):
            generate_tape(42, 2, 1, allow_partial_post=True)

    def test_planted_swap_moves_all_three_numeric_fields_only_in_selected_contexts(self):
        original = {"cells": [{"context": c, "source": s, "estimate": .5 + i * .01,
                                "lower": .1 + i * .01, "upper": .8 + i * .01}
                               for i, (c, s) in enumerate((c, s) for c in CONTEXTS for s in SOURCES)]}
        saved = deepcopy(original)
        planted = planted_evidence_map(original, ["Y"])
        a = {(c["context"], c["source"]): c for c in original["cells"]}
        b = {(c["context"], c["source"]): c for c in planted["cells"]}
        for field in ("estimate", "lower", "upper"):
            self.assertEqual(b["Y", "A"][field], a["Y", "B"][field])
            self.assertEqual(b["Y", "B"][field], a["Y", "A"][field])
        self.assertEqual(b["Y", "C"], a["Y", "C"])
        self.assertEqual(b["X", "A"], a["X", "A"])
        self.assertEqual(original, saved)

    def test_displayed_nonzero_and_mse_increase_not_assumed(self):
        for seed, nonzero in ((42, True), (20261019, False)):
            e = evidence_map([x.observed_record() for x in generate_tape(seed, 3, 3)[:3]])
            p = planted_evidence_map(e)
            check = planted_map_diagnostics(e, p)
            self.assertEqual(check["rendered_nonzero"], nonzero)
            self.assertEqual(check["rendered_mse_strictly_increased"], nonzero)
            if nonzero:
                self.assertEqual(check["mse_increase_exact"], {"numerator": 119, "denominator": 4500})
                # Reversing an already planted table decreases MSE. No assertion
                # inside the engine may force a positive manipulation result.
                reverse = planted_map_diagnostics(p, planted_evidence_map(p))
                self.assertLess(reverse["rendered_mse_increase"], 0)
                self.assertFalse(reverse["rendered_mse_strictly_increased"])

    def test_rounding_does_not_mutate_research_map(self):
        e = evidence_map([x.observed_record() for x in generate_tape(42, 3, 3)[:3]])
        original = deepcopy(e)
        displayed = render_map(e)
        self.assertEqual(e, original)
        self.assertNotEqual(e, displayed)
        for c in displayed["cells"]:
            for key in ("estimate", "lower", "upper"):
                self.assertEqual(c[key], round(c[key], 2))


class V2EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.tmp.name) / "diagnostic"
        cls.cfg = diagnostic_config()
        cls.provider = V2FixtureProvider()
        cls.summary = Engine(cls.provider, cls.cfg, cls.folder).run()
        assert cls.summary["status"] == "completed", cls.summary
        cls.events = [json.loads(x) for x in (cls.folder / "events.jsonl").read_text().splitlines()]
        cls.requests = [e for e in cls.events if e["event"] == "call_request"]
        cls.cp = json.loads((cls.folder / "checkpoint.json").read_text())["seeds"]["42"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _run(self, cfg, provider=None):
        folder = Path(self.tmp.name) / ("run-" + str(len(list(Path(self.tmp.name).iterdir()))))
        provider = provider or V2FixtureProvider()
        return Engine(provider, cfg, folder).run(), provider, folder

    def test_diagnostic_planned_actual_calls_and_per_branch_caps(self):
        plan = expected_call_breakdown(self.cfg)
        self.assertEqual(plan["total"], 219)
        self.assertEqual(self.summary["calls_attempted"], 219)
        self.assertEqual(plan["formation_per_seed"], 30)
        counts = self.summary["calls_attempted_by_scope"]["42"]
        for branch, cost in plan["branches_per_seed"].items():
            self.assertEqual(counts[branch], cost["total"])
            self.assertLessEqual(counts[branch], 20)
        self.assertEqual(counts["team_E"], 18)
        self.assertEqual(counts["team_R0"], 15)
        self.assertEqual(counts["solo_H"], 12)
        self.assertEqual(counts["nominal_R0"], 18)

    def test_initial_E_P_inputs_differ_only_in_map_and_provenance_is_neutral(self):
        def get(branch):
            return deepcopy(next(r["payload"] for r in self.requests
                                 if r["branch"] == branch and r["kind"] == "forecast_initial"))
        e, p = get("team_E"), get("team_P")
        self.assertNotEqual(e["slots"]["H"], p["slots"]["H"])
        e["slots"]["H"] = p["slots"]["H"] = None
        self.assertEqual(e, p)
        self.assertEqual(self.cp["forks"]["team_E"]["LE"], self.cp["forks"]["team_P"]["LE"])

    def test_R0_replicate_has_identical_initial_payload_and_state(self):
        first = lambda b: next(r["payload"] for r in self.requests if r["branch"] == b and r["kind"] == "forecast_initial")
        self.assertEqual(first("team_R0"), first("team_R0rep"))
        self.assertEqual(self.cp["forks"]["team_R0"], self.cp["forks"]["team_R0rep"])

    def test_map_instruction_only_map_and_audit_stages(self):
        for r in self.requests:
            task = r["payload"]["task"]
            self.assertEqual("map_instruction" in task, r["kind"] in ("map", "audit_map", "audit_recall"))
            for forbidden in ("call_id", "logical_call_id", "condition", "oracle_probability",
                              "schedule", "source_hashes", "planted_map_diagnostics"):
                self.assertNotIn(forbidden, r["payload"])
                self.assertNotIn(forbidden, task)
        self.assertTrue(all(context["logical_call_id"].startswith("call-") for context in self.provider.contexts))

    def test_all_actor_numeric_maps_are_rounded_but_checkpoint_E_is_raw(self):
        for r in self.requests:
            h = r["payload"]["slots"]["H"]
            if h:
                for cell in h["cells"]:
                    for key in ("estimate", "lower", "upper"):
                        if cell[key] is not None:
                            self.assertEqual(cell[key], round(cell[key], 2))
        self.assertNotEqual(self.cp["E0"], render_map(self.cp["E0"]))

    def test_recall_na_omits_calls_and_belief_uses_original_snapshot(self):
        audits = [e for e in self.events if e["event"] == "readonly_audit"]
        self.assertTrue(audits)
        for e in audits:
            self.assertEqual(e["state_hash_before"], e["state_hash_after"])
            branch = e["branch"]
            if branch in ("team_R0", "team_R0rep", "team_RU", "solo_R0", "nomessage_R0"):
                self.assertTrue(all(s == "not_applicable_no_numeric_map" for s in e["recall_status"].values()))
                self.assertFalse(any(r["branch"] == branch and r["kind"] == "audit_recall" for r in self.requests))
            for actor in e["maps"]:
                calls = [r for r in self.requests if r["branch"] == branch and r["payload"]["actor"]["id"] == actor
                         and r["kind"] in ("audit_recall", "audit_map")]
                self.assertEqual(len({r["state_hash"] for r in calls}), 1)
                self.assertEqual(len({r["visible_state_hash"] for r in calls}), 1)
        self.assertFalse(any(e["branch"].startswith("nominal") for e in audits))

    def test_nominal_own_readout_medians_are_not_cross_actor_merge(self):
        e = next(e for e in self.events if e["event"] == "map_updated" and e["branch"] == "nominal_H")
        for actor, reads in e["readout_replicates"].items():
            self.assertEqual(len(reads), 3)
            self.assertEqual(e["H"][actor], median_map(reads))
        self.assertNotEqual(e["H"]["N1"], e["H"]["N3"])
        self.assertIn("no cross-actor merge", e["map_provenance"])

    def test_two_round_interleaving_is_deterministic_and_new_map_consumed(self):
        cfg = default_v2_config()
        cfg.update(seeds=[42], map_update_interval=1, per_branch_call_cap=40)
        cfg["branches"] = [b for b in cfg["branches"] if b["id"] in ("team_H", "team_R0")]
        a, provider, folder = self._run(cfg)
        b, _, second = self._run(cfg)
        self.assertEqual(a["status"], "completed", a["error"])
        ca = json.loads((folder / "checkpoint.json").read_text())
        cb = json.loads((second / "checkpoint.json").read_text())
        self.assertEqual(ca, cb)
        events = [json.loads(x) for x in (folder / "events.jsonl").read_text().splitlines()]
        rounds = [e["post_round"] for e in events if e["event"] == "round_completed" and e["branch"] != "formation"]
        self.assertEqual(rounds, [1, 1, 2, 2])
        update = next(e for e in events if e["event"] == "map_updated" and e["branch"] == "team_H")
        second_call = next(e for e in events if e["event"] == "call_request" and e["branch"] == "team_H"
                           and e["kind"] == "forecast_initial" and e["payload"]["current"]["round_index"] == 5)
        actor = second_call["payload"]["actor"]["id"]
        self.assertEqual(second_call["payload"]["slots"]["H"], render_map(update["H"][actor]))
        self.assertIn("post-feedback", second_call["payload"]["task"]["map_provenance"])
        self.assertNotIn("initial reliability table", second_call["payload"]["task"]["map_provenance"])
        self.assertIn("after_first_update", a["seed_results"]["42"]["windowed_paired_cBR"])

    def test_branch_and_formation_caps_stop_before_extra_dispatch(self):
        for name, capfield, cap, expected in (("formation", "formation_call_cap", 5, 5),
                                             ("branch", "per_branch_call_cap", 2, 32)):
            cfg = default_v2_config()
            cfg["branches"] = [cfg["branches"][0]]
            cfg[capfield] = cap
            summary, provider, _ = self._run(cfg)
            self.assertEqual(summary["status"], "budget_exhausted", name)
            self.assertEqual(summary["calls_attempted"], expected)
            self.assertEqual(len(provider.seen), expected)

    def test_readonly_audit_does_not_accept_provider_writeback(self):
        class MutatingProvider(V2FixtureProvider):
            def complete(self, kind, payload, schema):
                result = super().complete(kind, payload, schema)
                payload["slots"]["LE"].append({"forged": True})
                payload["slots"]["H"] = None
                return result
        cfg = diagnostic_config()
        summary, _, folder = self._run(cfg, MutatingProvider())
        self.assertEqual(summary["status"], "completed", summary["error"])
        checkpoint = json.loads((folder / "checkpoint.json").read_text())
        self.assertEqual(checkpoint["seeds"]["42"], self.cp)

    def test_replay_preserves_all_experimental_results_and_source_hashes_are_recorded(self):
        replay = ReplayProvider(self.folder / "calls.jsonl")
        summary, _, folder = self._run(self.cfg, replay)
        self.assertEqual(summary["status"], "completed", summary["error"])
        self.assertEqual(summary["seed_results"], self.summary["seed_results"])
        self.assertEqual(summary["replayed_calls"], 219)
        self.assertEqual(summary["physical_dispatches_this_execution"], 0)
        self.assertEqual(json.loads((folder / "checkpoint.json").read_text())["seeds"]["42"], self.cp)
        manifest = json.loads((folder / "manifest.json").read_text())
        source = manifest["source_hashes"]
        self.assertEqual(source["combined_sha256"], digest(source["files"]))
        self.assertIn("rem_harness/engine.py", source["files"])
        self.assertFalse(any(":" in key or key.startswith("/") for key in source["files"]))

    def test_default_version_boundary_and_config_validation(self):
        self.assertEqual(default_config()["protocol_version"], PROTOCOL_VERSION)
        self.assertEqual(expected_calls(default_config()), 342)
        cfg = default_v2_config()
        self.assertEqual(cfg["protocol_version"], PROTOCOL_V2)
        self.assertEqual(expected_calls(cfg), 186)
        self.assertEqual(cfg["formation_call_cap"], 30)
        for field, value in (("nominal_map_readouts", 2), ("solo_map_readouts", True),
                             ("formation_call_cap", 0), ("per_branch_call_cap", -1)):
            bad = deepcopy(cfg)
            bad[field] = value
            with self.assertRaises(ValueError):
                validate_config(bad)
        bad = default_config()
        bad["post_rounds"] = 1
        with self.assertRaises(ValueError):
            validate_config(bad)


if __name__ == "__main__":
    unittest.main()
