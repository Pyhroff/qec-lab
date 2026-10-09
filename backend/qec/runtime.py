"""
Quantum OS runtime — end-to-end pipeline:

  compile_algorithm() → resource estimate → sensitivity sweep → RunReport

The sensitivity sweep is the interview-defense feature: it shows how physical
qubit count changes as p_physical varies from 0.05% to 0.3%, reproducing the
knee of the surface-code overhead curve.

Validation: RunReport.benchmarks compares the estimate against three
published milestones so reviewers can see the model tracks real results.
"""

from dataclasses import dataclass, asdict

from .compiler import compile_algorithm, CompileResult
from .resource import estimate


# ---------------------------------------------------------------------------
# Sensitivity sweep parameters
# ---------------------------------------------------------------------------

_SENSITIVITY_P_VALUES = [
    0.0005, 0.0007, 0.001, 0.0015, 0.002, 0.003, 0.005,
]


# ---------------------------------------------------------------------------
# RunReport
# ---------------------------------------------------------------------------

@dataclass
class RunReport:
    # compile stage
    algorithm:     str
    n_logical:     int
    t_count:       int
    cnot_count:    int
    h_count:       int
    circuit_depth: int
    compile_ref:   str
    compile_notes: str

    # resource estimate (at requested p_physical)
    p_physical:       float
    d:                int
    p_L_per_gate:     float
    p_L_achieved:     float
    phys_per_logical: int
    total_physical:   int
    feasible:         bool
    model_domain_valid: bool
    distance_cap_exceeded: bool
    target_met_within_search_cap: bool
    total_physical_is_cap_reference: bool

    # runtime estimate
    physical_cycles: int    # circuit_depth × d (QEC rounds per logical cycle)
    runtime_us:      float  # physical_cycles × 1µs (superconducting)
    runtime_s:       float

    # benchmarks & validation
    benchmarks:   dict  # {label: qubit_count}
    within_factor: float | None  # total_physical / nearest non-zero benchmark

    # sensitivity sweep: [{p_physical, d, total_physical}]
    sensitivity: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(
    algorithm:     str,
    p_physical:    float = 0.001,
    # custom circuit params (ignored for presets)
    n_logical:     int = 2,
    t_count:       int = 0,
    cnot_count:    int = 0,
    h_count:       int = 0,
    toffoli_count: int = 0,
) -> RunReport:
    """
    Full pipeline: compile → resource estimate → sensitivity sweep.

    Parameters
    ----------
    algorithm   : algorithm id (see compiler.list_algorithms())
    p_physical  : physical gate error rate (e.g. 0.001 = 0.1%)
    """
    compiled: CompileResult = compile_algorithm(
        algorithm, n_logical, t_count, cnot_count, h_count, toffoli_count
    )

    # Use T-count as the gate budget for resource estimation.
    # Bell (zero T-count) → use CNOT count as budget proxy (Clifford-only circuit).
    gate_budget = max(compiled.t_count, compiled.cnot_count, 1)

    res = estimate(
        p_physical      = p_physical,
        n_logical       = compiled.n_logical,
        t_gates         = gate_budget,
        p_total_failure = 0.5,
    )

    physical_cycles = compiled.circuit_depth * res["d"]
    runtime_us      = float(physical_cycles)      # 1 µs / QEC round, superconducting
    runtime_s       = runtime_us / 1_000_000

    # Sensitivity sweep
    sensitivity = []
    for p in _SENSITIVITY_P_VALUES:
        sr = estimate(
            p_physical      = p,
            n_logical       = compiled.n_logical,
            t_gates         = gate_budget,
            p_total_failure = 0.5,
        )
        sensitivity.append({
            "p_physical":    p,
            "d":             sr["d"],
            "total_physical": sr["total_physical"],
            "feasible":      sr["feasible"],
            "model_domain_valid": sr["model_domain_valid"],
            "distance_cap_exceeded": sr["distance_cap_exceeded"],
            "target_met_within_search_cap": sr["target_met_within_search_cap"],
        })

    # Validation factor vs nearest published benchmark
    references = res["references"]  # {label: qubit_count}
    nonzero = [v for v in references.values() if v > 0]
    nearest = min(nonzero, key=lambda v: abs(v - res["total_physical"])) if nonzero else None
    within_factor = (
        round(res["total_physical"] / nearest, 2) if nearest and nearest > 0 else None
    )

    return RunReport(
        algorithm      = compiled.algorithm,
        n_logical      = compiled.n_logical,
        t_count        = compiled.t_count,
        cnot_count     = compiled.cnot_count,
        h_count        = compiled.h_count,
        circuit_depth  = compiled.circuit_depth,
        compile_ref    = compiled.reference,
        compile_notes  = compiled.notes,

        p_physical       = p_physical,
        d                = res["d"],
        p_L_per_gate     = res["p_L_per_gate"],
        p_L_achieved     = res["p_L_achieved"],
        phys_per_logical = res["phys_per_logical"],
        total_physical   = res["total_physical"],
        feasible         = res["feasible"],
        model_domain_valid = res["model_domain_valid"],
        distance_cap_exceeded = res["distance_cap_exceeded"],
        target_met_within_search_cap = res["target_met_within_search_cap"],
        total_physical_is_cap_reference = res["total_physical_is_cap_reference"],

        physical_cycles = physical_cycles,
        runtime_us      = runtime_us,
        runtime_s       = runtime_s,

        benchmarks    = references,
        within_factor = within_factor,
        sensitivity   = sensitivity,
    )
