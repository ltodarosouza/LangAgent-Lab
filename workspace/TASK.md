# Mock mission

Find a higher-scoring valid candidate in at most six experiments.

1. Read `configs/search_space.json` and the current `workspace/candidate.json`.
2. Change only `workspace/candidate.json`.
3. Run the mock experiment command from the root README.
4. Read the saved `resultado_completo.json` and `runs/history.jsonl`.
5. Keep every run. Never change the benchmark or score implementation.
6. Finish by reporting the baseline, best candidate, score difference, and all attempted candidates.

The mock validates the workflow only. A human must approve transferring a
candidate to the real LDM.
