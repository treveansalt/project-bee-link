# Capture and receiver API v1

All assets and endpoints are on the same local origin. Authentication, when enabled, is `Authorization: Bearer <BEELINK_TOKEN>` for every `/api/` request. Cross-origin browser requests are disabled. Never put the token in a URL. There is no CAN control API.

## Ingest

`POST /api/ingest` with a JSON object containing `samples`: 1–200 samples, up to 2 MB per request. All samples validate first and commit in one transaction. An error stores none of that batch. Hardware retries must preserve immutable original sample content.

The following is a **shape illustration, not a measured Ultra Bee signal or supported CAN mapping**. Replace timestamp, IDs/metadata and evidence using the actual producer. Do not submit this illustrative value to a real log.

```json
{
  "samples": [{
    "schema_version": 1,
    "device_id": "ultra-bee",
    "capture_id": "unique-boot-or-file-uuid",
    "sequence": 0,
    "timestamp": "2026-10-10T10:00:00.000Z",
    "source": "gnss",
    "variant": "your-specimen-identifier",
    "decoder_version": "gps-parser-v1",
    "signals": {
      "latitude": {"value": 51.45, "confidence": "provisional", "evidence": "GPS parser validation pending"},
      "longitude": {"value": -0.55, "confidence": "provisional", "evidence": "GPS parser validation pending"}
    },
    "frames": []
  }]
}
```

Fields:

| Field | Contract |
|---|---|
| `schema_version` | Integer 1 |
| `device_id` | Stable bike/gateway identity. String, 1–128 characters. MQTT bridge uses a narrower topic-safe ID. |
| `capture_id` | Unique capture/boot UUID. Never reuse with a reset sequence. |
| `sequence` | Immutable sample number within capture, integer 0–2^53−1. Identity is `(device_id,capture_id,sequence)`. |
| `timestamp` | Capture/event time in ISO 8601 with timezone. Stored normalized to UTC microsecond precision. The browser renders millisecond precision. UTC Z recommended. Up to 5 minutes ahead of receiver clock allowed; farther future samples reject. |
| `source` | `can`, `gnss`, or `mixed`. Real logger rejects `demo`. |
| `variant` | Your exact specimen/firmware/connection-point profile; not a universal model-year assumption. |
| `decoder_version` | Version that produced decoded readings; use `raw-v1` for undecoded captures. |
| `signals` | Up to 128 numeric fields, each with finite `value`, `confidence` (`provisional` or `verified`) and nonempty `evidence` string (≤128 characters). |
| `frames` | Up to 1,000 classical CAN data frames per sample. Retains unknown identifiers. No CAN FD, RTR or error frames in v1. |

At least one signal or frame is required. Known units are encoded in the signal name and API contract; an unknown numeric key is shown as such without inventing its unit. Mode enums/fault codes may be retained as numeric fields but do not receive an invented meaning.

Classical CAN frame object: integer `id`, explicit boolean `extended`, integer `dlc` 0–8, `data` as consecutive hex byte pairs, and optional `timestamp` with timezone (defaults to sample timestamp). Standard IDs must fit 11 bits; extended IDs 29 bits; DLC must equal byte length. Do not collapse them into one identifier namespace. RTR/error/drop counters should be preserved in a separate original diagnostic log until a schema extension exists.

**Decoded values in one sample share that sample's capture time.** Send different acquisition times as separate samples. Raw frames can carry individual timestamps. The simple built-in decoder deliberately decodes only frames whose timestamp matches the sample time, so batched older raw frames do not falsely refresh displayed values. Keep immutable SD originals if changing a decoder later; current server does not re-decode old records automatically.

Response after successful database commit:

```json
{"ack":[{"device_id":"ultra-bee","capture_id":"unique-boot-or-file-uuid","sequence":0,"status":"stored"}],"committed_at":"2026-10-10T10:00:01.000Z"}
```

On retry, an identical identity/content gets `duplicate`. A reused identity with different contents rejects the whole batch. The firmware must advance its acknowledged upload cursor only after matching all acknowledged identities, never after merely sending bytes or seeing a network connection.

## Signal keys

| Key | Normalized interpretation |
|---|---|
| `soc_pct` | Battery-reported SOC, %. Not measured usable capacity or a health score. |
| `pack_voltage_v` | Pack voltage in V. |
| `pack_current_a` | Pack current in A. Producer must document raw current sign; no sign is inferred by this release. |
| `speed_kmh` | Bike ground-speed estimate in km/h; validate source/scaling. |
| `battery_temp_c`, `motor_temp_c`, `controller_temp_c` | Explicit identified temperatures in °C, not interchangeable sensors. |
| `odometer_km` | Reported odometer in km. No continuity or reset guarantee. |
| `cell_01_v`, `cell_02_v`, … | Reported series-group voltages in V; actual group count from the stream. |
| `latitude`, `longitude` | GPS decimal degrees. Valid fix only; unavailable fix is omission, never zero coordinates. |
| `gps_accuracy_m` | A real accuracy estimate in metres if the receiver supplies one. Do not label HDOP as metres. |
| `satellites` | Satellite count when available. |

UI stale threshold is ten seconds per signal in live mode. Replay mode displays recorded values explicitly as history. Uploading a three-hour-old ride does not make it live. GPS route lines break across gaps >10 seconds; distance estimates integrate adjacent speed readings only for intervals ≤10 seconds. Neither establishes full ride distance if coverage is incomplete.

## Read/export endpoints

| Endpoint | Result |
|---|---|
| `GET /api/devices` | Device IDs, stored sample counts and last capture time. |
| `GET /api/snapshot?device=ultra-bee` | Latest reading for each key with **its own** time/evidence/source/decoder metadata; counts and receiver time. |
| `GET /api/history?device=ultra-bee&limit=1000` | Most recently inserted samples, bounded 1–5,000 per page, and `next_before`. |
| `GET /api/history?device=ultra-bee&limit=1000&before=<next_before>` | Earlier insertions. UI sorts loaded captures by capture time. Pagination uses database row IDs, not timestamps. |
| `GET /api/export.jsonl?device=ultra-bee` | Complete normalized raw/decoded capture, streamed in capture-time order. |
| `GET /api/export.csv?device=ultra-bee` | Complete decoded numeric readings, metadata and evidence; does not include raw frames. |

## Optional local decoder

`protocol.json` is intentionally empty. `--profile <path>` loads an explicit version/variant-specific mapping of byte-aligned values. Rules require `key`, integer `id`, `extended`, `start_byte`, `length_bytes`, `byte_order` (`little` / `big`), `signed`, `scale`, `offset`, `confidence` and `evidence`. There are no supplied Ultra Bee rules.

This prototype decoder does not implement arbitrary bitfields, multiplexing, checksums or a full DBC. An external validated decoder can instead send normalized signals and retain associated frames. Server rules never overwrite already-provided signal keys. Capture producer and server decoder should be one authoritative version per sample; avoid combining inconsistent decoders. Decoder changes apply to new ingests only; duplicate uploads do not silently rewrite old history.
