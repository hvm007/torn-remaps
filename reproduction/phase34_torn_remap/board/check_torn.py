"""Phase 34 -- capture each torn-remap bitstream and check it against the
PRE-REGISTERED predictions (predictions.json, predicted/*.bin).

    python3 check_torn.py --port /dev/ttyUSB1 --variant torn01_A_stale --trial 1
    ... three trials per variant (press btnC between them) ...
    python3 check_torn.py --report
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(HERE, "evidence"); PRED = os.path.join(HERE, "predicted")
SYNC = b"NTD1"; RB, NP = 23, 13; TOTAL = RB*NP
REG = json.load(open(os.path.join(HERE, "predictions.json"))); VARIANTS = list(REG["variants"])

def crc8(d):
    v = 0
    for b in d:
        v ^= b
        for _ in range(8): v = ((v<<1)^0x07)&0xFF if v&0x80 else (v<<1)&0xFF
    return v
def relabel(base, fabric):
    rec = bytearray(base)
    for i in range(NP):
        s = rec[i*RB+8]; rec[i*RB+9] = fabric[s]; rec[i*RB+22] = crc8(rec[i*RB:i*RB+22])
    return bytes(rec)
def packets(rec): return [[rec[i*RB+5]&15, rec[i*RB+8], rec[i*RB+9]] for i in range(NP)]
def wrong(rec): return [i for i,(q,s,l) in enumerate(packets(rec)) if q != l]
def dups(rec):
    d = {}
    for q, s, l in packets(rec): d.setdefault(l, set()).add(s)
    return {str(l): sorted(v) for l, v in d.items() if len(v) > 1}

def capture(port, baud, variant, trial, timeout):
    import serial
    os.makedirs(os.path.join(EV, variant), exist_ok=True)
    path = os.path.join(EV, variant, f"trial{trial}.bin")
    print(f"[{variant}] listening on {port} -- press btnC")
    with serial.Serial(port, baud, timeout=timeout) as h:
        buf = bytearray()
        while True:
            c = h.read(max(1, h.in_waiting))
            if not c: sys.exit("timed out -- is the board programmed?")
            buf += c; i = buf.find(SYNC)
            if i >= 0 and len(buf)-i >= TOTAL: rec = bytes(buf[i:i+TOTAL]); break
    open(path, "wb").write(rec); print(f"[{variant}] {len(rec)} bytes -> {path}")

def trials(v):
    d = os.path.join(EV, v)
    return [open(os.path.join(d, f), "rb").read() for f in sorted(os.listdir(d)) if f.startswith("trial")] if os.path.isdir(d) else []

def report():
    T = {v: trials(v) for v in VARIANTS}; res = {}; ok = True
    print(f"{'variant':<20} {'kind':<9} {'trials':>6} {'stable':>6} {'byte-exact':>10} {'theory':>6}  verdict"); print("-"*72)
    for v in VARIANTS:
        e = REG["variants"][v]; t = T[v]
        if not t: print(f"{v:<20} not captured"); ok = False; continue
        stable = all(x == t[0] for x in t)
        th = packets(t[0]) == e["theory_packets"]
        if e["kind"] == "absolute": exact = all(x == open(os.path.join(PRED, f"{v}.bin"), "rb").read() for x in t)
        elif e["kind"] == "relative":
            b = T[e["base"]]; exact = bool(b) and all(x == relabel(b[0], e["fabric_labels"]) for x in t)
        else: exact = None
        good = stable and th and exact is not False
        ok &= good; res[v] = dict(stable=stable, byte_exact=exact, theory=th, verdict="PASS" if good else "FAIL")
        print(f"{v:<20} {e['kind']:<9} {len(t):>6} {str(stable):>6} {str(exact if exact is not None else '-'):>10} {str(th):>6}  {res[v]['verdict']}")
    C = REG["claims"]; got = lambda v: T[v][0] if T[v] else None; cl = {}
    if got("torn01_A_stale"): cl["C1_nonmonotone"] = len(wrong(got("torn01_A_stale"))) == C["C1_nonmonotone"]["wrong_counts"]["torn01_A_stale"]
    cl["C2_duplicate_label"] = all(dups(got(v)) == C["C2_duplicate_label"]["expected"][v] for v in VARIANTS if got(v))
    if got("torn01_A_stale") and got("torn01_A_fresh"):
        a, b = packets(got("torn01_A_stale")), packets(got("torn01_A_fresh"))
        cl["C3_transposition_ambiguous"] = [(q,l) for q,s,l in a] == [(q,l) for q,s,l in b] and [s for q,s,l in a] != [s for q,s,l in b]
    if got("torn_c3_A_stale") and got("torn_c3_A_fresh"):
        cl["C4_cycle_resolves"] = ([[i, packets(got("torn_c3_A_stale"))[i]] for i in wrong(got("torn_c3_A_stale"))] == C["C4_cycle_resolves"]["A_stale_wrong"]
            and [[i, packets(got("torn_c3_A_fresh"))[i]] for i in wrong(got("torn_c3_A_fresh"))] == C["C4_cycle_resolves"]["A_fresh_wrong"])
    if got("c3_self_consistent"):
        cl["C5_self_consistent_label_invisible"] = wrong(got("c3_self_consistent")) == []
        cp = os.path.join(HERE, "clean_reference.bin")
        if os.path.exists(cp):
            c = open(cp, "rb").read(); r = got("c3_self_consistent")
            cl["C6_self_consistent_moves_routes"] = [i for i in range(NP) if r[i*RB:(i+1)*RB] != c[i*RB:(i+1)*RB]] == C["C6_self_consistent_moves_routes"]["changed_packets"]
    print(); [print(f"{k:<38} {'PASS' if v else 'FAIL'}") for k, v in cl.items()]
    ok &= all(cl.values()) and len(cl) == 6
    json.dump(dict(variants=res, claims=cl), open(os.path.join(EV, "check.json"), "w"), indent=2)
    print("\nALL PRE-REGISTERED TORN-REMAP PREDICTIONS CONFIRMED" if ok else "\nNOT ALL CONFIRMED -- send evidence/ back before touching the paper")

ap = argparse.ArgumentParser()
ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200)
ap.add_argument("--variant", choices=VARIANTS); ap.add_argument("--trial", type=int, default=1)
ap.add_argument("--timeout", type=float, default=30.0); ap.add_argument("--report", action="store_true")
a = ap.parse_args()
if a.report: report()
elif a.port and a.variant: capture(a.port, a.baud, a.variant, a.trial, a.timeout)
else: sys.exit("need --port and --variant, or --report")
