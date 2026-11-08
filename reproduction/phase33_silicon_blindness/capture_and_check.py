"""Phase 33 -- capture each bitstream over UART and check it against the
PRE-REGISTERED predicted record (predicted/<variant>.bin), byte for byte.

    python3 capture_and_check.py --port /dev/ttyUSB1 --variant blind_04_05 --trial 1
    ... three trials per variant (press btnC between them) ...
    python3 capture_and_check.py --report
"""
import argparse, hashlib, json, os, sys
HERE=os.path.dirname(os.path.abspath(__file__))
EV=os.path.join(HERE,"evidence"); PRED=os.path.join(HERE,"predicted")
SYNC=b"NTD1"; TOTAL=23*13
REG=json.load(open(os.path.join(HERE,"predictions.json")))
VARIANTS=list(REG["variants"])

def capture(port,baud,variant,trial,timeout):
    import serial
    os.makedirs(os.path.join(EV,variant),exist_ok=True)
    path=os.path.join(EV,variant,f"trial{trial}.bin")
    print(f"[{variant}] listening on {port} -- press btnC")
    with serial.Serial(port,baud,timeout=timeout) as h:
        buf=bytearray()
        while True:
            c=h.read(max(1,h.in_waiting))
            if not c: sys.exit("timed out -- is the board programmed?")
            buf+=c; i=buf.find(SYNC)
            if i>=0 and len(buf)-i>=TOTAL: rec=bytes(buf[i:i+TOTAL]); break
    open(path,"wb").write(rec); print(f"[{variant}] {len(rec)} bytes -> {path}")

def report():
    print(f"{'variant':<15} {'law':<8} {'trials':>6} {'stable':>6} {'== predicted':>13} {'== clean':>9}  verdict")
    print("-"*72); allpass=True; res={}
    for v in VARIANTS:
        d=os.path.join(EV,v)
        trials=[open(os.path.join(d,f),"rb").read() for f in sorted(os.listdir(d))
                if f.startswith("trial")] if os.path.isdir(d) else []
        pred=open(os.path.join(PRED,f"{v}.bin"),"rb").read()
        law=REG["variants"][v]["law_says"]
        if not trials:
            print(f"{v:<15} {law:<8} {'--':>6}  not captured"); allpass=False; continue
        stable=all(t==trials[0] for t in trials)
        match=all(t==pred for t in trials)
        isclean=hashlib.sha256(trials[0]).hexdigest()==REG["clean_sha256"]
        verdict="PASS" if (stable and match) else "FAIL"; allpass&=(verdict=="PASS")
        res[v]=dict(law=law,trials=len(trials),stable=stable,matches_prediction=match,identical_to_clean=isclean,verdict=verdict)
        print(f"{v:<15} {law:<8} {len(trials):>6} {str(stable):>6} {str(match):>13} {str(isclean):>9}  {verdict}")
    json.dump(res,open(os.path.join(EV,"check.json"),"w"),indent=2)
    print("\nALL PREDICTIONS CONFIRMED ON SILICON" if allpass else "\nSOME PREDICTIONS FAILED -- send evidence/ before touching the paper")

ap=argparse.ArgumentParser()
ap.add_argument("--port"); ap.add_argument("--baud",type=int,default=115200)
ap.add_argument("--variant",choices=VARIANTS); ap.add_argument("--trial",type=int,default=1)
ap.add_argument("--timeout",type=float,default=30.0); ap.add_argument("--report",action="store_true")
a=ap.parse_args()
if a.report: report()
elif a.port and a.variant: capture(a.port,a.baud,a.variant,a.trial,a.timeout)
else: sys.exit("need --port and --variant, or --report")
