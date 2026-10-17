# Help and workshop guides

Printable guides for working with Bee Link and investigating the Surron Ultra Bee. These complement the [project wiki](https://github.com/treveansalt/project-bee-link/wiki) and [application documentation](../../app/README.md).

## Ultra Bee CAN workshop guide

**[Open or download the printable PDF](Bee-Link-Ultra-Bee-CAN-Workshop-Guide.pdf)**

Four A4 pages with original schematic illustrations, a reference pin table, checklists and space for handwritten observations:

1. Identify the T-box and connector, including wire colours and viewing-direction checks.
2. Check the suspected CAN pair and record measurements.
3. Prepare a reversible parallel tap with a CAN interface and the OEM T-box retained.
4. Check the setup and record a first passive, stationary capture.

**Version:** 1.0, 17 October 2026. Print at actual size or fit to A4; suitable for black-and-white printing.

**Scope:** identification and passive capture preparation. The QL-TBOX-JM pin table is a manufacturer-document reference, not a Bee-Link-verified pinout for your bike. Confirm the actual module, connector orientation, electrical interface and silent operation before connection. Exact ESP32 pins, interface power/grounding and CAN bitrate depend on the hardware and remain to be established.

The PDF includes its sources. Its diagrams show connection concepts; they are not photographs or a numbered view of the actual connector. No wiring or CAN signal definition is promoted to verified status by this guide.

See also the [capture research next steps](../next-steps.md) and [hardware roadmap](../roadmap.md).
