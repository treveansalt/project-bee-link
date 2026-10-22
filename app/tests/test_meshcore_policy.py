from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest

from meshcore_policy import format_telemetry


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
        self.data = {'signals': {key: {'value': value, 'timestamp': self.now.isoformat(),
                                     'confidence': 'verified', 'source': 'mixed'}
            for key, value in [('soc_pct', 65), ('speed_kmh', 12.3), ('latitude', 51), ('longitude', -1)]}}

    def format(self, data=None, **kwargs):
        return format_telemetry(self.data if data is None else data, now=self.now, **kwargs)

    def test_privacy_and_compact_message(self):
        self.assertEqual(self.format(), 'Bee-Link 12:00Z BAT 65% SPD 12.3km/h')
        msg = self.format(include_location=True)
        self.assertEqual(msg, 'Bee-Link 12:00Z BAT 65% SPD 12.3km/h GPS 51.0000,-1.0000')
        self.assertLessEqual(len(msg.encode('ascii')), 120)
        self.assertNotIn('GPS', self.format(include_location=1))

    def test_capture_freshness_not_upload_time(self):
        for seconds in [-61, 1]:
            data = deepcopy(self.data)
            for item in data['signals'].values():
                item['timestamp'] = (self.now+timedelta(seconds=seconds)).isoformat()
            data['received_at'] = self.now.isoformat()
            self.assertIsNone(self.format(data, include_location=True))
        self.data['signals']['soc_pct']['timestamp'] = (self.now-timedelta(seconds=60)).isoformat()
        self.assertIn('BAT 65%', self.format())

    def test_partial_fields_never_substitute_zero(self):
        self.data['signals']['soc_pct']['timestamp'] = (self.now-timedelta(seconds=70)).isoformat()
        self.assertEqual(self.format(), 'Bee-Link 12:00Z SPD 12.3km/h')
        self.assertIsNone(self.format({'signals': {}}))
        self.assertIsNone(self.format({'signals': {'latitude': self.data['signals']['latitude']}}))

    def test_provisional_simulated_and_replayed(self):
        for source in ['demo', 'simulated', 'replay']:
            data = deepcopy(self.data); data['source'] = source
            self.assertIsNone(self.format(data, include_location=True))
            data.pop('source')
            for item in data['signals'].values(): item['source'] = source
            self.assertIsNone(self.format(data, include_location=True))
        for confidence in ['provisional', 'simulated', None]:
            data = deepcopy(self.data)
            for item in data['signals'].values(): item['confidence'] = confidence
            self.assertIsNone(self.format(data, include_location=True))

    def test_numeric_validation(self):
        for value in [True, False, float('nan'), float('inf'), -1, 101, '65', 10**500]:
            data = {'signals': {'soc_pct': {**self.data['signals']['soc_pct'], 'value': value}}}
            self.assertIsNone(self.format(data))
        for value in [0, 100]:
            self.data['signals']['soc_pct']['value'] = value
            self.assertIn('BAT '+str(value)+'%', self.format())
        self.data['signals']['speed_kmh']['value'] = 251
        self.assertNotIn('SPD', self.format())

    def test_timestamp_formats_and_unzoned(self):
        for stamp in ['2026-10-13T12:00:00', 'bad', None]:
            data = {'signals': {'soc_pct': {**self.data['signals']['soc_pct'], 'timestamp': stamp}}}
            self.assertIsNone(self.format(data))
        for stamp in ['2026-10-13T12:00:00Z', '2026-10-13T13:00:00+01:00']:
            self.data['signals']['soc_pct']['timestamp'] = stamp
            self.assertIn('BAT 65%', self.format())

    def test_coordinate_pair_bounds_and_time(self):
        for key, value in [('latitude', 91), ('longitude', 181)]:
            data = deepcopy(self.data); data['signals'][key]['value'] = value
            self.assertNotIn('GPS', self.format(data, include_location=True))
        self.data['signals']['longitude']['timestamp'] = (self.now-timedelta(seconds=6)).isoformat()
        self.assertNotIn('GPS', self.format(include_location=True))
        self.data['signals']['longitude']['timestamp'] = (self.now-timedelta(seconds=5)).isoformat()
        self.assertIn('GPS', self.format(include_location=True))

    def test_invalid_policy_parameters(self):
        for age in [True, 0, -1, 60.0]: self.assertIsNone(self.format(max_age_seconds=age))
        self.assertIsNone(format_telemetry(self.data, now=self.now.replace(tzinfo=None)))
