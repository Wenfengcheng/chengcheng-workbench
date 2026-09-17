#!/usr/bin/env python3
"""Create-only install of a stable Scout-owned Chengcheng Workbench."""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil

REPO = pathlib.Path(__file__).resolve().parent.parent
SOURCE = REPO / "app"
INCLUDE = ["app.py", "preflight.ps1", "start-app.ps1", "stop-app.ps1", "static", "data"]


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
    (destination / "config.json").write_text(json.dumps({"port": args.port, "logRequests": False}, indent=2), encoding="utf-8")
    print(f"PASS: installed stable Scout Workbench create-only at {destination} on port {args.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
