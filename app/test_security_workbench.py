import sqlite3
import tempfile
import unittest
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
        return {"id": finding_id, "observedDate": "2026-09-17", "registry": "r", "image": "image", "sla": "Past SLA",
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


if __name__ == "__main__":
    unittest.main()
