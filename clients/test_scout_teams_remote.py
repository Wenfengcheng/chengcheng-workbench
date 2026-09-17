import unittest
from unittest.mock import patch
from scout_teams_remote import call_remote
class ClientTests(unittest.TestCase):
 def test_rejects_non_local_endpoint(self):
  with self.assertRaises(ValueError):call_remote('https://example.com','状态','id')
 def test_posts_identity_contract(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self):return b'{"ok":true,"executionEnabled":false}'
  with patch('scout_teams_remote.urlopen',return_value=Response()) as opener:
   result=call_remote('http://127.0.0.1:8787','状态','msg-1')
   body=opener.call_args.args[0].data.decode('utf-8')
  self.assertTrue(result['ok']);self.assertIn('scout-teams-bot',body);self.assertIn('personal',body)
if __name__=='__main__':unittest.main()
