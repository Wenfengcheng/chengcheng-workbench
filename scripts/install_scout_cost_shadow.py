#!/usr/bin/env python3
"""Create-only install of the Scout-native cost Shadow support files."""
from __future__ import annotations

import argparse
import pathlib
import shutil

REPO = pathlib.Path(__file__).resolve().parent.parent
FILES = {
    "jobs/cost-daily-shadow.py": REPO / "jobs" / "cost-daily-shadow.py",
    "scripts/preflight_cost_runtime.py": REPO / "scripts" / "preflight_cost_runtime.py",
    "scripts/publish_cost_lane.py": REPO / "scripts" / "publish_cost_lane.py",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scout-runtime-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = args.scout_runtime_root.resolve()
    if ".concordia-client" in str(root).lower():
        raise RuntimeError("Scout runtime root must not be inside OpenClaw")
    for relative, source in FILES.items():
        target = root / relative
        if target.exists():
            raise RuntimeError(f"Create-only guard: support file already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(f"PASS: installed {len(FILES)} cost Shadow support files create-only under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
