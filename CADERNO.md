# Caderno de experimentos

Uma entrada por tentativa, na ordem em que foram feitas, inclusive as que
pioraram ou falharam. Nada é apagado nem reescrito: uma correção vira uma
entrada nova que cita a anterior.

Cada entrada responde a quatro perguntas antes dos números:

- **Hipótese:** o que você espera que mude e por quê (cite `literatura/` quando houver base).
- **Mudança:** exatamente o que foi alterado; de preferência uma variável por vez.
- **Resultado:** o que o relatório e as prévias mostraram, por métrica e pelos piores casos, não só a nota.
- **Lição:** o que a tentativa ensina para a próxima, mesmo quando não melhorou.

## Modelo

```markdown
## NNN · nome-curto · AAAA-MM-DD

- Configuração: `workspace/candidate.json` = {...}
- Comandos e pastas: `runs/real/...`
- Comparado com: NNN (mesmos casos e semente)

**Hipótese.** ...

**Mudança.** ...

**Resultado.**

| indicador | antes | depois |
|---|---|---|
| textura (aprovada / revisão / reprovada) | | |
| brilho (aprovada / revisão / reprovada) | | |
| ... | | |

Piores casos e o que as prévias mostram: ...

**Lição.** ...

**Decisão.** promovida para 37 casos / nova melhor / descartada, e por quê.
```

---

## 000 · baseline · 2026-10-21

- Imagens: as 37 sintéticas válidas do Dsr que acompanham o avaliador,
  geradas pelo checkpoint atual (`models/model_ldm_pulmao_Dsr_best.pth`).
  Os parâmetros de amostragem desse lote ainda precisam ser confirmados com o
  Dayvison; `configs/baseline.json` traz o ponto de partida da busca
  (`steps` 25, `noise_level` 1, `ddim`, `scale_factor` 1.0, `seed` 42).
- Medido com: boletim do avaliador na tag `juiz-v1` (commit `3f334f0`),
  calibração `dsr-v1` (sha256 `dd6f732c…`).
- Comparado com: nada; esta é a referência das próximas entradas.

**Hipótese.** Nenhuma: a entrada só fixa o ponto de partida.

**Mudança.** Nenhuma.

**Resultado.**

| indicador | valor |
|---|---|
| textura (aprovada / revisão / reprovada) | 8 / 29 / 0 |
| brilho (aprovada / revisão / reprovada) | 35 / 2 / 0 |
| veredito final (aprovada / revisar / rejeitar) | 3 / 34 / 0 |
| Wavelet 2 px, mediana | 54% da original |
| Wavelet 4 px, mediana | 66% da original |
| razão 2 px ÷ 4 px | 0,83 |
| GLCM contraste, mediana | 60% da original (Δ −0,93 IQR) |
| GLCM energia, mediana | 133% da original (Δ +0,22 IQR) |
| \|Δμ\| de brilho, mediana | 0,14 |
| NEx fora da faixa real | 6 cortes altos, 2 inconclusivos |
| tipo de mudança (Wavelet) | 27 borrou, 5 perdeu contraste, 5 preservada |

**Lição.** O brilho está praticamente resolvido; o problema é textura. As
sintéticas perdem detalhe fino mais do que grosso (razão abaixo de 1) e ficam
mais lisas (energia GLCM acima de 100%). Qualquer tentativa deve ser julgada
primeiro por Wavelet 2 px, contraste GLCM e NEx, sem deixar o brilho piorar.

**Decisão.** Referência das próximas comparações.

## 001 · baseline-local-falhou-calibracao-ausente · 2026-10-22

- Configuração: `workspace/candidate.json` = {"steps": 25, "noise_level": 1, "sampler": "ddim", "scale_factor": 1.0, "seed": 42}
- Comando e pasta: `.venv/bin/python generator/run_batch.py --scope quick --config workspace/candidate.json --output-dir runs/real/baseline-quick`
- Comparado com: nada; tentativa de estabelecer o baseline local nos 7 casos fixos.

**Hipótese.** A configuração inicial reproduziria localmente o ponto de partida e permitiria medir os mesmos sete casos antes do lote completo.

**Mudança.** Nenhuma alteração de parâmetros; primeira execução da configuração inicial.

**Resultado.** A geração do primeiro dos sete cortes terminou, mas a avaliação falhou antes de produzir `report.json` ou `boletim.json`. O avaliador externo tentou ler `frameworks/texture_evaluator/calibracao/dsr-v1.json`, que não existe na instalação local, e encerrou com `FileNotFoundError`. Portanto não há nota, contagens de vereditos, deltas, intervalos de confiança ou métricas por imagem desta tentativa. Ficaram salvos somente o primeiro sintético e seu metadado em `runs/real/baseline-quick/synthetics/`.

Piores casos e o que as prévias mostram: não aplicável, pois a avaliação falhou no primeiro caso e nenhuma prévia comparativa foi produzida.

**Lição.** A preparação do ambiente está incompleta para a avaliação real. Sem a calibração congelada não é possível estabelecer um baseline comparável nem escolher com segurança uma próxima hipótese.

**Decisão.** Busca interrompida por bloqueio de ambiente. Nenhum candidato foi promovido e nenhum parâmetro foi alterado; a calibração congelada deve ser restaurada por um humano antes de repetir exatamente o mesmo comando e a mesma pasta.

## 002 · baseline-local-concluido · 2026-10-22

- Configuração: `workspace/candidate.json` = {"steps": 25, "noise_level": 1, "sampler": "ddim", "scale_factor": 1.0, "seed": 42}
- Comandos e pastas: `runs/real/baseline-quick` (7 casos) e `runs/real/baseline-full` (37 casos, com reaproveitamento do rápido)
- Comparado com: nada; baseline local da busca. Esta entrada corrige e completa a tentativa 001 depois que a calibração congelada foi restaurada por um humano.

**Hipótese.** A configuração inicial estabeleceria uma referência local válida, com correlação de pares preservada e margem principal de melhora nas métricas de textura.

**Mudança.** Nenhuma alteração de parâmetros. A execução rápida interrompida foi repetida na mesma pasta e, depois de concluída, promovida obrigatoriamente ao lote completo.

**Resultado.** O rápido obteve nota 66,3936, com veredito final 1/6/0 (aprovada/revisar/rejeitar), textura 2/5/0 e brilho 6/1/0. O lote completo obteve nota 68,9226 e permaneceu válido para comparação.

| indicador | rápido (7) | completo (37) |
|---|---:|---:|
| nota | 66,3936 | 68,9226 |
| textura (aprovada / revisão / reprovada) | 2 / 5 / 0 | 21 / 16 / 0 |
| brilho (aprovada / revisão / reprovada) | 6 / 1 / 0 | 34 / 3 / 0 |
| final (aprovada / revisar / rejeitar) | 1 / 6 / 0 | 7 / 30 / 0 |
| pares válidos | 7 / 7 | 37 / 37 |
| GLCM contraste, mediana | 85,83% | 78,62% |
| GLCM energia, mediana | 177,89% | 177,89% |
| Wavelet 2 px, mediana | 88,45% | 80,50% |
| Wavelet 4 px, mediana | 77,36% | 79,20% |
| razão Wavelet 2 px ÷ 4 px, mediana | 1,0157 | 0,9966 |
| correlação do par, mediana | 0,9156 | 0,9242 |
| correlação do mapa de textura, mediana | 0,8559 | 0,8921 |
| área de textura preservada, mediana | 17,86% | 18,87% |
| \|Delta mu\| de brilho, mediana | 0,2101 | 0,1769 |
| deslocamento de densidade, mediana (IQR) | -0,6619 | -0,5615 |
| NEx (sintética - original), mediana | +0,0417 | +0,0092 |

No boletim completo, os deltas medianos e IC95% foram: GLCM contraste -0,463 [-0,588; -0,362], GLCM energia +0,604 [+0,521; +0,727], Wavelet 2 px -0,476 [-0,546; -0,317], Wavelet 4 px -0,470 [-0,575; -0,386], entropia Wavelet -0,690 [-0,863; -0,464], LL -0,562 [-0,686; -0,268] e NEx +0,009 [-0,081; +0,142]. Houve 5 NEx altos, 1 baixo e 2 inconclusivos; 4 cortes escureceram por densidade.

Piores casos: `P4P117S301I00010...1-072` (nota 36,5834) combinou revisão de brilho/densidade com textura enfraquecida; `P4P117S302I00010...1-070` (41,7654) combinou escurecimento e NEx alto; `P4P117S300I00008...1-59` (47,0201) escureceu apesar de textura global aprovada; `P4P117S303I00005...1-033` (51,5820) teve apenas 48,20% de detalhe fino, 52,32% grosso, 51,77% de contraste GLCM e 0% da área classificada como preservada. As prévias e mapas são coerentes com perda de textura/contraste e, nos casos de brilho, escurecimento difuso.

**Lição.** O baseline é válido e conserva a anatomia, mas suaviza sistematicamente a textura: contraste e Wavelets ficam abaixo da original e a energia GLCM fica alta. Como o brilho já é aprovado em 34/37, a próxima mudança deve ser pequena e buscar detalhe/contraste sem criar novos casos de brilho, densidade, NEx ou correlação problemáticos.

**Decisão.** Baseline local fixado como melhor rápido e melhor completo iniciais. Conta como a primeira das 10 configurações.

## 003 · passos-35 · 2026-10-22

- Configuração: `workspace/candidate.json` = {"steps": 35, "noise_level": 1, "sampler": "ddim", "scale_factor": 1.0, "seed": 42}
- Comandos e pastas: `runs/real/candidate-01-quick` e `runs/real/candidate-01-full`
- Comparado com: 002 (25 passos; mesmos casos e semente)

**Hipótese.** Aumentar somente os passos DDIM de 25 para 35 daria uma discretização mais fina da trajetória de amostragem e poderia recuperar contraste e detalhe sem alterar ruído inicial, escala ou semente.

**Mudança.** `steps`: 25 -> 35. Todos os outros parâmetros permaneceram congelados.

**Resultado.** No rápido, a nota subiu de 66,3936 para 68,5735 (+2,1799) sem rejeições adicionais; o comparador declarou `melhor`. A textura passou de 2/5/0 para 5/2/0, o brilho permaneceu 6/1/0 e a energia GLCM melhorou claramente, embora a correlação do mapa tivesse uma pequena piora. A promoção completa confirmou a hipótese: nota 71,3001 contra 68,9226 (+2,3775), com decisão `melhor` e validade preservada.

| indicador completo | 25 passos | 35 passos |
|---|---:|---:|
| nota | 68,9226 | 71,3001 |
| textura (aprovada / revisão / reprovada) | 21 / 16 / 0 | 26 / 11 / 0 |
| brilho (aprovada / revisão / reprovada) | 34 / 3 / 0 | 34 / 3 / 0 |
| final (aprovada / revisar / rejeitar) | 7 / 30 / 0 | 12 / 25 / 0 |
| pares válidos | 37 / 37 | 37 / 37 |
| GLCM contraste, mediana | 78,62% | 81,08% |
| GLCM energia, mediana | 177,89% | 170,67% |
| Wavelet 2 px, mediana | 80,50% | 82,60% |
| Wavelet 4 px, mediana | 79,20% | 81,19% |
| razão Wavelet, mediana | 0,9966 | 1,0050 |
| correlação do par, mediana | 0,9242 | 0,9229 |
| correlação do mapa, mediana | 0,8921 | 0,8904 |
| textura preservada, mediana | 18,87% | 20,37% |
| \|Delta mu\|, mediana | 0,1769 | 0,1685 |
| densidade, mediana (IQR) | -0,5615 | -0,5339 |
| NEx, mediana | +0,0092 | +0,0131 |

Na comparação corte a corte, a fração de aprovações melhorou 13,51 p.p. (IC95% +2,70 a +24,32), e a energia GLCM ganhou 8,89 pontos rumo ao ideal (IC95% +7,80 a +10,25). Houve ganhos pequenos mas consistentes em Wavelet fina (+2,08), Wavelet grossa (+1,64), contraste GLCM (+1,87), brilho por `|Delta mu|` (+0,0082) e LL (+0,0029). A regressão foi uma pequena queda da correlação do mapa de textura (-0,00119; IC95% -0,00169 a -0,00061); a correlação mediana do par também caiu levemente, sem invalidar qualquer caso. NEx permaneceu essencialmente neutro (5 altos e 2 inconclusivos) e os casos escuros caíram de 4 para 3.

Piores casos permaneceram os mesmos grupos anatômicos: `P4P117S301I00010...1-072` (37,7549), `P4P117S302I00010...1-070` (44,5296), `P4P117S300I00008...1-59` (49,2820) e `P4P117S303I00005...1-033` (52,8544). Todos melhoraram a nota em relação ao baseline, mas as prévias ainda mostram escurecimento nos três primeiros quando indicado pelo boletim e forte perda de textura no último (aproximadamente 50% de detalhe fino e 54% grosso/GLCM).

**Lição.** A direção de mais passos é benéfica entre 25 e 35: melhora simultaneamente detalhe fino, grosso, contraste e energia sem piorar as contagens de brilho, validade ou rejeição. O ganho ainda não saturou claramente, mas a pequena perda de correlação do mapa exige aumentos controlados.

**Decisão.** Nova melhor configuração, confirmada nos 37 casos. Conta como a segunda das 10 configurações.

## 004 · passos-45 · 2026-10-22

- Configuração: `workspace/candidate.json` = {"steps": 45, "noise_level": 1, "sampler": "ddim", "scale_factor": 1.0, "seed": 42}
- Comando e pasta: `runs/real/candidate-02-quick`
- Comparado com: 003 (35 passos; mesmos 7 casos e semente)

**Hipótese.** Se o ganho de 25 para 35 passos ainda não estivesse saturado, mais 10 passos poderiam recuperar detalhe adicional sem alterar os demais parâmetros.

**Mudança.** `steps`: 35 -> 45. Nenhum outro parâmetro mudou.

**Resultado.** A nota rápida caiu de 68,5735 para 67,7301 (-0,8434), e o comparador declarou `pior`. A textura regrediu de 5/2/0 para 4/3/0; brilho permaneceu 6/1/0, veredito final permaneceu 2/5/0 e todos os 7 pares continuaram válidos. Contra 35 passos, Wavelet grossa perdeu 1,60 ponto rumo ao ideal (IC95% -2,94 a -1,24), a razão Wavelet piorou 0,0184 (IC95% -0,0278 a -0,0012) e a correlação do mapa caiu 0,0112 (IC95% -0,0148 a -0,0051). Não houve melhora clara nas demais métricas; `|Delta mu|` e LL também tenderam a piorar. O caso `P4P117S302I00009...1-047` voltou a apresentar excesso de detalhe fino/ruído (118%) e NEx alto (+0,697), enquanto o caso `P4P105S300I00011...1-031` caiu para 66% fino e 52% grosso.

**Lição.** O ganho por aumentar passos não é monotônico; 45 ultrapassa a região favorável observada em 35 e piora detalhe grosso, equilíbrio fino/grosso e correlação espacial. O ótimo de passos provavelmente está entre 35 e 45 ou próximo de 35.

**Decisão.** Descartada no rápido e não promovida aos 37 casos. A melhor permanece 003 (35 passos). Conta como a terceira das 10 configurações.

## 005 · passos-40-interrompido · 2026-10-22

- Configuração testada: `workspace/candidate.json` = {"steps": 40, "noise_level": 1, "sampler": "ddim", "scale_factor": 1.0, "seed": 42}
- Comando e pasta: `runs/real/candidate-03-quick`
- Comparado com: 003 (35 passos; mesmos 7 casos e semente)

**Hipótese.** Testar o ponto intermediário entre 35 e 45 passos poderia indicar se o máximo local estava acima de 35 sem repetir o salto que piorou em 45.

**Mudança.** `steps`: 35 -> 40. Nenhum outro parâmetro mudou.

**Resultado.** A execução foi interrompida por decisão humana durante a geração do sétimo caso, depois de 6/7 casos avaliados. O relatório parcial registra nota 68,8110, textura 3/3/0, brilho 5/1/0, veredito final 2/4/0 e 6/6 pares válidos. Como falta um dos sete casos e o relatório parcial não contém decisão comparativa, esses números não sustentam promoção nem comparação com 35 passos. A pasta e o relatório parcial foram preservados. Não foi executado lote completo.

Nos seis cortes concluídos, as medianas parciais foram: Wavelet fina 91,69%, Wavelet grossa 80,71%, razão 1,0305, contraste GLCM 88,48%, energia GLCM 173,99%, correlação do par 0,9119, correlação do mapa 0,8504, área preservada 18,94%, `|Delta mu|` 0,2370, densidade -0,7653 e NEx +0,0245. Houve um NEx alto, um inconclusivo e um corte mais escuro. Esses valores são apenas descritivos porque o subconjunto incompleto pode enviesar as medianas.

**Lição.** Um lote rápido incompleto não deve ser usado para declarar melhora ou piora. O resultado completo já confirmado em 35 passos é suficiente para encerrar a busca com uma melhora defensável, enquanto 45 passos mostrou regressão.

**Decisão.** Tentativa encerrada a pedido do humano, não promovida e não considerada candidata válida. `workspace/candidate.json` foi restaurado para a melhor configuração confirmada, 003 (35 passos). A busca termina com 4 configurações iniciadas dentro do limite de 10, das quais 3 tiveram lote rápido completo e 2 tiveram lote completo de 37 casos.

## 006 · migracao-para-regra-de-promocao-v2 · 2026-10-22

- Configuração preservada como ponto de partida: `steps=35`, `noise_level=1`, `sampler=ddim`, `scale_factor=1.0`, `seed=42`.
- Relatórios: `runs/real/candidate-01-quick` (10 casos) e `runs/real/candidate-01-full` (37 casos).
- Comparado com: baseline fixo de 25 passos, usando a nova média das sete distâncias até a original.

**Hipótese.** A melhor configuração encontrada pela busca anterior deve ser preservada como ponto de partida operacional, mesmo após a adoção de uma régua de promoção mais exigente.

**Mudança.** Nenhum sintético foi regenerado. Os relatórios rápidos foram reconstruídos com os 10 casos atuais reaproveitando os lotes completos, e a busca passou a distinguir explicitamente o baseline fixo da melhor configuração disponível.

**Resultado.** Com a nova régua, 35 passos melhora em média 7,4570% nos 10 casos e 7,7633% nos 37 casos contra o baseline. Portanto recebe o veredito `insuficiente` diante do novo mínimo de 15%, embora continue sendo o melhor resultado completo disponível da busca anterior e mantenha nota 71,3001, sem novas rejeições ou problemas de pareamento.

**Lição.** “Melhor disponível” e “aprovada pela régua atual” são conceitos diferentes. A próxima busca pode começar de 35 passos para escolher hipóteses, mas uma nova promoção precisa alcançar pelo menos 15% contra o baseline fixo e superar os 7,7633% da melhor disponível nos 37 casos.

**Decisão.** `candidate-01-full` foi registrado como ponto de partida da próxima busca; o baseline de 25 passos permanece imutável como régua científica.
