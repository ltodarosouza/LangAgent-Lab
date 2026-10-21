# LangAgent-Lab

Ambiente controlado para experimentar parâmetros do gerador de tomografias
pulmonares. Este repositório gera imagens e consome o JSON produzido pelo
framework externo `synthetic-lung-ct-evaluation`.

## Fronteira entre os projetos

- **LangAgent-Lab:** modelos, geração, busca de parâmetros e histórico dos experimentos.
- **synthetic-lung-ct-evaluation:** métricas, calibração e decisão sobre brilho e textura.

O agente pode alterar este laboratório, mas não as regras do avaliador durante
uma busca. Pesos, imagens médicas e resultados não são enviados ao GitHub.

## Organização local esperada

Os dois repositórios devem ficar lado a lado:

```text
dev/
├── LangAgent-Lab/
└── synthetic-lung-ct-evaluation/
```

Os pesos locais ficam em `models/` com estes nomes:

- `model_aekl_best_4_latent_new_lung.pth`
- `model_ldm_pulmao_Dsr_best.pth`

## Preparação

```bash
uv venv --python 3.10 .venv
uv pip install --python .venv/bin/python -r generator/requirements.txt
```

## Teste rápido dos modelos

```bash
.venv/bin/python generator/smoke_test.py
```

## Ciclo completo

```bash
.venv/bin/python generator/run_cycle.py \
  "../synthetic-lung-ct-evaluation/dados/Dsr/IMAGEM.tiff" \
  --steps 25
```

O ciclo valida a entrada no framework, gera a TIFF, pede a avaliação ao outro
repositório e reúne tudo em `outputs/cycles/.../resultado_completo.json`.

Se os repositórios não estiverem lado a lado, configure
`TEXTURE_EVALUATOR_REPO` com o caminho do avaliador.
