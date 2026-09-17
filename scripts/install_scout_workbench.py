#!/usr/bin/env python3
"""Create-only install of a stable Scout-owned Chengcheng Workbench."""
from __future__ import annotations

import argparse
import json
import pathlib
import secrets
import shutil

REPO = pathlib.Path(__file__).resolve().parent.parent
SOURCE = REPO / "app"
INCLUDE = ["app.py", "preflight.ps1", "start-app.ps1", "stop-app.ps1", "static", "data"]
RUNTIME_TOOLS = [
    REPO / "scripts" / "claim_security_batch.py",
    REPO / "scripts" / "record_security_batch_result.py",
    REPO / "clients" / "scout_teams_remote.py",
    REPO / "runtime" / "s360-scout-consumer.json",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True, type=pathlib.Path)
    parser.add_argument("--port", type=int, default=8792)
    args = parser.parse_args()
    destination = args.destination.resolve()
    if ".concordia-client" in str(destination).lower():
        raise RuntimeError("Stable Workbench must not be installed under OpenClaw")
    if destination.exists():
        raise RuntimeError(f"Create-only guard: destination exists: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    for name in INCLUDE:
        source = SOURCE / name
        target = destination / name
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "daily-flow-app.pid"))
        else:
            shutil.copy2(source, target)
    tools = destination / "runtime-tools"
    tools.mkdir(exist_ok=False)
    for source in RUNTIME_TOOLS:
        if not source.is_file():
            raise RuntimeError(f"Required runtime tool missing: {source}")
        shutil.copy2(source, tools / source.name)
    (destination / "config.json").write_text(json.dumps({"port": args.port, "logRequests": False,
        "remoteControlToken": secrets.token_urlsafe(32)}, indent=2), encoding="utf-8")
    print(f"PASS: installed stable Scout Workbench create-only at {destination} on port {args.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
