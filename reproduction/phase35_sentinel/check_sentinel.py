"""Phase 35 -- capture the new bitstream and score the sentinel claims.
    python3 check_sentinel.py --port /dev/ttyUSB1 --trial 1   (x3, btnC each time)
    python3 check_sentinel.py --report"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(HERE)
EV = os.path.join(HERE, "evidence", "torn01_A_only_fresh"); RB, NP = 23, 13
P31 = os.path.join(R, "phase31_board_transposition", "evidence"); P34 = os.path.join(R, "phase34_torn_remap", "board", "evidence")
REG = json.load(open(os.path.join(HERE, "prediction.json")))
def capture(port, trial):
    import serial
    os.makedirs(EV, exist_ok=True); p = os.path.join(EV, f"trial{trial}.bin")
    print(f"[torn01_A_only_fresh] listening on {port} -- press btnC")
    with serial.Serial(port, 115200, timeout=30) as h:
        buf = bytearray()
        while True:
            c = h.read(max(1, h.in_waiting))
            if not c: sys.exit("timed out -- is the board programmed?")
            buf += c; i = buf.find(b"NTD1")
            if i >= 0 and len(buf) - i >= RB*NP: rec = bytes(buf[i:i+RB*NP]); break
    open(p, "wb").write(rec); print(f"{len(rec)} bytes -> {p}")
def rd(p): return open(p, "rb").read()
def wrong(r): return [i for i in range(NP) if (r[i*RB+5] & 15) != r[i*RB+9]]
def report():
    t = [rd(os.path.join(EV, f)) for f in sorted(os.listdir(EV)) if f.startswith("trial")]
    pred = rd(os.path.join(HERE, "predicted", "torn01_A_only_fresh.bin"))
    stable = len(t) == 3 and all(x == t[0] for x in t); exact = all(x == pred for x in t)
    print(f"torn01_A_only_fresh: trials={len(t)} stable={stable} byte-exact={exact}")
    S = {"clean": rd(f"{P31}/clean/trial1.bin"), "t01_one_sided": rd(f"{P31}/t01_one_sided/trial1.bin"),
         "t01_self_consistent": rd(f"{P31}/t01_self_consistent/trial1.bin"),
         "torn01_A_stale": rd(f"{P34}/torn01_A_stale/trial1.bin"), "torn01_A_fresh": rd(f"{P34}/torn01_A_fresh/trial1.bin"),
         "torn01_A_only_fresh": t[0]}
    orders = {"O1 = B0,B1,A": ["clean", "torn01_A_stale", "t01_one_sided", "t01_self_consistent"],
              "O2 = A,B0,B1": ["clean", "torn01_A_only_fresh", "torn01_A_fresh", "t01_self_consistent"]}
    ok = stable and exact
    for o, seq in orders.items():
        print(f"\n{o}")
        for k, v in enumerate(seq):
            w = wrong(S[v]); print(f"  k={k} {v:<22} wrong packets {w}   pkt5(asks 14):{'CAUGHT' if 5 in w else '-':<7} pkt6(asks 13):{'CAUGHT' if 6 in w else '-'}")
        ok &= all(5 in wrong(S[v]) for v in seq[1:3])                       # sentinel catches k=1,2
        ok &= any(6 not in wrong(S[v]) for v in seq[1:3])                   # pkt 6 misses one
        ok &= wrong(S[seq[0]]) == [] and wrong(S[seq[3]]) == []             # k=0, k=3 label-invisible
    print("\nSENTINEL PREDICTIONS CONFIRMED" if ok else "\nNOT CONFIRMED -- send evidence back")
ap = argparse.ArgumentParser(); ap.add_argument("--port"); ap.add_argument("--trial", type=int, default=1); ap.add_argument("--report", action="store_true")
a = ap.parse_args()
if a.report: report()
elif a.port: capture(a.port, a.trial)
else: sys.exit("need --port or --report")
