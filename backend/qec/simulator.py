"""
Surface code simulation engine.

Two modes:
  1. run_shot()   — code-capacity depolarizing noise, standalone PyMatching decoder.
                    Returns full state for D3 animation: errors, syndromes, correction, match pairs.
  2. run_threshold() — circuit-level noise via Stim + PyMatching.
                       Returns {d, p, logical_error_rate} table for the threshold curve.

Noise model for run_shot (code-capacity):
  Each data qubit independently suffers:
    X error with probability p
    Z error with probability p
  These are independent channels, not depolarizing — simpler to visualize clearly.

Noise model for run_threshold (circuit-level via Stim):
  after_clifford_depolarization=p applied throughout the syndrome extraction circuit.
  This is the standard model used in surface code threshold papers.
  Threshold emerges near p ~ 0.5-1%.
"""

import numpy as np
import pymatching
import stim

from .lattice import make_lattice


# ---------------------------------------------------------------------------
# Single-shot simulation (code-capacity, for visualization)
# ---------------------------------------------------------------------------

def _build_matching(stabs: list, d: int, error_type: str):
    """
    Build a PyMatching object for decoding one error type.
    error_type: 'X' -> use Z-stabilizers | 'Z' -> use X-stabilizers
    """
    detect_type = "Z" if error_type == "X" else "X"
    relevant = [s for s in stabs if s["type"] == detect_type]

    qubit_ids = [f"q_{r}_{c}" for r in range(d) for c in range(d)]
    qidx = {q: i for i, q in enumerate(qubit_ids)}
    n_q = d * d
    n_s = len(relevant)

    # H[si, qi] = 1 if qubit qi is in stabilizer si
    # Extra column = virtual boundary qubit
    H = np.zeros((n_s, n_q + 1), dtype=np.uint8)
    for si, stab in enumerate(relevant):
        for q in stab["qubits"]:
            H[si, qidx[q]] = 1
        if stab["boundary"]:
            H[si, n_q] = 1   # connect boundary stabs to virtual node

    return pymatching.Matching(H), relevant, qubit_ids


def run_shot(d: int, p: float, seed: int | None = None) -> dict:
    """
    Simulate one syndrome-extraction round with code-capacity noise.

    Returns
    -------
    dict:
      d, p
      errors_x        : list of qubit ids with X errors
      errors_z        : list of qubit ids with Z errors
      syndromes       : dict {stab_id: 1} for triggered stabilizers only
      correction_x    : list of qubit ids where X correction is applied
      correction_z    : list of qubit ids where Z correction is applied
      logical_x_error : bool — X correction failed to remove logical X error
      logical_z_error : bool — Z correction failed to remove logical Z error
      logical_error   : bool — either type
    """
    rng = np.random.default_rng(seed)
    lat = make_lattice(d)
    data = lat["data"]
    stabs = lat["stabs"]

    # --- inject errors ---
    errors_x = {q["id"] for q in data if rng.random() < p}
    errors_z = {q["id"] for q in data if rng.random() < p}

    # --- compute syndromes ---
    syndromes: dict[str, int] = {}
    for stab in stabs:
        if stab["type"] == "Z":   # Z-stab detects X errors
            parity = sum(1 for q in stab["qubits"] if q in errors_x) % 2
        else:                     # X-stab detects Z errors
            parity = sum(1 for q in stab["qubits"] if q in errors_z) % 2
        if parity:
            syndromes[stab["id"]] = 1

    # --- decode X errors (via Z-stabilizer syndromes) ---
    correction_x = _decode(stabs, d, "X", syndromes)

    # --- decode Z errors (via X-stabilizer syndromes) ---
    correction_z = _decode(stabs, d, "Z", syndromes)

    # --- check logical outcomes ---
    logical_x = _logical_error(errors_x, correction_x, lat["logical_x"])
    logical_z = _logical_error(errors_z, correction_z, lat["logical_z"])

    return {
        "d": d,
        "p": p,
        "errors_x": sorted(errors_x),
        "errors_z": sorted(errors_z),
        "syndromes": syndromes,
        "correction_x": sorted(correction_x),
        "correction_z": sorted(correction_z),
        "logical_x_error": logical_x,
        "logical_z_error": logical_z,
        "logical_error": logical_x or logical_z,
    }


def _decode(stabs: list, d: int, error_type: str, syndromes: dict) -> set:
    """Run MWPM and return set of qubit ids where correction should be applied."""
    detect_type = "Z" if error_type == "X" else "X"
    relevant = [s for s in stabs if s["type"] == detect_type]

    if not relevant:
        return set()

    m, relevant, qubit_ids = _build_matching(stabs, d, error_type)

    syndrome_vec = np.array(
        [syndromes.get(s["id"], 0) for s in relevant], dtype=np.uint8
    )

    if not syndrome_vec.any():
        return set()

    correction = m.decode(syndrome_vec)
    # Last entry is virtual boundary qubit — exclude
    return {qubit_ids[i] for i in range(d * d) if correction[i]}


def _logical_error(errors: set, correction: set, logical_op: list) -> bool:
    """Return True if net error has odd overlap with the logical operator."""
    net = errors.symmetric_difference(correction)
    return sum(1 for q in logical_op if q in net) % 2 == 1


# ---------------------------------------------------------------------------
# Threshold curve (circuit-level noise via Stim)
# ---------------------------------------------------------------------------

_THRESHOLD_P_VALUES = [
    0.001, 0.002, 0.003, 0.005, 0.007,
    0.009, 0.011, 0.013, 0.015, 0.018,
    0.022, 0.027, 0.033, 0.040,
]

_THRESHOLD_D_VALUES = [3, 5, 7]


def run_threshold(shots: int = 600, d_values: list | None = None) -> list:
    """
    Sweep physical error rates for multiple code distances.
    Uses Stim circuit-level noise + PyMatching MWPM decoder.

    Returns list of {d, p, logical_error_rate}.
    """
    if d_values is None:
        d_values = _THRESHOLD_D_VALUES

    results = []
    for d in d_values:
        for p in _THRESHOLD_P_VALUES:
            circuit = stim.Circuit.generated(
                "surface_code:rotated_memory_z",
                distance=d,
                rounds=d,
                after_clifford_depolarization=p,
            )
            dem = circuit.detector_error_model(decompose_errors=True)
            matcher = pymatching.Matching.from_detector_error_model(dem)
            sampler = circuit.compile_detector_sampler()
            # append_observables=True appends logical observable bits after
            # detector bits — required to compare predictions vs ground truth.
            data = sampler.sample(shots, append_observables=True)
            n_det = circuit.num_detectors
            preds = matcher.decode_batch(data[:, :n_det])
            n_errors = int(np.sum(preds != data[:, n_det:]))
            results.append({
                "d": d,
                "p": p,
                "logical_error_rate": n_errors / shots,
            })

    return results
