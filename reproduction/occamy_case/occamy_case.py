"""Case study on the Occamy mesh configuration of FlooNoC (floogen/examples/occamy_mesh_xy.yml).
The YAML is read as data only.  Managers own a system address map (SAM) each; subordinate
regions are the labels.  Remap: two concurrent HBM channel failovers, HBM0<->HBM2 (lower half)
and HBM5<->HBM7 (upper half).  Packet-level semantics as in Section III of the paper."""
import sys, json, itertools, numpy as np, yaml
cfg = yaml.safe_load(open(sys.argv[1]))
ep = {e['name']: e for e in cfg['endpoints']}
def expand(e):
    a = e.get('array')
    if a is None: return [(e['name'],)]
    return [(e['name'],) + idx for idx in itertools.product(*[range(n) for n in a])]
# router coordinates of each endpoint, from the connections section
pos = {}
for c in cfg['connections']:
    name = c['src']
    if 'dst_idx' in c: pos[(name,)] = tuple(c['dst_idx'])
    elif name == 'cluster':
        for (x, y) in itertools.product(range(3), range(8)): pos[(name, x, y)] = (x, y)
    elif name == 'hbm':
        for k in range(8): pos[(name, k)] = (0, k)
    elif name == 'serial_link':
        for k in range(3): pos[(name, k)] = (k, 0)
managers = [n for e in cfg['endpoints'] if e.get('mgr_port_protocol') for n in expand(e)]
regions  = [n for e in cfg['endpoints'] if e.get('sbr_port_protocol') for n in expand(e)]
print(f"managers (each with its own SAM): {len(managers)}   subordinate regions: {len(regions)}")
# remap: labels = regions; sigma = identity placement; tau swaps HBM0<->HBM2 and HBM5<->HBM7
L = {r: i for i, r in enumerate(regions)}; N = len(regions)
pi = list(range(N))
for a, b in [(('hbm', 0), ('hbm', 2)), (('hbm', 5), ('hbm', 7))]:
    pi[L[a]], pi[L[b]] = L[b], L[a]
M = [l for l in range(N) if pi[l] != l]; tinv = {pi[l]: l for l in range(N)}
NA = len(managers)
regs = sorted({pi[l] for l in M}); bidx = {s: NA + j for j, s in enumerate(regs)}; K = NA + len(regs)
def observe(states, i, l):
    """states: uint64 array of torn states (bit = stale). returns (slot, label) arrays."""
    a = (states >> np.uint64(i)) & np.uint64(1)
    slot = np.where(a == 1, l, pi[l])
    out = np.empty_like(slot)
    for s in set([l, pi[l]]):
        if s in bidx:
            b = (states >> np.uint64(bidx[s])) & np.uint64(1)
            lab_s = np.where(b == 1, s, tinv[s])
        else:
            lab_s = np.full(states.shape, tinv.get(s, s))
        out = np.where(slot == s, lab_s, out)
    return slot, out
def detected(states, P):
    d = np.zeros(states.shape, bool)
    for (i, l) in P:
        _, lab = observe(states, i, l); d |= lab != l
    return d
# test plans: locality split (lower-half managers test HBM0/HBM2, upper-half test HBM5/HBM7)
lower = [i for i, m in enumerate(managers) if pos[m][1] <= 3]
upper = [i for i, m in enumerate(managers) if pos[m][1] >= 4]
lo_l = [L[('hbm', 0)], L[('hbm', 2)]]; up_l = [L[('hbm', 5)], L[('hbm', 7)]]
split = [(i, lo_l[k % 2]) for k, i in enumerate(lower)] + [(i, up_l[k % 2]) for k, i in enumerate(upper)]
bridged = split + [(lower[0], up_l[0])]
print(f"lower-half managers {len(lower)}, upper-half {len(upper)}; split plan {len(split)} packets; bridged {len(bridged)}; "
      f"Thm 4 minimum max(m, N_A+c-1) = {max(len(M), NA + 2 - 1)}")
# 1. the escape predicted by Theorem 3(iii): upper-half maps and the HBM5/HBM7 registers stale
X = 0
for i in upper: X |= 1 << i
for l in up_l: X |= 1 << bidx[pi[l]]
X = np.array([X], dtype=np.uint64)
res = {}
res['escape_state_silent_under_split'] = bool(not detected(X, split)[0])
res['escape_state_caught_by_bridged'] = bool(detected(X, bridged)[0])
w = (lower[1], up_l[0]); _, lab = observe(X, *w)
res['escape_is_real_fault'] = {'packet': [managers[w[0]], regions[w[1]]], 'reported': list(regions[int(lab[0])]), 'asked': list(regions[w[1]])}
# 2. the same state arises from an ordinary interrupted update: write lower half (maps + HBM0/2 regs), then upper half
order = lower + [bidx[pi[l]] for l in lo_l] + upper + [bidx[pi[l]] for l in up_l]
ks = np.arange(K + 1)
st = np.array([sum(1 << c for c in order[k:]) for k in ks], dtype=np.uint64)
res['interruptions_missed_by_split'] = [int(k) for k in ks[~detected(st, split)] if 0 < k < K]
res['interruptions_missed_by_bridged'] = [int(k) for k in ks[~detected(st, bridged)] if 0 < k < K]
res['split_after_write'] = len(lower) + 2
# 3. random torn states: bridged plan misses none (Theorem 3), split plan misses exactly the closed sets
rng = np.random.default_rng(2026)
S = rng.integers(0, 1 << K, size=2_000_000, dtype=np.uint64)
S = S[(S != 0) & (S != np.uint64((1 << K) - 1))]
res['random_states'] = int(S.size)
res['random_missed_by_bridged'] = int((~detected(S, bridged)).sum())
res['random_missed_by_split'] = int((~detected(S, split)).sum())
print(json.dumps(res, indent=1))
json.dump(dict(managers=len(managers), regions=len(regions), K=K, split=len(split), bridged=len(bridged), **res),
          open('occamy_case.json', 'w'), indent=1, default=str)
