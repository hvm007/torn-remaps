# Phase 33 — silicon test of predicted blindness (pre-registered)

Under label-only observation a one-sided swap is visible only to packets delivered to one of its two slots.
The board's 13-packet suite delivers to slots
D = {0,1,2,3,6,7,10,12,15}, so it is blind to exactly the 21 one-sided
transpositions inside U = {4,5,8,9,11,13,14}. `predict_records.py` turns that
into the exact 299-byte record each bitstream must emit. The predictor was first
checked against the two phase-31 one-sided captures: byte-identical on all 3 trials
of each.

| variant | swap | visible to the suite? | predicted record |
|---|---|---|---|
| blind_04_05 | 4↔5 | BLIND | byte-identical to clean |
| blind_08_13 | 8↔13 | BLIND | byte-identical to clean |
| blind_11_14 | 11↔14 | BLIND | byte-identical to clean |
| visible_06_09 | 6↔9 | VISIBLE | pkt 1: 3→11 |
| visible_04_10 | 4↔10 | VISIBLE | pkts 2, 12: 4→15 |
| visible_08_15 | 8↔15 | VISIBLE | pkts 3, 4, 10, 11: 6→10 |

The blind ones still misdeliver — any packet to slots 4/5, 8/13 or 11/14 lands on
the wrong logical endpoint — but no packet in this suite goes there.

## Rebuild and re-capture (Vivado 2025.2, Basys-3)

From the repository root:

    bash reproduction/phase33_silicon_blindness/build_blindness.sh      # ~90 min, 6 bitstreams
    # program each evidence/<variant>/noc_ttv_phase31_basys3.bit, then 3 trials each:
    python3 reproduction/phase33_silicon_blindness/capture_and_check.py --port /dev/ttyUSB1 --variant blind_04_05 --trial 1
    python3 reproduction/phase33_silicon_blindness/capture_and_check.py --report

`--report` alone re-scores the captures in `evidence/`. The clean (old-map) reference record is the
phase-31 capture in `../phase31_board_transposition/evidence/clean/`.

`predictions.json` and `predicted/*.bin` were written before any build; their hashes are in
`PREREGISTRATION.sha256`.
