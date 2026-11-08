# Reference captures: one shared table, label-encoded remaps (Basys-3)

The probe `rtl/noc_ttv_phase31_probe_split.v` drives the 4x4 mesh of virtual-channel routers
(`third_party/stanford_router`) with a 13-packet suite and emits one 23-byte record per packet
(299 bytes per run: requested label, delivered slot, reported label, hop trace, CRC-8).
The host address table (`HOST_LABELS`) and the endpoint identity registers (`FABRIC_LABELS`)
are synthesis parameters, so each torn state is its own bitstream.

The five bitstreams here are the reference records the later board experiments are scored
against:

| variant | host table | identity registers |
|---|---|---|
| `clean` | old map | old map |
| `t01_one_sided` | swap of slots 0,1 | old map |
| `t01_self_consistent` | swap of slots 0,1 | swap of slots 0,1 |
| `t0512_one_sided` | swap of slots 5,12 | old map |
| `t0512_self_consistent` | swap of slots 5,12 | swap of slots 5,12 |

`evidence/<variant>/` holds three hardware-reset captures (`trial1..3.bin`, byte-stable), the
Vivado metrics with the label vectors actually built, and the timing and utilization reports.
`evidence/SHA256SUMS.txt` covers the captures, metrics and `capture_and_score.py`; those files are
kept byte-identical to the originals and therefore still contain build-machine paths.

    python3 reproduction/phase31_board_transposition/capture_and_score.py --report   # re-score the captures
    bash reproduction/phase31_board_transposition/build_phase31.sh                   # rebuild (Vivado 2025.2)

To capture: program `evidence/<variant>/noc_ttv_phase31_basys3.bit`, then
`capture_and_score.py --port /dev/ttyUSB1 --variant <variant> --trial <t>` and press btnC.
