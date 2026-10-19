"""Full 342-response offline replay and recording-integrity regressions."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

from rem_harness.engine import Engine
from rem_harness.models import default_config
from rem_harness.providers import ReplayProvider

# Reuse the test-only fixture; no live provider is constructed by these tests.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_core import FixtureProvider

spec=importlib.util.spec_from_file_location("recording_verifier",Path(__file__).resolve().parents[1]/"tools"/"verify_recording.py")
verifier=importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.recording=Path(cls.tmp.name)/"original"
        cls.original=Engine(FixtureProvider(),default_config(),cls.recording).run()
        assert cls.original["status"]=="completed"

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_complete_342_replay_identical_summary_and_checkpoint(self):
        provider=ReplayProvider(self.recording/"calls.jsonl")
        output=Path(self.tmp.name)/"replayed"
        replay=Engine(provider,default_config(),output).run()
        self.assertEqual(replay["status"],"completed",replay["error"])
        self.assertEqual(provider.index,342)
        # Summary contains no provider identity/time; full semantic equality is
        # stronger than comparing only the aggregate final score.
        self.assertEqual(self.original,replay)
        a=json.loads((self.recording/"checkpoint.json").read_text())
        b=json.loads((output/"checkpoint.json").read_text())
        self.assertEqual(a,b)
        check=verifier.verify(output)
        self.assertEqual(check["status"],"verified_complete",check.get("failures"))

    def _corrupted(self,name,mutate):
        rows=[json.loads(x) for x in (self.recording/"calls.jsonl").read_text().splitlines()]
        mutate(rows)
        path=Path(self.tmp.name)/(name+".jsonl")
        path.write_text("\n".join(json.dumps(x) for x in rows)+"\n",encoding="utf-8")
        return path

    def test_missing_response_rejected_at_construction(self):
        path=self._corrupted("missing",lambda rows: rows.pop())
        with self.assertRaises(ValueError):ReplayProvider(path)

    def test_mismatched_call_id_rejected_at_construction(self):
        path=self._corrupted("bad-id",lambda rows: rows[1].update(call_id="call-999999"))
        with self.assertRaises(ValueError):ReplayProvider(path)

    def test_changed_request_rejected_without_approximation(self):
        def mutate(rows):rows[0]["payload"]["current"]["private_signal"] ^= 1
        provider=ReplayProvider(self._corrupted("changed-request",mutate))
        result=Engine(provider,default_config(),Path(self.tmp.name)/"bad-request-replay").run()
        self.assertEqual(result["status"],"error")
        self.assertEqual(result["calls_attempted"],1)
        self.assertEqual(provider.index,0)
        self.assertIn("Replay request mismatch",result["error"]["message"])

    def test_changed_response_changes_state_and_replay_stops(self):
        def mutate(rows):rows[1]["response"]["probability"] = .51
        provider=ReplayProvider(self._corrupted("changed-response",mutate))
        result=Engine(provider,default_config(),Path(self.tmp.name)/"bad-response-replay").run()
        self.assertEqual(result["status"],"error")
        self.assertLess(result["calls_attempted"],342)
        self.assertIn("Replay request mismatch",result["error"]["message"])

    def test_completed_original_passes_independent_verifier(self):
        check=verifier.verify(self.recording)
        self.assertEqual(check["status"],"verified_complete",check.get("failures"))
        self.assertEqual(check["calls"]["responses"],342)
        self.assertEqual(check["configured_branches"],10)
        self.assertEqual(check["configured_horizons"],{"formation":3,"post":3})

    def test_interrupted_recording_is_never_certified_complete(self):
        cfg=default_config();cfg["max_calls"]=2
        folder=Path(self.tmp.name)/"interrupted"
        Engine(FixtureProvider(),cfg,folder).run()
        check=verifier.verify(folder)
        self.assertEqual(check["status"],"incomplete",check.get("failures"))

    def test_verifier_detects_score_corruption(self):
        import shutil
        folder=Path(self.tmp.name)/"corrupt-score"
        shutil.copytree(self.recording,folder)
        summary=json.loads((folder/"summary.json").read_text())
        summary["seed_results"]["20261019"]["branches"]["team_H"]["mean_cBR"]+=.1
        (folder/"summary.json").write_text(json.dumps(summary),encoding="utf-8")
        check=verifier.verify(folder)
        self.assertEqual(check["status"],"invalid")
        self.assertTrue(any(f["check"]=="summary_means:team_H" for f in check["failures"]))


if __name__=="__main__":unittest.main()
