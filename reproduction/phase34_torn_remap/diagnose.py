"""Diagnosability of torn states under the FULL suite (every source x every label).
Count classes of torn states with identical observations."""
import itertools, sys, json
from collections import defaultdict
sys.path.insert(0, '.')
from torn import Inst, cycles_of
out = []
for N in (3, 4, 5, 6):
    seen = set()
    for p in itertools.permutations(range(N)):
        p = list(p)
        if p == list(range(N)): continue
        ct = tuple(sorted(len(c) for c in cycles_of(p)))
        for NA in (1, 2, 3):
            if (ct, NA) in seen: continue
            seen.add((ct, NA))
            I = Inst(N, NA, p)
            if I.K > 12: continue
            P = [(i, l) for i in range(NA) for l in range(N)]
            for obs in ('label', 'pos'):
                cls = defaultdict(list)
                for st in range(1 << I.K):
                    cls[tuple(I.observe(st, i, l, obs) for (i, l) in P)].append(st)
                amb = [c for c in cls.values() if len(c) > 1]
                # describe the ambiguous pairs: which atoms differ
                ex = None
                if amb:
                    a, b = amb[0][:2]; d = a ^ b
                    ex = [I.atoms[k][0] for k in range(I.K) if d >> k & 1]
                out.append(dict(N=N, cycles=list(ct), NA=NA, obs=obs, states=1 << I.K,
                                classes=len(cls), ambiguous_classes=len(amb), example_diff=ex))
                print(N, ct, NA, obs, 'states', 1 << I.K, 'classes', len(cls), 'ambiguous', len(amb), ex or '')
json.dump(out, open('diagnose_results.json', 'w'), indent=1, default=str)
