"""Fast, deterministic regression tests for QEC Lab's core model."""

import pytest

from qec import estimate, make_lattice, run_shot
from qec.resource import logical_error_rate, min_distance


@pytest.mark.parametrize("distance", [3, 5, 7, 9])
def test_rotated_surface_code_stabilizer_count(distance):
    lattice = make_lattice(distance)
    assert lattice["n_data"] == distance**2
    assert lattice["n_stabs"] == distance**2 - 1
    assert len(lattice["logical_x"]) == distance
    assert len(lattice["logical_z"]) == distance


def test_seeded_zero_noise_shot_is_reproducible_and_clean():
    first = run_shot(d=3, p=0.0, seed=1234)
    second = run_shot(d=3, p=0.0, seed=1234)
    assert first == second
    assert first["errors_x"] == []
    assert first["errors_z"] == []
    assert first["logical_error"] is False


def test_logical_error_rate_handles_zero_noise():
    assert logical_error_rate(0.0, 3) == 0.0


@pytest.mark.parametrize(
    "p,d",
    [(-0.1, 3), (1.1, 3), (0.01, 2), (0.01, 4)],
)
def test_logical_error_rate_rejects_invalid_inputs(p, d):
    with pytest.raises(ValueError):
        logical_error_rate(p, d)


def test_min_distance_rejects_invalid_target():
    with pytest.raises(ValueError):
        min_distance(0.001, 0.0)


def test_resource_estimator_rejects_invalid_inputs():
    for kwargs in (
        {"p_physical": -0.1},
        {"p_physical": 0.001, "n_logical": 0},
        {"p_physical": 0.001, "t_gates": 0},
        {"p_physical": 0.001, "p_total_failure": 0.0},
    ):
        with pytest.raises(ValueError):
            estimate(**kwargs)


def test_resource_estimate_is_explicit_and_nonnegative():
    result = estimate(p_physical=0.001, n_logical=100, t_gates=1_000_000)
    assert result["d"] >= 3
    assert result["d"] % 2 == 1
    assert result["total_physical"] == result["n_logical"] * result["phys_per_logical"]
    assert result["total_physical"] > 0



def test_seeded_noisy_shot_is_reproducible():
    first = run_shot(d=3, p=0.03, seed=9876)
    second = run_shot(d=3, p=0.03, seed=9876)
    assert first == second


def test_surface_code_error_model_is_monotonic_below_threshold():
    low_noise = logical_error_rate(0.001, 3)
    higher_noise = logical_error_rate(0.002, 3)
    larger_distance = logical_error_rate(0.001, 5)
    assert 0 <= larger_distance < low_noise < higher_noise


def test_required_distance_does_not_increase_when_noise_decreases():
    noisier = min_distance(0.001, 1e-6)
    cleaner = min_distance(0.0005, 1e-6)
    assert cleaner <= noisier
    assert cleaner >= 3 and cleaner % 2 == 1
    assert noisier >= 3 and noisier % 2 == 1


def test_resource_estimator_rejects_boolean_counts():
    with pytest.raises(ValueError):
        estimate(p_physical=0.001, n_logical=True)
    with pytest.raises(ValueError):
        estimate(p_physical=0.001, t_gates=True)


def test_api_cors_has_explicit_local_allowlist():
    from server import app

    cors = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
    assert cors.kwargs["allow_origins"] == [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    assert cors.kwargs["allow_methods"] == ["GET", "POST"]
    assert cors.kwargs["allow_headers"] == ["Content-Type"]
    assert "*" not in cors.kwargs["allow_origins"]



def test_resource_sweep_records_reproducible_parameters_and_model_limits():
    from qec.resource_sweep import build_sweep_report

    report = build_sweep_report(
        p_values=[0.001, 0.005],
        t_gate_counts=[1000, 100000],
        n_logical=100,
        p_total_failure=0.5,
        code_revision="test-revision",
    )
    assert report["schema_version"] == "1.0"
    assert report["code_revision"] == "test-revision"
    assert report["measurement_type"] == "analytical_model_sweep_not_hardware_measurement"
    assert report["result_count"] == 4
    assert len(report["results"]) == 4
    assert report["model"]["distance_cap_sentinel"] == 61
    assert all("distance_cap_exceeded" in row for row in report["results"])


def test_resource_sweep_rejects_threshold_and_empty_grids():
    from qec.resource_sweep import build_sweep_report

    with pytest.raises(ValueError):
        build_sweep_report(p_values=[0.01], t_gate_counts=[1000])
    with pytest.raises(ValueError):
        build_sweep_report(p_values=[], t_gate_counts=[1000])
