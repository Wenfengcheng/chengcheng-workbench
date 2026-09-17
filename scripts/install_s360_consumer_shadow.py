#!/usr/bin/env python3
"""Install exactly one disabled Scout S360 consumer Shadow automation."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import uuid

NAME = "程程工作台 - S360 批次消费者 Shadow"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True, type=pathlib.Path)
    parser.add_argument("--workbench-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    store = args.store.resolve()
    root = args.workbench_root.resolve()
    if not root.is_dir() or ".scout" not in str(root).lower():
        raise RuntimeError("consumer must target a Scout-owned Workbench runtime")
    entries = json.loads(store.read_text(encoding="utf-8-sig")) if store.is_file() else []
    if not isinstance(entries, list):
        raise RuntimeError("Scout automation store must be an array")
    if any(item.get("name") == NAME for item in entries if isinstance(item, dict)):
        raise RuntimeError("create-only guard: S360 consumer Shadow already exists")
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    tools = root / "runtime-tools"
    prompt = (
        f"Use the S360 execution consumer contract at {tools / 's360-scout-consumer.json'}. "
        f"The Workbench is http://127.0.0.1:8796 and its database is {root / 'data' / 'daily_flow.db'}. "
        f"Claim with {tools / 'claim_security_batch.py'} and write evidence under {root / 'evidence' / 's360-execution'}. "
        "This automation is a disabled Shadow and must remain no-send/no-execute until explicitly cut over. "
        "Do not claim a real batch, send Teams messages, create tags, trigger or approve builds, change ADO, deploy, or modify Azure/AKS."
    )
    automation = {
        "id": str(uuid.uuid4()), "name": NAME,
        "description": "Disabled contract-only Shadow for digest-bound S360 execution and Teams synchronization.",
        "schedule": {"kind": "interval", "naturalLanguage": "every 5 minutes", "intervalMinutes": 5},
        "steps": [{"id": str(uuid.uuid4()), "label": "S360 consumer contract Shadow", "prompt": prompt}],
        "enabled": False, "oneShot": False, "createdAt": now, "updatedAt": now,
        "triggerType": "schedule", "workingDir": str(root), "skillNames": [], "teamsNotify": "never",
    }
    entries.append(automation)
    store.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "id": automation["id"], "enabled": False,
                      "teamsNotify": "never", "store": str(store)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
