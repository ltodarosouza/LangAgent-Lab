"""Gera e avalia o lote rápido de 7 cortes ou o conjunto completo de 37."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.config import load_json, validate_candidate  # noqa: E402
from generate_one import generate_image  # noqa: E402
from models import choose_device, load_models  # noqa: E402
from reporting import compare_summaries, load_report, markdown_report, summarize  # noqa: E402
from settings import EVALUATOR_HISTORY, EVALUATOR_PYTHON, EVALUATOR_REPO  # noqa: E402


DATASET = ROOT / "data" / "dsr-valid" / "manifest.json"
QUICK_CASES = ROOT / "configs" / "quick_cases.json"
REAL_SEARCH_SPACE = ROOT / "configs" / "real_search_space.json"


def selected_cases(scope: str) -> list[dict]:
    manifest = load_json(DATASET)
    cases = {case["case_id"]: case for case in manifest["cases"]}
    if scope == "full":
        selected = list(cases.values())
    else:
        quick = load_json(QUICK_CASES)["cases"]
        missing = [case_id for case_id in quick if case_id not in cases]
        if missing:
            raise ValueError(f"casos rápidos ausentes do manifesto: {missing}")
        selected = [cases[case_id] for case_id in quick]
    return selected


def save_preview(source: Path, output: Path, low: float, high: float) -> None:
    array = np.asarray(tifffile.imread(source), dtype=np.float32)
    visible = np.clip((array - low) / max(high - low, 1e-8), 0, 1)
    Image.fromarray(np.uint8(visible * 255), mode="L").save(output)


def persist_report(payload: dict, run_dir: Path) -> None:
    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "report.md").write_text(markdown_report(payload), encoding="utf-8")


def reused_records(path: Path | None, candidate: dict) -> dict[str, dict]:
    if path is None:
        return {}
    report = load_report(path)
    if report["candidate"] != candidate:
        raise ValueError("o relatório reutilizado foi gerado com outros parâmetros")
    return {record["case_id"]: {**record, "reused_from": str(path.resolve())} for record in report["cases"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("quick", "full"), required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "workspace" / "candidate.json")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--compare-to", type=Path)
    parser.add_argument("--reuse-report", type=Path)
    parser.add_argument("--device", choices=("auto", "cpu", "mps"), default="auto")
    args = parser.parse_args()

    candidate = validate_candidate(load_json(args.config), load_json(REAL_SEARCH_SPACE))
    cases = selected_cases(args.scope)
    run_name = datetime.now().strftime(f"%Y%m%d-%H%M%S-{args.scope}")
    run_dir = (args.output_dir or ROOT / "runs" / "real" / run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "synthetics").mkdir(exist_ok=True)
    (run_dir / "evaluations").mkdir(exist_ok=True)
    (run_dir / "previews").mkdir(exist_ok=True)

    previous_report_path = run_dir / "report.json"
    existing = load_report(previous_report_path) if previous_report_path.exists() else None
    if existing and existing["candidate"] != candidate:
        raise ValueError(f"{run_dir} já contém uma execução com outros parâmetros")
    records = {record["case_id"]: record for record in (existing or {}).get("cases", [])}
    records.update({key: value for key, value in reused_records(args.reuse_report, candidate).items() if key not in records})

    pending = [case for case in cases if case["case_id"] not in records]
    device = choose_device(args.device)
    stage1 = diffusion = model_config = None
    if pending:
        stage1, diffusion, model_config = load_models(device)

    dataset_root = DATASET.parent
    for index, case in enumerate(cases, start=1):
        case_id = case["case_id"]
        if case_id in records:
            print(f"[{index}/{len(cases)}] Reutilizado: {case_id}")
            continue
        print(f"[{index}/{len(cases)}] Gerando: {case_id}")
        original = (dataset_root / case["original"]).resolve()
        mask = (dataset_root / case["mask"]).resolve()
        synthetic = run_dir / "synthetics" / f"{case_id}_generate.tiff"
        evaluation_path = run_dir / "evaluations" / f"{case_id}.json"
        generation = generate_image(
            original, synthetic, stage1, diffusion, model_config, device,
            steps=int(candidate["steps"]),
            noise_level=int(candidate["noise_level"]),
            scale_factor=float(candidate["scale_factor"]),
            seed=int(candidate["seed"]),
        )
        subprocess.run([
            str(EVALUATOR_PYTHON), "-m", "frameworks.texture_evaluator.evaluate_one",
            "--original", str(original), "--synthetic", str(synthetic),
            "--mask", str(mask), "--history", str(EVALUATOR_HISTORY),
            "--output", str(evaluation_path),
        ], check=True, cwd=EVALUATOR_REPO)
        evaluation = load_json(evaluation_path)

        original_array = np.asarray(tifffile.imread(original), dtype=np.float32)
        low, high = (float(value) for value in np.percentile(original_array, (1, 99)))
        original_preview = run_dir / "previews" / f"{case_id}_original.png"
        synthetic_preview = run_dir / "previews" / f"{case_id}_synthetic.png"
        save_preview(original, original_preview, low, high)
        save_preview(synthetic, synthetic_preview, low, high)
        records[case_id] = {
            "case_id": case_id,
            "generation": generation,
            "evaluation": evaluation,
            "previews": {
                "original": str(original_preview),
                "synthetic": str(synthetic_preview),
            },
        }
        ordered = [records[item["case_id"]] for item in cases if item["case_id"] in records]
        payload = {
            "schema_version": 1,
            "run": run_dir.name,
            "scope": args.scope,
            "completed": len(ordered) == len(cases),
            "candidate": candidate,
            "dataset": {"manifest": str(DATASET), "requested_case_count": len(cases)},
            "summary": summarize(ordered),
            "cases": ordered,
        }
        persist_report(payload, run_dir)

    ordered = [records[item["case_id"]] for item in cases]
    payload = {
        "schema_version": 1,
        "run": run_dir.name,
        "scope": args.scope,
        "completed": True,
        "candidate": candidate,
        "dataset": {"manifest": str(DATASET), "requested_case_count": len(cases)},
        "summary": summarize(ordered),
        "cases": ordered,
    }
    if args.compare_to:
        reference = load_report(args.compare_to)
        if reference["scope"] != args.scope:
            raise ValueError("só é possível comparar relatórios do mesmo escopo")
        payload["comparison"] = {
            "reference": str(args.compare_to.resolve()),
            **compare_summaries(payload["summary"], reference["summary"]),
        }
    persist_report(payload, run_dir)
    print(f"Relatório JSON: {run_dir / 'report.json'}")
    print(f"Relatório legível: {run_dir / 'report.md'}")
    print(f"Nota: {payload['summary']['score']:.4f}")


if __name__ == "__main__":
    main()
