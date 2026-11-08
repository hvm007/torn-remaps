# Torn remaps at full size, and the fault-model hierarchy (phase 34, step 2)

## 1. Exhaustive checks at N = 16 with 16 per-source tables (`scale16.py`, `agnostic16.py`)

Every torn state is simulated packet by packet with numpy, independently of the graph theory: 2^18 to 2^24 states per case, **380 million states in total**.

| check | cases | result |
|---|---|---|
| T2: undetected states = closed sets of G_P, compared state by state | 57 (remap, suite) pairs, 10 remap shapes | exact in 57/57 |
| T3: complete ⇔ the three conditions | 57 | 57/57 |
| T4: the proof's construction, size max(\|M\|, 16 + c − 1), is complete | 10 shapes (16–19 packets) | 10/10 complete |
| the same suite minus one packet | 10 | 10/10 incomplete |
| every source and every moved label tested, but sources split across cycles | 7 multi-cycle shapes | **7/7 incomplete**, as T3(iii) predicts |
| T5: the 240-packet agnostic suite (source i skips label i) | all 120 transpositions + 28 other remaps | complete in all 148 |
| T5: drop one more label at one source (239 packets) | swap of the two skipped labels | escapes = {A_0} and its complement, exactly as predicted; the escape misdelivers in operation |

The "all covered but disconnected" row is the key one. A suite that touches every table and every moved label still lets a torn update through, and coverage reasoning cannot see it.

## 2. Fault-model hierarchy (`sentinel.py`)

| how the update tears | label-only test | position-observing test |
|---|---|---|
| interrupted after k of K ordered writes | **2 packets always**; **1** iff the write order is a *sentinel order*; "nothing written" never detectable | **1 packet always** (target the last write) |
| one dropped write | max(\|M\|, N_A) | max(\|M\|, N_A) |
| any subset of writes lost | **max(\|M\|, N_A + c − 1)**, needs strong connectivity | max(\|M\|, N_A) |
| remap unknown to the tester | N_A(N − 1) = 240 at 4×4 | N_A(N − 1) |

**Sentinel order.** Packet (i, ℓ) detects exactly the interruption points k in one interval:

- label-only: [pos B_σ(ℓ), pos A_i) ∪ [pos A_i, pos B_τ(ℓ));
- position-observing: [0, max(pos A_i, pos B_τ(ℓ))).

So one label-only packet certifies the whole update iff the first write is A_i or B_σ(ℓ) and the last write is A_i or B_τ(ℓ). This is a design-for-test rule: write the remap so that its two ends belong to one test packet, and a single packet certifies that the update completed.

Checked by simulating every interruption point:

| claim | checks | result |
|---|---|---|
| S1: interval structure | 34,272 packet checks | 0 mismatches |
| S2: sentinel iff condition | 300 random orders | 300/300 |
| S3: single-drop criterion | 200 suites | 200/200 |
| S4: 1 packet (position) / 2 packets (label-only) always suffice | 150 random orders | 150/150 |
| sentinel orders built explicitly | 100 | all detect every interruption |

With a random write order, one label-only packet is enough in 1/3 of cases; otherwise two are needed.

**Why S4 holds (sketch).** Position observation: if the last write is A_i, send any moved label from i; if it is B_s, send label τ⁻¹(s) from any source. Either packet sees every earlier k. Label-only: one packet anchored at the first write and one at the last write cover [1, K).

## 3. Status

- **Proved, sketch level:** T1–T5, T7 for the full suite, S1–S4.
- **Exhaustive at N ≤ 7 for every shape:** T2–T5, T7.
- **Exhaustive at N = 16 for 10 shapes:** T2–T5.
- **Silicon (one shared table):** C1–C6.
- **Not done:** per-source tables in RTL. This is deliberate: delivery semantics were already confirmed byte-exact on the board, and the content of the theorems is combinatorial.
