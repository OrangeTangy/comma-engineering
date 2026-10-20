#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
yosys_bin="${YOSYS_BIN:-yosys}"
mkdir -p ../reports
for unit in can_rx can_tx; do
  "$yosys_bin" -Q -T -p "read_verilog -sv rtl/$unit.sv; synth -top $unit -noabc; check -assert; stat; write_json ../reports/$unit-generic.json" > "../reports/$unit-generic-synthesis.log" 2>&1
  # Some runtimes can exit early at subprocess boundaries. Require the artifact.
  test -s "../reports/$unit-generic.json"
  echo "$unit: generic synthesis complete; mapping and timing remain unverified"
done
