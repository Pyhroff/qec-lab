# QEC Lab

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)
![D3.js v7](https://img.shields.io/badge/D3.js-v7-orange)
![Stim](https://img.shields.io/badge/Stim-1.16-purple)
![PyMatching v2](https://img.shields.io/badge/PyMatching-v2-green)

Interactive surface code quantum error correction simulator. Run real MWPM decoding on a rotated distance-d code, watch syndrome extraction animate in D3, plot the error threshold curve via Stim circuit-level noise, and see how RSA-2048 qubit estimates have dropped from 20M → 100K between 2019 and 2026.

---

## What it shows

| Feature | Description |
|---|---|
| **Lattice visualiser** | Rotated surface code at d = 3, 5, 7, 9 — data qubits, X/Z stabilizer faces, boundary weight-2 checks |
| **Shot animation** | Inject depolarizing errors → measure syndromes → MWPM decode → display correction → show logical outcome |
| **Error threshold curve** | Stim circuit-level noise + PyMatching v2 across d = 3, 5, 7 at 14 physical error rates; threshold emerges near p ~ 1% |
| **RSA-2048 resource estimator** | Physical qubit count as a function of p and n\_logical; side-by-side published benchmarks (Gidney 2019 / 2025 / 2026) |

---

## Architecture

```
qec-lab/
├── backend/
│   ├── server.py          FastAPI, port 8001
│   ├── demo.py            CLI demo (no server needed)
│   └── qec/
│       ├── lattice.py     Rotated surface code geometry
│       ├── simulator.py   Code-capacity shots (PyMatching) + threshold (Stim)
│       └── resource.py    p_L model, qubit estimator, published refs
├── frontend/
│   └── index.html         D3 visualiser (no build step)
├── docs/
│   └── DESIGN.md          Lattice math, noise models, decoder details
└── .gitignore
```

---

## Noise models

| Mode | Model | Details |
|---|---|---|
| Shot simulation | Code-capacity | Independent X/Z errors per data qubit; no measurement noise |
| Threshold curve | Circuit-level | Stim `surface_code:rotated_memory_z` with `after_clifford_depolarization=p` |

**Threshold:** below ~ 1%, larger d → lower logical error rate. Above ~ 1%, larger d → higher logical error rate. The surface code is only useful below the threshold.

---

## Decision thresholds (surface code, rotated memory-Z)

| Physical p | Behaviour |
|---|---|
| < 0.5 % | Well below threshold — rapidly improvable with larger d |
| 0.5 – 1 % | Near threshold — diminishing returns |
| ≥ 1 % | Above threshold — encoding makes things **worse** |

---

## Quickstart

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --port 8001 --reload
```

Or run the CLI demo (no server needed):

```bash
cd backend
python demo.py
```

### Frontend

Open `frontend/index.html` directly in a browser — no build step needed. The page polls `http://localhost:8001`.

```
# Direct file open
file:///path/to/qec-lab/frontend/index.html
```

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/lattice?d=3` | Lattice geometry (data qubits + stabilizers) |
| `POST` | `/api/shot` | Single shot: `{d, p, seed?}` → errors, syndromes, corrections, logical outcome |
| `GET` | `/api/threshold?shots=600` | Threshold sweep across d=3,5,7 (takes ~90s) |
| `GET` | `/api/resource?p=0.001&n_logical=3000` | RSA-2048 qubit estimate |

---

## RSA-2048 published qubit estimates

| Paper | Qubits | Key improvements |
|---|---|---|
| Gidney & Ekerå 2019 ([arXiv:1905.09749](https://arxiv.org/abs/1905.09749)) | ~ 20 M | Baseline surface code Shor |
| Gidney 2025 ([arXiv:2505.15917](https://arxiv.org/abs/2505.15917)) | < 1 M | Approx. residue arithmetic, yoked surface codes, magic state cultivation |
| Heterogeneous arch. 2026 ([arXiv:2604.06319](https://arxiv.org/abs/2604.06319)) | ~ 100 K | Novel heterogeneous layout |

All assume p ≈ 0.1% physical error rate. The 200× reduction from 2019 → 2026 is primarily algorithmic, not from better error correction codes.

---

## License

MIT — see [LICENSE](LICENSE)
