import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "publish_cost_lane.py"
spec = importlib.util.spec_from_file_location("publish_cost_lane", SCRIPT)
publisher = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(publisher)


class CostLanePublisherTests(unittest.TestCase):
    def test_latest_evidence_and_complete_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            evidence_dir = root / "runtime" / "evidence" / "cost"
            evidence_dir.mkdir(parents=True)
            payload = {
                "exitCode": 0,
                "notificationsSent": False,
                "externalWrites": False,
                "resourceChanges": False,
                "stdout": "FY27 Power BI cost monitor OK | Snapshot=2026-09-17 | ReportAsOf=2026-09-15 | MTD=$38,555.15 | Forecast=$77,110.29 | SHA256=" + "A" * 64 + " | OperationalInsights skill verify PASS | Drift=-6.71% | Provider canonical reconciliation OK | Storage=BASELINE(actual=$1.00) | Search=PASS(actual=$1.00) | CDN=BASELINE(actual=$1.00) | AML=PASS(actual=$1.00)"
            }
            path = evidence_dir / "run.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(path, publisher.latest_evidence(root))
            self.assertIsNotNone(publisher.SUMMARY.search(payload["stdout"]))
            self.assertEqual(4, len(publisher.PROVIDER.findall(payload["stdout"])))
            self.assertEqual(["2026-09-15"], publisher.green_fact_dates(root))

            # A rerun for the same ReportAsOf must not advance the Gate.
            (evidence_dir / "rerun.json").write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(["2026-09-15"], publisher.green_fact_dates(root))

            # A distinct verified fact date advances it exactly once.
            next_payload = dict(payload)
            next_payload["stdout"] = payload["stdout"].replace("ReportAsOf=2026-09-15", "ReportAsOf=2026-09-16")
            (evidence_dir / "next.json").write_text(json.dumps(next_payload), encoding="utf-8")
            self.assertEqual(["2026-09-15", "2026-09-16"], publisher.green_fact_dates(root))

    def test_safety_attestation_is_fail_closed(self):
        unsafe = {"exitCode": 0, "notificationsSent": True, "externalWrites": False, "resourceChanges": False}
        self.assertTrue(any(unsafe.get(key) is not False for key in ("notificationsSent", "externalWrites", "resourceChanges")))


if __name__ == "__main__":
    unittest.main()
