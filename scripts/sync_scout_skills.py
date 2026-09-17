#!/usr/bin/env python3
"""Create-only synchronization of reviewed Chengcheng skills into Microsoft Scout."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil

REPO = pathlib.Path(__file__).resolve().parent.parent
HOME = pathlib.Path.home()
HANDOVER = HOME / ".concordia-client" / "workspace" / "s360-security-automation-handover-20260910" / "skills"
WORKSPACE_SKILLS = HOME / ".concordia-client" / "workspace" / "skills"

SOURCES = {
    "chengcheng-workbench": REPO / "skills" / "chengcheng-workbench",
    "chengcheng-workbench-teams-control": WORKSPACE_SKILLS / "chengcheng-workbench-teams-control",
    "admin-ui-rebuild": HANDOVER / "admin-ui-rebuild",
    "alpine-base-fix": HANDOVER / "alpine-base-fix",
    "cert-manager-security-fix": HANDOVER / "cert-manager-security-fix",
    "container-security-fix": HANDOVER / "container-security-fix",
    "istio-security-fix": HANDOVER / "istio-security-fix",
    "mise-security-fix": HANDOVER / "mise-security-fix",
    "pipeline-approval": HANDOVER / "pipeline-approval",
    "pipeline-retry": HANDOVER / "pipeline-retry",
    "s360-report-reliability": HANDOVER / "s360-report-reliability",
    "security-orchestrator": HANDOVER / "security-orchestrator",
    "security-tag-planner": HANDOVER / "security-tag-planner",
    "security-verify": HANDOVER / "security-verify",
    "swagger-ui-rebuild": HANDOVER / "swagger-ui-rebuild",
    "vulnerability-reporting-vnext": HANDOVER / "vulnerability-reporting-vnext",
}

BLOCKED_MARKER = "SCOUT-COMPATIBILITY.md"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=pathlib.Path, default=HOME / ".scout" / "skills")
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    installed = []
    for name, source in SOURCES.items():
        if not (source / "SKILL.md").is_file():
            raise RuntimeError(f"missing reviewed source skill: {name}: {source}")
        target = destination / name
        if target.exists():
            raise RuntimeError(f"create-only guard: Scout skill already exists: {target}")
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        skill_file = target / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8-sig")
        text = text.replace("$env:USERPROFILE\\.concordia-client\\skills", "$env:USERPROFILE\\.scout\\skills")
        text = text.replace("~/.concordia-client/skills", "~/.scout/skills")
        text = text.replace("C:\\Users\\j-wenfengc\\.concordia-client\\skills", "$env:USERPROFILE\\.scout\\skills")
        skill_file.write_text(text, encoding="utf-8")
        compatibility = {
            "skill": name,
            "runtime": "Microsoft Scout",
            "status": "installed-shadow" if name not in {"chengcheng-workbench", "chengcheng-workbench-teams-control"} else "installed",
            "executionDefault": "read-only/create-only",
            "rules": [
                "Do not invoke OpenClaw commands, cron, sessions, memory, or messaging.",
                "Do not use any .concordia-client path at runtime.",
                "Use Scout Runtime paths and the Workbench Teams outbox.",
                "Any ADO/tag/build/deploy/cloud write requires the immutable Workbench batch and live preflight.",
                "If a referenced script still contains a legacy path or OpenClaw command, fail closed and report blocked; do not execute it.",
            ],
        }
        (target / BLOCKED_MARKER).write_text(json.dumps(compatibility, ensure_ascii=False, indent=2), encoding="utf-8")
        files = sorted(p for p in target.rglob("*") if p.is_file())
        installed.append({"name": name, "path": str(target), "files": len(files),
                          "skillSha256": sha256(skill_file), "status": compatibility["status"]})
    manifest = {"schemaVersion": 1, "runtimeOwner": "Microsoft Scout", "mode": "create-only",
                "skills": installed, "count": len(installed)}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "count": len(installed), "manifest": str(args.manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
