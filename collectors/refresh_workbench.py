"""Run all read-only Chengcheng Workbench collectors once."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline_collector import build_snapshot as pipeline_snapshot
from pipeline_collector import post_snapshot
from release_collector import build_snapshot as release_snapshot
from s360_collector import build_snapshot as s360_snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--app-url", default="http://127.0.0.1:8787")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    snapshots = [
        s360_snapshot(args.workspace),
        release_snapshot(args.workspace),
        pipeline_snapshot(args.workspace),
    ]
    results = snapshots if args.dry_run else [post_snapshot(args.app_url, snapshot) for snapshot in snapshots]
    print(json.dumps({"ok": True, "readOnly": True, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
