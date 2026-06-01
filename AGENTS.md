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
python run_pipeline_df.py

# Gerar batch completo de degradação com resume
python -m src.ipam_gif_factory.interfaces.cli --generate --batch batch_v001.json --workers 6 --resume

# Listar datasets disponíveis
python -m src.ipam_gif_factory.interfaces.cli --list-datasets

# Listar territórios disponíveis
python -m src.ipam_gif_factory.interfaces.cli --list-territories

# Gerar CSVs para Looker Studio
python build_looker_csvs.py

# Upload para GCS
python sync_to_hub.py
```

## Arquivos-Chave

| Arquivo | Para que serve |
|---------|---------------|
| `config/datasets.yaml` | Adicionar/editar datasets e produtos |
| `config/visualization.yaml` | Ajustar paletas, ranges, legendas |
| `config/visualization_col101.yaml` | Visualizações específicas Degradação Col 10.1 |
| `config/territories.yaml` | Adicionar/editar territórios |
| `config/paths.yaml` | Dimensões, durações, caminhos |
| `config/visibility.json` | Toggles de visibilidade por produto |
| `src/ipam_gif_factory/core/pipeline.py` | Orquestrador principal |
| `src/ipam_gif_factory/core/ee_transforms.py` | Processors EE (novos cálculos) |
| `src/ipam_gif_factory/core/frame_processor.py` | Labels, legendas, escala |
| `batch_v001.json` | Batch de degradação (150 combos) |

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
4. Testar com `run_pipeline_df.py` (território DF, rápido)
5. Adicionar ao batch

## Como Adicionar um Novo Território

1. Adicionar no YAML apropriado em `config/territories/`
2. Especificar `feature_collection` (asset GEE FeatureCollection)
3. Opcional: `filter` para subselecionar features
4. Opcional: `overlay.feature_collection` para bordas

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
