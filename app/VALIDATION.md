# Validation record — 10 October 2026

## Completed

- Python receiver and optional bridge compile; browser script syntax check passes.
- Ten automated tests pass: commit/reopen persistence, identical retry deduplication, conflicting retry atomic rollback, delayed capture times and independent signal freshness, raw frame retention with format flags, invalid input rejection, signed variant-scoped decoding, history pagination, authenticated HTTP ingestion/exports/origin rejection, and MQTT policy/discovery configuration.
- Browser demo renders and navigation works. Battery view displays twenty **synthetic** groups and a calculated spread; the live implementation does not assume a group count.
- Demo recording, stop/save, replay, JSONL export, browser import and CSV export exercised end-to-end. Export validation confirms twelve demo samples round-trip and 384 decoded CSV rows, all marked `demo`.
- Empty real receiver connection shows zero stored samples and missing readings, with no simulated fields mixed into live mode.
- A separate disposable loopback fixture confirms two-minute-old values display as stale/missing on the overview, their original time/value/evidence remains inspectable, and raw ID/format/DLC/bytes are visible. These fixtures are explicitly synthetic, not protocol findings.
- Desktop (1440px viewport) and phone (390px viewport) responsive layouts inspected. No page-level horizontal overflow observed on overview/setup. Navigation/tables use their own intended scrolling containers.
- Browser warning/error log was empty during the exercised demo and empty-receiver flow.
- Setup guide returns HTTP 200 from the local receiver. Static assets use no internet libraries, fonts or map tiles.
- Self-contained OPEN-BEE-LINK.html generated from checked app sources. The browser automation surface only permits HTTP/HTTPS, so direct file-protocol launch of that separate preview was **not browser-verified**. No security-policy workaround was used.

## Not validated on hardware or external services

- No ESP32 firmware, harness, CAN bitrate/pinout, electrical silent mode, actual GPS receiver or SD/power-loss behavior was exercised.
- No real Ultra Bee CAN signal, cell count, current sign, fault meaning, GPS fix or battery-health estimate is validated.
- No live Home Assistant/Mosquitto deployment was performed. MQTT discovery/eligibility logic is tested, but broker authentication/TLS/reconnect and HA ingestion need a local integration test.
- Docker/Compose and Windows double-click launcher behavior have not been executed. The underlying local Python receiver was started and exercised successfully using the installed bundled runtime.
- Capture throughput, storage endurance, unattended startup and long-duration database growth have not been benchmarked. No automatic purge exists.

The saved preview screenshot shows simulated values. The main development receiver contains no real bike records. Temporary QA servers are stopped at handoff; use START-BEE-LINK.cmd to start a persistent local session.
