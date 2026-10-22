# Prompt de execução do agente

Copie o texto abaixo e altere apenas `MAX_CONFIGURATIONS` se quiser aumentar ou
reduzir o número máximo de configurações avaliadas.

---

Trabalhe neste repositório para encontrar parâmetros de amostragem do LDM que
melhorem a geração de tomografias pulmonares.

`MAX_CONFIGURATIONS = 10`

Antes de começar, leia `AGENTS.md`, `README.md`,
`configs/real_search_space.json` e `workspace/candidate.json`.

O ambiente já foi preparado por um humano com `./tools/bootstrap.sh`, e esta
sessão roda com as travas de `tools/agente.sh`: você só escreve em
`workspace/candidate.json` e `runs/`, não tem acesso ao avaliador e o lote real
passa por um controle de orçamento. Se algo faltar ou uma trava impedir um passo
legítimo, pare e reporte o bloqueio; não tente contorná-la.

Regras:

1. Não altere os pesos, o AEKL, o avaliador externo, a fórmula da nota, os 7
   casos rápidos nem o conjunto de 37 casos.
2. Durante a busca, altere somente `workspace/candidate.json` e arquivos locais
   de resultados dentro de `runs/`, que não são versionados.
3. Use somente valores permitidos por `configs/real_search_space.json`.
4. Conte a configuração inicial dentro de `MAX_CONFIGURATIONS` e nunca exceda
   esse total.
5. Guarde todas as tentativas, inclusive as que piorarem.
6. Registre cada tentativa em `CADERNO.md`, seguindo o modelo do arquivo:
   hipótese, mudança, resultado e lição, antes de escolher a próxima. Só
   acrescente entradas; corrija uma entrada antiga com uma entrada nova.
7. Quando uma hipótese vier de um artigo, cite-o a partir de `literatura/` e
   deixe suas anotações em `literatura/notas/`.

Fluxo:

1. Execute a configuração inicial nos 7 casos fixos com `.venv/bin/python
   generator/run_batch.py --scope quick --config workspace/candidate.json
   --output-dir runs/real/baseline-quick`. Leia o `report.json` completo, não
   apenas a nota.
2. Execute a mesma configuração nos 37 casos com `--scope full`, reutilizando o
   relatório rápido com `--reuse-report runs/real/baseline-quick/report.json` e
   salvando em `runs/real/baseline-full`. Esses dois relatórios formam o baseline.
3. Escolha uma alteração pequena e justificável, preferencialmente uma variável
   por vez. Execute primeiro os 7 casos e compare com o melhor relatório rápido
   usando `--compare-to CAMINHO_DO_MELHOR_QUICK/report.json`. Salve a tentativa
   numa pasta nova, como `runs/real/candidate-01-quick`.
4. Só execute os 37 casos quando o relatório rápido disser `melhor`. No lote
   completo, use `--reuse-report CAMINHO_DO_QUICK/report.json`, compare com
   `--compare-to CAMINHO_DO_MELHOR_FULL/report.json` e salve numa pasta como
   `runs/real/candidate-01-full`.
5. Uma configuração só vira a nova melhor se o relatório completo disser
   `melhor`. Caso contrário, preserve a melhor anterior e tente outra hipótese.
6. Entre as tentativas, use todas as métricas por imagem — Wavelet fina e
   grossa, GLCM, NEx, brilho, densidade e correlação — para escolher o próximo
   teste. Inspecione as prévias dos piores casos quando isso ajudar. Cada lote
   também grava `boletim.json`, a nota do juiz congelado: contagens de textura
   e brilho, Δ de cada métrica com intervalo de 95% e, quando houver
   `--compare-to`, a comparação corte a corte com o lote de referência. Use os
   números dele nas entradas do caderno.
7. Pare ao atingir `MAX_CONFIGURATIONS`, quando não houver outra hipótese segura
   dentro do espaço permitido ou quando encontrar uma configuração válida sem
   melhora defensável adicional.

Use pastas com nomes claros, por exemplo `runs/real/baseline-quick`,
`runs/real/baseline-full`, `runs/real/candidate-01-quick` e
`runs/real/candidate-01-full`. Se uma execução for interrompida, repita o mesmo
comando com a mesma pasta para continuar sem perder os casos concluídos.

Ao terminar, apresente: parâmetros iniciais e melhores, diferença da nota,
contagens de vereditos, métricas que melhoraram ou pioraram, lista de todas as
configurações tentadas, melhor relatório completo e limitações encontradas.

Não treine nem faça fine-tuning. Não declare melhora usando apenas o lote de 7.

---
