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

## 007 · condicionamento-1.10 · 2026-10-22

- Configuração 2/5 do orçamento atual: `workspace/candidate.json` = {"steps": 35, "noise_level": 1, "sampler": "ddim", "scale_factor": 1.0, "seed": 42, "eta": 0.0, "latent_noise_scale": 1.0, "conditioning_noise_scale": 1.1}
- Comandos e pastas planejados: `runs/real/candidate-04-screen`, com promoção cumulativa para `candidate-04-quick` e `candidate-04-full` somente após veredito `melhor` em cada estágio.
- Comparado com: baseline fixo de 25 passos; a melhor completa atual é 006/003 (35 passos e escalas neutras).

**Hipótese antes da execução.** A melhor atual ainda apresenta suavização ampla: energia GLCM mediana de 170,67% da original, contraste GLCM de 81,08%, Wavelet fina de 82,60%, Wavelet grossa de 81,19% e somente 20,37% da área de textura preservada. Aumentar levemente apenas `conditioning_noise_scale` deve reduzir a tendência de copiar a condição suavizada e deixar o prior reconstruir textura. Espera-se que os módulos das distâncias de contraste GLCM, energia GLCM e Wavelets fina/grossa diminuam, com entropia e LL também caminhando para zero; NEx, brilho, densidade, correlação do par e correlação do mapa não devem piorar. O incremento é pequeno porque já existem 5 casos com NEx alto e a correlação do mapa caiu levemente ao passar de 25 para 35 passos.

**Mudança.** `conditioning_noise_scale`: 1,00 -> 1,10. Todos os demais parâmetros permanecem iguais à melhor atual.

**Resultado.** Nos 5 casos, o relatório declarou `insuficiente`: melhora média de 7,4492% contra o baseline, abaixo dos 15% exigidos. Em comparação com a triagem da melhor atual, seis componentes tiveram ganho relativo adicional contra o baseline: contraste GLCM 9,0403% versus 7,9452%; energia GLCM 13,3075% versus 12,1191%; Wavelet fina 8,7104% versus 7,7248%; grossa 9,6530% versus 7,9134%; entropia 12,1937% versus 9,4310%; LL 2,5065% versus 2,4631%. Porém NEx regrediu de +0,8854% para -3,2669%, derrubando o ganho médio e a nota para 61,2778 (0,7936 acima do baseline, mas cerca de 0,79 abaixo da melhor atual). Permaneceram 5/5 pares válidos, textura 2/3/0, brilho 4/1/0, um NEx alto, um baixo e um inconclusivo. Os casos continuaram heterogêneos: `...S302...1-047` teve Wavelet fina excessiva (~120%) e NEx alto (+0,671), enquanto `...S300...1-36` ficou com detalhe fino/grosso baixo (~71%/75%) e NEx baixo (-0,660); `...S300...1-59` manteve escurecimento.

**Lição.** Aumentar levemente o ruído da condição deslocou as métricas de textura na direção esperada, mas não de forma defensável: agravou os extremos bidirecionais de NEx e reduziu a nota. A hipótese de liberar mais o prior por esse controle fica rejeitada neste nível; não se deve elevar ainda mais o mesmo parâmetro após o sinal de ruído espúrio.

**Decisão.** Descartada na triagem de 5 casos; não promovida para 10. A melhor completa permanece a configuração de 35 passos e controles neutros.

## 008 · eta-0.10 · 2026-10-22

- Configuração 3/5 do orçamento atual: `workspace/candidate.json` = {"steps": 35, "noise_level": 1, "sampler": "ddim", "scale_factor": 1.0, "seed": 42, "eta": 0.1, "latent_noise_scale": 1.0, "conditioning_noise_scale": 1.0}
- Comandos e pastas planejados: `runs/real/candidate-05-screen`, com promoção cumulativa para `candidate-05-quick` e `candidate-05-full` apenas mediante `melhor`.
- Comparado com: baseline fixo; melhor atual de 35 passos, `eta=0` e escalas neutras.

**Hipótese antes da execução.** O defeito dominante segue sendo suavização, mas elevar o ruído da condição produziu extremos opostos de NEx. Uma estocasticidade DDIM pequena (`eta=0,10`) pode recuperar variação fina ao longo da trajetória sem aumentar diretamente a corrupção da condição. Espera-se diminuir os módulos de Wavelet fina, entropia e contraste/energia GLCM e aumentar a área preservada. Para confirmar a hipótese, NEx alto/baixo, correlação do par/mapa, brilho e densidade não podem piorar; uma melhora média abaixo de 15% também impede promoção.

**Mudança.** A partir da melhor atual, apenas `eta`: 0,00 -> 0,10. `conditioning_noise_scale` foi restaurado a 1,00; os demais parâmetros permanecem congelados.

**Resultado.** A triagem permaneceu válida, mas recebeu `insuficiente`: melhora média de 12,3427% contra o baseline, abaixo do limiar de 15%. As sete distâncias responderam na direção esperada e superaram a triagem da melhor atual: contraste GLCM 9,7000%, energia GLCM 14,0201%, Wavelet fina 10,5180%, grossa 11,5058%, entropia 17,8815%, LL 6,3849% e NEx 16,3888% de melhora contra o baseline. A nota foi 62,4282 (+1,9440 sobre o baseline e cerca de +0,365 sobre a melhor atual na mesma triagem). Houve 5/5 pares válidos, textura 2/3/0, brilho 4/1/0, NEx 3 ok/1 baixo/1 inconclusivo e densidade 4 ok/1 escuro. A correlação mediana do par foi 0,9108 e a do mapa 0,8410. O caso `...S302...1-047`, antes com NEx alto nas configurações neutra e de condicionamento, passou a aprovado e NEx +0,480; `...S300...1-36` continuou com NEx baixo (-0,660) e perda de contraste, enquanto `...S300...1-59` permaneceu escuro.

**Lição.** Uma pequena estocasticidade DDIM teve efeito mais equilibrado que aumentar o ruído da condição: melhorou todas as sete distâncias e eliminou o NEx alto da triagem, sem novos problemas de pareamento ou brilho. O ganho ficou 2,6573 pontos percentuais aquém da promoção, mas a resposta conjunta fornece evidência causal para um incremento adicional pequeno de `eta`.

**Decisão.** Não promovida porque o veredito foi `insuficiente`; serve como evidência de tendência para a tentativa seguinte. A melhor completa permanece a configuração de 35 passos e `eta=0`.

## 009 · eta-0.20 · 2026-10-22

- Configuração 4/5 do orçamento atual: `workspace/candidate.json` = {"steps": 35, "noise_level": 1, "sampler": "ddim", "scale_factor": 1.0, "seed": 42, "eta": 0.2, "latent_noise_scale": 1.0, "conditioning_noise_scale": 1.0}
- Comandos e pastas planejados: `runs/real/candidate-06-screen`, seguido de `candidate-06-quick` e `candidate-06-full` somente se cada relatório anterior disser `melhor`.
- Comparado com: baseline fixo; melhor atual completa de 35 passos e `eta=0`.

**Hipótese antes da execução.** A passagem de `eta=0` para 0,10 melhorou conjuntamente as sete distâncias na triagem, elevando a média de 6,9260% para 12,3427%, sem rejeições nem pares problemáticos. Elevar somente `eta` para 0,20 deve continuar recuperando detalhe/entropia e pode ultrapassar 15%, sobretudo por Wavelets, energia GLCM e NEx. A hipótese será refutada se surgir ruído espúrio (Wavelet/NEx excessivos), se correlação, brilho ou densidade piorarem, ou se a melhora agregada não alcançar 15%.

**Mudança.** `eta`: 0,10 -> 0,20, mantendo `steps=35` e os demais controles iguais à melhor atual.

**Resultado.** O relatório declarou `insuficiente` por margem estreita: melhora média de 14,5458% contra o baseline, 0,4542 ponto percentual abaixo de 15%. Todas as sete distâncias melhoraram: contraste GLCM 11,0879%, energia GLCM 18,8027%, Wavelet fina 11,6771%, grossa 13,9803%, entropia 23,7808%, LL 10,4192% e NEx 12,0726%. A nota subiu para 63,0815 (+2,5973 sobre o baseline); textura foi 3/2/0, brilho 4/1/0, todos os 5 pares ficaram `ok`, com um caso escuro e um NEx alto. A área preservada média subiu para 23,55%, a correlação mediana do par para 0,9131 e a do mapa para 0,8414. Entretanto, `...S302...1-047` voltou a NEx alto (+0,604), enquanto `...S105...1-031` ainda mostrou baixos detalhe fino/grosso e contraste (~66%/54%/65%).

**Lição.** A resposta de `eta` permaneceu favorável e aproximadamente monotônica no agregado de 0 a 0,20, mas NEx individual não é monotônico: o caso alto eliminado em 0,10 reapareceu em 0,20. Como faltou menos de meio ponto percentual para o limiar, cabe apenas um incremento final menor, limitado pelo risco de ruído espúrio.

**Decisão.** Não promovida porque o veredito formal foi `insuficiente`. A evidência sustenta uma última extrapolação conservadora de `eta`.

## 010 · eta-0.25 · 2026-10-22

- Configuração 5/5 do orçamento atual: `workspace/candidate.json` = {"steps": 35, "noise_level": 1, "sampler": "ddim", "scale_factor": 1.0, "seed": 42, "eta": 0.25, "latent_noise_scale": 1.0, "conditioning_noise_scale": 1.0}
- Comandos e pastas planejados: `runs/real/candidate-07-screen`, com promoção para `candidate-07-quick` e `candidate-07-full` somente mediante `melhor` em cada estágio.
- Comparado com: baseline fixo; melhor atual completa de 35 passos e `eta=0`.

**Hipótese antes da execução.** A série controlada `eta=0,00 -> 0,10 -> 0,20` elevou a melhora média da triagem de 6,9260% para 12,3427% e 14,5458%, com resposta favorável nas sete distâncias. Um incremento final menor para 0,25 pode fornecer o ganho residual de 0,4542 p.p. necessário para promoção sem o risco de um salto maior. Esperam-se ganhos sobretudo em energia GLCM, entropia e LL; Wavelets e contraste devem não regredir. O caso de NEx alto em 0,20 exige que rejeições e problemas de par permaneçam iguais ao baseline e que os extremos individuais não se agravem materialmente.

**Mudança.** `eta`: 0,20 -> 0,25. Nenhum outro parâmetro mudou.

**Resultado parcial — 5 casos.** O relatório declarou `melhor` por margem mínima: melhora média de 15,0084% contra o baseline, sem perda de validade. As sete distâncias tiveram ganhos: contraste GLCM 11,6983%, energia GLCM 21,1666%, Wavelet fina 11,8997%, grossa 14,8640%, entropia 24,9379%, LL 12,4187% e NEx 8,0734%. A nota foi 63,3746 (+2,8904 sobre o baseline); textura ficou 3/2/0, brilho 4/1/0 e pares 5/5 `ok`. Um caso permaneceu escuro e `...S302...1-047` permaneceu com NEx alto (+0,611); os demais três NEx avaliáveis ficaram `ok`, além de um inconclusivo. Correlação mediana do par foi 0,9141, correlação do mapa 0,8414 e área preservada média 24,22%.

**Lição parcial.** O incremento menor acrescentou ganho suficiente em energia GLCM, Wavelet grossa, entropia e LL para cruzar a régua, sem agravar as contagens de validade. A margem de apenas 0,0084 p.p. e o NEx alto individual tornam indispensável a confirmação nos 10 casos.

**Decisão parcial.** Promovida de 5 para 10 casos conforme o funil. Resultado final pendente.

**Resultado final — 10 casos.** A confirmação recebeu `insuficiente`: melhora média de 13,6621% contra o baseline, abaixo de 15%. Energia GLCM (+23,2558%), entropia Wavelet (+24,0227%), Wavelet grossa (+14,8519%) e LL (+11,3573%) conservaram ganhos fortes, mas contraste GLCM (+9,8184%), Wavelet fina (+8,8911%) e sobretudo NEx (+3,4375%) diluíram a média. A nota foi 70,3969 (+5,8656 sobre o baseline rápido); textura 7/3/0, brilho 9/1/0, final 2/8/0, pares 10/10 `ok`, NEx 7 ok/2 altos/1 inconclusivo e densidade 8 ok/2 escuros. As prévias confirmaram heterogeneidade: no corte apical `...S105...1-031`, a sintética manteve a anatomia global mas mostrou textura pulmonar visualmente mais uniforme, coerente com fino/grosso/contraste baixos; em `...S302...1-047`, a anatomia permaneceu alinhada, mas a textura fina/NEx ficou excessiva; em `...S302...1-070`, a prévia mostrou escurecimento difuso sutil coerente com o alerta de densidade.

**Lição final.** `eta` melhora de forma consistente energia GLCM, entropia e LL nesta faixa, mas o efeito não generaliza com força suficiente para contraste, detalhe fino e NEx. O cruzamento por apenas 0,0084 p.p. nos 5 casos não se sustentou ao adicionar outros 5, demonstrando por que o funil cumulativo é necessário.

**Decisão final.** Descartada nos 10 casos e não promovida aos 37. Como nenhuma configuração nova concluiu o lote completo, a melhor completa permanece `candidate-01-full`: 35 passos, `noise_level=1`, `eta=0`, escalas latente e de condicionamento 1,0. `workspace/candidate.json` foi restaurado para essa configuração. O orçamento de 5/5 configurações foi encerrado.

## 011 · encerramento-orcamento-5 · 2026-10-22

- Configuração 1/5: melhor inicial, 35 passos e controles neutros; relatório completo existente com melhora média de 7,7633%, veredito `insuficiente`, nota 71,3001 e 37/37 pares válidos.
- Configuração 2/5: `conditioning_noise_scale=1,10`; triagem 7,4492%, `insuficiente`; regressão de NEx e nota.
- Configuração 3/5: `eta=0,10`; triagem 12,3427%, `insuficiente`; melhora nas sete distâncias, sem promoção.
- Configuração 4/5: `eta=0,20`; triagem 14,5458%, `insuficiente`; um NEx alto reapareceu.
- Configuração 5/5: `eta=0,25`; triagem 15,0084%, `melhor`; confirmação em 10 casos 13,6621%, `insuficiente`; sem lote completo.

**Conclusão.** Nenhuma nova configuração satisfez o funil completo 5 -> 10 -> 37, portanto não há nova melhor defensável. O melhor relatório completo continua sendo `runs/real/candidate-01-full/report.json`. Contra o baseline completo, ele melhora contraste GLCM 8,5576%, energia GLCM 14,0794%, Wavelet fina 8,7300%, grossa 8,5875%, entropia 10,9169%, LL 1,8004% e NEx 1,6716%; a média de 7,7633% ainda fica abaixo da régua atual de 15%. Limitações: o candidato mais promissor foi observado apenas em 10 casos, mostrou dois NEx altos e dois cortes escuros, e não pode ser extrapolado para 37 casos nem aceito como melhor completa.

## 012 · correção-da-regra-de-promoção · 2026-10-23

Esta entrada atualiza a interpretação da 011 sem apagar o histórico. A meta absoluta de
15% deixou de bloquear a promoção: agora uma candidata avança quando supera diretamente
a melhor operacional do mesmo escopo, vence em mais cortes do que perde pela distância
conjunta das sete métricas e não acrescenta rejeições ou pares inválidos. Os 15% continuam
registrados separadamente como meta forte.

Nenhuma imagem foi regenerada. Os relatórios existentes de `eta=0,25` foram apenas
recalculados contra `candidate-01` do mesmo escopo. Na triagem, a melhora foi 15,0084%
contra 6,9260% da melhor atual, com 4 vitórias e 1 derrota. Nos 10 casos, foi 13,6621%
contra 7,4570%, com 8 vitórias e 2 derrotas, sem novas rejeições ou pares inválidos.
Portanto `candidate-07-quick` passa a estar autorizado a seguir para 37 casos, mas ainda
não é uma nova melhor completa. A melhor operacional permanece `candidate-01-full` até
essa validação.
