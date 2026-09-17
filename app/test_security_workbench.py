import sqlite3
import tempfile
import unittest
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import app


class SecurityWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "security.db"
        self.connections = []
        def connect():
            db = sqlite3.connect(self.db_path)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            self.connections.append(db)
            return db
        self.patcher = patch.object(app, "connect", connect)
        self.patcher.start()
        app.init_db()

    def tearDown(self):
        self.patcher.stop()
        for db in self.connections:
            db.close()
        self.tmp.cleanup()

    def finding(self, finding_id="f1", bucket="canExecute", repo="Repo"):
        return {"id": finding_id, "observedDate": "2026-09-17", "registry": "r", "image": f"image-{finding_id}", "sla": "Past SLA",
                "vulnerabilityName": "CVE-X", "maxCvss": 9.8, "repository": repo, "remediationBucket": bucket,
                "remediation": {"repo": repo, "mainSha": "abc", "dockerfilePath": "/Dockerfile"}}

    def test_import_and_batch_approval_are_auditable(self):
        result = app.import_security_findings({"findings": [self.finding()]})
        self.assertEqual(1, result["imported"])
        approved = app.approve_security_batch({"findingIds": ["f1"], "note": "go"})
        self.assertFalse(approved["executionStarted"])
        self.assertEqual("approved_pending_scout", approved["status"])
        state = app.list_security_findings()
        self.assertEqual("approved_pending_scout", state["findings"][0]["status"])
        self.assertEqual(1, len(state["batches"]))

    def test_unmapped_cannot_be_approved(self):
        app.import_security_findings({"findings": [self.finding(bucket="unmapped", repo="")]})
        with self.assertRaises(ValueError):
            app.approve_security_batch({"findingIds": ["f1"]})

    def test_dedicated_skill_can_be_approved(self):
        item = self.finding(bucket="dedicatedFlow", repo="")
        item["remediation"] = {"dedicatedSkill": "swagger-ui-rebuild"}
        app.import_security_findings({"findings": [item]})
        approved = app.approve_security_batch({"findingIds": ["f1"]})
        self.assertEqual("approved_pending_scout", approved["status"])

    def test_second_approval_is_rejected(self):
        app.import_security_findings({"findings": [self.finding()]})
        app.approve_security_batch({"findingIds": ["f1"]})
        with self.assertRaises(ValueError):
            app.approve_security_batch({"findingIds": ["f1"]})

    def test_teams_preview_digest_then_confirmed_approval_is_idempotent(self):
        app.import_security_findings({"findings": [self.finding()]})
        preview = app.remote_control({"command": "查看 f1", "requestId": "teams-preview-1",
            "source": "scout-teams-bot", "conversationType": "personal", "userConfirmed": False})
        self.assertTrue(preview["ok"])
        digest = preview["preview"]["planFingerprint"]
        denied = app.remote_control({"command": "批准漏洞 f1", "requestId": "teams-approve-no-digest",
            "source": "scout-teams-bot", "conversationType": "personal", "userConfirmed": True})
        self.assertFalse(denied["ok"])
        approved = app.remote_control({"command": "批准漏洞 f1", "requestId": "teams-approve-1",
            "source": "scout-teams-bot", "conversationType": "personal", "userConfirmed": True,
            "expectedDigest": digest})
        replay = app.remote_control({"command": "批准漏洞 f1", "requestId": "teams-approve-1",
            "source": "scout-teams-bot", "conversationType": "personal", "userConfirmed": True,
            "expectedDigest": digest})
        self.assertTrue(approved["ok"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(approved["batch"]["batchId"], replay["batch"]["batchId"])

    def test_group_chat_cannot_approve_security(self):
        app.import_security_findings({"findings": [self.finding()]})
        result = app.remote_control({"command": "批准漏洞 f1", "requestId": "teams-group-1",
            "source": "scout-teams-bot", "conversationType": "group", "userConfirmed": True,
            "expectedDigest": "x"})
        self.assertFalse(result["ok"])

    def test_teams_outbox_claim_and_ack_is_idempotent(self):
        app.import_security_findings({"findings": [self.finding()]})
        app.approve_security_batch({"findingIds": ["f1"]})
        claimed = app.claim_teams_notifications()
        self.assertEqual(1, claimed["count"])
        notification_id = claimed["notifications"][0]["id"]
        first = app.acknowledge_teams_notification(notification_id, {"status": "sent", "deliveryId": "m1"})
        replay = app.acknowledge_teams_notification(notification_id, {"status": "sent", "deliveryId": "m1"})
        self.assertTrue(first["ok"])
        self.assertTrue(replay["replayed"])

    def test_recent_teams_claim_is_not_claimed_twice(self):
        app.import_security_findings({"findings": [self.finding()]})
        app.approve_security_batch({"findingIds": ["f1"]})
        self.assertEqual(1, app.claim_teams_notifications()["count"])
        self.assertEqual(0, app.claim_teams_notifications()["count"])

    def test_failed_teams_delivery_is_retried(self):
        app.import_security_findings({"findings": [self.finding()]})
        app.approve_security_batch({"findingIds": ["f1"]})
        notification = app.claim_teams_notifications()["notifications"][0]
        failed = app.acknowledge_teams_notification(notification["id"], {"status": "failed", "error": "temporary"})
        self.assertEqual("pending", failed["status"])
        self.assertEqual(1, app.claim_teams_notifications()["count"])

    def test_claim_consumer_groups_and_blocks_stale_approval(self):
        spec = importlib.util.spec_from_file_location("claim_security_batch", Path(__file__).parents[1] / "scripts" / "claim_security_batch.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app.import_security_findings({"findings": [self.finding("f1"), self.finding("f2")]})
        approved = app.approve_security_batch({"findingIds": ["f1", "f2"]})
        evidence = Path(self.tmp.name) / "evidence"
        result = module.claim(self.db_path, evidence)
        self.assertTrue(result["claimed"])
        self.assertEqual(1, result["unitCount"])
        envelope = json.loads(Path(result["claimEnvelope"]).read_text(encoding="utf-8"))
        self.assertFalse(envelope["executionPolicy"]["executionAllowed"])
        self.assertEqual(2, len(envelope["remediationUnits"][0]["findings"]))

        app.import_security_findings({"findings": [self.finding("f3")]})
        stale = app.approve_security_batch({"findingIds": ["f3"]})
        with app.connect() as db:
            db.execute("UPDATE security_findings SET scan_digest='changed' WHERE id='f3'")
        blocked = module.claim(self.db_path, evidence)
        self.assertFalse(blocked["claimed"])
        self.assertTrue(blocked["requiresReapproval"])
        with app.connect() as db:
            status = db.execute("SELECT status FROM execution_batches WHERE id=?", (stale["batchId"],)).fetchone()["status"]
        self.assertEqual("blocked_stale_approval", status)

    def test_progress_is_idempotent_and_cannot_record_terminal(self):
        spec = importlib.util.spec_from_file_location("claim_security_batch", Path(__file__).parents[1] / "scripts" / "claim_security_batch.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app.import_security_findings({"findings": [self.finding()]})
        approved = app.approve_security_batch({"findingIds": ["f1"]})
        module.claim(self.db_path, Path(self.tmp.name) / "evidence")
        payload = {"stage": "preflight", "eventKey": "preflight-start", "message": "checking", "evidence": ["e1"]}
        first = app.record_execution_batch_progress(approved["batchId"], payload)
        replay = app.record_execution_batch_progress(approved["batchId"], payload)
        self.assertTrue(first["ok"])
        self.assertTrue(replay["replayed"])
        with self.assertRaises(ValueError):
            app.record_execution_batch_progress(approved["batchId"], {**payload, "stage": "verified", "eventKey": "bad"})

    def test_verified_result_requires_complete_evidence(self):
        spec = importlib.util.spec_from_file_location("record_security_batch_result", Path(__file__).parents[1] / "scripts" / "record_security_batch_result.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = {"batchId": "b1", "status": "verified", "finalS360State": "cleared"}
        missing = module.REQUIRED_VERIFIED - set(payload)
        self.assertIn("verificationEvidence", missing)


if __name__ == "__main__":
    unittest.main()
