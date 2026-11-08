# Occamy case study (model level)

`occamy_case.py` reads FlooNoC's `floogen/examples/occamy_mesh_xy.yml` as data: 29 managers, each
with its own system address map, and 36 subordinate regions. It applies the packet-level model
of Section III to a double HBM failover (HBM0<->HBM2 and HBM5<->HBM7), so K = 29 tables + 4
registers = 33 components.

    python3 occamy_case.py <FlooNoC>/floogen/examples/occamy_mesh_xy.yml     # needs numpy, pyyaml

Result (`occamy_case.json`):
- the 29-packet split plan (lower-half managers test HBM0/2, upper-half test HBM5/7) misses
  interruption k = 17 of the half-by-half order;
- the 30-packet bridged plan, the minimum max(m, N_A + c - 1), misses none;
- 2,000,000 uniformly random torn states contain no escape for either plan. The split plan's
  implication digraph has exactly two non-trivial closed sets (17 and 16 components), i.e. 2 of
  the 2^33 states, which is why sampling does not find them.

Delivery is modelled from the address maps only; this is not an RTL simulation.
