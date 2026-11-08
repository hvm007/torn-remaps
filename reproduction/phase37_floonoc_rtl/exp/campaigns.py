"""Campaign definitions for the FlooNoC torn-remap experiment (shared by the model and the TB generator).
Ports/regions: cluster (x,y) -> 4x+y (0..15), HBM k -> 16+k.  Old map: region r served by port r."""
CLUSTERS = list(range(16)); H = [16, 17, 18, 19]
REMAPS = {0: {16: 18, 18: 16},                       # one HBM failover: HBM0 <-> HBM2
          1: {16: 17, 17: 16, 18: 19, 19: 18}}       # two failovers: HBM0 <-> HBM1, HBM2 <-> HBM3
def tau(remap): t = list(range(20)); [t.__setitem__(a, b) for a, b in REMAPS[remap].items()]; return t
A = lambda i: i            # table of cluster i
B = lambda p: 32 + p       # identity register of port p
lower = [4*x + y for x in range(4) for y in (0, 1)]   # clusters in rows y = 0, 1
upper = [4*x + y for x in range(4) for y in (2, 3)]
ORDERS = {
  0: [B(16)] + [A(i) for i in CLUSTERS if i != 5] + [B(18), A(5)],          # sentinel for (5, Hbm0)
  1: [A(i) for i in CLUSTERS] + [B(16), B(18)],                             # tables first
  2: [A(i) for i in lower] + [B(16), B(17)] + [A(i) for i in upper] + [B(18), B(19)],   # half by half
}
split = [(i, [16, 17][n % 2]) for n, i in enumerate(lower)] + [(i, [18, 19][n % 2]) for n, i in enumerate(upper)]
SUITES = {0: [(5, 16)],                 # the sentinel packet: cluster (1,1) reads region Hbm0
          1: [(0, 16)],                 # tables-first order: packet from the first-written table
          2: split,                     # covers every interface and every remapped region
          3: split + [(0, 18)],         # one bridging packet: minimum max(m, N_A + c - 1) = 17
          4: [(4, 18)]}                 # witness: normal read of region Hbm2 by cluster (1,0)
CAMPAIGNS = [  # (remap, order, suite, drop, name)
  (0, 0, 0, False, "one failover, sentinel order, 1 packet"),
  (0, 1, 0, False, "one failover, tables first, same packet"),
  (0, 1, 1, False, "one failover, tables first, packet from first-written table"),
  (1, 2, 2, False, "two failovers, half-by-half order, split suite (16)"),
  (1, 2, 3, False, "two failovers, half-by-half order, bridged suite (17)"),
  (1, 2, 4, False, "two failovers, normal read Hbm2 by cluster (1,0)"),
  (1, 2, 3, True,  "two failovers, bridged suite, one lost write")]
