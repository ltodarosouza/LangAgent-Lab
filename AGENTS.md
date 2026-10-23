# lung-agent-lab agent contract

This repository is the writable laboratory. The sibling repository
`synthetic-lung-ct-evaluation` is an external, read-only evaluator.

## Non-negotiable boundaries

- Never change evaluator code, calibration, thresholds, or reference history during an experiment.
- The two Git LFS checkpoints in `models/` are immutable inputs. Never replace or modify them.
- Never commit medical images, virtual environments, or generated runs.
- Do not fine-tune or train weights unless the human explicitly authorizes it.
- Keep AEKL weights and `scale_factor=1.0` frozen while investigating LDM sampling.
- Compare candidates on the same cases and seeds.
- Use the fixed `data/dsr-valid/manifest.json` selection for real DSR comparisons.
- Do not add, remove, or replace DSR cases during a parameter search.

## Mock optimization

- Edit only `workspace/candidate.json` when searching for better parameters.
- Treat `agent/mock_backend.py`, `agent/score.py`, `configs/search_space.json`, and tests as fixed benchmarks.
- Run `python -m agent.run_experiment --backend mock --config workspace/candidate.json`.
- Record every attempted configuration; never overwrite or hide a worse result.
- Prefer one controlled parameter change at a time until its effect is understood.

## Real optimization

- Follow `AGENT_PROMPT.md` and treat `MAX_CONFIGURATIONS` as a hard cap.
- Read `SEARCH_STRATEGY.md` before proposing a candidate. Every change needs a metric-based
  causal hypothesis. Do not bisect or choose a midpoint merely because the previous value failed.
- If `workspace/search_state.json` exists, use its fixed baseline and current best;
  do not regenerate either one. Its current-best configuration is the first configuration
  in the new budget and the next hypothesis must start from those parameters.
- Edit only `workspace/candidate.json` during the search.
- Use the cumulative 5 → 10 → 37 funnel. Promote 5 to 10, then 10 to 37, only when the
  preceding report says `melhor` relative to the same-size report of the current best.
  Every comparison still uses the fixed baseline as the scientific ruler. Reuse completed cases.
- The agent may vary `steps`, `noise_level`, `eta`, `latent_noise_scale` and
  `conditioning_noise_scale` within `configs/real_search_space.json`. Keep sampler,
  scale factor and seed frozen.
- Accept a new operational best when the complete 37-case report beats the current best,
  wins in more cuts than it loses, and adds no rejected cases or invalid pairs. Report the
  15% improvement threshold separately as a strong target, not as a promotion gate.
- Read per-case metrics and previews; never optimize from the aggregate score alone.
- Read `CADERNO.md` and inventory existing reports before proposing a candidate. Never
  regenerate an exact configuration when a complete same-scope report can be reused.

## Completion

A candidate is better only when its saved score improves without violating brightness,
pair-correlation, or validity constraints. Report both improvements and regressions.
