#!/usr/bin/env bash
# Roda GP-BO e depois Nelder-Mead no backend real, um de cada vez (GPU única).
# Só com autorização humana para gerar na GPU. Retoma de onde parou: basta rodar de
# novo. Cada método tenta até 3 vezes se o processo cair e para de vez na terceira.
#
# Variáveis (padrões para rodar a partir de um worktree do lab):
#   LAB_MAIN     checkout com data/, runs/real (baselines) e .venv do gerador
#   GEN_PYTHON   Python do gerador (torch + monai), usado por run_batch.py
#   OPT_PYTHON   Python do otimizador (tools/requirements-otimizador.txt)
#   TEXTURE_EVALUATOR_REPO  clone do avaliador congelado (juiz-v1)
#   METHODS      padrão "gp nm"
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB_MAIN="${LAB_MAIN:-$repo_root}"
GEN_PYTHON="${GEN_PYTHON:-$LAB_MAIN/.venv/bin/python}"
OPT_PYTHON="${OPT_PYTHON:-$repo_root/.venv/bin/python}"
export TEXTURE_EVALUATOR_REPO="${TEXTURE_EVALUATOR_REPO:-$(cd "$LAB_MAIN/.." && pwd)/synthetic-lung-ct-evaluation}"
runs_real="$LAB_MAIN/runs/real"

for method in ${METHODS:-gp nm}; do
  for attempt in 1 2 3; do
    echo "=== $(date '+%F %T') método $method, tentativa $attempt"
    if "$OPT_PYTHON" "$repo_root/tools/otimizador_real.py" otimizar --method "$method" --backend real \
        --confirmo-gpu --python "$GEN_PYTHON" --out-root "$runs_real" --baseline-dir "$runs_real"; then
      break
    fi
    if [[ $attempt == 3 ]]; then
      echo "=== $(date '+%F %T') $method falhou 3 vezes; parando"
      exit 1
    fi
    sleep 60
  done
done
echo "=== $(date '+%F %T') fim"
