"""Phase 34 -- pre-registered silicon test of torn-remap theory (THEORY.md T1, T6, T7).

Board model: one host table A (HOST_LABELS, used by the injector for source and
destination slots) and one identity register B_s per slot (FABRIC_LABELS[s]).
'fresh' = intended remap applied, 'stale' = clean.  FABRIC_LABELS only feeds the
reported label (RTL line 372), so a variant that differs from a captured
bitstream only in FABRIC must reproduce that capture except byte 9 (reported
label) and byte 22 (CRC) of the packets delivered to the changed slots.

Record layout (23 B): 0-3 'NTD1', 4 packet, 5 = (logical src<<4)|logical dst,
8 delivered physical slot, 9 reported logical label, 22 CRC-8 over 0-21.
Label-only observation of packet i = (byte5 & 0xF, byte 9).
"""
import json, hashlib, os
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.expanduser("~/mnt/PE/phase31_evidence_digital5/reproduction/phase31_board_transposition/evidence")
RB, NP = 23, 13
CL = [14,13,2,1,15,12,3,0,10,11,4,5,9,8,7,6]           # slot -> logical, clean

def crc8(d):
    v = 0
    for b in d:
        v ^= b
        for _ in range(8): v = ((v<<1)^0x07)&0xFF if v&0x80 else (v<<1)&0xFF
    return v
def load(name): r = open(f"{EV}/{name}/trial1.bin","rb").read(); assert len(r)==RB*NP; return bytearray(r)
def relabel(base, fabric):
    """base record + a FABRIC change: byte 9 := fabric[delivered slot], CRC fixed."""
    rec = bytearray(base)
    for i in range(NP):
        s = rec[i*RB+8]; rec[i*RB+9] = fabric[s]; rec[i*RB+22] = crc8(rec[i*RB:i*RB+22])
    return bytes(rec)
def obs(rec):   # label-only observation, and delivered slots
    return [(rec[i*RB+5]&15, rec[i*RB+9]) for i in range(NP)], [rec[i*RB+8] for i in range(NP)]
def wrong(rec): return [i for i,(q,l) in enumerate(obs(rec)[0]) if q!=l]
def dups(rec):
    o, sl = obs(rec); seen = {}
    for (q,l), s in zip(o, sl): seen.setdefault(l, set()).add(s)
    return {l: sorted(v) for l, v in seen.items() if len(v) > 1}

clean, sc01, os01 = load("clean"), load("t01_self_consistent"), load("t01_one_sided")
# ---- step 1: the FABRIC-only rule reproduces existing silicon ----
T01 = CL[:]; T01[0], T01[1] = T01[1], T01[0]
v_os = relabel(clean, T01) == bytes(os01)
v_sc = relabel(sc01, T01) == bytes(sc01)
v_cl = relabel(clean, CL) == bytes(clean)
print(f"rule check on phase-31 silicon: clean->one_sided {v_os}, self_consistent fixed point {v_sc}, clean fixed point {v_cl}")
assert v_os and v_sc and v_cl

# ---- intended remaps ----
# R1: transposition of slots 0,1 (labels 14,13).  R2: 3-cycle 12->6->2->12 (labels 9,3,2).
C3 = CL[:]; C3[6], C3[2], C3[12] = CL[12], CL[6], CL[2]       # label at 12 -> slot 6, 6 -> 2, 2 -> 12
V = {}
# v1: A stale, B0 fresh, B1 stale (half-applied swap, host not updated)
F1 = CL[:]; F1[0] = T01[0]
V["torn01_A_stale"] = dict(remap="swap(0,1)", host="clean", fabric=F1, stale=["A","B1"], fresh=["B0"],
                          kind="absolute", record=relabel(clean, F1))
# v2: A fresh, B0 fresh, B1 stale
V["torn01_A_fresh"] = dict(remap="swap(0,1)", host="T01", fabric=F1, stale=["B1"], fresh=["A","B0"],
                          kind="absolute", record=relabel(sc01, F1))
# v3: 3-cycle applied self-consistently (all fresh) -- theory-level prediction only
V["c3_self_consistent"] = dict(remap="cycle(12->6->2)", host="C3", fabric=C3, stale=[], fresh=["A","B12","B6","B2"],
                          kind="theory")
# v4: A stale, B12 fresh, B6 B2 stale
F4 = CL[:]; F4[12] = C3[12]
V["torn_c3_A_stale"] = dict(remap="cycle(12->6->2)", host="clean", fabric=F4, stale=["A","B6","B2"], fresh=["B12"],
                          kind="absolute", record=relabel(clean, F4))
# v5: A fresh, B6 stale, B12 B2 fresh  -- relative to the v3 capture
F5 = C3[:]; F5[6] = CL[6]
V["torn_c3_A_fresh"] = dict(remap="cycle(12->6->2)", host="C3", fabric=F5, stale=["B6"], fresh=["A","B12","B2"],
                          kind="relative", base="c3_self_consistent")

# theory-level per-packet prediction (requested label q, delivered slot, reported label) for every variant
HOSTS = {"clean": CL, "T01": T01, "C3": C3}
req = [clean[i*RB+5] & 15 for i in range(NP)]
def theory(host, fabric):
    out = []
    for q in req:
        s = HOSTS[host].index(q); out.append([q, s, fabric[s]])
    return out
reg = {"clean_sha256": hashlib.sha256(clean).hexdigest(), "requested_labels": req, "variants": {}}
os.makedirs(os.path.join(HERE, "predicted"), exist_ok=True)
for name, v in V.items():
    th = theory(v["host"], v["fabric"])
    e = dict(remap=v["remap"], host=v["host"], host_labels=HOSTS[v["host"]], fabric_labels=v["fabric"],
             stale=v["stale"], fresh=v["fresh"], kind=v["kind"],
             theory_packets=th, theory_wrong=[i for i,(q,s,l) in enumerate(th) if q != l])
    if v["kind"] == "absolute":
        rec = v["record"]; open(os.path.join(HERE, "predicted", f"{name}.bin"), "wb").write(rec)
        e["predicted_sha256"] = hashlib.sha256(rec).hexdigest()
        # self-check: the byte-exact record agrees with the theory-level prediction
        o, sl = obs(rec); assert [[q, s, l] for (q, l), s in zip(o, sl)] == th, name
    if v["kind"] == "relative":
        e["base"] = v["base"]; e["rule"] = "capture == base capture with byte9 := fabric[byte8] and CRC recomputed"
    reg["variants"][name] = e

# ---- cross-variant claims, fixed now ----
th = {n: reg["variants"][n]["theory_packets"] for n in V}
reg["claims"] = {
 "C1_nonmonotone": dict(text="stale sets {A} < {A,B1} < {A,B0,B1}: wrong-label packets 2 > 1 > 0 "
                        "(t01_one_sided from phase 31, torn01_A_stale, clean). Monotone failure models forbid this.",
                        wrong_counts=dict(t01_one_sided=len(wrong(os01)), torn01_A_stale=len(reg["variants"]["torn01_A_stale"]["theory_wrong"]), clean=0)),
 "C2_duplicate_label": dict(text="each torn variant shows one label reported by two delivered slots",
                        expected={n: {str(l): sl for l, sl in dups_th.items()} for n, dups_th in
                                  ((n, (lambda t: {l: sorted({s for q, s, ll in t if ll == l}) for l in {x[2] for x in t}
                                                   if len({s for q, s, ll in t if ll == l}) > 1})(th[n])) for n in V)}),
 "C3_transposition_ambiguous": dict(text="torn01_A_stale and torn01_A_fresh: identical label-only observations, different delivered slots",
                        label_only_identical=[(q,l) for q,s,l in th["torn01_A_stale"]] == [(q,l) for q,s,l in th["torn01_A_fresh"]],
                        slots_differ=[s for q,s,l in th["torn01_A_stale"]] != [s for q,s,l in th["torn01_A_fresh"]]),
 "C4_cycle_resolves": dict(text="torn_c3_A_stale vs torn_c3_A_fresh: the wrong label differs, so label-only observation tells which side is stale",
                        A_stale_wrong=[(i, th["torn_c3_A_stale"][i]) for i in reg["variants"]["torn_c3_A_stale"]["theory_wrong"]],
                        A_fresh_wrong=[(i, th["torn_c3_A_fresh"][i]) for i in reg["variants"]["torn_c3_A_fresh"]["theory_wrong"]]),
 "C5_self_consistent_label_invisible": dict(text="c3_self_consistent: zero wrong labels although three slots moved",
                        theory_wrong=reg["variants"]["c3_self_consistent"]["theory_wrong"]),
}
moved = {9, 3, 2}
reg["claims"]["C6_self_consistent_moves_routes"] = dict(
    text="c3_self_consistent differs from clean exactly in the packets whose logical source or destination is a moved label (phase-31 pattern: arriving or leaving)",
    changed_packets=[i for i in range(NP) if (clean[i*RB+5] >> 4) in moved or (clean[i*RB+5] & 15) in moved])
json.dump(reg, open(os.path.join(HERE, "predictions.json"), "w"), indent=1)
for n, e in reg["variants"].items():
    w = e["theory_wrong"]
    print(f"{n:<20} stale={','.join(e['stale']) or '-':<10} wrong pkts={w} " +
          "; ".join(f"pkt{i}: asked {th[n][i][0]} got {th[n][i][2]} @slot{th[n][i][1]}" for i in w) + f"  [{e['kind']}]")
for k, c in reg["claims"].items(): print(k, {x: y for x, y in c.items() if x != "text"})
