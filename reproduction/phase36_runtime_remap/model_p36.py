"""Phase 36 -- independent model of the runtime-remap campaigns, and the theory's
predictions.  Written from the paper's model (Section III), not from the RTL.

Writes predictions.json:
  per record : campaign, k, packet, source slot, requested label,
               delivered slot, reported label, reported epoch
  per run    : detected? under label-only / position / epoch observation
  claims     : which interruption points each suite misses, by theory
"""
import json, hashlib, sys

OLD = [14, 13, 2, 1, 15, 12, 3, 0, 10, 11, 4, 5, 9, 8, 7, 6]              # slot -> label
NEW = {0: [13, 14, 2, 1, 15, 12, 3, 0, 10, 11, 4, 5, 9, 8, 7, 6],          # swap slots 0,1
       1: [13, 14, 2, 1, 15, 9, 3, 0, 10, 11, 4, 5, 12, 8, 7, 6]}          # + swap slots 5,12
A = lambda i: ('A', i)
B = lambda s: ('B', s)
ORDERS = {
    0: [B(0)] + [A(i) for i in (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15)] + [B(1), A(7)],
    1: [A(i) for i in range(2, 16)] + [A(0), A(1), B(0), B(1)],
    2: [A(i) for i in (2, 3, 4, 5, 6, 7, 12, 15)] + [B(0), B(1)] +
       [A(i) for i in (0, 1, 8, 9, 10, 11, 13, 14)] + [B(5), B(12)],
}
G1 = [(2, 14), (3, 13), (4, 14), (5, 13), (6, 14), (7, 13), (12, 14), (15, 13)]
G2 = [(0, 12), (1, 9), (8, 12), (9, 9), (10, 12), (11, 9), (13, 12), (14, 9)]
SUITES = {0: [(7, 14)], 1: [(7, 14), (2, 13)], 2: G1 + G2, 3: G1 + G2 + [(2, 12)], 4: [(8, 13)]}
CAMPAIGNS = [  # remap, order, suite, drop
    (0, 0, 0, False), (0, 1, 0, False), (0, 1, 1, False),
    (1, 2, 2, False), (1, 2, 3, False), (1, 2, 4, False), (1, 2, 3, True)]
NAMES = ["sentinel order, 1 packet", "tables-first order, same packet", "tables-first order, 2 anchor packets",
         "two swaps, split suite (16)", "two swaps, bridged suite (17)", "two swaps, witness packet",
         "two swaps, bridged suite, one dropped write"]

def run(remap, order, suite, drop, k):
    new = NEW[remap]; seq = ORDERS[order]
    written = {c for j, c in enumerate(seq) if (j != k if drop else j < k)}
    table = {i: (new if A(i) in written else OLD) for i in range(16)}
    reg = {s: ((new[s], 1) if B(s) in written else (OLD[s], 0)) for s in range(16)}
    out = []
    for (i, l) in SUITES[suite]:
        d = table[i].index(l)
        assert d != i, "self-send"
        lab, ep = reg[d]
        out.append(dict(src=i, req=l, slot=d, label=lab, epoch=ep,
                        exp_slot=new.index(l), exp_epoch=1 if new.index(l) != OLD.index(l) or True else 0))
    return out

def main():
    recs, runs = [], []
    for c, (remap, order, suite, drop) in enumerate(CAMPAIGNS):
        K = len(ORDERS[order]); kmax = K - 1 if drop else K
        for k in range(kmax + 1):
            pk = run(remap, order, suite, drop, k)
            for p, r in enumerate(pk):
                recs.append(dict(campaign=c, k=k, packet=p, src=r['src'], req=r['req'],
                                 slot=r['slot'], label=r['label'], epoch=r['epoch']))
            runs.append(dict(campaign=c, k=k,
                             label_detect=any(r['label'] != r['req'] for r in pk),
                             position_detect=any(r['slot'] != r['exp_slot'] or r['label'] != r['req'] for r in pk),
                             epoch_detect=any(r['epoch'] != 1 or r['label'] != r['req'] for r in pk),
                             wrong_packets=[p for p, r in enumerate(pk) if r['label'] != r['req']]))
    miss = {}
    for c in range(len(CAMPAIGNS)):
        rr = [r for r in runs if r['campaign'] == c]
        miss[c] = dict(name=NAMES[c],
                       label_silent=[r['k'] for r in rr if not r['label_detect']],
                       position_silent=[r['k'] for r in rr if not r['position_detect']],
                       epoch_silent=[r['k'] for r in rr if not r['epoch_detect']])
    reg = dict(records=recs, runs=runs, silent_points=miss, total_records=len(recs),
               stream_bytes=23 * (len(recs) + 1))
    return reg

if __name__ == '__main__':
    reg = main()
    for c, m in reg['silent_points'].items():
        print(f"c{c} {m['name']:<44} label-silent k={m['label_silent']}  position-silent={m['position_silent']}  epoch-silent={m['epoch_silent']}")
    print('records', reg['total_records'], 'stream bytes', reg['stream_bytes'])
    if len(sys.argv) > 1:
        json.dump(reg, open(sys.argv[1], 'w'), indent=0)
