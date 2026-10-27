# golf-v2: low-profile connector redesign

**Work in progress. Routing is incomplete, so there is no valid score.** See "Status" below.

`golf-v2/` keeps the four-layer trial's repaired schematic (ERC clean) and changes
the connectors and layout to cut the assembly height, which drives the score.

## What changed

| Item | Before | After | Why |
|---|---|---|---|
| OBD-C ports J5–J8 | Amphenol 10132328 vertical, 8.8 mm above board | JAE DX07S024XJ1R1100 horizontal, 3.4 mm | Same 24-pin receptacle the original design uses for host port J3. Horizontal ports are allowed (commaai/PCBGolf#4) |
| Port spacing | 12.85 × 7.0 mm grid | 12.85 mm centres along the top edge, faces flush | Minimum USB-C plug spacing (commaai/PCBGolf#9) |
| 12 V jack J1 | PJ-002AH-SMT-TR, 11.0 mm above board | Same Sky PJ-107AH-MSMT-TR mid-mount in a board notch | Same 5.5 / 2.0 mm plug (both datasheets show the same mating plug); rated 7 A vs 5 A |
| Mounting holes BH1–BH4 | DNP M2 footprints | Removed from the board | Optional (commaai/PCBGolf#5) |
| Copper layers | 4 (trial) | 2 | +5,000 per layer |
| Placement | One side, 70.4 × 60.4 mm | Both sides, about 50–58 mm square | The jack hangs 2.05 mm below the board, so underside parts ≤ 1.8 mm add no height |

Pad numbers on the new port footprint are renamed to the vertical symbol's pins, so no
schematic net changes. Schematic/PCB parity reports no net differences.

The jack footprint comes from the Same Sky datasheet (2024-09-25): centre pin Ø1.4/2.4 mm,
terminals 2 and 3 as plated slots, shell legs, and a 10.3 mm wide notch. The front face
overhangs the edge by 1.2 mm as the datasheet layout shows. Its 3D model is the
manufacturer's STEP. In the assembly the jack spans z = −2.05 to +7.05 mm (board 0–1.6).

## Rules and net classes

JLCPCB standard 2-layer limits with margin: 0.127 mm track and clearance, 0.6/0.3 mm vias,
0.3 mm copper to edge. The DX07 footprint's B-row holes have a 0.1 mm annular ring.
That is comma's own footprint (also used for J3), so the minimum is set to 0.1 mm.

| Class | Width | Nets |
|---|---|---|
| HighCurrent | 1.2 mm | +12V, jack input |
| PortPower | 0.8 mm | the four switched port VBUS nets (eFuse limit 3.06 A each) |
| Power | 0.4 mm | +5V, +3V3, GND, host VBUS, buck switch nodes, SMPS |
| Default | 0.15 mm | everything else |

The router may neck down to 0.127 mm at fine-pitch pins.

## Scripts (reproducible)

1. `make_golf_v2.py four-layer-trial golf-v2 PJ-107AH-MSMT-TR.step`: copies the project,
   writes both footprints, updates J1, J5–J8 and BH1–BH4 in the schematic, sets rules and classes.
2. `place_golf_v2.py golf-v2 golf-v2-bodies.json --width W --height H` (KiCad Python): swaps
   the PCB footprints by pad number, draws the notched outline, fixes connectors on the edges
   and anneals the rest over wirelength with body/courtyard rectangles on each side.
   `golf-v2-bodies.json` holds body sizes measured from the 3D models.
3. `route_golf_v2.py export|import` (KiCad Python): Specctra round trip for Freerouting,
   with GND pours on both layers so GND is treated as a plane.
4. `score.py golf-v2/pcbgolf.kicad_pcb ASSEMBLY.step`: score estimate from the STEP.

## Status — October 26

Committed layout: 58 × 56 mm board, both sides, routed by Freerouting for 12 passes (90 min).

| Check | Result |
|---|---|
| ERC | 0 violations |
| Schematic parity | No net differences; one field warning (J1 datasheet URL) |
| Assembly STEP (`golf-v2-PARTIAL.step`) | 58.0 × 57.2 × 9.11 mm = 30,236 mm³ |
| Vias / layers | 160 vias (8,000) / 2 layers (10,000) |
| Score estimate as committed | **48,236**, but **not valid**: routing is incomplete |
| Unconnected items | 213: 75 GND islands after the pour fill, 138 signal/power connections |
| DRC errors | 199 router neck-downs below 0.127 mm (0.06–0.11 mm), 45 single-spoke GND thermals, 1 clearance (eFuse U13) |

For comparison, the old layout was at least 70,569 before any routing. Height is now
9.11 mm (set by the jack) instead of 14.24 mm.

### What was learned routing it

- A 50 × 49 mm placement (22,877 mm³, about 33k before vias) would not route:
  Freerouting stalled around 300 unrouted connections. A four-layer version stalled too.
- Two causes: power-class widths (0.4–1.2 mm) cannot enter 0.5 mm-pitch pins without
  neck-down, and courtyard-to-courtyard packing left no escape room (72% pin escape).
  Neck-down plus a routing margin of 0.15 mm × √pins raised pin escape to 83%.
  Unrouted connections then fell by about 5 per pass, but did not converge.
- Board area beyond 58 × 56 did not help (62 × 58 performed the same).

### Remaining before a submission

1. Finish the 138 open connections (interactive routing in KiCad, or longer router runs
   resumed from `golf-v2-router/` with `-de golf-v2.dsn+golf-v2.ses`; Freerouting 2.5 with `--router.automatic_neckdown=true --router.scoring.via_costs=200`), and reroute the sub-0.127 mm neck-downs.
2. Stitch the 75 GND islands. Each stitching via costs 50, so join islands with top
   copper where possible.
3. Re-run DRC (zero errors), export the final STEP, check port plug clearance, then score.
4. Shrink the outline again once routing is known to close.
