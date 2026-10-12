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

## Capture overview update — 12 October 2026

- All 18 automated tests passed on Windows and on the M2 Mac. Eight new tests cover capture summaries and their HTTP endpoint: device isolation, parameterized queries, empty results, sparse/reordered sequences, tuple/Row factories, microsecond duration, stable sorting, clamped limits, read-only queries, authentication and origin rejection.
- Browser check with disposable synthetic data showed two distinct captures, counts 3/1 and sequence holes 1/0. Manual refresh completed successfully. No warning/error console messages were observed. All DOM IDs were unique.
- At desktop width and a 390px phone viewport, the page had no horizontal overflow. On the phone, the wide capture table scrolls within its card.
- JavaScript syntax check passed; offline preview regenerated. Docker COPY now includes capture_summary.py; container execution remains untested.
- OpenCode on the Mac used LM Studio's local kali-agent-llm model to draft the module. Its first draft and repair attempt required substantial independent correction. The reviewer wrote the regression tests and integrated the API/UI. A later OpenCode job ran the complete test suite on the Mac successfully. Its prose summary misread an expected authentication rejection; the actual tool output reports all 18 tests OK. Local model output must still be reviewed.
- Existing hardware, CAN decoding and MQTT deployment limitations above still apply. This feature uses stored capture facts only.
