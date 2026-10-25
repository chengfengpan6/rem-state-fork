"""Adversarial recording changes must fail even when visible hashes agree."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_protocol_v2 import V2FixtureProvider, diagnostic_config
from rem_harness.engine import Engine
from rem_harness.models import digest

spec=importlib.util.spec_from_file_location('verify_v2',Path(__file__).resolve().parents[1]/'tools/verify_v2.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class SemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.folder=Path(cls.temp.name)/'original'
        result=Engine(V2FixtureProvider(),diagnostic_config(),cls.folder).run()
        assert result['status']=='completed',result
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def _alter(self,name,change):
        folder=Path(self.temp.name)/name
        shutil.copytree(self.folder,folder)
        events=[json.loads(l) for l in (folder/'events.jsonl').read_text().splitlines()]
        for row in events:
            if row['event']=='call_request' and row['branch']=='team_H':
                change(row)
                row['visible_state_hash']=digest(row['payload']['slots'])
        (folder/'events.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in events),encoding='utf-8')
        (folder/'calls.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in events if r['event'].startswith('call_')),encoding='utf-8')
        return module.verify_v2(folder)

    def test_unmodified_recording_passes(self):
        report=module.verify_v2(self.folder)
        self.assertEqual(report['status'],'verified_complete',report['failures'])

    def test_map_null_with_recomputed_hash_is_rejected(self):
        result=self._alter('null-map',lambda row:row['payload']['slots'].update(H=None))
        self.assertEqual(result['status'],'invalid')
        self.assertTrue(any(r['check']=='reconstructed_semantic_requests' for r in result['failures']))

    def test_wrong_personal_record_with_recomputed_hash_is_rejected(self):
        result=self._alter('wrong-personal',lambda row:row['payload']['slots']['Pi'].update(own_records=[]))
        self.assertEqual(result['status'],'invalid')
        self.assertTrue(any(r['check']=='reconstructed_semantic_requests' for r in result['failures']))

    def test_reintroduced_nonmap_reporting_instruction_is_rejected(self):
        def change(row):
            if row['kind']=='message':row['payload']['task']['map_instruction']='Report nine cells'
        result=self._alter('bad-stage',change)
        self.assertTrue(any(r['check'].startswith('stage_map_instruction:') for r in result['failures']))

    def test_live_manifest_cannot_be_certified_without_actual_transport_trace(self):
        folder=Path(self.temp.name)/'missing-live-trace'
        shutil.copytree(self.folder,folder)
        path=folder/'manifest.json';manifest=json.loads(path.read_text())
        manifest['provider']['is_live']=True
        path.write_text(json.dumps(manifest))
        result=module.verify_v2(folder)
        self.assertEqual(result['status'],'invalid')
        self.assertTrue(any(r['check'].startswith('live_transport_trace_present:') for r in result['failures']))

if __name__=='__main__':unittest.main()
