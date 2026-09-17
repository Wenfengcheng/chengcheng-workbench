#!/usr/bin/env python3
"""Scout shadow wrapper: read Azure, write package-local evidence, notify nobody."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = args.package_root.resolve()
    if ".concordia-client" in str(root).lower():
        raise RuntimeError("Shadow runtime cannot execute from OpenClaw workspace")
    manifest = json.loads((root / "package-manifest.json").read_text(encoding="utf-8"))
    if manifest["shadowPolicy"] != {"notifications": False, "externalWrites": False, "resourceChanges": False, "allowed": ["Power BI read", "Azure ARM read", "Log Analytics query", "package-local CSV, JSON, HTML and evidence writes"]}:
        raise RuntimeError("Unexpected shadow policy; fail closed")

    entrypoint = root / manifest["entrypoint"]
    result = subprocess.run([sys.executable, str(entrypoint)], cwd=str(entrypoint.parent.parent), text=True, capture_output=True, encoding="utf-8")
    evidence_dir = root / "runtime" / "evidence" / "cost"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")
    output_html = root / "fy27-cost-review" / "monitoring" / "pbi-cost-trend.html"
    evidence = {
        "schemaVersion": 1,
        "mode": "shadow",
        "runtimeOwner": "Microsoft Scout",
        "startedAtLocal": stamp,
        "exitCode": result.returncode,
        "notificationsSent": False,
        "externalWrites": False,
        "resourceChanges": False,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "trendSHA256": sha256(output_html) if output_html.is_file() else None
    }
    evidence_path = evidence_dir / f"{stamp}.json"
    with evidence_path.open("x", encoding="utf-8") as handle:
        json.dump(evidence, handle, ensure_ascii=False, indent=2)
    if result.stdout: print(result.stdout, end="")
    if result.stderr: print(result.stderr, end="", file=sys.stderr)
    print(f"Scout shadow evidence: {evidence_path}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
