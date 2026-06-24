from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from qec import (
    make_lattice, run_shot, run_threshold, estimate,
    make_merged_geometry, run_merge_shot, run_phenomenological,
)

app = FastAPI(title="QEC Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── lattice ──────────────────────────────────────────────────────────────────

@app.get("/api/lattice")
def lattice_endpoint(d: int = Query(3, ge=3, le=9)):
    return make_lattice(d)


# ── single shot ──────────────────────────────────────────────────────────────

class ShotRequest(BaseModel):
    d: int = Field(3, ge=3, le=9)
    p: float = Field(0.01, ge=0.0, le=0.5)
    seed: int | None = None


@app.post("/api/shot")
def shot_endpoint(req: ShotRequest):
    return run_shot(req.d, req.p, req.seed)


# ── threshold curve ───────────────────────────────────────────────────────────

@app.get("/api/threshold")
def threshold_endpoint(shots: int = Query(600, ge=100, le=2000)):
    return run_threshold(shots=shots)


# ── resource estimator ───────────────────────────────────────────────────────

@app.get("/api/resource")
def resource_endpoint(
    p: float = Query(0.001, ge=1e-4, le=0.05),
    n_logical: int = Query(3000, ge=100, le=20000),
    t_gates: int = Query(3_000_000_000, ge=1_000_000),
):
    return estimate(p_physical=p, n_logical=n_logical, t_gates=t_gates)


# ── lattice surgery ───────────────────────────────────────────────────────────

@app.get("/api/surgery/geometry")
def surgery_geometry(d: int = Query(3, ge=3, le=5)):
    return make_merged_geometry(d)


class MergeRequest(BaseModel):
    d: int = Field(3, ge=3, le=5)
    p: float = Field(0.01, ge=0.0, le=0.5)
    seed: int | None = None


@app.post("/api/surgery")
def surgery_endpoint(req: MergeRequest):
    return run_merge_shot(req.d, req.p, req.seed)


# ── phenomenological noise ────────────────────────────────────────────────────

@app.get("/api/phenomenological")
def phenomenological_endpoint(shots: int = Query(300, ge=100, le=1000)):
    return run_phenomenological(shots=shots)
