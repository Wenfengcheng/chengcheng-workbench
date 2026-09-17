import json
import tempfile
import unittest
from pathlib import Path

from s360_collector import build_snapshot


class S360CollectorTests(unittest.TestCase):
    def test_builds_attention_snapshot_from_latest_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracking = Path(tmp) / "s360-tracking"
            tracking.mkdir()
            (tracking / "analysis-20260917.json").write_text(json.dumps({
                "date": "2026-09-17",
                "registries": {"officeplusRows": 72, "creatorRows": 60,
                    "officeplusSla": {"Past SLA": 7, "Near SLA": 9},
                    "creatorSla": {"Near SLA": 29}},
                "changes": {"vulnAdded": [], "vulnCleared": [{"image": "finance.ui"}],
                    "slaChanges": [{"image": "storage.api", "to": "Near SLA", "due": "2026-09-25"}]}
            }), encoding="utf-8")
            (tracking / "phase3-summary-20260917.json").write_text(json.dumps({
                "status": "PASS", "unmappedImages": [], "tagPlan": "tag-plan.json"
            }), encoding="utf-8")
            result = build_snapshot(Path(tmp))
            self.assertEqual("security", result["lane"])
            self.assertEqual("attention", result["status"])
            self.assertEqual(132, result["metrics"][0]["value"])
            self.assertEqual(7, result["metrics"][1]["value"])
            self.assertEqual(3, len(result["evidence"]))

    def test_missing_analysis_is_explicit_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_snapshot(Path(tmp))
            self.assertEqual("unknown", result["status"])
            self.assertIn("未找到", result["headline"])


if __name__ == "__main__":
    unittest.main()
