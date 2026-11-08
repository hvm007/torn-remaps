"""Independent model (paper, Section III) of every read in every campaign -> predictions.json."""
import json, sys
sys.path.insert(0, '.')
from campaigns import *
recs, runs = [], []
for c, (remap, order, suite, drop, name) in enumerate(CAMPAIGNS):
    t = tau(remap); tinv = {p: r for r, p in enumerate(t)}; seq = ORDERS[order]; K = len(seq)
    for k in range(K if drop else K + 1):
        w = {x for j, x in enumerate(seq) if (j != k if drop else j < k)}
        pk = []
        for p, (src, region) in enumerate(SUITES[suite]):
            port = t[region] if A(src) in w else region          # table version decides the port
            moved = port in REMAPS[remap].values()
            fresh_reg = B(port) in w
            label = tinv[port] if fresh_reg else port            # old register: label of its old region
            epoch = 1 if fresh_reg else 0
            recs.append(dict(c=c, k=k, p=p, src=src, region=region, port=port, label=label, epoch=epoch))
            pk.append((region, port, label, epoch, t[region]))
        runs.append(dict(c=c, k=k, label_silent=all(l == r for r, _, l, _, _ in pk),
                         epoch_silent=all(l == r and e == 1 for r, _, l, e, _ in pk)))
sil = {c: dict(name=CAMPAIGNS[c][4], label=[r['k'] for r in runs if r['c'] == c and r['label_silent']],
               epoch=[r['k'] for r in runs if r['c'] == c and r['epoch_silent']]) for c in range(len(CAMPAIGNS))}
json.dump(dict(records=recs, silent=sil), open('predictions.json', 'w'), indent=0)
for c, s in sil.items(): print(f"c{c} {s['name']:<62} label-silent {s['label']}  epoch-silent {s['epoch']}")
print('reads', len(recs))
