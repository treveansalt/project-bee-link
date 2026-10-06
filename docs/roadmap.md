# Phased roadmap

All phases are planned. No implementation or hardware-validation milestone is complete. Progress depends on evidence, not dates.

## 0 — Scope and independence

Record model/market, build period, battery/controller/display revisions, T-box identity and connector photographs. Redact identifiers. Inventory desired app functions, actual account/cloud/local dependencies and proposed replacements. Mark unknowns and exclusions.

**Exit:** one target specimen, priority functions and a dependency matrix. Do not infer cloud-free vehicle operation from this inventory.

## 1 — Electrical survey and logger

Verify connector viewing direction, voltage domains, grounds/isolation, speed, topology and existing termination. Design a reversible tap and protected power supply. Evaluate shorts, transients and unpowered-interface behaviour without modifying traction wiring.

**Exit:** reviewed specimen-specific drawing; verified silent operation including ACK/error behaviour across boot/reset. No universal pinout is assumed.

## 2 — Baseline capture

Capture normal stationary key/display states and normal OEM charging where the approved interface permits. Record topology, logger configuration, time base, dropped frames/errors and OEM behaviour. Do not induce hazardous faults.

**Exit:** repeatable redacted traces; before/after operation compared; bus errors and sleep effects assessed. Silence does not authorise guessed wake commands.

## 3 — Decode

Create versioned machine-readable definitions and a signal catalogue. Prioritise available battery data. Correlate with suitable independent references. Distinguish raw observations, provisional meanings and corroborated signals.

**Exit:** released signals have fixtures, scaling/units, evidence and variant scope. Replay checks cover missing/truncated frames, unknown IDs, endian/sign errors and stale/incomplete snapshots. No guessed AI mappings are promoted.

## 4 — Local dashboard

Serve all assets locally. Display units, age and confidence. Preserve unknown/missing values and raw logs. Export CSV and a documented capture format. Keep reported health separate from calculated trends.

**Exit:** cold-start use with external internet blocked and no account or cached CDN assets; correct stale-data handling; restart/export checks and protected local access. No vehicle-control endpoint.

## 5 — Reproducible pilot

Publish BOM, build instructions, protection design, reversible harness drawings, enclosure requirements and compatibility limits. Measure active/idle/key-off consumption and sleep effects. Validate reset, power loss and disconnection. Assess mounting and environmental suitability before field use.

**Exit:** independent reproduction on the stated variant; failures do not disturb OEM operation; measured power impact is documented and accepted; installation and rollback match tested hardware. Select appropriate licences before reusable implementation release.

## 6 — Optional expansion

Study T-box duties before choosing augmentation/replacement. Add GNSS, BLE or local integrations only for established needs. Active features require a separate design and review, not automatic progression from telemetry.

**Exit per active feature:** verified purpose/protocol; explicit local enable; authentication, rate limits, bounded duration, watchdog and safe disconnect behaviour; independent review and variant tests. Browser loss cannot be the only safety mechanism. Revival charging and protection bypass remain excluded.

## Practical feasibility

A local logger/dashboard is a credible research objective given reported third-party progress. Full T-box/app replacement is considerably less certain. Reproducible decoding, variant coverage and safe power/sleep behaviour are the difficult parts.

An owner with reasonable electronics skills can lead identification, harnesses, capture and documentation. Programming support is needed for firmware, decoder validation and a maintainable interface. Start with one variant and one useful observation before committing to final hardware.

## Suggested first issues

- Inventory the first specimen and connectors.
- Map app/cloud/T-box dependencies.
- Review silent logger and power protection.
- Define capture metadata and redaction.
- Seek existing research with reuse permission.
- Define offline and stale-data acceptance tests.
