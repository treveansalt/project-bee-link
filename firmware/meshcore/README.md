# On-bike MeshCore module — XIAO ESP32S3 + Wio-SX1262 + L76K

Experimental firmware overlay for **Project Bee-Link / Surron Ultra Bee only**. It runs on the bike's XIAO, uses the Wio-SX1262 directly through MeshCore, reads the L76K, and schedules private-channel text without a home receiver. This is a bench prototype, not complete CAN/GPS/SD capture firmware or a validated bike installation.

## Hardware finding: do not assume the boards can simply stack

The [Seeed kit documentation](https://wiki.seeedstudio.com/wio_sx1262_with_xiao_esp32s3_kit/) identifies its B2B radio connection. The [pinned official MeshCore board configuration](https://github.com/meshcore-dev/MeshCore/blob/a366955cb2f67b8e6842d4f00d2b6a554dddd88a/variants/xiao_s3_wio/platformio.ini) specifies radio SPI SCK/MISO/MOSI as GPIO7/8/9. Seeed's [XIAO pin reference](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/) maps D10 to GPIO9.

The [L76K V1.0 schematic, pages 2–3](https://files.seeedstudio.com/wiki/Seeeduino-XIAO-Expansion-Board/GPS_Module/L76K/109100021-L76K-GNSS-Module-for-Seeed-Studio-XIAO-Schematic.pdf) connects GNSS reset to the corresponding D10 header position through a diode. **Radio MOSI and GNSS reset therefore overlap in an unmodified stack.** Prediction: radio SPI activity can pull GNSS reset low. This conclusion comes from published design documents; continuity and behaviour on the owner's board have not been measured.

Use an interposer or separate wiring arrangement that isolates the GNSS D10 reset connection from the radio's MOSI. Have the GNSS reset remain correctly biased according to its design; verify the actual revision and continuity before connecting. This firmware never drives GNSS reset on D10. Merely changing a software pin definition does not remove the hardware connection. Compilation deliberately requires `BEELINK_GNSS_RESET_ISOLATED=1`; that acknowledgement is not an electrical test.

| Function | Documented assignment / status |
| --- | --- |
| Radio SCK / MISO / MOSI | GPIO7 / 8 / 9; use upstream XIAO kit target |
| Radio NSS / DIO1 / reset / busy | GPIO41 / 39 / 42 / 40, upstream target |
| GNSS UART at host | RX D7/GPIO44; TX D6/GPIO43; 9600 baud |
| GNSS wake | D0/GPIO1, reserved and held high |
| GNSS reset | D10/GPIO9 conflict; must be isolated from MOSI |
| CAN transceiver | Not chosen or wired; no assignments or CAN transmission |
| SD | Not implemented here; plan SPI arbitration, CS and pin budget first |

GNSS UART assignments and default baud come from [Seeed's L76K guide](https://wiki.seeedstudio.com/get_start_l76k_gnss/). The radio target is specifically the ESP32S3 kit, not the nRF52840 header version. No regional RF profile, range or power-consumption claim is validated by this overlay.

## Implemented behaviour

- Disabled after every reboot. Settings live in RAM. USB controls can enable/disable and choose 15–1440 minutes.
- First attempt waits a full interval plus 0–60 seconds jitter; each attempt starts another full interval. Failed/missed attempts have no replay queue or retries.
- Disabling prevents future attempts; a packet already queued inside MeshCore cannot be recalled.
- Private channel 1–7 only; explicit operator acknowledgement, non-empty/non-zero key, rejection of upstream's known public key, and key pinning at enable. A changed channel key disables the module rather than redirecting telemetry.
- Separate GPS-location opt-in. GNSS speed may be sent without coordinates. Each reading must be verified, finite, within bounds, at most 60 seconds old and not simulated. Coordinate captures must match within five seconds.
- Fresh GNSS UTC required for outgoing messages. UTC is independent of MeshCore's fallback boot clock. Without current trusted time, the attempt is skipped, including a battery-only attempt.
- Compact ASCII text up to 120 bytes. `submitted` means MeshCore queued the packet, not confirmed reception. Upstream MeshCore performs encryption/routing; this overlay does not reimplement either.
- No auto position advertisements from the GNSS parser, no telemetry-body logs and no remote mesh control of enable/location/settings. USB companion commands are local device access. Normal upstream companion functions still exist independently.

`beeLinkVerifiedSoc(percent, capture_monotonic_ms)` is the integration point for a **future validated CAN decoder**, called from the main loop task, never an ISR. No CAN mapping is supplied. Until that producer exists, messages omit `BAT`; they never use the XIAO's own power supply measurement as bike battery SOC. Speed in this prototype comes from GNSS, not an asserted CAN field.

## Build without flashing

Prepare a fresh disposable clone of the upstream source, pinned to the reviewed revision:

```sh
git clone https://github.com/meshcore-dev/MeshCore.git MeshCore-beelink
git -C MeshCore-beelink checkout a366955cb2f67b8e6842d4f00d2b6a554dddd88a
python firmware/meshcore/prepare_build.py MeshCore-beelink
python -m pip install platformio==6.2.0
```

The overlay script refuses another revision or a dirty clone. It copies the module and hooks into the companion main loop and local command handler, preserving upstream MeshCore and board support. The target is `BeeLink_Xiao_S3_WIO`, with USB companion access and no display/BLE/Wi-Fi requirement. It does not use the companion hardware UART, which would clash with the GNSS UART.

After the reset wiring has been checked, set the acknowledgement for compilation:

```sh
export PLATFORMIO_BUILD_FLAGS='-D BEELINK_GNSS_RESET_ISOLATED=1'
pio run -d MeshCore-beelink -e BeeLink_Xiao_S3_WIO
```

PowerShell equivalent: `$env:PLATFORMIO_BUILD_FLAGS='-D BEELINK_GNSS_RESET_ISOLATED=1'`. Do not use the flag as a substitute for isolation. Building has no radio side effect. No flashing command or ready-to-flash binary is provided as a validated release. First hardware bring-up must be on an isolated bench with matching antennas, correct supply and your established regional MeshCore settings, before any bike connection.

On Windows, keep the clone and PlatformIO core paths short. The Xtensa compiler failed to launch from the long synced-project path during development; short local path aliases resolved it without a source change.

## User enable/disable

Configure a private channel in slot 1–7 through the usual MeshCore USB client before enabling. The secret stays in the node's MeshCore channel store; do not send it to GitHub. Disconnect other clients sharing the USB port. These controls require `pyserial==3.5`:

```sh
python firmware/meshcore/control.py /dev/ttyACM0 status
python firmware/meshcore/control.py /dev/ttyACM0 enable --channel 1 --interval 15 --private-channel
# Separate location opt-in:
python firmware/meshcore/control.py /dev/ttyACM0 enable --channel 1 --interval 15 --private-channel --location
python firmware/meshcore/control.py /dev/ttyACM0 disable
```

Use the appropriate COM port on Windows. Port-opening behaviour is driver dependent; a reset starts disabled. No `send now` exists. Private keys derived from public names or shared outside the intended group cannot be detected as private by software; use a genuinely private key and verify membership yourself.

The current browser dashboard controls operate the **Python receiver bridge**, not this ESP32. On-bike web/BLE controls are pending. USB control is the implemented firmware user interface. Do not enable both transmitters for the same bike; otherwise each has an independent interval.

## Validation and remaining work

The full XIAO ESP32S3 firmware cross-build and final link passed. See the [validation record](VALIDATION.md) for tool versions, measured build size and explicit limits. Compilation used the isolation macro to check code; physical wiring remains unverified and nothing was flashed.

The Mac's local Qwen2.5 Coder model drafted the interval gate. Review found it omitted the interval after the first attempt; the repaired code is covered by native Mac C++ tests. Native policy tests exercise delay, jitter bounds, disabling, no backlog, long uptime, stale/future/simulated readings, coordinate coherence, UTC gating and default privacy. Python tests cover local command encoding and framed replies. These are synthetic tests, not radio or GNSS measurements.

Still required: board continuity/reset isolation, actual GNSS acquisition, channel reception and RF/airtime settings, settings UI integration, protected listen-only CAN hardware/decoder, SD logging, bus arbitration, task latency, power budget/sleep and reboot/power-loss behaviour. This prototype must not replace the complete capture design in [the ESP32 contract](../../app/docs/esp32.md).
