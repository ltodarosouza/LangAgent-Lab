import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVALUATOR_REPO = ROOT.parent / "synthetic-lung-ct-evaluation"
EVALUATOR_REPO = Path(os.environ.get("TEXTURE_EVALUATOR_REPO", DEFAULT_EVALUATOR_REPO)).resolve()
# Não usar resolve() aqui: o executável do venv é um symlink e precisa ser
# chamado pelo caminho do ambiente para ativar seus pacotes.
EVALUATOR_PYTHON = Path(os.environ.get("TEXTURE_EVALUATOR_PYTHON", EVALUATOR_REPO / ".venv" / "bin" / "python"))
DATA_ROOT = Path(os.environ.get("LUNG_DATA_ROOT", EVALUATOR_REPO / "dados")).resolve()
EVALUATOR_HISTORY = Path(
    os.environ.get("TEXTURE_EVALUATOR_HISTORY", EVALUATOR_REPO / "outputs" / "placar" / "historico.json")
).resolve()
