# Torn Remaps: reproduction package

Code, data and silicon captures for the paper *Torn Remaps: Exact Test Conditions for Partially
Applied Network-on-Chip Reconfiguration* (anonymous submission).

## Quick check (about 30 s, Python 3 only)

    bash tools/verify_all.sh

This re-runs the small-scale theory checks, re-scores every board capture and the FlooNoC
simulation log against the pre-registered predictions, re-runs the board predictors, and checks
every pre-registration hash. It ends with `ALL CHECKS PASSED`.

## Where each result lives

| Paper | Folder (under `reproduction/`) | Command |
|---|---|---|
| Lemma 1, Thms 1-6, Prop. 1-2, Table II | `phase34_torn_remap/` | `python3 run_checks.py`, `sentinel.py`, `diagnose.py`, `agnostic.py`, `ni_atomic.py` (seconds); `scale16.py`, `agnostic16.py` (N = N_A = 16, minutes) |
| Sec. VII-B, Fig. 5: update engine on the board | `phase36_runtime_remap/` | `python3 phase36_runtime_remap/check_p36.py --report` |
| Sec. VII-B, earlier experiments (12 bitstreams) | `phase33_silicon_blindness/`, `phase34_torn_remap/board/`, `phase35_sentinel/`, `rescore_phase33_34/` | each folder's `--report` |
| Reference captures used by the above | `phase31_board_transposition/` | `capture_and_score.py --report` |
| Sec. VII-C, Table III: FlooNoC RTL | `phase37_floonoc_rtl/` | see its `RESULT.md` (Verilator 5.020) |
| Sec. VI: area of identity registers and epochs | `asic_nangate45/` | Yosys 0.33 + NanGate45 |
| Sec. VI: Occamy case study | `occamy_case/` | `python3 occamy_case.py <occamy_mesh_xy.yml>` |

The theory scripts are independent packet-level simulators: they apply the delivery and
reporting rules of Section III directly and never build the implication digraph, and compare
their results with the theorems. Their outputs (`*_results.json`, `scale16.log`) are included.

## Board experiments

Hardware: Digilent Basys-3 (XC7A35T), Vivado 2025.2, UART at 115200 baud. The design is a 4x4
mesh of open-source virtual-channel routers (`third_party/stanford_router`) at 50 MHz with a
packet probe that emits one 23-byte record per test packet (sync word, requested label,
delivered slot, reported label and epoch, hop trace, CRC-8). Each experiment folder has its own
build script, capture script and README; every build runs from the repository root.

Phase 36 is the main result: one bitstream with 16 per-source address tables, identity
registers with epochs, and an update engine that is interrupted after every write. One button
press runs 7 campaigns, 1,130 records. Three captures are byte-identical to each other and to
the record predicted in advance.

## Pre-registration

Every board and FlooNoC experiment has a `PREREGISTRATION.sha256` written before any build or
simulation. The files it lists (models, predictions, predicted records, and for phase 36 the
probe RTL and its simulated record stream) are byte-identical to the hashed versions. Two of the
hashed predictor scripts contain absolute paths of the original build machine;
`tools/rerun_predictions.sh` recreates those paths in a temporary directory, re-runs the
predictors and compares their outputs with the committed files.

Two disclosed deviations, with full details in the respective `RESULT.md`:

- **Phase 36, attempt 1:** the first capture script spliced two consecutive runs because it
  started listening mid-stream. Every complete record already matched. Only the capture script
  was changed (`check_p36_v1.py` is kept; see `ATTEMPT1_ANALYSIS.txt` and `evidence/attempt1/`).
- **FlooNoC:** the shipped XY example misroutes 48 of 64 cluster-to-HBM reads (found by the
  identity check before any update), and YX routing with the default turn pruning drops the
  responses; the experiment uses YX routing with `XYRouteOpt = 0`. The predictions are
  routing-independent and were not changed.

## Requirements

- Python 3.8+; `numpy` and `pyyaml` for the N = 16 checks and the Occamy case; `pyserial` for
  board captures.
- Vivado 2025.2 and a Basys-3 to rebuild and re-capture the board experiments.
- Verilator 5.020 and floogen 0.9.0 (from FlooNoC) for the FlooNoC experiment; `tools/fetch_deps.sh`
  in that folder fetches FlooNoC and its dependencies at the revisions used.
- Yosys 0.33 and the NanGate45 typical library for the area numbers.
