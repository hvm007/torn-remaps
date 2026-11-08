#!/usr/bin/env bash
# Rebuild the five reference bitstreams from the label vectors recorded in evidence/<variant>/metrics.txt.
# Run from the repository root:  bash reproduction/phase31_board_transposition/build_phase31.sh   (~75 min)
# Output goes to reproduction/phase31_board_transposition/rebuild/<variant>/ so the evidence is not overwritten.
set -u
ROOT="$(pwd)"; HERE="$ROOT/reproduction/phase31_board_transposition"; VIVADO="${VIVADO:-vivado}"
[ -d "$ROOT/third_party/stanford_router/src" ] || { echo "run from the repository root"; exit 1; }
for v in clean t01_one_sided t01_self_consistent t0512_one_sided t0512_self_consistent; do
  M="$HERE/evidence/$v/metrics.txt"
  H=$(grep '^host_labels=' "$M" | cut -d= -f2); F=$(grep '^fabric_labels=' "$M" | cut -d= -f2)
  mkdir -p "$HERE/rebuild/$v"
  "$VIVADO" -mode batch -nojournal -nolog -source "$HERE/vivado/run_bitstream_split.tcl" \
     -tclargs "$ROOT" "$ROOT/third_party/stanford_router/src" "$HERE/rebuild/$v" "$H" "$F" 0 0 0 "16'b0000000000000000" \
     < /dev/null > "$HERE/rebuild/$v/vivado_console.log" 2>&1
  echo "$v: $(grep -h '^status=\|^worst_slack_ns=' "$HERE/rebuild/$v/metrics.txt" | tr '\n' ' ')"
done
