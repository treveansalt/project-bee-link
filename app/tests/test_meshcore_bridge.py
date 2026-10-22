import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error

from meshcore_bridge import MeshCoreService, radio_settings, transmit
from server import Handler, Store, ThreadingHTTPServer


def snapshot():
    return {'signals': {'soc_pct': {'value': 65, 'confidence': 'verified',
            'source': 'can', 'timestamp': datetime.now(timezone.utc).isoformat()}}}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.time = 0
        self.messages = []
        self.store = types.SimpleNamespace(snapshot=lambda device: snapshot())
        self.service = MeshCoreService(self.store, sender=self.send, clock=lambda:self.time, jitter=lambda:0)

    def send(self, message, permitted):
        if permitted():
            self.messages.append(message)
            return 'submitted'
        return 'cancelled'

    def test_disabled_and_first_delay(self):
        self.time=10000;self.service.poll();self.assertFalse(self.messages)
        self.service.configure({'enabled':True})
        self.time+=899;self.service.poll();self.assertFalse(self.messages)
        self.time+=1;self.service.poll();self.assertEqual(len(self.messages),1)

    def test_no_catchup_burst_and_failure_throttle(self):
        self.service.configure({'enabled':True})
        self.time=100000;self.service.poll();self.service.poll()
        self.assertEqual(len(self.messages),1)
        self.service.sender=lambda *args: (_ for _ in ()).throw(RuntimeError('sensitive error'))
        self.time+=900;self.service.poll();self.service.poll()
        self.assertNotIn('sensitive',self.service.status()['status'])
        self.assertEqual(self.service.status()['next_attempt_in_seconds'],900)

    def test_skip_empty_data_and_disable(self):
        self.store.snapshot=lambda device:{'signals':{}}
        self.service.configure({'enabled':True});self.time=900;self.service.poll()
        self.assertFalse(self.messages)
        self.assertIn('skipped',self.service.status()['status'])
        self.service.configure({'enabled':False});self.time=99999;self.service.poll()
        self.assertFalse(self.messages)

    def test_disable_cancels_pending_submission(self):
        def sending(message, permitted):
            self.service.configure({'enabled':False})
            return self.send(message,permitted)
        self.service.sender=sending
        self.service.configure({'enabled':True});self.time=900;self.service.poll()
        self.assertFalse(self.messages);self.assertEqual(self.service.status()['status'],'disabled')

    def test_settings_bounds(self):
        for body in [{'interval_minutes':1},{'interval_minutes':True},{'enabled':'yes'},
                     {'include_location':1},{'device':'../x'},{'sender':'x'}]:
            with self.assertRaises(ValueError):self.service.configure(body)
        self.assertFalse(self.service.status()['enabled'])

    def test_location_optin_and_restart(self):
        now=datetime.now(timezone.utc).isoformat()
        self.store.snapshot=lambda device:{'signals':{key:{'value':value,'confidence':'verified','timestamp':now}
            for key,value in [('latitude',51),('longitude',-1)]}}
        self.service.configure({'enabled':True});self.time=900;self.service.poll()
        self.assertFalse(self.messages)
        self.service.configure({'include_location':True});self.time+=900;self.service.poll()
        self.assertEqual(len(self.messages),1)
        fresh=MeshCoreService(self.store,sender=self.send)
        self.assertFalse(fresh.status()['enabled']);self.assertFalse(fresh.status()['include_location'])


class RadioTests(unittest.TestCase):
    def test_channel_transports_refresh_and_cancel(self):
        calls=[]
        event=types.SimpleNamespace(OK='ok')
        async def send(channel,message):calls.append((channel,message));return types.SimpleNamespace(type='ok')
        async def disconnect():calls.append('disconnect')
        radio=types.SimpleNamespace(commands=types.SimpleNamespace(send_chan_msg=send),disconnect=disconnect)
        async def connect(*args,**kwargs):calls.append(('connect',args));return radio
        fake=types.SimpleNamespace(MeshCore=types.SimpleNamespace(create_tcp=connect,create_ble=connect),EventType=event)
        with patch.dict('sys.modules',{'meshcore':fake}):
            for transport in ['tcp','ble']:
                calls.clear()
                config={'transport':transport,'address':'fake','port':4000,'channel':1}
                self.assertEqual(asyncio.run(transmit(config,lambda:'fresh',lambda:True)),'submitted')
                self.assertIn((1,'fresh'),calls);self.assertEqual(calls[-1],'disconnect')
                calls.clear()
                self.assertIn('skipped',asyncio.run(transmit(config,lambda:None,lambda:True)))
                self.assertEqual(len(calls),2)
                calls.clear()
                self.assertEqual(asyncio.run(transmit(config,lambda:'fresh',lambda:False)),'cancelled')
                self.assertEqual(len(calls),2)

    def test_explicit_private_destination(self):
        with patch.dict(os.environ,{'BEELINK_MESHCORE_ADDRESS':'/dev/ttyUSB0'},clear=True):
            with self.assertRaises(ValueError):radio_settings()
            with patch.dict(os.environ,{'BEELINK_MESHCORE_CONTACT':'a'*64}):
                self.assertEqual(radio_settings()['contact'],'a'*64)
            with patch.dict(os.environ,{'BEELINK_MESHCORE_CHANNEL':'0','BEELINK_MESHCORE_PRIVATE_CHANNEL':'1'}):
                with self.assertRaises(ValueError):radio_settings()

    def test_adapter_submission_is_not_delivery_and_disconnects(self):
        calls=[]
        event=types.SimpleNamespace(CONTACTS='contacts',MSG_SENT='sent',OK='ok')
        async def contacts():return types.SimpleNamespace(type='contacts',payload={'a'*64:{'public_key':'a'*64}})
        async def send(contact,message):calls.append(message);return types.SimpleNamespace(type='sent')
        async def disconnect():calls.append('disconnect')
        radio=types.SimpleNamespace(commands=types.SimpleNamespace(get_contacts=contacts,send_msg=send),disconnect=disconnect)
        async def connect(*args,**kwargs):return radio
        fake=types.SimpleNamespace(MeshCore=types.SimpleNamespace(create_serial=connect),EventType=event)
        with patch.dict('sys.modules',{'meshcore':fake}):
            result=asyncio.run(transmit({'transport':'serial','address':'fake','contact':'a'*64},lambda:'test',lambda:True))
        self.assertEqual(result,'submitted');self.assertEqual(calls,['test','disconnect'])


class ApiTests(unittest.TestCase):
    def test_controls_require_auth_and_same_origin(self):
        with tempfile.TemporaryDirectory() as temp:
            srv=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            srv.token='test-token';srv.store=Store(Path(temp)/'test.sqlite')
            srv.meshcore=MeshCoreService(srv.store,sender=lambda *args:'submitted',jitter=lambda:0)
            thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
            url=f'http://127.0.0.1:{srv.server_port}/api/meshcore'
            try:
                for headers in [{},{'Authorization':'Bearer test-token','Origin':'http://evil.invalid'}]:
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        urllib.request.urlopen(urllib.request.Request(url,data=b'{"enabled":true}',headers=headers))
                    self.assertIn(error.exception.code,{401,403})
                req=urllib.request.Request(url,data=b'{"enabled":true}',headers={'Authorization':'Bearer test-token'})
                with urllib.request.urlopen(req) as response:state=json.load(response)
                self.assertTrue(state['enabled']);self.assertGreaterEqual(state['next_attempt_in_seconds'],900)
                self.assertIsNone(state['last_submission'])
            finally:srv.meshcore.close();srv.shutdown();srv.server_close();thread.join()
