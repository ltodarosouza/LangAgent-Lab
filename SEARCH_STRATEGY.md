# Estratégia de busca orientada pelas métricas

O agente não deve procurar parâmetros por chute nem fazer busca binária automática.
Antes de cada tentativa, ele precisa ler o relatório por corte, identificar o erro
dominante e escrever uma hipótese sobre qual controle pode afetá-lo.

## Controles disponíveis

- `steps` (10–100): resolução numérica do denoise. Mais passos não significam
  automaticamente mais textura. Use quando várias métricas mudam juntas e há evidência
  de que a trajetória ainda não convergiu.
- `noise_level` (0–349): classe/timestep de ruído usada pelo modelo e na condição.
  É um controle forte; altere em incrementos pequenos no início.
- `eta` (0–1): aleatoriedade adicionada durante os passos DDIM. `0` é determinístico;
  valores maiores podem recuperar variação fina, mas também criar ruído espúrio.
- `latent_noise_scale` (0,75–1,25): amplitude do ruído latente inicial. Pode mudar
  contraste e diversidade global, com risco de reduzir a fidelidade ao par.
- `conditioning_noise_scale` (0,5–1,5): amplitude da corrupção aplicada à imagem que
  condiciona o modelo. É útil para testar o equilíbrio entre copiar uma entrada suave e
  deixar o prior aprendido reconstruir textura.
- `sampler=ddim`, `scale_factor=1.0` e `seed=42` ficam congelados. O seed fixo permite
  comparar causas; o scale factor pertence ao espaço latente aprendido.

## Como transformar sintomas em hipóteses

- Contraste GLCM baixo, Wavelet fina/grossa baixas e energia GLCM alta em muitos cortes:
  provável suavização. Priorize `conditioning_noise_scale`, `eta` ou
  `latent_noise_scale`; não aumente `steps` repetidamente sem evidência.
- Wavelet fina ou NEx excessivos, correlação do par menor ou aspecto granulado:
  provável ruído espúrio. Reduza primeiro o controle de ruído que foi elevado.
- Textura grossa preservada e textura fina baixa: prefira controles de ruído/condição a
  `steps`, pois o erro é específico das altas frequências.
- Brilho, densidade, validade ou correlação pioraram: rejeite a hipótese mesmo que uma
  métrica de textura tenha melhorado.
- Efeito diferente entre cortes: olhe os casos individuais. Uma média melhor causada por
  um ou dois casos não é evidência suficiente.

Essas relações são hipóteses físicas, não garantias. O relatório da tentativa deve
confirmá-las ou refutá-las.

## Protocolo de cada tentativa

1. Leia métricas agregadas e por corte da melhor versão atual.
2. Declare o defeito dominante, o parâmetro escolhido e quais métricas devem mudar.
3. Altere uma variável por vez, salvo quando houver justificativa explícita para interação.
4. Rode a triagem fixa de 5 casos. Se disser `melhor`, amplie para 10 reutilizando os 5.
   Se os 10 disserem `melhor`, amplie para 37 reutilizando os 10.
5. Depois de um resultado ruim, revise a hipótese. Não escolha automaticamente o ponto
   médio. Só faça refinamento numérico quando dois testes mostrarem uma tendência clara.
6. Registre no `CADERNO.md`: parâmetro, direção, efeito esperado, efeito observado por
   métrica e conclusão causal.

O baseline é sempre a régua fixa. A melhor versão completa serve como ponto de partida e
como adversária adicional, mas nunca substitui o baseline na medição.
