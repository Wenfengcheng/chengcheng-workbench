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


def az_json(*args: str):
    result = subprocess.run(["az.cmd", *args], text=True, capture_output=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return json.loads(result.stdout)


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
    missing_modules = [name for name in manifest["runtimePrerequisites"]["pythonModules"] if importlib.util.find_spec(name) is None]
    missing_commands = [name for name in manifest["runtimePrerequisites"]["commands"] if shutil.which(name) is None]
    missing_files = [name for name in manifest["files"] if not (root / name).is_file()]
    problems = []
    if sys.version_info[:2] < minimum: problems.append(f"Python {minimum[0]}.{minimum[1]}+ required")
    if missing_modules: problems.append(f"missing Python modules: {missing_modules}")
    if missing_commands: problems.append(f"missing commands: {missing_commands}")
    if missing_files: problems.append(f"missing package files: {missing_files}")

    checked = []
    if not problems and not args.skip_azure_session_check:
        context = manifest["runtimePrerequisites"]["azureCliContext"]
        checks = [
            ("AzureCloud", context["globalSubscription"]),
            *[("AzureChinaCloud", subscription) for subscription in context["chinaSubscriptions"]],
        ]
        try:
            for cloud, subscription in checks:
                subprocess.run(["az.cmd", "cloud", "set", "--name", cloud], check=True, text=True, capture_output=True, encoding="utf-8")
                subprocess.run(["az.cmd", "account", "set", "--subscription", subscription], check=True, text=True, capture_output=True, encoding="utf-8")
                account = az_json("account", "show", "--query", "{name:name,id:id,environmentName:environmentName}", "-o", "json")
                if account["environmentName"] != cloud:
                    raise RuntimeError(f"Cloud mismatch for {subscription}: {account}")
                checked.append(f"{cloud}/{account['name']}")
        except Exception as exc:
            problems.append(f"Azure CLI login/context unavailable: {exc}")
        finally:
            subprocess.run(["az.cmd", "cloud", "set", "--name", "AzureChinaCloud"], text=True, capture_output=True, encoding="utf-8")
            subprocess.run(["az.cmd", "account", "set", "--subscription", context["chinaSubscriptions"][0]], text=True, capture_output=True, encoding="utf-8")
    if problems:
        print("BLOCKED: " + " | ".join(problems))
        return 3
    print(f"PASS: Scout cost runtime preflight ({len(manifest['files'])} files; host Azure CLI contexts: {', '.join(checked)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
