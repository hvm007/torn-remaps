#!/bin/bash
# Build a Verilator testbench for the patched FlooNoC mesh (Verilator 5.020).
# usage: FLOONOC=<FlooNoC checkout> DEPS=<dependency dir> tools/build.sh GENDIR PATCHDIR BUILDDIR [TOP=tb_torn]
# GENDIR holds floogen output, PATCHDIR the patched top (tools/patch_top.py); see tools/fetch_deps.sh.
set -e
: "${FLOONOC:?set FLOONOC to the FlooNoC checkout}"; : "${DEPS:?set DEPS to the dependency directory}"
F=$(cd "$(dirname "$0")/.." && pwd)
GEN=$(cd "$1" && pwd); PAT=$(cd "$2" && pwd); OUT=$3; TOP=${4:-tb_torn}
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
sed -e "s#\$FLOONOC#$FLOONOC#" -e "s#\$DEPS#$DEPS#" "$F/tools/srcs_template.txt" > "$OUT/srcs_$TOP.txt"
printf '%s\n' "$GEN/floo_axi_mesh_noc_pkg.sv" "$F/patched/floo_id_translation.sv" "$F/patched/floo_axi_chimney.sv" \
  "$PAT/floo_axi_mesh_noc.sv" "$F/exp/$TOP.sv" >> "$OUT/srcs_$TOP.txt"
cd "$OUT"
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  --top-module "$TOP" +incdir+"$DEPS/common_cells/include" +incdir+"$DEPS/axi/include" \
  +incdir+"$FLOONOC/hw/include" +incdir+"$F/exp" $(cat "srcs_$TOP.txt") -o "$TOP" > "vl_$TOP.log" 2>&1
echo "built $OUT/obj_dir/$TOP"
