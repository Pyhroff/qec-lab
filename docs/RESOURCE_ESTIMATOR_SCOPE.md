# Resource estimator: scope and interpretation

The resource estimator is an analytical model for exploring how selected assumptions affect surface-code resource estimates. It is not a hardware benchmark, a cryptanalytic implementation, or a prediction of when RSA-2048 will be factored.

## Model assumptions

The current estimator in `backend/qec/resource.py` uses a simplified logical-error approximation:

```
p_L ≈ A × (p_physical / p_threshold)^((d + 1) / 2)
```

The implementation sets `A = 0.1` and `p_threshold = 0.01`, searches odd code distances, and estimates physical qubits using `2 × d²` per logical qubit. These are explicit model choices, not values measured by this repository's own hardware experiments.

The output depends on the physical error rate, logical-qubit count, gate budget, total failure budget, the approximation above, and the finite distance search. Results should always be interpreted with those assumptions visible.

## Important interpretation limits

- A computed physical-qubit count is an analytical estimate, not a measured device requirement.
- Comparing the output to a published estimate is a comparison of model outputs and assumptions; it does not independently validate the model.
- Published factoring estimates may use different arithmetic, magic-state, architecture, error-correction, and scheduling assumptions. Similar output units do not make the underlying models directly comparable.
- Runtime values derived from a fixed assumed cycle duration are conditional calculations, not measured runtime.
- A finite code-distance search can reach its cap. Treat that as a model limitation or unmet target, not as evidence that the capped estimate is feasible.
- A seeded Monte Carlo sweep over model parameters describes sensitivity to the chosen input distributions. It is not an empirical confidence interval unless those distributions and the statistical interpretation are independently justified.

## Reporting checklist

For a report, table, or chart, include:

1. source revision and model version;
2. physical error rate and code-distance assumptions;
3. logical-qubit count, gate budget, and total failure budget;
4. whether the value is analytical, simulated, or measured;
5. search caps and any unmet target flags;
6. the primary source and assumptions for every external comparison.

Do not label an analytical estimate as a benchmark result. Do not claim validation merely because the result is within a chosen factor of a published number.

## Primary research references

- [Gidney and Ekerå, *How to factor 2048-bit RSA integers in 8 hours using 20 million noisy qubits* (2019)](https://arxiv.org/abs/1905.09749)
- [Gidney, *Factor RSA-2048 using less than a million noisy qubits* (2025)](https://arxiv.org/abs/2505.15917)
- [Xu et al., *Constant-overhead fault-tolerant quantum computation with reconfigurable atom arrays* (2026)](https://arxiv.org/abs/2604.06319)

Read the source papers' own model assumptions before comparing their figures to this estimator.
