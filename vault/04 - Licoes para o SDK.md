# Lições para o SDK (`mapbiomas-sdk`)

---

## Lição 1: Catálogo de Produtos YAML → `client.catalog`

**O que a Fábrica faz:**

Define 80+ produtos em YAML com todos os metadados necessários:

```yaml
products:
  - id: fire_annual_burned
    name: "Área Queimada Anual"
    ee_asset: projects/mapbiomas-public/assets/brazil/fire/collection5/...
    ee_type: Image
    band_pattern: burned_area_{year}
    years: [1985..2025]
    processor: null
    viz_key: fire_annual_burned
```

**O que o SDK ganha:**

Hoje o SDK expõe skills por domínio (`client.fire`, `client.water`) com
subthemeKeys hardcoded. Com um catálogo YAML-driven:

```python
# Antes: hardcoded
area = await client.fire.burned_area("1-1-1", 2024)

# Depois: catalog-driven
product = client.catalog.get("fire", "annual_burned")
area = await client.statistics.area(
    territory_id="1-1-1",
    subtheme_key=product.subtheme_key,
    legend_key=product.default_legend_key,
    pixel_value=product.default_pixel_value,
    year=2024,
)
```

**Ação:**
- [ ] Criar `mapbiomas_sdk/catalog/` com loader de YAML
- [ ] Migrar definições de produto das skills para arquivos YAML
- [ ] `client.catalog.search("área queimada")` → retorna produtos

---

## Lição 2: Sistema de Visualização → `client.visualization`

**O que a Fábrica faz:**

70+ paletas oficiais com metadados completos (min, max, cmap_type, discrete_labels):

```yaml
fire_monthly:
  palette: ['#a900ff', '#6f02ff', ...]
  min: 1
  max: 12
  cmap_type: categorical
  discrete_labels: {1: "Janeiro", 2: "Fevereiro", ...}
```

**O que o SDK ganha:**

Hoje o SDK não expõe paletas. O `client.legend` retorna legendas da API, mas
não as paletas de cor associadas.

```python
# Novo
viz = await client.visualization.get("fire_monthly")
# viz.palette → ['#a900ff', '#6f02ff', ...]
# viz.discrete_labels → {1: "Janeiro", ...}
# viz.cmap_type → "categorical"
```

**Ação:**
- [ ] Criar `mapbiomas_sdk/skills/visualization.py`
- [ ] Carregar de YAML (reaproveitar `visualization.yaml` da Fábrica)
- [ ] Expor via `client.visualization.get(key)`

---

## Lição 3: Territórios → `client.territory` enriquecido

**O que a Fábrica faz:**

45+ territórios com FeatureCollections GEE, filtros, e bounding boxes:

```yaml
territories:
  - id: amazonia
    name: "Amazônia"
    type: biome
    ee_source: projects/mapbiomas-workspace/AUXILIAR/biomas-2019
    ee_filter: "CD_Bioma == 'AMAZONIA'"
```

**O que o SDK ganha:**

Hoje o `client.territory` faz busca na API. Mas a API não tem bounding boxes
pré-calculados nem FeatureCollections GEE. O SDK poderia ter um catálogo
local de territórios comuns com metadados enriquecidos.

```python
# Novo
amazonia = client.territory.get_catalog("amazonia")
# amazonia.bbox → [-74, -18, -44, 5]
# amazonia.ee_source → "projects/.../biomas-2019"
# amazonia.ee_filter → "CD_Bioma == 'AMAZONIA'"
```

**Ação:**
- [ ] Adicionar catálogo de territórios em `_data/territories.yaml`
- [ ] `client.territory.get_catalog(id)` → metadados enriquecidos
- [ ] `client.territory.get_ee_feature_collection(id)` → FeatureCollection GEE

---

## Lição 4: EE Processors → `client.ee.processors`

**O que a Fábrica faz:**

44 funções de transformação GEE que decodificam pixels MapBiomas.
Exemplo:

```python
def decode_monthly_burned(image, band):
    month = image.select(band).mod(100)
    lulc_class = image.select(band).divide(100).floor()
    # ... retorna imagem processada
```

**O que o SDK ganha:**

Hoje o SDK não tem utilitários GEE. Os usuários precisam saber decodificar
pixels manualmente. Um módulo `ee.processors` no SDK forneceria funções
prontas:

```python
from mapbiomas_sdk.ee import processors

# Decodifica banda mensal de fogo
img = ee.Image(asset)
month, lulc = processors.fire.decode_monthly(img, 'burned_monthly_2025')

# Reclassifica cobertura em Nível 1 (Natural/Antrópico)
natural_anthropic = processors.coverage.reclassify_level(img, level=1)
```

**Ação:**
- [ ] Criar `mapbiomas_sdk/ee/processors.py`
- [ ] Portar os 44 processors da Fábrica (ou os mais usados)
- [ ] Organizar por tema: `processors.fire`, `processors.coverage`, `processors.degradation`

---

## Lição 5: Pipeline Checkpoint → `client.pipeline`

**O que a Fábrica faz:**

Sistema de checkpoint com arquivos `.state_<step>`:

```python
class StateManager:
    def is_step_done(self, step_name): ...
    def mark_step_done(self, step_name): ...
    def resume(self, pipeline_fn): ...
```

**O que o SDK ganha:**

Para operações longas (ex: baixar série temporal de 40 anos para 27 estados),
um sistema de checkpoint evita refazer trabalho.

**Ação:**
- [ ] Criar `mapbiomas_sdk/utils/state.py` com checkpoint file-based
- [ ] Integrar nos métodos de export/statistics de longa duração

---

## Lição 6: ConfigLoader com `!include` → `client.config`

**O que a Fábrica faz:**

Sistema de configuração YAML com:
- `!include` para referenciar outros arquivos
- Deep merge de dicionários
- Auto-descoberta de diretórios (`config/initiatives/`)

**O que o SDK ganha:**

O SDK poderia usar o mesmo padrão para:
- Configuração de regiões (`config/regions/brazil.yaml`)
- Configuração de temas (`config/themes/fire.yaml`)
- Overrides por ambiente (`config/env/staging.yaml`)

**Ação:**
- [ ] Portar `ConfigLoader` da Fábrica para `mapbiomas_sdk/config/loader.py`
- [ ] Usar para carregar catálogo de produtos + territórios + visualizações

---

## Resumo para o SDK

| P | Lição | Nova skill/módulo |
|---|---|---|
| **P0** | Catálogo YAML (L1) | `client.catalog` |
| **P0** | Visualizações (L2) | `client.visualization` |
| **P1** | Territórios enriquecidos (L3) | `client.territory.catalog` |
| **P1** | EE Processors (L4) | `mapbiomas_sdk.ee.processors` |
| **P2** | Checkpoint (L5) | `mapbiomas_sdk.utils.state` |
| **P2** | ConfigLoader (L6) | `mapbiomas_sdk.config.loader` |

## Conexões

- [[02 - Sistema de Configuracao]] — Detalhes do sistema YAML
- [[03 - Processadores GEE]] — Os 44 processors
- [[05 - Licoes para o MCP]] — Como expor via MCP
- [[06 - Licoes para as Skills]] — Como as skills consomem isso
