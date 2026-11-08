"""pi-agnostic suites: one suite that must be torn-complete for EVERY nontrivial remap.
Independent check by packet simulation (bitmasks), exhaustive over suites."""
import itertools, sys, json
sys.path.insert(0, '.')
from torn import Inst

def agnostic_min(N, NA, obs):
    perms = [list(p) for p in itertools.permutations(range(N)) if list(p) != list(range(N))]
    insts = [Inst(N, NA, p) for p in perms]
    cand = [(i, l) for i in range(NA) for l in range(N)]
    # per instance: masks per candidate, target
    data = []
    for I in insts:
        full = (1 << (1 << I.K)) - 1
        tgt = 1 | ((1 << ((1 << I.K) - 1)) if obs == 'label' else 0)
        data.append((full, tgt, [I.undetected_mask(i, l, obs) for (i, l) in cand]))
    for k in range(1, len(cand) + 1):
        for comb in itertools.combinations(range(len(cand)), k):
            good = True
            for full, tgt, masks in data:
                m = full
                for j in comb: m &= masks[j]
                if m & ~tgt: good = False; break
            if good: return k, [cand[j] for j in comb]
    return None

out = []
for N in (3, 4):
    for NA in (1, 2, 3, 4):
        if NA * N > 16: continue
        for obs in ('label', 'pos'):
            k, P = agnostic_min(N, NA, obs)
            pred = N if NA == 1 else NA * (N - 1)
            print(f'N={N} NA={NA} {obs:5s}: min agnostic suite = {k}  predicted {pred}  {"OK" if k==pred else "MISMATCH"}  e.g. {P}')
            out.append(dict(N=N, NA=NA, obs=obs, min=k, pred=pred))
json.dump(out, open('agnostic_results.json', 'w'), indent=1)
