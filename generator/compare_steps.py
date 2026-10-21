import argparse
import csv
import json
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np
import tifffile
import torch
from PIL import Image

from generate_one import generate_image
from models import choose_device, load_models
from settings import DATA_ROOT, EVALUATOR_HISTORY, EVALUATOR_PYTHON, EVALUATOR_REPO, ROOT



def first_valid_cases(limit: int) -> list[str]:
    with (EVALUATOR_HISTORY.parent / "por_caso.csv").open(encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return list(dict.fromkeys(row["case_id"] for row in rows))[:limit]


def save_preview(source: Path, output: Path, low: float, high: float) -> None:
    array = np.asarray(tifffile.imread(source), dtype=np.float32)
    visible = np.clip((array - low) / max(high - low, 1e-8), 0, 1)
    Image.fromarray(np.uint8(visible * 255), mode="L").save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara dois números de passos nas mesmas imagens.")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--steps", type=int, nargs=2, default=(25, 50))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--noise-level", type=int, default=1)
    parser.add_argument("--scale-factor", type=float, default=1.0)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "comparisons" / "steps-25-vs-50")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    device = choose_device("auto")
    stage1, diffusion, config = load_models(device)
    cases = first_valid_cases(args.count)
    records = []

    for case_index, case_id in enumerate(cases, start=1):
        print(f"\nCaso {case_index}/{len(cases)}: {case_id}")
        case_dir = args.output_dir / f"caso-{case_index}"
        case_dir.mkdir(parents=True, exist_ok=True)
        original = DATA_ROOT / "Dsr" / f"{case_id}.tiff"
        mask = DATA_ROOT / "Dgen" / f"{case_id}_mask.tiff"
        original_array = np.asarray(tifffile.imread(original), dtype=np.float32)
        low, high = (float(value) for value in np.percentile(original_array, (1, 99)))
        original_preview = case_dir / "original.png"
        save_preview(original, original_preview, low, high)

        case_record = {"case_id": case_id, "original_preview": str(original_preview.resolve()), "variants": {}}
        for steps in args.steps:
            synthetic = case_dir / f"steps-{steps}.tiff"
            metadata = generate_image(
                original, synthetic, stage1, diffusion, config, device,
                steps=steps,
                noise_level=args.noise_level,
                scale_factor=args.scale_factor,
                seed=args.seed,
            )
            evaluation_path = case_dir / f"steps-{steps}-avaliacao.json"
            subprocess.run([
                str(EVALUATOR_PYTHON), "-m", "frameworks.texture_evaluator.evaluate_one",
                "--original", str(original),
                "--synthetic", str(synthetic),
                "--mask", str(mask),
                "--output", str(evaluation_path),
            ], check=True, cwd=EVALUATOR_REPO)
            preview = case_dir / f"steps-{steps}.png"
            save_preview(synthetic, preview, low, high)
            evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
            case_record["variants"][str(steps)] = {
                "preview": str(preview.resolve()),
                "generation": metadata,
                "evaluation": evaluation,
            }
        records.append(case_record)

    aggregates = {}
    for steps in args.steps:
        variants = [record["variants"][str(steps)] for record in records]
        measurements = [variant["evaluation"]["measurements"] for variant in variants]
        verdicts = [variant["evaluation"]["verdicts"] for variant in variants]
        aggregates[str(steps)] = {
            "elapsed_seconds_total": round(sum(variant["generation"]["elapsed_seconds"] for variant in variants), 3),
            "final_counts": dict(Counter(verdict["final"] for verdict in verdicts)),
            "brightness_counts": dict(Counter(verdict["brightness"] for verdict in verdicts)),
            "texture_counts": dict(Counter(verdict["texture"] for verdict in verdicts)),
            "median": {
                "pair_correlation": float(np.median([row["pair_correlation"] for row in measurements])),
                "wavelet_fine_pct": float(np.median([row["wavelet_fine_pct"] for row in measurements])),
                "wavelet_coarse_pct": float(np.median([row["wavelet_coarse_pct"] for row in measurements])),
                "glcm_contrast_pct": float(np.median([row["glcm_contrast_pct"] for row in measurements])),
                "delta_mu_abs": float(np.median([abs(row["delta_mu"]) for row in measurements])),
            },
        }

    payload = {
        "experiment": "Mesmas 5 imagens e mesma seed; somente o número de passos muda.",
        "parameters": {"steps": list(args.steps), "seed": args.seed, "noise_level": args.noise_level, "scale_factor": args.scale_factor},
        "aggregates": aggregates,
        "cases": records,
    }
    (args.output_dir / "comparacao.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nComparação salva em: {args.output_dir / 'comparacao.json'}")


if __name__ == "__main__":
    main()
