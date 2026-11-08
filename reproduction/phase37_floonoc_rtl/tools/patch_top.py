"""Add per-cluster run-time SAM ports to a floogen-generated floo_axi_mesh_noc.sv.
Cluster chimneys get cluster_sam_i[x][y]; HBM chimneys keep the generated constant Sam.
usage: patch_top.py IN OUT [--no-xy-opt]
--no-xy-opt sets the routers' XYRouteOpt parameter to 0 (keeps the X->Y / Y->X turns that
dimension-order routing would prune; needed for responses from West-edge endpoints under YX routing)."""
import re, sys
s = open(sys.argv[1]).read()
s = "// PATCHED for torn-remap experiments: per-cluster run-time SAM ports.\n" + s
old = "  input axi_out_rsp_t             [3:0] hbm_axi_out_rsp_i\n"
assert s.count(old) == 1
s = s.replace(old, "  input axi_out_rsp_t             [3:0] hbm_axi_out_rsp_i,\n"
                   "  input sam_rule_t [SamNumRules-1:0] cluster_sam_i [3:0][3:0]\n")
n = [0, 0]
def cl(m):
    n[0] += 1
    return m.group(0) + f"  .sam_i            ( cluster_sam_i[{m.group(1)}][{m.group(2)}] ),\n"
def hb(m):
    n[1] += 1
    return m.group(0) + "  .sam_i            ( Sam ),\n"
s = re.sub(r"\) cluster_ni_(\d)_(\d) \(\n  \.clk_i,\n  \.rst_ni,\n  \.test_enable_i,\n", cl, s)
s = re.sub(r"\) hbm_ni_\d \(\n  \.clk_i,\n  \.rst_ni,\n  \.test_enable_i,\n", hb, s)
assert n == [16, 4], n
if "--no-xy-opt" in sys.argv:
    k = s.count("  .RouteAlgo (YXRouting),\n") + s.count("  .RouteAlgo (XYRouting),\n")
    s = s.replace("  .RouteAlgo (YXRouting),\n", "  .RouteAlgo (YXRouting),\n  .XYRouteOpt (1'b0),\n")
    s = s.replace("  .RouteAlgo (XYRouting),\n", "  .RouteAlgo (XYRouting),\n  .XYRouteOpt (1'b0),\n")
    print("XYRouteOpt = 0 in", k, "routers")
open(sys.argv[2], "w").write(s)
print("patched", n[0], "cluster and", n[1], "HBM chimneys")
