#!/usr/bin/env python3
"""Create-only synchronization of declared Chengcheng automations into Scout."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import uuid

REPO = pathlib.Path(__file__).resolve().parent.parent
SOURCE = REPO / "automations" / "scout-native-migration.json"
CONSUMER = REPO / "runtime" / "s360-scout-consumer.json"


def schedule(value: str) -> dict:
    mapping = {
        "every day at 9am": ("0 9 * * *", 9, 0, list(range(7))),
        "every day at 9:30am": ("30 9 * * *", 9, 30, list(range(7))),
        "every day at 9:45am": ("45 9 * * *", 9, 45, list(range(7))),
        "every weekday at 8am": ("0 8 * * 1-5", 8, 0, [1, 2, 3, 4, 5]),
        "every Monday at 11am": ("0 11 * * 1", 11, 0, [1]),
    }
    if value not in mapping:
        raise ValueError(f"unsupported declared schedule: {value}")
    expression, hour, minute, days = mapping[value]
    return {"kind": "cron", "naturalLanguage": value, "cronExpression": expression,
            "days": days, "hour": hour, "minute": minute}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True, type=pathlib.Path)
    parser.add_argument("--runtime-root", required=True, type=pathlib.Path)
    parser.add_argument("--workbench-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    store = args.store.resolve()
    runtime = args.runtime_root.resolve()
    workbench = args.workbench_root.resolve()
    entries = json.loads(store.read_text(encoding="utf-8-sig")) if store.is_file() else []
    if not isinstance(entries, list):
        raise RuntimeError("Scout automation store must be an array")
    definitions = json.loads(SOURCE.read_text(encoding="utf-8"))["automations"]
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    created, existing = [], []
    by_name = {item.get("name"): item for item in entries if isinstance(item, dict)}
    for item in definitions:
        name = item["name"]
        if name in by_name:
            existing.append(name)
            continue
        prompt = item["steps"][0]["prompt"].replace("{{SCOUT_RUNTIME_ROOT}}", str(runtime))
        prompt += (f" Workbench URL is http://127.0.0.1:8796 and stable root is {workbench}. "
                   "This synchronized automation is disabled. Do not enable until every referenced job exists under Scout Runtime, preflight passes, and the matching OpenClaw owner is explicitly cut over.")
        automation = {
            "id": str(uuid.uuid4()), "name": name, "description": item["description"],
            "schedule": schedule(item["schedule"]),
            "steps": [{"id": str(uuid.uuid4()), "label": item["steps"][0]["label"], "prompt": prompt}],
            "enabled": False, "oneShot": False, "createdAt": now, "updatedAt": now,
            "triggerType": "schedule", "workingDir": str(runtime),
            "skillNames": item.get("skillNames") or [], "teamsNotify": "never",
            "cutoverTeamsNotify": item.get("cutoverTeamsNotify", "auto"),
            "migrationState": "disabled-synchronized",
        }
        entries.append(automation)
        created.append(name)
    store.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "created": created, "existing": existing,
                      "totalInStore": len(entries)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
