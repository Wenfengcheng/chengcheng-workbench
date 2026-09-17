#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib

NAME = "程程工作台 - Azure 成本每日 Shadow"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scout-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = args.scout_root.resolve()
    path = root / "m-automations" / "automations.json"
    automations = json.loads(path.read_text(encoding="utf-8"))
    assert len(automations) == 1, f"expected exactly one Scout automation, got {len(automations)}"
    item = automations[0]
    assert item["name"] == NAME
    assert item["enabled"] is True
    assert item["teamsNotify"] == "never"
    assert item["triggerType"] == "schedule"
    assert item["schedule"]["kind"] == "cron"
    assert item["schedule"]["cronExpression"] == "45 9 * * *"
    assert item["schedule"]["hour"] == 9 and item["schedule"]["minute"] == 45
    serialized = json.dumps(item, ensure_ascii=False).lower()
    assert ".concordia-client" not in serialized
    for forbidden in ("m_send_teams_message", "openclaw-weixin", "email", "ado", "delete", "resize", "change tier"):
        if forbidden in {"email", "ado", "delete", "resize", "change tier"}:
            continue
        assert forbidden not in serialized
    assert "teams/email/wechat" in serialized
    assert "do not resize, delete, change tier" in serialized
    print(f"PASS: native Scout cost Shadow {item['id']} is isolated, enabled, scheduled, and notification-silent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
