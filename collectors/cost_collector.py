"""Read-only Azure cost monitoring CSV collector."""
from __future__ import annotations
import argparse, csv, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


def rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def build_snapshot(workspace: Path) -> dict[str,Any]:
    monitor=workspace/'fy27-cost-review'/'monitoring'; daily=monitor/'pbi-cost-daily-snapshots.csv'; providers=monitor/'provider-cost-model-verification.csv'; oi=monitor/'operationalinsights-cost-verification.csv'
    if not daily.is_file(): return {'lane':'cost','status':'unknown','headline':'未找到成本监控快照','summary':f'未找到 {daily}','metrics':[],'items':[],'evidence':[],'source':'cost_collector'}
    daily_rows=rows(daily); latest=daily_rows[-1] if daily_rows else {}; date=latest.get('SnapshotDate') or latest.get('snapshotDate') or next(iter(latest.values()),'')
    actual=float(latest.get('MTDCostUSD') or 0); runrate=float(latest.get('ProjectedMonthUSD') or 0); budget=float(latest.get('AugustBudgetUSD') or 0); variance=float(latest.get('VarianceToBudgetUSD') or 0)
    provider_rows=rows(providers) if providers.is_file() else []; current=[r for r in provider_rows if date and date in r.values()]
    oi_rows=rows(oi) if oi.is_file() else []; oi_latest=oi_rows[-1] if oi_rows else {}; oi_status='PASS' if 'PASS' in oi_latest.values() else ('DRIFT' if 'DRIFT' in oi_latest.values() else 'UNKNOWN')
    drift=[]
    for r in current:
        provider=r.get('Provider') or 'provider'
        if r.get('Status') == 'DRIFT': drift.append(provider)
    status='attention' if drift or oi_status=='DRIFT' or variance>0 else 'verified'
    items=[]
    if variance>0: items.append({'title':f'Run-rate 超预算 ${variance:,.0f}','status':'attention','nextAction':'核对驱动项；不自动执行缩容'})
    if drift: items.append({'title':f'{len(drift)} 个 Provider 模型漂移','status':'attention','nextAction':'重新校准后再用于决策'})
    items.append({'title':f'OperationalInsights 模型 {oi_status}','status':'verified' if oi_status=='PASS' else 'attention','nextAction':'保持每日验证'})
    evidence=[{'label':'PBI 每日成本快照','path':str(daily)}]
    if providers.is_file(): evidence.append({'label':'Provider 模型验证','path':str(providers)})
    if oi.is_file(): evidence.append({'label':'OperationalInsights 验证','path':str(oi)})
    return {'lane':'cost','status':status,'headline':f'Run-rate ${runrate:,.0f}，预算差 ${variance:,.0f}','summary':f'{date} Actual ${actual:,.0f}；仅展示 actual/run-rate/model verification，不将预测写成已实现节省。','metrics':[{'label':'Actual','value':f'${actual/1000:.1f}K'},{'label':'Run-rate','value':f'${runrate/1000:.1f}K'},{'label':'预算差','value':f'${variance/1000:.1f}K'}],'items':items,'evidence':evidence,'source':'fy27-cost-monitoring','observedAt':datetime.fromtimestamp(daily.stat().st_mtime,timezone.utc).isoformat()}

def post_snapshot(url,snapshot):
    req=Request(url.rstrip('/')+'/api/ops-lanes',data=json.dumps(snapshot,ensure_ascii=False).encode(),headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
    with urlopen(req,timeout=10) as r:return json.loads(r.read().decode())
def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--app-url',default='http://127.0.0.1:8787');p.add_argument('--dry-run',action='store_true');a=p.parse_args();s=build_snapshot(a.workspace);print(json.dumps(s if a.dry_run else post_snapshot(a.app_url,s),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
