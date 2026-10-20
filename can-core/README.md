# Original Classical CAN bit-level engines

**Status: tested HDL prototype, not a complete CAN controller or CAN-FD core.**
This is original SystemVerilog written during the AI-assisted project. No CTU RTL
was copied. The CTU repository was inspected for project scope and verification
expectations; these tests do not establish equivalence to CTU.

## Reproduce

Requirements: Python 3.10+ and Icarus Verilog (tested with 13.0).

```sh
python3 tests/run.py
python3 tests/arbitration.py
```

The scripts stop on failures and save a failing testbench for debugging. Seeds
are fixed. Testbenches and compiled simulations use temporary directories.
`tests/results.json` and `tests/arbitration-results.json` record actual runs.

## Synthesis evidence

Both modules completed generic Yosys synthesis and structural checks with zero
reported problems (RX 878 generic cells / 227 flip-flop bits; TX 826 / 132).
These counts are not FPGA LUT usage. Gowin mapping was attempted but did not
finish; there is no place-and-route or timing-closure result. Run
`YOSYS_BIN=/path/to/yosys bash synth.sh` to reproduce generic synthesis.

## Interface and supported behavior

`can_tx.sv` accepts an 11-bit identifier, RTR flag, DLC 0–8 and a 64-bit payload.
The first transmitted byte is `data[63:56]`. The input is latched on `start`
when `ready` is high. `start` during a transmission is ignored. A system-clock
cycle must separate accepting `start` from the first `drive_en`.

The external bit timing unit pulses `drive_en` at a bit boundary and
`sample_en` at that bit's sample point, in that order, on different clock cycles.
It must allow a complete drive/sample pair before the next pair. Both enables
are one-clock pulses. `bus_bit` must already be synchronized. `tx_bit=1` releases
the bus, `tx_bit=0` requests dominant. Never connect this directly to CANH/CANL.

The transmitter inserts bits through the CRC sequence, including a necessary
stuff bit after the last CRC bit. It reports missing ACK, bit errors, rejected
DLC, arbitration loss and successful completion. It emits intermission after
success. It does not decide whether the bus is idle before starting. The caller
must grant bus access and hold off retries until the bus is available. On
arbitration loss/error the output releases at the next drive boundary.

`can_rx.sv` consumes sampled wire bits. It de-stuffs, checks CRC and fixed-form
fields, requests ACK on a valid CRC, and reports a complete base frame.
`data` is **right aligned** on receive (two received bytes occupy bits 15:0).
Unused high bits are zero. RTR frames return no payload. Receive DLC 9–15 is
retained while consuming eight bytes; transmit DLC above eight is rejected.
A receive frame with IDE=1 reports `unsupported` and enters recovery.

`ack_request` means the next bus bit is the ACK slot. The integration layer must
suppress self-acknowledgement when this node is the transmitter; the two-node
test uses a separate receiving observer to drive ACK. `frame_valid`,
`frame_error`, `done`, `arbitration_lost` and `tx_error` are one-system-clock
pulses. Consumers must latch them. Outputs retain the last accepted frame.

## Test design

The Python oracle builds complete messages and calculates CRC by integer
polynomial division, independently of the RTL's sequential LFSR. The HDL is
compared against that oracle, not merely connected to itself in loopback.
Tests cover zero to eight data bytes, remote frames, all-zero/all-one and
alternating patterns, seeded random payloads, reserved receive DLCs, stuff bits
at CRC boundaries, corrupt CRC, illegal stuff bits, malformed delimiters/EOF,
unsupported IDE, recovery, minimum intermission and reset at every wire bit.
The two-transmitter bench models a wired-AND bus and checks both identifier
priority and data/remote arbitration. Additional tests cover missing ACK,
transmit bit errors and rejected DLC.

These are directed and randomized simulations, **not** an ISO conformance
suite, exhaustive formal proof, hardware interoperability result or code
coverage claim. The Python model and RTL were produced by the same assistant;
an external controller or independent protocol VIP remains necessary validation.

## Required before hardware use

1. Implement nominal bit timing, hard synchronization, bounded resynchronization,
   input synchronizer, clock-tolerance and propagation-delay tests.
2. Integrate TX/RX with bus-idle qualification, queueing, ACK ownership,
   arbitration-loss receive continuation and automatic retransmission.
3. Implement active/passive error flags, overload frames, TEC/REC counters,
   all error-counter exceptions, error-passive suspension, bus-off and recovery.
4. Add 29-bit frames and CAN-FD only after the Classical CAN controller works.
   FD requires different CRC/stuff-count/fixed-stuff handling, rate switching and
   transceiver-delay compensation; these modules do not implement those features.
5. Add register/FIFO interface, overflow behavior, timestamping, acceptance
   filtering, FPGA pin/clock constraints, implementation and timing reports.
6. Demonstrate interoperability and fault injection against an independent node.

The module separation supports a useful research direction: log each wire-level
fault with field/bit position, compare to an independent oracle, and minimize
failing traces. The current prototype supplies deterministic vectors and error
categories, but **does not yet implement a trace minimizer**. Novelty has not
been established.

Protocol reference: Bosch CAN Specification 2.0 (1991),
https://tech-tools.com/files/can2spec.pdf .
Comparison project: https://github.com/Logic-Design-Services/CTU-CAN-FD .
