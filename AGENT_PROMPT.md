# Prompt de execução do agente

Copie o texto abaixo e altere apenas `MAX_CONFIGURATIONS`.

---

Trabalhe neste repositório para encontrar parâmetros de amostragem do LDM que
melhorem a textura das tomografias pulmonares.

`MAX_CONFIGURATIONS = 10`

Antes de agir, leia `AGENTS.md`, `SEARCH_STRATEGY.md`, `README.md`, `CADERNO.md`,
`configs/real_search_space.json`, `workspace/candidate.json` e, se existir,
`workspace/search_state.json`.

O ambiente já foi preparado com `./tools/bootstrap.sh`. Durante a busca, escreva
somente em `workspace/candidate.json`, `runs/`, `literatura/notas/` e, por acréscimo,
em `CADERNO.md`. Não altere pesos, código, casos, avaliador, thresholds ou fórmula da
nota. Se uma trava impedir um passo, reporte; não tente contorná-la.

## Como raciocinar

Não faça busca aleatória, busca binária automática nem fique variando apenas `steps`.
Antes de cada configuração, leia as métricas agregadas e por imagem da melhor execução,
identifique o defeito dominante e escreva no caderno:

1. o que está ruim;
2. qual parâmetro provavelmente causa ou controla esse efeito;
3. qual mudança será feita;
4. quais métricas devem responder e em qual direção.

Use o mapa causal de `SEARCH_STRATEGY.md`. Você pode variar `steps`, `noise_level`,
`eta`, `latent_noise_scale` e `conditioning_noise_scale` dentro das faixas permitidas.
Mude uma variável por vez, salvo se justificar explicitamente uma interação. Se uma
tentativa falhar, revise a hipótese; não escolha simplesmente o meio entre dois valores.
Antes de propor qualquer valor, procure a configuração exata no caderno e nos relatórios
existentes. Não gere novamente uma configuração já medida no mesmo escopo: reutilize o
relatório e a lição registrada.

## Estado inicial

Se `workspace/search_state.json` existir, ele contém três relatórios de baseline
(`screen`, `quick`, `full`) e os três relatórios da melhor versão atual. Não regenere
esses arquivos. Comece dos parâmetros de `current_best.candidate`; eles contam como a
primeira configuração do orçamento.

Se não existir, crie o baseline cumulativo:

1. `--scope screen --config configs/baseline.json` em
   `runs/real/baseline-screen` (5 casos);
2. `--scope quick` em `runs/real/baseline-quick`, com
   `--config configs/baseline.json` e
   `--reuse-report runs/real/baseline-screen/report.json` (só gera mais 5);
3. `--scope full` em `runs/real/baseline-full`, com
   `--config configs/baseline.json` e
   `--reuse-report runs/real/baseline-quick/report.json` (só gera os 27 restantes).

Depois, trate `workspace/candidate.json` como a primeira configuração candidata
e compare-a com esses três baselines. No primeiro lote completo, use
`runs/real/baseline-full/report.json` também como `--compare-to`.
Enquanto ainda não houver outra melhor, os caminhos `CAMINHO_MELHOR_SCREEN`,
`CAMINHO_MELHOR_QUICK` e `CAMINHO_MELHOR_FULL` são os próprios baselines.

## Funil de cada configuração

Salve cada tentativa em pastas novas com o mesmo número, por exemplo:
`candidate-02-screen`, `candidate-02-quick` e `candidate-02-full`.

1. Rode 5 casos:
   `.venv/bin/python generator/run_batch.py --scope screen --config workspace/candidate.json --baseline CAMINHO_BASELINE_SCREEN --compare-to CAMINHO_MELHOR_SCREEN --output-dir runs/real/candidate-02-screen`
2. Somente se o relatório disser `melhor`, rode 10 reutilizando os 5:
   `.venv/bin/python generator/run_batch.py --scope quick --config workspace/candidate.json --reuse-report runs/real/candidate-02-screen/report.json --baseline CAMINHO_BASELINE_QUICK --compare-to CAMINHO_MELHOR_QUICK --output-dir runs/real/candidate-02-quick`
3. Somente se também disser `melhor`, rode 37 reutilizando os 10:
   `.venv/bin/python generator/run_batch.py --scope full --config workspace/candidate.json --reuse-report runs/real/candidate-02-quick/report.json --baseline CAMINHO_BASELINE_FULL --compare-to CAMINHO_MELHOR_FULL --output-dir runs/real/candidate-02-full`

Use os caminhos exatos de `workspace/search_state.json` quando ele existir. Se uma
execução for interrompida, repita o mesmo comando e a mesma pasta; os casos prontos serão
reutilizados.

O veredito compara sete distâncias até a imagem original: GLCM contraste e energia,
Wavelet 2 px, 4 px, entropia e LL, e NEx. Para dizer `melhor`, a candidata precisa ter
melhora média contra o baseline acima da melhor atual, vencer em mais cortes do que
perder pela distância conjunta das sete métricas e não aumentar rejeições nem pares inválidos. Os 15% são uma
meta forte informada separadamente por `target_reached`; não são uma barreira para
investigar ou adotar uma melhora incremental. A nota agregada é apenas um resumo: leia
métricas, casos e prévias. Uma configuração só vira a nova melhor operacional depois de
confirmar essa superioridade nos 37 casos.

Registre todas as tentativas no `CADERNO.md`, inclusive as ruins. Pare ao atingir
`MAX_CONFIGURATIONS`, quando não houver hipótese segura restante ou quando não houver
melhora defensável. Ao terminar, informe parâmetros iniciais e melhores, métricas que
melhoraram e pioraram, vereditos, todas as configurações testadas, melhor relatório
completo e limitações. Não treine nem faça fine-tuning.

---
