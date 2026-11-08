# Phases 33 and 34: silicon result (Basys-3, 31 Oct 2026)

There are 11 bitstreams, all at PASS with positive slack (4.36–8.89 ns), and 3 hardware-reset trials of each, every trial byte-stable. Every predicted record and claim was registered before any build, and the phase-33 and phase-34 prediction hashes are intact. All of it was re-scored independently by `rescore_independent.py`, from the raw captures and the label vectors Vivado actually built, without reusing the board check scripts.

**Phase 33 (delivered-set blindness).** Three swaps outside the suite's delivered set D are byte-identical to clean, even though they misdeliver labels 15/12, 10/8 and 5/7 in operation. The three swaps inside D change exactly the predicted packets: [1], [2, 12] and [3, 4, 10, 11].

**Phase 34 (torn remaps):**
- C1, non-monotone. Stale sets {A} ⊂ {A,B1} ⊂ {A,B0,B1} give 2, 1 and 0 wrong packets on silicon.
- C2, non-bijective. Each torn variant has one label reported by two slots.
- C3, swap ambiguity. The two half-applied swaps give identical label-only observations; only the delivered slot differs (0 vs 1).
- C4, the 3-cycle resolves which side is stale. Packet 0 asks for 9 and gets 2 when A is stale, 3 when A is fresh.
- C5/C6, self-consistent 3-cycle. Zero wrong labels, while exactly packets 0, 1, 3, 7 and 8 change.
- FABRIC-only variants differ from their HOST twin only in the label and CRC bytes.

**Framing.** This shows that the model's predictions match a synthesized implementation end to end. It is not independent evidence for the theorems; that comes from the proofs and the exhaustive checks.
