#!/usr/bin/env bash
# Quick verification of every result from the committed data (about 1 minute, Python 3 only).
# Run from the repository root:  bash tools/verify_all.sh
set -u
R=reproduction; fail=0
step() { echo; echo "== $1"; shift; if "$@"; then :; else echo "   FAILED"; fail=1; fi; }
hashes() { (cd "$1" && sha256sum -c --quiet PREREGISTRATION.sha256) && echo "   pre-registration hashes OK"; }
step "pre-registration hashes, phases 33-37" bash -c "$(declare -f hashes); hashes $R/phase33_silicon_blindness && hashes $R/phase34_torn_remap/board && hashes $R/phase35_sentinel && hashes $R/phase36_runtime_remap && hashes $R/phase37_floonoc_rtl/exp"
step "phase-31 reference evidence checksums" bash -c "sha256sum -c --quiet $R/phase31_board_transposition/evidence/SHA256SUMS.txt && echo '   OK'"
step "theory: Thm 2-4 checks (N<=7)" bash -c "cd $R/phase34_torn_remap && python3 run_checks.py | tail -1"
step "theory: Prop. 2 / sentinel order" bash -c "cd $R/phase34_torn_remap && python3 sentinel.py | tail -1"
step "theory: Thm 6 diagnosis" bash -c "cd $R/phase34_torn_remap && python3 diagnose.py | tail -1"
step "board, phase 33 (delivered-set blindness)" bash -c "python3 $R/phase33_silicon_blindness/capture_and_check.py --report | tail -1"
step "board, phase 34 (torn remaps, shared table)" bash -c "python3 $R/phase34_torn_remap/board/check_torn.py --report | tail -1"
step "board, phase 35 (sentinel order)" bash -c "python3 $R/phase35_sentinel/check_sentinel.py --report | tail -1"
step "board, phases 33-34 independent re-score" bash -c "cd $R/rescore_phase33_34 && python3 rescore_independent.py | tail -1"
step "board, phase 36 (update engine, Fig. 5)" bash -c "python3 $R/phase36_runtime_remap/check_p36.py --report | tail -1"
step "board predictors re-run (phases 33-35)" bash -c "bash tools/rerun_predictions.sh | tail -1"
step "FlooNoC RTL log, Table III (rebuilding needs Verilator, see its RESULT.md)" bash -c "cd $R/phase37_floonoc_rtl/exp && python3 score.py ../logs/run3_yx_noopt_torn_sim.log | tail -1"
echo; [ $fail = 0 ] && echo "ALL CHECKS PASSED" || { echo "SOME CHECKS FAILED"; exit 1; }
