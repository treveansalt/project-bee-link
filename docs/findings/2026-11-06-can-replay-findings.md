# Ultra Bee CAN replay and observations — 6 November 2026

> **Research preview, not validated vehicle telemetry.** These observations come from one owner's bike. The device revisions, signal semantics, scaling, invalid values and compatibility across bikes remain unverified. Do not use these candidates for vehicle control or safety decisions.

[Watch the silent CAN replay](images/2026-11-06-can-replay.mp4) · [Earlier observations](2026-10-25-initial-can-observations.md)

The 49-second animation replays approximately 290 seconds of the recording at six times speed. The strip below the dashboard displays the **selected latest recorded bytes**, in hexadecimal, used for the corresponding values above it. It is a derived replay of a single recording, not independent proof of signal identity, signal quality, live reception or real-world speed. It contains no original phone footage or audio. Raw CAN records and source media are not published.

## Capture context

An owner-operated SH-C31x v1.5 capture was exported from diCAN as 500 kbit/s classic CAN in Silent mode. The export contains 130,350 Rx records over approximately 291 seconds, spanning 33 identifiers, and no Tx records. Its filtered-scope metadata records no active filter. Silent mode is software-reported and has not been independently verified electrically. Previous receive errors were observed; this recording's dropped-frame count is unknown. No inter-record gap exceeded 0.5 seconds, which does not prove a lossless capture.

The owner narrated controls while filming the display. The rear wheel was raised during the wheel-speed exercises: dashboard speed in that portion is not actual road speed. Video and CAN clocks were not hardware-synchronised. Exact bike, controller, battery and module revisions remain to be recorded. Physical signal reference/ground and permanent-installation electrical behaviour remain unresolved.

## Candidate signals

All examples use standard 11-bit IDs and 8-byte frames. Byte positions are one-based; indexes in parentheses are zero-based. Status labels reflect correlation, not OEM documentation or independently verified measurements.

| ID / field | Working interpretation | Evidence | Limitations |
| --- | --- | --- | --- |
| `0x113` byte 6 (5) | `00` E, `03` D, `01` S, `04` reverse | Repeated mode changes and reverse lamp/narration in this and the earlier capture | Provisional status mapping; not a command. Other fields change in reverse. |
| `0x113` byte 2 (1) | READY-related state | `00 → 01` near READY indication | Exact interlock semantics unknown. |
| `0x102` bytes 1–2 (0–1) | Little-endian unsigned / 10, candidate pack voltage in V | Approximately 78.4 V near beginning, close to candidate cell-group total; fell under exercise and recovered | No independent voltage measurement or invalid-value specification. |
| `0x203` selector byte 1 (0), packed bytes 2–8 | Selectors `80`–`84`; four little-endian 14-bit candidate group millivolt values per selector | Five selectors make 20 logical values; sum and extrema agree with other candidate fields | Physical group numbering, sentinel values, timing and units unverified. |
| `0x205` bytes 1–2 and 4–5 | Little-endian candidate max/min group millivolts | Correspond to computed extrema at quiet snapshots | Provisional; measurements are not simultaneous. |
| `0x221` byte 1 (0) | Raw unsigned value assumed km/h, multiplied by 0.621371 for an estimated mph readout | At sampled dashboard values of about 5, 11, 15 and 22 mph, corresponding raw values near approximate alignment were 9, 18, 25 and 34 | **Provisional wheel-speed estimate**, not verified road speed. Dynamic samples did not consistently align; latency, scaling, invalid values and display rounding need validation. |
| `0x112` bytes 1–2 (0–1) | Vary with wheel movement | Rise and fall during throttle tests | Unknown scale and meaning. Not a validated throttle percentage. |
| `0x204`, selector `E1`, byte 7 (6) | Raw value rose from 55 to 60 | Slow change during session; storage ambient estimated around 15 °C | Exploratory raw-Fahrenheit assumption yields 12.8–15.6 °C; Celsius with an offset is another possibility. Neither unit nor motor/battery sensor identity is known. |
| `0x103` byte 5 (4) | Unknown | Remained `46` hex (70 decimal) while dashboard displayed roughly 99–96% | Prior SOC hypothesis is **contradicted**. A battery-percentage mapping remains unidentified. |

## Example battery snapshot

At a quiet point approximately 30 seconds into the recording, the 20 proposed group values were:

| Selector | Candidate group values (V) |
| --- | --- |
| `80` | 3.909, 3.912, 3.913, 3.896 |
| `81` | 3.914, 3.943, 3.943, 3.945 |
| `82` | 3.946, 3.943, 3.901, 3.890 |
| `83` | 3.902, 3.906, 3.902, 3.938 |
| `84` | 3.940, 3.939, 3.938, 3.940 |

The sum is 78.460 V; the separate candidate pack field was 78.4 V. Candidate minimum/maximum were 3.890/3.946 V, a 56 mV spread. These are logical selector order, not confirmed physical cell numbers. They are parallel-group readings, not individual-cell measurements. The values arrive across a rotating cycle and must not be used to assess battery condition or charging safety.

The candidate pack value fell from roughly 78.2 V to 75.6 V during the narrated S-mode exercise and recovered. During rapidly changing load, sequential frames can mix different moments; the largest apparent computed group spread in the recording is therefore not established as a real instantaneous spread.

## Sample timing and follow-up

Median host-observed intervals were approximately 20.1 ms for `0x102`, 200.8 ms for individual `0x203` messages and 200.8 ms for `0x205`. Each `0x203` selector recurred about every 1.004 seconds; one selector had a roughly two-second gap. These timings are capture-specific and do not prove no frame loss.

Further work should independently verify displayed speed over stable points and a safe external reference, test temperature fields against known temperatures, confirm pack voltage and group numbering, and capture SOC at known display levels. Separate captures of brake regen, coasting regen, traction control and throttle sensitivity are needed. These settings may differ by variant. Keep captures receive-only, preserve raw timestamps and identify missing or stale groups.

The application has an **opt-in** one-specimen experimental speed profile; see [receiver API and profile documentation](../../app/docs/api.md#optional-local-decoder). Its value is not used for road-distance calculation and is not enabled for other variants.
