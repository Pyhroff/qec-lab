"""
QEC Lab CLI demo — no server needed.

Runs a surface code simulation sweep and prints results.
"""

from qec import make_lattice, run_shot, run_threshold
from qec.resource import estimate, logical_error_rate


def main():
    print("=" * 58)
    print("  QEC LAB — Surface Code Simulator")
    print("=" * 58)

    # ── lattice structure ──────────────────────────────────────
    print("\n[1] Rotated surface code lattice counts")
    print(f"{'d':>4}  {'data':>6}  {'stabs':>6}  {'X-stabs':>8}  {'Z-stabs':>8}")
    for d in [3, 5, 7, 9]:
        lat = make_lattice(d)
        xs = sum(1 for s in lat['stabs'] if s['type'] == 'X')
        zs = sum(1 for s in lat['stabs'] if s['type'] == 'Z')
        print(f"{d:>4}  {lat['n_data']:>6}  {lat['n_stabs']:>6}  {xs:>8}  {zs:>8}")

    # ── single shot sweep ──────────────────────────────────────
    print("\n[2] Single-shot results (d=5, code-capacity noise)")
    print(f"{'p':>8}  {'X-err':>6}  {'Z-err':>6}  {'syn':>5}  {'logical':>8}")
    for p in [0.005, 0.01, 0.02, 0.05, 0.10]:
        r = run_shot(5, p, seed=123)
        flag = "FAIL" if r['logical_error'] else "ok"
        print(f"{p:>8.3f}  {len(r['errors_x']):>6}  {len(r['errors_z']):>6}  {len(r['syndromes']):>5}  {flag:>8}")

    # ── resource estimate ──────────────────────────────────────
    print("\n[3] RSA-2048 resource estimates (surface code)")
    print(f"{'p_phys':>8}  {'d_req':>6}  {'phys/log':>9}  {'total_M':>8}  {'feasible':>9}")
    for p in [0.0003, 0.001, 0.003, 0.01]:
        r = estimate(p)
        print(f"{p:>8.4f}  {r['d']:>6}  {r['phys_per_logical']:>9}  {r['total_physical']/1e6:>8.2f}  {str(r['feasible']):>9}")

    print("\n  Published benchmarks at p=0.1%:")
    est = estimate(0.001)
    for label, count in est['references'].items():
        print(f"    {label}: {count/1e6:.1f} M qubits" if count >= 1e6 else f"    {label}: {count//1000} K qubits")

    # ── threshold preview (fast, 200 shots) ───────────────────
    print("\n[4] Threshold curve sample (200 shots, circuit-level noise)")
    print("    (full 600-shot run takes ~60s — see dashboard for complete curve)")
    results = run_threshold(shots=200, d_values=[3, 5])
    # Show a few key points
    key_p = [0.005, 0.01, 0.015, 0.022]
    print(f"{'p':>8}  {'d=3 pL':>8}  {'d=5 pL':>8}")
    for p in key_p:
        r3 = next((r for r in results if r['d']==3 and abs(r['p']-p)<0.001), None)
        r5 = next((r for r in results if r['d']==5 and abs(r['p']-p)<0.001), None)
        v3 = f"{r3['logical_error_rate']:.3f}" if r3 else "—"
        v5 = f"{r5['logical_error_rate']:.3f}" if r5 else "—"
        print(f"{p:>8.4f}  {v3:>8}  {v5:>8}")

    print("\n  Threshold signature: below ~1%, larger d -> lower p_L")
    print("  Above ~1%, larger d -> higher p_L (encoding overhead dominates)")
    print()


if __name__ == '__main__':
    main()
