import argparse
import json
from pathlib import Path

import numpy as np
import tifffile
import torch
import torch.nn.functional as F
from generative.networks.schedulers import DDIMScheduler
from PIL import Image
from tqdm import tqdm

from models import choose_device, load_models


def save_png(array: np.ndarray, path: Path, low: float, high: float) -> None:
    visible = np.clip((array - low) / max(high - low, 1e-8), 0, 1)
    Image.fromarray(np.uint8(visible * 255), mode="L").save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Salva etapas reais do denoise para fins didáticos.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--noise-level", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scale-factor", type=float, default=1.0)
    args = parser.parse_args()

    device = choose_device("auto")
    stage1, diffusion, config = load_models(device)
    latent_size = tuple(int(value) for value in config.inference.latent_size)
    original = np.asarray(tifffile.imread(args.input), dtype=np.float32).squeeze()
    low, high = (float(v) for v in np.percentile(original, (1, 99)))
    low_res = F.interpolate(
        torch.from_numpy(original).unsqueeze(0).unsqueeze(0),
        size=latent_size,
        mode="bilinear",
        align_corners=False,
    ).to(device)

    generator = torch.Generator(device="cpu").manual_seed(args.seed)
    latents = torch.randn((1, int(config.ldm.out_channels), *latent_size), generator=generator).to(device)
    low_res_noise = torch.randn((1, 1, *latent_size), generator=generator).to(device)
    noise_level = torch.tensor([args.noise_level], dtype=torch.long, device=device)
    scheduler = DDIMScheduler(
        num_train_timesteps=int(config.scheduler.num_train_timesteps),
        schedule=str(config.scheduler.schedule),
        beta_start=float(config.scheduler.beta_start),
        beta_end=float(config.scheduler.beta_end),
        prediction_type=str(config.scheduler.prediction_type),
        clip_sample=False,
    )
    scheduler.set_timesteps(args.steps)
    noisy_low_res = scheduler.add_noise(low_res, low_res_noise, noise_level)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_png(original, args.output_dir / "original.png", low, high)
    guide = F.interpolate(low_res, size=original.shape, mode="bilinear", align_corners=False)[0, 0].cpu().numpy()
    save_png(guide, args.output_dir / "guide.png", low, high)

    checkpoints = sorted({0, 1, round(args.steps * .2), round(args.steps * .4), round(args.steps * .6), round(args.steps * .8), args.steps})
    stages = []

    def capture(completed: int) -> None:
        decoded = stage1.decode_stage_2_outputs(latents / args.scale_factor)
        image = decoded[0, 0].detach().float().cpu().numpy()
        filename = f"step-{completed:02d}.png"
        save_png(image, args.output_dir / filename, low, high)
        stages.append({"completed": completed, "file": filename})

    with torch.inference_mode():
        capture(0)
        for completed, timestep in enumerate(tqdm(scheduler.timesteps, desc="Denoise didático"), start=1):
            timestep_value = int(timestep)
            model_input = torch.cat((latents, noisy_low_res), dim=1)
            predicted_noise = diffusion(
                x=model_input,
                timesteps=torch.tensor([timestep_value], dtype=torch.long, device=device),
                class_labels=noise_level,
            )
            latents, _ = scheduler.step(predicted_noise, timestep_value, latents)
            if completed in checkpoints:
                capture(completed)

    manifest = {
        "input": str(args.input.resolve()),
        "steps": args.steps,
        "noise_level": args.noise_level,
        "seed": args.seed,
        "window": {"low": low, "high": high},
        "stages": stages,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
