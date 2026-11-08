#!/usr/bin/env bash
# Phase 33 -- build the six pre-registered one-sided transposition bitstreams.
# Run from the tree root that already holds phase 31 (the repository root):
#     bash reproduction/phase33_silicon_blindness/build_blindness.sh
# ~15 min per bitstream, ~90 min total. Clean is reused from phase 31.
set -u
ROOT="$(pwd)"
ROUTER_SRC="$ROOT/third_party/stanford_router/src"
TCL="$ROOT/reproduction/phase31_board_transposition/vivado/run_bitstream_split.tcl"
EVID="$ROOT/reproduction/phase33_silicon_blindness/evidence"
VIVADO="${VIVADO:-vivado}"
[ -f "$TCL" ] || { echo "phase-31 TCL not found at $TCL -- run from the phase-31 tree root"; exit 1; }

CLEAN=(14 13 2 1 15 12 3 0 10 11 4 5 9 8 7 6)          # slot -> logical
bits() { local s="" v k; for v in "$@"; do for k in 3 2 1 0; do s+=$(( (v>>k)&1 )); done; done; echo "$s"; }
HOST=$(bits "${CLEAN[@]}")
[ "$HOST" = "1110110100100001111111000011000010101011010001011001100001110110" ] || { echo "clean label encoding mismatch"; exit 1; }

declare -A SWAP=( [blind_04_05]="4 5" [blind_08_13]="8 13" [blind_11_14]="11 14"
                  [visible_06_09]="6 9" [visible_04_10]="4 10" [visible_08_15]="8 15" )
for name in blind_04_05 blind_08_13 blind_11_14 visible_06_09 visible_04_10 visible_08_15; do
  read a b <<< "${SWAP[$name]}"
  F=("${CLEAN[@]}"); t=${F[$a]}; F[$a]=${F[$b]}; F[$b]=$t
  FAB=$(bits "${F[@]}")
  echo "=== $name  swap($a,$b) ==="
  echo "    HOST   = 64'b$HOST"
  echo "    FABRIC = 64'b$FAB"
  mkdir -p "$EVID/$name"
  "$VIVADO" -mode batch -nojournal -nolog -source "$TCL" \
      -tclargs "$ROOT" "$ROUTER_SRC" "$EVID/$name" "64'b$HOST" "64'b$FAB" 0 0 0 "16'b0000000000000000" \
      > "$EVID/$name/vivado_console.log" 2>&1
  rc=$?
  grep -h "^status=\|^worst_slack_ns=\|^lut_cells=" "$EVID/$name/metrics.txt" 2>/dev/null | tr '\n' ' '
  echo "  (exit $rc)"
done
echo "Done. Program each evidence/<variant>/noc_ttv_phase31_basys3.bit and run capture_and_check.py"
