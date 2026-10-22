import argparse
import json
import subprocess
import time
from collections import Counter
from pathlib import Path

import numpy as np
import tifffile
import torch
from PIL import Image

from models import choose_device, load_stage1
from settings import DATA_ROOT, EVALUATOR_PYTHON, EVALUATOR_REPO, ROOT, valid_case_ids



def first_valid_cases(limit: int) -> list[str]:
    return valid_case_ids()[:limit]


def save_preview(array: np.ndarray, output: Path, low: float, high: float) -> None:
    visible = np.clip((array - low) / max(high - low, 1e-8), 0, 1)
    Image.fromarray(np.uint8(visible * 255), mode="L").save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Isola a compressão e reconstrução do AEKL.")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "aekl-isolated")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    device = choose_device("auto")
    stage1, _ = load_stage1(device)
    cases = first_valid_cases(args.count)
    records, all_latents = [], []

    for index, case_id in enumerate(cases, start=1):
        print(f"Caso {index}/{len(cases)}: {case_id}")
        case_dir = args.output_dir / f"caso-{index}"
        case_dir.mkdir(parents=True, exist_ok=True)
        original_path = DATA_ROOT / "Dsr" / f"{case_id}.tiff"
        mask_path = DATA_ROOT / "Dgen" / f"{case_id}_mask.tiff"
        original = np.asarray(tifffile.imread(original_path), dtype=np.float32)
        image = torch.from_numpy(original).unsqueeze(0).unsqueeze(0).to(device)

        torch.manual_seed(args.seed)
        started = time.perf_counter()
        with torch.inference_mode():
            latent_mean, latent_sigma = stage1.encode(image)
            latent = stage1.sampling(latent_mean, latent_sigma)
            reconstruction = stage1.decode(latent)
        elapsed = time.perf_counter() - started
        reconstructed = reconstruction[0, 0].detach().float().cpu().numpy().astype(np.float32)
        latent_cpu = latent.detach().float().cpu().numpy()
        all_latents.append(latent_cpu.ravel())

        reconstructed_path = case_dir / "aekl_reconstruction.tiff"
        tifffile.imwrite(reconstructed_path, reconstructed)
        low, high = (float(value) for value in np.percentile(original, (1, 99)))
        original_preview = case_dir / "original.png"
        reconstructed_preview = case_dir / "aekl_reconstruction.png"
        save_preview(original, original_preview, low, high)
        save_preview(reconstructed, reconstructed_preview, low, high)

        evaluation_path = case_dir / "avaliacao.json"
        subprocess.run([
            str(EVALUATOR_PYTHON), "-m", "frameworks.texture_evaluator.evaluate_one",
            "--original", str(original_path),
            "--synthetic", str(reconstructed_path),
            "--mask", str(mask_path),
            "--output", str(evaluation_path),
        ], check=True, cwd=EVALUATOR_REPO)
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        records.append({
            "case_id": case_id,
            "files": {
                "original": str(original_path.resolve()),
                "reconstruction": str(reconstructed_path.resolve()),
                "original_preview": str(original_preview.resolve()),
                "reconstruction_preview": str(reconstructed_preview.resolve()),
            },
            "elapsed_seconds": round(elapsed, 3),
            "latent_std": float(latent_cpu.std()),
            "evaluation": evaluation,
        })

    measurements = [record["evaluation"]["measurements"] for record in records]
    verdicts = [record["evaluation"]["verdicts"] for record in records]
    combined_latents = np.concatenate(all_latents)
    payload = {
        "experiment": "Reconstrução isolada: original → AEKL → reconstrução, sem LDM.",
        "seed": args.seed,
        "aggregate": {
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
            "latent_std": float(combined_latents.std()),
            "estimated_scale_factor": float(1.0 / combined_latents.std()),
        },
        "cases": records,
    }
    result_path = args.output_dir / "resultado.json"
    result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Resultado salvo em: {result_path}")


if __name__ == "__main__":
    main()
