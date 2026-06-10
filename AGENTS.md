---
tags: [ai, agents, setup]
aliases: [Guia IA, Agentes, Instructions]
date: 2026-06-01
---

# AGENTS.md — Guia para Agentes de IA

## Sobre o Projeto

**IPAM MapBiomas GIF Factory** — Pipeline para gerar GIFs animados de dados ambientais do MapBiomas via Google Earth Engine.

## Setup Rápido

```powershell
# Criar venv
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt

# Autenticar Earth Engine
python -c "import ee; ee.Authenticate()"
```

## Comandos Essenciais

```powershell
# Gerar um GIF de teste rápido (DF, rápido, ~30s)
python scripts/run/run_pipeline_df.py

# Gerar batch completo de degradação com resume
python -m src.ipam_gif_factory.interfaces.cli --generate --batch config/batches/v001.json --workers 6 --resume

# Listar datasets disponíveis
python -m src.ipam_gif_factory.interfaces.cli --list-datasets

# Listar territórios disponíveis
python -m src.ipam_gif_factory.interfaces.cli --list-territories

# Gerar CSVs para Looker Studio
python scripts/looker/build_looker_csvs.py

# Upload para GCS
python scripts/sync/sync_to_hub.py

# Pós-processamento: GeoPDFs (GeoTIFF + tentativa GeoPDF)
python -m src.ipam_gif_factory.postprocessing.cli build-geopdfs --all

# Pós-processamento: Collages especiais (first_last, decadal_10, decadal_15, last)
python -m src.ipam_gif_factory.postprocessing.cli build-special-collages --mode first_last
python -m src.ipam_gif_factory.postprocessing.cli build-special-collages --mode decadal_10

# Pós-processamento: Catálogos PDF (mega, por território, por coleção, por par)
python -m src.ipam_gif_factory.postprocessing.cli build-catalogs --mode all
python -m src.ipam_gif_factory.postprocessing.cli build-catalogs --mode first_last --mega
```

## Arquivos-Chave

| Arquivo | Para que serve |
|---------|---------------|
| `config/datasets.yaml` | Adicionar/editar datasets e produtos |
| `config/visualization.yaml` | Ajustar paletas, ranges, legendas |
| `config/visualization_col101.yaml` | Visualizações específicas Degradação Col 10.1 |
| `config/territories.yaml` | Adicionar/editar territórios (hub com includes) |
| `config/territories_paraguay.yaml` | Paraguai: departamentos e regiões |
| `config/batches/` | Batch definitions JSON |
| `src/ipam_gif_factory/core/pipeline.py` | Orquestrador principal |
| `src/ipam_gif_factory/core/ee_transforms.py` | Processors EE (novos cálculos) |
| `src/ipam_gif_factory/core/frame_processor.py` | Labels, legendas, escala |
| `src/ipam_gif_factory/postprocessing/geo_pdf.py` | GeoPDF/GeoTIFF por frame |
| `src/ipam_gif_factory/postprocessing/special_collages.py` | Collages PNG + GIF especiais |
| `src/ipam_gif_factory/postprocessing/catalog_pdf.py` | Catálogos PDF |
| `src/ipam_gif_factory/postprocessing/frame_selector.py` | Seleção de frames (compartilhado) |
| `src/ipam_gif_factory/postprocessing/cli.py` | CLI do pós-processamento |
| `scripts/_template_batch.py` | Template para criar novos batches |
| `notebooks/fabrica_fire_col5.ipynb` | Notebook interativo Colab/VS Code |

## Convenções

- **Nomes de produto no YAML:** snake_case, em inglês (ex: `fire_frequency`)
- **Nomes de território:** snake_case, em português (ex: `mata_atlantica`)
- **Output:** `outputs/v001/<dataset>/<product>/<territory>/`
- **GIFs:** frame_duration=300ms → arquivos `_0_3s.gif`
- **Checkpoint:** arquivos `.state_*` no output dir. Use `resume=True`
- **Workers:** padrão 6, ThreadPoolExecutor (I/O bound no GEE)

## Como Adicionar um Novo Produto

1. Adicionar entrada em `config/datasets.yaml` com asset e visualização
2. Se precisar de EE processor: adicionar em `ee_transforms.py` e registrar
3. Criar visualização em `config/visualization.yaml` (ou usar existente)
4. Testar com `scripts/run_pipeline_df.py` (território DF, rápido)
5. Adicionar ao batch

## Como Adicionar um Novo Território

1. Adicionar no YAML apropriado em `config/`
2. Especificar `source` (asset GEE FeatureCollection)
3. Opcional: `filter`, `filter_in` para subselecionar features
4. Opcional: `overlay_source` para bordas

## Como Ajustar Visualização

1. Editar `config/visualization.yaml` ou `config/visualization_col101.yaml`
2. Parâmetros ajustáveis: `min`, `max`, `palette`, `cmap_type`, `discrete_labels`, `label`
3. Rodar teste com DF para validar visualmente
4. `discrete_labels` aceita lista de strings (uma por valor de pixel)
5. Para paletas contínuas: mínimo 3 cores, ideal 10+
6. Verificar `specs/visualization.md` para referência de tipos de cmap

## Debugging

- Estados de checkpoint em `outputs/v001/<dataset>/<product>/<territory>/.state_*`
- Apague o `.state_*` da etapa que falhou e rode com `resume=True`
- Erros GEE: verificar autenticação (`ee.Initialize`), quotas, asset existence
- Erros de fonte: verificar se `Arial.ttf` ou `segoeui.ttf` existem
- Erros de rede GCS: reduzir workers, usar `resume`

## Especificações Detalhadas

Ver pasta `specs/`:
- `overview.md` — Visão geral e stack
- `pipeline.md` — Arquitetura e fluxo
- `config-system.md` — Sistema YAML
- `datasets.md` — Catálogo completo
- `visualization.md` — Paletas e legendas
- `territories.md` — Territórios
- `batch-processing.md` — Processamento em lote
- `degradation-col101.md` — Degradação (386 GIFs)
- `fire-col5.md` — Fire Col 5 (em ajuste)
- `looker.md` — Looker Studio
- `html-interface.md` — Interface local
- `colab.md` — Notebook colaborativo

## Backlog / Próximos Passos

- **Factsheets** — PDFs com mapas + tabelas de estatísticas + gráficos integrados
- **GeoPDF nativo (sem GDAL CLI)** — Implementar escrita direta de GeoPDF via `rasterio` + PDF proper metadata
- **Catálogos com sumário** — Página de índice nos catálogos com links para cada seção
