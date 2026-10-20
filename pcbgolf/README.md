# PCBGolf engineering study

**Not a submission. No validated score.**

Upstream: https://github.com/commaai/PCBGolf
Revision: d0fd5a71087e3e10a49610f8c3e89912b4d20d77
Retrieved: 2026-10-15.

The upstream board contains 245 footprints, 1,078 pads, 302 named nets,
two copper layers, no track segments, no vias, no zones and no board outline.
Sixty-nine footprints have no courtyard geometry. Other courtyards can also be
incomplete; a nonzero vertex count is not evidence of validity.

## Run

```sh
python3 analyze.py /path/to/PCBGolf/pcbgolf.kicad_pcb --out baseline.json
python3 place.py /path/to/PCBGolf/pcbgolf.kicad_pcb candidate
```

`place.py` produces an **unrouted placement study**, preserving all components
and electrical assignments. It adds a 70 by 60 mm outline, fixes connector
anchors, uses a 12.85 by 7.0 mm envelope around each vertical OBD-C receptacle,
and packs geometry proxies with 0.25 mm separation. Signal-net span guides
placement and local optimization. High-degree nets are excluded from attraction
so a ground net does not collapse the placement; power and ground still require
explicit routing design. No decoupling, power-loop or thermal constraints are
implemented yet. The placement is therefore an experiment, not a recommended
layout. The current objective is HPWL, **not a congestion-aware routing model**.

`placement.svg` is a labeled **proxy** picture. Rectangle boundaries combine pad
bounds and available drawing geometry; they are not exact component bodies.
Missing courtyard/3D information is not repaired by the script. Connector
approach directions, ejected microSD clearance, probe access and simultaneous
plug fit need a real mechanical assembly check. In particular the fixed host
and barrel connector positions are hypotheses, not verified insertion paths.

`placement-results.json` reports actual surrogate metrics. HPWL is a wiring
estimate; it is not routed copper length or a leaderboard score. All parts remain
on the original layer with original rotation. `candidate/` carries the upstream
schematics, footprints and 3D component models with the experimental PCB.
Upstream files remain attributed to comma.ai; no ownership of them is claimed.

## Rules and current benchmark

https://github.com/commaai/PCBGolf/blob/master/README.md specifies assembled
bounding-box volume + 50 per via + 5,000 per copper layer. The prize deadline was
October 12, 2026. On October 15 the leaderboard still labels this a hiring
challenge and crosses out the cash prize. Scores range from 10,345 to 116,226.
Late submission acceptance has not been confirmed.

https://github.com/commaai/PCBGolf/issues/9 documents mandatory connector spacing,
simultaneous ports, retained 0.1-inch debug access, and acceptable SPI microSD.
Multi-board assemblies are allowed. Through-hole pads used only to change
layers count as vias. These constraints rule out several superficial shortcuts.

## Hypothesis and novelty

Optimize placement and MCU pin assignment together, then assess score only
among electrically and mechanically verified candidates. The present code
implements deterministic placement and net-identity auditing. It does **not**
implement legal MCU alternate-function reassignment, routing congestion,
routing, or a manufacturability certificate. Those are further work.

A search found published automated placement/routing and stacked-board attempts,
including https://silixon.io/blog/pcbgolf and the investigation at
https://github.com/tscircuit/tscircuit/issues/4948 . Thus “AI autorouting”, stacked
boards and changing connectors are not defensibly new on their own. No claim
that this approach has never been done online is justified by this search.

## Gates before submission

- Repair mechanical models/courtyards and verify all mating envelopes.
- Validate schematic equivalence and relevant input-voltage tolerances.
- Constrain decoupling, switcher loops, current paths, returns and USB pairs.
- Route all nets, fill planes, and run native KiCad ERC/DRC with no unexplained
  electrical violations or unconnected items.
- Verify JLCPCB fabrication capability against actual stackup and trace/drill rules.
- Export full assembly STEP, verify collisions/bounding box and calculate score.
- Review submission identity and package, then submit through the official form.

## Native verification update — October 19

KiCad 10.0.6 runs from a local app copy. `candidate-UNROUTED.step` and its PNG
are genuine native exports. The measured 70 × 60 × 12.595 mm assembly envelope
belongs only to the first unrouted candidate, not the later trials.

`routing-trial/` joins the five original standalone schematics into one hierarchy.
`integrate_schematics.py` preserves symbols/wires/global labels and repairs instance
paths. Native schematic/PCB parity now reports zero issues. Five redundant
host-connector SMD/PTH pad pairs were assigned their common physical terminal's
unused net; no functional signal was shorted. Twelve NC pads received explicit
unconnected-net names. BOM flags were aligned with the schematic.

The outline grew to 70.4 × 60.4 mm for edge clearance. Trial defaults are 0.15 mm
copper clearance, 0.20 mm hole clearance and 0.20 mm copper-to-edge clearance;
these are not a complete JLC fabrication rule set. Pre-route native DRC reports
129 warnings, zero other violations and **499 unconnected items**. Enabling the
upstream-disabled power-drive ERC check exposes **14 power-input errors** which
still need circuit review. Zero parity errors does not mean zero ERC errors.

`place_critical.py` creates a separate `critical-trial/` from the integrated
project. It moves selected regulator, crystal and bypass components underneath
and minimizes local pad distances subject to conservative body/pad rectangles.
It is a placement experiment, not a routed or thermally validated power layout.
No fabrication files or submission ZIP are offered.

### Critical-placement measurements

The first underside experiment moves 47 footprints (see `critical-placement.json`
for the exact inventory). Native checks report 139 warnings, 499 unconnected
items and zero schematic-parity issues. No non-connectivity errors were found;
this is not a clean routed DRC result. Bootstrap pad distances are 1.701 mm;
regulator switching-pin-to-inductor pad distances are 2.815 mm. These are straight
line XY distances, not routed lengths or electrical loop measurements.

The native assembly export `critical-UNROUTED.step` measures
70.4 × 60.4 × 14.230 mm, bounding volume 60,508.238 mm³. The underside adds
1.635 mm in height relative to the original assembly. Its geometry-only volume
plus two-layer penalty is 70,508.238, **before any via penalty**. This is not a
submission score: it has no routed interconnects or functional validation.

The original all-top routing experiment completed a first pass with 380 router
unrouted items and one router violation. Its internal score is unrelated to the
contest formula. The process later exited and saved a partial session on October 20. The placement
lacks sound critical-circuit grouping; completing its routing would not establish
function.

Reproduce the corrected integrated project on a copy of `candidate/`:

1. Run `prepare_routing.py COPY` with KiCad's Python.
2. Run `integrate_schematics.py COPY` with Python 3.
3. Export `COPY/pcbgolf.kicad_sch` as a KiCad XML netlist with `kicad-cli sch export netlist --format kicadxml`.
4. Run `prepare_routing.py COPY NETLIST.xml` with KiCad's Python.
5. Run `place_critical.py COPY NEW_COPY` with KiCad's Python.
6. Run native ERC, DRC with schematic parity, and STEP export on NEW_COPY.

Datasheet basis for keeping the switcher power components together:
https://www.diodes.com/datasheet/download/AP62300.pdf . The algorithm does not
yet implement the datasheet's routed copper, return-current or thermal layout.

### Imported partial route — October 20

`partial-route/` preserves the router's saved session on the old all-top layout.
Native KiCad reports 2,814 track segments, 437 vias, **339 unconnected items**,
zero schematic-parity issues, six track-width errors and 331 warnings. Six
router neck-down segments are 0.1000 mm, below the project's 0.1016 mm minimum.
The 199 dangling-via warnings further show that this is unfinished routing.
Do not fabricate this branch or combine its tracks with the moved components
in `critical-trial/`. The session was imported successfully, but the routing
experiment failed the completion gate. Native and router unrouted-item counts
use different definitions and must not be treated as interchangeable.
