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
- Edit only `workspace/candidate.json` during the search.
- Promote a candidate from 7 to 37 cases only when its quick report improves.
- Accept a new best candidate only after improvement on the complete 37-case report.
- Read per-case metrics and previews; never optimize from the aggregate score alone.

## Completion

A candidate is better only when its saved score improves without violating brightness,
pair-correlation, or validity constraints. Report both improvements and regressions.
