"""Independent re-scoring of the phase 33/34 silicon captures.
Uses only: raw trial*.bin, the label vectors Vivado actually built (metrics.txt),
and the phase-31 clean capture.  Does not import or reuse the board check scripts."""
import os, json, hashlib
R = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(R)
RB, NP = 23, 13
CL = [14,13,2,1,15,12,3,0,10,11,4,5,9,8,7,6]
def crc(d):
    v = 0
    for x in d:
        v ^= x
        for _ in range(8): v = ((v << 1) ^ 7) & 255 if v & 128 else (v << 1) & 255
    return v
def rd(p): return open(p, "rb").read()
def labels(s): s = s.split("b")[-1]; return [int(s[i:i+4], 2) for i in range(0, 64, 4)]
def pk(r, i): return r[i*RB:(i+1)*RB]
clean = rd(f"{B}/phase31_board_transposition/evidence/clean/trial1.bin")
os01 = rd(f"{B}/phase31_board_transposition/evidence/t01_one_sided/trial1.bin")
bad = []
def chk(c, msg):
    if not c: bad.append(msg)
    return c
def load(d):
    ts = [rd(f"{d}/{f}") for f in sorted(os.listdir(d)) if f.startswith("trial")]
    m = dict(l.strip().split("=", 1) for l in open(f"{d}/metrics.txt") if "=" in l)
    return ts, labels(m["host_labels"]), labels(m["fabric_labels"]), m
def integrity(name, ts):
    chk(len(ts) == 3, f"{name}: {len(ts)} trials")
    chk(all(t == ts[0] for t in ts), f"{name}: trials differ")
    r = ts[0]; chk(len(r) == RB*NP, f"{name}: length {len(r)}")
    for i in range(NP):
        p = pk(r, i)
        chk(p[:4] == b"NTD1" and p[4] == i, f"{name}: pkt {i} header")
        chk(crc(p[:22]) == p[22], f"{name}: pkt {i} CRC")
    return r
def model(r, host, fab):
    """first-principles prediction of bytes 8,9 from the BUILT label vectors"""
    out = []
    for i in range(NP):
        q = r[i*RB+5] & 15; s = host.index(q); out.append((q, s, fab[s]))
    return out
def seen(r): return [(r[i*RB+5] & 15, r[i*RB+8], r[i*RB+9]) for i in range(NP)]
def wrong(r): return [i for i, (q, s, l) in enumerate(seen(r)) if q != l]
def diffpk(a, b): return [i for i in range(NP) if pk(a, i) != pk(b, i)]

print("== phase 33 ==")
D = sorted({clean[i*RB+8] for i in range(NP)})
for v in ["blind_04_05","blind_08_13","blind_11_14","visible_06_09","visible_04_10","visible_08_15"]:
    a, b = int(v[-5:-3]), int(v[-2:])
    ts, host, fab, m = load(f"{B}/phase33_silicon_blindness/evidence/{v}")
    r = integrity(v, ts)
    F = CL[:]; F[a], F[b] = F[b], F[a]
    chk(host == CL and fab == F, f"{v}: built labels wrong")
    chk(seen(r) == model(r, host, fab), f"{v}: bytes 8/9 disagree with model")
    blind = a not in D and b not in D
    # non-label bytes must equal clean
    same_rest = all(pk(r, i)[:9] + pk(r, i)[10:22] == pk(clean, i)[:9] + pk(clean, i)[10:22] for i in range(NP))
    chk(same_rest, f"{v}: non-label bytes changed")
    chk((r == clean) == blind, f"{v}: identical-to-clean {r == clean} but blind={blind}")
    misdeliver = [CL[s] for s in (a, b)]  # labels that would be misdelivered in operation
    print(f"{v:<15} blind={str(blind):<5} ==clean={str(r == clean):<5} wrong pkts={wrong(r)} "
          f"slack={m['worst_slack_ns']}  (labels {misdeliver} misdeliver in operation)")

print("\n== phase 34 ==")
P34 = f"{B}/phase34_torn_remap/board/evidence"
cap = {}
for v in ["torn01_A_stale","torn01_A_fresh","c3_self_consistent","torn_c3_A_stale","torn_c3_A_fresh"]:
    ts, host, fab, m = load(f"{P34}/{v}")
    r = integrity(v, ts); cap[v] = (r, host, fab)
    chk(seen(r) == model(r, host, fab), f"{v}: bytes 8/9 disagree with model")
    print(f"{v:<20} wrong pkts={[(i, seen(r)[i]) for i in wrong(r)]}  slack={m['worst_slack_ns']}")
T01 = CL[:]; T01[0], T01[1] = T01[1], T01[0]
C3 = CL[:]; C3[6], C3[2], C3[12] = CL[12], CL[6], CL[2]
# built vectors are the intended torn states
chk(cap["torn01_A_stale"][1] == CL and cap["torn01_A_stale"][2] == [T01[0]] + CL[1:], "v1 build")
chk(cap["torn01_A_fresh"][1] == T01 and cap["torn01_A_fresh"][2] == [T01[0]] + CL[1:], "v2 build")
chk(cap["c3_self_consistent"][1] == C3 and cap["c3_self_consistent"][2] == C3, "v3 build")
F4 = CL[:]; F4[12] = C3[12]; chk(cap["torn_c3_A_stale"][1] == CL and cap["torn_c3_A_stale"][2] == F4, "v4 build")
F5 = C3[:]; F5[6] = CL[6];   chk(cap["torn_c3_A_fresh"][1] == C3 and cap["torn_c3_A_fresh"][2] == F5, "v5 build")
v1, v2, v3, v4, v5 = (cap[k][0] for k in ["torn01_A_stale","torn01_A_fresh","c3_self_consistent","torn_c3_A_stale","torn_c3_A_fresh"])
# FABRIC-only variants differ from their HOST-twin only in label/CRC bytes
for name, a, b in [("v1 vs clean", v1, clean), ("v4 vs clean", v4, clean), ("v2 vs phase31 self-consistent",
                   v2, rd(f"{B}/phase31_board_transposition/evidence/t01_self_consistent/trial1.bin")),
                   ("v5 vs v3", v5, v3)]:
    ok = all(pk(a, i)[:9] + pk(a, i)[10:22] == pk(b, i)[:9] + pk(b, i)[10:22] for i in range(NP))
    chk(ok, f"{name}: non-label bytes differ"); print(f"{name:<32} only label+CRC bytes differ: {ok}  (packets differing: {diffpk(a, b)})")
dup = lambda r: {l: sorted({s for q, s, ll in seen(r) if ll == l}) for l in {x[2] for x in seen(r)} if len({s for q, s, ll in seen(r) if ll == l}) > 1}
print()
c1 = (len(wrong(os01)), len(wrong(v1)), len(wrong(clean))); print("C1 stale {A} < {A,B1} < {A,B0,B1}: wrong =", c1, chk(c1 == (2, 1, 0), "C1"))
print("C2 duplicate labels:", {k: dup(cap[k][0]) for k in cap}, chk(all(dup(cap[k][0]) for k in cap if k != "c3_self_consistent") and not dup(v3), "C2"))
lab = lambda r: [(q, l) for q, s, l in seen(r)]; sl = lambda r: [s for q, s, l in seen(r)]
print("C3 swap: label-only identical", lab(v1) == lab(v2), "| slots differ", sl(v1) != sl(v2), chk(lab(v1) == lab(v2) and sl(v1) != sl(v2), "C3"))
print("C4 cycle: v4 pkt0", seen(v4)[0], "v5 pkt0", seen(v5)[0], chk(seen(v4)[0][2] != seen(v5)[0][2] and wrong(v4) == wrong(v5) == [0], "C4"))
print("C5 consistent remap: wrong =", wrong(v3), chk(wrong(v3) == [], "C5"))
print("C6 consistent remap changes packets", diffpk(v3, clean), chk(diffpk(v3, clean) == [0, 1, 3, 7, 8], "C6"))
# pre-registration integrity
pre = {l.split()[1]: l.split()[0] for l in open(f"{B}/phase34_torn_remap/board/PREREGISTRATION.sha256")}
okh = all(hashlib.sha256(rd(f"{B}/phase34_torn_remap/board/{f}")).hexdigest() == h for f, h in pre.items())
print("\npre-registration hashes (phase 34) intact:", okh)
p33 = hashlib.sha256(rd(f"{B}/phase33_silicon_blindness/predictions.json")).hexdigest()
print("phase 33 predictions.json sha256 starts", p33[:8], "(registered 3033e7c5)")
print("\nINDEPENDENT RESCORE:", "ALL CONFIRMED" if not bad and okh and p33.startswith("3033e7c5") else f"PROBLEMS: {bad}")
