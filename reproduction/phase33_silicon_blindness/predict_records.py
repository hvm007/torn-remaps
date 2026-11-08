"""Phase 33 -- pre-registered silicon prediction of blindness.

From the clean board capture alone, predict the EXACT 299-byte UART record each
one-sided transposition bitstream will emit: packets delivered to a swapped
slot report the other slot's clean label (byte 9) and get a new CRC (byte 22);
every other byte is unchanged.  A transposition whose two slots are both
outside the suite's delivered set D must therefore emit a record
byte-identical to clean.

Step 1 validates the predictor on the two one-sided bitstreams already
captured in phase 31.  Step 2 writes predictions for new variants BEFORE they
are built.
"""
import json, hashlib, os
EV=os.path.expanduser("~/mnt/PE/phase31_evidence_digital5/reproduction/phase31_board_transposition/evidence")
RB,NP=23,13
CLEAN_LABELS=[14,13,2,1,15,12,3,0,10,11,4,5,9,8,7,6]      # slot -> logical, clean
def crc8(d):
    v=0
    for b in d:
        v^=b
        for _ in range(8): v=((v<<1)^0x07)&0xFF if v&0x80 else (v<<1)&0xFF
    return v
clean=bytearray(open(f"{EV}/clean/trial1.bin","rb").read())
assert len(clean)==RB*NP
dphys=[clean[i*RB+8] for i in range(NP)]
D=sorted(set(dphys)); U=sorted(set(range(16))-set(D))
def predict(a,b):
    rec=bytearray(clean); changed=[]
    for i in range(NP):
        s=dphys[i]
        if s in (a,b):
            other=b if s==a else a
            rec[i*RB+9]=CLEAN_LABELS[other]
            rec[i*RB+22]=crc8(rec[i*RB:i*RB+22])
            changed.append(dict(packet=i,slot=s,clean_label=CLEAN_LABELS[s],predicted_label=CLEAN_LABELS[other]))
    return bytes(rec),changed

print(f"board suite delivered slots D={D} (|D|={len(D)}), uncovered U={U}")
print(f"law: blind one-sided transpositions = C(16-{len(D)},2) = {len(U)*(len(U)-1)//2}\n")

# ---- step 1: validate on existing silicon ----
ok=True
for name,(a,b) in {"t01_one_sided":(0,1),"t0512_one_sided":(5,12)}.items():
    pred,_=predict(a,b)
    for t in (1,2,3):
        act=open(f"{EV}/{name}/trial{t}.bin","rb").read()
        same = act==pred; ok&=same
    print(f"validate {name:<16} swap({a},{b}): predicted record == all 3 captured trials: {same}")
print(f"PREDICTOR VALID ON EXISTING SILICON: {ok}\n")

# ---- step 2: pre-register new variants ----
NEW={"blind_04_05":(4,5),"blind_08_13":(8,13),"blind_11_14":(11,14),
     "visible_06_09":(6,9),"visible_04_10":(4,10),"visible_08_15":(8,15)}
reg={"clean_sha256":hashlib.sha256(clean).hexdigest(),"D":D,"U":U,"variants":{}}
os.makedirs("predicted",exist_ok=True)
for name,(a,b) in NEW.items():
    rec,ch=predict(a,b)
    open(f"predicted/{name}.bin","wb").write(rec)
    blind = {a,b}.isdisjoint(D)
    reg["variants"][name]=dict(swap=[a,b],law_says="BLIND" if blind else "VISIBLE",
        predicted_identical_to_clean=(rec==bytes(clean)),changed_packets=ch,
        predicted_sha256=hashlib.sha256(rec).hexdigest())
    desc="byte-identical to clean" if not ch else "; ".join(f"pkt {c['packet']}: {c['clean_label']}->{c['predicted_label']}" for c in ch)
    print(f"{name:<14} swap({a:>2},{b:>2})  law={'BLIND  ' if blind else 'VISIBLE'}  -> {desc}")
json.dump(reg,open("predictions.json","w"),indent=2)
print("\nwrote predictions.json and predicted/*.bin  (pre-registered before any build)")
