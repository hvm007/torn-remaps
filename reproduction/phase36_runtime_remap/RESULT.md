# Phase 36 on silicon: PHASE 36 CONFIRMED (Basys-3, 8 Nov 2026)

**Build.** status=PASS, worst slack 7.353 ns, 14,271 LUTs, 6,732 FFs, Vivado 2025.2.

**Captures.** Three captures, one btnC press each, with check_p36.py v2:

| trial | sha256 |
|---|---|
| 1 | 19ae7e5464be99e8... |
| 2 | 19ae7e5464be99e8... |
| 3 | 19ae7e5464be99e8... |

- All three are identical to each other and to the pre-registered `rtl_sim_stream.bin`.
- The prediction files are unchanged since 31 Oct: `predictions.json`, `model_p36.py`, `rtl/noc_ttv_p36_probe.v` and `rtl_sim_stream.bin` all pass `sha256sum -c PREREGISTRATION.sha256`.
- In trial 3, one stray byte on the serial line next to the stream was discarded. It is the TX glitch at the btnC reset; see below.

**Scoring.**
- 1,130 records plus the end record.
- 0 CRC errors, 0 timeouts, 0 router errors.
- Every (source, label, delivered slot, reported label, epoch) equals the prediction.
- The silent interruption points of all 7 campaigns equal the prediction:
  - c0 (sentinel order): the packet catches every interruption.
  - c1 (tables first, same packet): misses k = 1..5.
  - c2 (two anchor packets): catch all.
  - c3 (split suite of 16): misses k = 10.
  - c4 (bridged suite of 17): catches all.
  - c5 (witness packet): as predicted.
  - c6 (one lost write): every lost write is caught.
  - With epochs, only the completed update is silent.

**Attempt 1 (disclosed).**
- Captured with check_p36.py v1. Each trial was a splice of two consecutive runs, because the v1 capture opened the port while the board was still sending and started at the first header it saw.
- Every complete record in it already matched. See `ATTEMPT1_ANALYSIS.txt`, and the files in `evidence/attempt1/`.
- The fix (v2) changed the capture only: wait for an idle line, then keep the complete stream that starts at record (c0, k0, p0).
- The design, bitstream, predictions and scoring rules did not change.

**Evidence.** `evidence/` (trials, REPORT.txt, build reports and bitstream, attempt1/).
