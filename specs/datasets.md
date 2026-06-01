---
tags: [datasets, config]
aliases: [Datasets, Catálogo de Produtos]
date: 2026-06-01
---

[[config-system]] | [[visualization]] | [[fire-col5]] | [[degradation-col101]]

# Datasets e Produtos

## Estrutura de um Dataset

```yaml
<dataset_id>:
  description: "..."
  category: "fire" | "land_cover" | "degradation" | "soil"
  source: "MapBiomas"
  collection: <número>
  visualization: "<viz_key_padrão>"
  products:
    <product_id>:
      name: "Nome legível"
      asset: "projects/..."          # Asset GEE
      temporal_range: [1985, 2025]
      visualization: "<viz_key>"     # Opcional, herda do dataset
      bands_slice: [0, 41]           # Opcional, fatia bandas
      bands: [...]                   # Opcional, lista explícita de bandas
      processor: "<processor_id>"    # Opcional, EE transform
```

## Catálogo Completo

### 1. `brasil_degradation_col10_1` (STATUS: 386 GIFs gerados)

Categoria: `degradation` | Coleção: 10.1 | Período: 1985-2024

**15 produtos:**

| Produto | Asset/Processor | Bandas |
|---------|----------------|--------|
| `edge_area` | Processor `edge_area` | 1985-2024 (40) |
| `edge_age` | Asset: `...edge_age...` | classificação anual |
| `patch_size` | Processor `patch_size` | 1985-2024 (40) |
| `patch_size_fragments` | Asset: `...patch_size_fragments...` | classificação |
| `patch_size_massifs` | Asset: `...patch_size_massifs...` | classificação |
| `patch_id` | Processor `patch_id` | IDs únicos por fragmento |
| `landscape_morphology` | Processor `landscape_morphology` | classes 0-6 |
| `secondary_vegetation_age` | Processor `secondary_vegetation_age` | idade 0-40 |
| `secondary_vegetation_coverage` | Asset: `...secondary_vegetation_coverage...` | classes 0-62 |
| `fire_frequency` | Processor `fire_frequency` | frequência 0-40 |
| `natural_coverage` | Processor `natural_coverage` | classes 0-2 |
| `primary_natural_coverage` | Asset: `...primary_natural_coverage...` | classificação |
| `fire_age` | Processor `fire_age` | idade 0-40 |
| `burned_natural_coverage` | Processor `burned_natural_coverage` | cobertura queimada |
| `canopy_disturbance_frequency` | Processor `canopy_disturbance` | eventos 1-12 |
| `logging` | Processor `logging` | binary 0-1 |

**Observação:** `burned_at_least_once` também existe (processor, ternary), mas não está listado nos products do dataset — é computado via processor direto.

### 2. `brasil_fire_col5` (STATUS: Configurado, 0 GIFs)

Categoria: `fire` | Coleção: 5 | Período: 1985-2025

**9 produtos com assets GEE públicos:**

| Produto | Asset Path (sob `projects/mapbiomas-public/assets/brazil/fire/collection5/`) |
|---------|---------------------------------------------------------------------------|
| `annual_burned` | `mapbiomas_fire_collection5_annual_burned_v1` |
| `annual_burned_coverage` | `mapbiomas_fire_collection5_annual_burned_coverage_v1` |
| `monthly_burned` | `mapbiomas_fire_collection5_monthly_burned_v1` |
| `scar_size_range` | `mapbiomas_fire_collection5_annual_burned_scar_size_range_v1` |
| `accumulated_burned` | `mapbiomas_fire_collection5_accumulated_burned_v1` |
| `accumulated_burned_coverage` | `mapbiomas_fire_collection5_accumulated_burned_coverage_v1` |
| `fire_frequency` | `mapbiomas_fire_collection5_fire_frequency_v1` |
| `year_last_fire` | `mapbiomas_fire_collection5_year_last_fire_v1` |
| `time_after_fire` | `mapbiomas_fire_collection5_time_after_fire_v1` |

**Convenções de nome de banda (atenção: variam por produto):**
- `annual_burned`, `annual_burned_coverage`: `burned_area_{YYYY}`, `burned_coverage_{YYYY}`
- `monthly_burned`: `burned_monthly_{YYYY}` (valores 1-12)
- `scar_size_range`: `scar_area_ha_{YYYY}` (valores 1-8)
- `accumulated_burned`, `accumulated_burned_coverage`: `fire_accumulated_{INICIO}_{FIM}`
- `fire_frequency`: `fire_frequency_{INICIO}_{FIM}`
- `year_last_fire`, `time_after_fire`: `classification_{YYYY}` (1986-2026)

### 3. `brasil_fire_col3`

Categoria: `fire` | Coleção: 3 | Período: 1985-2023

11 produtos: `annual_burned`, `monthly_burned`, `fire_frequency`, `accumulated_burned`, `scar_size_range`, `year_last_fire`, `time_after_fire`, `time_before_fire`, `year_next_fire` + coverage variants.

### 4. `paraguay_fire_col1`

Categoria: `fire` | Coleção: 1 | Período: 1998-2023

6 produtos. Mesma estrutura dos datasets fire.

### 5. `brasil_lulc_col9`

Categoria: `land_cover` | Coleção: 9 | Período: 1985-2023

Produtos: `integration`, `deforestation_secondary`, `irrigated`, `mining`, `pasture_quality`, `secondary_vegetation_age`, `quality`.

### 6. `brasil_lulc_col10`

Categoria: `land_cover` | Coleção: 10 | Período: 1985-2024

Similar ao Col 9, atualizado.

### 7. `brasil_soil`

Categoria: `soil` | Produto único (SOC).

### 8. `brasil_degradation_col9`

Categoria: `degradation` | Coleção: 9 | Período: 1985-2023

Produtos: `edge_area`, `fragment_size`, `distance_Xha`, `secondary_vegetation`, `fire_frequency`, `fire_age`.

## EE Processors (ee_transforms.py)

28 funções registradas em `PROCESSOR_REGISTRY`. Principais usados pela Degradação Col 10.1:

| Processor | Descrição |
|-----------|-----------|
| `edge_area` | Área de borda por classe de distância |
| `patch_size` | Tamanho contínuo de fragmento (ha) |
| `patch_id` | ID único por fragmento |
| `landscape_morphology` | Morfologia: Core, Edge, Perforation, Patch, Loop, Bridge |
| `secondary_vegetation_age` | Idade da vegetação secundária |
| `fire_frequency` | Frequência de fogo (÷100, round) |
| `fire_age` | Tempo desde último fogo |
| `natural_coverage` | Cobertura natural |
| `burned_natural_coverage` | Cobertura em áreas queimadas (mod 100) |
| `canopy_disturbance` | Frequência de distúrbio de dossel |
| `logging` | Extração de madeira (binary) |
| `burned_at_least_once` | Queimado ao menos uma vez (ternary) |

Fire Col 3 e Col 5 **não usam processors** — acessam assets GEE diretamente.
