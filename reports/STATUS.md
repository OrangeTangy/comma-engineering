# Verification status — 2026-10-20

| Check | Result | Limitation |
|---|---|---|
| Icarus 13.0 simulation | 2,386 cases passed | Directed/random tests, not conformance or exhaustive proof |
| RX generic synthesis | 878 cells, 227 flip-flop bits; zero check problems | Generic gates, not FPGA LUT usage |
| TX generic synthesis | 826 cells, 132 flip-flop bits; zero check problems | Generic gates, not FPGA LUT usage |
| Gowin mapping | Incomplete | Runtime stopped at ABC9 invocation; no final mapping statistics |
| FPGA placement/timing | Not run | No constrained board-level integration |
| Physical CAN interoperability | Not run | No FPGA/transceiver/reference peer available |
| PCB electrical assignment audit | Preserved 245 footprints and pad/net mappings | Does not imply schematic correctness or connectivity |
| PCB placement | 70 × 60 mm; wiring proxy −28.71% | Unrouted, proxy geometry only |
| Native KiCad checks | Running locally; integrated parity: 0 issues | Pre-route: 499 unconnected items, 129 warnings; ERC: 14 power-drive errors |
| Assembly STEP | Native export: 70 × 60 × 12.595 mm first candidate | Unrouted; no valid contest score or collision certification |
| Submission | Not sent | Neither project is complete |

Generic synthesis used yowasp-yosys 0.70.0.0.post1259, yowasp-runtime 1.96 and
wasmtime 47.0.1. Both runs completed the JSON backend and `check -assert` with
zero reported problems. No latch cells appear in the final generic statistics.
The generic netlists and full logs are retained alongside this file. Reproduce
with `YOSYS_BIN=/path/to/yowasp-yosys bash synth.sh` from the CAN source folder.
Gowin attempt logs are also retained; their zero shell exit status is **not**
treated as successful mapping because final statistics/netlist are absent.

The actual source, reports and tests are the deliverables. No formal proof,
complete CAN controller, CAN-FD support, fabricated board, contest acceptance,
leaderboard placement, prize eligibility or universal novelty is claimed.

Critical underside trial: 70.4 × 60.4 × 14.230 mm; volume 60,508.238 mm³.
139 DRC warnings, 499 unconnected items, zero parity issues. Critical XY pad
distances improved; no routed performance or fabrication readiness established.

Partial all-top routing imported October 20: 2,814 segments, 437 vias; native
DRC finds 339 unconnected items, six width errors, 331 warnings, zero parity
issues. This failed experiment is separate from the unrouted underside trial.
No background router remains running. See partial-route-drc.json and
router-baseline.log. The six width errors are 0.1000 mm neck-down segments
against a 0.1016 mm project minimum; constraints were not relaxed to hide them.
