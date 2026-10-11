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




def test_monte_carlo_resource_scenarios_are_seeded_and_labeled_as_scenarios():
    from qec.uncertainty import monte_carlo_resource_scenarios

    kwargs = {
        "samples": 100,
        "seed": 123,
        "p_min": 0.001,
        "p_max": 0.002,
        "n_logical_min": 100,
        "n_logical_max": 200,
        "t_gates_min": 1000,
        "t_gates_max": 2000,
        "p_total_failure_min": 0.2,
        "p_total_failure_max": 0.8,
    }
    first = monte_carlo_resource_scenarios(**kwargs)
    second = monte_carlo_resource_scenarios(**kwargs)
    assert first == second
    assert first["measurement_type"] == "monte_carlo_scenario_sweep_not_empirical_uncertainty"
    assert first["sample_count"] == 100
    assert first["seed"] == 123
    assert first["results"]["total_physical"]["p05"] <= first["results"]["total_physical"]["p50"]
    assert first["results"]["total_physical"]["p50"] <= first["results"]["total_physical"]["p95"]
    assert 0.0 <= first["rates"]["distance_cap_exceeded"] <= 1.0
    assert "confidence interval" in first["interpretation"].lower()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"samples": 0},
        {"samples": 10, "p_min": 0.005, "p_max": 0.001},
        {"samples": 10, "n_logical_min": 10, "n_logical_max": 1},
        {"samples": 10, "t_gates_min": 100, "t_gates_max": 10},
        {"samples": 10, "p_total_failure_min": 0.8, "p_total_failure_max": 0.2},
    ],
)
def test_monte_carlo_resource_scenarios_reject_invalid_ranges(kwargs):
    from qec.uncertainty import monte_carlo_resource_scenarios

    with pytest.raises(ValueError):
        monte_carlo_resource_scenarios(**kwargs)


def test_resource_uncertainty_api_is_registered():
    from server import app

    assert any(route.path == "/api/resource/uncertainty" for route in app.routes)


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



def test_above_threshold_resource_estimate_is_flagged_not_reported_feasible():
    assert logical_error_rate(0.05, 3) == 1.0
    result = estimate(p_physical=0.05, n_logical=100, t_gates=1_000_000)
    assert result["model_domain_valid"] is False
    assert result["distance_cap_exceeded"] is True
    assert result["target_met_within_search_cap"] is False
    assert result["total_physical_is_cap_reference"] is True
    assert result["feasible"] is False


def test_runtime_propagates_resource_model_domain_flags():
    from qec.runtime import run

    report = run("shor-rsa2048", p_physical=0.05).to_dict()
    assert report["model_domain_valid"] is False
    assert report["distance_cap_exceeded"] is True
    assert report["feasible"] is False
    assert report["within_factor"] is None
    assert all("model_domain_valid" in row for row in report["sensitivity"])

def _sample_quantum_collapse_bridge():
    return {
        "schema_version": "1.0",
        "source": {"format": "SARIF", "version": "2.1.0", "tool": "pqc-scanner"},
        "observed_evidence": {"finding_count": 2},
        "modeled_scenario": {
            "node_count": 2,
            "edge_count": 0,
            "nodes": [
                {
                    "id": "finding-0001",
                    "crypto": "RSA",
                    "evidence_file": "src/auth.py",
                    "evidence_line": 12,
                    "evidence_algorithm": "RSA",
                },
                {
                    "id": "finding-0002",
                    "crypto": "ECC-P256",
                    "evidence_file": "src/exchange.py",
                    "evidence_line": 30,
                    "evidence_algorithm": "ECC/ECDSA/ECDH",
                },
            ],
        },
    }


def test_scenario_bridge_estimates_only_rsa_nodes():
    from qec.scenario_bridge import build_scenario_report

    report = build_scenario_report(
        _sample_quantum_collapse_bridge(),
        p_physical=0.001,
        n_logical=100,
        t_gates=1_000_000,
    )
    assert report["measurement_type"] == "conditional_analytical_resource_estimate_not_hardware_measurement"
    assert report["summary"]["supported_rsa_node_count"] == 1
    assert report["summary"]["unsupported_node_count"] == 1
    assert report["findings"][0]["status"] == "estimated"
    assert report["findings"][0]["resource_estimate"]["n_logical"] == 100
    assert report["findings"][1]["status"] == "unsupported_crypto_model"
    assert report["findings"][1]["resource_estimate"] is None


def test_scenario_bridge_rejects_unrecognized_contract():
    from qec.scenario_bridge import build_scenario_report

    with pytest.raises(ValueError, match="schema_version 1.0"):
        build_scenario_report({"schema_version": "2.0"})


def test_scenario_bridge_propagates_resource_model_domain_flags():
    from qec.scenario_bridge import build_scenario_report

    report = build_scenario_report(
        _sample_quantum_collapse_bridge(),
        p_physical=0.05,
        n_logical=100,
        t_gates=1_000_000,
    )
    rsa = report["findings"][0]["resource_estimate"]
    assert rsa["model_domain_valid"] is False
    assert rsa["distance_cap_exceeded"] is True
    assert rsa["feasible"] is False


def test_monte_carlo_separates_cap_sentinels_from_valid_resource_quantiles(monkeypatch):
    import qec.uncertainty as uncertainty

    def capped_estimate(**kwargs):
        return {
            "total_physical": 7442,
            "d": 61,
            "distance_cap_exceeded": True,
            "model_domain_valid": True,
            "feasible": False,
        }

    monkeypatch.setattr(uncertainty, "estimate", capped_estimate)
    report = uncertainty.monte_carlo_resource_scenarios(
        samples=3,
        seed=11,
        p_min=0.001,
        p_max=0.002,
        n_logical_min=100,
        n_logical_max=100,
        t_gates_min=1000,
        t_gates_max=1000,
        p_total_failure_min=0.5,
        p_total_failure_max=0.5,
    )
    assert report["schema_version"] == "1.1"
    assert report["results"]["full_distribution_includes_distance_cap_reference_values"] is True
    assert report["results_within_search_cap"]["sample_count"] == 0
    assert report["results_within_search_cap"]["total_physical"] is None
    assert report["results_within_search_cap"]["reported_distance"] is None
    assert report["rates"]["distance_cap_exceeded"] == 1.0


def test_resource_cap_uses_supported_distance_for_reference_counts():
    result = estimate(p_physical=0.05, n_logical=100, t_gates=1_000_000)

    assert result["d"] == 61  # compatibility sentinel, not a physical distance
    assert result["modeled_distance"] == 59
    assert result["distance_limit_reached"] is True
    assert result["phys_per_logical"] == 2 * 59 * 59
    assert result["total_physical"] == 100 * 2 * 59 * 59
    assert result["feasible"] is False
    assert "cap-reference" in result["feasibility_note"]


def test_min_distance_rejects_unit_failure_target():
    with pytest.raises(ValueError):
        min_distance(0.001, 1.0)
