"""Boletim do juiz para um lote já gerado.

Monta, dentro do lote, uma pasta de entrada com links para cada original e
sintética (`X.tiff`, `X_generate.tiff`) e pede ao avaliador o boletim com a
régua congelada. O resultado fica em `boletim.json`, ao lado do `report.json`.
`run_batch.py` chama isto no fim de cada lote; para refazer um lote antigo:

    .venv/bin/python generator/boletim.py --run-dir runs/real/baseline-full \\
        [--baseline runs/real/OUTRO/boletim.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from settings import EVALUATOR_HISTORY, EVALUATOR_PYTHON, EVALUATOR_REPO

INPUT_DIR = "boletim-entrada"
OUTPUT_FILE = "boletim.json"


def link(source: Path, target: Path) -> None:
    if target.is_symlink() or target.exists():
        target.unlink()
    target.symlink_to(source.resolve())


def write_boletim(run_dir: Path, report: dict, baseline: Path | None = None) -> Path:
    """Gera `run_dir/boletim.json` para os casos do relatório; devolve o caminho."""
    run_dir = run_dir.resolve()
    entry = run_dir / INPUT_DIR
    masks = entry / "mascaras"
    masks.mkdir(parents=True, exist_ok=True)
    for record in report["cases"]:
        case_id, files = record["case_id"], record["evaluation"]["files"]
        link(Path(files["original"]), entry / f"{case_id}.tiff")
        link(Path(files["synthetic"]), entry / f"{case_id}_generate.tiff")
        link(Path(files["mask"]), masks / f"{case_id}_mask.tiff")
    output = run_dir / OUTPUT_FILE
    command = [
        str(EVALUATOR_PYTHON), "-m", "frameworks.texture_evaluator.boletim", "avaliar",
        "--images", str(entry), "--mask-dir", str(masks),
        "--calibration", str(EVALUATOR_HISTORY), "--output", str(output),
    ]
    if baseline:
        command += ["--baseline", str(baseline.resolve())]
    subprocess.run(command, check=True, cwd=EVALUATOR_REPO)
    return output


def sibling_boletim(report_path: Path | None) -> Path | None:
    """Boletim do lote de referência, se ele existir ao lado do relatório comparado."""
    if report_path is None:
        return None
    candidate = report_path.resolve().parent / OUTPUT_FILE
    return candidate if candidate.is_file() else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", type=Path, required=True, help="pasta do lote, com report.json")
    parser.add_argument("--baseline", type=Path, help="boletim.json de outro lote do mesmo escopo")
    args = parser.parse_args()
    report = json.loads((args.run_dir / "report.json").read_text(encoding="utf-8"))
    print(f"Boletim: {write_boletim(args.run_dir, report, args.baseline)}")


if __name__ == "__main__":
    main()
