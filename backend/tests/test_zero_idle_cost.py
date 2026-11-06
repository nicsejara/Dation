"""Prevent hidden floor costs and double-counted billing-account credits."""
import importlib.util
from pathlib import Path
import sys
import unittest
spec=importlib.util.spec_from_file_location('zero_idle_cost',Path(__file__).resolve().parents[2]/'scripts/estimate_monthly_cost.py')
cost=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cost;spec.loader.exec_module(cost)
class ZeroIdleCostTests(unittest.TestCase):
    def test_idle_is_not_promised_zero_gross(self):
        r=cost.estimate(cost.Scenario(pilots=0,api_read_requests=0))
        self.assertEqual(r['usage']['recovery_ticks'],2880)
        self.assertAlmostEqual(r['gcp']['gross']['cloud_run_job_cpu']+r['gcp']['gross']['cloud_run_job_ram'],3.2832)
        self.assertEqual(r['gcp']['net_total'],r['gcp']['gross_total'])
    def test_pair_includes_two_separate_sixty_second_tasks(self):
        r=cost.estimate(cost.Scenario(pairs_per_day=1,workdays=1,d1_wall_seconds=1,d2_wall_seconds=1,comparative_per_pair=0))
        self.assertEqual(r['usage']['compute_task_seconds_billed'],120)
    def test_shared_cpu_credit_applied_once_across_api_and_jobs(self):
        r=cost.estimate(cost.Scenario(pilots=10),{'cpu':4.32,'ram':.9})
        applied=r['gcp']['allocated_credits']
        self.assertAlmostEqual(applied['cloud_run_job_cpu']+applied['cloud_run_api_cpu'],4.32)
        with self.assertRaises(ValueError):cost.estimate(cost.Scenario(),{'cpu':8.64})
    def test_retry_startup_and_long_job_sensitivity_increase_gross(self):
        base=cost.estimate(cost.Scenario())
        for s in [cost.Scenario(extra_activation_attempts=2),cost.Scenario(d1_wall_seconds=300,compute_gib=2)]:
            self.assertGreater(cost.estimate(s)['gcp']['gross_total'],base['gcp']['gross_total'])
