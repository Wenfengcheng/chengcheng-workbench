#!/usr/bin/env python3
"""Create exactly one enabled, notification-silent Scout cost Shadow automation."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import uuid

NAME = "程程工作台 - Azure 成本每日 Shadow"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scout-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    scout_root = args.scout_root.resolve()
    runtime_root = scout_root / "runtime"
    if ".concordia-client" in str(scout_root).lower() or ".concordia-client" in str(runtime_root).lower():
        raise RuntimeError("Scout automation paths must not resolve into OpenClaw")
    store = scout_root / "m-automations" / "automations.json"
    if store.exists():
        current = json.loads(store.read_text(encoding="utf-8"))
        if not isinstance(current, list):
            raise RuntimeError("Scout automation store is not an array")
        if current:
            raise RuntimeError(f"Create-only guard: Scout already has {len(current)} automation(s); use its native tool/UI")
    else:
        current = []
    required = [
        runtime_root / "jobs" / "cost-daily-shadow.py",
        runtime_root / "scripts" / "preflight_cost_runtime.py",
        runtime_root / "scripts" / "publish_cost_lane.py",
        runtime_root / "packages" / "chengcheng-cost-monitor-v0.5.1" / "package-manifest.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Scout cost runtime is incomplete: {missing}")
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    automation = {
        "id": str(uuid.uuid4()),
        "name": NAME,
        "description": "Scout-native 09:45 deterministic Azure cost monitor Shadow; notification silent.",
        "schedule": {
            "kind": "cron",
            "naturalLanguage": "every day at 9:45am",
            "cronExpression": "45 9 * * *",
            "days": [0, 1, 2, 3, 4, 5, 6],
            "hour": 9,
            "minute": 45
        },
        "steps": [{
            "id": str(uuid.uuid4()),
            "label": "Run deterministic Azure cost Shadow",
            "prompt": (
                f"Run exactly: python {runtime_root}\\scripts\\preflight_cost_runtime.py --package-root "
                f"{runtime_root}\\packages\\chengcheng-cost-monitor-v0.5.1 ; if ($LASTEXITCODE -eq 0) {{ "
                f"python {runtime_root}\\jobs\\cost-daily-shadow.py --package-root "
                f"{runtime_root}\\packages\\chengcheng-cost-monitor-v0.5.1 ; if ($LASTEXITCODE -eq 0) {{ "
                f"python {runtime_root}\\scripts\\publish_cost_lane.py --package-root "
                f"{runtime_root}\\packages\\chengcheng-cost-monitor-v0.5.1 --workbench-url http://127.0.0.1:8791 }} }}. "
                "Shadow only: do not send Teams/email/WeChat messages; do not resize, delete, change tier, modify Azure resources, "
                "update ADO, or mutate any scheduler. Return the final PASS/FAIL summary only."
            )
        }],
        "enabled": True,
        "oneShot": False,
        "createdAt": now,
        "updatedAt": now,
        "triggerType": "schedule",
        "workingDir": str(runtime_root),
        "skillNames": [],
        "teamsNotify": "never"
    }
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("x" if not store.exists() else "w", encoding="utf-8") as handle:
        json.dump([automation], handle, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "id": automation["id"], "name": NAME, "enabled": True, "teamsNotify": "never", "store": str(store)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
