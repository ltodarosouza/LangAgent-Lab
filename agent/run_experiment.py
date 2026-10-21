import argparse
import json
from datetime import datetime
from pathlib import Path

from agent.config import ROOT, load_json, validate_candidate
from agent.mock_backend import run_mock
from agent.score import score_cases


def next_run_dir(root: Path, backend: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return root / f"{timestamp}-{backend}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa um experimento controlado do LungAgent-Lab.")
    parser.add_argument("--backend", choices=("mock",), default="mock")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "runs")
    args = parser.parse_args()

    candidate = validate_candidate(load_json(args.config))
    cases = run_mock(candidate)
    summary = score_cases(cases)
    run_dir = next_run_dir(args.runs_dir, args.backend)
    run_dir.mkdir(parents=True, exist_ok=False)

    result = {
        "schema_version": 1,
        "backend": args.backend,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "candidate": candidate,
        "summary": summary,
        "cases": cases,
    }
    result_path = run_dir / "resultado_completo.json"
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (args.runs_dir / "history.jsonl").open("a", encoding="utf-8") as history:
        history.write(json.dumps({"run": run_dir.name, "candidate": candidate, "summary": summary}, ensure_ascii=False) + "\n")

    print(f"Run: {run_dir.name}")
    print(f"Score: {summary['score']:.4f} | válidos: {summary['case_count'] - summary['invalid_cases']}/{summary['case_count']} | aprovados: {summary['approved_cases']}/{summary['case_count']}")
    print(f"Resultado: {result_path}")


if __name__ == "__main__":
    main()
