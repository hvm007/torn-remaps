import random, itertools, json, sys
sys.path.insert(0, '.')
from torn import Inst, cycles_of, min_complete

res = {}
# 1. characterization at scale, track how many complete / incomplete
rng = random.Random(7); stats = dict(pairs=0, mism=0, complete=0, incomplete=0, nontrivial_undetected_total=0)
for t in range(6000):
    N = rng.randint(3, 7); NA = rng.randint(1, 5)
    pi = list(range(N))
    while pi == list(range(N)): rng.shuffle(pi)
    I = Inst(N, NA, pi)
    if I.K > 13: continue
    cand = [(i, l) for i in range(NA) for l in range(N)]
    # bias towards near-complete suites so both outcomes occur
    P = rng.sample(cand, rng.randint(max(1, len(cand)//3), len(cand)))
    full = (1 << (1 << I.K)) - 1; m = full
    for (i, l) in P: m &= I.undetected_mask(i, l, 'label')
    brute = [st for st in range(1 << I.K) if m >> st & 1]
    theory = I.closed_sets(P)
    complete = set(brute) <= {0, (1 << I.K) - 1}
    sc = I.strongly_connected(P); tc = I.three_conditions(P)
    stats['pairs'] += 1
    stats['complete' if complete else 'incomplete'] += 1
    stats['nontrivial_undetected_total'] += len(brute) - 2
    # all-stale always undetected under label observation
    assert ((1 << I.K) - 1) in brute
    if brute != theory or sc != complete or tc != complete:
        stats['mism'] += 1
res['characterization_label'] = stats
print('label characterization', stats)

# 2. position observation: monotone coverage
rng = random.Random(8); st2 = dict(pairs=0, mism=0, complete=0)
for t in range(3000):
    N = rng.randint(3, 7); NA = rng.randint(1, 5)
    pi = list(range(N))
    while pi == list(range(N)): rng.shuffle(pi)
    I = Inst(N, NA, pi)
    if I.K > 13: continue
    cand = [(i, l) for i in range(NA) for l in range(N)]
    P = rng.sample(cand, rng.randint(1, len(cand)))
    full = (1 << (1 << I.K)) - 1; m = full
    for (i, l) in P: m &= I.undetected_mask(i, l, 'pos')
    brute = [s for s in range(1 << I.K) if m >> s & 1]
    covered = set()
    for (i, l) in P:
        if pi[l] != l:
            covered.add(I.comp_atom[('A', i)]); covered.add(I.comp_atom[('B', I.tau[l])])
    theory = [s for s in range(1 << I.K) if all(not (s >> k & 1) for k in covered)]
    st2['pairs'] += 1; st2['complete'] += (brute == [0])
    if brute != theory: st2['mism'] += 1
res['characterization_pos'] = st2
print('pos characterization', st2)

# 3. minimum suite size vs formula, exhaustive
rows = []; mism = 0
def perms_with_cycle_types(N):
    seen = {}
    for p in itertools.permutations(range(N)):
        if list(p) == list(range(N)): continue
        ct = tuple(sorted(len(c) for c in cycles_of(list(p))))
        seen.setdefault(ct, list(p))
    return seen
for N in (3, 4, 5, 6):
    for ct, pi in sorted(perms_with_cycle_types(N).items()):
        for NA in (1, 2, 3, 4, 5):
            I = Inst(N, NA, pi)
            if I.K > 11 or NA * len(I.M) > 20: continue
            Mn = len(I.M); c = len(ct)
            r = min_complete(I, 'label')
            rp = min_complete(I, 'pos')
            f = max(Mn, NA + c - 1); fp = max(Mn, NA)
            ok = (r[0] == f and rp[0] == fp)
            mism += (not ok)
            rows.append(dict(N=N, cycles=list(ct), NA=NA, M=Mn, min_label=r[0], formula_label=f,
                             min_pos=rp[0], formula_pos=fp, ok=ok))
            print(N, ct, NA, '|M|', Mn, 'label', r[0], 'vs', f, ' pos', rp[0], 'vs', fp, '' if ok else '  <-- MISMATCH')
res['min_size'] = dict(rows=rows, mismatches=mism)
json.dump(res, open('torn_results.json', 'w'), indent=1)
print('min-size mismatches', mism, 'of', len(rows))
