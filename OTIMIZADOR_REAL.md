# Otimizadores clássicos no funil real

Experimento separado, autorizado por Matheus **só no branch `claude/otimizador-real`**:
`tools/otimizador_real.py` propõe configurações e escreve `workspace/candidate.json` no
lugar do agente. Avaliador, `agent/score.py`, `configs/`, checkpoints e baseline fixo
continuam intocados. O backend real só roda com `--confirmo-gpu`, e o script se recusa a
rodar no `main`. A execução real foi autorizada por Matheus e feita em 2026-10-23
(resultado abaixo).

## Resultado da execução real (2026-10-23, seed 42)

Os dois métodos rodaram em sequência, sem quedas nem retomadas: GP-BO das 15:30 às 19:49 e
Nelder-Mead das 19:49 às 22:06, ou cerca de 1 min por caso. Logs, resumos e a trajetória
do agente no mesmo formato estão em `resultados/otimizador-real/`. Relatórios e imagens
ficam em `runs/real/gpbo-NN-*` e `runs/real/nm-NN-*`, fora do git.

### Curva: melhor melhora em 37 casos × casos gerados

Cada valor é a melhora média das 7 métricas contra o baseline fixo (teto de 50% por
métrica) da melhor configuração confirmada em 37 casos até aquele ponto do orçamento.

| casos gerados | 37 | 50 | 82 | 119 | 156 | 195 | 232 | 258 | 269 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| agente (M4–M12) | +4,81 | +4,81 | +6,01 | +7,93 | +16,05 | +18,51 | +21,24 | +21,24 | **+23,05** |
| GP-BO | 0 | 0 | +19,84 | **+44,17** | +44,17 | +44,17 | +44,17 | +44,17 | +44,17 |
| Nelder-Mead | +5,26 | +5,26 | +9,41 | +9,41 | +24,05 | +24,05 | +24,05 | **+24,44** | +24,44 |

Para gerar o gráfico (PNG fora do git):

```bash
python tools/otimizador_real.py curva resultados/otimizador-real/agente-log.jsonl resultados/otimizador-real/gpbo-log.jsonl resultados/otimizador-real/nm-log.jsonl
```

| | agente | GP-BO | Nelder-Mead |
|---|---|---|---|
| configurações medidas | 9 | 41 | 23 |
| chegaram a 37 casos | 7 | 2 | 4 |
| paradas em 5 / 10 | 2 / 0 | 39 / 0 | 14 / 5 |
| casos gerados | 269 | 269 | 268 (sobrou 1) |
| etapas com rejeição ou par inválido | 1 (M5) | 24 | 2 |
| casos gastos nessas etapas | 5 | 120 (45% do orçamento) | 10 |
| melhor atingido em | 269 casos | 119 casos (11ª configuração) | 258 casos |

O GP-BO achou o melhor ponto com 119 casos e depois não melhorou mais. 32 das 75
propostas dele repetiam configurações já medidas, quase todas pontos podados em 5 casos, e
foram trocadas por pontos Sobol. O Nelder-Mead não convergiu: o orçamento acabou primeiro.

### Melhor configuração de cada método (37 casos)

| | GP-BO `gpbo-11` | Nelder-Mead `nm-21` | agente M12 |
|---|---|---|---|
| steps / noise / eta | 43 / 2 / **0,767** | 29 / 1 / 0,068 | 35 / 1 / 0,4 |
| latent / cond | **0,75** / **1,5** | 1,008 / 1,02 | 1,0 / 1,4 |
| melhora média (teto 50) | **+44,17%** | +24,44% | +23,05% |
| GLCM contraste | +48,8 | +28,8 | +19,8 |
| GLCM energia | +50 (sem teto: 67,0) | +50 (sem teto: 52,6) | +33,6 |
| Wavelet fina | +40,1 | +27,9 | +16,8 |
| Wavelet grossa | +50 (sem teto: 63,1) | +12,9 | +26,9 |
| Wavelet entropia | +50 (sem teto: 62,5) | +46,7 | +29,8 |
| Wavelet LL | +48,8 | +3,8 | +14,5 |
| NEx | +21,5 | **+1,0** | +19,9 |
| nota (score do juiz) | **85,79** | 75,41 | 76,73 |
| final aprovada / revisar | 29 / 8 | 14 / 23 | 18 / 19 |
| textura aprovada | 34 / 37 | 25 / 37 | 30 / 37 |
| NEx fora de ok | 5 (2 inconcl., 2 baixo, 1 alto) | **13 (10 alto)** | 5 |
| brilho em revisão / densidade fora de ok | 0 / 0 | 2 / 3 | 1 / 2 |
| rejeições / pares fora de ok | 0 / 0 | 0 / 0 | 0 / 0 |
| vitórias / derrotas por corte vs baseline | 35 / 2 | 36 / 1 | 37 / 0 |
| regra `melhor` contra a M12 | melhor (29 / 8) | melhor (22 / 15) | — |
| frente a frente por corte | GP-BO vence NM 31 / 6, vence M12 29 / 8 | NM vence M12 22 / 15 | |

Baseline: nota 68,92. Por caso abaixo, cada célula traz a distância conjunta (média das 7
distâncias normalizadas pela média do baseline), com ▼ = melhor que o baseline e ▲ = pior,
seguida da nota do caso e do veredito final.

| corte | baseline | GP-BO gpbo-11 | NM nm-21 | agente M12 |
|---|---:|---|---|---|
| P4P100S300I00003 · 1-058 | 1.09 · 67 | 0.24 ▼ · 92 · apr | 0.73 ▼ · 70 · rev NEx alto | 0.82 ▼ · 74 · rev |
| P4P105S300I00004 · 1-059 | 0.29 · 90 | 0.72 ▲ · 73 · rev | 0.27 ▼ · 86 · apr | 0.23 ▼ · 90 · apr |
| P4P105S300I00006 · 1-042 | 1.00 · 69 | 0.35 ▼ · 88 · apr | 0.66 ▼ · 77 · rev NEx alto | 0.73 ▼ · 77 · apr |
| P4P105S300I00006 · 1-070 | 0.47 · 89 | 0.65 ▲ · 86 · apr | 0.25 ▼ · 94 · apr | 0.37 ▼ · 92 · rev NEx baixo |
| P4P105S300I00006 · 1-078 | 0.54 · 84 | 0.51 ▼ · 90 · apr | 0.36 ▼ · 91 · apr | 0.46 ▼ · 92 · apr |
| P4P105S300I00008 · 1-078 | 0.68 · 80 | 0.31 ▼ · 96 · apr | 0.45 ▼ · 89 · apr | 0.48 ▼ · 86 · apr |
| P4P105S300I00009 · 1-078 | 0.76 · 78 | 0.47 ▼ · 95 · apr | 0.58 ▼ · 87 · rev | 0.68 ▼ · 83 · rev |
| P4P105S300I00009 · 1-081 | 0.66 · 78 | 0.32 ▼ · 93 · apr | 0.44 ▼ · 88 · apr | 0.52 ▼ · 83 · rev |
| P4P105S300I00010 · 1-056 | 0.51 · 90 | 0.47 ▼ · 86 · apr | 0.30 ▼ · 92 · rev NEx alto | 0.26 ▼ · 97 · apr |
| P4P105S300I00011 · 1-031 | 0.77 · 56 | 0.45 ▼ · 79 · rev | 0.56 ▼ · 63 · rev | 0.74 ▼ · 57 · rev |
| P4P105S300I00013 · 1-045 | 0.61 · 78 | 0.43 ▼ · 84 · apr | 0.43 ▼ · 80 · apr | 0.56 ▼ · 82 · apr |
| P4P105S300I00013 · 1-060 | 0.47 · 83 | 0.34 ▼ · 87 · apr | 0.20 ▼ · 89 · rev NEx alto | 0.26 ▼ · 93 · apr |
| P4P117S300I00005 · 1-36 | 1.87 · 63 | 0.73 ▼ · 85 · apr | 1.47 ▼ · 68 · rev | 1.35 ▼ · 69 · rev |
| P4P117S300I00006 · 1-53 | 1.15 · 62 | 0.62 ▼ · 86 · apr | 0.81 ▼ · 82 · apr | 0.99 ▼ · 76 · apr |
| P4P117S300I00008 · 1-27 | 0.92 · 73 | 0.44 ▼ · 95 · apr | 0.73 ▼ · 85 · apr | 0.72 ▼ · 85 · apr |
| P4P117S300I00008 · 1-59 | 0.79 · 47 | 0.33 ▼ · 91 · apr NEx inconclusivo | 0.58 ▼ · 54 · rev NEx inconclusivo | 0.54 ▼ · 52 · rev NEx inconclusivo |
| P4P117S301I00006 · 1-044 | 1.27 · 62 | 0.36 ▼ · 90 · apr | 0.94 ▼ · 72 · rev | 0.96 ▼ · 74 · rev |
| P4P117S301I00008 · 1-062 | 1.25 · 64 | 0.60 ▼ · 84 · apr | 1.00 ▼ · 73 · rev | 0.99 ▼ · 70 · rev |
| P4P117S301I00010 · 1-072 | 1.19 · 37 | 0.75 ▼ · 77 · rev NEx baixo | 1.00 ▼ · 61 · rev NEx baixo | 1.15 ▼ · 62 · rev |
| P4P117S302I00003 · 1-054 | 0.70 · 72 | 0.56 ▼ · 64 · rev NEx alto | 0.64 ▼ · 68 · rev NEx alto | 0.55 ▼ · 76 · rev NEx alto |
| P4P117S302I00006 · 1-036 | 0.64 · 75 | 0.57 ▼ · 72 · rev | 0.72 ▲ · 67 · rev NEx alto | 0.54 ▼ · 82 · apr |
| P4P117S302I00009 · 1-047 | 0.97 · 69 | 0.80 ▼ · 63 · rev | 0.95 ▼ · 62 · rev NEx alto | 0.67 ▼ · 78 · apr |
| P4P117S302I00010 · 1-070 | 1.14 · 42 | 0.66 ▼ · 87 · apr | 1.06 ▼ · 43 · rev NEx alto | 0.83 ▼ · 81 · apr |
| P4P117S303I00003 · 1-051 | 1.14 · 69 | 0.34 ▼ · 94 · apr | 0.87 ▼ · 78 · apr | 0.78 ▼ · 80 · apr |
| P4P117S303I00005 · 1-033 | 1.84 · 52 | 1.17 ▼ · 64 · rev NEx baixo | 1.55 ▼ · 54 · rev NEx alto | 1.61 ▼ · 50 · rev NEx alto |
| P4P117S304I00007 · 1-58 | 1.42 · 66 | 0.52 ▼ · 85 · apr | 1.07 ▼ · 73 · rev | 1.10 ▼ · 68 · rev |
| P4P117S304I00011 · 1-46 | 1.05 · 67 | 0.21 ▼ · 96 · apr | 0.75 ▼ · 76 · rev | 0.78 ▼ · 77 · apr |
| P4P117S305I00003 · 1-46 | 1.17 · 68 | 0.28 ▼ · 94 · apr | 0.84 ▼ · 75 · rev | 0.82 ▼ · 76 · rev |
| P4P117S305I00003 · 1-58 | 1.27 · 64 | 0.49 ▼ · 87 · apr | 0.91 ▼ · 71 · rev | 1.06 ▼ · 70 · rev |
| P4P117S305I00004 · 1-65 | 1.61 · 58 | 0.95 ▼ · 71 · rev | 1.29 ▼ · 62 · rev | 1.51 ▼ · 58 · rev |
| P4P117S305I00005 · 1-43 | 0.94 · 71 | 0.25 ▼ · 93 · apr | 0.72 ▼ · 81 · apr | 0.59 ▼ · 84 · apr |
| P4P117S305I00008 · 1-54 | 1.38 · 66 | 0.62 ▼ · 87 · apr | 0.92 ▼ · 69 · rev NEx alto | 1.05 ▼ · 70 · rev |
| P4P117S305I00009 · 1-49 | 1.00 · 70 | 0.22 ▼ · 97 · apr | 0.80 ▼ · 79 · apr | 0.81 ▼ · 81 · apr |
| P4P117S306I00008 · 1-53 | 1.36 · 65 | 0.68 ▼ · 80 · apr | 0.95 ▼ · 74 · apr | 1.05 ▼ · 69 · rev |
| P4P117S308I00005 · 1-044 | 1.04 · 78 | 0.29 ▼ · 97 · apr | 0.72 ▼ · 86 · rev | 0.55 ▼ · 86 · apr |
| P4P117S308I00007 · 1-065 | 0.81 · 78 | 0.50 ▼ · 96 · apr | 0.66 ▼ · 87 · apr | 0.60 ▼ · 85 · apr |
| P4P117S308I00009 · 1-039 | 1.22 · 72 | 0.19 ▼ · 90 · apr NEx inconclusivo | 0.66 ▼ · 81 · apr NEx inconclusivo | 0.76 ▼ · 76 · rev NEx inconclusivo |

Os dois cortes em que o gpbo-11 piora contra o baseline são `P4P105S300I00004 · 1-059`
(0,29 → 0,72) e `P4P105S300I00006 · 1-070` (0,48 → 0,65). Nos dois, a M12 e o nm-21 tinham
melhorado.

### Rejeições e pares inválidos

Em todas as etapas com problema, cada caso rejeitado também tem par fora de ok
(rejeições = pares). Nenhuma das melhores configurações tem rejeição ou par inválido.

- **GP-BO:** 24 de 45 etapas, todas no escopo de 5 casos, somando 65 casos rejeitados e
  120 casos gastos. Os padrões são `latent` ≥ 1,10 (rejeição em 4 ou 5 dos 5 casos, a
  mesma lição de M5), `noise_level` alto (90 a 349) e os cantos do cubo (`steps` 100,
  `noise` 349, `eta` 1). Configurações: gpbo-01, 02, 05, 06, 07, 08, 09, 13, 15, 16, 17,
  19, 21, 23, 25, 27, 28, 29, 30, 31, 35, 37, 39 e 41 (detalhe na tabela abaixo).
- **Nelder-Mead:** 2 etapas, as duas por `latent` > 1. nm-04 (`latent` 1,05) teve 4 de 5
  casos rejeitados; nm-08 (`latent` 1,025) teve 1 de 5.
- **Agente:** 1 etapa, M5 (`latent` 1,10), com 5 de 5 casos rejeitados.

### Melhora média e nota discordam no Nelder-Mead

O nm-21 passa pela regra `melhor` contra a M12: +24,44% contra +23,05% e 22 vitórias
contra 15 derrotas por corte. **Mesmo assim, a nota do juiz é menor** (75,41 contra 76,73),
a textura aprova menos (25 contra 30 de 37) e o final aprova menos (14 contra 18). O NEx
fica alto em 10 casos.

A causa está na média de 7 métricas com teto: o ganho do nm-21 está concentrado em GLCM
energia (no teto de 50) e Wavelet entropia (+46,7). NEx (+1,0), LL (+3,8) e Wavelet
grossa (+12,9) quase não melhoram. A média premia duas métricas muito boas, enquanto a nota
pune os casos com NEx alto e textura em revisão. No gpbo-11 as duas réguas concordam
(+44% e nota 85,8). No nm-21, a melhora média sozinha superestima o resultado.

### Ressalvas antes de adotar o gpbo-11

- **Teto.** 3 das 7 métricas (energia, Wavelet grossa e entropia) estão no teto de 50, e
  outras 2 (contraste 48,8 e LL 48,8) estão a menos de 1,3 ponto dele. A média de 44% é
  limitada pelo teto, e a diferença real para a M12 nas métricas saturadas fica escondida.
  Sem teto, energia sobe para 67%, grossa para 63% e entropia para 62%.
- **Ruído no fundo (ar).** Com `eta` 0,77, o ar fora do corpo sai mais ruidoso. Medi o
  desvio padrão nos pixels em que a original é constante (o valor mínimo), em % da faixa
  p1–p99 da original, média dos 37 casos: baseline 1,30, M12 1,45, nm-21 1,40 e gpbo-11
  **1,91** (+32% sobre a M12; máximo 2,57). As métricas de textura, calculadas dentro da
  máscara, não veem isso.
  - A sessão principal mediu o corte -070 em outra unidade: σ 0,0 na original, 1,6 na
    M12 e 3,3 no gpbo-11.
  - O placar marca 4 cortes do gpbo-11 como "ruído". Não verifiquei isso aqui.
- **Seed única (42).** Uma configuração só, medida uma vez. O GP escolheu o gpbo-11 entre
  41 configurações, o que favorece um resultado com sorte de ruído (maldição do vencedor).
  A melhora oscilou entre escopos: +46,6 em 5 casos, +37,7 em 10 e +44,2 em 37.
- **Extrapolação.** `latent` 0,75 e `cond` 1,5 estão nos limites do espaço, e `eta` 0,77
  fica muito acima do que o agente testou (≤ 0,4). Nenhum valor perto de `latent` 0,75 foi
  medido por outro método.
- **Parada das podadas.** No modo `podar`, o GP só aprendeu com 2 lotes completos e uma
  sequência Sobol. O sucesso dele dependeu muito do 10º e do 11º ponto, e não de um
  modelo bem ajustado.

### Todas as configurações medidas

"Melhora" é contra o baseline no escopo em que a configuração parou. V/D são as vitórias e
derrotas por corte contra a melhor atual **do próprio método** naquele escopo.

| método | # | escopo final | steps | noise | eta | latent | cond | melhora % | veredito | V/D | rej | pares |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| GP-BO | 1 | screen | 87 | 233 | 0.363 | 0.932 | 0.64 | -60.7 | pior | 0/5 | 1 | 1 |
| GP-BO | 2 | screen | 13 | 4 | 0.628 | 1.123 | 1.225 | -92.0 | pior | 1/4 | 1 | 1 |
| GP-BO | 3 | screen | 47 | 44 | 0.171 | 0.793 | 1.483 | -33.8 | insuficiente | 1/4 | 0 | 0 |
| GP-BO | 4 | screen | 75 | 0 | 0.842 | 1.23 | 0.883 | -10.1 | insuficiente | 2/3 | 0 | 0 |
| GP-BO | 5 | screen | 100 | 349 | 1.0 | 0.75 | 1.5 | -43.5 | pior | 2/3 | 4 | 4 |
| GP-BO | 6 | screen | 100 | 349 | 1.0 | 1.25 | 1.5 | -81.5 | pior | 0/5 | 4 | 4 |
| GP-BO | 7 | screen | 100 | 349 | 1.0 | 1.25 | 0.5 | -115.0 | pior | 0/5 | 3 | 3 |
| GP-BO | 8 | screen | 65 | 25 | 0.516 | 1.133 | 0.771 | -306.3 | pior | 0/5 | 4 | 4 |
| GP-BO | 9 | screen | 100 | 349 | 1.0 | 0.75 | 0.5 | -60.3 | pior | 0/5 | 2 | 2 |
| GP-BO | 10 | full | 36 | 2 | 0.469 | 0.828 | 1.372 | +19.8 | melhor **nova melhor** | 32/5 | 0 | 0 |
| GP-BO | 11 | full | 43 | 2 | 0.767 | 0.75 | 1.5 | +44.2 | melhor **nova melhor** | 30/7 | 0 | 0 |
| GP-BO | 12 | screen | 54 | 3 | 1.0 | 0.75 | 1.5 | +42.5 | insuficiente | 0/5 | 0 | 0 |
| GP-BO | 13 | screen | 25 | 90 | 0.95 | 1.029 | 1.113 | -18.0 | pior | 0/5 | 1 | 1 |
| GP-BO | 14 | screen | 98 | 9 | 0.06 | 0.962 | 0.529 | -83.9 | insuficiente | 0/5 | 0 | 0 |
| GP-BO | 15 | screen | 90 | 68 | 0.881 | 0.861 | 1.141 | +8.7 | pior | 0/5 | 1 | 1 |
| GP-BO | 16 | screen | 28 | 1 | 0.115 | 1.177 | 0.744 | -1419.0 | pior | 0/5 | 5 | 5 |
| GP-BO | 17 | screen | 39 | 252 | 0.586 | 0.973 | 0.986 | -45.5 | pior | 0/5 | 1 | 1 |
| GP-BO | 18 | screen | 56 | 6 | 0.414 | 1.035 | 1.399 | +20.7 | insuficiente | 1/4 | 0 | 0 |
| GP-BO | 19 | screen | 66 | 148 | 0.225 | 1.063 | 1.26 | -484.7 | pior | 0/5 | 5 | 5 |
| GP-BO | 20 | screen | 50 | 16 | 0.772 | 0.882 | 0.847 | +20.0 | insuficiente | 1/4 | 0 | 0 |
| GP-BO | 21 | screen | 16 | 27 | 0.309 | 1.21 | 0.605 | -1428.3 | pior | 0/5 | 5 | 5 |
| GP-BO | 22 | screen | 78 | 2 | 0.699 | 0.767 | 1.003 | +40.2 | insuficiente | 1/4 | 0 | 0 |
| GP-BO | 23 | screen | 81 | 35 | 0.085 | 1.005 | 0.916 | +18.9 | pior | 0/5 | 1 | 1 |
| GP-BO | 24 | screen | 20 | 3 | 0.913 | 0.94 | 1.441 | +28.1 | insuficiente | 1/4 | 0 | 0 |
| GP-BO | 25 | screen | 53 | 129 | 0.385 | 1.144 | 1.199 | -935.2 | pior | 0/5 | 5 | 5 |
| GP-BO | 26 | screen | 70 | 13 | 0.62 | 0.832 | 0.659 | +28.7 | insuficiente | 1/4 | 0 | 0 |
| GP-BO | 27 | screen | 58 | 348 | 0.801 | 0.804 | 0.547 | -46.6 | pior | 0/5 | 2 | 2 |
| GP-BO | 28 | screen | 42 | 7 | 0.192 | 1.235 | 1.088 | -1362.4 | pior | 0/5 | 5 | 5 |
| GP-BO | 29 | screen | 30 | 65 | 0.728 | 0.907 | 1.329 | +8.7 | pior | 0/5 | 1 | 1 |
| GP-BO | 30 | screen | 92 | 0 | 0.275 | 1.1 | 0.805 | -523.5 | pior | 0/5 | 4 | 4 |
| GP-BO | 31 | screen | 95 | 103 | 0.658 | 1.2 | 1.428 | -127.6 | pior | 0/5 | 4 | 4 |
| GP-BO | 32 | screen | 21 | 11 | 0.33 | 0.76 | 0.965 | -27.4 | insuficiente | 1/4 | 0 | 0 |
| GP-BO | 33 | screen | 33 | 19 | 0.871 | 1.089 | 0.707 | -17.2 | insuficiente | 0/5 | 0 | 0 |
| GP-BO | 34 | screen | 61 | 1 | 0.137 | 0.903 | 1.185 | -51.6 | insuficiente | 0/5 | 0 | 0 |
| GP-BO | 35 | screen | 73 | 46 | 0.44 | 0.999 | 1.046 | +17.6 | pior | 0/5 | 1 | 1 |
| GP-BO | 36 | screen | 45 | 0 | 0.549 | 1.055 | 0.568 | +18.8 | insuficiente | 0/5 | 0 | 0 |
| GP-BO | 37 | screen | 11 | 168 | 0.031 | 0.853 | 0.827 | -114.9 | pior | 0/5 | 1 | 1 |
| GP-BO | 38 | screen | 84 | 4 | 0.984 | 1.17 | 1.289 | +10.4 | insuficiente | 1/4 | 0 | 0 |
| GP-BO | 39 | screen | 85 | 41 | 0.573 | 1.105 | 0.511 | +9.7 | pior | 2/3 | 1 | 1 |
| GP-BO | 40 | screen | 12 | 0 | 0.433 | 0.918 | 1.097 | -29.8 | insuficiente | 0/5 | 0 | 0 |
| GP-BO | 41 | screen | 45 | 211 | 0.897 | 1.248 | 1.355 | -27.0 | pior | 0/5 | 3 | 3 |
| NM | 1 | full | 34 | 1 | 0.0 | 1.0 | 1.0 | +5.3 | melhor **nova melhor** | 37/0 | 0 | 0 |
| NM | 2 | full | 25 | 3 | 0.0 | 1.0 | 1.0 | +9.4 | melhor **nova melhor** | 31/6 | 0 | 0 |
| NM | 3 | screen | 25 | 1 | 0.1 | 1.0 | 1.0 | +3.6 | insuficiente | 3/2 | 0 | 0 |
| NM | 4 | screen | 25 | 1 | 0.0 | 1.05 | 1.0 | -400.1 | pior | 0/5 | 4 | 4 |
| NM | 5 | screen | 25 | 1 | 0.0 | 1.0 | 1.1 | +0.6 | insuficiente | 1/4 | 0 | 0 |
| NM | 6 | screen | 29 | 2 | 0.04 | 0.95 | 1.04 | -69.5 | insuficiente | 0/5 | 0 | 0 |
| NM | 7 | screen | 28 | 1 | 0.03 | 0.975 | 1.03 | -43.6 | insuficiente | 0/5 | 0 | 0 |
| NM | 8 | screen | 26 | 1 | 0.01 | 1.025 | 1.01 | -1.9 | pior | 3/2 | 1 | 1 |
| NM | 9 | screen | 27 | 1 | 0.025 | 0.988 | 1.025 | -31.1 | insuficiente | 0/5 | 0 | 0 |
| NM | 10 | quick | 26 | 1 | 0.015 | 1.012 | 1.015 | +18.1 | insuficiente | 5/5 | 0 | 0 |
| NM | 11 | full | 29 | 2 | 0.046 | 1.005 | 1.046 | +24.1 | melhor **nova melhor** | 33/4 | 0 | 0 |
| NM | 12 | screen | 31 | 2 | 0.069 | 1.008 | 1.069 | +18.9 | insuficiente | 2/3 | 0 | 0 |
| NM | 13 | screen | 31 | 2 | 0.064 | 1.007 | 0.924 | +18.3 | insuficiente | 2/3 | 0 | 0 |
| NM | 14 | quick | 33 | 2 | 0.0 | 1.01 | 0.994 | +16.0 | insuficiente | 4/6 | 0 | 0 |
| NM | 15 | quick | 24 | 3 | 0.05 | 1.014 | 0.992 | +13.6 | insuficiente | 4/6 | 0 | 0 |
| NM | 16 | screen | 32 | 1 | 0.07 | 1.019 | 0.989 | +17.6 | insuficiente | 3/2 | 0 | 0 |
| NM | 17 | screen | 37 | 1 | 0.028 | 1.008 | 0.995 | +17.9 | insuficiente | 2/3 | 0 | 0 |
| NM | 18 | quick | 29 | 1 | 0.089 | 1.011 | 0.994 | +19.0 | insuficiente | 5/5 | 0 | 0 |
| NM | 19 | screen | 29 | 1 | 0.027 | 0.998 | 1.001 | -0.5 | insuficiente | 0/5 | 0 | 0 |
| NM | 20 | quick | 31 | 1 | 0.059 | 1.014 | 0.992 | +12.6 | insuficiente | 4/6 | 0 | 0 |
| NM | 21 | full | 29 | 1 | 0.068 | 1.008 | 1.02 | +24.4 | melhor **nova melhor** | 20/17 | 0 | 0 |
| NM | 22 | screen | 30 | 2 | 0.055 | 1.006 | 0.985 | +19.3 | insuficiente | 1/4 | 0 | 0 |
| NM | 23 | screen | 28 | 1 | 0.03 | 1.009 | 1.03 | +25.4 | melhor | 4/1 | 0 | 0 |

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
0). No real, as pastas são `runs/real/gpbo-NN-<escopo>` e `runs/real/nm-NN-<escopo>`; o
log é `runs/real/gpbo-log.jsonl` (ou `nm-log.jsonl`), gravado a cada etapa, e o resumo
final é `<prefixo>-resumo.json`. Nada em `baseline-*` ou `candidate-*` é escrito.

**Retomada.** Se o processo cair, basta rodar o mesmo comando. O script reconstrói do log
o orçamento gasto, a melhor atual e todas as configurações medidas. Depois reinicia o
otimizador e serve as propostas já registradas a partir do log, sem custo. O Nelder-Mead
é determinístico e reproduz exatamente a mesma trajetória; isso está testado em
`tests/test_otimizador_real.py`. No GP, as propostas antigas são reenfileiradas na ordem
original. Se a proposta seguinte divergir, o log ganha uma linha `divergencia` e a busca
continua. Uma etapa interrompida com a mesma configuração é retomada pelo próprio
`run_batch.py`. Uma pasta interrompida de outra configuração é renomeada para
`...-abandonado-<data>`, e os casos gerados nela contam no orçamento.

A trajetória do agente é convertida para o mesmo formato a partir dos relatórios M4–M12:

```bash
python tools/otimizador_real.py agente
```

A curva melhor melhora em 37 casos × casos gerados (CSV, e PNG se houver matplotlib):

```bash
python tools/otimizador_real.py curva runs/otimizador-curvas/agente/log.jsonl runs/real/gpbo-log.jsonl runs/real/nm-log.jsonl
```

## Como rodar no real (só com autorização humana para gerar na GPU)

`tools/rodar_otimizadores_real.sh` roda GP-BO e depois Nelder-Mead, um de cada vez, com
até 3 tentativas por método, retomando a cada uma. Ele pode rodar a partir de um
worktree deste branch, sem trocar o branch do checkout principal:

1. No worktree, crie o venv do otimizador e aponte `data/` para o checkout principal. O
   venv fica em `.venv/`, ignorado pelo git; o link `data` vai em `.git/info/exclude`.

   ```bash
   ../../../.venv/bin/python -m venv .venv && .venv/bin/pip install "numpy==1.26.4" "torch==2.0.1" -r tools/requirements-otimizador.txt
   ```

   ```bash
   ln -s "$PWD/../../../data" data
   ```

2. Confira o primeiro comando, sem gerar nada:

   ```bash
   TEXTURE_EVALUATOR_REPO=../../../../synthetic-lung-ct-evaluation .venv/bin/python tools/otimizador_real.py otimizar --method gp --backend real --dry-run --python ../../../.venv/bin/python --baseline-dir ../../../runs/real
   ```

3. Rode em segundo plano. São cerca de 2,1 min por caso (medido em `candidate-12-full`),
   ou seja, cerca de 9,5 h por método e 19 h no total.

   ```bash
   LAB_MAIN="$PWD/../../.." nohup tools/rodar_otimizadores_real.sh > ../../../runs/real/otimizadores-real.out 2>&1 &
   ```

4. Ao terminar, gere a curva com os três logs e registre cada configuração no CADERNO, na
   seção "Experimento separado: otimizadores clássicos (O)".

Em 2026-10-23 estava aberta no checkout principal uma sessão de agente (`claude
--settings .agente/settings.json`), ociosa. Se ela gerar ao mesmo tempo, as duas disputam
a GPU e o tempo dobra.

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
