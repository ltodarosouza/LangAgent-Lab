import argparse
from pathlib import Path

from models import DEFAULT_AEKL, DEFAULT_CONFIG, DEFAULT_LDM, choose_device, load_models


def main() -> None:
    parser = argparse.ArgumentParser(description="Confere os pesos e a arquitetura dos dois modelos.")
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "mps"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--aekl", type=Path, default=DEFAULT_AEKL)
    parser.add_argument("--ldm", type=Path, default=DEFAULT_LDM)
    args = parser.parse_args()

    device = choose_device(args.device)
    stage1, diffusion, _ = load_models(device, args.config, args.aekl, args.ldm)

    print(f"Dispositivo: {device}")
    print(f"AEKL carregado: {sum(p.numel() for p in stage1.parameters()):,} parâmetros")
    print(f"LDM carregado:  {sum(p.numel() for p in diffusion.parameters()):,} parâmetros")
    print("Resultado: pesos e arquitetura compatíveis.")


if __name__ == "__main__":
    main()
