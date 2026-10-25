"""Offline checks of model identity, exact rendering and budgeted recovery."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from rem_harness.providers import build_prompt, served_model_identity, PrefixResumeProvider
from rem_harness.models import digest


class TransportTests(unittest.TestCase):
    def test_served_model_is_never_inferred_from_alias(self):
        self.assertEqual(served_model_identity([{"type":"turn.completed","usage":{}}]), (None,"not_exposed_by_cli"))
        self.assertEqual(served_model_identity([{"response":{"model":"actual-returned-version"}}])[0], "actual-returned-version")
        self.assertEqual(served_model_identity([{"model":"a"},{"model":"b"}])[0], None)

    def test_two_decimal_map_render_does_not_round_behavior(self):
        payload={"task":{"protocol_version":"rem-prototype-0.2-test"},
                 "slots":{"H":{"cells":[{"estimate":.5,"lower":.04,"upper":.99}]},
                          "LB":[{"probability":.123456789}]}}
        _, prompt=build_prompt("audit_map", payload, {})
        self.assertIn('"estimate": 0.50',prompt)
        self.assertIn('"probability": 0.123456789',prompt)
        self.assertIn("OWN current",prompt)
        self.assertEqual(json.loads(prompt.split("\n\n",1)[1]),payload)

    def test_v1_prompt_remains_identical(self):
        from rem_harness.providers import INSTRUCTIONS
        payload={"task":{"protocol_version":"rem-prototype-0.1"},"slots":{"H":None}}
        _, prompt=build_prompt("forecast_initial",payload,{})
        self.assertEqual(prompt, INSTRUCTIONS["forecast_initial"]+"\n\n"+json.dumps(payload,ensure_ascii=False,sort_keys=True))

    def test_v2_map_instruction_removed_from_system_as_well_as_payload(self):
        payload={"task":{"protocol_version":"rem-prototype-0.2-test"},"slots":{"H":None}}
        for kind in ("forecast_initial","forecast_revision","probe"):
            system,_=build_prompt(kind,payload,{})
            self.assertNotIn("all nine",system)
            self.assertNotIn("lower <=",system)
        system,_=build_prompt("map",payload,{})
        self.assertIn("all nine",system)
        system,_=build_prompt("audit_recall",payload,{})
        self.assertIn("Transcribe",system)
        self.assertNotIn("your subjective",system)

    def _interrupted(self,folder):
        cfg={"per_branch_call_cap":2,"formation_call_cap":2,"max_calls":3}
        manifest={"config":cfg,"status":"error","provider":{"requested_model":"same-model"}}
        schema={"type":"object","properties":{"probability":{"type":"number","minimum":0,"maximum":1}},"required":["probability"],"additionalProperties":False}
        first={"event":"call_request","call_id":"call-000001","seed":1,"branch":"team_P","kind":"forecast_initial","payload":{"slot":1},"schema":schema}
        second={**first,"call_id":"call-000002","payload":{"slot":2}}
        response={"event":"call_response","call_id":"call-000001","response":{"probability":.5}}
        (folder/"manifest.json").write_text(json.dumps(manifest))
        (folder/"calls.jsonl").write_text("\n".join(map(json.dumps,[first,response,second]))+"\n")
        return cfg,first,second

    def test_resume_reuses_prefix_and_counts_failed_dispatch_toward_cap(self):
        class Fake:
            requested_model="same-model";is_live=False;last_trace={}
            def complete(self,*args): raise AssertionError("Physical branch budget must prevent transport")
        with tempfile.TemporaryDirectory() as d:
            cfg,first,second=self._interrupted(Path(d))
            provider=PrefixResumeProvider(d,Fake(),cfg)
            self.assertEqual(provider.complete(first["kind"],first["payload"],first["schema"]),{"probability":.5})
            self.assertFalse(provider.last_trace["physical_dispatch"])
            provider.call_context={"seed":1,"branch":"team_P"}
            with self.assertRaisesRegex(RuntimeError,"budget exhausted"):
                provider.complete(second["kind"],second["payload"],second["schema"])

    def test_resume_refuses_payload_or_model_substitution(self):
        class Fake:
            requested_model="same-model";is_live=False
        with tempfile.TemporaryDirectory() as d:
            cfg,first,_=self._interrupted(Path(d))
            provider=PrefixResumeProvider(d,Fake(),cfg)
            with self.assertRaisesRegex(RuntimeError,"prefix mismatch"):
                provider.complete(first["kind"],{"slot":99},first["schema"])
            Fake.requested_model="different-model"
            with self.assertRaisesRegex(ValueError,"substitute"):
                PrefixResumeProvider(d,Fake(),cfg)

    def test_hard_interrupted_resume_cannot_forget_old_failures(self):
        class Fake:
            requested_model="same-model";is_live=False
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);cfg,_,_=self._interrupted(folder)
            manifest=json.loads((folder/'manifest.json').read_text())
            manifest['provider']['name']='exact_prefix_resume'
            manifest['status']='running'
            (folder/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'durable cumulative ledger'):
                PrefixResumeProvider(folder,Fake(),cfg)
            ledger={'config_hash':digest(cfg),'attempts_by_branch':{'1:team_P':2}}
            (folder/'physical_attempts.json').write_text(json.dumps(ledger))
            resumed=PrefixResumeProvider(folder,Fake(),cfg)
            self.assertEqual(resumed.physical,{'1:team_P':2})

    def test_resume_persists_attempt_before_delegate_runs(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);cfg,first,second=self._interrupted(folder)
            cfg['per_branch_call_cap']=3
            manifest=json.loads((folder/'manifest.json').read_text());manifest['config']=cfg
            (folder/'manifest.json').write_text(json.dumps(manifest))
            output=folder/'new';output.mkdir()
            class Fake:
                requested_model='same-model';is_live=False;last_trace={}
                def complete(self,*args):
                    saved=json.loads((output/'physical_attempts.json').read_text())
                    assert saved['attempts_by_branch']['1:team_P']==3
                    return {'probability':.6}
            resumed=PrefixResumeProvider(folder,Fake(),cfg,output_dir=output)
            resumed.complete(first['kind'],first['payload'],first['schema'])
            resumed.call_context={'seed':1,'branch':'team_P'}
            self.assertEqual(resumed.complete(second['kind'],second['payload'],second['schema']),{'probability':.6})

if __name__ == "__main__": unittest.main()
