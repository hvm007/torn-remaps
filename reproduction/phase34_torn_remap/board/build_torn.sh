#!/usr/bin/env bash
# Phase 34 -- build the five pre-registered torn-remap bitstreams (~15 min each, ~75 min).
# Run from the phase-31 tree root (the repository root):
#     bash reproduction/phase34_torn_remap/board/build_torn.sh
set -u
ROOT="$(pwd)"
ROUTER_SRC="$ROOT/third_party/stanford_router/src"
TCL="$ROOT/reproduction/phase31_board_transposition/vivado/run_bitstream_split.tcl"
HERE="$ROOT/reproduction/phase34_torn_remap/board"
EVID="$HERE/evidence"
VIVADO="${VIVADO:-vivado}"
[ -f "$TCL" ] || { echo "phase-31 TCL not found at $TCL -- run from the phase-31 tree root"; exit 1; }
# label vectors come straight from the pre-registered predictions.json
python3 - "$HERE/predictions.json" > "$HERE/.variants" <<'PY'
import json, sys
reg = json.load(open(sys.argv[1]))
bits = lambda v: "".join(format(x, "04b") for x in v)
assert bits([14,13,2,1,15,12,3,0,10,11,4,5,9,8,7,6]) == "1110110100100001111111000011000010101011010001011001100001110110"
for n, e in reg["variants"].items(): print(n, bits(e["host_labels"]), bits(e["fabric_labels"]))
PY
while read name HOST FAB; do
  echo "=== $name ==="; echo "    HOST   = 64'b$HOST"; echo "    FABRIC = 64'b$FAB"
  mkdir -p "$EVID/$name"
  "$VIVADO" -mode batch -nojournal -nolog -source "$TCL" \
      -tclargs "$ROOT" "$ROUTER_SRC" "$EVID/$name" "64'b$HOST" "64'b$FAB" 0 0 0 "16'b0000000000000000" \
      > "$EVID/$name/vivado_console.log" 2>&1
  rc=$?
  grep -h "^status=\|^worst_slack_ns=\|^lut_cells=" "$EVID/$name/metrics.txt" 2>/dev/null | tr '\n' ' '
  echo "  (exit $rc)"
done < "$HERE/.variants"
echo "Done. Program each evidence/<variant>/noc_ttv_phase31_basys3.bit and run check_torn.py"
