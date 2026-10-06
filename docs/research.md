# Research register

Reviewed **6 October 2026**. This is a bounded public-source review, not independent hardware validation.

## Evidence labels

- **Source-verified:** the inspected publication contains the described statement.
- **Author-reported:** implementation or measurements described by their creator.
- **Community claim:** discussion material without reviewed implementation evidence.
- **Hypothesis:** a proposal needing an experiment.
- **Bee-Link verified:** reproduced on an identified specimen with evidence. There are currently no such findings.

## Kevin Graehl / Electric Moto Garage

[Ultra Bee Live](https://kevingraehl.com/projects/ultra-bee-live/) presents pack readings, 20 cell groups and temperatures. It says public telemetry is read-only and control requests need local approval. It showed **waiting for device** during review, so live values were not validated.

[Surron Battery Reviver](https://kevingraehl.com/projects/surron-battery-reviver/) describes a working ESP32 CAN bridge, CSV logging and support for older four-pin and newer six-pin Ultra Bee charge connectors. These are author-reported capabilities. Model-year descriptions do not replace specimen inspection. Reported wake/output control does not establish that every signal is available passively.

No reusable firmware/DBC repository was identified in the inspected pages. Its development direction includes cloud history; Bee-Link must independently satisfy its offline goal. Recovery thresholds are not battery safety certification, and recovery procedures are outside this project.

## BraapZap

[UltraBee CANbus](https://www.braapzap.com/post/surron-ultrabee-canbus) tentatively interprets traffic as J1939 and discusses PGN 57344 and charger-related observations, leaving control details unresolved. Parsing an identifier as J1939 does not establish standard payload semantics. A PGN is not a complete CAN identifier or an instruction to transmit.

[Communications-port pinout](https://www.braapzap.com/post/surron-ultrabee-battery-com-port-pinout) is a connector lead. Retrieved text did not provide a usable pin table; diagram assignments were not independently verified and are not transcribed here. Obtain the original diagram, viewing direction and specimen details before comparison. The footer states that BraapZap is no longer in business; ongoing support cannot be assumed.

## Surron T-box FCC filing and firmware investigation

[FCC ID 2A92B-QL-TBOX-JM](https://fccid.io/2A92B-QL-TBOX-JM) is a public mirror of the US radio-certification filing for Surron's **QL-TBOX-JM telematics module**, submitted by Chongqing Qiulong Technology. The listed grant date is 22 March 2023. Its exhibits include the manufacturer user manual, internal PCB photographs, external photographs, label information and radio test reports.

**Why it matters:** the internal photographs provide a starting point for hardware identification before opening a unit. They may help identify components and candidate interfaces, but they are not a validated schematic, firmware image, debug pinout or CAN specification. Schematics, block diagram and operational description are listed as metadata only, rather than available public documents.

**Applicability:** confirm the model and hardware revision on the actual Ultra Bee T-box. A 2023 filing does not prove that every 2023 Ultra Bee, regional module or later revision uses identical hardware. No chip identities, debug pins or firmware readout method have been verified by Bee-Link.

The [manufacturer T-box manual](https://device.report/manual/9999122) describes CAN message upload, Bluetooth bus-data queries, device binding, remote-command delivery, low-power management, diagnostics and firmware updates. These are documented module capabilities, not proof that every feature is enabled on our target bike. In particular, its reference to Bluetooth firmware download may mean transferring an update **into** the device; it does not establish readback of installed firmware.

Potential investigation routes, not confirmed access methods:

- Observe normal CAN traffic to distinguish unsolicited telemetry from requests or commands.
- Inspect the owner's Bluetooth interaction and Android app to understand local queries and update handling.
- Examine an official update package if legitimately obtainable; it may be encrypted, compressed or a partial update.
- Identify PCB components and candidate UART/debug interfaces on a spare module; readout may be protected.
- Consider external-flash inspection only if suitable memory is identified; firmware may be internal or encrypted.

No published Surron T-box firmware dump or confirmed extraction procedure was located in this review. Behavioural analysis may be sufficient for Bee-Link without extracting firmware. Preserve the original unit and credentials; avoid unlocking operations that could erase them, and redact device keys, IMEI and identifiers from shared findings.

## Reddit and community

[CAN bus decoded fully (almost)](https://www.reddit.com/r/Surron/comments/1w0zdwh/canbus_decoded_fully_almost/) contains claims of charger emulation, charge-port control, breakout prototypes and planned GitHub publication. Temperature identification and some faults remained unresolved. These are collaboration leads, not reviewed specifications.

[Help with Ultra Bee battery](https://www.reddit.com/r/Surron/comments/1ogyexn/help_with_ultra_bee_battery/) includes September 2026 claims of nearly complete mapping and ESP32/VESC applicability. No corresponding public implementation was verified. Search results date the first thread to August 2026, while its opened page showed inconsistent relative ages; those ages should not establish chronology. The Reddit account's relationship to the website author was not independently established.

[Ultra Bees arrived from Gonped](https://www.reddit.com/r/Surron/comments/1ofe34r/ultra_bees_arrived_from_gonped/) includes reports of imported-bike app registration problems. This establishes reported access friction, not a universal regional rule or cloud-dependent riding.

## Commercial and adjacent work

[Source'IT Ultra Bee chargers](https://www.source-it.fr/en/collections/chargeurs-sur-ron-ultra-bee) states that the vendor developed a CAN interface for original Ultra Bee batteries. This is vendor-reported interoperability, not an open protocol, independent test or purchasing recommendation.

[patagonaa/surron-light-bee](https://github.com/patagonaa/surron-light-bee) documents Light Bee components and RS485 BMS work. Its pinouts and T-box observations do not establish Ultra Bee behaviour.

[Australian Surron 2026 Ultra Bee HP page](https://ridesurron.com.au/2026-surron-ultra-bee-hp/) describes CAN-based battery management and an updated charging interface. This supports broad architecture, not frame layouts or pin assignments.

## Search coverage and limitations

The review included Kevin's pages, BraapZap CAN/pinout material, web queries for Ultra Bee CAN/DBC/GitHub work, GitHub repository searches for `"ultra bee"` and `surron CAN`, and relevant Reddit discussions. No reproducible public Ultra Bee CAN gateway/DBC was located. Search can miss differently named repositories, unindexed discussions, private work and later releases.

Kevin's pages and BraapZap's pinout text were retrieved directly when the search browser could not open them. No private accounts or control endpoints were accessed. Third-party artwork and raw materials are not redistributed.

## Current assumptions and open questions

| Question | Status | Evidence needed |
| --- | --- | --- |
| Accessible telemetry at the T-box connector | Hypothesis | Module identity, wiring and captures |
| T-box removal preserves required functions | Unknown | OEM-role inventory, stationary comparison and rollback |
| Battery-port and bike-side telemetry match | Unknown | Separate captures with topology recorded |
| Desired signals are unsolicited | Unknown | Silent captures across normal states |
| ESP32 is suitable for permanent fitment | Candidate | Protection, loading, power/sleep and environmental checks |
| Speed/mode/controller temperatures are decodable | Unknown | Correlation with independent references |
| Reported health/SOC reflects actual capacity | Unknown | Separate validation; distinguish reported/calculated data |
| Definitions work across firmware/connector revisions | Unproven | Independently reproduced compatibility matrix |
| Periodic monitoring improves storage outcomes | Hypothesis | Wake/consumption measurements and longitudinal evidence |
| All app/cloud functions can be replaced | Unproven | Function inventory and explicit exclusions |

## Protocol admission rule

Do not promote AI/Gemini-proposed IDs, meanings, bitrates or pin assignments without evidence. Retain exact identifier, standard/extended flag, DLC, bytes, timestamps and capture context. Separate identifier parsing from payload interpretation. Record scale, byte order, signedness, units, sample age and variant limits.

Corroborate decodes with repeatable correlation and independent references where feasible. Publish provisional meanings as provisional, including counterexamples. Never create overcurrent, overtemperature, shorts or deep discharge merely to identify faults.

## Next research actions

1. Identify the first bike and electronics revisions.
2. Inventory actual app/cloud/T-box dependencies.
3. Seek voluntarily shared traces/code and reuse permissions from researchers. No contact was made for this package.
4. Recheck public releases before duplicating protocol work.
5. Capture normal stationary behaviour with a reviewed silent logger.
