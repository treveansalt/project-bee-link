import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Handler, Store, ThreadingHTTPServer, validate_sample
from mqtt_bridge import discovery, eligible


def fixture(sequence=1, timestamp=None, signals=None, frames=None):
    return {"schema_version": 1, "device_id": "test-bike", "capture_id": "test-capture",
            "sequence": sequence, "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "source": "can", "variant": "test-only", "decoder_version": "external-test-decoder",
            "signals": signals if signals is not None else {"pack_voltage_v": {"value": 72.0, "confidence": "provisional", "evidence": "Test fixture, not Ultra Bee evidence"}},
            "frames": frames or []}


class LoggerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "log.sqlite")

    def tearDown(self):
        self.temp.cleanup()

    def test_commit_retry_and_reopen(self):
        s = fixture()
        self.assertEqual(self.store.ingest([s])[0]["status"], "stored")
        self.assertEqual(self.store.ingest([s])[0]["status"], "duplicate")
        reopened = Store(self.store.path)
        self.assertEqual(reopened.snapshot("test-bike")["sample_count"], 1)
        self.assertEqual(reopened.snapshot("test-bike")["signals"]["pack_voltage_v"]["value"], 72)

    def test_conflicting_retry_rolls_back_whole_batch(self):
        original = fixture()
        self.store.ingest([original])
        conflict = copy.deepcopy(original); conflict["signals"]["pack_voltage_v"]["value"] = 73
        with self.assertRaises(ValueError):
            self.store.ingest([fixture(sequence=2), conflict])
        self.assertEqual(self.store.snapshot("test-bike")["sample_count"], 1)

    def test_late_upload_does_not_refresh_older_signal(self):
        now = datetime.now(timezone.utc)
        older = now - timedelta(hours=3)
        self.store.ingest([fixture(timestamp=now.isoformat())])
        self.store.ingest([fixture(sequence=2, timestamp=older.isoformat(), signals={"pack_voltage_v": {"value": 70, "confidence": "provisional", "evidence": "Old fixture"},
                                  "battery_temp_c": {"value": 24, "confidence": "provisional", "evidence": "Old fixture"}})])
        snap = self.store.snapshot("test-bike")
        self.assertEqual(snap["signals"]["pack_voltage_v"]["value"], 72)
        self.assertEqual(snap["signals"]["battery_temp_c"]["timestamp"], older.isoformat(timespec="microseconds").replace("+00:00", "Z"))
        self.assertNotEqual(snap["received_at"], snap["signals"]["battery_temp_c"]["timestamp"])

    def test_unknown_frames_and_formats_are_preserved(self):
        frames = [{"id": 0x321, "extended": False, "dlc": 2, "data": "0102"},
                  {"id": 0x321, "extended": True, "dlc": 2, "data": "0304"}]
        self.store.ingest([fixture(signals={}, frames=frames)])
        rows = list(self.store.export("test-bike"))
        self.assertEqual(len(rows[0]["frames"]), 2)
        self.assertEqual(rows[0]["signals"], {})
        self.assertEqual([f["extended"] for f in rows[0]["frames"]], [False, True])

    def test_bad_samples_reject_atomically(self):
        cases = []
        for key, val in [("timestamp", "2026-10-10T00:00:00"), ("source", "demo"), ("sequence", True),
                         ("timestamp", (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())]:
            s = fixture(); s[key] = val; cases.append(s)
        s=fixture();s["signals"]["pack_voltage_v"]["value"]=float("nan");cases.append(s)
        s=fixture(signals={},frames=[{"id":2048,"extended":False,"dlc":1,"data":"00"}]);cases.append(s)
        s=fixture(signals={},frames=[{"id":1,"extended":False,"dlc":2,"data":"00"}]);cases.append(s)
        for sample in cases:
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                self.store.ingest([fixture(sequence=10), sample])
        self.assertEqual(self.store.devices(), [])

    def test_variant_scoped_signed_decoder(self):
        self.store.profile={"version":"test-profile-v1","variant":"test-only","signals":[
            {"id":0x321,"extended":False,"key":"pack_current_a","start_byte":0,"length_bytes":2,
             "byte_order":"little","signed":True,"scale":0.1,"offset":0,"confidence":"provisional","evidence":"Test fixture"}]}
        s=fixture(signals={},frames=[{"id":0x321,"extended":False,"dlc":2,"data":"9cff"}])
        self.store.ingest([s]);snap=self.store.snapshot("test-bike")
        self.assertAlmostEqual(snap["signals"]["pack_current_a"]["value"],-10)
        self.assertEqual(snap["signals"]["pack_current_a"]["decoder_version"],"test-profile-v1")
        wrong=fixture(sequence=2,signals={},frames=s["frames"]);wrong["variant"]="other-specimen"
        self.store.ingest([wrong]);self.assertEqual(self.store.history("test-bike")["samples"][-1]["signals"],{})

    def test_history_pagination_no_loss(self):
        self.store.ingest([fixture(sequence=i) for i in range(15)])
        page=self.store.history("test-bike",5)
        self.assertEqual([s["sequence"] for s in page["samples"]],list(range(10,15)))
        second=self.store.history("test-bike",5,page["next_before"])
        self.assertEqual([s["sequence"] for s in second["samples"]],list(range(5,10)))


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.server.store=Store(Path(self.temp.name)/"http.sqlite")
        self.server.token="test-token"
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()

    def request(self,path,body=None,auth=True,origin=None):
        headers={"Authorization":"Bearer test-token"} if auth else {}
        if origin:headers["Origin"]=origin
        data=json.dumps(body).encode() if body is not None else None
        return urllib.request.urlopen(urllib.request.Request(self.url+path,data=data,headers=headers),timeout=5)

    def test_api_auth_ingest_exports_and_page(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.request("/api/snapshot",auth=False)
        self.assertEqual(ctx.exception.code,401)
        with self.request("/api/ingest",{"samples":[fixture()]}) as r:self.assertEqual(json.load(r)["ack"][0]["status"],"stored")
        with self.request("/api/export.jsonl?device=test-bike") as r:self.assertEqual(json.loads(r.read())["device_id"],"test-bike")
        with self.request("/api/export.csv?device=test-bike") as r:self.assertIn("pack_voltage_v",r.read().decode())
        with self.request("/",auth=False) as r:self.assertIn("Know your Bee",r.read().decode())
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.request("/api/ingest",{"samples":[fixture()]},origin="http://foreign.example")
        self.assertEqual(ctx.exception.code,403)


class MqttTests(unittest.TestCase):
    def test_freshness_provenance_and_gps_opt_in(self):
        item={"timestamp":datetime.now(timezone.utc).isoformat(),"confidence":"verified"}
        self.assertTrue(eligible("pack_voltage_v",item))
        self.assertFalse(eligible("latitude",item))
        self.assertTrue(eligible("latitude",item,gps=True))
        self.assertFalse(eligible("pack_voltage_v",{**item,"confidence":"provisional"}))
        self.assertTrue(eligible("pack_voltage_v",{**item,"confidence":"provisional"},allow_provisional=True))
        self.assertFalse(eligible("pack_voltage_v",{**item,"timestamp":(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()}))
        self.assertFalse(eligible("pack_voltage_v",{**item,"confidence":"simulated"},allow_provisional=True))

    def test_discovery_expiry_and_stable_identity(self):
        config=discovery("test-bike","pack_voltage_v")
        self.assertEqual(config["expire_after"],15)
        self.assertEqual(config["device_class"],"voltage")
        self.assertNotIn("command_topic",config)
        self.assertNotIn("state_class",discovery("test-bike","odometer_km"))


if __name__ == "__main__":
    unittest.main()
