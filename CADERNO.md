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
