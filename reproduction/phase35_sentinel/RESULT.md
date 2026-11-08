# Phase 35: sentinel write order on silicon (Basys-3, 31 Oct 2026)

The new bitstream `torn01_A_only_fresh` (host swapped, endpoint labels clean) passed with 7.361 ns of slack. Its 3 trials are byte-stable and byte-exact to the pre-registered record (sha256 1103ea67…).

| interruption point k | order O1 = B0, B1, A | order O2 = A, B0, B1 |
|---|---|---|
| 0 (nothing written) | clean: no wrong packet | clean: no wrong packet |
| 1 | torn01_A_stale: [5] | torn01_A_only_fresh: [5, 6] |
| 2 | t01_one_sided: [5, 6] | torn01_A_fresh: [5] |
| 3 (done) | t01_self_consistent: no wrong packet | t01_self_consistent: no wrong packet |

- **Packet 5** (asks 14) is the sentinel for both orders. It catches every interruption point, as the S2 rule predicts.
- **Packet 6** (asks 13) is the sentinel for neither, and it misses one interruption point in each order.
- **k = 0 and k = 3** are invisible to label-only observation (T1 corollary), as predicted.
