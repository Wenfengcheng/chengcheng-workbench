import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from collaboration_collector import build_snapshot
class CollaborationTests(unittest.TestCase):
 def test_empty_is_explicit_unknown(self):
  with tempfile.TemporaryDirectory() as t:self.assertEqual('unknown',build_snapshot(Path(t))['status'])
 def test_persisted_note_with_todo_is_attention(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'memory'/'meetings';root.mkdir(parents=True);(root/'2026-09-17-release-sync.html').write_text('<h1>Release sync</h1><h2>TODO</h2><p>行动项</p>',encoding='utf-8')
   with patch('collaboration_collector.datetime') as dt:
    dt.now.return_value.date.return_value.isoformat.return_value='2026-09-17';dt.fromtimestamp.side_effect=__import__('datetime').datetime.fromtimestamp
    r=build_snapshot(Path(t))
   self.assertEqual('attention',r['status']);self.assertEqual(2,r['metrics'][1]['value']);self.assertEqual(1,len(r['evidence']))
if __name__=='__main__':unittest.main()
