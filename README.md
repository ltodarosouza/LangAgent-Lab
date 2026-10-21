# lung-agent-lab

Ambiente controlado para experimentar parâmetros do gerador de tomografias
pulmonares. Este repositório gera imagens e consome o JSON produzido pelo
framework externo `synthetic-lung-ct-evaluation`.

## Preparação em uma máquina nova

Clone este repositório com Git LFS instalado e execute:

```bash
./tools/bootstrap.sh
```

O script baixa os dois checkpoints, confere seus hashes, prepara os ambientes,
clona o avaliador público ao lado deste repositório quando necessário, monta os
37 casos DSR válidos e roda apenas testes de software. Ele não gera imagens e
não treina modelos.

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

## Dataset DSR válido

A pasta original do DSR contém 100 pares, mas o protocolo operacional do
avaliador aceita 37 cortes. Para montar uma visão local somente com esses
originais e suas máscaras:

```bash
.venv/bin/python tools/prepare_dsr_dataset.py
```

O resultado fica em `data/dsr-valid/`, com `originals/`, `masks/` e um
`manifest.json`. As imagens são links para o repositório avaliador: não são
duplicadas e não são enviadas ao GitHub.

## Avaliação real em lote

O lote rápido usa sempre os mesmos 7 cortes. O lote completo usa os 37 cortes
válidos. Cada execução salva `report.json` com todas as métricas de todas as
imagens, `report.md` com o resumo e prévias visuais dos pares.

```bash
.venv/bin/python generator/run_batch.py \
  --scope quick \
  --config workspace/candidate.json \
  --output-dir runs/real/baseline-quick

.venv/bin/python generator/run_batch.py \
  --scope full \
  --config workspace/candidate.json \
  --reuse-report runs/real/baseline-quick/report.json \
  --output-dir runs/real/baseline-full
```

Para comparar uma nova tentativa, acrescente `--compare-to` apontando para o
melhor relatório anterior do mesmo tamanho. A comparação primeiro evita novas
rejeições e depois usa a nota como resumo; o agente também deve ler todas as
métricas por imagem.

O prompt pronto para entregar a qualquer agente está em `AGENT_PROMPT.md`. O
campo `MAX_CONFIGURATIONS` controla quantas configurações ele pode testar.

## Fronteira entre os projetos

- **lung-agent-lab:** modelos, geração, busca de parâmetros e histórico dos experimentos.
- **synthetic-lung-ct-evaluation:** métricas, calibração e decisão sobre brilho e textura.

O agente pode alterar este laboratório, mas não as regras do avaliador durante
uma busca. Os dois checkpoints congelados são distribuídos por Git LFS. Imagens
médicas e resultados de execução não são enviados por este repositório.

## Organização local esperada

Os dois repositórios devem ficar lado a lado:

```text
dev/
├── lung-agent-lab/
└── synthetic-lung-ct-evaluation/
```

Os pesos congelados ficam em `models/` com estes nomes:

- `model_aekl_best_4_latent_new_lung.pth`
- `model_ldm_pulmao_Dsr_best.pth`

## Preparação

```bash
uv venv --python 3.10 .venv
uv pip install --python .venv/bin/python -r generator/requirements.txt
```

O caminho recomendado é `./tools/bootstrap.sh`, que também prepara o avaliador,
o dataset e o Git LFS.

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

O mock não escolhe parâmetros reais automaticamente. A busca real usa
`generator/run_batch.py` e o fluxo definido em `AGENT_PROMPT.md`.

Se os repositórios não estiverem lado a lado, configure
`TEXTURE_EVALUATOR_REPO` com o caminho do avaliador.
