import csv,tempfile,unittest
from pathlib import Path
from cost_collector import build_snapshot

class CostCollectorTests(unittest.TestCase):
 def test_reads_named_fields_and_keeps_negative_variance_verified(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=Path(tmp)/'fy27-cost-review'/'monitoring';m.mkdir(parents=True)
   with (m/'pbi-cost-daily-snapshots.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['SnapshotDate','MTDCostUSD','ProjectedMonthUSD','AugustBudgetUSD','VarianceToBudgetUSD']);w.writeheader();w.writerow({'SnapshotDate':'2026-09-17','MTDCostUSD':'38555.15','ProjectedMonthUSD':'77110.29','AugustBudgetUSD':'77968.87','VarianceToBudgetUSD':'-858.58'})
   with (m/'operationalinsights-cost-verification.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['SnapshotDate','Status']);w.writeheader();w.writerow({'SnapshotDate':'2026-09-17','Status':'PASS'})
   r=build_snapshot(Path(tmp));self.assertEqual('verified',r['status']);self.assertEqual('$38.6K',r['metrics'][0]['value']);self.assertIn('-859',r['headline'])
 def test_missing_is_unknown(self):
  with tempfile.TemporaryDirectory() as tmp:self.assertEqual('unknown',build_snapshot(Path(tmp))['status'])
if __name__=='__main__':unittest.main()
