# Quantum OS

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)
![D3.js v7](https://img.shields.io/badge/D3.js-v7-orange)
![Stim](https://img.shields.io/badge/Stim-1.16-purple)
![PyMatching v2](https://img.shields.io/badge/PyMatching-v2-green)

This is the second half of a two-project arc. The first half — [Quantum Collapse](https://github.com/Pyhroff/quantum-collapse) — simulates what happens when a cryptographically relevant quantum computer breaks RSA: cascading infrastructure failure across banks, CAs, cloud providers, and government systems. It's the "what breaks" story.

Quantum OS is the "how and when" story. It simulates the fault-tolerant quantum computer that would actually do that: a surface code engine running real MWPM decoding, lattice surgery primitives, and a physical resource estimator grounded in current literature. The gap between "cryptographically relevant QC" and today's hardware is mostly an error correction problem, and this is what that problem looks like under the hood.

---

## What's in the simulator

**Surface code lattice** — rotated memory-Z code at d = 3, 5, 7, 9. Data qubits, X/Z stabilizer faces, weight-2 boundary checks. Click any distance and watch the geometry update.

**Shot animation** — inject depolarizing errors, run syndrome extraction, decode with MWPM, see corrections applied qubit-by-qubit, check whether a logical error survived. All of it animated step by step in D3 so you can actually watch what the decoder is doing.

**Error threshold** — the classic surface code plot: logical error rate vs physical error rate across d = 3, 5, 7. Threshold comes out near p ≈ 1% using circuit-level Stim noise. Below the threshold, larger codes do better. Above it, they do worse. This is the number that determines whether fault-tolerant QC is even viable on a given hardware platform.

**Lattice surgery — X-merge** — two d×d patches joined at a rough boundary, measuring the joint logical X_L ⊗ X_R parity. This is the primitive operation behind logical CNOT in a surface code computer. Animated in 5 phases: merge, inject errors, extract syndromes, MWPM correct, split. Verified correct at p=0 for d=3,5.

**Phenomenological noise** — adds measurement errors on top of data errors (the standard multi-round model). Threshold drops from ~1% to ~0.7%. Overlaid on the circuit-level curves so you can see exactly how much measurement noise costs.

**Fault-tolerant gate scheduler** — maps logical gate sequences to lattice surgery primitives and draws a D3 Gantt chart showing the schedule. Four preset circuits: CNOT (3 patches, depth 4), T gate via magic state injection (2 patches), Bell pair (3 patches), Toffoli (8 patches, depth 34, T-count 7). Resource counts — physical qubits, QEC rounds, runtime in µs — are exact for each circuit at any code distance.

**Logical qubit register** — N×M grid of independent surface code patches (1×1 up to 4×4). Runs a full shot on each patch and shows which ones survived without a logical error. Good for seeing how error rates scale when you're trying to keep a register alive between gates.

**RSA-2048 resource estimator** — physical qubit count as a function of physical error rate and logical qubit count. Side-by-side comparison against three published estimates: Gidney & Ekerå 2019 (~20M qubits), Gidney 2025 (<1M), and the 2026 heterogeneous architecture paper (~100K). The 200× reduction is almost entirely algorithmic.

---

## Running it

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --port 8001 --reload
```

Then open `frontend/index.html` directly in a browser. No build step, no bundler, just a file open. The page connects to `http://localhost:8001`.

If you just want to see some numbers without the UI:

```bash
cd backend
python demo.py
```

---

## Project structure

```
backend/
  server.py         FastAPI app, port 8001
  qec/
    lattice.py      Rotated surface code geometry
    simulator.py    Code-capacity shots + Stim circuit-level threshold
    surgery.py      Two-patch X-merge with seam stabilizers
    scheduler.py    Gate → lattice surgery primitive mapping + Gantt data
    register.py     N×M patch grid simulation
    resource.py     Physical qubit estimator + published benchmarks
frontend/
  index.html        Everything — D3 visualiser, controls, all panels
docs/
  DESIGN.md         Lattice math, noise models, decoder internals
```

---

## API

```
GET  /api/lattice?d=3
GET  /api/threshold?shots=600
GET  /api/resource?p=0.001&n_logical=3000
GET  /api/surgery/geometry?d=3
GET  /api/phenomenological?shots=300
GET  /api/scheduler/circuits
GET  /api/scheduler?circuit=toffoli&d=5
GET  /api/register?n=3&m=3&d=3&p=0.01

POST /api/shot      {"d": 3, "p": 0.01, "seed": null}
POST /api/surgery   {"d": 3, "p": 0.01, "seed": null}
```

---

## The noise models

Shot simulation uses code-capacity noise: independent X and Z errors per data qubit at rate p, no measurement errors. Simple enough to visualize clearly.

The threshold curve uses circuit-level noise via Stim: `after_clifford_depolarization=p` throughout the full syndrome extraction circuit including ancilla prep and measurement. This is the standard model in the surface code literature and gives a threshold around 0.5–1%.

Phenomenological noise is the middle ground: data errors plus measurement flip probability both at rate p, run for multiple rounds. Threshold comes out lower (~0.7%) because measurement errors create time-domain ambiguities the decoder has to chase.

---

## References

- Fowler et al. (2012) — Surface codes: towards practical large-scale quantum computation. [arXiv:1208.0928](https://arxiv.org/abs/1208.0928)
- Horsman et al. (2012) — Surface code quantum computing by lattice surgery. [arXiv:1111.4022](https://arxiv.org/abs/1111.4022)
- Bravyi & Kitaev (2005) — Universal quantum computation with ideal Clifford gates and noisy ancillas. [arXiv:quant-ph/0403025](https://arxiv.org/abs/quant-ph/0403025)
- Selinger (2013) — Quantum circuits of T-depth one. [arXiv:1210.0974](https://arxiv.org/abs/1210.0974)
- Gidney & Ekerå (2019) — How to factor 2048-bit RSA integers in 8 hours using 20 million noisy qubits. [arXiv:1905.09749](https://arxiv.org/abs/1905.09749)
- Gidney (2025) — Factor RSA-2048 using less than a million noisy qubits. [arXiv:2505.15917](https://arxiv.org/abs/2505.15917)
- Xu et al. (2026) — Constant-overhead fault-tolerant quantum computation with reconfigurable atom arrays. [arXiv:2604.06319](https://arxiv.org/abs/2604.06319)

---

MIT license.
