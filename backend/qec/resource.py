"""
Physical qubit resource estimator for fault-tolerant RSA-2048 factoring.

Uses a surface-code logical error rate model and adjustable algorithmic parameters.
The Mosca-style panel computes required code distance and total physical qubit count.

Reference estimates (all assume p ~ 0.1% physical error rate):
  Gidney & Ekera 2019  : ~20 million physical qubits  (arXiv:1905.09749)
  Gidney 2025          : < 1 million physical qubits  (arXiv:2505.15917)
  Heterogeneous 2026   : ~100 thousand physical qubits (arXiv:2604.06319 / Feb 2026)

The improvement across estimates comes from:
  - Approximate residue arithmetic (2025)
  - Yoked surface codes for idle qubit storage (2025)
  - Magic state cultivation vs distillation (2025)
  - Novel architectural layouts (2026)

This estimator uses the 2025 algorithmic T-count as its default.
"""

import math


# Approximate logical error rate for a surface code of distance d
# at physical error rate p, using the standard threshold approximation.
# p_th ~ 1% is well-established for circuit-level noise; we use 0.01.
_P_TH = 0.01
_A = 0.1  # pre-factor — empirically calibrated for surface codes


def logical_error_rate(p: float, d: int) -> float:
    """p_L ≈ A * (p / p_th)^((d+1)/2)"""
    return _A * (p / _P_TH) ** ((d + 1) / 2)


def min_distance(p: float, p_L_per_gate: float) -> int:
    """Smallest odd d >= 3 such that p_L(p, d) < p_L_per_gate."""
    for d in range(3, 61, 2):
        if logical_error_rate(p, d) < p_L_per_gate:
            return d
    return 61   # above d=60 — system is too noisy


def estimate(
    p_physical: float,
    n_logical: int = 3_000,
    t_gates: int = 3_000_000_000,
    p_total_failure: float = 0.5,
) -> dict:
    """
    Estimate physical qubit count for fault-tolerant Shor factoring of RSA-2048.

    Parameters
    ----------
    p_physical      : physical gate error rate (e.g. 0.001 = 0.1%)
    n_logical       : number of logical qubits needed (default: ~3000, from Gidney 2025)
    t_gates         : total T-gate count for Shor's algorithm (Gidney 2025: ~3e9, reduced from 2019)
    p_total_failure : acceptable total failure probability (default 50% — maximally lenient)

    Returns
    -------
    dict with:
      d               : required surface code distance
      p_L_per_gate    : required logical error rate per T gate
      p_L_achieved    : actual logical error rate at chosen d
      phys_per_logical: 2*d^2 physical qubits per logical qubit (rotated surface code)
      total_physical  : n_logical * phys_per_logical
      feasible        : bool — True if total < 10 million
      references      : {label: qubit_count} dict of published estimates
    """
    # Target per-gate failure budget
    p_L_per_gate = p_total_failure / t_gates

    d = min_distance(p_physical, p_L_per_gate)
    phys_per_logical = 2 * d * d
    total = n_logical * phys_per_logical
    p_L = logical_error_rate(p_physical, d)

    return {
        "d": d,
        "p_physical": p_physical,
        "n_logical": n_logical,
        "t_gates": t_gates,
        "p_L_per_gate": p_L_per_gate,
        "p_L_achieved": p_L,
        "phys_per_logical": phys_per_logical,
        "total_physical": total,
        "feasible": total < 10_000_000,
        "references": {
            "Gidney & Ekera 2019 (arXiv:1905.09749)": 20_000_000,
            "Gidney 2025 (arXiv:2505.15917)": 1_000_000,
            "Heterogeneous arch. 2026 (arXiv:2604.06319)": 100_000,
        },
    }
