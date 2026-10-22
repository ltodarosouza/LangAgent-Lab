"""Prepara localmente os cortes DSR aceitos pelo framework de avaliação."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVALUATOR = ROOT.parent / "synthetic-lung-ct-evaluation"
DEFAULT_TARGET = ROOT / "data" / "dsr-valid"
CALIBRATION = Path("frameworks") / "texture_evaluator" / "calibracao" / "dsr-v1.json"


def originals_from_calibration(calibration: Path) -> dict[str, str]:
    """Lê os casos válidos (case_id -> hash dos pixels) da régua congelada."""
    originals = json.loads(calibration.read_text(encoding="utf-8")).get("originals")
    if not originals:
        raise RuntimeError(f"nenhum caso em 'originals' de {calibration}")
    return originals


def link_file(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"arquivo esperado não encontrado: {source}")
    if target.is_symlink() and target.resolve() == source.resolve():
        return
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"destino já existe e aponta para outro arquivo: {target}")
    target.symlink_to(source)


def prepare(evaluator: Path, target: Path) -> dict:
    calibration = evaluator / CALIBRATION
    originals_source = evaluator / "dados" / "Dsr"
    masks_source = evaluator / "dados" / "Dgen"
    originals = originals_from_calibration(calibration)

    originals_target = target / "originals"
    masks_target = target / "masks"
    originals_target.mkdir(parents=True, exist_ok=True)
    masks_target.mkdir(parents=True, exist_ok=True)

    cases = []
    for case_id in sorted(originals):
        original = originals_source / f"{case_id}.tiff"
        mask = masks_source / f"{case_id}_mask.tiff"
        link_file(original, originals_target / original.name)
        link_file(mask, masks_target / mask.name)
        cases.append({
            "case_id": case_id,
            "original": f"originals/{original.name}",
            "mask": f"masks/{mask.name}",
            "pixel_sha1": originals[case_id],
        })

    manifest = {
        "schema_version": 1,
        "selection_source": str(CALIBRATION),
        "description": "DSR cases accepted by the evaluator's operational validation.",
        "case_count": len(cases),
        "cases": cases,
    }
    manifest_path = target / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluator", type=Path, default=DEFAULT_EVALUATOR)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()
    manifest = prepare(args.evaluator.resolve(), args.target.resolve())
    print(f"Dataset preparado: {manifest['case_count']} cortes válidos")
    print(f"Pasta: {args.target.resolve()}")


if __name__ == "__main__":
    main()
