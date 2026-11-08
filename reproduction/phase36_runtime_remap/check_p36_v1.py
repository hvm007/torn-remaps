"""Phase 36 -- capture the runtime-remap stream and score it against predictions.json.

    python3 check_p36.py --port /dev/ttyUSB1 --trial 1     (press btnC; ~3 s of data)
    python3 check_p36.py --report                          (scores evidence/trial*.bin)
    python3 check_p36.py --score FILE                      (score one stream, e.g. RTL simulation)
"""
import argparse, json, os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.join(HERE, "evidence")
RB = 23
P = json.load(open(os.path.join(HERE, "predictions.json")))
TOTAL = P["stream_bytes"]

def crc8(d):
    v = 0
    for x in d:
        v ^= x
        for _ in range(8): v = ((v << 1) ^ 7) & 255 if v & 128 else (v << 1) & 255
    return v

def decode(b):
    assert len(b) == TOTAL, f"stream is {len(b)} bytes, expected {TOTAL}"
    recs, bad_crc = [], 0
    for n in range(len(b) // RB):
        r = b[n * RB:(n + 1) * RB]
        bad_crc += crc8(r[:22]) != r[22]
        if r[:4] == b"NTE2":
            end = (r[4] << 8) | r[5]; continue
        assert r[:4] == b"NTD2", f"record {n} bad sync"
        recs.append(dict(campaign=r[4], k=r[5], packet=r[6], src=r[7] >> 4, req=r[7] & 15,
                         slot=r[8], label=r[9] & 15, epoch=r[9] >> 4, flags=r[10],
                         timeout=bool(r[10] & 4), router_error=bool(r[10] & 8)))
    return recs, bad_crc, end

def score(b, verbose=True):
    recs, bad_crc, end = decode(b)
    fields = ("campaign", "k", "packet", "src", "req", "slot", "label", "epoch")
    pr = P["records"]
    rec_ok = len(recs) == len(pr) == end and all(all(r[f] == q[f] for f in fields) for r, q in zip(recs, pr))
    mism = [i for i, (r, q) in enumerate(zip(recs, pr)) if any(r[f] != q[f] for f in fields)]
    errs = sum(r["timeout"] or r["router_error"] for r in recs)
    # per-run detection recomputed from the captured stream
    runs = {}
    for r in recs: runs.setdefault((r["campaign"], r["k"]), []).append(r)
    silent = {}
    for (c, k), rr in runs.items():
        lab = any(x["label"] != x["req"] for x in rr)
        ep = lab or any(x["epoch"] != 1 for x in rr)
        silent.setdefault(c, {"label": [], "epoch": []})
        if not lab: silent[c]["label"].append(k)
        if not ep: silent[c]["epoch"].append(k)
    claims_ok = all(silent[c]["label"] == P["silent_points"][str(c)]["label_silent"] and
                    silent[c]["epoch"] == P["silent_points"][str(c)]["epoch_silent"] for c in silent)
    if verbose:
        print(f"records {len(recs)} (end record says {end}), CRC errors {bad_crc}, timeouts/router errors {errs}")
        print(f"every record's (source, label, delivered slot, reported label, epoch) == pre-registered: {rec_ok}"
              + ("" if rec_ok else f"  first mismatches {mism[:5]}"))
        for c in sorted(silent):
            print(f"  c{c} {P['silent_points'][str(c)]['name']:<44} label-silent {silent[c]['label']}  epoch-silent {silent[c]['epoch']}")
        print("silent interruption points == pre-registered:", claims_ok)
    return rec_ok and claims_ok and bad_crc == 0 and errs == 0

def capture(port, trial):
    import serial
    os.makedirs(EV, exist_ok=True); path = os.path.join(EV, f"trial{trial}.bin")
    print(f"listening on {port} -- press btnC (stream is {TOTAL} bytes, about 3 s)")
    with serial.Serial(port, 115200, timeout=30) as h:
        buf = bytearray()
        while True:
            c = h.read(max(1, h.in_waiting))
            if not c: sys.exit("timed out -- is the board programmed?")
            buf += c; i = buf.find(b"NTD2")
            if i >= 0 and len(buf) - i >= TOTAL: rec = bytes(buf[i:i + TOTAL]); break
    open(path, "wb").write(rec); print(f"{len(rec)} bytes -> {path}  sha256 {hashlib.sha256(rec).hexdigest()[:16]}")

def report():
    ts = sorted(f for f in os.listdir(EV) if f.startswith("trial"))
    data = [open(os.path.join(EV, f), "rb").read() for f in ts]
    stable = len(data) == 3 and all(d == data[0] for d in data)
    sim = os.path.join(HERE, "rtl_sim_stream.bin")
    eq_sim = os.path.exists(sim) and data and data[0] == open(sim, "rb").read()
    print(f"trials {len(data)}, byte-stable {stable}, identical to RTL simulation {eq_sim}")
    ok = score(data[0]) if data else False
    print("\nPHASE 36 CONFIRMED" if ok and stable else "\nNOT CONFIRMED -- send evidence/ back")

ap = argparse.ArgumentParser()
ap.add_argument("--port"); ap.add_argument("--trial", type=int, default=1)
ap.add_argument("--report", action="store_true"); ap.add_argument("--score")
a = ap.parse_args()
if a.report: report()
elif a.score: sys.exit(0 if score(open(a.score, "rb").read()) else 1)
elif a.port: capture(a.port, a.trial)
else: sys.exit("need --port, --report or --score")
