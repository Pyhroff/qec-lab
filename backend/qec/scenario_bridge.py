"""Consume Quantum Collapse bridge output and add scoped QEC resource estimates.

Only RSA findings are supported by the current RSA-2048 resource model. ECC/DH/DSA
findings are retained as observed evidence but never coerced into RSA estimates.
All generated values are analytical scenario outputs, not hardware measurements.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .resource import estimate


def build_scenario_report(
    bridge: dict[str, Any],
    *,
    p_physical: float = 0.001,
    n_logical: int = 3000,
    t_gates: int = 3_000_000_000,
    p_total_failure: float = 0.5,
) -> dict[str, Any]:
    """Add an RSA-2048 estimate for supported nodes in a bridge scenario."""
    if not isinstance(bridge, dict) or bridge.get("schema_version") != "1.0":
        raise ValueError("input must be a Quantum Collapse bridge output with schema_version 1.0")
    source = bridge.get("source")
    scenario = bridge.get("modeled_scenario")
    evidence = bridge.get("observed_evidence")
    if not isinstance(source, dict) or not isinstance(scenario, dict) or not isinstance(evidence, dict):
        raise ValueError("input must contain source, observed_evidence, and modeled_scenario objects")
    nodes = scenario.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("modeled_scenario.nodes must be a list")

    rows = []
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("each modeled scenario node must be an object")
        crypto = node.get("crypto")
        if not isinstance(crypto, str):
            raise ValueError("each scenario node must include a crypto label")
        evidence_ref = {
            "node_id": node.get("id"),
            "file": node.get("evidence_file", ""),
            "line": node.get("evidence_line"),
            "algorithm": node.get("evidence_algorithm", crypto),
        }
        if crypto == "RSA":
            model_result = estimate(
                p_physical=p_physical,
                n_logical=n_logical,
                t_gates=t_gates,
                p_total_failure=p_total_failure,
            )
            rows.append({
                **evidence_ref,
                "crypto": crypto,
                "status": "estimated",
                "resource_estimate": model_result,
                "limitation": "Estimate is scoped to RSA-2048 factoring; it does not establish runtime reachability or an attack timeline.",
            })
        else:
            rows.append({
                **evidence_ref,
                "crypto": crypto,
                "status": "unsupported_crypto_model",
                "resource_estimate": None,
                "limitation": "Current QEC resource model is scoped to RSA-2048 factoring; no RSA estimate is assigned to this finding.",
            })

    supported = sum(row["status"] == "estimated" for row in rows)
    return {
        "schema_version": "1.0",
        "experiment": "qec-lab-quantum-collapse-scenario-bridge",
        "measurement_type": "conditional_analytical_resource_estimate_not_hardware_measurement",
        "input": {
            "format": source.get("format"),
            "format_version": source.get("version"),
            "source_tool": source.get("tool"),
            "bridge_schema_version": bridge.get("schema_version"),
            "observed_finding_count": evidence.get("finding_count"),
        },
        "resource_model": {
            "name": "simplified_surface_code_rsa2048_estimator",
            "scope": "RSA-2048 factoring only",
            "parameters": {
                "p_physical": p_physical,
                "n_logical": n_logical,
                "t_gates": t_gates,
                "p_total_failure": p_total_failure,
            },
            "limitations": [
                "analytical approximation, not a hardware measurement or calibrated forecast",
                "omits architecture-specific routing, magic-state factory, and layout overhead",
                "reported distance 61 is a search-cap sentinel, not a validated minimum-distance solution",
                "source-code findings do not prove runtime reachability or deployed use",
                "ECC, DH, and DSA findings are preserved but unsupported by this RSA-2048 model",
            ],
        },
        "summary": {
            "scenario_node_count": len(nodes),
            "supported_rsa_node_count": supported,
            "unsupported_node_count": len(rows) - supported,
            "edge_count": scenario.get("edge_count", 0),
        },
        "findings": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path, help="Quantum Collapse SARIF bridge output JSON")
    parser.add_argument("--p-physical", type=float, default=0.001)
    parser.add_argument("--n-logical", type=int, default=3000)
    parser.add_argument("--t-gates", type=int, default=3_000_000_000)
    parser.add_argument("--p-total-failure", type=float, default=0.5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        bridge = json.loads(args.scenario.read_text(encoding="utf-8"))
        report = build_scenario_report(
            bridge,
            p_physical=args.p_physical,
            n_logical=args.n_logical,
            t_gates=args.t_gates,
            p_total_failure=args.p_total_failure,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
