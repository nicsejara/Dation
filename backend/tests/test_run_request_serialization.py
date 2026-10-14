import json
import unittest

from app.routes.dispatch import RunRequest


class SchedulingAdmissionSerializationTests(unittest.TestCase):
    def request(self, configuration):
        return RunRequest.model_validate({
            'orders_dataset_id': '00000000-0000-4000-8000-000000000001',
            'fleet_dataset_id': '00000000-0000-4000-8000-000000000002',
            'source_run_id': '00000000-0000-4000-8000-000000000004',
            'decision_case': {'case_id': '00000000-0000-4000-8000-000000000003',
                              'node_id': 'logistics_scheduling'},
            'configuration': configuration,
        })

    def test_global_planning_dates_are_json_safe_for_durable_admission(self):
        request = self.request({'strategy': 'service_first', 'planning_window_start': '2026-09-01',
                                'planning_window_end': '2026-09-02'})
        encoded = json.loads(json.dumps({'configuration': request.configuration, 'options': request.options}))
        self.assertEqual(encoded['configuration']['planning_window_start'], '2026-09-01')
        self.assertEqual(encoded['configuration']['planning_window_end'], '2026-09-02')
        self.assertEqual(encoded['configuration']['strategy'], 'service_first')

    def test_focus_rule_dates_are_json_safe_and_keep_the_same_intention(self):
        rule = {'id': 'TR-TEST', 'field': 'destination', 'values': ['Cordoba'], 'action': 'window',
                'planning_window_start': '2026-10-01', 'planning_window_end': '2026-10-03'}
        request = self.request({'temporal_rules': [rule]})
        config = json.loads(json.dumps(request.configuration))
        self.assertEqual(config['temporal_rules'], [rule])

    def test_automatic_window_still_uses_null_dates(self):
        request = self.request({'strategy': 'earliest_dispatch'})
        config = json.loads(json.dumps(request.configuration))
        self.assertIsNone(config['planning_window_start'])
        self.assertIsNone(config['planning_window_end'])
