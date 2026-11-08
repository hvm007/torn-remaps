"""Phase 35 -- sentinel write order on silicon (pre-registered).

Intended remap: swap slots 0,1 (labels 14,13).  Three writes: host table A, slot-0
register B0, slot-1 register B1.  An update interrupted after k writes leaves
the first k fresh and the rest stale.

  order O1 = B0, B1, A :  k=1 -> torn01_A_stale (ph34)   k=2 -> t01_one_sided (ph31)
  order O2 = A, B0, B1 :  k=1 -> torn01_A_only_fresh (NEW) k=2 -> torn01_A_fresh (ph34)
  k=0 (nothing written) = clean (ph31);  k=3 (done) = t01_self_consistent (ph31)

Sentinel rule (SCALE_AND_FAULT_MODELS.md, S2): packet (i,l) catches every interruption
iff the first write is A_i or B_sigma(l) and the last write is A_i or B_tau(l).
Label 14: sigma = slot 0, tau = slot 1 -> sentinel for BOTH orders (O1: B0 first, A last;
O2: A first, B1 last).  Label 13: sigma = slot 1, tau = slot 0 -> sentinel for neither.
Packet 5 asks for 14, packet 6 asks for 13.  Prediction: packet 5 is wrong at every
interruption point of both orders; packet 6 misses one interruption point in each order;
nothing is visible at k=0 or k=3 (label-only).
"""
import json, hashlib, os
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.expanduser("~/mnt/PE/phase31_evidence_digital5/reproduction/phase31_board_transposition/evidence")
EV34 = os.path.expanduser("~/mnt/PE/reproduction/evidence_digital5_33_34/phase34_torn_remap/board/evidence")
RB, NP = 23, 13
CL = [14,13,2,1,15,12,3,0,10,11,4,5,9,8,7,6]
T01 = CL[:]; T01[0], T01[1] = T01[1], T01[0]
def crc8(d):
    v = 0
    for b in d:
        v ^= b
        for _ in range(8): v = ((v<<1)^0x07)&0xFF if v&0x80 else (v<<1)&0xFF
    return v
def rd(p): r = open(p, "rb").read(); assert len(r) == RB*NP; return r
def relabel(base, fabric):
    rec = bytearray(base)
    for i in range(NP):
        s = rec[i*RB+8]; rec[i*RB+9] = fabric[s]; rec[i*RB+22] = crc8(rec[i*RB:i*RB+22])
    return bytes(rec)
def wrong(r): return [i for i in range(NP) if (r[i*RB+5] & 15) != r[i*RB+9]]

sc01 = rd(f"{EV}/t01_self_consistent/trial1.bin")
new = relabel(sc01, CL)                                   # host swapped, fabric clean
# the rule (fabric changes only bytes 9/22) reproduces two existing captures from sc01
assert relabel(sc01, [T01[0]] + CL[1:]) == rd(f"{EV34}/torn01_A_fresh/trial1.bin")
assert relabel(sc01, T01) == sc01
os.makedirs(f"{HERE}/predicted", exist_ok=True)
open(f"{HERE}/predicted/torn01_A_only_fresh.bin", "wb").write(new)
th = [[new[i*RB+5] & 15, new[i*RB+8], new[i*RB+9]] for i in range(NP)]
for q, s, l in th: assert s == T01.index(q) and l == CL[s]
reg = dict(variant="torn01_A_only_fresh", host_labels=T01, fabric_labels=CL,
           predicted_sha256=hashlib.sha256(new).hexdigest(), theory_packets=th,
           predicted_wrong=wrong(new),
           orders={"O1 (B0,B1,A)": {"k0": "ph31/clean", "k1": "ph34/torn01_A_stale", "k2": "ph31/t01_one_sided", "k3": "ph31/t01_self_consistent"},
                   "O2 (A,B0,B1)": {"k0": "ph31/clean", "k1": "ph35/torn01_A_only_fresh", "k2": "ph34/torn01_A_fresh", "k3": "ph31/t01_self_consistent"}},
           claims={"sentinel_pkt5_catches_k1_k2_both_orders": True,
                   "pkt6_misses_one_interruption_per_order": True,
                   "k0_and_k3_label_invisible": True})
json.dump(reg, open(f"{HERE}/prediction.json", "w"), indent=1)
print("new variant torn01_A_only_fresh: predicted wrong packets", wrong(new),
      [(i, th[i]) for i in wrong(new)])
