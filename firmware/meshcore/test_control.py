import io
import struct
import types
import unittest
from unittest.mock import patch
import control

class ControlTests(unittest.TestCase):
    def args(self, **changes):
        return types.SimpleNamespace(**dict(action='enable', interval=15, channel=1,
                     location=False, private_channel=True, **changes))

    def test_enable_disable_and_query_bytes(self):
        args = self.args()
        self.assertEqual(control.command(args), bytes([224,1,1,0,1,15,0,1]))
        args.action = 'disable'
        self.assertEqual(control.command(args)[2], 0)
        args.action = 'status'
        self.assertEqual(control.command(args), bytes([225,1]))

    def test_private_ack_interval_and_slot(self):
        for key, value in [('private_channel',False),('interval',14),('channel',0)]:
            args = self.args(); setattr(args,key,value)
            with self.assertRaises(ValueError): control.command(args)

    def test_framed_reply_and_rejection(self):
        payload = bytes([224,1,1,0,1,15,0,1])+struct.pack('<I',900)
        port = io.BytesIO(b'boot text'+b'>'+struct.pack('<H',len(payload))+payload)
        result = control.receive(port)
        self.assertTrue(result['enabled']); self.assertEqual(result['next_attempt_in_seconds'],900)
        self.assertNotIn('location', result)
        with self.assertRaises(ValueError): control.receive(io.BytesIO(b'>\x02\x00\x01\x02'))

if __name__ == '__main__': unittest.main()
