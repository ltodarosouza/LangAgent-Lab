import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from settings import DATA_ROOT, EVALUATOR_HISTORY, EVALUATOR_PYTHON, EVALUATOR_REPO, ROOT



def main() -> None:
    parser = argparse.ArgumentParser(description="Gera uma imagem e a envia automaticamente ao avaliador.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--noise-level", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scale-factor", type=float, default=1.0)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "cycles")
    parser.add_argument("--history", type=Path, default=EVALUATOR_HISTORY)
    args = parser.parse_args()

    original = args.input.resolve()
    mask = (args.mask or DATA_ROOT / "Dgen" / f"{original.stem}_mask.tiff").resolve()
    run_name = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = args.output_root / run_name
    synthetic = run_dir / f"{original.stem}_generate.tiff"
    evaluation_path = run_dir / "avaliacao.json"

    preflight_command = [
        str(EVALUATOR_PYTHON),
        "-m", "frameworks.texture_evaluator.evaluate_one",
        "--original", str(original),
        "--mask", str(mask),
        "--validate-only",
    ]
    subprocess.run(preflight_command, check=True, cwd=EVALUATOR_REPO)

    generation_command = [
        sys.executable,
        str(ROOT / "generator" / "generate_one.py"),
        str(original),
        str(synthetic),
        "--steps", str(args.steps),
        "--noise-level", str(args.noise_level),
        "--seed", str(args.seed),
        "--scale-factor", str(args.scale_factor),
    ]
    subprocess.run(generation_command, check=True, cwd=ROOT)

    evaluation_command = [
        str(EVALUATOR_PYTHON),
        "-m", "frameworks.texture_evaluator.evaluate_one",
        "--original", str(original),
        "--synthetic", str(synthetic),
        "--mask", str(mask),
        "--history", str(args.history),
        "--output", str(evaluation_path),
    ]
    subprocess.run(evaluation_command, check=True, cwd=EVALUATOR_REPO)

    generation_path = synthetic.with_suffix(synthetic.suffix + ".json")
    generation = json.loads(generation_path.read_text(encoding="utf-8"))
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    combined = {
        "schema_version": 1,
        "run": run_name,
        "generation": generation,
        "evaluation": evaluation,
    }
    result_path = run_dir / "resultado_completo.json"
    result_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    verdicts = evaluation["verdicts"]
    print(f"Ciclo completo salvo em: {run_dir}")
    print(f"Final: {verdicts['final']} | brilho: {verdicts['brightness']} | textura: {verdicts['texture']}")
    print(f"JSON completo: {result_path}")


if __name__ == "__main__":
    main()
