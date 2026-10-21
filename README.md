# LungAgent-Lab

Ambiente controlado para experimentar parâmetros do gerador de tomografias
pulmonares. Este repositório gera imagens e consome o JSON produzido pelo
framework externo `synthetic-lung-ct-evaluation`.

## Começo rápido: laboratório mockado

O modo mock imita o ciclo **parâmetros → geração → avaliação → nota**, mas não
carrega os modelos nem imagens médicas. Ele serve para confirmar, em segundos,
que o agente sabe experimentar sem alterar as regras da avaliação.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m agent.run_experiment \
  --backend mock \
  --config configs/baseline.json
```

Para entregar o laboratório ao agente, indique a missão em `workspace/TASK.md`.
Durante a busca ele pode mudar somente `workspace/candidate.json` e executar:

```bash
.venv/bin/python -m agent.run_experiment \
  --backend mock \
  --config workspace/candidate.json
```

Cada tentativa ganha uma pasta própria em `runs/`, e o resumo de todas fica em
`runs/history.jsonl`. Esses resultados permanecem apenas na máquina local.

## Fronteira entre os projetos

- **LungAgent-Lab:** modelos, geração, busca de parâmetros e histórico dos experimentos.
- **synthetic-lung-ct-evaluation:** métricas, calibração e decisão sobre brilho e textura.

O agente pode alterar este laboratório, mas não as regras do avaliador durante
uma busca. Pesos, imagens médicas e resultados não são enviados ao GitHub.

## Organização local esperada

Os dois repositórios devem ficar lado a lado:

```text
dev/
├── LungAgent-Lab/
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

O mock não escolhe parâmetros reais automaticamente. Depois que o fluxo do
agente estiver aprovado, conectaremos a mesma lógica ao ciclo completo acima.

Se os repositórios não estiverem lado a lado, configure
`TEXTURE_EVALUATOR_REPO` com o caminho do avaliador.
