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
 def remote(self,command,request_id='msg-1',confirmed=False,conversation='personal'):
  return app.remote_control({'command':command,'requestId':request_id,'source':'scout-teams-bot','conversationType':conversation,'userConfirmed':confirmed})
 def test_remote_status_and_approval_never_execute(self):
  status=self.remote('状态');self.assertEqual('status',status['kind']);self.assertFalse(status['executionEnabled'])
  item=app.create_engineering_action(self.payload());result=self.remote('批准 '+item['id'],'msg-2',True);self.assertEqual('approved',result['action']['status']);self.assertFalse(result['executionEnabled']);self.assertIn('未执行',result['message'])
 def test_remote_unknown_command_returns_help(self):
  result=self.remote('部署 prod');self.assertFalse(result['ok']);self.assertEqual('help',result['kind'])
 def test_remote_decision_requires_personal_chat_and_confirmation(self):
  item=app.create_engineering_action(self.payload())
  self.assertEqual('denied',self.remote('批准 '+item['id'],'group-msg',True,'group')['kind'])
  self.assertEqual('denied',self.remote('批准 '+item['id'],'no-confirm',False)['kind'])
  self.assertEqual('proposed',app.list_engineering_actions()['actions'][0]['status'])
 def test_remote_request_is_idempotent(self):
  item=app.create_engineering_action(self.payload());first=self.remote('批准 '+item['id'],'stable-id',True);second=self.remote('批准 '+item['id'],'stable-id',True)
  self.assertEqual('approved',first['action']['status']);self.assertTrue(second['replayed'])
 def test_remote_requires_bound_source(self):
  result=app.remote_control({'command':'状态','requestId':'bad-source','source':'unknown','conversationType':'personal'})
  self.assertEqual('denied',result['kind'])
if __name__=='__main__':unittest.main()
