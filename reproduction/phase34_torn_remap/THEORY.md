# Torn remaps: testability theory (phase 34)

## Setting

A NoC remap moves logical labels to new physical slots, for example moving a core onto a spare. The intended old→new change is σ→τ, and ρ = τ⁻¹σ is the remap on labels. M is the set of moved labels and c is the number of nontrivial cycles of ρ.

The remap is written into two kinds of state:

- **A_i**: the address table at source i (label → slot). There are N_A of them.
- **B_s**: the identity register at slot s (the label that slot reports).

An update is **torn** if some components hold the new map (fresh) and others still hold the old one (stale). Two simpler cases are special torn states:

- **One-sided:** every A on one version, every B on the other.
- **Self-consistent:** all components stale. This is the old map, which is itself consistent.

A packet (i, ℓ) goes to slot A_i(ℓ) and reports B at that slot. There are two observation models:

- **label-only:** in-field, the endpoint echoes its ID.
- **position:** the hops or delivery slot are also visible, as in the lab diagnoser and the board captures.

## Results

**T1. Version agreement and masking.** Assume label-only observation and a moved label ℓ. Packet (i, ℓ) reports the correct label iff A_i and the register it reaches are on the same version. A stale table plus a stale register cancel out, so detection is not monotone.

This is the structural difference from Boolean network tomography and from Monocle's probe checks. There, any faulty element on a probe's path makes that probe fail.

*Corollary:* under label-only observation, the all-stale state is undetectable by any suite. You cannot confirm that a remap happened from labels alone. One position-observing packet on a moved label fixes this.

**T2. Exact characterization.** Each packet (i, ℓ) with ℓ ∈ M contributes the edges B_τ(ℓ) → A_i → B_σ(ℓ). Under label-only observation, the torn states undetected by suite P are exactly the stale sets closed under these edges.

*Proof:* there are four cases per packet; see `torn.py`. The edges are the implications "B_τ stale ⇒ A_i stale ⇒ B_σ stale."

**T3. Completeness criterion.** Under label-only observation, P detects every torn state except all-stale iff the digraph G_P is strongly connected. That holds iff all three of these do:

- (i) every moved label is tested;
- (ii) every source sends at least one moved label;
- (iii) the bipartite graph between sources and the cycles of ρ, linking each source to the cycles it tests, is connected.

**T4. Tight minimum, remap known.** The minimum suite size is:

- label-only: **max(|M|, N_A + c − 1)**
- position: **max(|M|, N_A)**

*Lower bound:* (i) forces at least |M| packets. (iii) needs a connected bipartite graph on N_A + c nodes, which takes at least N_A + c − 1 distinct source–cycle edges.

*Construction:* take a bipartite spanning tree whose cycle-degrees are at most the cycle lengths, or at least them, then fill in the remaining labels.

The gap c − 1 is the extra price of label-only observation.

**T5. Remap-agnostic lower bound.** Suppose one suite must work for every possible remap. Under either observation model, each source must test at least N − 1 labels; otherwise a transposition of two labels it never tests hides its stale table. So:

- the minimum is **N_A(N − 1)** for N_A ≥ 2;
- the minimum is **N** for a single shared table.

For comparison, an atomic update (the uniform one-sided law) needs only N − 1. The cost scales with the product of update atoms and label space: the granularity principle, made quantitative.

**T6. Torn states break bijectivity.** A torn state with a single stale register makes two slots report the same label. This is the non-bijective address-fault regime of memory testing (Hamdioui & van de Goor). Atomic one-sided remaps are bijective, a regime memories cannot have. Torn remaps connect the two.

**T7. Diagnosis.** Take the full label-only suite (every source × every moved label). Torn states are identifiable up to the global version flip **iff ρ has no 2-cycles.**

*Reason:* a stale table yields the wrong label ρ(ℓ), while a stale register yields ρ⁻¹(ℓ). These coincide exactly on transpositions.

A core-to-spare swap is a transposition. Label-only field tests therefore cannot tell which side of a spare swap failed to update; position observation can. With position observation, the full suite identifies every state.

## Verification (independent packet-level simulation, not the graph)

| check | instances | mismatches |
|---|---|---|
| T2/T3 characterization, label-only, N ≤ 7, N_A ≤ 5, exhaustive over torn states | 6,000 (instance, suite) pairs; 3,608 complete, 2,392 incomplete | 0 |
| position model = monotone coverage | 3,000 pairs | 0 |
| T4 minimum, exhaustive over suites, every cycle type for N ≤ 6, N_A ≤ 5 | 98 cases | 0 |
| T5 agnostic minimum, every remap at once, N ≤ 4, N_A ≤ 4, both models | 16 cases | 0 |
| T7 identifiability, full suite, every cycle type for N ≤ 6, N_A ≤ 3 | 66 label-only + 66 position cases | pattern holds in all 66; position identifies every state in all 66; proof sketch above |

For transposition-only remaps, the number of label-only classes is 2^N_A·(4^t − 2^t)/2 + 2^t, with t the number of transpositions. This fits t ≤ 3 and is unproven.

## 4×4 example (N = 16, one spare swap)

| update granularity | minimum suite |
|---|---|
| atomic update, shared table (uniform law) | 15 packets for any remap |
| torn update, shared table | 2 if the remap is known; 16 for any remap |
| torn update, 16 per-NI tables, label-only | 16 if known; **240** for any remap |
| torn update, NI-atomic (table and register update together) | about N/2 if known; exhaustive results for N ≤ 5 only, no formula yet |

## Novelty vs. prior art

- **Boolean tomography** (Ma/He/Towsley 2014; Bartolini et al. 2019): monotone OR failures, so no masking. T1–T4 differ structurally.
- **Monocle** (Perešíni et al., CoNEXT 2015): checks rules one at a time. It explicitly leaves overlapping unconfirmed updates to future work and gives no completeness condition for partial updates.
- **Consistent updates** (Reitblatt et al., SIGCOMM 2012): prevents torn states by versioning rather than testing for them.
- **NoC spare remapping** (Zhang et al., TVLSI 2009): designs the remap but does not test that it landed.
- I found no prior characterization of label-only testability of partially applied remaps. That is a search result, not proof of absence.

## Caveats

- The theory is model-level, with deterministic delivery to A_i(ℓ). Routers whose own tables are torn (ID routing as in FlooNoC) can loop; that case is open.
- Hardware validation is possible only for N_A = 1, since the board RTL has one host table and per-slot fabric labels. Per-NI tables would need an RTL change.
- The NI-atomic minimum has data only, no formula.
- T7's class-count formula is fitted, not proved.
