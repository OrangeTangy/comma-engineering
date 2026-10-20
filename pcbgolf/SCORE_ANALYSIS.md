# Where the score goes — October 20

Measured with `score.py` (STEP bounding box from OCP, vias and copper layers
from the `.kicad_pcb`). None of these boards is routed and DRC-clean, so none
has a real score. The numbers below are lower bounds that show which levers matter.

| Trial | Size (mm) | Volume | Vias | Layers | Estimate |
|---|---|---:|---:|---:|---:|
| `critical-trial/` (unrouted) | 70.4 × 60.4 × 14.24 | 60,569 | 0 | 2 | 70,569 + vias |
| `four-layer-trial/` (unrouted) | 70.4 × 60.4 × 14.24 | 60,569 | 0 | 4 | 80,569 + vias |
| `partial-route/` (339 unconnected) | 70.4 × 60.4 × 12.61 | 53,615 | 437 | 2 | 85,465 |

Leaderboard on October 20: 10,345 (first), 16,670 (sixth), 57,822 (twelfth),
116,226 (last). Completing the routing of any of these layouts would put the board
near the bottom. The layout architecture limits the score, not the routing.

## Height stack (critical trial, board top at z = 1.6 mm)

| Part | Top z (mm) | Note |
|---|---:|---|
| J1 barrel jack `DCJACK_2MM_SMT` | 12.60 | Tallest part: 11.0 mm above the board |
| J5–J8 vertical OBD-C receptacles | 10.40 | 8.8 mm above the board |
| J3 host USB-C | 4.97 | |
| SW1 push button | 4.70 | |
| Underside regulators and 0805 capacitors | −1.64 | Adds 1.64 mm to the whole board |

Every millimetre of height costs about 4,250 mm³ at this outline. Each via costs 50,
so the 437 vias in the partial route cost more (21,850) than two extra copper
layers (10,000).

## Levers, largest first

Rough volume estimates. Each one still needs a mechanical check.

1. **Horizontal USB-C receptacles for the four OBD-C ports.** These are allowed
   (commaai/PCBGolf#4), but the receptacles must keep 12.85 / 7.0 mm centre
   spacing (commaai/PCBGolf#9). With a lower barrel jack, the assembly
   height drops from ~14 mm to ~5 mm. This is the only change that reaches the
   competitive range.
2. **Barrel jack J1 no taller than the next tallest part.** At the current outline,
   moving from 11.0 to 8.8 mm above the board saves about 9,400. The mating
   2.0 mm plug must still fit (rule: connectors stay mechanically compatible).
3. **Put the underside parts back on top** unless the outline shrinks to pay
   for it. The underside regrouping cost about 7,000 for no area saving.
4. **Stay at two layers (or one).** The four-layer trial adds 10,000. It only
   pays off if it removes more than 200 vias.
5. **Minimise vias.** Set a high via cost in the router. Every through-hole pad
   used only to change layers also counts.
6. **Shrink the outline** after the connectors are moved to the edges. The horizontal
   ports along one edge need about 4 × 12.85 mm of width.

## Review rejection reasons to avoid (commaai/PCBGolf#10, #9, #3)

- Power nets that are not routed wide enough for their current. The existing
  router DSN puts every net, including +12V, +5V and the port VBUS feeds, in one
  0.2 mm class. The eFuses allow up to 3.06 A per port.
- Connector mechanical problems visible in the STEP (plug overmold clearance,
  spacing between adjacent ports).
- Assemblies too dense to build, or schematics too messy to review.
- 0.1-inch debug header access must remain (a DNP SMT footprint is enough).
