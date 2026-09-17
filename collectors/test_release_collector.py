import json, tempfile, unittest
from pathlib import Path
from release_collector import build_snapshot

class ReleaseCollectorTests(unittest.TestCase):
    def test_plan_needing_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'s360-tracking'; root.mkdir()
            (root/'tag-plan-20260917.json').write_text(json.dumps({'generated':'now','totalRepos':17,'canExecute':[{'repo':'A','edog':{'same_as_main':True}}],'splitEnv':[{'repo':'B'}],'errors':[]}),encoding='utf-8')
            result=build_snapshot(Path(tmp))
            self.assertEqual('waiting_approval',result['status']); self.assertEqual(17,result['metrics'][0]['value']); self.assertIn('Pod',result['items'][1]['nextAction'])
    def test_errors_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'s360-tracking'; root.mkdir()
            (root/'tag-plan-20260917.json').write_text(json.dumps({'errors':['bad baseline']}),encoding='utf-8')
            self.assertEqual('blocked',build_snapshot(Path(tmp))['status'])
    def test_missing_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp: self.assertEqual('unknown',build_snapshot(Path(tmp))['status'])

if __name__=='__main__': unittest.main()
