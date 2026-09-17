#!/usr/bin/env python3
"""Create an independent Scout cost-monitor package without copying credentials."""
from __future__ import annotations

import argparse
import fnmatch
import json
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
MANIFEST = REPO / "runtime" / "cost-package-manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=pathlib.Path)
    parser.add_argument("--destination-root", required=True, type=pathlib.Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    source = args.source_root.resolve()
    destination = args.destination_root.resolve()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if ".concordia-client" in str(destination).lower():
        raise RuntimeError("Scout package destination must not be under .concordia-client")
    if destination.exists():
        raise RuntimeError(f"Create-only guard: destination already exists: {destination}")

    forbidden = [str(item).lower() for item in manifest["neverPackage"]]
    resolved: list[tuple[pathlib.Path, pathlib.Path]] = []
    for relative_text in manifest["files"]:
        relative = pathlib.Path(relative_text)
        lowered = relative.as_posix().lower()
        if any(part in lowered or fnmatch.fnmatch(relative.name.lower(), part) for part in forbidden):
            raise RuntimeError(f"Manifest includes forbidden path: {relative}")
        src = source / relative
        if not src.is_file():
            raise RuntimeError(f"Required package source is missing: {src}")
        resolved.append((src, relative))

    print(f"VALID: {len(resolved)} credential-free files; destination={destination}")
    if args.validate_only:
        return 0

    destination.mkdir(parents=True, exist_ok=False)
    for src, relative in resolved:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    for relative_text in manifest["generatedDirectories"]:
        (destination / relative_text).mkdir(parents=True, exist_ok=True)
    (destination / "package-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"CREATED: Scout cost package at {destination}; uses host Azure CLI login with explicit cloud/account selection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
