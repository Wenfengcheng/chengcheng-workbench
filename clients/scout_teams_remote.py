"""Deterministic localhost client for Scout Teams Bot remote control."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen


def local_token()->str:
 config=Path(__file__).resolve().parent.parent/'config.json'
 if not config.is_file():return ''
 try:return str(json.loads(config.read_text(encoding='utf-8')).get('remoteControlToken') or '')
 except (OSError,ValueError,TypeError):return ''

def call_remote(app_url:str,command:str,request_id:str,conversation_type:str='personal',confirmed:bool=False,expected_digest:str='',note:str='',auth_token:str='')->dict:
 parsed=urlparse(app_url)
 if parsed.hostname not in {'127.0.0.1','localhost','::1'}:
  raise ValueError('remote control endpoint must be localhost')
 payload={'command':command,'requestId':request_id,'source':'scout-teams-bot','conversationType':conversation_type,'userConfirmed':confirmed,'expectedDigest':expected_digest,'note':note,'authToken':auth_token or local_token()}
 req=Request(app_url.rstrip('/')+'/api/remote-control',data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
 with urlopen(req,timeout=10) as response:return json.loads(response.read().decode('utf-8'))

def main():
 p=argparse.ArgumentParser(description='Scout Teams Bot client for Chengcheng Workbench')
 p.add_argument('command');p.add_argument('--request-id',required=True);p.add_argument('--app-url',default='http://127.0.0.1:8797');p.add_argument('--conversation-type',default='personal',choices=['personal','group','meeting','channel']);p.add_argument('--confirmed',action='store_true');p.add_argument('--expected-digest',default='');p.add_argument('--note',default='');p.add_argument('--auth-token',default='')
 a=p.parse_args();result=call_remote(a.app_url,a.command,a.request_id,a.conversation_type,a.confirmed,a.expected_digest,a.note,a.auth_token);print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result.get('ok') else 2)
if __name__=='__main__':main()
