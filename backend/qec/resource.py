"""
Physical qubit resource estimator for fault-tolerant RSA-2048 factoring.

This is an illustrative surface-code model, not a hardware forecast. When the
distance search reaches its cap, the returned d=61 value is a sentinel and the
result is explicitly marked infeasible rather than silently treated as a valid
resource estimate.
"""

import math

_P_TH = 0.01
_A = 0.1
_MAX_DISTANCE = 59


def logical_error_rate(p: float, d: int) -> float:
    """Approximate p_L ≈ A * (p / p_th)^((d+1)/2)."""
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("physical error rate p must be finite and in [0, 1]")
    if isinstance(d, bool) or not isinstance(d, int) or d < 3 or d % 2 == 0:
        raise ValueError("code distance d must be an odd integer >= 3")
    return _A * (p / _P_TH) ** ((d + 1) / 2)


def min_distance(p: float, p_L_per_gate: float) -> int:
    """Return the smallest odd d >= 3 meeting the target, or 61 if capped."""
    if (
        isinstance(p_L_per_gate, bool)
        or not isinstance(p_L_per_gate, (int, float))
        or not math.isfinite(p_L_per_gate)
        or not 0 < p_L_per_gate < 1
    ):
        raise ValueError("p_L_per_gate must be finite and strictly between 0 and 1")
    for d in range(3, _MAX_DISTANCE + 1, 2):
        if logical_error_rate(p, d) < p_L_per_gate:
            return d
    return _MAX_DISTANCE + 2


def estimate(
    p_physical: float,
    n_logical: int = 3_000,
    t_gates: int = 3_000_000_000,
    p_total_failure: float = 0.5,
) -> dict:
    """Estimate physical qubits using a simplified surface-code model.

    If no supported distance meets the per-gate failure budget, the result is
    explicitly marked infeasible. Counts then describe the distance-cap
    scenario, not a claim that the target failure probability is achievable.
    """
    if (
        isinstance(p_physical, bool)
        or not isinstance(p_physical, (int, float))
        or not math.isfinite(p_physical)
        or not 0 < p_physical <= 1
    ):
        raise ValueError("p_physical must be finite and in (0, 1]")
    if isinstance(n_logical, bool) or not isinstance(n_logical, int) or n_logical < 1:
        raise ValueError("n_logical must be a positive integer")
    if isinstance(t_gates, bool) or not isinstance(t_gates, int) or t_gates < 1:
        raise ValueError("t_gates must be a positive integer")
    if (
        isinstance(p_total_failure, bool)
        or not isinstance(p_total_failure, (int, float))
        or not math.isfinite(p_total_failure)
        or not 0 < p_total_failure < 1
    ):
        raise ValueError("p_total_failure must be finite and strictly between 0 and 1")

    p_L_per_gate = p_total_failure / t_gates
    d = min_distance(p_physical, p_L_per_gate)
    distance_limit_reached = d > _MAX_DISTANCE
    modeled_d = _MAX_DISTANCE if distance_limit_reached else d
    phys_per_logical = 2 * modeled_d * modeled_d
    total = n_logical * phys_per_logical
    p_L = logical_error_rate(p_physical, modeled_d)

    return {
        "d": modeled_d,
        "p_physical": p_physical,
        "n_logical": n_logical,
        "t_gates": t_gates,
        "p_L_per_gate": p_L_per_gate,
        "p_L_achieved": p_L,
        "phys_per_logical": phys_per_logical,
        "total_physical": total,
        "feasible": not distance_limit_reached and total < 10_000_000,
        "distance_limit_reached": distance_limit_reached,
        "feasibility_note": (
            "Target failure budget was not met at any supported code distance; "
            "resource counts show the distance-cap scenario only."
            if distance_limit_reached
            else "Target failure budget met by the simplified model."
        ),
        "references": {
            "Gidney & Ekera 2019 (arXiv:1905.09749)": 20_000_000,
            "Gidney 2025 (arXiv:2505.15917)": 1_000_000,
            "Heterogeneous arch. 2026 (arXiv:2604.06319)": 100_000,
        },
    }
