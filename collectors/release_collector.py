"""Read-only deployment and security-tag plan collector."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


def latest(root: Path, pattern: str) -> Path | None:
    files = [p for p in root.glob(pattern) if p.is_file()]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def build_snapshot(workspace: Path) -> dict[str, Any]:
    tracking = workspace / "s360-tracking"
    artifact = latest(tracking, "tag-plan-20*.json")
    if not artifact:
        return {"lane":"release","status":"unknown","headline":"未找到部署与 Tag 计划","summary":f"未在 {tracking} 找到 tag-plan JSON。","metrics":[],"items":[],"evidence":[],"source":"release_collector"}
    data = json.loads(artifact.read_text(encoding="utf-8-sig"))
    total = int(data.get("totalRepos", 0) or 0)
    executable = data.get("canExecute") or []
    split = data.get("splitEnv") or []
    errors = data.get("errors") or []
    status = "blocked" if errors else ("waiting_approval" if executable else ("attention" if split else "verified"))
    items=[]
    for row in executable[:2]:
        envs=[]
        for env in ("int","edog","prod"):
            details=row.get(env) or {}
            if details.get("needs_tag") or details.get("same_as_main"):
                envs.append(env.upper())
        items.append({"title":f"{row.get('repo','repo')} · {', '.join(envs) or '基线已核对'}","status":"waiting_approval","nextAction":"仅在精确审批后执行 Tag/Build"})
    for row in split[:2]:
        items.append({"title":f"{row.get('repo','repo')} · 环境 Commit 不一致","status":"attention","nextAction":"按环境拆分，Pod 运行 Commit 优先"})
    for error in errors[:2]:
        items.append({"title":str(error)[:120],"status":"blocked","nextAction":"修复计划生成错误"})
    return {
        "lane":"release","status":status,
        "headline":f"{len(executable)} 个仓库可进入审批，{len(split)} 个需拆环境",
        "summary":f"{data.get('generated','')} 只读计划覆盖 {total} 个仓库；错误 {len(errors)}。未执行 Tag、Build 或部署。",
        "metrics":[{"label":"仓库","value":total},{"label":"可执行","value":len(executable)},{"label":"拆环境","value":len(split)}],
        "items":items,"evidence":[{"label":"Security Tag 计划","path":str(artifact)}],"source":"security-tag-plan",
        "observedAt":datetime.fromtimestamp(artifact.stat().st_mtime,timezone.utc).isoformat(),
    }


def post_snapshot(url: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    req=Request(url.rstrip('/')+'/api/ops-lanes',data=json.dumps(snapshot,ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
    with urlopen(req,timeout=10) as response: return json.loads(response.read().decode('utf-8'))


def main():
    p=argparse.ArgumentParser(); p.add_argument('--workspace',type=Path,required=True); p.add_argument('--app-url',default='http://127.0.0.1:8787'); p.add_argument('--dry-run',action='store_true'); a=p.parse_args()
    snapshot=build_snapshot(a.workspace); print(json.dumps(snapshot if a.dry_run else post_snapshot(a.app_url,snapshot),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
