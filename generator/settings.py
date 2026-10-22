import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVALUATOR_REPO = ROOT.parent / "synthetic-lung-ct-evaluation"
EVALUATOR_REPO = Path(os.environ.get("TEXTURE_EVALUATOR_REPO", DEFAULT_EVALUATOR_REPO)).resolve()
# Não usar resolve() aqui: o executável do venv é um symlink e precisa ser
# chamado pelo caminho do ambiente para ativar seus pacotes.
EVALUATOR_PYTHON = Path(os.environ.get("TEXTURE_EVALUATOR_PYTHON", EVALUATOR_REPO / ".venv" / "bin" / "python"))
DATA_ROOT = Path(os.environ.get("LUNG_DATA_ROOT", EVALUATOR_REPO / "dados")).resolve()
# Régua congelada do avaliador (tag juiz-v1): versionada, existe num clone novo.
DEFAULT_EVALUATOR_HISTORY = EVALUATOR_REPO / "frameworks" / "texture_evaluator" / "calibracao" / "dsr-v1.json"
EVALUATOR_HISTORY = Path(os.environ.get("TEXTURE_EVALUATOR_HISTORY", DEFAULT_EVALUATOR_HISTORY)).resolve()


def ensure_evaluator_ready(
    history: Path = EVALUATOR_HISTORY,
    evaluator_python: Path = EVALUATOR_PYTHON,
    evaluator_repo: Path = EVALUATOR_REPO,
) -> None:
    """Falha antes da geração quando o juiz congelado está incompleto."""
    if not history.is_file():
        raise RuntimeError(
            f"calibração congelada ausente: {history}\n"
            "rode ./tools/bootstrap.sh antes de iniciar a busca"
        )
    if not evaluator_python.is_file():
        raise RuntimeError(f"Python do avaliador ausente: {evaluator_python}; rode ./tools/bootstrap.sh")
    entrypoint = evaluator_repo / "frameworks" / "texture_evaluator" / "evaluate_one.py"
    if not entrypoint.is_file():
        raise RuntimeError(f"avaliador incompleto: {entrypoint}; rode ./tools/bootstrap.sh")
    payload = json.loads(history.read_text(encoding="utf-8"))
    missing = [key for key in ("calibration", "originals") if not payload.get(key)]
    if missing:
        raise RuntimeError(f"calibração inválida; campos ausentes: {', '.join(missing)}")


def valid_case_ids() -> list[str]:
    """Casos DSR válidos, em ordem alfabética, tirados de `originals` na calibração."""
    originals = json.loads(EVALUATOR_HISTORY.read_text(encoding="utf-8")).get("originals")
    if not originals:
        raise RuntimeError(f"calibração sem a chave 'originals': {EVALUATOR_HISTORY}")
    return sorted(originals)
