# PCBGolf work-in-progress portfolio

**Not a completed challenge solution. No valid score or leaderboard eligibility is claimed.**

Prepared for comma.ai's PCBGolf submission form and FPGA & Embedded Engineer
application context. This repository includes AI-assisted engineering work;
it should be evaluated as a prototype and record of experiments.

## Current PCB result

The project preserves the original PCBGolf circuit and explores deterministic
placement, local grouping of power/clock components, schematic integration,
native assembly export and experimental routing. The original design is from
[comma.ai/PCBGolf](https://github.com/commaai/PCBGolf), revision
`d0fd5a71087e3e10a49610f8c3e89912b4d20d77`.

- `pcbgolf/critical-trial/`: complete editable KiCad project for the latest
  unrouted placement experiment, with 47 components regrouped underneath.
- `pcbgolf/critical-UNROUTED.step`: native assembly export, not fabrication approval.
- `pcbgolf/partial-route/`: separate incomplete routing of the earlier layout.
- Latest placement: 499 unconnected items, zero schematic-parity issues,
  139 DRC warnings; assembly envelope 70.4 × 60.4 × 14.230 mm.
- Earlier partial route: 339 unconnected items, six width violations,
  331 warnings and 437 vias.
- Integrated schematic ERC still reports 14 power-drive errors needing review.

**Do not fabricate either trial.** Power integrity, return paths, USB routing,
thermal behavior, mechanical fit and full fabrication rules are not validated.
No online novelty claim has been established. No leaderboard score is supplied.

## Additional FPGA portfolio artifact

`can-core/` contains original Classical CAN transmit/receive bit-level engines
and deterministic simulation tests. The latest rerun passed 2,386 cases.
The CRC reference uses polynomial division rather than the RTL's sequential LFSR;
both model and implementation were produced with AI assistance, so external
protocol validation is still required. No CTU implementation was copied.

This is not a complete CAN controller: bit timing, resynchronization, error
confinement, integrated bus access and FPGA hardware validation remain unfinished.
It does not implement CAN-FD or 29-bit frames.

Reproduce the tests with Python 3.10+ and Icarus Verilog:

```sh
cd can-core
python3 tests/run.py
python3 tests/arbitration.py
```

See [verification status](reports/STATUS.md) and [PCB notes](pcbgolf/README.md)
for reports, methodology, reproduction steps and limitations.
