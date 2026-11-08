"""T5 at N = 16, N_A = 16: the remap-agnostic suite of N_A(N-1) = 240 packets
(source i tests every label except i) is complete for every remap checked,
and dropping one more label at one source opens an escape."""
import numpy as np, itertools, random, json, sys, time
sys.path.insert(0, '.')
from scale16 import simulate_undetected, perm_with_cycles
N = NA = 16
AG = [(i, l) for i in range(NA) for l in range(N) if l != i]
assert len(AG) == NA * (N - 1) == 240
res = dict(suite_size=len(AG)); t0 = time.time()
# all 120 transpositions, exhaustive over 2^18 torn states each
bad = 0
for a, b in itertools.combinations(range(N), 2):
    pi = list(range(N)); pi[a], pi[b] = b, a
    und, K, _ = simulate_undetected(N, NA, pi, AG)
    if not (und.sum() == 2 and und[0] and und[-1]): bad += 1
res['transpositions'] = dict(checked=120, incomplete=bad)
print('transpositions: 120 checked, incomplete =', bad, f'{time.time()-t0:.0f}s', flush=True)
# other remap shapes, exhaustive
rng = random.Random(7); shapes = [(3,), (4,), (2, 2), (5,), (2, 3), (3, 3), (2, 2, 2)]; bad2 = 0; n2 = 0
for sh in shapes:
    for r in range(4):
        pi = perm_with_cycles(N, sh, rng)
        und, K, _ = simulate_undetected(N, NA, pi, AG); n2 += 1
        if not (und.sum() == 2 and und[0] and und[-1]): bad2 += 1
res['other_shapes'] = dict(checked=n2, incomplete=bad2)
print('other shapes:', n2, 'checked, incomplete =', bad2, f'{time.time()-t0:.0f}s', flush=True)
# negative: source 0 skips labels 0 AND 1 -> transposition (0 1) hides {A_0}
AG2 = [p for p in AG if p != (0, 1)]
pi = list(range(N)); pi[0], pi[1] = 1, 0
und, K, _ = simulate_undetected(N, NA, pi, AG2)
esc = [int(s) for s in np.nonzero(und)[0] if s not in (0, (1 << K) - 1)]
exp = [1, ((1 << K) - 1) ^ 1]   # {A_0} and its complement: A_0 is an isolated node, both sides closed
res['negative'] = dict(suite_size=len(AG2), escapes=[bin(s) for s in esc], as_predicted=sorted(esc) == sorted(exp))
print('negative (239 packets): escapes', [bin(s) for s in esc], '-> exactly {A_0} and its complement, as predicted:', sorted(esc) == sorted(exp))
# the escape is a real fault: in operation, source 0 sending to label 1 misdelivers
full = [(0, 1)]
und_full, _, _ = simulate_undetected(N, NA, pi, full)
res['negative']['escape_is_real_fault'] = bool(not und_full[1])
print('escape is a real fault (packet 0->1 detects it):', not und_full[1])
json.dump(res, open('agnostic16_results.json', 'w'), indent=1)
