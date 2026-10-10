"""Input-validation tests for logical register simulation."""

import pytest

from qec import register


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"n": 0, "m": 1, "d": 3, "p": 0.0}, "n must be a positive integer"),
        ({"n": 1, "m": 0, "d": 3, "p": 0.0}, "m must be a positive integer"),
        ({"n": 1, "m": 1, "d": 2, "p": 0.0}, "d must be an odd integer"),
        ({"n": 1, "m": 1, "d": 3, "p": -0.1}, "p must be a finite probability"),
        ({"n": 1, "m": 1, "d": 3, "p": 1.1}, "p must be a finite probability"),
        ({"n": 1, "m": 1, "d": 3, "p": float("nan")}, "p must be a finite probability"),
        ({"n": 1, "m": 1, "d": 3, "p": 0.0, "seed": "7"}, "seed must be an integer"),
    ],
)
def test_run_register_rejects_invalid_inputs(kwargs, message):
    with pytest.raises(ValueError, match=message):
        register.run_register(**kwargs)


def test_run_register_validates_before_simulating(monkeypatch):
    monkeypatch.setattr(register, "run_shot", lambda d, p, seed: {
        "logical_error": False,
        "logical_x_error": False,
        "logical_z_error": False,
        "errors_x": [],
        "errors_z": [],
        "syndromes": {},
    })

    result = register.run_register(n=1, m=1, d=3, p=0.0, seed=7)

    assert result["total_patches"] == 1
    assert result["total_physical"] == 18
    assert result["logical_error_rate"] == 0
