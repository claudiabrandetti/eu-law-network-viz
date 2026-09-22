# Sensitivity analysis

All calculations use cached classifications and make no API calls.
Diffusion varies the restart weight and whether stored relation weights are used.
Splitting varies the four deterministic proposal thresholds; it does not rerun the historical LLM validation stage.

## appalti_it

- Canonical diffusion: mean H_global = 0.5195 at lambda = 0.50 with stored weights.
- Across diffusion settings: mean H_global = 0.4948–0.5346.
- Canonical deterministic thresholds: 13 proposals, paired reduction = 26.1%.
- Across threshold settings: 11–17 proposals; paired reduction = 23.2%–35.5%.

## fdi_screening

- Canonical diffusion: mean H_global = 0.5315 at lambda = 0.50 with stored weights.
- Across diffusion settings: mean H_global = 0.4751–0.5640.
- Canonical deterministic thresholds: 4 proposals, paired reduction = 14.5%.
- Across threshold settings: 2–5 proposals; paired reduction = 8.9%–17.5%.
