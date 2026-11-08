"""Interrupted updates and single-drop faults; the sentinel-order corollary.
Interruption after k of K ordered writes = torn state 'first k fresh, rest stale'.
Claim S1: packet (i,l) detects exactly the interruptions k in one interval:
          label-only  [min(qs,p), ...) per case analysis; position [1, max(p,qt)).
Claim S2: one packet detects every interruption 0<k<K (label-only) iff the first write is
          A_i or B_sigma(l) and the last write is A_i or B_tau(l) (not both A_i).
Claim S3: single dropped write (exactly one stale component): complete iff every source
          sends a moved label and every moved label is tested -> max(|M|, N_A), no c-1 term."""
import numpy as np, random, itertools, json, sys
sys.path.insert(0, '.')
from scale16 import simulate_undetected, perm_with_cycles, min_suite
from torn import Inst, cycles_of

def detects_prefix(N, NA, pi, order, pkt, obs):
    """simulate packet on every prefix state; order = list of atom ids (A_i -> i, B_s -> bidx)."""
    I = Inst(N, NA, pi); K = I.K; out = []
    pos_of = {a: k for k, a in enumerate(order)}
    for k in range(K + 1):
        st = 0
        for a in range(K):
            if pos_of[a] >= k: st |= 1 << a          # not yet written -> stale
        out.append(I.observe(st, *pkt, obs) != I.observe(0, *pkt, obs))
    return out   # out[k] for k = 0..K (k = number of completed writes)

rng = random.Random(11); N = NA = 16; rep = dict(S1=0, S1_bad=0, S2=0, S2_bad=0, S3=0, S3_bad=0)
stats = {}
for trial in range(300):
    sh = rng.choice([(2,), (3,), (2, 2), (4,), (2, 3)])
    pi = perm_with_cycles(N, sh, rng); I = Inst(N, NA, pi); K = I.K
    order = list(range(K)); rng.shuffle(order); pos = {a: k + 1 for k, a in enumerate(order)}  # 1-based write position
    cand = [(i, l) for i in range(NA) for l in I.M]
    covers = {}
    for (i, l) in cand:
        d = detects_prefix(N, NA, pi, order, (i, l), 'label')
        p = pos[I.comp_atom[('A', i)]]; qs = pos[I.comp_atom[('B', l)]]; qt = pos[I.comp_atom[('B', pi[l])]]
        pred = set(range(qs, p)) | set(range(p, qt))          # k with A stale & Bs fresh, or A fresh & Bt stale
        rep['S1'] += 1; rep['S1_bad'] += set(k for k in range(K + 1) if d[k]) != pred
        covers[(i, l)] = pred
        dp = detects_prefix(N, NA, pi, order, (i, l), 'pos')
        rep['S1'] += 1; rep['S1_bad'] += set(k for k in range(K + 1) if dp[k]) != set(range(0, max(p, qt)))
    target = set(range(1, K))
    one = any(covers[c] >= target for c in cand)
    first, last = order[0], order[-1]
    pred_one = any((first in (I.comp_atom[('A', i)], I.comp_atom[('B', l)])) and
                   (last in (I.comp_atom[('A', i)], I.comp_atom[('B', pi[l])])) and first != last for (i, l) in cand)
    rep['S2'] += 1; rep['S2_bad'] += one != pred_one
    # minimum interval cover (exact greedy) for random orders
    need, k, n = sorted(target), 1, 0
    while k < K:
        best = max((max(c) for c in covers.values() if k in c), default=None)
        if best is None: n = None; break
        n += 1; k = best + 1
    stats.setdefault('random_order_min_suite', []).append(n)
# sentinel orders always give 1
for trial in range(100):
    pi = perm_with_cycles(N, rng.choice([(2,), (3,), (2, 2)]), rng); I = Inst(N, NA, pi); K = I.K
    i, l = rng.randrange(NA), rng.choice(I.M)
    a, bs = I.comp_atom[('A', i)], I.comp_atom[('B', l)]
    rest = [x for x in range(K) if x not in (a, bs)]; rng.shuffle(rest)
    order = [bs] + rest + [a]                                   # B_sigma(l) first, A_i last
    d = detects_prefix(N, NA, pi, order, (i, l), 'label')
    stats.setdefault('sentinel_order_detects_all', []).append(all(d[1:K]))
# S3: single dropped write
for trial in range(200):
    sh = rng.choice([(2,), (3,), (2, 2), (2, 2, 2), (3, 3)])
    pi = perm_with_cycles(N, sh, rng); I = Inst(N, NA, pi); K = I.K
    cand = [(x, y) for x in range(NA) for y in I.M]
    P = rng.sample(cand, rng.randint(1, min(len(cand), 24)))
    singles = [1 << a for a in range(K)]
    brute = all(any(I.observe(s, *pk, 'label') != I.observe(0, *pk, 'label') for pk in P) for s in singles)
    Pm = P
    pred = {y for _, y in Pm} == set(I.M) and {x for x, _ in Pm} == set(range(NA))
    rep['S3'] += 1; rep['S3_bad'] += brute != pred
rr = stats['random_order_min_suite']
summary = dict(checks=rep, random_order_min_suite=dict(mean=sum(rr) / len(rr), min=min(rr), max=max(rr),
               one_packet_fraction=sum(x == 1 for x in rr) / len(rr)),
               sentinel_order_all_detected=all(stats['sentinel_order_detects_all']))
print(json.dumps(summary, indent=1)); json.dump(summary, open('sentinel_results.json', 'w'), indent=1)

# S4: interruptions -- position observation: ONE packet always suffices (pick the last write);
#     label-only: TWO always suffice. Exhaustive over packets for random orders.
rng = random.Random(23); s4 = dict(trials=0, pos_one_fails=0, label_two_fails=0)
for trial in range(150):
    pi = perm_with_cycles(N, rng.choice([(2,), (3,), (2, 2), (4,), (2, 3), (2, 2, 2)]), rng); I = Inst(N, NA, pi); K = I.K
    order = list(range(K)); rng.shuffle(order)
    cand = [(i, l) for i in range(NA) for l in I.M]
    Dl = {c: detects_prefix(N, NA, pi, order, c, 'label') for c in cand}
    Dp = {c: detects_prefix(N, NA, pi, order, c, 'pos') for c in cand}
    s4['trials'] += 1
    s4['pos_one_fails'] += not any(all(d[0:K]) for d in Dp.values())          # k = 0..K-1, incl. nothing written
    ok2 = any(all(a or b for a, b in zip(Dl[c1][1:K], Dl[c2][1:K])) for c1 in cand for c2 in cand)
    s4['label_two_fails'] += not ok2
print('S4', s4); summary['S4'] = s4; json.dump(summary, open('sentinel_results.json', 'w'), indent=1)
