# OEM functionality and local-app scope

Reviewed **10 October 2026** for the Ultra Bee project. Source verification means a publication contains the statement; it does not mean this project's hardware reproduced it. Exact model, region, firmware, module presence and account support remain specimen-specific.

## What the official app provides

The [official Android listing](https://play.google.com/store/apps/details?id=com.surron.oversea) and [iPhone listing](https://apps.apple.com/gb/app/surron/id6450043341) advertise bike location, battery status, ride trajectory, safety alerts, repair requests, online fault diagnosis and rider/community services. The iPhone version history also references OTA and vehicle-track improvements. Listings do not specify every battery field, sampling cadence, retained-history depth or universal Ultra Bee eligibility.

The [manufacturer's QL-TBOX-JM manual](https://device.report/manual/9999122), hosted as a public manual mirror, describes a telematics module with GNSS, cellular and Bluetooth, CAN/fault upload, local alerts, remote commands, low-power management, firmware updating and UDS diagnosis. These are documented module capabilities; not all are necessarily exposed in the owner's app. The manual is not a validated CAN payload specification for our bike.

The previous Bee-Link project register contains third-party decoding leads. [Kevin Graehl's Ultra Bee Live project](https://kevingraehl.com/projects/ultra-bee-live/) was previously inspected and author-reports a battery dashboard/cell-group detail. Its page was not accessible through the web reader in this review; it is a feasibility lead, not fresh independent validation. No third-party code or inferred CAN IDs have been reused.

## Feature-to-source matrix

| Feature | Published OEM evidence | Can a local app provide it? | Required source / qualification |
|---|---|---|---|
| Reported battery status | Official app listings | Likely a useful first target | CAN signal discovery; identify whether broadcasts or queries. No fields guaranteed. |
| Pack voltage/current/temperatures | Third-party leads; general battery diagnostic inference | Plausible, unverified here | Specimen captures plus independent correlation and valid units/current sign. |
| Cell-group voltages/spread | Third-party prototype reports | Plausible enhancement | BMS data may be query-only or absent at the chosen connector; count/layout unknown. |
| Speed/odometer/riding state | Vehicle data inference | Plausible | Capture on-bike controller/display traffic; battery port evidence does not establish harness traffic. |
| Route and position | App listings; T-box GNSS | Yes, independently of CAN | ESP32 GPS, valid fixes and clock. CAN alone does not create location. |
| Ride history | App advertises trajectory | Yes for captures recorded from installation onward | SD while riding, later upload and SQLite. Existing unrecorded history cannot be recovered. |
| Charge curves and energy estimates | Derived-feature inference | Conditional | Pack V/I, synchronized timestamps, validated sign/scaling and explicit gaps. SOC change is not a capacity measurement. Current release shows reported values; it does not estimate battery health. |
| Informational temperature/SOC alerts | App safety alerts; derived telemetry use | Conditional | Valid signals, owner's appropriate limits, current data and an available notification path. |
| Vibration/tip-over/power-disconnect alerts | T-box manual | Additional hardware/function work | IMU/ignition sensing or validated available message; parked power and mobile connectivity. |
| Passive fault history | App diagnosis; T-box fault upload | Possible | Broadcast codes plus a validated fault dictionary; preserve unknown codes without invented diagnosis. |
| Active diagnostics/service functions | T-box UDS | Separate project phase | Verified request/response semantics and transmit-capable design. Not implemented. |
| Remote tracking/theft alerts | T-box cellular + GNSS | Wi-Fi alone insufficient | LTE gateway or connected phone relay, connectivity/power and motion sensing. No current remote theft service. |
| Vendor OTA, binding, repair requests/community | App/manual | Not reproduced by CAN telemetry | Vendor service/authentication/update systems and signed firmware workflows. |
| Tuning/power/configuration controls | No universal promise established in this review | Excluded from the telemetry build | No transmit/control endpoints or guessed commands. |

This matrix deliberately distinguishes documented app functions from engineering inference. A feature being present in an app is not evidence it appears as a passive CAN broadcast. Likewise T-box removal is not presumed harmless or required.

## We cannot conclude the bike has no logs

The app advertises trajectory history and the T-box describes data upload. Available documentation does not establish its sample rate, retention, off-bike cloud storage, local buffering, raw capture depth or export capability. We should therefore say **unknown vendor history**, not "the bike keeps no history".

Our own archive is valuable regardless: it records with owner-controlled timestamps and exports, retains raw evidence, and does not depend on an undocumented vendor history API. It cannot monitor a powered-off/sleeping system that emits nothing; do not interpret silence as a healthy state.

## Recommended logging stack

**On the bike:** ESP32 + GPS + microSD appends CAN and GPS before Wi-Fi upload. Keep all undecoded frames during research, plus original clock/overflow metadata. A later production profile may keep high-rate bursts for faults and reduced-rate normal data, but define those rules after measuring real traffic and use.

**At home:** the implemented receiver commits to SQLite, returns durable sequence acknowledgements and serves the web app. A Pi or always-on server provides continuity; the home server does not record data that the bike never captured. No mandatory cloud dependency is introduced.

**Home Assistant:** use the implemented optional MQTT discovery bridge for selected fresh sensors, history and automations. [Home Assistant supports discovery and availability](https://www.home-assistant.io/integrations/mqtt/); [MQTT sensor expiry](https://www.home-assistant.io/integrations/sensor.mqtt/) prevents stale samples remaining indefinitely current. GPS publication is opt-in. Old SD captures go into SQLite, not re-published as live HA readings.

**Retention:** [the recorder documentation](https://www.home-assistant.io/integrations/recorder/) sets a default short-term keep period of ten days; long-term statistics are a different representation. Raw CAN should remain in SD/SQLite archives, not be sent frame-by-frame through Home Assistant. If long-term fleet-scale querying later justifies it, InfluxDB/Grafana is an optional upgrade; it is unnecessary for this first single-bike release.

No custom Home Assistant component is required initially. Standard MQTT avoids a bespoke integration maintenance burden while preserving local operation. Candidate automations include a reminder when a *fresh, validated* reported charge reading falls outside an owner-configured storage window, and an alert when an expected update has not arrived. Use gaps as "data unavailable," never as a battery fault diagnosis. Parked monitoring requires verified power/sleep behavior before enabling it.

## Current release and next engineering steps

The web app, SQLite ingestion/export, replay, empty profile loader, SD-copy uploader and MQTT bridge are implemented. The ESP32 board firmware, physical gateway and real Home Assistant deployment are not. No bitrate, pinout, CAN ID, cell count, scaling or controller behavior is promoted from an AI suggestion to a bike definition.

Next, identify the exact specimen and safe receive-only tap; capture stationary CAN in ignition/charging/sleep states; keep GPS/monotonic clock anchors; correlate candidate signals; then admit mappings with explicit variant/version/evidence. Start with local CAN logging even if no fields are known, since those raw records are what let us decode more later.

Electrical silent-mode design is informed by [Espressif's controller documentation](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/twai.html): an external transceiver is required, and listen-only mode suppresses ACK/error dominant bits. This is a controller behavior specification, not proof that a particular gateway is safe on the Ultra Bee.
