"""Reproducible parameter sweep for the simplified RSA-2048 resource model.

This is a deterministic analytical scenario sweep, not a hardware benchmark.
A reported distance of 61 is the model's cap sentinel (search tested d=3..59);
rows at that sentinel must not be read as a validated minimum-distance solution.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .resource import estimate

DEFAULT_P_VALUES = (0.0005, 0.001, 0.002, 0.005, 0.007, 0.009)
DEFAULT_T_GATES = (100_000_000, 1_000_000_000, 3_000_000_000)
THRESHOLD = 0.01


def build_sweep_report(
    *,
    p_values: Iterable[float] = DEFAULT_P_VALUES,
    t_gate_counts: Iterable[int] = DEFAULT_T_GATES,
    n_logical: int = 3000,
    p_total_failure: float = 0.5,
    code_revision: str | None = None,
) -> dict:
    physical_rates = list(p_values)
    gate_counts = list(t_gate_counts)
    if not physical_rates or not gate_counts:
        raise ValueError("p_values and t_gate_counts must not be empty")
    for p in physical_rates:
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p < THRESHOLD:
            raise ValueError(f"each physical error rate must be in [0, {THRESHOLD})")
    for gates in gate_counts:
        if isinstance(gates, bool) or not isinstance(gates, int) or gates < 1:
            raise ValueError("each T-gate count must be a positive integer")

    started = time.perf_counter()
    rows = []
    for p in physical_rates:
        for gates in gate_counts:
            result = estimate(
                p_physical=p,
                n_logical=n_logical,
                t_gates=gates,
                p_total_failure=p_total_failure,
            )
            cap_exceeded = result["d"] == 61
            rows.append({
                "p_physical": p,
                "n_logical": n_logical,
                "t_gates": gates,
                "p_total_failure": p_total_failure,
                "reported_distance": result["d"],
                "distance_cap_exceeded": cap_exceeded,
                "target_met_within_search_cap": not cap_exceeded,
                "p_L_per_gate_target": result["p_L_per_gate"],
                "p_L_at_reported_distance": result["p_L_achieved"],
                "physical_qubits_at_reported_distance": result["total_physical"],
                "below_10m_qubit_threshold_at_reported_distance": result["feasible"],
            })

    return {
        "schema_version": "1.0",
        "experiment": "qec-lab-rsa2048-resource-parameter-sweep",
        "measurement_type": "analytical_model_sweep_not_hardware_measurement",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_revision": code_revision or os.getenv("GITHUB_SHA", "unknown"),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "model": {
            "name": "simplified_surface_code_logical_error_approximation",
            "logical_error_rate": "A * (p_physical / p_threshold) ** ((distance + 1) / 2)",
            "p_threshold": THRESHOLD,
            "prefactor_A": 0.1,
            "searched_odd_distances": list(range(3, 60, 2)),
            "distance_cap_sentinel": 61,
            "total_failure_budget_interpretation": "per-T-gate target = p_total_failure / t_gates",
            "limitations": [
                "not calibrated against a hardware backend",
                "omits architecture-specific routing, magic-state factory, and layout overhead",
                "distance 61 means no solution was found within tested distances 3..59",
                "qubit counts at the cap sentinel are reference values, not validated minimum requirements",
            ],
        },
        "parameters": {
            "physical_error_rates": physical_rates,
            "t_gate_counts": gate_counts,
            "n_logical": n_logical,
            "p_total_failure": p_total_failure,
        },
        "result_count": len(rows),
        "runtime_seconds": round(time.perf_counter() - started, 6),
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p-values", default=",".join(map(str, DEFAULT_P_VALUES)))
    parser.add_argument("--t-gates", default=",".join(map(str, DEFAULT_T_GATES)))
    parser.add_argument("--n-logical", type=int, default=3000)
    parser.add_argument("--p-total-failure", type=float, default=0.5)
    parser.add_argument("--revision", default=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = build_sweep_report(
            p_values=[float(value) for value in args.p_values.split(",") if value.strip()],
            t_gate_counts=[int(value) for value in args.t_gates.split(",") if value.strip()],
            n_logical=args.n_logical,
            p_total_failure=args.p_total_failure,
            code_revision=args.revision,
        )
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
