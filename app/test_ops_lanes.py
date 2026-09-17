import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class OpsLaneContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "ops-test.db"
        self.connections = []

        def connect_test_db():
            db = sqlite3.connect(self.db_path)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            self.connections.append(db)
            return db

        self.connect_patch = patch.object(app, "connect", connect_test_db)
        self.connect_patch.start()
        app.init_db()

    def tearDown(self):
        self.connect_patch.stop()
        for db in self.connections:
            db.close()
        self.tmp.cleanup()

    def test_empty_contract_has_all_five_lanes(self):
        result = app.get_ops_lanes()
        self.assertEqual(5, len(result["lanes"]))
        self.assertEqual(
            ["security", "release", "pipeline", "cost", "collaboration"],
            [lane["lane"] for lane in result["lanes"]],
        )
        self.assertTrue(all(lane["status"] == "unknown" for lane in result["lanes"]))

    def test_snapshot_round_trip_preserves_structured_evidence(self):
        saved = app.upsert_ops_lane({
            "lane": "pipeline",
            "status": "blocked",
            "headline": "Build 265397 failed before Helm",
            "summary": "Key Vault endpoint resolution failed; deployment did not start.",
            "metrics": [{"label": "failed", "value": 1}],
            "items": [{"title": "Auth eDog", "status": "blocked"}],
            "evidence": [{"label": "Build", "href": "https://example.invalid/build/265397"}],
            "source": "unit-test",
        })
        self.assertEqual("blocked", saved["status"])
        self.assertEqual(1, saved["metrics"][0]["value"])
        self.assertEqual("Auth eDog", saved["items"][0]["title"])
        self.assertEqual(1, len(saved["evidence"]))

    def test_rejects_unknown_lane_and_status(self):
        with self.assertRaises(ValueError):
            app.upsert_ops_lane({"lane": "sales", "status": "normal"})
        with self.assertRaises(ValueError):
            app.upsert_ops_lane({"lane": "security", "status": "green"})

    def test_rejects_non_array_structured_fields(self):
        with self.assertRaises(ValueError):
            app.upsert_ops_lane({"lane": "cost", "metrics": {"value": 1}})


if __name__ == "__main__":
    unittest.main()
