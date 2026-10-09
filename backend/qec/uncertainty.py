"""Seeded Monte Carlo scenario sweep for the simplified resource estimator.

The output distribution reflects user-chosen input ranges and sampling policy.
It is not an empirical confidence interval or a forecast of quantum hardware.
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Any

from .resource import estimate


def _nearest_rank(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[min(index, len(ordered) - 1)]


def _distribution(values: list[int | float]) -> dict[str, int | float | None]:
    numeric = [float(value) for value in values]
    return {
        "count": len(numeric),
        "mean": statistics.fmean(numeric),
        "sample_stddev": statistics.stdev(numeric) if len(numeric) > 1 else None,
        "p05": _nearest_rank(numeric, 0.05),
        "p50": _nearest_rank(numeric, 0.50),
        "p95": _nearest_rank(numeric, 0.95),
        "min": min(numeric),
        "max": max(numeric),
    }


def monte_carlo_resource_scenarios(
    *,
    samples: int = 1000,
    seed: int = 20261010,
    p_min: float = 0.0005,
    p_max: float = 0.005,
    n_logical_min: int = 1000,
    n_logical_max: int = 5000,
    t_gates_min: int = 1_000_000_000,
    t_gates_max: int = 5_000_000_000,
    p_total_failure_min: float = 0.1,
    p_total_failure_max: float = 0.9,
) -> dict[str, Any]:
    """Sample input assumptions uniformly and summarize modeled resource outputs."""
    if isinstance(samples, bool) or not isinstance(samples, int) or not 1 <= samples <= 20_000:
        raise ValueError("samples must be an integer in [1, 20000]")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    for name, value in (("p_min", p_min), ("p_max", p_max)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if not 0 <= value < 0.01:
            raise ValueError(f"{name} must be in [0, 0.01), the estimator's below-threshold domain")
    if p_min > p_max:
        raise ValueError("p_min must be <= p_max")

    for name, value in (("n_logical_min", n_logical_min), ("n_logical_max", n_logical_max),
                        ("t_gates_min", t_gates_min), ("t_gates_max", t_gates_max)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if n_logical_min > n_logical_max:
        raise ValueError("n_logical_min must be <= n_logical_max")
    if t_gates_min > t_gates_max:
        raise ValueError("t_gates_min must be <= t_gates_max")

    for name, value in (("p_total_failure_min", p_total_failure_min),
                        ("p_total_failure_max", p_total_failure_max)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if not 0 < value <= 1:
            raise ValueError(f"{name} must be in (0, 1]")
    if p_total_failure_min > p_total_failure_max:
        raise ValueError("p_total_failure_min must be <= p_total_failure_max")

    rng = random.Random(seed)
    rows = []
    for _ in range(samples):
        p_physical = rng.uniform(p_min, p_max)
        n_logical = rng.randint(n_logical_min, n_logical_max)
        t_gates = rng.randint(t_gates_min, t_gates_max)
        p_total_failure = rng.uniform(p_total_failure_min, p_total_failure_max)
        result = estimate(
            p_physical=p_physical,
            n_logical=n_logical,
            t_gates=t_gates,
            p_total_failure=p_total_failure,
        )
        rows.append({
            "p_physical": p_physical,
            "n_logical": n_logical,
            "t_gates": t_gates,
            "p_total_failure": p_total_failure,
            "total_physical": result["total_physical"],
            "reported_distance": result["d"],
            "distance_cap_exceeded": result["distance_cap_exceeded"],
            "model_domain_valid": result["model_domain_valid"],
            "feasible": result["feasible"],
        })

    return {
        "schema_version": "1.0",
        "experiment": "qec-lab-resource-estimator-monte-carlo-scenarios",
        "measurement_type": "monte_carlo_scenario_sweep_not_empirical_uncertainty",
        "sample_count": samples,
        "seed": seed,
        "sampling_policy": {
            "p_physical": {"distribution": "uniform", "min": p_min, "max": p_max},
            "n_logical": {"distribution": "discrete_uniform", "min": n_logical_min, "max": n_logical_max},
            "t_gates": {"distribution": "discrete_uniform", "min": t_gates_min, "max": t_gates_max},
            "p_total_failure": {"distribution": "uniform", "min": p_total_failure_min, "max": p_total_failure_max},
        },
        "interpretation": (
            "Quantiles summarize outputs under the specified input ranges and uniform sampling policy. "
            "They are not calibrated hardware probabilities or empirical confidence intervals."
        ),
        "results": {
            "total_physical": _distribution([r["total_physical"] for r in rows]),
            "reported_distance": _distribution([r["reported_distance"] for r in rows]),
        },
        "rates": {
            "distance_cap_exceeded": sum(r["distance_cap_exceeded"] for r in rows) / samples,
            "model_domain_valid": sum(r["model_domain_valid"] for r in rows) / samples,
            "feasible": sum(r["feasible"] for r in rows) / samples,
        },
    }
