# Phase 36: runtime remap with real, sequential configuration writes

Phases 31–35 encoded each torn state as a synthesis parameter. This phase builds one bitstream in which nothing about the remap is fixed at build time.

- Each of the 16 source interfaces has its **own address table**, so N_A = 16.
- Each slot has an **identity register** holding a label and an epoch.
- An **update engine** writes the remap one component per clock cycle.

One press of btnC runs 7 campaigns. Each campaign sweeps the interruption point k: reset to the old map, apply the first k writes (or every write except write k, in drop mode), then send the test suite. The board emits 1,130 packet records plus an end record, 26,013 bytes in total (about 3 s).

| c | remap | write order | suite | what it shows |
|---|---|---|---|---|
| 0 | swap 0,1 | sentinel (B0 first, A7 last) | 1 packet (7→14) | one packet catches every interruption (Prop. 2) |
| 1 | swap 0,1 | tables first | same packet | it misses k = 1..5, where stale table and stale register cancel |
| 2 | swap 0,1 | tables first | 2 anchor packets | two packets always suffice |
| 3 | swaps 0,1 + 5,12 | grouped | split suite, 16 packets | every table and label is covered, yet k = 10 escapes (Thm. 3 iii) |
| 4 | same | grouped | split + 1 bridge packet, 17 (minimum) | complete |
| 5 | same | grouped | witness packet 8→13 | the k = 10 state misdelivers in operation |
| 6 | same | grouped, drop one write | bridged suite | every lost write is caught |

Every record also carries the endpoint's **epoch**. With epochs, only the finished update is silent, including k = 0 ("no write happened").

**Pre-registration.** `model_p36.py` was written from the paper's model, not from the RTL. It produced `predictions.json`, covering the source, requested label, delivered slot, reported label and epoch of every one of the 1,130 records, plus the silent interruption points of every campaign. It was hashed before simulation; see `PREREGISTRATION.sha256`. The Icarus RTL simulation then matched all 1,130 records (`rtl_sim_stream.bin`, also hashed). The board must reproduce both.

## Rebuild and re-capture (Vivado 2025.2, Basys-3)

From the repository root, with the board connected:

    bash reproduction/phase36_runtime_remap/run_p36_board.sh     # hash check, build (~20 min), program, 3 captures, report

or step by step:

    (cd reproduction/phase36_runtime_remap && sha256sum -c PREREGISTRATION.sha256)
    bash reproduction/phase36_runtime_remap/build_p36.sh
    vivado -mode batch -source reproduction/phase36_runtime_remap/vivado/program_basys3.tcl \
           -tclargs reproduction/phase36_runtime_remap/evidence/build/noc_ttv_p36_basys3.bit
    for t in 1 2 3; do python3 reproduction/phase36_runtime_remap/check_p36.py --port /dev/ttyUSB1 --trial $t; done
    python3 reproduction/phase36_runtime_remap/check_p36.py --report

`check_p36.py --report` alone re-scores the three captures in `evidence/`. Results: `RESULT.md`.
