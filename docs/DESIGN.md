# QEC Lab — Design Notes

## What this is

QEC Lab simulates quantum error correction on the **rotated surface code** —
the leading candidate for fault-tolerant quantum computation.
It exists to make two things concrete:

1. **Why error correction is hard**: even at 1% physical error rates, naive
   encoding makes things *worse* — you need to cross the threshold.
2. **Why RSA is threatened**: once a fault-tolerant machine crosses the threshold,
   the qubit count needed to run Shor's algorithm has been shrinking rapidly.

---

## Code structure

### Rotated surface code lattice

Distance-d code encodes 1 logical qubit into d² physical (data) qubits,
protected by d²−1 stabilizer measurements.

**Data qubits** at integer grid positions (row, col) ∈ [0, d−1]².

**Interior stabilizer faces** at half-integer positions (row+0.5, col+0.5):
- (row+col) % 2 == 0 → **X-type** stabilizer (measures Z⊗Z⊗Z⊗Z parity)
- (row+col) % 2 == 1 → **Z-type** stabilizer (measures X⊗X⊗X⊗X parity)

**Boundary (weight-2) stabilizers:**
- Top/bottom: Z-type, alternating even/odd columns
- Left/right: X-type, alternating odd/even rows

This gives exactly d²−1 stabilizers total, leaving 1 logical qubit.

### Logical operators

- **Logical X̄** = X⊗d on the top row of data qubits
- **Logical Z̄** = Z⊗d on the left column of data qubits

A logical error occurs when the net operator (physical error ⊕ correction)
has odd overlap with the respective logical operator.

---

## Noise models

### Shot simulation (code-capacity)

Each data qubit independently:
- Suffers X error with probability p
- Suffers Z error with probability p (independent channel)

No measurement errors. This is the simplest model that preserves the
threshold structure while being visualisable.

### Threshold curve (circuit-level via Stim)

Uses Stim's `surface_code:rotated_memory_z` circuit generator with
`after_clifford_depolarization=p` applied throughout the full syndrome
extraction circuit, including ancilla preparation and measurement.

This is the standard model in surface code threshold papers.
Threshold ≈ 0.5–1% under this model.

---

## Decoder

Both modes use **PyMatching v2** (Minimum Weight Perfect Matching).

For shot simulation: PyMatching is called with a parity-check matrix H
where H[i,j] = 1 if data qubit j is in stabilizer i.
Boundary stabilizers are connected to a virtual node to allow correction
paths to terminate at the code boundary.

For threshold: `Matching.from_detector_error_model(DEM)` uses Stim's
optimised detector error model directly — faster and more accurate.

---

## Resource estimator

### Logical error rate model

Standard surface code approximation:

```
p_L ≈ 0.1 × (p / p_th)^((d+1)/2)
```

where p_th = 1% and the 0.1 pre-factor is empirically calibrated.

### Physical qubits per logical qubit

Rotated surface code: **2d²** physical qubits per logical qubit.

### RSA-2048 parameters (defaults)

| Parameter | Value | Source |
|---|---|---|
| Logical qubits (n_L) | 3 000 | Gidney 2025 |
| T-gate count | 3 × 10⁹ | Gidney 2025 (reduced from 10¹² in 2019) |
| Target p_total failure | 50% | Conservative |

### Published estimates

| Paper | Qubits | Notes |
|---|---|---|
| Gidney & Ekerå 2019 (arXiv:1905.09749) | ~20 M | Original surface-code Shor |
| Gidney 2025 (arXiv:2505.15917) | < 1 M | Approx. residue arithmetic + yoked codes + magic state cultivation |
| Heterogeneous 2026 (arXiv:2604.06319) | ~100 K | Novel architectural layout |

All assume p ≈ 0.1% physical error rate. The 20× reduction from 2019→2025
comes primarily from algorithmic improvements (lower T-count, better magic
state management), not from better error correction codes.

---

## What this project explicitly does NOT model

- Lattice surgery (logical gate implementation)
- Magic state distillation or cultivation circuits
- T-gate counts or full Shor circuit
- Multiple qubit code families (only rotated surface code)
- Temporal noise correlations
- Crosstalk or leakage errors
- Hardware-specific connectivity constraints
