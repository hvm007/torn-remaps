#!/usr/bin/env bash
# Re-run the pre-registered board predictors (phases 33-35) in a scratch copy and compare their
# outputs with the committed, hashed files. The predictors read the phase-31 reference captures
# from absolute paths of the original machine; this script recreates those paths under a
# temporary HOME, so nothing in the repository is modified.
# Run from the repository root:  bash tools/rerun_predictions.sh
set -eu
ROOT="$(pwd)"; R="$ROOT/reproduction"; T="$(mktemp -d)"
mkdir -p "$T/mnt/PE/phase31_evidence_digital5/reproduction/phase31_board_transposition" \
         "$T/mnt/PE/reproduction/evidence_digital5_33_34/phase34_torn_remap/board"
ln -s "$R/phase31_board_transposition/evidence" "$T/mnt/PE/phase31_evidence_digital5/reproduction/phase31_board_transposition/evidence"
ln -s "$R/phase34_torn_remap/board/evidence" "$T/mnt/PE/reproduction/evidence_digital5_33_34/phase34_torn_remap/board/evidence"
ok=1
run() {  # folder, script, outputs...
  local d="$1" s="$2"; shift 2
  rm -rf "$T/w"; cp -r "$R/$d" "$T/w"; rm -rf "$T/w/predicted" "$T/w/prediction.json" "$T/w/predictions.json"
  (cd "$T/w" && HOME="$T" python3 "$s" > /dev/null)
  for f in "$@"; do
    if cmp -s "$T/w/$f" "$R/$d/$f"; then echo "  $d/$f: identical"; else echo "  $d/$f: DIFFERS"; ok=0; fi
  done
}
run phase33_silicon_blindness predict_records.py predictions.json predicted/blind_04_05.bin predicted/visible_08_15.bin
run phase34_torn_remap/board predict_torn.py predictions.json predicted/torn01_A_stale.bin predicted/torn_c3_A_stale.bin
run phase35_sentinel predict_sentinel.py prediction.json predicted/torn01_A_only_fresh.bin
rm -rf "$T"
[ $ok = 1 ] && echo "ALL PREDICTOR OUTPUTS REPRODUCED" || { echo "SOME OUTPUTS DIFFER"; exit 1; }
