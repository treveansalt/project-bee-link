"""Capture boundaries and sequence holes are facts, not inferred riding metrics."""
import sqlite3
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capture_summary import capture_summaries


class CaptureSummaryTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE samples (device_id TEXT, capture_id TEXT, sequence INTEGER, timestamp TEXT, UNIQUE(device_id,capture_id,sequence))')
        self.addCleanup(self.db.close)

    def add(self, capture, sequence, second=0, device='bike'):
        self.db.execute('INSERT INTO samples VALUES (?,?,?,?)',
                        (device,capture,sequence,f'2026-10-12T10:00:{second:02d}.123456Z'))

    def test_empty(self):
        self.assertEqual(capture_summaries(self.db,'bike'),[])

    def test_device_isolation_and_parameterization(self):
        self.add('shared',1,device='bike')
        self.add('shared',90,device='other')
        self.add('shared',45,device="' OR 1=1 --")
        rows=capture_summaries(self.db,'bike')
        self.assertEqual(rows[0]['sample_count'],1)
        self.assertEqual(rows[0]['first_sequence'],1)
        self.assertEqual(capture_summaries(self.db,"' OR 1=1 --")[0]['first_sequence'],45)
        self.assertEqual(capture_summaries(self.db,'unknown'),[])

    def test_reordered_timestamps_and_sparse_nonzero_sequence(self):
        self.add('ride',12,1)
        self.add('ride',10,4)
        self.add('ride',15,2)
        row=capture_summaries(self.db,'bike')[0]
        self.assertEqual(row,dict(capture_id='ride',sample_count=3,
            first_timestamp='2026-10-12T10:00:01.123456Z',last_timestamp='2026-10-12T10:00:04.123456Z',
            first_sequence=10,last_sequence=15,duration_seconds=3,missing_sequences=3))

    def test_single_sample_and_both_row_factories(self):
        self.add('single',100)
        tuple_result=capture_summaries(self.db,'bike')
        self.db.row_factory=sqlite3.Row
        self.assertEqual(capture_summaries(self.db,'bike'),tuple_result)
        self.assertEqual(tuple_result[0]['duration_seconds'],0)
        self.assertEqual(tuple_result[0]['missing_sequences'],0)

    def test_microsecond_duration(self):
        self.add('precision',1)
        self.db.execute('INSERT INTO samples VALUES (?,?,?,?)',('bike','precision',2,'2026-10-12T10:00:00.123457Z'))
        self.assertAlmostEqual(capture_summaries(self.db,'bike')[0]['duration_seconds'],0.000001,places=9)

    def test_sort_and_limits(self):
        self.add('older',0,1)
        self.add('z',0,5)
        self.add('a',0,5)
        self.assertEqual([r['capture_id'] for r in capture_summaries(self.db,'bike')],['a','z','older'])
        self.assertEqual(len(capture_summaries(self.db,'bike',0)),1)
        self.assertEqual(len(capture_summaries(self.db,'bike',2)),2)
        for i in range(105):self.add(f'extra-{i:03d}',0,6)
        self.assertEqual(len(capture_summaries(self.db,'bike',999)),100)

    def test_summary_does_not_write(self):
        self.add('ride',1)
        self.db.execute('PRAGMA query_only=ON')
        self.assertEqual(capture_summaries(self.db,'bike')[0]['sample_count'],1)


if __name__ == '__main__':
    unittest.main()
