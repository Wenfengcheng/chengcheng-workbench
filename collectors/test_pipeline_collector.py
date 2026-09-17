import json
import tempfile
import unittest
from pathlib import Path

from pipeline_collector import build_snapshot


class PipelineCollectorTests(unittest.TestCase):
    def test_non_retryable_failure_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracking = Path(tmp) / "s360-tracking"
            tracking.mkdir()
            artifact = tracking / "weekly-build-2026-09-14.json"
            artifact.write_text(json.dumps({
                "completedAt": "2026-09-14T10:45:59Z",
                "totalRetried": 0,
                "finalStatus": {"succeededCount": 22, "failedCount": 1, "inProgressCount": 0},
                "finalFailed": [{"id": 269035, "pipeline": "OfficePlus.Template.API.Job"}],
                "nonRetryable": [{"buildId": 269035, "failedTask": "Build"}],
            }), encoding="utf-8")
            result = build_snapshot(Path(tmp))
            self.assertEqual("blocked", result["status"])
            self.assertEqual(22, result["metrics"][0]["value"])
            self.assertEqual("blocked", result["items"][0]["status"])
            self.assertIn("禁止自动重试", result["items"][0]["nextAction"])

    def test_all_success_is_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracking = Path(tmp) / "s360-tracking"
            tracking.mkdir()
            (tracking / "weekly-build-2026-09-14.json").write_text(json.dumps({
                "finalStatus": {"succeededCount": 23, "failedCount": 0, "inProgressCount": 0}
            }), encoding="utf-8")
            result = build_snapshot(Path(tmp))
            self.assertEqual("verified", result["status"])
            self.assertIn("23", result["headline"])

    def test_missing_artifact_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_snapshot(Path(tmp))
            self.assertEqual("unknown", result["status"])


if __name__ == "__main__":
    unittest.main()
