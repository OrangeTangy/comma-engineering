# Four-layer completion branch

The latest experiment is `four-layer-trial/`. It starts from the underside
critical-circuit placement and adds In1.Cu as an internal GND plane; In2.Cu is
available for routing. The layer penalty increases by 10,000 versus two layers.
This is still a prototype, not a manufacturing release.

## Schematic repair

Native KiCad ERC reports zero violations with power-input drive checks enabled.
The existing ignored checks (including off-grid endpoints and simulation models)
remain ignored; this is not a claim that every possible ERC rule was enabled.
Native schematic/PCB parity reports zero differences. An XML netlist comparison
confirms all 309 original electrical nets retain identical reference/pin members.

The changes affect electrical-type metadata and supply-source assertions only:

- STM32H725 VLXSMPS is the switching output, not a power input.
- TPS25942 OUT pin 4 represents the output driver. Internally common OUT pins
  5–8 are passive, avoiding the false model of five independent supplies.
- USB2517 VDD18 and VDD18PLL represent the internal regulator outputs in this
  design. TEST is an input. External-regulator configurations would require
  revisiting those types.
- MCP2542 VIO is a power input.
- USB connectors, crystals and LED terminals are passive components.
- Supply-source markers document external DC/USB power, ground return,
  the filtered +12 V rail, the two buck outputs and filtered VDDA. They assert
  intended sources, not measured voltages or successful startup.

Datasheet references:
- https://www.st.com/resource/en/datasheet/stm32h725ve.pdf
- https://www.ti.com/lit/gpn/TPS25942A
- https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB2517-USB2517i-Data-Sheet-00001598C.pdf
- https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP2542FD-MCP2542WFD-4WFD-Data-Sheet-DS20005514C.pdf

## Remaining physical gates

A successful autorouter run alone cannot establish these requirements:

1. Zero unconnected copper and no unresolved DRC errors after plane refill.
2. High-current supply paths and thermal copper. Generic signal-width routing
   is not suitable evidence for the four switched port power feeds.
3. USB differential-pair routing/impedance and a concrete manufacturer stackup.
4. Local ground return paths, clock vias, bypass paths and switching loops.
5. Full STEP collision and connector-insertion checks, including simultaneous use.
6. Assembly access, component sourcing and a manufacturable output package.

No contest submission or numeric valid score is claimed.
