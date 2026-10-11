import pytest

from qec.resource import estimate, logical_error_rate, min_distance


def test_logical_error_rate_rejects_invalid_code_distance():
    with pytest.raises(ValueError):
        logical_error_rate(0.001, 4)


@pytest.mark.parametrize("target", [0.0, True, float("nan"), "0.1"])
def test_min_distance_rejects_invalid_failure_budget(target):
    with pytest.raises(ValueError):
        min_distance(0.001, target)


@pytest.mark.parametrize("physical_rate", [True, float("nan"), "0.001"])
def test_logical_error_rate_rejects_invalid_physical_rate(physical_rate):
    with pytest.raises(ValueError):
        logical_error_rate(physical_rate, 3)


def test_estimator_marks_distance_cap_as_infeasible():
    result = estimate(p_physical=0.05, n_logical=100, t_gates=1_000_000)

    assert result["distance_limit_reached"] is True
    assert result["feasible"] is False
    assert "distance-cap" in result["feasibility_note"]


def test_estimator_default_scenario_meets_distance_search():
    result = estimate(p_physical=0.001)

    assert result["distance_limit_reached"] is False
    assert result["d"] % 2 == 1
    assert result["p_L_achieved"] < result["p_L_per_gate"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"p_physical": 0.0},
        {"p_physical": float("nan")},
        {"p_physical": True},
        {"p_physical": "0.001"},
        {"p_physical": 0.001, "n_logical": 0},
        {"p_physical": 0.001, "t_gates": 0},
        {"p_physical": 0.001, "p_total_failure": 1.0},
        {"p_physical": 0.001, "p_total_failure": True},
    ],
)
def test_estimator_rejects_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        estimate(**kwargs)
