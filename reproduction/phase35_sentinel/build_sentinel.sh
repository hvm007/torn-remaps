#!/usr/bin/env bash
# Phase 35 -- one bitstream: host table swapped (0,1), endpoint labels clean. ~15 min.
# Run from the phase-31 tree root:  bash reproduction/phase35_sentinel/build_sentinel.sh
set -u
ROOT="$(pwd)"; HERE="$ROOT/reproduction/phase35_sentinel"
TCL="$ROOT/reproduction/phase31_board_transposition/vivado/run_bitstream_split.tcl"
VIVADO="${VIVADO:-vivado}"
[ -f "$TCL" ] || { echo "run from the phase-31 tree root"; exit 1; }
HOST=$(python3 -c "import json;print(''.join(format(x,'04b') for x in json.load(open('$HERE/prediction.json'))['host_labels']))")
FAB=$(python3 -c "import json;print(''.join(format(x,'04b') for x in json.load(open('$HERE/prediction.json'))['fabric_labels']))")
[ "$FAB" = "1110110100100001111111000011000010101011010001011001100001110110" ] || { echo "fabric encoding mismatch"; exit 1; }
OUT="$HERE/evidence/torn01_A_only_fresh"; mkdir -p "$OUT"
echo "HOST=64'b$HOST"; echo "FABRIC=64'b$FAB"
"$VIVADO" -mode batch -nojournal -nolog -source "$TCL" \
   -tclargs "$ROOT" "$ROOT/third_party/stanford_router/src" "$OUT" "64'b$HOST" "64'b$FAB" 0 0 0 "16'b0000000000000000" \
   > "$OUT/vivado_console.log" 2>&1
echo "exit $?"; grep -h "^status=\|^worst_slack_ns=" "$OUT/metrics.txt"
