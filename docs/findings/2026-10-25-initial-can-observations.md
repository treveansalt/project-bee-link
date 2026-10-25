# Initial Ultra Bee CAN findings — 25 October 2026

> **Initial findings — not confirmed.** These are observational associations from one owner's Ultra Bee, not an OEM specification, validated decoder, installation guide or instruction to transmit. Values may differ across bikes and firmware revisions.

## Capture context and evidence limits

An owner-supplied CAN CSV was compared with two narrated video parts. The owner reports a connection at the T-box wiring. The exact bike year, market, T-box/controller revisions, connector orientation and pin assignments were not documented sufficiently for independent reproduction.

- Logger: DSD TECH SH-C31G; firmware v1.5 was verified separately before capture. The CSV itself says firmware “not reported”.
- Software: diCAN 1.0.0; export reports **500 kbit/s, classic CAN, Silent mode**.
- Dataset: **105,346 Rx records, 33 CAN IDs**, approximately four minutes. The export labels its scope FILTERED, with “no filter” listed throughout its filter history.
- Physical setup: owner reports R120 off, BOOT off, +5 V unconnected and no separate adapter GND connection. This documents the experiment; it is not a recommended wiring arrangement.
- Earlier session logs showed receive errors. Error rate and dropped frames for this recording are not established. Receiving frames does not validate signal integrity, electrical silence or connection safety.
- Audio was automatically transcribed locally. Spoken letters and word timings can be misrecognised. Narration may precede the action.
- Raw CSV and videos are retained privately and **not included here**. These tables are derived observations; public independent replay verification is not yet possible. Device identifiers, location metadata and identifying payloads have been omitted.

## Candidate signal table

**All IDs and payload values below are hexadecimal.** Payload positions are counted from **byte 1**; zero-based indexes are supplied to avoid ambiguity. All candidate frames in this table use **standard 11-bit identifiers and DLC 8**.

| CAN ID | Payload location | Observed hex value/change | Narrated association | Evidence and status |
| --- | --- | --- | --- | --- |
| `0x113` | Byte 6 (index 5) | `00` | E riding mode | Repeated returns to E across both video parts; **stronger candidate, unconfirmed** |
| `0x113` | Byte 6 (index 5) | `03` | D riding mode | Repeated D selections across both parts; **stronger candidate, unconfirmed** |
| `0x113` | Byte 6 (index 5) | `01` | S riding mode | S selections in both parts; **stronger candidate, unconfirmed** |
| `0x113` | Byte 6 (index 5) | `04` | Reverse selected | One narrated reverse episode, followed by return to `00`; other fields change too; **tentative** |
| `0x113` | Byte 2 (index 1) | `00 → 01` | Ready / drive-enabled state | Near ready announcements in both parts; exact interlock/state semantics unknown; **tentative** |
| `0x112` | Bytes 1–2 (indexes 0–1) | Varying raw bytes; baseline `00 00` | Throttle-related activity | Changes near throttle exercises; could represent speed, current or another correlated quantity; **unresolved** |
| `0x221` | Byte 1 (index 0) | Varies from baseline `00` | Throttle-related activity | Changes during the same exercises; **unresolved** |
| Not identified | Not identified | No assigned value | Left/right indicators, hazards, horn, high beam | No convincing mapping established in this comparison. **Not observed/decoded**, not proof of absence from CAN |

The mode candidates describe observed status; they are not commands. No bit mask has been validated for these fields. Byte order, signedness, scale, offset and engineering units for the varying multi-byte channels are unknown. No throttle percentage or speed/current calibration is claimed.

## Narrated mode sequence and observed transitions

Times are seconds from the CSV recording start. Video locations are approximate, derived from embedded creation times rather than a shared synchronization signal.

| CSV time (s) | Video part / approximate elapsed time | ID | Payload byte | Hex value | Narrated association |
| --- | --- | --- | --- | --- | --- |
| 41.629 | Part 1 / 00:57.27 | `0x113` | 2 | `01` | Ready announcement |
| 49.406 | Part 1 / 01:05.05 | `0x113` | 6 | `03` | D |
| 52.133 | Part 1 / 01:07.77 | `0x113` | 6 | `00` | E |
| 53.648 | Part 1 / 01:09.29 | `0x113` | 6 | `01` | S |
| 55.567 | Part 1 / 01:11.21 | `0x113` | 6 | `00` | E |
| 57.184 | Part 1 / 01:12.83 | `0x113` | 6 | `03` | D |
| 59.001 | Part 1 / 01:14.64 | `0x113` | 6 | `00` | E |
| 94.148 | Part 1 / 01:49.79 | `0x113` | 6 | `04` | Reverse candidate |
| 96.876 | Part 1 / 01:52.52 | `0x113` | 6 | `00` | Return from reverse candidate |
| 205.613 | Part 2 / 00:04.25 | `0x113` | 2 | `01` | Ready announcement |
| 215.613 | Part 2 / 00:14.25 | `0x113` | 6 | `03` | D |
| 217.733 | Part 2 / 00:16.37 | `0x113` | 6 | `00` | E |
| 218.945 | Part 2 / 00:17.59 | `0x113` | 6 | `01` | S |
| 220.763 | Part 2 / 00:19.40 | `0x113` | 6 | `00` | Return state consistent with E; narration less clear |

One reverse-associated sequence illustrates why assigning only one field is incomplete:

| CSV time (s) | Full `0x113` payload |
| --- | --- |
| 94.148478 | `00 01 02 00 00 04 00 00` |
| 94.250214 | `00 01 01 00 00 04 00 00` |
| 96.876007 | `01 01 00 00 00 00 00 00` |

Interpretations of bytes 1 and 3 in this sequence remain open.

## Raw activity during throttle tests

![Raw CAN candidate channels during throttle exercises; no speed or throttle-position decode established](images/2026-10-25-throttle-related-candidates.png)

The left panels show the recording as a whole; the right panels enlarge the first exercise. Green shading marks approximate narrated throttle windows, and gray marks the interval without video. Axes show raw numeric values, **not throttle percentage, mph, km/h, RPM or amperes**.

| Candidate | Plot interpretation | Observed range | Largest peak |
| --- | --- | --- | --- |
| `0x112`, bytes 1–2 | Assumed unsigned 16-bit little-endian: byte 1 + 256 × byte 2 | 0–2,958 | CSV 73.636 s |
| `0x221`, byte 1 | Unsigned raw byte | 0–43 | CSV 73.644 s |

Both traces show a small pulse around CSV 66–68 s, then a larger rise and return to zero around 70–76 s. Activity also appears around 211–213 s and 228–230 s. The later episode's precise narrated association remains unresolved.

**Was speed captured? Possibly, but no signal is confirmed as speed.** The similar shapes make these useful candidates for related measurements or differently scaled representations. They could reflect motor/wheel speed, throttle demand, current or another correlated quantity. Byte order and field interpretation for `0x112` are plotting assumptions, not validated definitions. The observed peaks are not evidence of 43 mph or 2,958 RPM.

The rear-wheel motion and independently displayed speed were not established in this analysis. Establish those references before assigning a physical quantity or units. These plots do not reconstruct the rider's hand position and do not resolve earlier electrical/error concerns.

## Initial battery telemetry candidates — unconfirmed

Further analysis of the same private short capture suggests battery fields with useful internal consistency. **These are hypotheses derived from this dataset, not published OEM definitions or independently validated battery measurements.** They must not be used to assess charging safety, battery health or serviceability.

Public comparison sources provide context rather than these byte definitions:

- [BeeDash](https://electricmotogarage.com/beedash/app/) reports pack-voltage, state-of-charge and cell-group decoding. The inspected page does not publish the CAN layouts or formulas below.
- [Battery Reviver](https://electricmotogarage.com/products/surron-battery-reviver/) describes 20 Ultra Bee cell groups. Its illustrative demo values are explicitly fabricated and were not used as calibration evidence.
- [BraapZap](https://www.braapzap.com/post/surron-ultrabee-canbus) tentatively describes J1939-style PGN 57344 (`0xE000`). Our extended `18E000xx` / `18E00100` identifiers are compatible with that identifier interpretation, but this does not establish their payload meanings or identify the physical sender. The battery candidates below use different, standard-format IDs.

### Candidate battery fields

Positions are **one-based**, with zero-based indexes in parentheses. All listed IDs are standard 11-bit frames with DLC 8 in the analysed capture.

| CAN ID | Payload location | Proposed interpretation | Observed evidence | Status |
| --- | --- | --- | --- | --- |
| `0x102` | Bytes 1–2 (indexes 0–1) | Unsigned little-endian ÷ 10, hypothesised pack volts | Raw 793–799 → **79.3–79.9 V**; close to the sum of proposed cell-group readings | Internally corroborated candidate; unconfirmed |
| `0x103` | Byte 5 (index 4) | Unsigned reported state of charge, hypothesised percent | `46` hex = **70 decimal** in 11,025 records; remaining 597 records contain zero. Owner recalls roughly 70% or more, not an exact independent reference | Tentative; zero/stale/sentinel semantics unresolved |
| `0x203` | Byte 1 (index 0) | Selector `80`–`84` | Five rotating selector values | Observed structure; meaning unconfirmed |
| `0x203` | Bytes 2–8 (indexes 1–7) | Four packed unsigned 14-bit little-endian values per selector, hypothesised millivolts | Five groups × four values = **20**; plausible cell values, matching sum and extrema | Internally corroborated candidate; unconfirmed |
| `0x205` | Bytes 1–2 and 4–5 (indexes 0–1 and 3–4) | Unsigned little-endian maximum/minimum cell-group millivolts | First comparison gives **4020 / 3961**, matching the proposed cell-array extrema | Internally corroborated candidate; unconfirmed |

For the `0x203` hypothesis, interpret bytes 2–8 as one little-endian unsigned integer `p`. The four candidate values are `(p >> (14 × i)) & 0x3FFF`, for `i = 0, 1, 2, 3`. There is no additional scaling if these values are millivolts. This describes a proposed receive-side interpretation, not a command.

Ordering selectors `80` through `84`, then their four fields, creates a logical array. **The physical cell-group numbering is not verified.**

### First complete five-selector set

The following set completed at CSV **7.060853 s**. Values were collected across a rotating cycle, not sampled simultaneously.

| Selector, hex | Four candidate cell-group values, mV |
| --- | --- |
| `80` | 3982, 3986, 3986, 3969 |
| `81` | 3988, 4017, 4018, 4020 |
| `82` | 4017, 4015, 3973, 3961 |
| `83` | 3975, 3978, 3975, 4012 |
| `84` | 4012, 4012, 4012, 4015 |

- Candidate cell sum: **79.923 V**, versus **79.9 V** from the contemporaneous `0x102` interpretation.
- Candidate minimum/maximum: **3961 / 4020 mV**, also matching the proposed `0x205` fields.
- Candidate spread for this set: **59 mV**. This is not a battery-health judgement.

Across **1,153 overlapping rolling comparisons**, with all five selectors no more than 1.2 seconds apart, the median cell-sum minus candidate pack voltage was **+0.020 V**; the range was **−0.259 to +0.281 V**. These are correlated snapshots, not independent experiments. Asynchronous updates and changing load are possible explanations for differences, not proven causes.

The proposed cell values span **3926–4021 mV** across those snapshots. Median differences between calculated extrema and the candidate `0x205` maximum/minimum were both **0 mV**. Agreement between fields strengthens a hypothesis but does not replace an independent voltage reference.

### Battery validation still needed

Confirm a simultaneous dashboard SOC and trustworthy pack-voltage reference, then repeat at another normal charge level. Validate stale/sentinel behaviour, cell ordering and timing before implementing a supported decoder. Temperature, state of health, remaining capacity and battery-current definitions are **not established by this comparison**. Earlier electrical-reference and receive-error limitations still apply.

Raw recordings, identifying payloads, device serials, local paths and video location metadata remain private.

## Timing limitations

The approximate relationship is:

- Part 1: CSV seconds ≈ video seconds − 15.642.
- Part 2: CSV seconds ≈ video seconds + 201.358.

These assume the phone and laptop clocks agree. Embedded creation times have one-second precision, CSV timestamps are host-side, and narration/action offsets vary. Decimal places locate the original records; they do not imply sub-second synchronization accuracy.

Part 1 lasts 122.795 seconds and part 2 lasts 30.050 seconds. There is approximately **94.2 seconds without video** between them. CAN changes in that interval have no narrated association and must remain unassigned.

## What would confirm or reject these candidates?

1. Document bike/electronics revisions, connector viewing direction and the reviewed electrical setup, with identifiers redacted.
2. Repeat stationary E → D → E → S → E selections, holding each displayed mode for ten seconds and filming the display clearly.
3. Test ready/not-ready separately from mode selection, including normal interlocks without bypassing them.
4. Repeat reverse selection separately; distinguish selection status from motion.
5. Separate throttle demand from motor/wheel speed and current using independent references before assigning units.
6. Run a dedicated lighting-control capture if needed; absence of a decoded match is not evidence that no message exists.
7. Assess receive errors and prepare redacted replay evidence before promoting definitions into a supported decoder.

Keep subsequent capture work listen-only. No mapping here is admitted as **Bee-Link verified**, and no cross-variant compatibility is claimed.

[Back to the research register](../research.md)
