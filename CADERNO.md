# Caderno de experimentos

Memória da busca de parâmetros do LDM. Serve para o próximo agente saber **o que já foi
tentado, o que funcionou e o que não vale repetir**. Está resumido de propósito: uma linha
por tentativa e só as lições que mudam a próxima decisão. O texto completo de cada tentativa
(hipótese, tabelas por métrica, piores casos) está no histórico do git:
`git show 626bee9:CADERNO.md`.

Como manter:

- Cada tentativa nova vira **uma linha** na tabela de tentativas, inclusive as ruins.
- Só escreva um parágrafo quando a tentativa ensinar algo que ainda não está em "O que
  aprendemos". Se for confirmação de algo já registrado, a linha basta.
- Antes de rodar, procure aqui a configuração: nunca regenere uma tentativa já medida.
- Hipótese, mudança, resultado e lição continuam obrigatórios na cabeça do agente; no
  caderno entram só o resultado e o porquê.

## Melhor atual

`workspace/candidate.json`:

| steps | noise_level | sampler | scale_factor | seed | eta | latent_noise_scale | conditioning_noise_scale |
|---|---|---|---|---|---|---|---|
| 35 | 1 | ddim | 1.0 | 42 | **0.4** | 1.0 | **1.4** |

Nos 37 casos, contra o baseline fixo (`steps` 25, `eta` 0, escalas 1,0): **+23,05%** de
melhora média, 27 cortes melhores e 10 piores, nenhuma rejeição nem par inválido, meta de
15% atingida. Veio da busca de Matheus (2026-10-23). A busca de Lucas, no mesmo dia, parou
em `eta` 0,35 com escalas neutras: +15,96%.

Melhora média por métrica (37 casos, contra o baseline):

| métrica | melhor atual (eta 0,4 + cond 1,4) | Lucas (eta 0,35, cond 1,0) |
|---|---:|---:|
| GLCM contraste | +19,81% | +11,94% |
| GLCM energia | +33,56% | +22,65% |
| Wavelet fina | +16,80% | +10,38% |
| Wavelet grossa | +26,88% | +17,14% |
| Wavelet entropia | +29,83% | +17,94% |
| Wavelet LL | +14,52% | +12,97% |
| NEx | +19,95% | +18,71% |
| **média** | **+23,05%** | **+15,96%** |
| nota | 76,73 | 74,63 |
| textura aprovada / final aprovada | 30 / 18 | 29 / 15 |

Melhorou nas sete métricas e em todos os indicadores de contagem. A diferença vem de
`conditioning_noise_scale` 1,4 (ver abaixo).

**Atenção ao retomar.** `runs/` não vai para o git. Os relatórios completos da melhor atual
estão na máquina de Matheus; aqui existem os da busca de Lucas (`runs/real/candidate-08-full`
é o `eta` 0,35). `workspace/search_state.json` ainda aponta para `candidate-01-full`
(`eta` 0, +7,76%) e não foi atualizado. Para continuar a partir da melhor atual é preciso
copiar os relatórios dele para `runs/real/` e só então atualizar o `search_state.json`.

## Régua e funil

- Baseline fixo: `steps` 25, `noise_level` 1, `eta` 0, escalas 1,0, 37 casos do Dsr. Nunca é
  regenerado. Baseline por métrica: energia GLCM mediana 178% da original, contraste 79%,
  Wavelet fina 80%: a sintética sai lisa demais. Brilho e pares já estavam bem.
- Funil 5 → 10 → 37, reaproveitando os casos já feitos. Promove com `melhor`: média das
  sete métricas acima da melhor atual, mais cortes melhores do que piores, sem novas
  rejeições nem pares inválidos. Os 15% são meta forte, não critério.
- Até 2026-10-22 os 15% eram critério de promoção (regra antiga); mudou em 2026-10-23. As
  tentativas marcadas "regra antiga" foram paradas por isso e poderiam ter avançado hoje.

## O que aprendemos

- **`steps`: 35 é o ponto.** Sozinho (com `eta` 0) dá +7,8%. Em cima de `eta` e
  `conditioning` o efeito é bem maior: Matheus foi de +7,9% para +16,1% ao trocar 25 por 35.
  Com 45 piora (Wavelet grossa, LL e correlação do mapa caem) e com 50 quase nada muda.
- **`eta`: o parâmetro mais confiável.** De 0 a 0,4 a melhora quase só sobe. Ganha mais em
  energia GLCM, entropia, LL e NEx. Contraste e Wavelet fina saturam perto de +20% e +17%.
  Risco: o caso `...1-047` oscila entre NEx alto e normal conforme o `eta`. Ainda não se
  testou acima de 0,4.
- **`conditioning_noise_scale`: ajuda, mas só depois de `eta` e `steps`.** Com `eta` 0 e 35
  passos, 1,10 piorou o NEx (extremos nos dois sentidos) e foi descartado. Com `eta` 0,2 e
  25 passos, subiu a cada degrau (+4,8% → +6,0% com 1,10 → +7,9% com 1,25). Com 35 passos,
  de 1,25 para 1,40 foi +16,1% → +18,5%. Em `eta` 0,3 a 0,35 a diferença entre cond 1,0 e
  1,4 é de uns 5 pontos. Ainda não se testou 1,5 (limite do espaço).
- **`latent_noise_scale` 1,10: não mexer.** 5 rejeições e pares inválidos.
- **`noise_level`: não é alavanca.** 10 deu +4,4% e 50 piorou (1 rejeição, 1 par suspeito).
  Fica em 1.
- **Casos que nenhum controle permitido resolve:** `...1-033` (borrado), `...1-59`
  (escuro), `...1-031`, `...1-65`, `...1-072`. Mesmo na melhor atual a textura aprova 30 de
  37. Se a meta for esses cortes, parâmetro de amostragem não basta.
- **Interação.** Os efeitos de `conditioning` e `steps` dependem do `eta` e dos passos
  atuais; o que falha isolado pode funcionar em cima da melhor atual.

## Tentativas

Todas contra o baseline fixo. "M" = busca de Matheus; "L" = busca de Lucas. Quando há três
números, são os escopos de 5, 10 e 37 casos; quando há um só, é o escopo em que parou.
Parâmetros em negrito são o que mudou em relação à base.

| # | base | mudança | melhora vs baseline | veredito e motivo |
|---|---|---|---|---|
| L1 | baseline | nenhuma (referência local) | 0% | nota 68,92; textura 21/16/0, brilho 34/3/0 |
| M1 | baseline | `steps` 50 | ~0 (nota +0,05) | quase sem efeito; aceita no quick, sem ganho real |
| M2 | baseline | `noise_level` 50 | +4,40% (10) | pior: +1 rejeição, +1 par suspeito |
| M3 | baseline | `noise_level` 10 | +4,41% (10) | insuficiente (regra antiga); energia GLCM não se mexe |
| L2 | baseline | **`steps` 35** | +7,76% (37) | melhor (regra antiga: nova base); textura 26/11/0 |
| L3 | L2 | **`steps` 45** | n/d (7 casos) | pior: Wavelet grossa e correlação do mapa caem |
| L4 | L2 | **`steps` 40** | n/d | interrompida por decisão humana, sem conclusão |
| M4 | baseline | **`eta` 0,2** (steps 25) | +7,3 / +5,3 / +4,8% | melhor (29/8); ganho modesto com 25 passos |
| M5 | M4 | **`latent_noise_scale` 1,10** | n/d (5 casos) | pior: 5 rejeições, pares inválidos |
| M6 | M4 | **`conditioning` 1,10** | +7,8 / +6,4 / +6,0% | melhor (33/4) |
| M7 | M6 | **`conditioning` 1,25** | +8,7 / +8,1 / +7,9% | melhor (33/4) |
| M8 | M7 | **`steps` 35** | +16,5 / +16,0 / +16,1% | melhor (36/1); salto, passa dos 15% |
| M9 | M8 | `steps` 45 | n/d (5 casos) | insuficiente: 2 cortes melhores, 3 piores |
| M10 | M8 | **`conditioning` 1,40** | +18,0 / +18,1 / +18,5% | melhor (35/2) |
| M11 | M10 | **`eta` 0,30** | +22,4 / +20,8 / +21,2% | melhor (22/15); sobe LL e NEx |
| M12 | M11 | **`eta` 0,40** | +25,3 / +24,1 / +23,1% | melhor (27/10); **melhor atual** |
| L5 | L2 | **`conditioning` 1,10** | +7,45% (5) | insuficiente (regra antiga): NEx regride |
| L6 | L2 | **`eta` 0,10** | +12,34% (5) | insuficiente (regra antiga): sete métricas melhoram |
| L7 | L2 | **`eta` 0,20** | +14,55% (5) | insuficiente (regra antiga): NEx alto volta no `1-047` |
| L8 | L2 | **`eta` 0,25** | +15,0 / +13,7 / +13,1% | melhor (25/12) depois da correção da regra; nota 73,88 |
| L9 | L8 | **`eta` 0,35** | +20,3 / +16,8 / +16,0% | melhor (26/11); nota 74,63; superada por M12 |

L8 e L9 usaram steps 35 e escalas 1,0. M1 a M3 vieram de uma busca paralela anterior de
Matheus, com 7 ou 10 casos (quick) e sem lote completo.

## Para a próxima busca

Pistas a confirmar, nenhuma executada:

1. `eta` 0,4 → 0,5, mantendo `conditioning` 1,4: LL e NEx vinham subindo com o `eta`. Vigiar
   Wavelet entropia (já recuou 0,5 ponto de 0,3 para 0,4) e o NEx alto no `1-047`.
2. `conditioning_noise_scale` 1,4 → 1,5: foi o maior ganho depois de `steps`. É o limite do
   espaço; esperar menos retorno.
3. Só depois, `steps` entre 30 e 40, porque o efeito depende dos outros dois.

Antes de gastar orçamento, copie os relatórios da melhor atual (ver "Atenção ao retomar").

## Experimento separado: otimizadores clássicos (O)

**Não é continuação da busca do agente.** Exceção ao protocolo autorizada por Matheus só
no branch `claude/otimizador-real`: um script (`tools/otimizador_real.py`), e não o agente,
propõe as configurações e escreve `workspace/candidate.json` (restaurado no fim). Objetivo:
comparar GP-BO com restrições e Nelder-Mead com o agente, no mesmo funil 5 → 10 → 37, com a
mesma régua (baseline fixo) e o mesmo orçamento em casos gerados. Os otimizadores não leem
este caderno nem medições antigas, e o resultado deles não muda a "Melhor atual" acima sem
decisão humana.

Orçamento = casos gerados pela busca M4–M12 = **269** (7 configurações até 37 casos ×
(5 + 5 + 27) = 259, mais M5 e M9 parados em 5 = 10). M1–M3 e o baseline ficam de fora.
Desenho, decisões e comandos: `OTIMIZADOR_REAL.md`.

Estado: código pronto e testado só no backend simulado; **nenhuma geração real feita**.
Quando rodar, cada configuração vira uma linha aqui com prefixo "OG" (GP-BO) ou "ON"
(Nelder-Mead).

| # | método | configuração | escopo final | melhora vs baseline | veredito |
|---|---|---|---|---|---|
