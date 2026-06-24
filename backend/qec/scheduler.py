"""
Fault-tolerant gate scheduler for surface code logical qubits.

Maps gate sequences to lattice surgery primitives and computes physical resources.

Gate → lattice surgery primitives (Horsman et al. 2012, arXiv:1111.4022):
  CNOT       : ZZ-merge → XX-merge → measure-ancilla  (3 logical cycles, 1 ancilla patch)
  H          : transversal                              (1 logical cycle, no ancilla)
  T / T†     : magic-state injection via XX-merge       (3 logical cycles, 1 magic-state patch)
               [Bravyi & Kitaev 2005, arXiv:quant-ph/0403025]
  Pauli X/Z  : Pauli frame update (0 cycles, free)

Physical resource formula (rotated surface code):
  physical qubits per patch = 2d²  [consistent with resource.py]
  logical cycles per CNOT   = 3
  logical cycles per T gate = 3 (assumes pre-distilled magic state)
  logical cycles per H gate = 1
  QEC rounds per logical cycle = d
  cycle time (superconducting) ≈ 1 µs  [Fowler et al. 2012, arXiv:1208.0928]

Toffoli decomposition: T-count-7, CNOT-count-6, H-count-2
  Reference: Nielsen & Chuang §4.3; Selinger 2013 (arXiv:1210.0974)
  Gate sequence: H Q2 | CNOT Q1,Q2 | T† Q2 | CNOT Q0,Q2 | T Q2 |
                 CNOT Q1,Q2 | T† Q2 | CNOT Q0,Q2 | T Q1 ‖ T Q2 |
                 H Q2 | CNOT Q0,Q1 | T Q0 ‖ T† Q1 | CNOT Q0,Q1

NOTE: Gantt timings are a schematic illustration of the gate sequence and
parallelism structure. Per-cycle allocation is data-dependency-ordered but
not optimally packed. Resource counts (patches, qubits) are exact for the
assumed serial ancilla reuse model.
"""


def _phys_per_patch(d: int) -> int:
    return 2 * d * d


def _resources(patches: int, depth: int, t_count: int, d: int) -> dict:
    qpc = _phys_per_patch(d)
    physical_cycles = depth * d
    return {
        "t_count":             t_count,
        "logical_depth":       depth,
        "total_patches":       patches,
        "phys_per_patch":      qpc,
        "total_physical":      patches * qpc,
        "physical_cycles":     physical_cycles,
        "runtime_us":          physical_cycles,        # ~1 µs/round, superconducting
        "cycle_time_note":     "~1 µs/round (superconducting, Fowler 2012)",
        "references": [
            "CNOT primitive: Horsman et al. 2012 (arXiv:1111.4022)",
            "T injection: Bravyi & Kitaev 2005 (arXiv:quant-ph/0403025)",
            "Patch size 2d²: rotated surface code (consistent with resource.py)",
        ],
    }


# ── CNOT via lattice surgery ──────────────────────────────────────────────────

def _circuit_cnot(d: int) -> dict:
    ops = [
        # t=0: prepare ancilla
        {"lane": "A  ancilla", "t": 0, "dur": 1, "label": "PREP |0⟩", "cat": "prepare"},
        # t=1: ZZ-merge C and A  (rough-boundary merge — measures Z_C ⊗ Z_A)
        {"lane": "Q0  ctrl",   "t": 1, "dur": 1, "label": "ZZ-merge",  "cat": "merge"},
        {"lane": "A  ancilla", "t": 1, "dur": 1, "label": "ZZ-merge",  "cat": "merge"},
        # t=2: XX-merge A and T  (smooth-boundary merge — measures X_A ⊗ X_T)
        {"lane": "A  ancilla", "t": 2, "dur": 1, "label": "XX-merge",  "cat": "merge"},
        {"lane": "Q1  tgt",    "t": 2, "dur": 1, "label": "XX-merge",  "cat": "merge"},
        # t=3: measure A in Z, apply classical Pauli corrections
        {"lane": "A  ancilla", "t": 3, "dur": 1, "label": "Meas Z",    "cat": "measure"},
        {"lane": "Q0  ctrl",   "t": 3, "dur": 1, "label": "? Z-corr",  "cat": "correct"},
        {"lane": "Q1  tgt",    "t": 3, "dur": 1, "label": "? X-corr",  "cat": "correct"},
    ]
    return {
        "circuit":     "cnot",
        "title":       "CNOT Gate",
        "subtitle":    "X-merge + Z-merge via rough/smooth boundary lattice surgery",
        "reference":   "Horsman et al. 2012, arXiv:1111.4022",
        "lanes":       ["Q0  ctrl", "Q1  tgt", "A  ancilla"],
        "depth":       4,
        "ops":         ops,
        "resources":   _resources(patches=3, depth=4, t_count=0, d=d),
    }


# ── T gate via magic state injection ─────────────────────────────────────────

def _circuit_t_gate(d: int) -> dict:
    ops = [
        # t=0-1: distill magic state |T⟩ = T|+⟩ in factory patch
        {"lane": "M  factory",  "t": 0, "dur": 2, "label": "distill |T⟩", "cat": "t_distill"},
        # t=2: XX-merge M and Q (injection — teleports T gate onto Q)
        {"lane": "M  factory",  "t": 2, "dur": 1, "label": "XX-merge",     "cat": "merge"},
        {"lane": "Q0  target",  "t": 2, "dur": 1, "label": "XX-merge",     "cat": "merge"},
        # t=3: measure M in Z; if outcome = 1 → apply S correction to Q
        {"lane": "M  factory",  "t": 3, "dur": 1, "label": "Meas Z",       "cat": "measure"},
        {"lane": "Q0  target",  "t": 3, "dur": 1, "label": "? S-corr",     "cat": "correct"},
    ]
    return {
        "circuit":     "t_gate",
        "title":       "T Gate (magic state injection)",
        "subtitle":    "Pre-distilled |T⟩ teleported onto logical qubit via XX-merge",
        "reference":   "Bravyi & Kitaev 2005, arXiv:quant-ph/0403025",
        "lanes":       ["Q0  target", "M  factory"],
        "depth":       4,
        "ops":         ops,
        "resources":   _resources(patches=2, depth=4, t_count=1, d=d),
    }


# ── Bell pair preparation (H + CNOT) ─────────────────────────────────────────

def _circuit_bell(d: int) -> dict:
    ops = [
        # t=0: H on Q0, prepare ancilla
        {"lane": "Q0",          "t": 0, "dur": 1, "label": "H",          "cat": "clifford"},
        {"lane": "A  ancilla",  "t": 0, "dur": 1, "label": "PREP |0⟩",  "cat": "prepare"},
        # t=1-3: CNOT(Q0 → Q1)
        {"lane": "Q0",          "t": 1, "dur": 1, "label": "ZZ-merge",  "cat": "merge"},
        {"lane": "A  ancilla",  "t": 1, "dur": 1, "label": "ZZ-merge",  "cat": "merge"},
        {"lane": "A  ancilla",  "t": 2, "dur": 1, "label": "XX-merge",  "cat": "merge"},
        {"lane": "Q1",          "t": 2, "dur": 1, "label": "XX-merge",  "cat": "merge"},
        {"lane": "A  ancilla",  "t": 3, "dur": 1, "label": "Meas Z",    "cat": "measure"},
        {"lane": "Q0",          "t": 3, "dur": 1, "label": "? Z-corr",  "cat": "correct"},
        {"lane": "Q1",          "t": 3, "dur": 1, "label": "? X-corr",  "cat": "correct"},
    ]
    return {
        "circuit":     "bell",
        "title":       "Bell Pair Preparation",
        "subtitle":    "H on Q0, then CNOT(Q0 → Q1) via lattice surgery → |Φ⁺⟩",
        "reference":   "Horsman et al. 2012, arXiv:1111.4022",
        "lanes":       ["Q0", "Q1", "A  ancilla"],
        "depth":       4,
        "ops":         ops,
        "resources":   _resources(patches=3, depth=4, t_count=0, d=d),
    }


# ── Toffoli (CCX) — T-count 7, CNOT-count 6, H-count 2 ──────────────────────
#
# Gate sequence (Selinger 2013 / Nielsen & Chuang §4.3):
#   H Q2
#   CNOT Q1→Q2 | T†(Q2) | CNOT Q0→Q2 | T(Q2)
#   CNOT Q1→Q2 | T†(Q2) | CNOT Q0→Q2
#   T(Q1) ‖ T(Q2)   [parallel]
#   H Q2
#   CNOT Q0→Q1 | T(Q0) ‖ T†(Q1)  [parallel] | CNOT Q0→Q1
#
# Scheduling (data-dependency ordered, serial ancilla reuse):
#   Each CNOT = 3 cycles; each T = 3 cycles; each H = 1 cycle
#   Critical path depth = 34 logical cycles

def _circuit_toffoli(d: int) -> dict:
    ops = [
        # t=0: H Q2
        {"lane": "Q2  tgt",       "t":  0, "dur": 1, "label": "H",           "cat": "clifford"},

        # t=1–3: CNOT(Q1→Q2)
        {"lane": "Q1  ctrl2",     "t":  1, "dur": 3, "label": "CNOT ctrl",   "cat": "merge"},
        {"lane": "A_12  ancilla", "t":  1, "dur": 3, "label": "ZZ→XX→Meas",  "cat": "merge"},
        {"lane": "Q2  tgt",       "t":  1, "dur": 3, "label": "CNOT tgt",    "cat": "merge"},

        # t=4–6: T†(Q2)
        {"lane": "M2  factory",   "t":  4, "dur": 3, "label": "T† inject",   "cat": "t_inject"},
        {"lane": "Q2  tgt",       "t":  4, "dur": 3, "label": "T†",          "cat": "t_inject"},

        # t=7–9: CNOT(Q0→Q2)
        {"lane": "Q0  ctrl1",     "t":  7, "dur": 3, "label": "CNOT ctrl",   "cat": "merge"},
        {"lane": "A_02  ancilla", "t":  7, "dur": 3, "label": "ZZ→XX→Meas",  "cat": "merge"},
        {"lane": "Q2  tgt",       "t":  7, "dur": 3, "label": "CNOT tgt",    "cat": "merge"},

        # t=10–12: T(Q2)
        {"lane": "M2  factory",   "t": 10, "dur": 3, "label": "T inject",    "cat": "t_inject"},
        {"lane": "Q2  tgt",       "t": 10, "dur": 3, "label": "T",           "cat": "t_inject"},

        # t=13–15: CNOT(Q1→Q2)
        {"lane": "Q1  ctrl2",     "t": 13, "dur": 3, "label": "CNOT ctrl",   "cat": "merge"},
        {"lane": "A_12  ancilla", "t": 13, "dur": 3, "label": "ZZ→XX→Meas",  "cat": "merge"},
        {"lane": "Q2  tgt",       "t": 13, "dur": 3, "label": "CNOT tgt",    "cat": "merge"},

        # t=16–18: T†(Q2)
        {"lane": "M2  factory",   "t": 16, "dur": 3, "label": "T† inject",   "cat": "t_inject"},
        {"lane": "Q2  tgt",       "t": 16, "dur": 3, "label": "T†",          "cat": "t_inject"},

        # t=19–21: CNOT(Q0→Q2)
        {"lane": "Q0  ctrl1",     "t": 19, "dur": 3, "label": "CNOT ctrl",   "cat": "merge"},
        {"lane": "A_02  ancilla", "t": 19, "dur": 3, "label": "ZZ→XX→Meas",  "cat": "merge"},
        {"lane": "Q2  tgt",       "t": 19, "dur": 3, "label": "CNOT tgt",    "cat": "merge"},

        # t=22–24: T(Q1) ‖ T(Q2)  [parallel — independent qubits]
        {"lane": "Q1  ctrl2",     "t": 22, "dur": 3, "label": "T  ‖",        "cat": "t_inject"},
        {"lane": "M01 factory",   "t": 22, "dur": 3, "label": "T inject ‖",  "cat": "t_inject"},
        {"lane": "Q2  tgt",       "t": 22, "dur": 3, "label": "T  ‖",        "cat": "t_inject"},
        {"lane": "M2  factory",   "t": 22, "dur": 3, "label": "T inject ‖",  "cat": "t_inject"},

        # t=25: H Q2
        {"lane": "Q2  tgt",       "t": 25, "dur": 1, "label": "H",           "cat": "clifford"},

        # t=25–27: CNOT(Q0→Q1)  [Q1 free@25, Q0 free@22]
        {"lane": "Q0  ctrl1",     "t": 25, "dur": 3, "label": "CNOT ctrl",   "cat": "merge"},
        {"lane": "A_01  ancilla", "t": 25, "dur": 3, "label": "ZZ→XX→Meas",  "cat": "merge"},
        {"lane": "Q1  ctrl2",     "t": 25, "dur": 3, "label": "CNOT tgt",    "cat": "merge"},

        # t=28–30: T(Q0) ‖ T†(Q1)  [parallel]
        {"lane": "Q0  ctrl1",     "t": 28, "dur": 3, "label": "T  ‖",        "cat": "t_inject"},
        {"lane": "Q1  ctrl2",     "t": 28, "dur": 3, "label": "T† ‖",        "cat": "t_inject"},
        {"lane": "M01 factory",   "t": 28, "dur": 3, "label": "T/T† inj ‖",  "cat": "t_inject"},

        # t=31–33: CNOT(Q0→Q1)
        {"lane": "Q0  ctrl1",     "t": 31, "dur": 3, "label": "CNOT ctrl",   "cat": "merge"},
        {"lane": "A_01  ancilla", "t": 31, "dur": 3, "label": "ZZ→XX→Meas",  "cat": "merge"},
        {"lane": "Q1  ctrl2",     "t": 31, "dur": 3, "label": "CNOT tgt",    "cat": "merge"},
    ]

    # Lanes in display order
    lanes = [
        "Q0  ctrl1",
        "Q1  ctrl2",
        "Q2  tgt",
        "A_12  ancilla",
        "A_02  ancilla",
        "A_01  ancilla",
        "M2  factory",
        "M01 factory",
    ]

    # 8 patches: 3 data + 3 CNOT ancilla (serially reused pairs) + 2 magic factories
    return {
        "circuit":     "toffoli",
        "title":       "Toffoli (CCX) Gate",
        "subtitle":    "T-count 7, CNOT-count 6, H-count 2 — Selinger 2013",
        "reference":   "Selinger 2013, arXiv:1210.0974; Horsman et al. 2012, arXiv:1111.4022",
        "lanes":       lanes,
        "depth":       34,
        "ops":         ops,
        "resources":   _resources(patches=8, depth=34, t_count=7, d=d),
    }


# ── Public API ────────────────────────────────────────────────────────────────

_BUILDERS = {
    "cnot":    _circuit_cnot,
    "t_gate":  _circuit_t_gate,
    "bell":    _circuit_bell,
    "toffoli": _circuit_toffoli,
}


def list_circuits() -> list:
    return list(_BUILDERS.keys())


def get_schedule(circuit: str, d: int = 3) -> dict:
    if circuit not in _BUILDERS:
        raise ValueError(f"Unknown circuit '{circuit}'. Available: {list_circuits()}")
    return _BUILDERS[circuit](d)
