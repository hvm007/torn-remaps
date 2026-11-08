"""Emit campaign tables as a SystemVerilog include for the testbench (definitions only, no predictions)."""
import sys
sys.path.insert(0, '.')
from campaigns import *
L = []
L.append(f"localparam int NCAMP = {len(CAMPAIGNS)};")
L.append("localparam int CAMP_REMAP [NCAMP] = '{" + ", ".join(str(c[0]) for c in CAMPAIGNS) + "};")
L.append("localparam int CAMP_ORDER [NCAMP] = '{" + ", ".join(str(c[1]) for c in CAMPAIGNS) + "};")
L.append("localparam int CAMP_SUITE [NCAMP] = '{" + ", ".join(str(c[2]) for c in CAMPAIGNS) + "};")
L.append("localparam bit CAMP_DROP  [NCAMP] = '{" + ", ".join("1'b1" if c[3] else "1'b0" for c in CAMPAIGNS) + "};")
L.append("localparam int TAU [2][20] = '{" + ", ".join("'{" + ", ".join(map(str, tau(r))) + "}" for r in (0, 1)) + "};")
mx = max(len(o) for o in ORDERS.values())
L.append(f"localparam int ORDER_LEN [3] = '{{" + ", ".join(str(len(ORDERS[o])) for o in range(3)) + "};")
L.append(f"localparam int ORDER [3][{mx}] = '{{" + ", ".join("'{" + ", ".join(map(str, ORDERS[o] + [0]*(mx-len(ORDERS[o])))) + "}" for o in range(3)) + "};")
ms = max(len(s) for s in SUITES.values())
L.append(f"localparam int SUITE_LEN [5] = '{{" + ", ".join(str(len(SUITES[s])) for s in range(5)) + "};")
L.append(f"localparam int SUITE_SRC [5][{ms}] = '{{" + ", ".join("'{" + ", ".join(str(a) for a, b in SUITES[s] + [(0, 0)]*(ms-len(SUITES[s]))) + "}" for s in range(5)) + "};")
L.append(f"localparam int SUITE_REG [5][{ms}] = '{{" + ", ".join("'{" + ", ".join(str(b) for a, b in SUITES[s] + [(0, 0)]*(ms-len(SUITES[s]))) + "}" for s in range(5)) + "};")
open('tb_data.svh', 'w').write("\n".join(L) + "\n")
