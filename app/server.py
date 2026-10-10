"""Bee Link local telemetry receiver. Python 3.11+; no mandatory dependencies.

Receives data from a future ESP32 transport; never opens or transmits on CAN.
The empty supplied protocol profile intentionally decodes nothing.
"""
from __future__ import annotations

import argparse
import csv
import hmac
import io
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
SIGNALS = {
    "soc_pct": ("Charge level", "%", "battery"),
    "pack_voltage_v": ("Pack voltage", "V", "voltage"),
    "pack_current_a": ("Pack current", "A", "current"),
    "speed_kmh": ("Speed", "km/h", "speed"),
    "battery_temp_c": ("Battery temperature", "°C", "temperature"),
    "motor_temp_c": ("Motor temperature", "°C", "temperature"),
    "controller_temp_c": ("Controller temperature", "°C", "temperature"),
    "odometer_km": ("Odometer", "km", "distance"),
    "latitude": ("Latitude", "°", None),
    "longitude": ("Longitude", "°", None),
    "gps_accuracy_m": ("GPS accuracy", "m", "distance"),
    "satellites": ("GPS satellites", None, None),
}
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
CONFIDENCE = {"provisional", "verified"}


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def stamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO 8601 string with timezone")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp needs timezone; use UTC Z")
    if dt.timestamp() > time.time() + 300:
        raise ValueError("timestamp is more than five minutes in the future")
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("signal values must be finite numbers")
    return value


def textfield(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(f"{key} must be a non-empty string of at most 128 characters")
    return value


def validate_sample(s):
    if not isinstance(s, dict) or s.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    out = {"schema_version": 1, "timestamp": stamp(s.get("timestamp"))}
    for key in ("device_id", "capture_id", "variant", "decoder_version"):
        out[key] = textfield(s, key)
    seq = s.get("sequence")
    if isinstance(seq, bool) or not isinstance(seq, int) or not 0 <= seq < 2**53:
        raise ValueError("sequence must be a non-negative safe integer")
    out["sequence"] = seq
    source = s.get("source")
    if source not in {"can", "gnss", "mixed"}:
        raise ValueError("source must be can, gnss or mixed; demo data cannot enter the logger")
    out["source"] = source
    signals = s.get("signals", {})
    if not isinstance(signals, dict) or len(signals) > 128:
        raise ValueError("signals must be an object of at most 128 entries")
    out["signals"] = {}
    for key, item in signals.items():
        if not KEY_RE.fullmatch(key) or not isinstance(item, dict):
            raise ValueError("invalid signal name or signal object")
        v = finite(item.get("value"))
        confidence = item.get("confidence")
        if confidence not in CONFIDENCE:
            raise ValueError("each signal needs provisional or verified confidence")
        evidence = textfield(item, "evidence")
        if key in {"latitude", "longitude"}:
            bound = 90 if key == "latitude" else 180
            if not -bound <= v <= bound:
                raise ValueError("GPS coordinate out of range")
        out["signals"][key] = {"value": v, "confidence": confidence, "evidence": evidence}
    frames = s.get("frames", [])
    if not isinstance(frames, list) or len(frames) > 1000:
        raise ValueError("frames must be an array of at most 1000 classical CAN data frames")
    out["frames"] = []
    for f in frames:
        if not isinstance(f, dict) or type(f.get("extended")) is not bool:
            raise ValueError("frame needs explicit extended boolean")
        ident = f.get("id")
        if type(ident) is not int or not 0 <= ident <= (0x1FFFFFFF if f["extended"] else 0x7FF):
            raise ValueError("frame identifier out of range")
        data = f.get("data")
        if not isinstance(data, str) or not re.fullmatch(r"(?:[0-9a-fA-F]{2}){0,8}", data):
            raise ValueError("frame data needs 0–8 bytes of hex without spaces")
        if type(f.get("dlc")) is not int or f["dlc"] != len(data) // 2:
            raise ValueError("frame DLC must match byte length")
        out["frames"].append({"id": ident, "extended": f["extended"], "dlc": f["dlc"],
                              "data": data.upper(), "timestamp": stamp(f.get("timestamp", out["timestamp"]))})
    if not out["frames"] and not out["signals"]:
        raise ValueError("sample must contain frames or signals")
    return out


def decode(s, profile):
    """Opt-in byte-aligned decoder, scoped to a documented variant. No guessed mappings."""
    if s["variant"] != profile.get("variant"):
        return s
    for frame in s["frames"]:
        for rule in profile.get("signals", []):
            if frame["id"] != rule["id"] or frame["extended"] != rule["extended"]:
                continue
            start, length = rule["start_byte"], rule["length_bytes"]
            payload = bytes.fromhex(frame["data"])
            if start + length > len(payload):
                continue
            number = int.from_bytes(payload[start:start+length], rule["byte_order"], signed=rule["signed"])
            value = number * rule["scale"] + rule["offset"]
            # Preserve frame-specific time; rules only decode frames matching sample time.
            # For batched captures submit one sample per timestamp to retain exact ages.
            if frame["timestamp"] != s["timestamp"]:
                continue
            if rule["key"] not in s["signals"]:
                s["signals"][rule["key"]] = {"value": finite(value), "confidence": rule["confidence"],
                                             "evidence": rule["evidence"]}
                s["decoder_version"] = profile["version"]
    return s


def load_profile(path):
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    for rule in p["signals"]:
        if (not KEY_RE.fullmatch(rule["key"]) or rule["confidence"] not in CONFIDENCE
                or type(rule["extended"]) is not bool or type(rule["signed"]) is not bool
                or type(rule["id"]) is not int
                or not 0 <= rule["id"] <= (0x1FFFFFFF if rule["extended"] else 0x7FF)
                or type(rule["start_byte"]) is not int or rule["start_byte"] < 0
                or type(rule["length_bytes"]) is not int or not 1 <= rule["length_bytes"] <= 8
                or rule["start_byte"] + rule["length_bytes"] > 8
                or rule["byte_order"] not in {"little", "big"}):
            raise ValueError("invalid protocol rule")
        finite(rule["scale"]); finite(rule["offset"]); textfield(rule, "evidence")
    textfield(p, "version"); textfield(p, "variant")
    return p


class Store:
    def __init__(self, path, profile=None):
        self.path = str(path)
        self.profile = profile or {"variant": "unconfigured", "signals": []}
        self.lock = threading.RLock()
        with self.db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS samples (
                  row_id INTEGER PRIMARY KEY, device_id TEXT NOT NULL, capture_id TEXT NOT NULL,
                  sequence INTEGER NOT NULL, timestamp TEXT NOT NULL, received_at TEXT NOT NULL,
                  payload TEXT NOT NULL, original TEXT NOT NULL,
                  UNIQUE(device_id,capture_id,sequence));
                CREATE INDEX IF NOT EXISTS time_idx ON samples(device_id,timestamp);
                CREATE TABLE IF NOT EXISTS readings (
                  sample_id INTEGER NOT NULL REFERENCES samples(row_id), device_id TEXT NOT NULL,
                  key TEXT NOT NULL, timestamp TEXT NOT NULL, value REAL NOT NULL,
                  confidence TEXT NOT NULL, evidence TEXT NOT NULL,
                  PRIMARY KEY(sample_id,key));
                CREATE INDEX IF NOT EXISTS signal_idx ON readings(device_id,key,timestamp);
                CREATE TABLE IF NOT EXISTS latest (
                  device_id TEXT NOT NULL, key TEXT NOT NULL, sample_id INTEGER NOT NULL,
                  timestamp TEXT NOT NULL, PRIMARY KEY(device_id,key));
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def ingest(self, batch):
        if not isinstance(batch, list) or not 1 <= len(batch) <= 200:
            raise ValueError("samples must contain 1–200 samples")
        prepared = [(s, decode(validate_sample(s), self.profile)) for s in batch]
        ack = []
        with self.lock, self.db() as db:
            for original, s in prepared:
                identity = (s["device_id"], s["capture_id"], s["sequence"])
                old = db.execute("SELECT original FROM samples WHERE device_id=? AND capture_id=? AND sequence=?", identity).fetchone()
                raw = json.dumps(original, sort_keys=True, separators=(",", ":"), allow_nan=False)
                if old:
                    if old["original"] != raw:
                        raise ValueError("duplicate sequence with different data; use a new capture_id")
                    status = "duplicate"
                else:
                    cur = db.execute("INSERT INTO samples(device_id,capture_id,sequence,timestamp,received_at,payload,original) VALUES(?,?,?,?,?,?,?)",
                                     (*identity, s["timestamp"], utcnow(), json.dumps(s), raw))
                    for key, item in s["signals"].items():
                        db.execute("INSERT INTO readings VALUES(?,?,?,?,?,?,?)", (cur.lastrowid, s["device_id"], key,
                                   s["timestamp"], item["value"], item["confidence"], item["evidence"]))
                        db.execute("""INSERT INTO latest VALUES(?,?,?,?) ON CONFLICT(device_id,key)
                            DO UPDATE SET sample_id=excluded.sample_id,timestamp=excluded.timestamp
                            WHERE excluded.timestamp >= latest.timestamp""", (s["device_id"], key, cur.lastrowid, s["timestamp"]))
                    status = "stored"
                ack.append({"device_id": identity[0], "capture_id": identity[1], "sequence": identity[2], "status": status})
        # Commit happens before returning acknowledgement. Retried batches cannot duplicate logs.
        return ack

    def devices(self):
        with self.db() as db:
            return [dict(x) for x in db.execute("SELECT device_id,COUNT(*) samples,MAX(timestamp) last_seen FROM samples GROUP BY device_id ORDER BY device_id")]

    def snapshot(self, device):
        with self.db() as db:
            latest = db.execute("SELECT payload,received_at FROM samples WHERE device_id=? ORDER BY timestamp DESC,row_id DESC LIMIT 1", (device,)).fetchone()
            rows = db.execute("""SELECT r.*,s.payload FROM latest l
                JOIN readings r ON r.sample_id=l.sample_id AND r.key=l.key
                JOIN samples s ON s.row_id=r.sample_id WHERE l.device_id=?""", (device,))
            signals = {}
            for row in rows:
                if row["key"] in signals:
                    continue
                meta = json.loads(row["payload"])
                signals[row["key"]] = {"value": row["value"], "timestamp": row["timestamp"], "confidence": row["confidence"],
                                       "evidence": row["evidence"], "source": meta["source"], "decoder_version": meta["decoder_version"],
                                       "variant": meta["variant"]}
            count = db.execute("SELECT COUNT(*) FROM samples WHERE device_id=?", (device,)).fetchone()[0]
            meta = json.loads(latest["payload"]) if latest else {}
            return {"device_id": device, "timestamp": meta.get("timestamp"), "variant": meta.get("variant", "unknown"),
                    "received_at": latest["received_at"] if latest else None, "sample_count": count, "signals": signals,
                    "server_time": utcnow(), "protocol_version": self.profile.get("version", "unconfigured")}

    def history(self, device, limit=1000, before=None):
        with self.db() as db:
            sql = "SELECT row_id,payload FROM samples WHERE device_id=?"
            args = [device]
            if before is not None:
                sql += " AND row_id<?"; args.append(before)
            sql += " ORDER BY row_id DESC LIMIT ?"; args.append(limit)
            rows = list(db.execute(sql, args))
            return {"samples": [json.loads(r["payload"]) for r in reversed(rows)],
                    "next_before": rows[-1]["row_id"] if len(rows) == limit else None}

    def export(self, device):
        with self.db() as db:
            for row in db.execute("SELECT payload FROM samples WHERE device_id=? ORDER BY timestamp,row_id", (device,)):
                yield json.loads(row["payload"])


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "dist"), **kwargs)

    def log_message(self, fmt, *args):
        # Do not echo authorization headers or submitted telemetry.
        if args and "400" in str(args):
            print("Request rejected", flush=True)

    def authorized(self):
        token = self.server.token
        return not token or hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token)

    def safe_origin(self):
        origin = self.headers.get("Origin")
        return not origin or urlsplit(origin).netloc == self.headers.get("Host")

    def reply(self, obj, status=200):
        data = json.dumps(obj, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(data)

    def do_POST(self):
        if not self.safe_origin():
            return self.reply({"error": "cross-origin requests are disabled"}, 403)
        if not self.authorized():
            return self.reply({"error": "valid bearer token required"}, 401)
        if self.path != "/api/ingest":
            return self.reply({"error": "endpoint not found"}, 404)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 2_000_000:
                return self.reply({"error": "body must be 1 byte–2 MB"}, 413)
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("body must be an object")
            ack = self.server.store.ingest(body.get("samples"))
            self.reply({"ack": ack, "committed_at": utcnow()})
        except (ValueError, KeyError, TypeError, OverflowError) as e:
            self.reply({"error": str(e)}, 400)
        except sqlite3.Error:
            self.reply({"error": "storage failed; keep the local batch and retry"}, 503)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if not parsed.path.startswith("/api/"):
            return super().do_GET()
        if not self.safe_origin():
            return self.reply({"error": "cross-origin requests are disabled"}, 403)
        if not self.authorized():
            return self.reply({"error": "valid bearer token required"}, 401)
        q = parse_qs(parsed.query)
        device = q.get("device", ["ultra-bee"])[0]
        try:
            if parsed.path == "/api/devices":
                return self.reply({"devices": self.server.store.devices()})
            if parsed.path == "/api/snapshot":
                return self.reply(self.server.store.snapshot(device))
            if parsed.path == "/api/history":
                limit = min(5000, max(1, int(q.get("limit", ["1000"])[0])))
                before = int(q["before"][0]) if "before" in q else None
                return self.reply(self.server.store.history(device, limit, before))
            if parsed.path in {"/api/export.jsonl", "/api/export.csv"}:
                self.send_response(200)
                is_csv = parsed.path.endswith("csv")
                self.send_header("Content-Type", "text/csv" if is_csv else "application/x-ndjson")
                self.send_header("Content-Disposition", 'attachment; filename="bee-link-' + ("signals.csv" if is_csv else "capture.jsonl") + '"')
                self.send_header("Cache-Control", "no-store"); self.end_headers()
                if is_csv:
                    out = io.StringIO(); writer = csv.writer(out)
                    writer.writerow(["timestamp_utc", "device_id", "capture_id", "sequence", "variant", "decoder_version", "source", "signal", "value", "confidence", "evidence"])
                    self.wfile.write(out.getvalue().encode()); out.seek(0); out.truncate(0)
                for sample in self.server.store.export(device):
                    if is_csv:
                        for key, item in sample["signals"].items():
                            row = [sample[k] for k in ("timestamp", "device_id", "capture_id", "sequence", "variant", "decoder_version", "source")]
                            row += [key, item["value"], item["confidence"], item["evidence"]]
                            # Avoid interpreting metadata as spreadsheet formulae.
                            writer.writerow([("'" + x if isinstance(x, str) and x[:1] in "=+-@" else x) for x in row])
                            self.wfile.write(out.getvalue().encode()); out.seek(0); out.truncate(0)
                    else:
                        self.wfile.write((json.dumps(sample) + "\n").encode())
                return
            return self.reply({"error": "endpoint not found"}, 404)
        except (ValueError, TypeError) as e:
            self.reply({"error": str(e)}, 400)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--db", default=str(ROOT / "data" / "bee-link.sqlite"))
    p.add_argument("--profile", default=str(ROOT / "protocol.json"))
    p.add_argument("--open-browser", action="store_true", help="Open the local dashboard in your default browser")
    args = p.parse_args()
    token = os.environ.get("BEELINK_TOKEN", "")
    if args.host not in {"127.0.0.1", "localhost", "::1"} and len(token) < 24:
        p.error("set BEELINK_TOKEN to a random secret of at least 24 characters before enabling LAN access")
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.token = token
    srv.store = Store(args.db, load_profile(args.profile))
    print(f"Bee Link: http://{args.host}:{args.port} — local SQLite logging enabled", flush=True)
    if args.open_browser:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{args.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
