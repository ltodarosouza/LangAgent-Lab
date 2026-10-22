#!/usr/bin/env bash
# Abre o Claude Code com as travas do agente. Só esta sessão fica travada;
# sessões abertas de outro jeito nesta pasta continuam livres.
#
#   MAX_CONFIGURATIONS=10 ./tools/agente.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

max="${MAX_CONFIGURATIONS:-10}"

if [[ ! -x .venv/bin/python || ! -f data/dsr-valid/manifest.json ]]; then
  echo "Ambiente incompleto. Rode ./tools/bootstrap.sh antes: o agente não tem rede nem escrita para isso."
  exit 1
fi

mkdir -p .agente runs
python3 tools/trava_agente.py settings --max "${max}" > .agente/settings.json
echo "Travas ativas: até ${max} configurações; orçamento em .agente/orcamento.jsonl."

exec claude --settings .agente/settings.json --permission-mode acceptEdits "$@"
