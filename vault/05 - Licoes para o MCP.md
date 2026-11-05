# Lições para o MCP

## 10 Ferramentas MCP Candidatas

A Fábrica de GIFs expõe dados e operações que naturalmente viram
ferramentas MCP. Abaixo, cada ferramenta com inputs, outputs e
implementação de referência.

---

### 1. `catalog_list_datasets`

**Descrição**: Lista todos os datasets disponíveis (fire, lulc, degradation, soil...).

**Inputs**: `category` (opcional, filtro por categoria)

**Output**: Array de datasets com `id`, `name`, `category`, `n_products`, `years`

**Referência**: `DatasetManager` em `core/dataset_manager.py`

```python
datasets = dataset_manager.list_datasets(category="fire")
# [{"id": "brasil_fire_col5", "name": "Fire Coleção 5", "products": 22, ...}]
```

---

### 2. `catalog_get_product`

**Descrição**: Obtém informações completas de um produto: asset GEE, bandas, período, visualização.

**Inputs**: `dataset_id`, `product_id`

**Output**: Produto com `ee_asset`, `ee_type`, `band_pattern`, `years`, `viz_key`, `processor`

**Referência**: `DatasetManager.get_product()`

```python
product = dataset_manager.get_product("brasil_fire_col5", "fire_annual_burned")
# {"ee_asset": "projects/.../annual_burned_v1", "years": "1985..2025", ...}
```

---

### 3. `catalog_search`

**Descrição**: Busca produtos por termo (ex: "área queimada", "desmatamento").

**Inputs**: `query` (string)

**Output**: Array de produtos matching

**Referência**: `DatasetManager` — busca textual nos nomes/descrições

---

### 4. `territory_list`

**Descrição**: Lista territórios disponíveis com metadados.

**Inputs**: `type` (opcional: biome, state, country, region), `initiative`

**Output**: Array de territórios com `id`, `name`, `type`, `bbox`, `ee_source`

**Referência**: `TerritoryManager` em `core/territory_manager.py`

```python
territories = territory_manager.list_territories(type="biome")
# [{"id": "amazonia", "name": "Amazônia", "bbox": [-74,-18,-44,5], ...}]
```

---

### 5. `visualization_get`

**Descrição**: Obtém paleta de cor e parâmetros de visualização para um produto/tema.

**Inputs**: `viz_key` (ex: "fire_monthly", "coverage_lclu")

**Output**: `palette`, `min`, `max`, `cmap_type`, `discrete_labels`

**Referência**: `VisualizationManager` em `core/visualization_manager.py`

```python
viz = visualization_manager.get("fire_monthly")
# {"palette": ['#a900ff', ...], "min": 1, "max": 12, "discrete_labels": {...}}
```

---

### 6. `gif_generate`

**Descrição**: Gera um GIF animado para um produto, território e período.

**Inputs**: `dataset_id`, `product_id`, `territory_id`, `start_year`, `end_year`, `format` (gif/collage/frames)

**Output**: `gif_url` (GCS), `metadata` (JSON com timings)

**Referência**: `Pipeline.run()` em `core/pipeline.py` + `GIFGenerator`

```python
result = pipeline.run(
    dataset="brasil_fire_col5",
    product="fire_annual_burned",
    territory="amazonia",
    years=[2000, 2025]
)
# {"gif_url": "https://storage.googleapis.com/.../animation.gif", ...}
```

---

### 7. `area_stats_get`

**Descrição**: Calcula estatísticas de área para um produto e território.

**Inputs**: `dataset_id`, `product_id`, `territory_id`, `year`

**Output**: CSV com área por classe/pixel value

**Referência**: `AreaStatsCalculator` em `core/area_stats.py`

```python
stats = area_stats.calculate(
    dataset="brasil_fire_col5",
    product="fire_annual_burned",
    territory="amazonia",
    year=2025
)
# {"area_ha": 1234567, "by_class": {...}}
```

---

### 8. `pipeline_submit`

**Descrição**: Submete um job de processamento em lote (async).

**Inputs**: `batch_id` (arquivo JSON de batch) ou lista de combinações

**Output**: `job_id` para polling

**Referência**: `Pipeline.run()` + `StateManager`

---

### 9. `pipeline_status`

**Descrição**: Verifica status de um job submetido.

**Inputs**: `job_id`

**Output**: `status` (running/done/failed), `progress` (%), `outputs`

**Referência**: `StateManager.get_state()`

---

### 10. `validate_config`

**Descrição**: Valida a configuração (YAML syntax, referências, assets GEE existem).

**Inputs**: nenhum

**Output**: Relatório de saúde: erros, warnings, assets quebrados

**Referência**: `validate_config.py`

---

## Integração com o MCP existente

O servidor MCP atual do SDK (`flora3/src/mapbiomas_sdk/mcp/`) tem 9 ferramentas
focadas em **dados vivos** (API MapBiomas). As 10 ferramentas acima são focadas
em **catálogo + visualização** (GEE + YAML). Juntas, cobrem o espectro completo:

```
MCP Server completo:
├── Dados vivos (API MapBiomas) — 9 tools existentes
│   ├── territory_list_categories, territory_search, territory_get_by_id
│   ├── territory_by_coordinates
│   ├── legend_list_themes_clean, legend_find_class, legend_validate
│   ├── statistics_area
│   └── documentation_search
│
└── Catálogo + Visualização (Fábrica de GIFs) — 10 tools novas
    ├── catalog_list_datasets, catalog_get_product, catalog_search
    ├── territory_list
    ├── visualization_get
    ├── gif_generate, area_stats_get
    ├── pipeline_submit, pipeline_status
    └── validate_config
```

## Resumo para o MCP

| P | Tool | Complexidade | Impacto |
|---|---|---|---|
| **P0** | `catalog_list_datasets` | Baixa (read-only) | Alto |
| **P0** | `catalog_get_product` | Baixa (read-only) | Alto |
| **P0** | `visualization_get` | Baixa (read-only) | Alto |
| **P1** | `catalog_search` | Média (text search) | Médio |
| **P1** | `territory_list` | Baixa (read-only) | Médio |
| **P1** | `area_stats_get` | Média (EE compute) | Alto |
| **P2** | `gif_generate` | Alta (pipeline) | Médio |
| **P2** | `pipeline_submit` | Alta (async) | Baixo |
| **P3** | `pipeline_status` | Baixa (read-only) | Baixo |
| **P3** | `validate_config` | Média (validation) | Baixo |

## Conexões

- [[02 - Sistema de Configuracao]] — Fonte dos dados do catálogo
- [[04 - Licoes para o SDK]] — O SDK precisa existir para o MCP consumir
- [[06 - Licoes para as Skills]] — Skills como recursos MCP
