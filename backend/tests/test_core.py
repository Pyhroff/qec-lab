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
