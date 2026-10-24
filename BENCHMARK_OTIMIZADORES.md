# Otimizadores clássicos × agente LLM (backend mock)

Pergunta da apresentação: com o mesmo orçamento, um otimizador determinístico ou clássico
acha parâmetros tão bons quanto o agente? Este é o primeiro passo, só no **mock**, que é
barato e determinístico. Nada aqui usou o backend real.

> **Isto não é evidência sobre a busca real.** `agent/mock_backend.py` ignora `eta`,
> `latent_noise_scale` e `conditioning_noise_scale`; só `steps`, `noise_level` e `sampler`
> mudam o score, e o ótimo fica perto de `steps` ≈ 34 com `noise_level` 1. No real, os
> parâmetros que o mock ignora são justamente as alavancas mais fortes. O resultado abaixo
> serve **só como teste de que o código do benchmark funciona** (orçamento, reaproveitamento,
> restrições, curvas). Não use esses números para dizer que otimizador clássico empata com
> o agente, nem que perde para ele, no problema real.

Como reproduzir (precisa de Python ≥ 3.10; scipy, optuna, cma e matplotlib são opcionais,
e o método sem a dependência é pulado):

```bash
python tools/benchmark_otimizadores.py --budget 20 --repeats 50 --agent-history runs/history.jsonl
```

```bash
python tools/benchmark_otimizadores.py --budget 20 --repeats 50 --only steps noise_level sampler --agent-history runs/history.jsonl
```

O script chama `run_mock` e `score_cases` diretamente (as mesmas funções de
`agent.run_experiment`), não escreve em `runs/history.jsonl` e salva `resultado.json`,
`curvas.csv`, `trajetorias.json` e `curvas.png` em `runs/benchmark-otimizadores/<data>/`.

## Regras de justiça

- Todos os métodos começam avaliando o baseline (`steps` 25, `noise_level` 1, `ddim`), como o
  agente.
- Orçamento = configurações **distintas**. Repetir uma configuração já medida é
  reaproveitamento e não gasta orçamento (regra do AGENTS.md).
- "Melhor" só conta configurações válidas (brilho, par e validade); inválida vale 0 no score.
- `scale_factor` e `seed` congelados. Métodos estocásticos: 50 repetições com seeds
  diferentes; determinísticos: 1 execução (o resultado não muda).
- Métodos: busca aleatória; busca coordenada (pattern search por compasso, passo inicial
  0,25, divide por 2 quando nada melhora); Nelder-Mead do scipy (simplex inicial 0,2);
  Optuna TPE (5 pontos iniciais, categóricas nativas); GP-BO simples em numpy (RBF, EI);
  CMA-ES (`cma`, σ₀ 0,3). Os contínuos trabalham num cubo [0,1]^d, com as opções discretas
  em faixas iguais.

## O que o mock é, de fato

Antes dos números, uma limitação que muda a leitura: **o mock só reage a `steps`,
`noise_level` e `sampler`**. `eta`, `latent_noise_scale` e `conditioning_noise_scale` estão
no `search_space.json`, mas `simulate_case` os ignora. Sobram 7 × 6 × 2 = **84
configurações**, que a grade resolve por completo:

- ótimo: `steps` 35, `noise_level` 1, `ddim` → **99,6393** (baseline 97,3607);
- só **4 das 84** superam o baseline, todas com `steps` 35;
- 14 são inválidas (`noise_level` 50 estoura o brilho).

Por isso o benchmark roda em dois espaços: **completo** (8 dimensões do JSON; o otimizador
não sabe que 3 são inertes) e **reduzido** (`--only steps noise_level sampler`, o mesmo
espaço da trajetória do agente no mock).

## Resultados (orçamento 20)

Mediana do melhor score válido após *k* avaliações e, entre parênteses, a fração de
execuções que já tinham achado o ótimo.

**Espaço completo (8 dimensões, 3 inertes):**

| método | 1 | 2 | 3 | 5 | 8 | 10 | 12 | 15 | 20 |
|---|---|---|---|---|---|---|---|---|---|
| aleatória | 97,36 (0%) | 97,36 (2%) | 97,36 (2%) | 97,36 (4%) | 97,36 (6%) | 97,36 (6%) | 97,36 (6%) | 97,36 (10%) | 97,51 (12%) |
| coordenada | 97,36 | 97,36 | 97,36 | 97,36 | 97,36 | 97,36 | **99,64** | 99,64 | 99,64 |
| Nelder-Mead | 97,36 | **99,64** | 99,64 | 99,64 | 99,64 | 99,64 | 99,64 | 99,64 | 99,64 |
| TPE | 97,36 (0%) | 97,36 (4%) | 97,36 (4%) | 97,36 (6%) | 97,36 (28%) | 97,36 (42%) | 97,84 (48%) | 99,64 (58%) | 99,64 (68%) |
| GP-BO | 97,36 (0%) | 97,36 (4%) | 97,36 (6%) | 97,36 (6%) | 98,17 (42%) | 99,64 (52%) | 99,64 (54%) | 99,64 (66%) | 99,64 (82%) |
| CMA-ES | 97,36 (0%) | 97,36 (4%) | 97,36 (8%) | 97,36 (12%) | 98,17 (22%) | 98,17 (24%) | 98,17 (30%) | 98,17 (36%) | 98,57 (36%) |
| agente (mock) | 97,36 | **99,64** | 99,64 | 99,64 | — | — | — | — | — |

**Espaço reduzido (`steps`, `noise_level`, `sampler`):**

| método | 1 | 2 | 3 | 5 | 8 | 10 | 12 | 15 | 20 |
|---|---|---|---|---|---|---|---|---|---|
| aleatória | 97,36 (0%) | 97,36 (2%) | 97,36 (2%) | 97,36 (6%) | 97,36 (14%) | 97,36 (16%) | 97,43 (20%) | 97,84 (26%) | 98,17 (28%) |
| coordenada | 97,36 | 97,36 | 97,36 | 97,36 | **99,64** | 99,64 | 99,64 | 99,64 | 99,64 |
| Nelder-Mead | 97,36 | **99,64** | 99,64 | 99,64 | 99,64 | 99,64 | 99,64 | 99,64 | 99,64 |
| TPE | 97,36 (0%) | 97,36 (4%) | 97,36 (4%) | 97,36 (4%) | 97,36 (10%) | 97,36 (16%) | 97,43 (32%) | 99,64 (54%) | 99,64 (92%) |
| GP-BO | 97,36 (0%) | 97,36 (4%) | 97,36 (4%) | 97,36 (6%) | 98,97 (40%) | 99,64 (78%) | 99,64 (98%) | 99,64 (100%) | 99,64 (100%) |
| CMA-ES | 97,36 (0%) | 97,36 (4%) | 97,36 (4%) | 97,36 (16%) | 98,17 (26%) | 98,17 (38%) | 98,97 (48%) | 99,64 (82%) | 99,64 (90%) |
| agente (mock) | 97,36 | **99,64** | 99,64 | 99,64 | — | — | — | — | — |

Restrições (espaço completo, todas as avaliações das 50 repetições):

| método | avaliações inválidas | violações de brilho (casos) | pares suspeitos | melhor final respeita restrições |
|---|---:|---:|---:|---|
| aleatória | 15,9% | 795 | 0 | sim |
| coordenada | 0% | 0 | 0 | sim |
| Nelder-Mead | 0% | 0 | 0 | sim |
| TPE | 8,5% | 425 | 0 | sim |
| GP-BO | 3,8% | 190 | 0 | sim |
| CMA-ES | 1,1% | 55 | 0 | sim |

Nenhum método termina com um "melhor" inválido, porque a nota zera a configuração
inválida. Mas os exploradores (aleatória, TPE, GP-BO) **gastam orçamento** em `noise_level`
50. No real isso seria lote rejeitado: GPU gasta e, pelas regras do funil, um caso
rejeitado bloqueia a promoção.

**Sensibilidade dos determinísticos ao passo inicial** (orçamento 20, avaliação em que
acham o ótimo):

| passo inicial | 0,05 | 0,10 | 0,15 | 0,20 | 0,25 | 0,30 | 0,40 |
|---|---|---|---|---|---|---|---|
| coordenada (completo / reduzido) | nunca / nunca | 2 / 2 | 2 / 2 | 2 / 2 | 12 / 7 | 12 / 7 | 12 / 7 |
| Nelder-Mead (completo / reduzido) | nunca / nunca | 2 / 2 | 2 / 2 | 2 / 2 | 11 / 8 | 11 / 8 | 11 / 11 |

O "acerto em 2" do Nelder-Mead é geometria, não inteligência: com passo de 0,10 a 0,20 no
cubo, o primeiro vértice do simplex cai exatamente na faixa de `steps` 35 (vizinha de 25 na
lista de opções). Com passo 0,05 nunca sai da faixa do baseline; com 0,25 ou mais pula 35 e
cai em 50.

## Leitura (vale só para o mock)

1. **No mock, os determinísticos locais empatam com o agente** e os bayesianos chegam
   perto com folga de orçamento. Com 20 avaliações, coordenada e Nelder-Mead acham o ótimo
   sempre; GP-BO em 82–100% das execuções; TPE em 68–92%; CMA-ES em 36–90%; busca
   aleatória em 12–28%. A diferença está na **velocidade**: o agente chegou ao ótimo na 2ª
   avaliação; os bayesianos precisam de ~8–15.
2. **O mock não separa os métodos de forma útil.** Tem só 84 pontos, três dimensões
   efetivas e o ótimo é vizinho direto do baseline. Qualquer busca local que dê o passo
   certo vence em 2 avaliações, e o agente sabia o passo certo porque "mais passos ajuda
   até um ponto" é conhecimento prévio sobre DDIM. Isso é exatamente o que o agente traz e
   o otimizador não traz, mas o mock não consegue medir o quanto isso vale num problema
   difícil.
3. **Dimensões inertes custam caro para quem não lê as métricas.** No espaço completo, TPE
   cai de 92% para 68% de acerto e CMA-ES de 90% para 36%, porque gastam avaliações variando
   `eta` e escalas que não mudam nada. O agente vê as métricas por caso e percebe que um
   parâmetro não mexe na textura. No real é o oposto: `eta` e `conditioning` são as
   alavancas mais fortes (CADERNO), e `noise_level` é que quase não importa.
4. **Restrições.** Busca local partindo do baseline não gerou nenhuma configuração
   inválida; os exploradores geraram de 1% a 16%. Sem restrição explícita (ou penalidade na
   modelagem), BO/TPE vão testar `noise_level` alto no real.

## Comparação com a busca real registrada no CADERNO

A trajetória M (M4 → M12) **é, na prática, uma busca coordenada guiada**: um parâmetro por
vez, partindo da melhor atual, com direção e tamanho de passo escolhidos pelas métricas por
caso. Chegou a **+23,05%** sobre o baseline em ~12 configurações (M1–M12; 7 delas, de M4 a
M12 sem M5 e M9, formam a linha que leva à melhor), com duas tentativas descartadas cedo no funil (M5 com 5 casos, M9 com
5 casos). A busca L, com o mesmo tipo de raciocínio mas sob a regra antiga dos 15%, parou
em +15,96% com 9 configurações.

O que o mock **não** permite concluir:

- O real tem 5 dimensões ativas com interações fortes (`conditioning` só ajuda depois de
  `eta` e `steps`), ruído entre casos e custo por avaliação de ordens de grandeza maior.
  Uma superfície assim favorece GP-BO/TPE mais do que o mock sugere, e penaliza pattern
  search, que fica preso a eixos.
- A comparação justa no real precisa de orçamento igual em **casos avaliados**, não só em
  configurações, porque o agente descarta no funil com 5 casos.

Conclusão para a apresentação: **a pergunta continua em aberto.** O mock mostra apenas que
o benchmark funciona: todos os métodos rodam com o mesmo orçamento, partindo do mesmo
baseline, e o registro de restrições e curvas sai certo. Ele não diz nada sobre quem acha
parâmetros melhores no LDM real. A resposta exige a versão real abaixo ou, como passo
intermediário sem GPU, o surrogate proposto na próxima seção, que também tem limites.

## Atualização: execução real (2026-10-23)

A versão real foi rodada (ver `OTIMIZADOR_REAL.md`): mesmo funil 5 → 10 → 37, mesma
régua, seed 42 e 269 casos gerados para cada método, o mesmo orçamento da busca M do
agente.

- **GP-BO com restrições:** +44,17% em 37 casos (nota 85,79), atingido com 119 casos. Mas
  gastou 45% do orçamento em configurações com rejeição. O ponto achado fica nos limites
  do espaço (`eta` 0,77, `latent` 0,75, `cond` 1,5): 3 métricas no teto de 50, fundo mais
  ruidoso e seed única.
- **Nelder-Mead:** +24,44% (nota 75,41, abaixo da M12) e não convergiu.
- **Agente:** +23,05% (nota 76,73).

Resposta provisória: com o mesmo orçamento, o GP-BO achou uma configuração bem melhor pela
régua do lab. Ela veio de uma região que o agente não explorou (`latent` < 1, `eta` > 0,4).
O Nelder-Mead empatou com o agente pela média, mas perdeu pela nota. Falta a reavaliação
com outras seeds antes de concluir.

## Proposta (não implementada): surrogate ajustado às configurações reais

Ideia: trocar o mock por um modelo ajustado às ~21 configurações reais do CADERNO (L1–L9,
M1–M12) e rodar o mesmo script contra ele, ainda sem GPU.

- **Dados:** cada tentativa com relatório vira um ponto (5 parâmetros ativos → melhora média
  contra o baseline e, se os relatórios em `runs/real/` existirem, as sete métricas e os
  vereditos por caso). Peso maior para o escopo de 37 casos; os escopos de 5 e 10 entram
  como fidelidade menor, com mais ruído.
- **Modelo:** GP com kernel ARD (um comprimento por parâmetro) para a melhora, mais um
  classificador simples de validade (rejeições e pares inválidos, alimentado por M2
  `noise_level` 50 e M5 `latent` 1,10). Para não premiar um único mundo inventado, cada
  repetição do benchmark sorteia uma **amostra da posterior** do GP como função objetivo.
- **Validação antes de usar:** erro de leave-one-out nas configurações com 37 casos e
  checagem de que o surrogate reproduz as tendências do CADERNO (`eta` sobe até 0,4,
  `steps` 45 piora, `conditioning` ajuda só com `eta` e `steps` altos).

Limitações, que precisam ir junto com qualquer resultado:

- **Poucos pontos para 5 dimensões.** São ~21 tentativas, das quais umas 15 têm número
  (L3, L4, M5 e M9 pararam sem melhora mensurável) e menos ainda com 37 casos.
- **Viés a favor do agente.** Os pontos vêm da trajetória do próprio agente, que ficou em
  `steps` 25–50, `eta` 0–0,4, `conditioning` 1,0–1,4 e `latent` 1,0. Fora disso (`eta` >
  0,4, `conditioning` 1,5, `latent` < 1, `noise_level` alto) o surrogate só extrapola: um
  otimizador que explore lá será premiado ou punido por uma superfície inventada.
- **Escopos e regras misturados.** 5, 10 e 37 casos, e tentativas paradas pela regra antiga
  dos 15%, não são diretamente comparáveis.
- **Sem ruído real entre casos** se só a média for modelada; o agente decide olhando caso
  por caso, e o surrogate agregado tira essa vantagem dele.
- Qualquer ótimo encontrado no surrogate é **hipótese**, não resultado: precisa passar pelo
  funil real, com autorização, antes de ir para o CADERNO.

## Desenho (não executado) da versão real com multi-fidelidade

O funil 5 → 10 → 37 já é uma escada de fidelidade. Um BOHB / Hyperband encaixa assim:

- **Espaço:** `configs/real_search_space.json` com `sampler` = `ddim`, `scale_factor` = 1,0 e
  `seed` = 42 congelados. Ativos: `steps` (int 10–100), `noise_level` (int 0–349; sugiro
  log), `eta` (0–1), `latent_noise_scale` (0,75–1,25), `conditioning_noise_scale` (0,5–1,5).
- **Fidelidade = número de casos**, com os mesmos subconjuntos cumulativos e fixos do funil
  (5 ⊂ 10 ⊂ 37 do `data/dsr-valid/manifest.json`), η = 2–3,7. Os casos já gerados são
  reaproveitados quando a configuração sobe de nível, como no funil.
- **Objetivo:** a mesma régua do relatório, isto é, a melhora média das sete métricas
  contra o baseline fixo, calculada só nos casos daquele nível. **Restrições** como
  restrição dura: rejeição nova ou par inválido = resultado inválido (Optuna:
  `constraints_func`; BOHB: valor −∞), nunca só penalidade suave.
- **Promoção:** o Hyperband promove por ranking dentro do *bracket*. Para ficar comparável
  com o agente, exigir também o `melhor` do funil (média acima da melhor atual, mais cortes
  melhores que piores) antes de subir para 37.
- **Orçamento justo:** medir em casos gerados (ou GPU-hora), igual para todos. Referência do
  agente: somar os casos que a busca M consumiu (M1–M12 com as paradas em 5 e 10).
- **Partida:** mesmo baseline e, em uma segunda rodada, a mesma melhor atual do
  `search_state.json`, como o AGENTS.md exige para o agente.
- **Repetições:** BOHB é estocástico. Com orçamento real só cabem poucas execuções (2–3
  seeds do otimizador); o seed da geração continua 42.
- Precisa de autorização humana antes de rodar, e o histórico tem que ir para o CADERNO
  como uma busca separada (ex.: "B1…").
