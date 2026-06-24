"""
Lattice surgery simulation: X-type merge between two surface code patches.

An X-merge (rough-boundary merge) connects the right X-boundary of patch L
with the left X-boundary of patch R to measure the joint logical X_L ⊗ X_R
observable — the parity of their logical X operators.

Layout (visual coordinates):
  L qubits at (r, c),     r,c ∈ [0, d-1]
  R qubits at (r, c+d+1), r,c ∈ [0, d-1]   (gap of 1 col for clarity)
  Seam:  weight-4 stabs at visual col d, bridging L's col d-1 to R's col 0.

Correctness check: at p=0, both patches in |+>_L → X_L⊗X_R = +1 on every shot.

CNOT via lattice surgery (not implemented here) requires three patches:
  ZZ-merge(A, ancilla) → XX-merge(ancilla, B) → measure ancilla Z → Pauli corrections.
  Reference: Horsman et al. 2012, arXiv:1111.4022
"""

import numpy as np
import pymatching

from .lattice import make_lattice


def make_merged_geometry(d: int) -> dict:
    """
    Return geometry for two d×d patches in X-merge configuration.

    Returns
    -------
    dict:
      d
      data       : all 2d² data qubits  {id, row, col (visual), patch}
      stabs_L    : L stabilizers (right X boundary removed)
      stabs_R    : R stabilizers (left X boundary removed; visual col offset by d+1)
      seam_stabs : weight-4 seam stabilizers created by the merge
      logical_x_L, logical_x_R : qubit IDs for logical X operators
      logical_z_L, logical_z_R : qubit IDs for logical Z operators
    """
    lat = make_lattice(d)

    def rename_L(qid: str) -> str:
        return "L_" + qid[2:]    # "q_r_c"  →  "L_r_c"

    def rename_R(qid: str) -> str:
        return "R_" + qid[2:]    # "q_r_c"  →  "R_r_c"

    # Data qubits — L keeps visual col, R shifts by d+1
    data_L = [
        {"id": rename_L(q["id"]), "row": q["row"], "col": q["col"], "patch": "L"}
        for q in lat["data"]
    ]
    data_R = [
        {"id": rename_R(q["id"]), "row": q["row"], "col": q["col"] + d + 1, "patch": "R"}
        for q in lat["data"]
    ]

    # Left-patch stabilizers — drop the right X boundary (visual col ≈ d-0.5)
    stabs_L = []
    for s in lat["stabs"]:
        if s["boundary"] and s["type"] == "X" and abs(s["col"] - (d - 0.5)) < 0.1:
            continue          # removed — merged into seam stabs
        stabs_L.append({
            "id":       "L_" + s["id"],
            "type":     s["type"],
            "row":      s["row"],
            "col":      s["col"],
            "qubits":   [rename_L(q) for q in s["qubits"]],
            "weight":   s["weight"],
            "boundary": s["boundary"],
            "seam":     False,
            "patch":    "L",
        })

    # Right-patch stabilizers — drop the left X boundary (col ≈ -0.5), offset visually
    stabs_R = []
    for s in lat["stabs"]:
        if s["boundary"] and s["type"] == "X" and abs(s["col"] - (-0.5)) < 0.1:
            continue          # removed — merged into seam stabs
        stabs_R.append({
            "id":       "R_" + s["id"],
            "type":     s["type"],
            "row":      s["row"],
            "col":      s["col"] + d + 1,   # visual shift
            "qubits":   [rename_R(q) for q in s["qubits"]],
            "weight":   s["weight"],
            "boundary": s["boundary"],
            "seam":     False,
            "patch":    "R",
        })

    # Seam stabs — weight-4 faces at visual col d, row r+0.5
    # Checkerboard: type X if (r+d-1)%2==0, else Z
    seam_stabs = []
    for r in range(d - 1):
        stype = "X" if (r + d - 1) % 2 == 0 else "Z"
        seam_stabs.append({
            "id":       f"seam_{r}",
            "type":     stype,
            "row":      r + 0.5,
            "col":      d,            # visual midpoint between L col d-1 and R col d+1
            "qubits":   [f"L_{r}_{d-1}", f"L_{r+1}_{d-1}",
                         f"R_{r}_0",   f"R_{r+1}_0"],
            "weight":   4,
            "boundary": False,
            "seam":     True,
            "patch":    "seam",
        })

    return {
        "d":           d,
        "data":        data_L + data_R,
        "stabs_L":     stabs_L,
        "stabs_R":     stabs_R,
        "seam_stabs":  seam_stabs,
        "logical_x_L": [f"L_0_{c}" for c in range(d)],
        "logical_x_R": [f"R_0_{c}" for c in range(d)],
        "logical_z_L": [f"L_{r}_0" for r in range(d)],
        "logical_z_R": [f"R_{r}_0" for r in range(d)],
    }


def run_merge_shot(d: int, p: float, seed: int | None = None) -> dict:
    """
    Simulate one X-merge shot.

    Both patches start in |+>_L (X_L = X_R = +1).
    Z errors anticommute with X-type stabs and can flip logical X.

    Returns per-phase state for animation:
      errors_z        : qubit IDs with Z errors
      syndromes       : {stab_id: 1} for triggered X-type stabs (incl. seam)
      correction_z    : qubit IDs where Z correction is applied
      x_L_error       : bool — X_L was flipped
      x_R_error       : bool — X_R was flipped
      joint_preserved : bool — X_L⊗X_R unchanged  (at p=0, always True)
    """
    rng = np.random.default_rng(seed)
    geo = make_merged_geometry(d)

    all_data  = geo["data"]
    all_stabs = geo["stabs_L"] + geo["stabs_R"] + geo["seam_stabs"]

    # Z errors on all 2d² qubits (code-capacity)
    errors_z = {q["id"] for q in all_data if rng.random() < p}

    # X-type syndromes (Z errors anticommute with X-type stabs)
    syndromes: dict[str, int] = {}
    for stab in all_stabs:
        if stab["type"] != "X":
            continue
        if sum(1 for q in stab["qubits"] if q in errors_z) % 2:
            syndromes[stab["id"]] = 1

    # MWPM decode on merged X-stab graph
    correction_z = _decode_merged(geo, syndromes)

    # Logical X error ⟺ net Z has odd overlap with logical Z operator
    net_z  = errors_z.symmetric_difference(correction_z)
    x_L_err = bool(sum(1 for q in geo["logical_z_L"] if q in net_z) % 2)
    x_R_err = bool(sum(1 for q in geo["logical_z_R"] if q in net_z) % 2)

    return {
        "d":             d,
        "p":             p,
        "errors_z":      sorted(errors_z),
        "syndromes":     syndromes,
        "correction_z":  sorted(correction_z),
        "x_L_error":     x_L_err,
        "x_R_error":     x_R_err,
        "joint_preserved": not (x_L_err or x_R_err),
    }


def _decode_merged(geo: dict, syndromes: dict) -> set:
    """MWPM decode for the merged X-stab graph (corrects Z errors)."""
    all_stabs  = geo["stabs_L"] + geo["stabs_R"] + geo["seam_stabs"]
    x_stabs    = [s for s in all_stabs if s["type"] == "X"]
    bnd_stabs  = [s for s in x_stabs if s.get("boundary", False)]

    qubit_ids  = [q["id"] for q in geo["data"]]
    qidx       = {q: i for i, q in enumerate(qubit_ids)}
    n_q        = len(qubit_ids)
    n_s        = len(x_stabs)
    n_bnd      = len(bnd_stabs)
    bnd_virt   = {s["id"]: n_q + i for i, s in enumerate(bnd_stabs)}

    # Each boundary stab gets its own virtual node so each column has ≤2 ones.
    # (Sharing one virtual node fails for d≥5 where 4 boundary X-stabs would give
    # 4 ones in that column, violating PyMatching's graph-edge constraint.)
    H = np.zeros((n_s, n_q + n_bnd), dtype=np.uint8)
    for si, stab in enumerate(x_stabs):
        for q in stab["qubits"]:
            H[si, qidx[q]] = 1
        if stab.get("boundary", False):
            H[si, bnd_virt[stab["id"]]] = 1

    m        = pymatching.Matching(H)
    synd_vec = np.array([syndromes.get(s["id"], 0) for s in x_stabs], dtype=np.uint8)

    if not synd_vec.any():
        return set()

    correction = m.decode(synd_vec)
    return {qubit_ids[i] for i in range(n_q) if correction[i]}
