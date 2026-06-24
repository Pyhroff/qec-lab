"""
Logical qubit register: N×M grid of independent surface code patches.

Each patch is simulated independently with code-capacity noise (run_shot).
Physical qubit count: N×M × 2d² (rotated surface code, one patch per logical qubit).

This models the idle register between gates — no inter-patch surgery.
"""
import random

from .simulator import run_shot


def run_register(n: int, m: int, d: int, p: float, seed: int | None = None) -> dict:
    rng = random.Random(seed)
    patches = []
    logical_errors = 0

    for row in range(n):
        for col in range(m):
            patch_seed = rng.randint(0, 2**32 - 1) if seed is not None else None
            shot = run_shot(d, p, patch_seed)
            has_err = shot["logical_error"]
            if has_err:
                logical_errors += 1
            patches.append({
                "row": row,
                "col": col,
                "id": f"q_{row}_{col}",
                "logical_error": has_err,
                "logical_x_error": shot["logical_x_error"],
                "logical_z_error": shot["logical_z_error"],
                "errors": len(shot["errors_x"]) + len(shot["errors_z"]),
                "syndromes": len(shot["syndromes"]),
            })

    phys_per_patch = 2 * d * d
    total_patches = n * m
    return {
        "n": n,
        "m": m,
        "d": d,
        "p": p,
        "patches": patches,
        "total_patches": total_patches,
        "phys_per_patch": phys_per_patch,
        "total_physical": total_patches * phys_per_patch,
        "logical_errors": logical_errors,
        "logical_error_rate": logical_errors / total_patches,
    }
