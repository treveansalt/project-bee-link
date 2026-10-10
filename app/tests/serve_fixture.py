"""Disposable loopback-only UI fixture. All values are synthetic test data."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Handler, Store, ThreadingHTTPServer


with tempfile.TemporaryDirectory() as temp:
    store = Store(Path(temp) / "ui-fixture.sqlite")
    for i in range(3):
        timestamp = (datetime.now(timezone.utc)-timedelta(minutes=2,seconds=2-i)).isoformat()
        def signal(value):
            return {"value":value,"confidence":"provisional","evidence":"Synthetic browser test fixture; not bike evidence"}
        store.ingest([{"schema_version":1,"device_id":"test-fixture","capture_id":"browser-qa-only",
                      "sequence":i,"timestamp":timestamp,"source":"mixed","variant":"SYNTHETIC UI TEST",
                      "decoder_version":"test-only","signals":{"pack_voltage_v":signal(72+i/10),"latitude":signal(51.45+i/1000),
                      "longitude":signal(-0.55+i/1000)},"frames":[{"id":0x321,"extended":False,"dlc":2,"data":"0102"}]}])
    srv=ThreadingHTTPServer(("127.0.0.1",8766),Handler);srv.store=store;srv.token=""
    print("Disposable browser test at http://127.0.0.1:8766; use device test-fixture",flush=True)
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()
