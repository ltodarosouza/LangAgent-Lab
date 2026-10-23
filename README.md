# lung-agent-lab

Ambiente controlado para experimentar parâmetros do gerador de tomografias
pulmonares. Este repositório gera imagens e consome o JSON produzido pelo
framework externo `synthetic-lung-ct-evaluation`.

## Preparação em uma máquina nova

Pré-requisito: o [Git LFS](https://git-lfs.com/), porque os dois checkpoints em
`models/` só existem como arquivos LFS. É uma instalação única por máquina:

- macOS com Homebrew: `brew install git-lfs`
- Ubuntu/Debian: `sudo apt install git-lfs`
- Windows: já vem com o Git for Windows
- Sem gerenciador de pacotes: baixe o binário em https://git-lfs.com/ e rode
  `sudo ./install.sh` dentro da pasta extraída

Também é preciso ter o [`uv`](https://docs.astral.sh/uv/) ou o Python 3.10.

Clone este repositório com o Git LFS instalado e execute:

```bash
./tools/bootstrap.sh
```

O script baixa os dois checkpoints, confere seus hashes, prepara os ambientes,
clona o avaliador público ao lado deste repositório quando necessário (já na tag
`juiz-v1`), monta os 37 casos DSR válidos e roda apenas testes de software. Ele
não gera imagens e não treina modelos. Se o avaliador já estiver clonado, o
script não o altera: apenas avisa quando ele não está na tag `juiz-v1`.

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
avaliador aceita 37 cortes. A lista vem da chave `originals` da régua congelada
`frameworks/texture_evaluator/calibracao/dsr-v1.json` do avaliador (tag
`juiz-v1`), que é versionada; não é preciso ter `outputs/` no avaliador. Para
montar uma visão local somente com esses originais e suas máscaras:

```bash
.venv/bin/python tools/prepare_dsr_dataset.py
```

O resultado fica em `data/dsr-valid/`, com `originals/`, `masks/` e um
`manifest.json`, que guarda também o hash dos pixels de cada original registrado
na calibração. As imagens são links para o repositório avaliador: não são
duplicadas e não são enviadas ao GitHub.

## Avaliação real em lote

A busca usa um funil cumulativo: 5 cortes fixos de triagem, depois 10 cortes e,
somente após duas confirmações de melhora, os 37 válidos. Cada etapa reutiliza
as imagens da anterior, portanto uma configuração promovida gera 5 + 5 + 27,
sem repetir trabalho. Cada execução salva `report.json` com todas as métricas de todas as
imagens, `report.md` com o resumo e prévias visuais dos pares, e `boletim.json`,
a nota do avaliador na régua congelada `juiz-v1` (formato em
`docs/contracts/boletim.md` do avaliador). Com `--compare-to`, o boletim também
compara o lote, corte a corte, com o boletim do lote de referência. Para
refazer o boletim de um lote já gerado:

```bash
.venv/bin/python generator/boletim.py --run-dir runs/real/baseline-full
```

```bash
.venv/bin/python generator/run_batch.py \
  --scope screen \
  --config workspace/candidate.json \
  --output-dir runs/real/baseline-screen

.venv/bin/python generator/run_batch.py \
  --scope quick \
  --config workspace/candidate.json \
  --reuse-report runs/real/baseline-screen/report.json \
  --output-dir runs/real/baseline-quick

.venv/bin/python generator/run_batch.py \
  --scope full \
  --config workspace/candidate.json \
  --reuse-report runs/real/baseline-quick/report.json \
  --output-dir runs/real/baseline-full
```

Para comparar uma nova tentativa, comece em `--scope screen` e acrescente
`--baseline` apontando para o relatório do baseline do mesmo tamanho. Só avance
quando o relatório disser `melhor`; no lote completo, acrescente também
`--compare-to` com o melhor relatório completo atual. A régua é a mesma nos dois
tamanhos: para cada distância até a original (`glcm_contrast_z`,
`glcm_energy_z`, `wavelet_fine_z`, `wavelet_coarse_z`, `wavelet_entropy_z`,
`wavelet_ll_z`, `nex_delta`), a melhora é `1 − média|candidato| /
média|baseline|` nos mesmos casos, com teto de 50% por métrica. A média das 7
precisa chegar a 15% para o veredito `melhor`; no lote completo, ela também
precisa superar a da melhor atual. Mais rejeições ou pares fora de `ok` que o
baseline dão `pior`. A nota continua no relatório, só como informação; o agente
também deve ler todas as métricas por imagem.

O prompt pronto para entregar a qualquer agente está em `AGENT_PROMPT.md`. O
campo `MAX_CONFIGURATIONS` controla quantas configurações ele pode testar.
O raciocínio esperado para escolher parâmetros está em `SEARCH_STRATEGY.md`.
Além de `steps` e `noise_level`, a busca pode controlar `eta`,
`latent_noise_scale` e `conditioning_noise_scale`; sampler, seed e scale factor
continuam congelados para manter comparações válidas.

### Rodar com o Codex

1. Abra a pasta `lung-agent-lab` no Codex.
2. Crie uma conversa nova nessa pasta.
3. Abra `AGENT_PROMPT.md`, copie todo o texto entre as linhas `---` e cole na
   conversa.
4. Se quiser, altere apenas `MAX_CONFIGURATIONS` antes de enviar.
5. Envie o prompt. O Codex lerá `AGENTS.md`, o estado da busca e começará pela
   próxima hipótese, sem refazer o baseline nem a melhor versão atual.

Não execute `tools/agente.sh` para usar o Codex: esse script abre o Claude Code.
No Codex, basta abrir a pasta correta e enviar o prompt completo.

### Continuar a partir do melhor resultado já encontrado

O baseline continua sendo a régua fixa, mas uma nova busca pode começar dos
parâmetros e do relatório da melhor execução completa anterior. Antes de abrir
o agente, rode como humano:

```bash
.venv/bin/python tools/select_starting_point.py \
  --from-run runs/real/candidate-01-full
```

O comando encontra o lote rápido correspondente, valida os mesmos casos,
encontra também a triagem de 5 e o lote rápido correspondentes, atualiza
`workspace/candidate.json`, cria o estado local
`workspace/search_state.json` e arquiva o orçamento anterior. Ele não gera
imagens. Sem `--from-run`, o mesmo comando apenas mostra a seleção atual.

A partir daí, o baseline continua fixo em `baseline-screen/quick/full`, enquanto o
relatório escolhido passa a ser a melhor atual usada por `--compare-to`. A
configuração escolhida conta como a primeira do novo orçamento.

## Travas do agente no Claude Code

Para usar o Claude Code com as travas técnicas, abra-o por este script depois do
`bootstrap.sh`:

```bash
MAX_CONFIGURATIONS=10 ./tools/agente.sh
```

Ele gera `.agente/settings.json` e abre o Claude Code com esse arquivo. Só essa
sessão fica travada; sessões abertas de outro jeito nesta pasta continuam livres.
As regras estão em `tools/trava_agente.py`:

- **Permissões:** Edit/Write negados em `agent/`, `generator/`, `configs/`,
  `tests/`, `tools/`, `models/`, `data/`, `.git/`, nas regras do projeto e no
  avaliador; Read negado nos documentos do avaliador que contam resultados.
- **Sandbox** (Bash e tudo o que ele chama, inclusive Python escrito pelo
  agente): as mesmas negações no sistema de arquivos, rede só para arXiv e PyPI,
  nenhum comando fora do sandbox.
- **Hook PreToolUse:** escrita só em `workspace/candidate.json`, `runs/`,
  `literatura/notas/` e `CADERNO.md`, que só aceita acréscimos;
  avaliador fora do alcance; Python só por `generator/run_batch.py`, pelo mock e
  pelos testes. O lote real só passa pelo orçamento: até `MAX_CONFIGURATIONS`
  configurações distintas, seguindo obrigatoriamente o funil 5 → 10 → 37 e
  avançando apenas após `melhor` contra o baseline.
  O registro fica em `.agente/orcamento.jsonl`; use
  `tools/select_starting_point.py` para começar uma busca nova preservando o
  orçamento anterior em `.agente/historico/`.

Limites conhecidos: um agente decidido ainda consegue ler o código do avaliador
pelo Python que roda a avaliação, e o filtro de comandos do hook pode ser
contornado com ofuscação. A trava definitiva é a do sistema operacional, com o
avaliador e os dados pertencendo a outro usuário, prevista para a máquina com GPU.

## Caderno e literatura

`CADERNO.md` guarda uma entrada por tentativa (hipótese, mudança, resultado e
lição), a começar pela linha de base `000`. Nada é apagado: correções viram
entradas novas. `literatura/` tem o índice dos artigos que o agente pode
consultar; os PDFs ficam em `literatura/artigos/` só na máquina local, e as
anotações do agente em `literatura/notas/`.

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

A avaliação usa como `--history` a régua congelada
`frameworks/texture_evaluator/calibracao/dsr-v1.json` do avaliador. Para usar
outra calibração, configure `TEXTURE_EVALUATOR_HISTORY` com o caminho do JSON
(ele precisa das chaves `calibration` e `originals`).
