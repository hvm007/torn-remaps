"""Exhaustive torn-remap checks at the real size: N = 16 slots, N_A = 16 per-source tables.
Every torn state (2^K, K = 16 + |moved slots|) is simulated packet by packet (numpy),
independently of the graph theory, and compared with it."""
import numpy as np, itertools, random, json, time, sys
sys.path.insert(0, '.')
from torn import cycles_of

def simulate_undetected(N, NA, pi, P, obs='label', chunk_bits=22):
    """Return boolean array over all 2^K torn states: True = undetected by suite P.
    Atom order: A_0..A_{NA-1}, then B_s for moved slots (sorted)."""
    M = [l for l in range(N) if pi[l] != l]
    mslots = sorted(set(pi[l] for l in M))
    bidx = {s: NA + k for k, s in enumerate(mslots)}
    K = NA + len(mslots); total = 1 << K
    tauinv = [0]*N
    for l, s in enumerate(pi): tauinv[s] = l
    out = np.empty(total, dtype=bool)
    step = 1 << min(chunk_bits, K)
    Pm = [(i, l) for (i, l) in P if pi[l] != l]
    for base in range(0, total, step):
        st = np.arange(base, min(base + step, total), dtype=np.int64)
        und = np.ones(st.shape, dtype=bool)
        for (i, l) in Pm:
            a = (st >> i) & 1
            s_old, s_new = l, pi[l]                      # sigma = identity
            slot = np.where(a == 1, s_old, s_new)
            b_old = (st >> bidx[s_old]) & 1; b_new = (st >> bidx[s_new]) & 1
            bstale = np.where(a == 1, b_old, b_new)
            tinv = np.array(tauinv)
            label = np.where(bstale == 1, slot, tinv[slot])  # stale register reports old label (= slot)
            ok = label == l
            if obs == 'pos': ok &= (slot == s_new)
            und &= ok
        out[base:base + len(st)] = und
    return out, K, bidx

def closed_mask(K, edges, chunk_bits=22):
    total = 1 << K; out = np.empty(total, dtype=bool); step = 1 << min(chunk_bits, K)
    for base in range(0, total, step):
        st = np.arange(base, min(base + step, total), dtype=np.int64)
        ok = np.ones(st.shape, dtype=bool)
        for u, v in edges: ok &= ~(((st >> u) & 1 == 1) & ((st >> v) & 1 == 0))
        out[base:base + len(st)] = ok
    return out

def digraph(N, NA, pi, P, bidx):
    E = set()
    for (i, l) in P:
        if pi[l] == l: continue
        E.add((bidx[pi[l]], i)); E.add((i, bidx[l]))
    return E

def sc_conditions(N, NA, pi, P):
    M = [l for l in range(N) if pi[l] != l]
    Pm = [(i, l) for i, l in P if pi[l] != l]
    if {l for _, l in Pm} != set(M) or {i for i, _ in Pm} != set(range(NA)): return False
    cyc = cycles_of(pi); cid = {l: k for k, c in enumerate(cyc) for l in c}
    par = list(range(NA + len(cyc)))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for i, l in Pm: par[f(i)] = f(NA + cid[l])
    return len({f(x) for x in range(len(par))}) == 1

def min_suite(N, NA, pi):
    """constructive suite of size max(|M|, NA + c - 1) (proof construction):
    source 0 joins every cycle; other sources fill cycle deficits first."""
    cyc = cycles_of(pi); c = len(cyc); M = sum(len(x) for x in cyc)
    deficit = [len(cy) - 1 for cy in cyc]; assign = []
    for i in range(1, NA):
        k = next((k for k in range(c) if deficit[k] > 0), 0)
        if deficit[k] > 0: deficit[k] -= 1
        assign.append((i, k))
    edges = [(0, k) for k in range(c)] + assign
    used = {k: 0 for k in range(c)}; P = []
    for i, k in edges:
        lab = cyc[k][used[k] % len(cyc[k])]; used[k] += 1; P.append((i, lab))
    for k in range(c):
        for j in range(used[k], len(cyc[k])): P.append((0, cyc[k][j]))
    assert len(P) == max(M, NA + c - 1), (len(P), M, NA, c)
    return P

def perm_with_cycles(N, lengths, rng):
    slots = rng.sample(range(N), sum(lengths)); pi = list(range(N)); k = 0
    for L in lengths:
        cyc = slots[k:k + L]; k += L
        for j in range(L): pi[cyc[j]] = cyc[(j + 1) % L]
    return pi

if __name__ == '__main__':
    N = NA = 16; rng = random.Random(2026); res = []; t0 = time.time()
    types = [(2,), (3,), (4,), (2, 2), (2, 3), (2, 2, 2), (3, 3), (2, 2, 2, 2), (4, 4), (2, 6)]
    for lengths in types:
        pi = perm_with_cycles(N, lengths, rng); M = sum(lengths); c = len(lengths)
        suites = {}
        P = min_suite(N, NA, pi); suites['minimal'] = P
        suites['minimal_minus_one'] = P[:-1]
        if c >= 2:   # every source & every label tested, but sources split between cycles -> disconnected
            cyc = cycles_of(pi); half = NA // 2
            Q = [(i, cyc[0][i % len(cyc[0])]) for i in range(half)] + \
                [(i, cyc[1 + (i % (c - 1))][i % len(cyc[1 + (i % (c - 1))])]) for i in range(half, NA)]
            for k, cy in enumerate(cyc):
                for l in cy:
                    if l not in {x for _, x in Q}: Q.append((0 if k == 0 else half, l))
            suites['all_covered_disconnected'] = Q
        cand = [(i, l) for i in range(NA) for l in range(N) if pi[l] != l]
        for r in range(3):
            suites[f'random{r}'] = rng.sample(cand, rng.randint(M, min(len(cand), NA + c + 6)))
        for name, S in suites.items():
            und, K, bidx = simulate_undetected(N, NA, pi, S)
            cl = closed_mask(K, digraph(N, NA, pi, S, bidx))
            n_und = int(und.sum()); complete_brute = bool(n_und == 2 and und[0] and und[-1])
            row = dict(cycles=list(lengths), K=K, suite=name, size=len(S), undetected=n_und,
                       char_exact=bool(np.array_equal(und, cl)), complete=complete_brute,
                       criterion=sc_conditions(N, NA, pi, S))
            row['ok'] = bool(row['char_exact'] and row['complete'] == row['criterion'])
            if name == 'minimal': row['ok'] &= complete_brute
            if name in ('minimal_minus_one', 'all_covered_disconnected'): row['ok'] &= not complete_brute
            res.append(row)
            print(f"{str(lengths):<14} K={K:<2} {name:<26} |P|={len(S):<3} undetected={n_und:<8} "
                  f"theory==sim:{row['char_exact']}  complete:{complete_brute}  criterion:{row['criterion']}  "
                  f"{'OK' if row['ok'] else 'MISMATCH'}  t={time.time() - t0:.0f}s", flush=True)
    json.dump(res, open('scale16_results.json', 'w'), indent=1)
    print('rows', len(res), 'mismatches', sum(not r['ok'] for r in res))
