#!/usr/bin/env bash
# Phase 36, start to finish. Run from the repository root with the Basys-3 plugged in:
#   bash reproduction/phase36_runtime_remap/run_p36_board.sh
set -u
H=reproduction/phase36_runtime_remap
VIVADO="${VIVADO:-vivado}"
PORT="${PORT:-/dev/ttyUSB1}"
[ -d third_party/stanford_router/src ] || { echo "run this from the repository root"; exit 1; }

echo "== 1/5 pre-registration hashes"
(cd "$H" && sha256sum -c PREREGISTRATION.sha256) || { echo "HASH MISMATCH - stop and send this output"; exit 1; }

echo "== 2/5 build the bitstream (15-20 min, no output until it finishes)"
VIVADO="$VIVADO" bash "$H/build_p36.sh" < /dev/null
grep -q '^status=PASS' "$H/evidence/build/metrics.txt" 2>/dev/null || { echo "BUILD DID NOT PASS - send $H/evidence/build back"; exit 1; }

echo "== 3/5 program the Basys-3"
"$VIVADO" -mode batch -nojournal -nolog -source "$H/vivado/program_basys3.tcl" \
   -tclargs "$H/evidence/build/noc_ttv_p36_basys3.bit" < /dev/null > "$H/evidence/build/program.log" 2>&1
grep -q NOC_TTV_BASYS3_PROGRAM_OK "$H/evidence/build/program.log" || { echo "PROGRAMMING FAILED:"; tail -15 "$H/evidence/build/program.log"; exit 1; }

echo "== 4/5 three captures: each time it says 'listening', press btnC (centre button) once"
for t in 1 2 3; do
  python3 "$H/check_p36.py" --port "$PORT" --trial $t || { echo "capture $t failed"; exit 1; }
done

echo "== 5/5 score against the pre-registered predictions"
python3 "$H/check_p36.py" --report | tee "$H/evidence/REPORT.txt"
