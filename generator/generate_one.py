import argparse
import json
import time
from pathlib import Path

import numpy as np
import tifffile
import torch
import torch.nn.functional as F
from generative.networks.schedulers import DDIMScheduler
from tqdm import tqdm

from models import DEFAULT_AEKL, DEFAULT_CONFIG, DEFAULT_LDM, choose_device, load_models


def array_stats(array: np.ndarray) -> dict[str, float | list[int] | str]:
    return {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "min": float(array.min()),
        "max": float(array.max()),
        "mean": float(array.mean()),
        "std": float(array.std()),
    }


def generate_image(
    source_path: Path,
    output_path: Path,
    stage1,
    diffusion,
    config,
    device: torch.device,
    *,
    steps: int,
    noise_level: int,
    scale_factor: float,
    seed: int,
) -> dict:
    """Gera uma TIFF reutilizando modelos já carregados e devolve os metadados."""
    latent_size = tuple(int(value) for value in config.inference.latent_size)
    if not 0 <= noise_level < int(config.ldm.num_class_embeds):
        raise ValueError(f"noise-level deve ficar entre 0 e {int(config.ldm.num_class_embeds) - 1}")

    source = np.asarray(tifffile.imread(source_path), dtype=np.float32).squeeze()
    if source.ndim != 2:
        raise ValueError(f"Esperada uma imagem 2D; recebida forma {source.shape}")

    low_res = torch.from_numpy(source).unsqueeze(0).unsqueeze(0)
    low_res = F.interpolate(low_res, size=latent_size, mode="bilinear", align_corners=False).to(device)
    generator = torch.Generator(device="cpu").manual_seed(seed)
    latents = torch.randn((1, int(config.ldm.out_channels), *latent_size), generator=generator).to(device)
    low_res_noise = torch.randn((1, 1, *latent_size), generator=generator).to(device)
    noise_tensor = torch.tensor([noise_level], dtype=torch.long, device=device)

    scheduler = DDIMScheduler(
        num_train_timesteps=int(config.scheduler.num_train_timesteps),
        schedule=str(config.scheduler.schedule),
        beta_start=float(config.scheduler.beta_start),
        beta_end=float(config.scheduler.beta_end),
        prediction_type=str(config.scheduler.prediction_type),
        clip_sample=False,
    )
    scheduler.set_timesteps(steps)
    noisy_low_res = scheduler.add_noise(low_res, low_res_noise, noise_tensor)

    started = time.perf_counter()
    with torch.inference_mode():
        for timestep in tqdm(scheduler.timesteps, desc=f"Difusão ({steps} passos)"):
            timestep_value = int(timestep)
            timestep_tensor = torch.tensor([timestep_value], dtype=torch.long, device=device)
            predicted_noise = diffusion(
                x=torch.cat((latents, noisy_low_res), dim=1),
                timesteps=timestep_tensor,
                class_labels=noise_tensor,
            )
            latents, _ = scheduler.step(predicted_noise, timestep_value, latents)
        generated = stage1.decode_stage_2_outputs(latents / scale_factor)

    result = generated[0, 0].detach().float().cpu().numpy().astype(np.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(output_path, result)
    metadata = {
        "input": str(source_path.resolve()),
        "output": str(output_path.resolve()),
        "device": str(device),
        "parameters": {"steps": steps, "noise_level": noise_level, "scale_factor": scale_factor, "seed": seed},
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "input_stats": array_stats(source),
        "output_stats": array_stats(result),
    }
    output_path.with_suffix(output_path.suffix + ".json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera uma imagem sintética a partir de uma TIFF original.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "mps"))
    parser.add_argument("--steps", type=int)
    parser.add_argument("--noise-level", type=int)
    parser.add_argument("--scale-factor", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--aekl", type=Path, default=DEFAULT_AEKL)
    parser.add_argument("--ldm", type=Path, default=DEFAULT_LDM)
    args = parser.parse_args()

    device = choose_device(args.device)
    stage1, diffusion, config = load_models(device, args.config, args.aekl, args.ldm)
    inference = config.inference
    steps = args.steps if args.steps is not None else int(inference.num_inference_steps)
    noise_level = args.noise_level if args.noise_level is not None else int(inference.noise_level)
    scale_factor = args.scale_factor if args.scale_factor is not None else float(inference.scale_factor)
    seed = args.seed if args.seed is not None else int(inference.seed)
    generate_image(
        args.input, args.output, stage1, diffusion, config, device,
        steps=steps, noise_level=noise_level, scale_factor=scale_factor, seed=seed,
    )
    metadata_path = args.output.with_suffix(args.output.suffix + ".json")
    print(f"Imagem salva em: {args.output}")
    print(f"Parâmetros salvos em: {metadata_path}")


if __name__ == "__main__":
    main()
