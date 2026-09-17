#!/usr/bin/env python3
"""Fail-closed result recorder for Scout S360 remediation batches."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sqlite3

TERMINAL = {"verified", "blocked_preflight", "failed", "requires_reapproval"}
REQUIRED_VERIFIED = {"claimEnvelopeSHA256", "executionPlanSHA256", "skill",
                     "preflightEvidence", "executionEvidence", "verificationEvidence", "finalS360State"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=pathlib.Path)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--status", required=True, choices=sorted(TERMINAL))
    parser.add_argument("--result", required=True, type=pathlib.Path)
    args = parser.parse_args()
    payload = json.loads(args.result.read_text(encoding="utf-8"))
    if payload.get("batchId") != args.batch_id or payload.get("status") != args.status:
        raise RuntimeError("result identity/status does not match command")
    if args.status == "verified":
        missing = sorted(REQUIRED_VERIFIED - set(payload))
        if missing:
            raise RuntimeError(f"verified result lacks evidence fields: {missing}")
        if payload.get("finalS360State") != "cleared":
            raise RuntimeError("verified requires finalS360State=cleared")
        for field in ("preflightEvidence", "executionEvidence", "verificationEvidence"):
            if not isinstance(payload.get(field), list) or not payload[field]:
                raise RuntimeError(f"verified requires non-empty {field}")
    result_hash = hashlib.sha256(args.result.read_bytes()).hexdigest()
    db = sqlite3.connect(args.database, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN IMMEDIATE")
        batch = db.execute("SELECT * FROM execution_batches WHERE id=?", (args.batch_id,)).fetchone()
        if not batch:
            raise RuntimeError("batch not found")
        if batch["status"] not in {"claimed_pending_live_preflight", "in_progress"}:
            raise RuntimeError(f"batch state does not accept result: {batch['status']}")
        ids = json.loads(batch["finding_ids_json"])
        placeholders = ",".join("?" for _ in ids)
        stored = {**payload, "resultFile": str(args.result.resolve()), "resultSHA256": result_hash}
        timestamp = now()
        db.execute("UPDATE execution_batches SET status=?,updated_at=?,completed_at=?,result_json=? WHERE id=?",
                   (args.status, timestamp, timestamp, json.dumps(stored, ensure_ascii=False), args.batch_id))
        finding_status = "verified_cleared" if args.status == "verified" else ("open" if args.status == "requires_reapproval" else args.status)
        db.execute(f"UPDATE security_findings SET status=? WHERE id IN ({placeholders})", [finding_status, *ids])
        event_key = f"{args.batch_id}:terminal:{args.status}"
        event_id = f"secevt_{hashlib.sha256(event_key.encode()).hexdigest()[:24]}"
        message = str(payload.get("summary") or payload.get("reason") or args.status)[:1200]
        db.execute("INSERT OR IGNORE INTO execution_batch_events(id,batch_id,created_at,stage,status,message,evidence_json,source,event_key) VALUES(?,?,?,?,?,?,?,?,?)",
                   (event_id, args.batch_id, timestamp, "terminal", args.status, message,
                    json.dumps(payload.get("verificationEvidence") or [], ensure_ascii=False), "scout-consumer", event_key))
        notification_id = f"teams_{hashlib.sha256(event_key.encode()).hexdigest()[:24]}"
        title = "S360 修复已验证" if args.status == "verified" else "S360 修复需要关注"
        severity = "success" if args.status == "verified" else ("warning" if args.status in {"blocked_preflight", "requires_reapproval"} else "error")
        db.execute("INSERT OR IGNORE INTO teams_notification_outbox(id,event_key,created_at,severity,event_type,batch_id,title,message,payload_json,status) VALUES(?,?,?,?,?,?,?,?,?,'pending')",
                   (notification_id, event_key, timestamp, severity, "security-batch-terminal", args.batch_id,
                    title, message, json.dumps(stored, ensure_ascii=False)))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(json.dumps({"ok": True, "batchId": args.batch_id, "status": args.status, "resultSHA256": result_hash}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
