#!/usr/bin/env python3
"""Fail-closed preflight for the Scout-owned Azure cost runtime package."""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True, type=pathlib.Path)
    parser.add_argument("--skip-azure-session-check", action="store_true")
    args = parser.parse_args()
    root = args.package_root.resolve()
    if ".concordia-client" in str(root).lower():
        raise RuntimeError("Scout package must not run from .concordia-client")
    manifest_path = root / "package-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"Package manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    minimum = tuple(int(x) for x in manifest["runtimePrerequisites"]["pythonMinimum"].split("."))
    if sys.version_info[:2] < minimum:
        raise RuntimeError(f"Python {minimum[0]}.{minimum[1]}+ required")
    missing_modules = [name for name in manifest["runtimePrerequisites"]["pythonModules"] if importlib.util.find_spec(name) is None]
    missing_commands = [name for name in manifest["runtimePrerequisites"]["commands"] if shutil.which(name) is None]
    missing_files = [name for name in manifest["files"] if not (root / name).is_file()]
    missing_profiles = [name for name in manifest["runtimePrerequisites"]["azureProfiles"] if not (root / name).is_file()]
    problems = []
    if missing_modules: problems.append(f"missing Python modules: {missing_modules}")
    if missing_commands: problems.append(f"missing commands: {missing_commands}")
    if missing_files: problems.append(f"missing package files: {missing_files}")
    if missing_profiles: problems.append(f"missing Scout-owned Azure profiles: {missing_profiles}")

    if not missing_profiles and not args.skip_azure_session_check:
        az_command = manifest["runtimePrerequisites"]["commands"][0]
        for profile in manifest["runtimePrerequisites"]["azureProfiles"]:
            config_dir = (root / profile).parent
            result = subprocess.run(
                [az_command, "account", "show", "-o", "none"],
                env={**__import__("os").environ, "AZURE_CONFIG_DIR": str(config_dir)},
                text=True, capture_output=True, encoding="utf-8"
            )
            if result.returncode != 0:
                problems.append(f"Azure session unavailable for {config_dir}")
    if problems:
        print("BLOCKED: " + " | ".join(problems))
        return 3
    print(f"PASS: Scout cost runtime preflight ({len(manifest['files'])} files, isolated profiles, no OpenClaw path)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
