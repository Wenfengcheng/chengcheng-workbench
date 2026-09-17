"""Read-only collector for locally persisted meeting/action evidence."""
from __future__ import annotations
import argparse,json,re
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from urllib.request import Request,urlopen

DATE_RE=re.compile(r'^(\d{4}-\d{2}-\d{2})-(.+)\.html$',re.I)
def build_snapshot(workspace:Path)->dict[str,Any]:
 root=workspace/'memory'/'meetings'; files=sorted(root.glob('*.html'),key=lambda p:p.stat().st_mtime,reverse=True) if root.is_dir() else []
 if not files:return {'lane':'collaboration','status':'unknown','headline':'今天没有已沉淀的会议纪要','summary':'本地 meeting evidence 为空；不从缺失材料推断会议结论或待办。','metrics':[{'label':'纪要','value':0},{'label':'待办线索','value':0},{'label':'待审批','value':0}],'items':[],'evidence':[],'source':'meeting-memory'}
 today=datetime.now().date().isoformat(); today_files=[p for p in files if p.name.startswith(today)]
 recent=today_files or files[:3]; todo_count=0;items=[];evidence=[]
 for p in recent[:3]:
  text=p.read_text(encoding='utf-8-sig',errors='replace'); count=len(re.findall(r'\bTODO\b|待办|行动项',text,re.I));todo_count+=count
  m=DATE_RE.match(p.name); title=(m.group(2) if m else p.stem).replace('-',' ')
  items.append({'title':title[:100],'status':'verified','nextAction':'打开纪要复核行动项'})
  evidence.append({'label':title[:60],'path':str(p)})
 status='attention' if todo_count else 'verified'
 label='今日' if today_files else '最近'
 return {'lane':'collaboration','status':status,'headline':f'{label} {len(recent)} 份会议纪要，{todo_count} 处待办线索','summary':'仅汇总本地已持久化纪要；邮件、Teams 外发和日历变更仍需精确审批。','metrics':[{'label':'纪要','value':len(recent)},{'label':'待办线索','value':todo_count},{'label':'待审批','value':0}],'items':items,'evidence':evidence,'source':'meeting-memory','observedAt':datetime.fromtimestamp(recent[0].stat().st_mtime,timezone.utc).isoformat()}
def post_snapshot(url,s):
 req=Request(url.rstrip('/')+'/api/ops-lanes',data=json.dumps(s,ensure_ascii=False).encode(),headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
 with urlopen(req,timeout=10) as r:return json.loads(r.read().decode())
def main():
 p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--app-url',default='http://127.0.0.1:8787');p.add_argument('--dry-run',action='store_true');a=p.parse_args();s=build_snapshot(a.workspace);print(json.dumps(s if a.dry_run else post_snapshot(a.app_url,s),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
