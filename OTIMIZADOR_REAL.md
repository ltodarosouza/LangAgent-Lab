# Otimizadores clássicos no funil real

Experimento separado, autorizado por Matheus **só no branch `claude/otimizador-real`**:
`tools/otimizador_real.py` propõe configurações e escreve `workspace/candidate.json` no
lugar do agente. Avaliador, `agent/score.py`, `configs/`, checkpoints e baseline fixo
continuam intocados. **Nenhuma geração real foi feita.** O backend real só roda com
`--confirmo-gpu`, e o script se recusa a rodar no `main`.

## Orçamento: 269 casos gerados

O orçamento é a soma dos casos que a busca M do agente (M4–M12 = `candidate-04` …
`candidate-12` em `runs/real`) gerou de fato, ou seja, os casos que cada relatório não
reutilizou:

| configuração | 5 casos | +5 (10) | +27 (37) | gerados | veredito final |
|---|---:|---:|---:|---:|---|
| M4 `eta` 0,2 | 5 | 5 | 27 | 37 | melhor |
| M5 `latent` 1,10 | 5 | — | — | 5 | pior (rejeições) |
| M6 `cond` 1,10 | 5 | 5 | 27 | 37 | melhor |
| M7 `cond` 1,25 | 5 | 5 | 27 | 37 | melhor |
| M8 `steps` 35 | 5 | 5 | 27 | 37 | melhor |
| M9 `steps` 45 | 5 | — | — | 5 | insuficiente |
| M10 `cond` 1,40 | 5 | 5 | 27 | 37 | melhor |
| M11 `eta` 0,30 | 5 | 5 | 27 | 37 | melhor |
| M12 `eta` 0,40 | 5 | 5 | 27 | 37 | melhor (+23,05%) |
| **total** | | | | **269** | 9 configurações |

Ficam fora o baseline, que é a régua comum e não é regenerado, e M1–M3, de uma busca
anterior. A conta sai do próprio script:

```bash
python tools/otimizador_real.py orcamento
```

## Decisões de desenho

**Espaço.** São os cinco parâmetros de `configs/real_search_space.json`, sem cortar
dimensão nenhuma. `sampler` ddim, `scale_factor` 1,0 e `seed` 42 ficam congelados. Os
otimizadores trabalham num cubo [0,1]^5. `noise_level` (0–349) usa escala log1p, porque em
escala linear um passo de 10% pularia 35 níveis; os outros parâmetros são lineares.
`steps` e `noise_level` são arredondados para inteiro, e os contínuos para 3 casas.
Configurações que ficam iguais depois do arredondamento são reaproveitadas sem custo.

**Objetivo e restrições.** O objetivo é `mean_improvement_pct` do `compare_reports`, isto
é, a melhora média das 7 métricas contra o baseline fixo do mesmo escopo, a mesma régua do
agente. As restrições são duas: rejeições = 0 e pares fora de `ok` = 0. Valem em termos
absolutos, e o baseline tem 0 e 0.

**Funil.** É o 5 → 10 → 37 com a regra `melhor` de `generator/reporting.py`, comparando
com a melhor atual **do próprio método**, que começa no baseline. Os casos já gerados são
reaproveitados via `--reuse-report`. Só um lote de 37 casos com `melhor` troca a melhor
atual.

**Orçamento.** Conta casos gerados. Uma etapa só começa se os casos novos dela cabem no
que resta (5, 5 ou 27). Se não cabem, a configuração fica no último escopo concluído
(registrado como `orcamento_esgotado` no log) e o método termina. Pode sobrar um resto
menor que 27.

**GP-BO** (Optuna `GPSampler`, `constraints_func`):

- Pontos iniciais: o baseline (custo 0, já medido) mais 4 pontos Sobol embaralhados com
  semente fixa (`--seed`, padrão 0). Depois disso, quem propõe é o GP.
- As restrições entram num modelo de viabilidade separado, que multiplica a aquisição.
  Não são penalidade no objetivo.
- `--gp-parados podar` (padrão, conforme o pedido): só resultados de 37 casos alimentam o
  GP. Configuração parada em 5 ou 10 vira trial `PRUNED`, e o GP não a vê, nem o objetivo
  nem a restrição.
- Efeito colateral medido no teste: o GP repropõe pontos que já foram podados. Quando
  repropõe uma configuração já medida, o script repete o resultado conhecido (sem custo) e
  a próxima proposta vem da sequência Sobol. O `resumo.json` conta quantas vezes isso
  aconteceu (`repeated`, `sobol_fallback`).
- `--gp-parados escopo`: alternativa que alimenta o GP com a melhora no escopo em que a
  configuração parou, como no Nelder-Mead. Fica documentada para comparação; não é o
  padrão.

**Nelder-Mead** (scipy, `bounds` [0,1]^5):

- Parte do baseline. O simplex inicial é fixo: baseline mais um vértice por parâmetro,
  deslocado +10% da faixa no cubo (−10% se passar do limite). É uma regra neutra, igual
  para todos; nenhum valor vem do CADERNO. No real o primeiro vértice dá `steps` 34.
- Valor de uma configuração parada em 5 ou 10: a melhora média contra o baseline naquele
  escopo. Por construção, ela ficou abaixo da melhor atual naquele escopo, e o valor
  mistura escopos de tamanhos diferentes. Essa é a limitação aceita.
- Configuração inviável (rejeição ou par fora de ok) vale +∞ na minimização. Isso é uma
  barreira, não uma penalidade graduada: o Nelder-Mead precisa de um número por ponto.
- Sem reinício: se convergir antes de gastar o orçamento, o resto sobra e o log mostra.

**O que o script não faz:** ler o CADERNO, medições antigas ou `search_state.json`, mudar
seed, sampler ou scale_factor, regenerar baseline, nem promover nada a "Melhor atual" do
agente.

## Log e curva

Cada execução escreve `log.jsonl`, com uma linha por etapa do funil. Cada linha traz:
`method`, `config_index`, `candidate`, `scope`, `cases_generated`, `cases_cumulative`,
`mean_improvement_pct`, `metric_improvement_pct` (as 7 métricas), `verdict`, `reason`,
`case_wins` e `case_losses`, `rejected`, `pair_issues`, `new_best`,
`best_full_improvement_pct` e `report`. Linhas `cache` registram reaproveitamento (custo
0). A execução também escreve um `resumo.json`.

A trajetória do agente é convertida para o mesmo formato a partir dos relatórios M4–M12:

```bash
python tools/otimizador_real.py agente
```

A curva melhor melhora em 37 casos × casos gerados (CSV, e PNG se houver matplotlib):

```bash
python tools/otimizador_real.py curva runs/otimizador-curvas/agente/log.jsonl runs/real/otim-gp-*/log.jsonl runs/real/otim-nm-*/log.jsonl
```

## Como rodar no real (só depois da confirmação do Matheus)

Rode no checkout principal, onde estão `data/`, `runs/real/` (com os baselines) e o
`.venv` com torch.

1. Troque para o branch do experimento:

   ```bash
   git switch claude/otimizador-real
   ```

2. Instale as dependências extras no `.venv` (scipy 1.13.1 e optuna 5.0.0):

   ```bash
   .venv/bin/pip install -r tools/requirements-otimizador.txt
   ```

3. Confira o comando e a primeira configuração, sem gerar nada:

   ```bash
   .venv/bin/python tools/otimizador_real.py otimizar --method nm --backend real --dry-run
   ```

4. Rode os dois métodos, um de cada vez (mesma GPU). Uma interrupção perde o estado do
   otimizador, então rode com outra `--tag`; os relatórios de cada pasta continuam
   reaproveitáveis à mão.

   ```bash
   .venv/bin/python tools/otimizador_real.py otimizar --method gp --backend real --confirmo-gpu --tag v1
   ```

   ```bash
   .venv/bin/python tools/otimizador_real.py otimizar --method nm --backend real --confirmo-gpu --tag v1
   ```

5. Gere a curva com os três logs e registre cada configuração no CADERNO, na seção
   "Experimento separado: otimizadores clássicos (O)".

Custo esperado: 269 casos por método, a mesma geração que as 9 configurações da busca M,
ou seja, cerca de 2 × o tempo de GPU daquela busca.

Atenção ao primeiro ponto Sobol do GP com `--seed 0`: `steps` 87, `noise_level` 233,
`latent` 0,932, `cond` 0,64. É uma região que o agente nunca tentaria e que provavelmente
custa 5 casos sem ganho. É o preço normal da exploração e faz parte da comparação.

## Etapa separada, só planejada: reavaliar com seeds novas

Depois dos dois métodos, reavalie a melhor configuração final de cada um (GP-BO,
Nelder-Mead e a M12 do agente) nos 37 casos com 1 ou 2 seeds novas, por exemplo 43 e 44.
Compare cada uma com o baseline gerado **na mesma seed**. Isso mede se a vantagem
sobrevive à troca do ruído de geração.

**Bloqueio a decidir:** `configs/real_search_space.json` só aceita `seed` 42, e
`run_batch.py` valida contra ele. Como `configs/` não pode mudar, a reavaliação precisa de
uma de duas coisas, e Matheus decide qual:

- um script separado que chame `generate_image` com a seed como argumento, sem passar pela
  validação do espaço;
- uma autorização explícita para um espaço de reavaliação à parte, por exemplo
  `configs/reavaliacao_seeds.json`, usado só nessa etapa.

Custo: (3 configurações + baseline) × 37 casos × número de seeds, ou seja, 148 casos por
seed.

## Teste de ponta a ponta (backend simulado)

`tools/otimizador_simulado.py` escreve relatórios no formato de `run_batch.py`. As
métricas por caso vêm de uma função **inventada** dos cinco parâmetros, com interações,
ruído e regiões inválidas (`latent` > 1,08 rejeita; `noise_level` > 60 suja pares). O
resumo e o veredito usam as funções verdadeiras de `generator/reporting.py`. Os números
abaixo validam o código, **não dizem nada sobre o LDM**:

| método | casos usados | configurações | melhor em 37 casos (simulado) | observação |
|---|---:|---:|---:|---|
| Nelder-Mead | 267 | 14 | +10,95% | parou com a 14ª no quick: os 27 do full não cabiam |
| GP-BO `podar` | 269 | 40 | +11,71% | 37 parados em 5; 3 repropostas trocadas por Sobol |
| GP-BO `escopo` | 253 | 23 | +7,83% | parou quando um full de 27 não cabia |

Reproduzir:

```bash
python tools/otimizador_real.py otimizar --method nm --tag teste
```

Testes unitários (pulam o funil se scipy/optuna faltarem):

```bash
python -m unittest discover -s tests -p "test_otimizador_real.py"
```
