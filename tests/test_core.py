"""Offline invariants of the implemented prototype, not tests of REM hypotheses."""
from copy import deepcopy
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest

from rem_harness.data import (CONTEXTS, SOURCES, REL, generate_tape, oracle_probability,
                              evidence_map, pair_probability_exact, history_metrics)
from rem_harness.engine import Engine
from rem_harness.models import default_config, validate_config, expected_calls, digest, median_map


class FixtureProvider:
    """Test-only responses. No model, SDK, subprocess, or network calls."""
    name = "unittest_fixture"
    requested_model = "none"
    is_live = False

    def __init__(self):
        self.seen = []
        self.last_trace = {}

    def complete(self, kind, payload, schema):
        self.seen.append((kind, deepcopy(payload)))
        actor = payload["actor"]["id"]
        offset = {"A": .01, "B": .02, "C": .03, "S": .02, "N1": .01, "N2": .02, "N3": .03}[actor]
        if kind in ("map", "audit_map"):
            estimate = min(.8, .52 + len(payload["slots"]["LE"])*.01 + offset)
            return {"cells": [{"context": c, "source": s, "estimate": estimate,
                               "lower": estimate-.1, "upper": estimate+.1}
                              for c in CONTEXTS for s in SOURCES]}
        if kind in ("message", "private_memo"):
            return {"message": "ARCHIVED-NOTE-"+str(len(self.seen))}
        h = payload["slots"]["H"]
        estimate = h["cells"][0]["estimate"] if h else None
        probability = .5 if estimate is None else estimate
        if kind == "probe_batch":
            return {"predictions": [{"profile_id": p["profile_id"], "probability": probability}
                                    for p in payload["profiles"]]}
        return {"probability": probability}


class DgpTests(unittest.TestCase):
    def test_deterministic_balance_and_immutable_events(self):
        first = generate_tape(42, 24, 84)
        self.assertEqual(first, generate_tape(42, 24, 84))
        self.assertNotEqual(first, generate_tape(43, 24, 84))
        for start in range(0, len(first), 3):
            self.assertEqual({x.context for x in first[start:start+3]}, set(CONTEXTS))
        for context in CONTEXTS:
            self.assertEqual(sum(e.context == context for e in first[:24]), 8)
            self.assertEqual(sum(e.context == context for e in first[24:]), 28)
        with self.assertRaises(Exception):
            first[0].truth = 1

    def test_oracle_direct_joint_enumeration(self):
        for context in CONTEXTS:
            for bits in product((0, 1), repeat=3):
                signal = dict(zip(SOURCES, bits))
                mass = []
                for y in (0, 1):
                    p = .5
                    for source in SOURCES:
                        r = REL[context][source]
                        p *= r if signal[source] == y else 1-r
                    mass.append(p)
                self.assertAlmostEqual(oracle_probability(context, signal), mass[1]/sum(mass), places=14)
                self.assertAlmostEqual(oracle_probability(context, signal)+oracle_probability(context, {s:1-v for s,v in signal.items()}), 1, places=14)

    def test_ties_exact_and_strict_reversals(self):
        for n in (0, 1, 8, 12, 36):
            for x in range(n+1):
                self.assertEqual(pair_probability_exact(x, x, n), Fraction(1, 2))
        ledger = [{"round_index": i+1, "context": c, "signals": {s: 0 for s in SOURCES}, "truth": 0}
                  for i,c in enumerate(CONTEXTS)]
        metrics = history_metrics(ledger)
        self.assertEqual(metrics["M"], 0)
        self.assertEqual(metrics["strict_reversal_count"], 0)

    def test_M_invariant_under_truth_signal_complement(self):
        ledger = [e.observed_record() for e in generate_tape(67, 24, 84)[:24]]
        flipped = deepcopy(ledger)
        for row in flipped:
            row["truth"] = 1-row["truth"]
            row["signals"] = {s:1-v for s,v in row["signals"].items()}
        self.assertEqual(history_metrics(ledger), history_metrics(flipped))
        self.assertEqual(evidence_map(ledger), evidence_map(flipped))

    def test_beta_map_not_true_reliabilities(self):
        mapping = evidence_map([])
        self.assertEqual(len(mapping["cells"]), 9)
        for cell in mapping["cells"]:
            self.assertEqual(cell["estimate"], .5)
            self.assertAlmostEqual(cell["lower"], .05)
            self.assertAlmostEqual(cell["upper"], .95)


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.tmp.name)/"smoke"
        cls.provider = FixtureProvider()
        cls.engine = Engine(cls.provider, default_config(), cls.folder)
        cls.summary = cls.engine.run()
        cls.cp = json.loads((cls.folder/"checkpoint.json").read_text())
        cls.events = [json.loads(x) for x in (cls.folder/"events.jsonl").read_text().splitlines()]
        cls.seed = cls.cp["seeds"]["20261019"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_full_smoke_count_and_unique_ids(self):
        self.assertEqual(self.summary["status"], "completed", self.summary["error"])
        self.assertEqual(self.summary["calls_attempted"], 342)
        self.assertEqual(expected_calls(default_config()), 342)
        requests = [e for e in self.events if e["event"] == "call_request"]
        self.assertEqual(len({e["call_id"] for e in requests}), 342)
        self.assertEqual(len(self.summary["seed_results"]["20261019"]["branches"]), 10)

    def test_forks_differ_only_H_within_architecture(self):
        forks = self.seed["forks"]
        for architecture in ("team", "solo", "nomessage", "nominal"):
            a,b = deepcopy(forks[architecture+"_H"]),deepcopy(forks[architecture+"_R0"])
            self.assertNotEqual(a.pop("H"), b.pop("H"))
            self.assertEqual(a,b)
        # No Python aliases across different branch maps.
        original = self.seed["formation"]
        self.assertEqual(len(original["LE"]), 3)
        self.assertEqual(len(forks["team_H"]["LE"]), 3)

    def test_persisted_states_follow_published_json_schema(self):
        import jsonschema
        schema=json.loads((Path(__file__).resolve().parents[1]/"schemas"/"state-slots-v1.json").read_text())
        validator=jsonschema.Draft202012Validator(schema)
        validator.validate(self.seed["formation"])
        for state in self.seed["forks"].values():
            validator.validate(state)
        for branch in self.seed["branches"].values():
            validator.validate(branch["state"])

    def test_future_exogenous_equal_but_behavior_can_diverge(self):
        a,b = (self.seed["branches"][x]["state"] for x in ("team_H","team_R0"))
        self.assertEqual(a["LE"],b["LE"])
        self.assertNotEqual(a["LB"],b["LB"])
        self.assertEqual(len(a["LE"]),6)

    def test_no_oracle_future_truth_or_historical_messages_in_payload(self):
        for e in self.events:
            if e["event"] != "call_request":
                continue
            p = e["payload"]
            self.assertNotIn("condition", p)
            self.assertNotIn("branch", p)
            self.assertNotIn("call_id", p)
            self.assertNotIn("truth", p["current"])
            self.assertNotIn("oracle_probability", json.dumps(p))
            self.assertNotIn("ARCHIVED-NOTE", json.dumps(p["slots"]))
            if e["kind"].startswith("forecast_") or e["kind"] in ("message","private_memo"):
                self.assertTrue(all(x["round_index"] < p["current"]["round_index"] for x in p["slots"]["LE"]))
            if e["kind"] in ("message","private_memo"):
                self.assertNotIn("messages",p["current"])
            if e["kind"] == "forecast_initial" and p["actor"]["id"] in SOURCES:
                self.assertNotIn("signals",p["current"])
                self.assertIn("private_signal",p["current"])

    def test_first_postfork_actor_inputs_differ_only_in_map(self):
        for architecture, actor in (("team","A"),("nomessage","A"),("solo","S"),("nominal","N1")):
            inputs=[]
            for condition in ("H","R0"):
                event=next(e for e in self.events if e["event"]=="call_request" and
                           e["branch"]==architecture+"_"+condition and e["kind"]=="forecast_initial" and
                           e["payload"]["actor"]["id"]==actor and e["payload"]["current"]["round_index"]==4)
                payload=deepcopy(event["payload"])
                payload["slots"].pop("H")
                inputs.append(payload)
            self.assertEqual(*inputs)

    def test_private_memos_do_not_cross_actors(self):
        for e in self.events:
            if e["event"] == "call_request" and e["branch"] and e["branch"].startswith(("nomessage_","solo_","nominal_")):
                p=e["payload"]
                self.assertNotEqual(e["kind"],"message")
                self.assertNotIn("messages",p["current"])
                if e["kind"] == "forecast_revision":
                    self.assertIn("own_private_memo",p["current"])

    def test_nominal_isolation_and_founder_provenance(self):
        for e in self.events:
            if e["event"] != "call_request" or not (e["branch"] or "").startswith("nominal_"):
                continue
            p=e["payload"]; actor=p["actor"]["id"]
            self.assertEqual(set(p["slots"]["Pi"]["founder_records"]), set(SOURCES))
            for row in p["slots"]["LB"]:
                if row["origin"] != "formation":
                    self.assertEqual(set(row["forecasts"]),{actor})
                    self.assertNotIn("aggregate_probability",row)
        maps=self.seed["branches"]["nominal_H"]["state"]["H"]
        self.assertNotEqual(maps["N1"],maps["N3"])

    def test_readonly_and_preupdate_checkpoint(self):
        for e in self.events:
            if e["event"] in ("readonly_audit","readonly_probes"):
                self.assertEqual(e["state_hash_before"],e["state_hash_after"])
                self.assertEqual(e["ordering"],"post_feedback_pre_update")
        for branch in self.seed["branches"]:
            ev=[e for e in self.events if e["branch"]==branch]
            audit=next(i for i,e in enumerate(ev) if e["event"]=="readonly_audit")
            probe=next(i for i,e in enumerate(ev) if e["event"]=="readonly_probes")
            update=next(i for i,e in enumerate(ev) if e["event"]=="map_updated")
            self.assertLess(audit,update); self.assertLess(probe,update)

    def test_global_budget_and_no_retry(self):
        cfg=default_config();cfg["max_calls"]=2
        p=FixtureProvider()
        summary=Engine(p,cfg,Path(self.tmp.name)/"budget").run()
        self.assertEqual(summary["status"],"budget_exhausted")
        self.assertEqual(summary["calls_attempted"],2)
        self.assertEqual(len(p.seen),2)

    def test_cancellation_stops_new_calls(self):
        p=FixtureProvider()
        summary=Engine(p,default_config(),Path(self.tmp.name)/"cancel",lambda: len(p.seen)>=2).run()
        self.assertEqual(summary["status"],"cancelled")
        self.assertEqual(len(p.seen),2)

    def test_schema_failure_stops_and_records_response(self):
        class Bad(FixtureProvider):
            def complete(self,*args):
                self.seen.append(args)
                return {"probability":1.1}
        p=Bad();folder=Path(self.tmp.name)/"bad"
        summary=Engine(p,default_config(),folder).run()
        self.assertEqual(summary["status"],"error")
        self.assertEqual(summary["calls_attempted"],1)
        events=[json.loads(x) for x in (folder/"events.jsonl").read_text().splitlines()]
        self.assertTrue(any(e["event"]=="call_response" and e["response"]["probability"]==1.1 for e in events))

    def test_updated_map_consumed_next_round_and_standing_preserved(self):
        cfg=default_config();cfg["post_rounds"]=6;cfg["branches"]=cfg["branches"][:1]
        p=FixtureProvider();out=Path(self.tmp.name)/"update"
        result=Engine(p,cfg,out).run();self.assertEqual(result["status"],"completed")
        initial=[payload for kind,payload in p.seen if kind=="forecast_initial" and payload["actor"]["id"]=="A"]
        h_before=next(x["slots"]["H"] for x in initial if x["current"]["round_index"]==4)
        h_after=next(x["slots"]["H"] for x in initial if x["current"]["round_index"]==7)
        self.assertNotEqual(h_before,h_after)
        cfg["lifecycle"]="standing";p=FixtureProvider();out=Path(self.tmp.name)/"standing"
        result=Engine(p,cfg,out).run();self.assertEqual(result["status"],"completed")
        cp=json.loads((out/"checkpoint.json").read_text())["seeds"]["20261019"]
        self.assertEqual(cp["forks"]["team_H"]["H"],cp["branches"]["team_H"]["state"]["H"])

    def test_default_horizon_safe_and_formal_live_guard(self):
        cfg=default_config()
        self.assertEqual((cfg["formation_rounds"],cfg["post_rounds"]),(3,3))
        self.assertEqual(cfg["purpose"],"smoke_noninferential")
        cfg["purpose"]="formal_candidate_offline";cfg["live_allowed"]=False
        p=FixtureProvider();p.is_live=True
        with self.assertRaises(ValueError):
            Engine(p,cfg,Path(self.tmp.name)/"blocked")
        cfg=default_config();cfg["truth_design"]="balanced_truth_quota"
        with self.assertRaises(ValueError): validate_config(cfg)

    def test_full_24_profiles_use_independent_readonly_calls_offline(self):
        cfg=default_config();cfg["branches"]=[cfg["branches"][4]]
        cfg["probes"].update(mode="single",contexts=["X","Y","Z"])
        p=FixtureProvider();folder=Path(self.tmp.name)/"full-probes"
        summary=Engine(p,cfg,folder).run()
        self.assertEqual(summary["status"],"completed")
        self.assertEqual(summary["calls_attempted"],65)
        probes=[payload for kind,payload in p.seen if kind=="probe"]
        self.assertEqual(len(probes),24)
        self.assertEqual(len({(x["current"]["context"],tuple(x["current"]["signals"].values())) for x in probes}),24)
        self.assertEqual(len({digest(x["slots"]) for x in probes}),1)
        self.assertTrue(all("truth" not in x["current"] for x in probes))

    def test_output_never_overwrites_completed_run(self):
        with self.assertRaises(FileExistsError):
            Engine(FixtureProvider(),default_config(),self.folder).run()


if __name__ == "__main__":
    unittest.main()
