#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import py_compile
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
manifest = json.loads((ROOT / "runtime" / "cost-package-manifest.json").read_text(encoding="utf-8"))
assert manifest["runtimeOwner"] == "Microsoft Scout"
assert manifest["shadowPolicy"]["notifications"] is False
assert manifest["shadowPolicy"]["externalWrites"] is False
assert manifest["shadowPolicy"]["resourceChanges"] is False
assert all(".concordia-client" not in item.lower() for item in manifest["files"])
assert all("azure-config" not in item.lower() for item in manifest["files"])
assert len(manifest["runtimePrerequisites"]["azureProfiles"]) == 3
for relative in ("scripts/package_cost_runtime.py", "scripts/preflight_cost_runtime.py", "jobs/cost-daily-shadow.py"):
    py_compile.compile(str(ROOT / relative), doraise=True)
text = (ROOT / "jobs" / "cost-daily-shadow.ps1").read_text(encoding="utf-8")
assert "preflight_cost_runtime.py" in text and "cost-daily-shadow.py" in text
with tempfile.TemporaryDirectory() as tmp:
    destination = pathlib.Path(tmp) / "probe"
    assert not destination.exists()
print(f"PASS: cost runtime package policy and {len(manifest['files'])} source entries validated")
