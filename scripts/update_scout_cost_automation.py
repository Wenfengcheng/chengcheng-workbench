#!/usr/bin/env python3
"""Narrow update of the one known Scout cost Shadow automation."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib

EXPECTED_ID = "8ef736c9-d945-4e05-9c96-e4ee3879665b"
EXPECTED_NAME = "程程工作台 - Azure 成本每日 Shadow"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scout-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = args.scout_root.resolve()
    store = root / "m-automations" / "automations.json"
    items = json.loads(store.read_text(encoding="utf-8"))
    if len(items) != 1 or items[0].get("id") != EXPECTED_ID or items[0].get("name") != EXPECTED_NAME:
        raise RuntimeError("Refusing update: Scout automation store does not contain exactly the expected cost Shadow")
    item = items[0]
    if item.get("teamsNotify") != "never" or item.get("enabled") is not True:
        raise RuntimeError("Refusing update: safety state changed")
    old = str(item["steps"][0]["prompt"])
    new = old.replace("scripts\\publish_cost_lane.py", "scripts\\publish_cost_lane_v052.py")
    new = new.replace("--workbench-url http://127.0.0.1:8791", "--workbench-url http://127.0.0.1:8792")
    if new == old:
        raise RuntimeError("Expected publisher or Workbench reference not found")
    item["steps"][0]["prompt"] = new
    item["updatedAt"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    store.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PASS: updated {EXPECTED_ID} to versioned evidence publisher; teamsNotify=never preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
