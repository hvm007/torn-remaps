"""Granularity variant: NI k at slot k holds its source table A_k and its register B_k,
updated atomically (one atom per NI). Exhaustive minimum suites (pi-aware)."""
import itertools, sys
sys.path.insert(0, '.')
from torn import Inst, cycles_of, min_complete
for N in (3, 4, 5):
    seen = set()
    for p in itertools.permutations(range(N)):
        p = list(p)
        if p == list(range(N)): continue
        ct = tuple(sorted(len(c) for c in cycles_of(p)))
        if ct in seen: continue
        seen.add(ct)
        atoms = []
        for k in range(N):
            at = [('A', k)]
            if p[k] != k or k in p and p.index(k) != k: at.append(('B', k))
            atoms.append(tuple(at))
        I = Inst(N, N, p, atoms=atoms)
        cand = [(i, l) for i in range(N) for l in I.M]
        rl = min_complete(I, 'label', cand); rp = min_complete(I, 'pos', cand)
        M = len(I.M); c = len(ct)
        print(f'N={N} cycles={ct} |M|={M}: NI-atomic min label={rl[0]} pos={rp[0]}   table-atomic formula label={max(M, N + c - 1)} pos={max(M, N)}')
