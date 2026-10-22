#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
evaluator_root="$(cd "${repo_root}/.." && pwd)/synthetic-lung-ct-evaluation"
evaluator_tag="juiz-v1"

cd "${repo_root}"

if ! command -v git-lfs >/dev/null 2>&1; then
  echo "Git LFS não está instalado. Instale-o antes de continuar: https://git-lfs.com/"
  exit 1
fi

git lfs install --local
git lfs pull --include="models/*.pth"
shasum -a 256 -c models/SHA256SUMS

if [[ ! -d "${evaluator_root}/.git" ]]; then
  git clone https://github.com/matheuscbrito/synthetic-lung-ct-evaluation.git "${evaluator_root}"
  git -C "${evaluator_root}" -c advice.detachedHead=false checkout "${evaluator_tag}"
else
  # Clone existente: busca o juiz e avança automaticamente apenas quando é seguro.
  git -C "${evaluator_root}" fetch origin --tags
  expected="$(git -C "${evaluator_root}" rev-parse -q --verify "${evaluator_tag}^{commit}" || true)"
  current="$(git -C "${evaluator_root}" rev-parse HEAD)"
  if [[ -z "${expected}" ]]; then
    echo "ERRO: o avaliador em ${evaluator_root} não possui a tag ${evaluator_tag}."
    exit 1
  elif [[ "${current}" != "${expected}" ]]; then
    if [[ -n "$(git -C "${evaluator_root}" status --porcelain)" ]]; then
      echo "ERRO: o avaliador tem alterações locais e não está na tag ${evaluator_tag}."
      echo "      Preserve essas alterações antes de atualizar ${evaluator_root}."
      exit 1
    fi
    if git -C "${evaluator_root}" merge-base --is-ancestor "${current}" "${expected}"; then
      git -C "${evaluator_root}" merge --ff-only "${evaluator_tag}"
    else
      echo "ERRO: o avaliador está em ${current:0:7}, mas o juiz exige ${expected:0:7}."
      echo "      Faça checkout da tag ${evaluator_tag} em um clone limpo."
      exit 1
    fi
  fi
fi

calibration="${evaluator_root}/frameworks/texture_evaluator/calibracao/dsr-v1.json"
if [[ ! -f "${calibration}" ]]; then
  echo "ERRO: calibração congelada ausente: ${calibration}"
  exit 1
fi

if command -v uv >/dev/null 2>&1; then
  [[ -x .venv/bin/python ]] || uv venv --python 3.10 .venv
  uv pip install --python .venv/bin/python -r generator/requirements.txt
  [[ -x "${evaluator_root}/.venv/bin/python" ]] || uv venv --python 3.10 "${evaluator_root}/.venv"
  uv pip install --python "${evaluator_root}/.venv/bin/python" -r "${evaluator_root}/wavelet/requirements.txt"
else
  if ! command -v python3.10 >/dev/null 2>&1; then
    echo "Python 3.10 ou uv é necessário para preparar os ambientes."
    exit 1
  fi
  [[ -x .venv/bin/python ]] || python3.10 -m venv .venv
  .venv/bin/python -m pip install -r generator/requirements.txt
  [[ -x "${evaluator_root}/.venv/bin/python" ]] || python3.10 -m venv "${evaluator_root}/.venv"
  "${evaluator_root}/.venv/bin/python" -m pip install -r "${evaluator_root}/wavelet/requirements.txt"
fi

.venv/bin/python tools/prepare_dsr_dataset.py
.venv/bin/python -m unittest discover -s tests -v

echo "Ambiente pronto. Nenhuma imagem foi gerada e nenhum peso foi treinado."
