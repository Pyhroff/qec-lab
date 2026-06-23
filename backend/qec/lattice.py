"""
Rotated surface code lattice generator.

Convention:
  - Data qubits at integer grid positions (row, col), row/col in [0, d-1]
  - Interior stabilizer faces at half-integer positions (row+0.5, col+0.5)
  - Boundary (weight-2) faces at positions outside the grid:
      Z-type on top/bottom, X-type on left/right

Face checkerboard rule (interior):
  (row+col) % 2 == 0  ->  X-type stabilizer
  (row+col) % 2 == 1  ->  Z-type stabilizer

Logical operators:
  Logical X-bar = X on any horizontal row  (row 0)
  Logical Z-bar = Z on any vertical column (col 0)
"""


def make_lattice(d: int) -> dict:
    """
    Return the full lattice description for a distance-d rotated surface code.

    Returns
    -------
    dict with keys:
      d          : int
      data       : list of data-qubit dicts  {id, row, col}
      stabs      : list of stabilizer dicts  {id, type, row, col, qubits, weight}
      logical_x  : list of qubit ids forming the logical X operator (row 0)
      logical_z  : list of qubit ids forming the logical Z operator (col 0)
    """
    data = []
    for r in range(d):
        for c in range(d):
            data.append({"id": f"q_{r}_{c}", "row": r, "col": c})

    stabs = []
    sid = 0

    # --- interior faces ---
    for r in range(d - 1):
        for c in range(d - 1):
            stype = "X" if (r + c) % 2 == 0 else "Z"
            stabs.append({
                "id": f"s_{sid}",
                "type": stype,
                "row": r + 0.5,
                "col": c + 0.5,
                "qubits": [f"q_{r}_{c}", f"q_{r}_{c+1}",
                           f"q_{r+1}_{c}", f"q_{r+1}_{c+1}"],
                "weight": 4,
                "boundary": False,
            })
            sid += 1

    # --- boundary faces ---

    # Top Z-type (row = -0.5), even cols
    for c in range(0, d - 1, 2):
        stabs.append({
            "id": f"s_{sid}",
            "type": "Z",
            "row": -0.5,
            "col": c + 0.5,
            "qubits": [f"q_0_{c}", f"q_0_{c+1}"],
            "weight": 2,
            "boundary": True,
        })
        sid += 1

    # Bottom Z-type (row = d-0.5), odd cols
    for c in range(1, d - 1, 2):
        stabs.append({
            "id": f"s_{sid}",
            "type": "Z",
            "row": d - 0.5,
            "col": c + 0.5,
            "qubits": [f"q_{d-1}_{c}", f"q_{d-1}_{c+1}"],
            "weight": 2,
            "boundary": True,
        })
        sid += 1

    # Left X-type (col = -0.5), odd rows
    for r in range(1, d - 1, 2):
        stabs.append({
            "id": f"s_{sid}",
            "type": "X",
            "row": r + 0.5,
            "col": -0.5,
            "qubits": [f"q_{r}_0", f"q_{r+1}_0"],
            "weight": 2,
            "boundary": True,
        })
        sid += 1

    # Right X-type (col = d-0.5), even rows
    for r in range(0, d - 1, 2):
        stabs.append({
            "id": f"s_{sid}",
            "type": "X",
            "row": r + 0.5,
            "col": d - 0.5,
            "qubits": [f"q_{r}_{d-1}", f"q_{r+1}_{d-1}"],
            "weight": 2,
            "boundary": True,
        })
        sid += 1

    logical_x = [f"q_0_{c}" for c in range(d)]   # top row
    logical_z = [f"q_{r}_0" for r in range(d)]   # left column

    return {
        "d": d,
        "data": data,
        "stabs": stabs,
        "logical_x": logical_x,
        "logical_z": logical_z,
        "n_data": len(data),
        "n_stabs": len(stabs),
    }


def verify_counts(d: int) -> bool:
    lat = make_lattice(d)
    expected_stabs = d * d - 1
    return len(lat["stabs"]) == expected_stabs
