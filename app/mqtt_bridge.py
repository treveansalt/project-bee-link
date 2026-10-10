"""Publish fresh logger signals through MQTT discovery. Optional paho-mqtt 2.x."""
import argparse
from datetime import datetime, timezone
import json
import os
import re
import threading
import time
import urllib.request
import urllib.parse

from server import SIGNALS


def metadata(key):
    if key in SIGNALS:
        return SIGNALS[key]
    if re.fullmatch(r"cell_\d+_v", key):
        return (f"Cell group {int(key.split('_')[1])}", "V", "voltage")
    return None


def discovery(device, key):
    name, unit, cls = metadata(key)
    base = f"beelink/{device}"
    obj = {"name": name, "unique_id": f"beelink_{device}_{key}", "state_topic": f"{base}/signal/{key}",
           "value_template": "{{ value_json.value }}", "json_attributes_topic": f"{base}/signal/{key}",
           "availability_topic": f"{base}/availability", "payload_available": "online", "payload_not_available": "offline",
           "expire_after": 15, "state_class": "measurement",
           "device": {"identifiers": [f"beelink_{device}"], "name": f"Bee Link {device}",
                      "manufacturer": "Independent Bee Link project", "model": "Ultra Bee telemetry gateway"}}
    if unit:
        obj["unit_of_measurement"] = unit
    if cls:
        obj["device_class"] = cls
    # Odometer reset/continuity is not validated: no total_increasing statistic.
    if key == "odometer_km":
        obj.pop("state_class", None)
    return obj


def eligible(key, item, allow_provisional=False, gps=False, now=None):
    if not metadata(key) or item.get("confidence") not in ({"verified", "provisional"} if allow_provisional else {"verified"}):
        return False
    if key in {"latitude", "longitude", "gps_accuracy_m", "satellites"} and not gps:
        return False
    try:
        dt = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
        seconds = ((now or datetime.now(timezone.utc)) - dt).total_seconds()
        return 0 <= seconds <= 10
    except (ValueError, TypeError, KeyError):
        return False


def main():
    import paho.mqtt.client as mqtt
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--logger", default="http://127.0.0.1:8765")
    p.add_argument("--broker", required=True)
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--device", default="ultra-bee")
    p.add_argument("--tls", action="store_true")
    p.add_argument("--include-provisional", action="store_true")
    p.add_argument("--gps", action="store_true", help="Opt in to publishing location to your private broker")
    args = p.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", args.device):
        p.error("device must contain only letters, digits, underscore or hyphen")
    base = f"beelink/{args.device}"
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"beelink-{args.device}", protocol=mqtt.MQTTv5)
    client.will_set(f"{base}/availability", "offline", qos=1, retain=True)
    username = os.environ.get("MQTT_USERNAME")
    if username:
        client.username_pw_set(username, os.environ.get("MQTT_PASSWORD"))
    if args.tls:
        client.tls_set()
    reset = threading.Event()

    def connected(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            return
        client.publish(f"{base}/availability", "online", qos=1, retain=True)
        client.subscribe("homeassistant/status", qos=1)
        reset.set()

    def message(client, userdata, msg):
        if msg.topic == "homeassistant/status" and msg.payload == b"online":
            reset.set()

    client.on_connect = connected
    client.on_message = message
    client.connect_async(args.broker, args.port, keepalive=30)
    client.loop_start()
    sent, known = {}, set()
    failures = 0
    try:
        print("Bee Link MQTT bridge running; only fresh eligible readings are published.", flush=True)
        while True:
            try:
                req = urllib.request.Request(args.logger.rstrip("/") + "/api/snapshot?device=" + urllib.parse.quote(args.device))
                secret = os.environ.get("BEELINK_TOKEN")
                if secret:
                    req.add_header("Authorization", "Bearer " + secret)
                with urllib.request.urlopen(req, timeout=5) as response:
                    snapshot = json.load(response)
                if reset.is_set():
                    known.clear(); sent.clear(); reset.clear()
                if client.is_connected():
                    for key, item in snapshot["signals"].items():
                        if not eligible(key, item, args.include_provisional, args.gps):
                            continue
                        if key not in known:
                            result = client.publish(f"homeassistant/sensor/beelink_{args.device}/{key}/config",
                                                    json.dumps(discovery(args.device, key)), qos=1, retain=True)
                            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                                continue
                            known.add(key)
                        if sent.get(key) != item["timestamp"]:
                            # State is NOT retained: reconnect must not refresh an old sample.
                            result = client.publish(f"{base}/signal/{key}", json.dumps(item), qos=1, retain=False)
                            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                                sent[key] = item["timestamp"]
                failures = 0
            except (OSError, ValueError, KeyError):
                failures += 1
                if failures == 1 or failures % 60 == 0:
                    print("Logger unavailable; sensor readings will expire. Retrying.", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if client.is_connected():
            result = client.publish(f"{base}/availability", "offline", qos=1, retain=True)
            result.wait_for_publish(timeout=3)
            client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
