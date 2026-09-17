#!/usr/bin/env python3
"""Project the latest Scout cost Shadow evidence into Chengcheng Workbench."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import urllib.request

SUMMARY = re.compile(
    r"Snapshot=(?P<snapshot>\d{4}-\d{2}-\d{2}).*?ReportAsOf=(?P<asof>\d{4}-\d{2}-\d{2})"
    r".*?MTD=\$(?P<mtd>[\d,.]+).*?Forecast=\$(?P<forecast>[\d,.]+).*?SHA256=(?P<sha>[A-Fa-f0-9]{64})"
)
OPINSIGHTS = re.compile(r"OperationalInsights skill verify (?P<status>PASS|BASELINE|DRIFT).*?Drift=(?P<drift>[+-]?[\d.]+)%")
PROVIDER = re.compile(r"(Storage|Search|CDN|AML)=(PASS|BASELINE|DRIFT)\(")


def latest_evidence(root: pathlib.Path) -> pathlib.Path:
    evidence_dir = root / "runtime" / "evidence" / "cost"
    candidates = sorted(evidence_dir.glob("*.json"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        raise RuntimeError(f"No Scout cost evidence found in {evidence_dir}")
    return candidates[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True, type=pathlib.Path)
    parser.add_argument("--workbench-url", default="http://127.0.0.1:8787")
    parser.add_argument("--evidence", type=pathlib.Path)
    args = parser.parse_args()
    root = args.package_root.resolve()
    evidence_path = args.evidence.resolve() if args.evidence else latest_evidence(root)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("exitCode") != 0:
        raise RuntimeError(f"Refusing to publish failed Shadow evidence: {evidence_path}")
    if any(evidence.get(key) is not False for key in ("notificationsSent", "externalWrites", "resourceChanges")):
        raise RuntimeError("Shadow safety attestations are not all false")
    stdout = str(evidence.get("stdout") or "")
    summary = SUMMARY.search(stdout)
    opinsights = OPINSIGHTS.search(stdout)
    providers = PROVIDER.findall(stdout)
    if not summary or not opinsights or len(providers) != 4:
        raise RuntimeError("Scout cost evidence does not contain the complete verified summary")
    values = summary.groupdict()
    provider_items = [{"title": name, "status": status.lower()} for name, status in providers]
    overall = "verified" if opinsights.group("status") in {"PASS", "BASELINE"} and all(x["status"] in {"pass", "baseline"} for x in provider_items) else "attention"
    observed = dt.datetime.fromtimestamp(evidence_path.stat().st_mtime, dt.timezone.utc).isoformat()
    payload = {
        "lane": "cost",
        "status": overall,
        "headline": f"Scout Shadow GREEN · {values['snapshot']} · 1/3",
        "summary": f"成本事实截至 {values['asof']}；OperationalInsights {opinsights.group('status')}，四个 Provider 模型均完成对账。Shadow 未发送通知、未执行外部写入或资源变更。",
        "metrics": [
            {"label": "MTD", "value": f"${float(values['mtd'].replace(',', '')):,.2f}"},
            {"label": "月度投影", "value": f"${float(values['forecast'].replace(',', '')):,.2f}"},
            {"label": "OI 漂移", "value": f"{float(opinsights.group('drift')):+.2f}%"},
            {"label": "Shadow Gate", "value": "1 / 3"}
        ],
        "items": provider_items,
        "evidence": [
            {"label": "Scout Shadow evidence", "path": str(evidence_path)},
            {"label": "Cost trend HTML", "path": str(root / "fy27-cost-review" / "monitoring" / "pbi-cost-trend.html")},
            {"label": "Trend SHA256", "value": values["sha"].upper()}
        ],
        "source": "microsoft-scout/cost-daily-shadow",
        "observedAt": observed
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        args.workbench_url.rstrip("/") + "/api/ops-lanes",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
    lane = result.get("lane") or {}
    if not result.get("ok") or lane.get("status") != overall or lane.get("source") != payload["source"]:
        raise RuntimeError(f"Workbench read-back mismatch: {result}")
    print(f"PASS: published Scout cost evidence to Workbench ({lane['headline']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
