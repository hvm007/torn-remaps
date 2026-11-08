"""Phase 36 -- capture the runtime-remap stream and score it against predictions.json.

    python3 check_p36.py --port /dev/ttyUSB1 --trial 1     (press btnC; ~3 s of data)
    python3 check_p36.py --report                          (scores evidence/trial*.bin)
    python3 check_p36.py --score FILE                      (score one stream, e.g. RTL simulation)

v2 (8 Nov 2026), capture only: the v1 capture opened the port while the board could still be sending
an earlier stream and started at the first "NTD2" it saw, so it could splice the tail of one run onto
the head of the next.  v2 waits for an idle line, then keeps the complete stream that starts with the
start-of-stream record (campaign 0, k 0, packet 0).  Predictions and scoring rules are unchanged.
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

START = b"NTD2\x00\x00\x00"   # first record of every stream: campaign 0, k 0, packet 0

def decode(b):
    recs, bad_crc, end, bad_sync = [], 0, -1, []
    for n in range(len(b) // RB):
        r = b[n * RB:(n + 1) * RB]
        bad_crc += crc8(r[:22]) != r[22]
        if r[:4] == b"NTE2":
            end = (r[4] << 8) | r[5]; continue
        if r[:4] != b"NTD2":
            bad_sync.append(n); continue
        recs.append(dict(campaign=r[4], k=r[5], packet=r[6], src=r[7] >> 4, req=r[7] & 15,
                         slot=r[8], label=r[9] & 15, epoch=r[9] >> 4, flags=r[10],
                         timeout=bool(r[10] & 4), router_error=bool(r[10] & 8)))
    return recs, bad_crc, end, bad_sync

def score(b, verbose=True):
    if len(b) != TOTAL or not b.startswith(START):
        print(f"stream is {len(b)} bytes and starts with {b[:7].hex()}; expected {TOTAL} bytes starting with {START.hex()}")
        return False
    recs, bad_crc, end, bad_sync = decode(b)
    if bad_sync:
        print(f"{len(bad_sync)} records without sync, first at record {bad_sync[0]} -- the stream is misaligned")
        return False
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
    import serial, time
    os.makedirs(EV, exist_ok=True); path = os.path.join(EV, f"trial{trial}.bin")
    with serial.Serial(port, 115200, timeout=0.2) as h:
        quiet = time.time()                       # wait for 1 s of silence: no earlier stream may leak in
        while time.time() - quiet < 1.0:
            if h.read(4096): quiet = time.time()
        h.reset_input_buffer()
        print(f"trial {trial}: line is idle -- press btnC now (stream is {TOTAL} bytes, about 3 s)")
        buf, last, t0 = bytearray(), None, time.time()
        while True:                               # collect until the stream has ended (1 s of silence)
            c = h.read(4096)
            if c: buf += c; last = time.time()
            elif last is None and time.time() - t0 > 60: sys.exit("no data for 60 s -- is the board programmed?")
            elif last is not None and time.time() - last > 1.0: break
    starts = [i for i in range(len(buf)) if buf.startswith(START, i) and len(buf) - i >= TOTAL]
    if not starts:
        open(path + ".raw", "wb").write(bytes(buf))
        sys.exit(f"no complete stream in {len(buf)} bytes (raw bytes saved to {path}.raw) -- press btnC once and retry")
    i = starts[-1]; rec = bytes(buf[i:i + TOTAL])
    extra = len(buf) - TOTAL
    open(path, "wb").write(rec)
    print(f"{len(rec)} bytes -> {path}  sha256 {hashlib.sha256(rec).hexdigest()[:16]}"
          + (f"  ({extra} extra bytes on the line around the stream were discarded)" if extra else ""))

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
