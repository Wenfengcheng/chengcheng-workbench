"""Read-only S360 artifact collector for Chengcheng Workbench."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def latest(root: Path, pattern: str) -> Path | None:
    files = [p for p in root.glob(pattern) if p.is_file()]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def build_snapshot(workspace: Path) -> dict[str, Any]:
    tracking = workspace / "s360-tracking"
    analysis_path = latest(tracking, "analysis-*.json")
    phase_path = latest(tracking, "phase3-summary-*.json")
    if not analysis_path:
        return {
            "lane": "security", "status": "unknown", "headline": "未找到 S360 分析结果",
            "summary": f"只读采集器未在 {tracking} 找到 analysis-*.json。",
            "metrics": [], "items": [], "evidence": [], "source": "s360_collector",
        }

    analysis = load_json(analysis_path)
    phase = load_json(phase_path) if phase_path else {}
    registries = analysis.get("registries") or {}
    office = registries.get("officeplusSla") or {}
    creator = registries.get("creatorSla") or {}
    past = int(office.get("Past SLA", 0) or 0) + int(creator.get("Past SLA", 0) or 0)
    near = int(office.get("Near SLA", 0) or 0) + int(creator.get("Near SLA", 0) or 0)
    total = int(registries.get("officeplusRows", 0) or 0) + int(registries.get("creatorRows", 0) or 0)
    changes = analysis.get("changes") or {}
    added = changes.get("vulnAdded") or []
    cleared = changes.get("vulnCleared") or []
    sla_changes = changes.get("slaChanges") or []
    unmapped = phase.get("unmappedImages") or []
    phase_ok = not phase or phase.get("status") == "PASS"
    status = "blocked" if unmapped or not phase_ok else ("attention" if past or near or added else "verified")

    items: list[dict[str, Any]] = []
    if past:
        items.append({"title": f"{past} 项已超过 SLA", "status": "blocked", "nextAction": "优先核对 Owner 与修复证据"})
    for change in sla_changes[:2]:
        items.append({
            "title": f"{change.get('image', 'image')} → {change.get('to', 'SLA 变化')}",
            "status": "attention", "nextAction": f"到期 {change.get('due', '未知')}",
        })
    for change in cleared[:1]:
        items.append({"title": f"已清除：{change.get('image', 'image')}", "status": "verified", "nextAction": "保留验证证据"})
    if unmapped:
        items.append({"title": f"{len(unmapped)} 个镜像未映射", "status": "blocked", "nextAction": "补齐专属修复流程"})

    evidence = [{"label": "S360 日分析", "path": str(analysis_path)}]
    if phase_path:
        evidence.append({"label": "Phase 3 完整性", "path": str(phase_path)})
    tag_plan = phase.get("tagPlan")
    if tag_plan:
        evidence.append({"label": "Security Tag 计划", "path": str(tag_plan)})

    date = str(analysis.get("date") or analysis_path.stem.replace("analysis-", ""))
    headline = f"{past} 项超 SLA，{near} 项临近 SLA" if past or near else "当前没有超期或临期项"
    return {
        "lane": "security", "status": status, "headline": headline,
        "summary": f"{date} 扫描覆盖 {total} 行；新增 {len(added)}、清除 {len(cleared)}；Phase 3 {'通过' if phase_ok else '未通过'}。",
        "metrics": [
            {"label": "扫描行", "value": total}, {"label": "超 SLA", "value": past}, {"label": "临近 SLA", "value": near},
        ],
        "items": items, "evidence": evidence, "source": "s360-tracking",
        "observedAt": datetime.fromtimestamp(analysis_path.stat().st_mtime, timezone.utc).isoformat(),
    }


def post_snapshot(url: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
    request = Request(url.rstrip("/") + "/api/ops-lanes", data=body, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--app-url", default="http://127.0.0.1:8787")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    snapshot = build_snapshot(args.workspace)
    result = snapshot if args.dry_run else post_snapshot(args.app_url, snapshot)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
