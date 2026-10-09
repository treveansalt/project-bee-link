# Next steps

The immediate Bee-Link milestone is to obtain a **safe, passive CAN capture from a stock Surron Ultra Bee** before attempting any CAN transmission or T-box emulation.

## 1 — Access the stock CAN bus without removing the T-box

For the first capture, keep the OEM T-box connected and tap CAN-H/CAN-L **in parallel** so the bike remains in its normal factory configuration.

Preferred physical methods, in order:

1. A reversible Y/pass-through harness between the bike loom and T-box.
2. Automotive back-probe pins inserted at the rear of the connected T-box connector.
3. Temporary probe clips only where there is no realistic risk of adjacent-pin shorts.

Avoid piercing insulation or making permanent loom changes during discovery.

A published QL-TBOX-JM reference indicates CAN_L on pin 3 and CAN_H on pin 6, but **do not treat that as specimen-verified Bee-Link data**. Confirm connector orientation, pin numbering and wire colours on the actual Ultra Bee before making a connection.

## 2 — Connect the CAN analyser

Initial development hardware: **DSD TECH SH-C31G isolated USB-CAN adapter**.

- Power the SH-C31G from USB only.
- Initially connect only CAN-H and CAN-L.
- Leave the adapter's 120 Ω termination **OFF** when attaching to the existing vehicle bus.
- Do not connect or inject vehicle power into the analyser unless a later validated design specifically requires it.

With the bike completely powered down, measure resistance between the suspected CAN-H and CAN-L lines. Approximately 60 Ω is consistent with a normally terminated two-end CAN bus, but is supporting evidence rather than proof of identity.

## 3 — Capture the untouched stock bike

Make the first trace with all OEM modules, including the T-box, connected.

Suggested initial captures:

- key/display on, stationary, no controls touched;
- front brake on/off;
- rear brake on/off;
- ride-mode changes;
- controlled throttle movement where safe;
- rear wheel rotation where safely supported;
- normal charging, if that interface is part of the tested bus.

Each capture should record timestamp, full arbitration ID, standard/extended frame flag, DLC and raw payload.

## 4 — Repeat with the T-box disconnected

Only after a clean stock baseline exists, repeat comparable stationary captures with the T-box unplugged if the bike powers normally.

Compare:

- arbitration IDs present/absent;
- message frequencies;
- payload changes;
- bus errors;
- display/fault behaviour;
- sleep/wake behaviour.

Frames that disappear or materially change become candidates for T-box-originated or T-box-dependent traffic. This does not, by itself, prove message ownership.

## 5 — Build a reusable development harness

Once the connector is positively identified, build a small reversible Bee-Link development harness:

```text
Bike loom
   │
   ├──────── OEM T-box
   │
   └──────── CAN-H / CAN-L breakout
                 │
             SH-C31G / future Bee-Link gateway
```

The aim is repeatable capture without repeated back-probing or loom damage.

## Exit criterion

This milestone is complete when we have:

- a verified specimen-specific CAN access point;
- a repeatable receive-only capture method;
- at least one clean stock trace;
- a matched T-box-connected / T-box-disconnected trace;
- documented connector photos, measurements and analyser settings;
- no observed disruption caused by the logger.

No active CAN transmission should be introduced before these captures have been reviewed.
