#!/usr/bin/env python3
"""Normalize S360 CSV + current/historical tag plans into Workbench findings."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import urllib.request

BUCKETS = ("analysis", "needConfirmation", "canExecute")


def key_for(registry: str, image: str, vulnerability: str, scan_result: str) -> str:
    # Identity follows the underlying finding, not an observation date, tag,
    # digest, cluster, SLA or due date. Those are mutable exposure attributes.
    normalized_result = " ".join(scan_result.lower().split())
    raw = "\x1f".join((registry.lower().rstrip("/"), image.lower().lstrip("/"), vulnerability.lower().strip(), normalized_result))
    return "s360_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def plan_index(path: pathlib.Path) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    current: dict[str, dict] = {}
    by_repo: dict[str, list[dict]] = {}
    for bucket in BUCKETS:
        for item in plan.get(bucket) or []:
            if not isinstance(item, dict):
                continue
            repo = str(item.get("repo") or "")
            if repo:
                by_repo.setdefault(repo, []).append({"date": plan.get("date"), "bucket": bucket, "plan": item})
            for image in item.get("images") or []:
                current[image.lower()] = {"bucket": bucket, "repo": repo, "plan": item}
    # acrPrerequisite and splitEnv are overlays, not primary dispositions.
    for overlay in ("acrPrerequisite", "splitEnv"):
        for item in plan.get(overlay) or []:
            if not isinstance(item, dict):
                continue
            repo = str(item.get("repo") or "")
            for mapped in current.values():
                if mapped.get("repo") == repo:
                    mapped.setdefault("overlays", []).append(overlay)
    return current, by_repo


def history_index(tracking: pathlib.Path, current_repo: set[str], limit: int = 12) -> dict[str, list[dict]]:
    result = {repo: [] for repo in current_repo}
    plans = sorted(tracking.glob("tag-plan-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in plans:
        try:
            _, repos = plan_index(path)
        except (OSError, ValueError, TypeError):
            continue
        for repo in current_repo:
            for entry in repos.get(repo, []):
                if len(result[repo]) < limit:
                    plan = entry["plan"]
                    result[repo].append({
                        "date": entry["date"], "bucket": entry["bucket"], "source": str(path),
                        "mainSha": plan.get("main_sha"), "latestVersion": plan.get("latest_version"),
                        "dockerfileFrom": plan.get("dockerfile_from"), "mismatches": plan.get("kubectl_mismatch") or []
                    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--csv", action="append", required=True, type=pathlib.Path)
    parser.add_argument("--tag-plan", required=True, type=pathlib.Path)
    parser.add_argument("--workbench-url", required=True)
    args = parser.parse_args()
    current, repo_entries = plan_index(args.tag_plan)
    phase3_path = args.tag_plan.parent / f"phase3-summary-{args.date.replace('-', '')}.json"
    if phase3_path.is_file():
        phase3 = json.loads(phase3_path.read_text(encoding="utf-8"))
        for route in phase3.get("dedicatedFlows") or []:
            current[str(route["image"]).lower()] = {
                "bucket": "dedicatedFlow", "repo": "", "plan": {"dedicatedSkill": route["skill"], "images": [route["image"]]}
            }
    history = history_index(args.tag_plan.parent, set(repo_entries))
    findings = []
    for csv_path in args.csv:
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                mapped = current.get(row["Image"].lower(), {})
                repo = mapped.get("repo", "")
                plan = mapped.get("plan", {})
                findings.append({
                    "id": key_for(row["Registry"], row["Image"], row["VulnerabilityName"], row["ScanResult"]),
                    "observedDate": args.date, "registry": row["Registry"], "image": row["Image"],
                    "tags": row["Tag"], "scanDigest": row["ScanDigest"], "sla": row["SLA"],
                    "vulnerabilityCount": int(row["VulnCt"] or 0), "maxCvss": float(row["MaxCVSS"] or 0),
                    "earliestDue": row["EarliestDue"], "lastSeenUtc": row["LastSeen_UTC"],
                    "namespaces": row["K8sNamespace"], "clusters": row["ClusterName"],
                    "vulnerabilityName": row["VulnerabilityName"], "scanResult": row["ScanResult"],
                    "vendorSolution": row["VulnSolution"], "repository": repo,
                    "remediationBucket": mapped.get("bucket", "unmapped"),
                    "remediation": {
                        "repo": repo, "dedicatedSkill": plan.get("dedicatedSkill"), "dockerfilePath": plan.get("dockerfile_path"),
                        "dockerfileFrom": plan.get("dockerfile_from"), "mainSha": plan.get("main_sha"),
                        "latestVersion": plan.get("latest_version"), "securityTagSuffix": json.loads(args.tag_plan.read_text(encoding="utf-8")).get("securityTagSuffix"),
                        "environments": {name: plan.get(name) for name in ("int", "edog", "prod") if plan.get(name)},
                        "mismatches": plan.get("kubectl_mismatch") or [], "overlays": mapped.get("overlays") or [],
                        "businessCommitsPresent": any((plan.get(name) or {}).get("has_biz") for name in ("edog", "prod"))
                    },
                    "history": history.get(repo, []),
                    "source": {"csv": str(csv_path), "tagPlan": str(args.tag_plan)}
                })
    body = json.dumps({"findings": findings}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(args.workbench_url.rstrip("/") + "/api/security-findings/import", data=body, method="POST", headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.load(response)
    print(f"PASS: imported {result['imported']} S360 finding rows into Workbench")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
