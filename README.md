# comma.ai engineering portfolio — work in progress

This folder contains AI-assisted source, experiments and measured results for
the PCBGolf and original-CAN-core requests. **Neither requested project is
complete. These are work-in-progress portfolio artifacts, not a finalized
PCBGolf solution. No board has been fabricated or tested on hardware.**

## Reviewer entry points

- [Submission status and reproducibility](SUBMISSION.md): current evidence and known failures.
- [Classical CAN RTL and tests](can-core/README.md): simulation-tested bit-level engines.
- [PCBGolf layout experiments](pcbgolf/README.md): native KiCad projects and assembly exports.
- [Verification status](reports/STATUS.md): explicit completion gates.

## What works now

- `WORKING_PROMPT.md`: the prompt applied to guide the work.
- `can-core/`: original transmit/receive SystemVerilog bit-level engines, an
  independent polynomial-division Python oracle and deterministic simulation tests.
- `pcbgolf/`: source inventory, deterministic placement experiment, unchanged
  libraries, integrated schematics and editable KiCad placement/routing trials.
- `reports/`: tool logs and project status.

The CAN simulation suite passed 2,386 cases: 777 valid receive vectors, 770
transmit vectors, 496 receive fault/recovery cases, 100 back-to-back frames,
127 reset positions, 113 arbitration scenarios and three transmitter faults.
Twenty-six receive cases exercise a stuff bit immediately after the CRC sequence.
These are simulation results, not hardware or ISO compliance claims. Both RTL
modules also passed generic Yosys synthesis and structural checks with no
reported problems. FPGA mapping/timing remain unverified; see reports/STATUS.md.

The PCB placement experiment produced a 70 × 60 mm outline with all 245 original
footprints and their pad/net assignments retained. Its all-net half-perimeter
wirelength proxy decreased from 10,780.574 to 7,685.120 mm (28.71%). That is an
optimization of a proxy, **not a reduction in measured board score**. It has
zero routed tracks. Native KiCad now works: an assembly STEP was exported and
measured at 70 × 60 × 12.595 mm. This is an unrouted geometry measurement, not
a valid contest score. The integrated routing trial has repaired schematic
hierarchy and zero schematic/PCB parity errors; 499 unconnected items remain.

## Blocking completion

PCB: KiCad 10.0.6 runs from the local tools directory. The candidate still needs
mechanical/functional placement review, complete routing, native ERC/DRC,
fabrication-rule checks, assembly collision checks and an actual score. A leaderboard
entry would be misleading at this stage. Published prize deadline: October 12,
2026; current date: October 20. Late leaderboard acceptance is unconfirmed.

CAN: the core still needs bit timing/resynchronization, integrated bus access,
error frames/confinement/recovery, register/FIFO interface and FPGA constraints.
Extended CAN and CAN-FD are not implemented. No hardware is available.

The experiments suggest follow-up hypotheses, but an online search did not
establish that either is new. Existing work already includes AI placement,
autorouting, multi-board stacking and aggressive connector changes.

## Cheapest hardware starting point

As checked October 15, 2026: Tang Nano 9K was listed at $14.90 by Seeed, but out
of stock. It is a low-cost candidate for developing a small original controller;
a complete future CAN-FD design's fit and timing have not been established.
Sipeed documents its 8,640 LUT4 resources and onboard programming interface.
A Waveshare SN65HVD230 3.3 V Classical-CAN transceiver board was listed at $4.99.
That is about $20 excluding shipping, wiring and a second independent CAN node.
The SN65HVD230 is not the choice for validating high-rate CAN-FD.

Start with free simulation. Confirm FPGA fit and available seller inventory
before buying. Buy a CAN **transceiver** for the FPGA, not an MCP2515 controller
module that would implement the protocol externally. An independent MCU CAN
node or USB-CAN adapter is useful later as a reference peer.

Sources:
- https://wiki.sipeed.com/hardware/en/tang/Tang-Nano-9K/Nano-9K.html
- https://www.seeedstudio.com/tag/FPGA-Development-Board.html
- https://www.waveshare.com/product/sn65hvd230-can-board.htm
- https://github.com/commaai/PCBGolf
- https://comma.ai/leaderboard
- https://github.com/Logic-Design-Services/CTU-CAN-FD

## Application use

Do not describe this as a completed contest entry or an independently built,
production-ready CAN-FD controller. A defensible current description is:
“Developing an AI-assisted Classical CAN RTL prototype; I am reproducing and
reviewing its fault-injection tests and extending it toward hardware validation.”
Use that wording only after you have actually reproduced/reviewed the tests.
The final application should explain your own decisions, measurements and
contributions, with AI assistance disclosed accurately. No application email
has been prepared or sent.

Latest work (October 20): `pcbgolf/critical-trial/` groups 47 components by
circuit on the underside. It shortens critical switcher/clock pad distances and
has zero schematic-parity issues, but all 499 connections remain unrouted.
Its assembly envelope is 70.4 × 60.4 × 14.230 mm. The old placement's separate
`partial-route/` contains an incomplete routing diagnostic with 339 unconnected
items and six width violations. Neither is fabrication-ready or a submission.
