#!/usr/bin/env bash
# Phase 36 -- one bitstream: runtime remap with per-source tables (~15-20 min).
# Run from the phase-31 tree root:  bash reproduction/phase36_runtime_remap/build_p36.sh
set -u
ROOT="$(pwd)"; HERE="$ROOT/reproduction/phase36_runtime_remap"
VIVADO="${VIVADO:-vivado}"
[ -d "$ROOT/third_party/stanford_router/src" ] || { echo "run from the phase-31 tree root"; exit 1; }
OUT="$HERE/evidence/build"; mkdir -p "$OUT"
"$VIVADO" -mode batch -nojournal -nolog -source "$HERE/vivado/run_bitstream_p36.tcl" \
   -tclargs "$ROOT" "$ROOT/third_party/stanford_router/src" "$OUT" runtime runtime 0 0 0 none \
   > "$OUT/vivado_console.log" 2>&1
echo "exit $?"; grep -h "^status=\|^worst_slack_ns=\|^lut_cells=\|^ff_cells=" "$OUT/metrics.txt"
