"""Pure telemetry policy, drafted on the Mac local model and independently repaired."""
import math
from datetime import datetime, timezone


def _timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def format_telemetry(snapshot, include_location=False, now=None, max_age_seconds=60):
    """Return <=120 ASCII bytes, or None. Never turn unavailable data into zero."""
    if type(max_age_seconds) is not int or max_age_seconds <= 0:
        return None
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        return None
    now = now.astimezone(timezone.utc)
    excluded = ('demo', 'simulated', 'replay')
    if not isinstance(snapshot, dict) or snapshot.get('source') in excluded:
        return None
    signals = snapshot.get('signals')
    if not isinstance(signals, dict):
        return None
    bounds = {'soc_pct': (0, 100), 'speed_kmh': (0, 250),
              'latitude': (-90, 90), 'longitude': (-180, 180)}
    readings = {}
    for key, (low, high) in bounds.items():
        item = signals.get(key)
        if not isinstance(item, dict) or item.get('confidence') != 'verified' or item.get('source') in excluded:
            continue
        value = item.get('value')
        if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
            continue
        timestamp = _timestamp(item.get('timestamp'))
        if timestamp is None or not 0 <= (now-timestamp).total_seconds() <= max_age_seconds:
            continue
        readings[key] = (value, timestamp)
    parts = []
    used_times = []
    for key, template in [('soc_pct', 'BAT {:.0f}%'), ('speed_kmh', 'SPD {:.1f}km/h')]:
        if key in readings:
            value, timestamp = readings[key]
            parts.append(template.format(value))
            used_times.append(timestamp)
    if include_location is True and 'latitude' in readings and 'longitude' in readings:
        lat, lat_time = readings['latitude']
        lon, lon_time = readings['longitude']
        if abs((lat_time-lon_time).total_seconds()) <= 5:
            parts.append('GPS {:.4f},{:.4f}'.format(lat, lon))
            used_times.extend([lat_time, lon_time])
    if not parts:
        return None
    # Label the freshest included observation, not its later upload/send time.
    message = 'Bee-Link '+max(used_times).strftime('%H:%MZ')+' '+' '.join(parts)
    return message if len(message.encode('ascii')) <= 120 else None
