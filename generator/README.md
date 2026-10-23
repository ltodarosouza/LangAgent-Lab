# Gerador local — primeiro protótipo

Este diretório contém o modelo de geração. O avaliador vive no repositório
separado `synthetic-lung-ct-evaluation` e é chamado pela sua interface JSON.

## O que já está fixado

- arquitetura exata do AEKL e do LDM Dsr;
- pesos carregados de forma estrita (qualquer incompatibilidade gera erro);
- uso automático da GPU MPS do Mac, com alternativa em CPU;
- registro dos parâmetros de cada geração em um JSON ao lado da TIFF.

## Preparar o ambiente

```bash
uv venv --python 3.10 .venv
uv pip install --python .venv/bin/python -r generator/requirements.txt
```

## Conferir os modelos

```bash
.venv/bin/python generator/smoke_test.py
```

## Gerar uma imagem

```bash
.venv/bin/python generator/generate_one.py \
  "../synthetic-lung-ct-evaluation/dados/Dsr/IMAGEM_ORIGINAL.tiff" \
  "outputs/generator/teste_generate.tiff"
```

Os controles de inferência expostos ao laboratório são `steps`, `noise_level`,
`eta`, `latent_noise_scale` e `conditioning_noise_scale`. O `seed` fica fixo em
42 para a comparação medir o efeito do parâmetro, e não outra amostra aleatória.
`sampler=ddim` e `scale_factor=1.0` também ficam congelados.
O `scale-factor` ficou em `1.0`, conforme o exemplo do projeto original, mas ainda precisa ser confirmado experimentalmente.

## Gerar e avaliar automaticamente

O comando abaixo gera a sintética, encontra a máscara pelo nome, usa as réguas
reais guardadas pelo repositório avaliador e produz um JSON único:

```bash
.venv/bin/python generator/run_cycle.py \
  "../synthetic-lung-ct-evaluation/dados/Dsr/IMAGEM_ORIGINAL.tiff" --steps 25
```

Cada execução ganha uma pasta própria em `outputs/cycles/`, contendo a TIFF,
os parâmetros da geração, a avaliação e `resultado_completo.json`. Antes de
gerar, o ciclo também confere se a máscara passa pelo filtro operacional do
avaliador, evitando gastar tempo com um corte que seria recusado.
