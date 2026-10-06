# Contributing

Electronics, CAN analysis, firmware, local interfaces, testing and documentation contributions are welcome. Careful photographs and reproducible observations are valuable without programming skills.

Read the README safety principles and research register. Open an issue with the problem, variant and proposed evidence. Share only material you own or have permission to contribute. Licensing is pending; public visibility is not a reuse licence.

## Evidence checklist

- Bike/model/market/build period and electronics revisions where known.
- Connector photographs and viewing direction, with identifiers hidden.
- Topology, logger hardware/firmware, CAN configuration and transmission capability.
- Operating state, time base, duration and dropped frames/errors.
- Redacted raw capture and independent reference readings where available.
- Observations separated from inference, alternative explanations and unknowns.

A signal proposal should include identifier and standard/extended flag, DLC, byte/bit positions, byte order, signedness, scale/offset, units, timing and variant scope. Include example frames and counterexamples. An identifier shape alone does not establish payload meaning.

## Pull requests

Keep changes focused, credit sources and link evidence. Label provisional mappings honestly. Decoder changes need replay fixtures and handling of incomplete data. UI work should demonstrate offline, missing and stale states. Hardware claims need measurements.

Do not submit hazardous fault-generation experiments, battery revival procedures, protection bypasses, tuning or credential extraction. Transmit features require the roadmap's separate review before being represented as supported.

## Privacy and reporting

Remove VINs, serials, home/ride locations, tokens and Wi-Fi credentials before sharing. Share others' captures only with their permission. Discuss safety/security concerns without publishing credentials or weaponised commands; use a maintainer's private channel if available. No private reporting address is currently established.

Useful first contributions include variant inventories, verified connector sourcing, capture formats, evidence-backed corrections, offline mockups and power measurements. Negative results help when setup and limits are documented.
