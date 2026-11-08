# Torn remaps on FlooNoC RTL — result

**Verdict: FLOONOC RTL CONFIRMS PREDICTIONS.** All 1,111 reads match the pre-registered
(delivered port, reported label, epoch) exactly, and so do the silent interruption points of all
7 campaigns. There were 0 timeouts.

## Setup

- **NoC.** FlooNoC `3623659` (2026-11-02), floogen 0.9.0. It is the 4×4 AXI mesh from
  `floogen/examples/axi_mesh_xy.yml`: 16 clusters, plus 4 HBM channels on the West edge.
- **Changes to FlooNoC.**
  - Each cluster chimney gets its own run-time copy of the system address map (SAM). The patch is
    `patched/floo_id_translation.sv` and `patched/floo_axi_chimney.sv`, plus `tools/patch_top.py`.
  - The routing change is described under "Deviation" below.
  - Routers, links and arbiters are otherwise unmodified.
- **Testbench (`exp/tb_torn.sv`).**
  - Each of the 20 subordinate ports answers a read with {port, identity label, epoch}.
  - A torn state = the first k writes of an update order (or all writes but write k) applied to
    16 SAM tables + 20 identity registers.
- **Simulator.** Verilator 5.020.

## Pre-registration

`exp/PREREGISTRATION.sha256` was written at 21:13 UTC on 5 Nov 2026, before any simulation ran.
It covers:

```
60440b55…  predictions.json   (written by model.py from the paper's model; no RTL input)
09bc03af…  campaigns.py
0f983b04…  model.py
```

All three hashes still verify (`sha256sum -c`). Nothing in them changed after any run.

## Results (run 3, `build_yx2/torn_sim.log`, sha256 231157ea…)

| campaign | silent at k (label only) | silent with epoch |
|---|---|---|
| c0 one failover, sentinel order, 1 packet | 0, 18 (= old and new consistent states) | 18 |
| c1 one failover, tables first, same packet | 0, **1–5**, 18 | 18 |
| c2 one failover, tables first, packet from first-written table | 0, 18 | 18 |
| c3 two failovers, half-by-half, split suite (16 packets) | 0, **10**, 20 | 20 |
| c4 two failovers, half-by-half, bridged suite (17 = minimum) | 0, 20 | 20 |
| c5 two failovers, single witness read | 0, **1, 2**, 20 | 20 |
| c6 bridged suite, one lost write | none | none |

The bold entries are torn states that the suite misses, exactly where the theory says.

- Sentinel order: one packet is enough.
- Bridging: the split suite misses k = 10, the closed set "lower half done"; one extra bridging
  packet (17) closes it.
- Epoch: every torn state is detected.

## Deviation from the original configuration (disclosed)

### Run 1: stock `axi_mesh_xy.yml` (XY routing, HBMs on the West edge)

Run 1 mismatched at k = 0, i.e. before any write. Cause: X-first routing reaches the West edge in
the source's own row. Any HBM read from row y lands on HBM y.

The routing sanity test (`exp/tb_sanity.sv`: every cluster reads every other region once, old
map) shows this directly:

- Stock XY: **48 of 64 cluster→HBM reads reach the wrong HBM channel**, always the HBM of the
  source's row. All 240 cluster→cluster reads are correct.
- The identity check flags every one of the 48 at the first read.

This is a property of the example configuration, not of the torn-state theory.

### Run 2: YX routing, default `XYRouteOpt = 1`

Run 2 produced 995 timeouts. Requests now reach the right channel, but a response that enters a
router from the West edge needs a West→North/South turn. FlooNoC's turn optimisation prunes that
turn for YX routing, so the response is never delivered.

### Run 3: YX routing, `XYRouteOpt = 0` on all 16 routers

- Routing sanity: 304/304 reads correct.
- Torn campaigns: all predictions confirmed (table above).

`XYRouteOpt` is an existing FlooNoC router parameter. Re-enabling the turns gives up FlooNoC's
deadlock-freedom argument for the response network. That does not matter here because the
testbench has one read in flight at a time. It would matter for real traffic.

The predictions are routing-independent (port level), so they were not and did not need to be
changed. The configuration change was made after seeing runs 1 and 2. It is justified by the
independent sanity test, not by the torn-state result.

## Reproduce

```
tools/fetch_deps.sh /some/dir            # FlooNoC 3623659 + common_cells, common_verification, tech_cells_generic, axi
export FLOONOC=/some/dir/FlooNoC DEPS=/some/dir/deps
pip install "$FLOONOC"                    # floogen 0.9.0
floogen rtl -c cfg/axi_mesh_westhbm_yx.yml -o gen_yx
python3 tools/patch_top.py gen_yx/floo_axi_mesh_noc.sv patched_yx_noopt/floo_axi_mesh_noc.sv --no-xy-opt
tools/build.sh gen_yx patched_yx_noopt build_yx2 tb_torn
(cd build_yx2 && ./obj_dir/tb_torn > torn_sim.log)
(cd exp && sha256sum -c PREREGISTRATION.sha256 && python3 score.py ../build_yx2/torn_sim.log)
```

The routing sanity check is the same with `tb_sanity` as the top module and the stock `gen_xy` /
`patched_xy` files. The build takes about 75 s and the simulation about 25 s. `gen_xy/`, `gen_yx/` and
the patched tops are included, so floogen is only needed to regenerate them.

FlooNoC and the files derived from it (`patched/`, `gen_*/`, `patched_*/`) are under FlooNoC's
licenses (`LICENSE-SHL`, `LICENSE-APACHE`).
