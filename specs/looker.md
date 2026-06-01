---
tags: [looker, interface]
aliases: [Looker Studio, Dashboard Público]
date: 2026-06-01
---

# Looker Studio — Interface Pública

## Dashboard Público

URL: `https://datastudio.google.com/u/0/reporting/179f6b47-8f6e-4f51-abd5-75b7ae018a2b/page/XDzxF`

## Fluxo de Dados

```
GIFs gerados (local) → metadata JSON
     ↓
gen_csv.py / build_looker_csvs.py → CSV index
     ↓
Upload CSV → GCS (opcional)
     ↓
Looker Studio → Fonte de dados: CSV público no GCS
     ↓
Dashboard interativo (filtros por dataset, território, produto, ano)
```

## Geradores de CSV

### `gen_csv.py` (versão inicial, 142 linhas)
- Lê todos os `metadata_*.json` de `outputs/v001/`
- Gera 3 variantes: `gif_index.csv`, `gif_index_pivot_territorios.csv`, `gif_index_pivot_produtos.csv`
- Inclui GIFs, frames individuais e collages
- Colunas: link_direto, tipo_arquivo, dataset, colecao, produto, territorio, timing, EE estimates

### `build_looker_csvs.py` (versão refinada, 166 linhas)
- Mesma lógica, output em 3 subpastas:
  - `raw/` — CSVs completos
  - `pivot_territorios/` — pivotado por território (linhas=territórios, colunas=produtos)
  - `pivot_produtos/` — pivotado por produto (linhas=produtos, colunas=territórios)
- Divide por biomas vs custom_regions
- Apenas arquivos `.gif` (não frames individuais)
- 4 variantes: all + biomes + custom_regions + <dataset>

## Colunas do CSV

| Coluna | Descrição |
|--------|-----------|
| `link_direto` | URL pública do GIF no GCS |
| `tipo_arquivo` | "gif", "frame", "collage" |
| `arquivo` | Nome do arquivo |
| `ano` | Ano do frame (ou null para GIF/collage) |
| `dataset` | ID do dataset |
| `colecao` | Número da coleção |
| `produto_id` | ID do produto |
| `nome_produto` | Nome legível do produto |
| `territorio_id` | ID do território |
| `nome_territorio` | Nome legível do território |
| `tipo_territorio` | "biome", "state", "custom_region" |
| `tempo_total_s` | Tempo total de geração |
| `ee_estimates_*` | Estimativas de consumo GEE |
| `pixel_*` | Dimensões e resolução |

## GCS Base URL

```
https://storage.googleapis.com/mapbiomas-fire/gif-factory/
```

## Tarefas Pendentes

1. Rodar `build_looker_csvs.py` após gerar GIFs Fire Col 5
2. Upload dos CSVs para GCS
3. Conectar/atualizar fonte de dados no Looker Studio
4. Verificar se o link do dashboard existente funciona com os novos dados
