import sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import app
class EngineeringActionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.db';self.connections=[]
  def connect():
   db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');self.connections.append(db);return db
  self.p=patch.object(app,'connect',connect);self.p.start();app.init_db()
 def tearDown(self):
  self.p.stop();[db.close() for db in self.connections];self.tmp.cleanup()
 def payload(self):return {'lane':'pipeline','actionType':'pipeline-retry','title':'Retry Build 1','target':'Build 1','environment':'edog','exactAction':'Retry only Build 1 once','prechecks':['failure is transient','deploy stage not reached'],'rollback':'stop after one retry','evidence':[{'label':'timeline'}]}
 def test_create_is_proposal_and_never_executable(self):
  item=app.create_engineering_action(self.payload());self.assertEqual('proposed',item['status']);self.assertFalse(item['executionEnabled']);self.assertEqual(2,len(item['prechecks']))
 def test_approval_records_intent_only(self):
  item=app.create_engineering_action(self.payload());approved=app.decide_engineering_action(item['id'],'approved','reviewed');self.assertEqual('approved',approved['status']);self.assertFalse(approved['executionEnabled']);self.assertEqual('reviewed',approved['decision_note'])
 def test_second_decision_is_rejected(self):
  item=app.create_engineering_action(self.payload());app.decide_engineering_action(item['id'],'rejected');
  with self.assertRaises(ValueError):app.decide_engineering_action(item['id'],'approved')
 def test_requires_exact_target_and_action(self):
  with self.assertRaises(ValueError):app.create_engineering_action({'lane':'pipeline','actionType':'pipeline-retry','title':'bad'})
if __name__=='__main__':unittest.main()
