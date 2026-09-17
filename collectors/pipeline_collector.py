"""Read-only pipeline artifact collector for Chengcheng Workbench."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def latest(root: Path, patterns: list[str]) -> Path | None:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(p for p in root.glob(pattern) if p.is_file())
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def build_snapshot(workspace: Path) -> dict[str, Any]:
    tracking = workspace / "s360-tracking"
    artifact = latest(tracking, ["weekly-build-*.json", "*build-status*.json", "security-builds-live-*.json"])
    if not artifact:
        return {
            "lane": "pipeline", "status": "unknown", "headline": "未找到 Pipeline 状态产物",
            "summary": f"只读采集器未在 {tracking} 找到受支持的 Build JSON。",
            "metrics": [], "items": [], "evidence": [], "source": "pipeline_collector",
        }

    data = load_json(artifact)
    final = data.get("finalStatus") or {}
    succeeded = int(final.get("succeededCount", len(data.get("finalSucceeded") or [])) or 0)
    failed_rows = data.get("finalFailed") or []
    failed = int(final.get("failedCount", len(failed_rows)) or 0)
    running = int(final.get("inProgressCount", len(data.get("finalInProgress") or [])) or 0)
    not_found = int(final.get("notFoundCount", 0) or 0)
    non_retryable = data.get("nonRetryable") or []
    retried = int(data.get("totalRetried", 0) or 0)
    status = "blocked" if non_retryable or not_found else ("attention" if failed else ("in_progress" if running else "verified"))

    items: list[dict[str, Any]] = []
    non_retryable_ids = {str(row.get("buildId")) for row in non_retryable}
    for row in failed_rows[:3]:
        build_id = str(row.get("id") or row.get("buildId") or "")
        blocked = build_id in non_retryable_ids
        items.append({
            "title": f"{row.get('pipeline', 'Pipeline')} · Build {build_id or '未知'}",
            "status": "blocked" if blocked else "attention",
            "nextAction": "人工分析；禁止自动重试" if blocked else "运行瞬态错误分析后再决定是否申请重试",
        })
    for row in (data.get("finalInProgress") or [])[:2]:
        items.append({"title": f"{row.get('pipeline', 'Pipeline')} · Build {row.get('id', '')}", "status": "in_progress", "nextAction": "等待完成后复查"})
    if not items and succeeded:
        items.append({"title": f"{succeeded} 个 Build 已完成", "status": "verified", "nextAction": "无需操作"})

    completed_at = str(data.get("completedAt") or "")
    return {
        "lane": "pipeline", "status": status,
        "headline": f"{failed} 个失败，{running} 个运行中" if failed or running else f"{succeeded} 个 Build 已通过",
        "summary": f"最近只读产物：成功 {succeeded}、失败 {failed}、运行中 {running}、重试 {retried}；不可重试 {len(non_retryable)}。",
        "metrics": [
            {"label": "成功", "value": succeeded}, {"label": "失败", "value": failed}, {"label": "运行中", "value": running},
        ],
        "items": items,
        "evidence": [{"label": "Pipeline 状态 JSON", "path": str(artifact)}],
        "source": "pipeline-artifacts",
        "observedAt": completed_at or datetime.fromtimestamp(artifact.stat().st_mtime, timezone.utc).isoformat(),
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
