"""Torn-remap testability: independent packet-level simulation vs. graph theory.

Model
-----
Labels and slots are 0..N-1.  Old map sigma: label -> slot (identity here),
new map tau = pi (label l moves to slot pi[l]).  Components:
  A_i  source address table at source i (label -> slot), i in 0..NA-1
  B_s  identity register at slot s (slot -> label it reports)
A torn state marks each component fresh (new map) or stale (old map).
Packet (i, l): source i sends to label l.
  slot   = tau[l] if A_i fresh else sigma[l]
  label  = tauinv[slot] if B_slot fresh else sigmainv[slot]
Observation 'label': only the reported label.  'pos': (slot, label).
A state is undetected by a suite P iff every packet observes what the
all-fresh (intended) state observes.

The simulator below never uses the graph; graph predictions are separate.
"""
import itertools, random, sys
from functools import lru_cache

def cycles_of(pi):
    n = len(pi); seen = [False]*n; cyc = []
    for s in range(n):
        if seen[s] or pi[s] == s:
            seen[s] = True; continue
        c = []; x = s
        while not seen[x]:
            seen[x] = True; c.append(x); x = pi[x]
        cyc.append(c)
    return cyc

class Inst:
    """components: list of ('A',i) / ('B',s); atoms: list of tuples of components
    (granularity: components in one atom share a version)."""
    def __init__(self, N, NA, pi, atoms=None, src_slot=None):
        self.N, self.NA, self.pi = N, NA, list(pi)
        self.sigma = list(range(N)); self.siginv = list(range(N))
        self.tau = list(pi); self.tauinv = [0]*N
        for l, s in enumerate(pi): self.tauinv[s] = l
        self.M = [l for l in range(N) if pi[l] != l]
        movedslots = sorted(set(self.tau[l] for l in self.M))
        if atoms is None:  # table-atomic: every A_i and every moved B_s its own atom
            atoms = [(('A', i),) for i in range(NA)] + [(('B', s),) for s in movedslots]
        self.atoms = atoms
        self.comp_atom = {}
        for k, at in enumerate(atoms):
            for c in at: self.comp_atom[c] = k
        self.K = len(atoms)
        self.src_slot = src_slot

    def stale(self, state, comp):
        k = self.comp_atom.get(comp)
        return False if k is None else bool(state >> k & 1)

    def observe(self, state, i, l, obs):
        slot = self.sigma[l] if self.stale(state, ('A', i)) else self.tau[l]
        lab = self.siginv[slot] if self.stale(state, ('B', slot)) else self.tauinv[slot]
        return lab if obs == 'label' else (slot, lab)

    def undetected_mask(self, i, l, obs):
        """bitmask over states (bit = state index) where packet (i,l) does NOT detect."""
        ref = self.observe(0, i, l, obs); m = 0
        for st in range(1 << self.K):
            if self.observe(st, i, l, obs) == ref: m |= 1 << st
        return m

    # ---------------- graph theory predictions ----------------
    def digraph(self, P):
        """edges between atoms: b_tau(l) -> A_i -> b_sigma(l) for each packet with l moved."""
        E = set()
        for (i, l) in P:
            if self.pi[l] == l: continue
            a = self.comp_atom[('A', i)]
            bt = self.comp_atom[('B', self.tau[l])]
            bs = self.comp_atom[('B', self.sigma[l])]
            E.add((bt, a)); E.add((a, bs))
        return E

    def closed_sets(self, P):
        E = self.digraph(P); out = []
        for st in range(1 << self.K):
            ok = all(not (st >> u & 1) or (st >> v & 1) for (u, v) in E)
            if ok: out.append(st)
        return out

    def strongly_connected(self, P):
        E = self.digraph(P); K = self.K
        adj = [[] for _ in range(K)]; radj = [[] for _ in range(K)]
        for u, v in E: adj[u].append(v); radj[v].append(u)
        def reach(g):
            seen = {0}; st = [0]
            while st:
                u = st.pop()
                for v in g[u]:
                    if v not in seen: seen.add(v); st.append(v)
            return len(seen) == K
        return reach(adj) and reach(radj)

    def three_conditions(self, P):
        """(i) every moved label tested, (ii) every source sends >=1 moved label,
        (iii) source-cycle incidence graph connected.  Table-atomic only."""
        Pm = [(i, l) for (i, l) in P if self.pi[l] != l]
        if set(l for _, l in Pm) != set(self.M): return False
        if set(i for i, _ in Pm) != set(range(self.NA)): return False
        cyc = cycles_of(self.pi); cid = {}
        for k, c in enumerate(cyc):
            for l in c: cid[l] = k
        # union-find over sources (0..NA-1) and cycles (NA..)
        par = list(range(self.NA + len(cyc)))
        def f(x):
            while par[x] != x: par[x] = par[par[x]]; x = par[x]
            return x
        for i, l in Pm: par[f(i)] = f(self.NA + cid[l])
        return len(set(f(x) for x in range(len(par)))) == 1


def check_characterization(trials=400, seed=1):
    rng = random.Random(seed); bad = 0; tot = 0
    for t in range(trials):
        N = rng.randint(3, 6); NA = rng.randint(1, 4)
        pi = list(range(N))
        while pi == list(range(N)): rng.shuffle(pi)
        I = Inst(N, NA, pi)
        if I.K > 12: continue
        cand = [(i, l) for i in range(NA) for l in range(N)]
        P = rng.sample(cand, rng.randint(1, len(cand)))
        full = (1 << (1 << I.K)) - 1; m = full
        for (i, l) in P: m &= I.undetected_mask(i, l, 'label')
        brute = [st for st in range(1 << I.K) if m >> st & 1]
        theory = I.closed_sets(P)
        sc = I.strongly_connected(P); tc = I.three_conditions(P)
        complete = set(brute) <= {0, (1 << I.K) - 1}
        tot += 1
        if brute != theory or sc != complete or tc != complete:
            bad += 1
            print('MISMATCH', N, NA, pi, P, len(brute), len(theory), sc, tc, complete)
    return tot, bad


def min_complete(I, obs, cand=None, limit=None):
    """exhaustive minimum suite size so that undetected states <= {fresh, all-stale}
    (label) or {fresh} (pos)."""
    if cand is None:
        cand = [(i, l) for i in range(I.NA) for l in I.M]
    masks = [I.undetected_mask(i, l, obs) for (i, l) in cand]
    allst = (1 << I.K) - 1
    target = (1 << 0) | ((1 << allst) if obs == 'label' else 0)
    full = (1 << (1 << I.K)) - 1
    for k in range(1, len(cand) + 1):
        if limit and k > limit: return None
        for comb in itertools.combinations(range(len(cand)), k):
            m = full
            for j in comb:
                m &= masks[j]
                if m == target: break
            if m & ~target == 0: return k, [cand[j] for j in comb]
    return None


if __name__ == '__main__':
    tot, bad = check_characterization()
    print(f'characterization: {tot} random (instance, suite) pairs, mismatches={bad}')
