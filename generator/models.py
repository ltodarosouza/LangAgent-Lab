from pathlib import Path

import torch
from generative.networks.nets import AutoencoderKL, DiffusionModelUNet
from omegaconf import OmegaConf

from settings import ROOT

DEFAULT_CONFIG = Path(__file__).with_name("model_config.yaml")
DEFAULT_AEKL = ROOT / "models" / "model_aekl_best_4_latent_new_lung.pth"
DEFAULT_LDM = ROOT / "models" / "model_ldm_pulmao_Dsr_best.pth"


def load_config(path: Path = DEFAULT_CONFIG):
    return OmegaConf.load(path)


def load_stage1(
    device: torch.device,
    config_path: Path = DEFAULT_CONFIG,
    aekl_path: Path = DEFAULT_AEKL,
):
    config = load_config(config_path)
    stage1 = AutoencoderKL(**OmegaConf.to_container(config.stage1))
    stage1.load_state_dict(torch.load(aekl_path, map_location="cpu", weights_only=True), strict=True)
    stage1.eval().to(device)
    return stage1, config


def load_models(
    device: torch.device,
    config_path: Path = DEFAULT_CONFIG,
    aekl_path: Path = DEFAULT_AEKL,
    ldm_path: Path = DEFAULT_LDM,
):
    stage1, config = load_stage1(device, config_path, aekl_path)

    diffusion = DiffusionModelUNet(**OmegaConf.to_container(config.ldm))
    diffusion.load_state_dict(torch.load(ldm_path, map_location="cpu", weights_only=True), strict=True)
    diffusion.eval().to(device)

    return stage1, diffusion, config


def choose_device(requested: str = "auto") -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
