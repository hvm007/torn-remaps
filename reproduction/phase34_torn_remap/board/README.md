# Phase 34: torn remaps on silicon (pre-registered)

This tests results T1, T6 and T7 of `../THEORY.md` on the Basys-3. The board has one host table, A (`HOST_LABELS`), and one identity register per slot, B_s (`FABRIC_LABELS[s]`). A variant is "torn" when only part of an intended remap is written: here, some FABRIC slots stay on the old labels while others take the new ones.

| variant | intended remap | stale components | prediction |
|---|---|---|---|
| torn01_A_stale | swap slots 0,1 | A, B1 | pkt 5 asks 14, gets 13 at slot 0; byte-exact |
| torn01_A_fresh | swap slots 0,1 | B1 | pkt 5 asks 14, gets 13 at **slot 1**; byte-exact |
| c3_self_consistent | cycle 12→6→2 | none | zero wrong labels; only pkts 0,1,3,7,8 change |
| torn_c3_A_stale | cycle 12→6→2 | A, B6, B2 | pkt 0 asks 9, gets **2** at slot 12; byte-exact |
| torn_c3_A_fresh | cycle 12→6→2 | B6 | pkt 0 asks 9, gets **3** at slot 6; = c3 capture with one label changed |

Claims checked automatically by `check_torn.py --report`:

- **C1, non-monotone (T1).** Stale sets {A} ⊂ {A,B1} ⊂ {A,B0,B1} give 2, then 1, then 0 wrong labels. `t01_one_sided` (phase 31) has 2, `torn01_A_stale` has 1, and clean has 0. Adding stale parts *removes* errors, because a stale table plus a stale register cancel out. Tomography-style monotone models forbid this.
- **C2, non-bijective (T6).** In every torn variant, one label is reported by two different slots.
- **C3, transposition ambiguity (T7).** `torn01_A_stale` and `torn01_A_fresh` have identical label-only observations but different delivered slots. Label-only tests cannot tell which side of a swap is stale.
- **C4, cycles resolve it (T7).** For the 3-cycle, the wrong label differs (2 vs 3) depending on which side is stale.
- **C5/C6, self-consistent.** No wrong label, yet routes change on exactly the packets that arrive at or leave a moved label.

The FABRIC-only rule (`FABRIC_LABELS` feeds only the reported label, RTL line 372) was first checked on phase-31 silicon. Clean → `t01_one_sided` is reproduced byte-for-byte, and clean and `t01_self_consistent` are fixed points. `predict_torn.py` refuses to run if that check fails.

## Rebuild and re-capture (Vivado 2025.2, Basys-3)

From the repository root:

    bash reproduction/phase34_torn_remap/board/build_torn.sh        # 5 bitstreams, ~75 min
    # program each evidence/<variant>/noc_ttv_phase31_basys3.bit, then 3 trials each:
    python3 reproduction/phase34_torn_remap/board/check_torn.py --port /dev/ttyUSB1 --variant torn01_A_stale --trial 1
    python3 reproduction/phase34_torn_remap/board/check_torn.py --report

`--report` alone re-scores the captures in `evidence/`. Capture `c3_self_consistent` before
`torn_c3_A_fresh`, since the latter is checked relative to it. `predictions.json`,
`predicted/*.bin` and `predict_torn.py` were written before any build; their hashes are in
`PREREGISTRATION.sha256`.
