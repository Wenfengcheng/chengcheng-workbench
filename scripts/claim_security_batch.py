#!/usr/bin/env python3
"""Atomically claim one approved S360 batch and build an immutable envelope.

Claiming is deliberately not execution. Scout must run the route-specific
security skill, perform live preflight, and bind an exact plan to the envelope
hash before it is allowed to change ADO, Git, AKS, or Azure state.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sqlite3

ALLOWED_BUCKETS = {"canExecute", "needConfirmation", "dedicatedFlow"}
ALLOWED_SKILLS = {
    "container-security-fix", "istio-security-fix", "mise-security-fix",
    "admin-ui-rebuild", "swagger-ui-rebuild",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(value: str, fallback):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def fingerprint(rows: list[sqlite3.Row]) -> str:
    canonical = [{
        "id": row["id"], "repository": row["repository"],
        "scanDigest": row["scan_digest"],
        "remediation": load_json(row["remediation_json"], {}),
    } for row in sorted(rows, key=lambda item: item["id"])]
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_unit(row: sqlite3.Row) -> tuple[str, dict]:
    remediation = load_json(row["remediation_json"], {})
    bucket = row["remediation_bucket"]
    if bucket not in ALLOWED_BUCKETS:
        raise ValueError(f"finding {row['id']} is not executable: {bucket}")
    dedicated = str(remediation.get("dedicatedSkill") or "").strip()
    repository = str(row["repository"] or remediation.get("repo") or "").strip()
    dockerfile = str(remediation.get("dockerfilePath") or "").strip()
    prefix = str(remediation.get("prefix") or "").strip()
    if dedicated:
        if dedicated not in ALLOWED_SKILLS:
            raise ValueError(f"finding {row['id']} requests unapproved skill {dedicated}")
        key = f"skill:{dedicated}:{row['registry'].lower()}/{row['image'].lower()}"
        route = {"type": "dedicated-skill", "skill": dedicated}
    else:
        if not repository or not dockerfile:
            raise ValueError(f"finding {row['id']} lacks repository/Dockerfile routing")
        key = f"repo:{repository}:{dockerfile}:{prefix}"
        route = {"type": "repository", "skill": "container-security-fix",
                 "repository": repository, "dockerfilePath": dockerfile, "tagPrefix": prefix}
    return key, {
        "unitKey": key, "route": route, "disposition": bucket,
        "approvedBaseline": {
            "mainSha": remediation.get("mainSha"),
            "latestVersion": remediation.get("latestVersion"),
            "dockerfileFrom": remediation.get("dockerfileFrom"),
            "environments": remediation.get("environments") or {},
            "mismatches": remediation.get("mismatches") or [],
            "businessCommitsPresent": bool(remediation.get("businessCommitsPresent")),
        },
        "findings": [{
            "id": row["id"], "registry": row["registry"], "image": row["image"],
            "vulnerability": row["vulnerability_name"], "sla": row["sla"],
            "maxCvss": row["max_cvss"], "scanDigest": row["scan_digest"],
            "observedDate": row["observed_date"], "tags": row["tags"],
            "namespaces": row["namespaces"], "clusters": row["clusters"],
        }],
    }


def enqueue(connection: sqlite3.Connection, batch_id: str, stage: str, status: str,
            title: str, message: str, severity: str = "info") -> None:
    timestamp = utc_now()
    event_key = f"{batch_id}:{stage}:{status}"
    event_id = f"secevt_{hashlib.sha256(event_key.encode()).hexdigest()[:24]}"
    connection.execute(
        "INSERT OR IGNORE INTO execution_batch_events(id,batch_id,created_at,stage,status,message,evidence_json,source,event_key) VALUES(?,?,?,?,?,?,'[]','scout-consumer',?)",
        (event_id, batch_id, timestamp, stage, status, message, event_key),
    )
    notification_id = f"teams_{hashlib.sha256(event_key.encode()).hexdigest()[:24]}"
    payload = {"batchId": batch_id, "stage": stage, "status": status}
    connection.execute(
        "INSERT OR IGNORE INTO teams_notification_outbox(id,event_key,created_at,severity,event_type,batch_id,title,message,payload_json,status) VALUES(?,?,?,?,?,?,?,?,?,'pending')",
        (notification_id, event_key, timestamp, severity, "security-batch-progress", batch_id,
         title, message, json.dumps(payload, ensure_ascii=False)),
    )


def claim(db_path: pathlib.Path, evidence_root: pathlib.Path) -> dict:
    db = sqlite3.connect(db_path, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN IMMEDIATE")
        batch = db.execute(
            "SELECT * FROM execution_batches WHERE status='approved_pending_scout' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if not batch:
            db.rollback()
            return {"ok": True, "claimed": False, "message": "No approved S360 batch is waiting."}
        ids = load_json(batch["finding_ids_json"], [])
        if not isinstance(ids, list) or not ids:
            raise ValueError("batch finding list is invalid")
        placeholders = ",".join("?" for _ in ids)
        rows = list(db.execute(f"SELECT * FROM security_findings WHERE id IN ({placeholders})", ids))
        if len(rows) != len(ids):
            raise ValueError("one or more approved findings no longer exist")
        current = fingerprint(rows)
        if current != batch["plan_fingerprint"]:
            result = {"reason": "approval-plan-fingerprint-changed",
                      "approvedFingerprint": batch["plan_fingerprint"],
                      "currentFingerprint": current, "requiresReapproval": True}
            timestamp = utc_now()
            db.execute("UPDATE execution_batches SET status='blocked_stale_approval',updated_at=?,result_json=? WHERE id=?",
                       (timestamp, json.dumps(result, ensure_ascii=False), batch["id"]))
            db.execute(f"UPDATE security_findings SET status='open' WHERE id IN ({placeholders})", ids)
            enqueue(db, batch["id"], "claim", "requires_reapproval", "S360 批次需要重新批准",
                    "批准后的扫描摘要或修复方案已变化；未执行任何修复。", "warning")
            db.commit()
            return {"ok": False, "claimed": False, "batchId": batch["id"], **result}

        units: dict[str, dict] = {}
        for row in rows:
            key, unit = build_unit(row)
            if key in units:
                units[key]["findings"].extend(unit["findings"])
            else:
                units[key] = unit
        timestamp = utc_now()
        expires = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=4)).isoformat().replace("+00:00", "Z")
        envelope = {
            "schemaVersion": "s360-execution-envelope/v1", "batchId": batch["id"],
            "claimedAt": timestamp, "expiresAt": expires,
            "approval": {"planFingerprint": batch["plan_fingerprint"], "note": batch["approval_note"],
                         "requestedBy": batch["requested_by"], "findingIds": ids},
            "remediationUnits": list(units.values()),
            "executionPolicy": {
                "executionAllowed": False,
                "reason": "Scout live preflight and a digest-bound exact plan are required",
                "requiredPreflight": ["current S360 digest", "live Pod image/tag/commit",
                    "repository main SHA", "Dockerfile FROM", "Git tags and build state",
                    "route-specific skill deterministic prechecks"],
                "failClosedOn": ["expired envelope", "digest changed", "main SHA changed",
                    "Pod baseline changed", "Dockerfile changed", "new business commits",
                    "missing credentials or evidence", "mixed or unknown route"],
            },
        }
        raw = json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")
        envelope_hash = hashlib.sha256(raw).hexdigest()
        destination = evidence_root / batch["id"] / "claim-envelope.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(raw)
        result = {"claimEnvelope": str(destination), "claimEnvelopeSHA256": envelope_hash,
                  "unitCount": len(units), "findingCount": len(rows),
                  "nextState": "claimed_pending_live_preflight", "executionStarted": False}
        cursor = db.execute(
            "UPDATE execution_batches SET status='claimed_pending_live_preflight',claimed_at=?,updated_at=?,result_json=? WHERE id=? AND status='approved_pending_scout'",
            (timestamp, timestamp, json.dumps(result, ensure_ascii=False), batch["id"]))
        if cursor.rowcount != 1:
            raise RuntimeError("atomic batch claim failed")
        db.execute(f"UPDATE security_findings SET status='claimed_pending_live_preflight' WHERE id IN ({placeholders})", ids)
        enqueue(db, batch["id"], "claim", "claimed_pending_live_preflight", "S360 修复批次已领取",
                f"Scout 已领取 {len(rows)} 条漏洞、{len(units)} 个修复单元，正在执行实时基线检查。")
        db.commit()
        return {"ok": True, "claimed": True, "batchId": batch["id"], **result}
    except Exception as exc:
        db.rollback()
        return {"ok": False, "claimed": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=pathlib.Path)
    parser.add_argument("--evidence-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    if not args.database.is_file():
        raise RuntimeError(f"Workbench database missing: {args.database}")
    result = claim(args.database.resolve(), args.evidence_root.resolve())
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 3


if __name__ == "__main__":
    raise SystemExit(main())
