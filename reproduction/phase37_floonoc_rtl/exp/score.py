"""Score the FlooNoC RTL records against the pre-registered predictions.json."""
import json, sys, collections
P = json.load(open('predictions.json'))
rec = [list(map(int, l.split()[1:])) for l in open(sys.argv[1]) if l.startswith('REC ')]
keys = ('c', 'k', 'p', 'src', 'region', 'port', 'label', 'epoch')
obs = [dict(zip(keys, r[:8]), timeout=r[8]) for r in rec]
pred = P['records']
same = len(obs) == len(pred) and all(all(o[k] == q[k] for k in keys) for o, q in zip(obs, pred))
bad = [i for i, (o, q) in enumerate(zip(obs, pred)) if any(o[k] != q[k] for k in keys)]
to = sum(o['timeout'] for o in obs)
runs = collections.defaultdict(list)
for o in obs: runs[(o['c'], o['k'])].append(o)
sil = collections.defaultdict(lambda: {'label': [], 'epoch': []})
for (c, k), rr in sorted(runs.items()):
    if all(o['label'] == o['region'] for o in rr): sil[c]['label'].append(k)
    if all(o['label'] == o['region'] and o['epoch'] == 1 for o in rr): sil[c]['epoch'].append(k)
ok_sil = all(sil[int(c)]['label'] == P['silent'][c]['label'] and sil[int(c)]['epoch'] == P['silent'][c]['epoch'] for c in P['silent'])
print(f"reads {len(obs)}, timeouts {to}; every (port, label, epoch) == pre-registered: {same}" + ("" if same else f" first mismatches {bad[:5]}"))
for c in sorted(int(c) for c in P['silent']): print(f"  c{c} {P['silent'][str(c)]['name']:<62} label-silent {sil[c]['label']}  epoch-silent {sil[c]['epoch']}")
print("silent interruption points == pre-registered:", ok_sil)
print("FLOONOC RTL CONFIRMS PREDICTIONS" if same and ok_sil and to == 0 else "MISMATCH")
