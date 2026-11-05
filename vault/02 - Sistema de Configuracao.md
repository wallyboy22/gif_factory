# Sistema de Configuração (YAML)

## Estrutura

```
config/
├── paths.yaml                         # Output dirs, cache, GCS bucket, parâmetros
├── visualization.yaml                 # 2008 linhas: 70+ paletas, cmap_types, discrete_labels
├── visualization_col101.yaml          # Override: Degradação Col 10.1
├── visualization_reference.yaml       # Metadados de referência das legendas oficiais
├── categories.yaml                    # Categorias: fire, land_cover, degradation, soil
├── initiatives/
│   └── brasil/
│       ├── initiative.yaml            # Metadados da iniciativa Brasil
│       ├── collections/
│       │   ├── fire_5.yaml            # 22 produtos Fire Col 5
│       │   ├── fire_3.yaml            # 11 produtos Fire Col 3
│       │   ├── degradation_10_1.yaml  # 15 produtos Degradação Col 10.1
│       │   ├── lulc_9.yaml, lulc_10.yaml, soil.yaml
│       └── territories/
│           ├── states.yaml            # 27 estados (UF)
│           ├── biomes.yaml            # 9 biomas
│           ├── country.yaml           # Brasil
│           └── regions.yaml           # MATOPIBA, Centro-Oeste, etc.
│   └── paraguay/
│       ├── collections/fire_1.yaml    # 6 produtos Paraguay Fire
│       └── territories/
└── batches/
    ├── v002.json                      # 748 combinações (degradação × territórios)
    ├── v002_ufs.json, v002_biomas.json, v002_regioes.json, v002_pais.json
    └── test_df.json
```

## Catálogo de Produtos (`collections/*.yaml`)

Cada produto é definido com:

```yaml
products:
  - id: fire_annual_burned
    name: "Área Queimada Anual"
    category: fire
    ee_asset: projects/mapbiomas-public/assets/brazil/fire/collection5/mapbiomas_fire_collection5_annual_burned_v1
    ee_type: Image
    band_pattern: burned_area_{year}
    years: [1985..2025]
    processor: null  # ou nome do processor no PROCESSOR_REGISTRY
    viz_key: fire_annual_burned
    coverage_levels: null  # ou [0, 1, 2] para níveis de agregação LULC
```

**8 datasets catalogados:**

| Dataset | Categoria | Produtos | GIFs |
|---|---|---|---|
| `brasil_fire_col5` | fire | 22 | — |
| `brasil_fire_col3` | fire | 11 | — |
| `paraguay_fire_col1` | fire | 6 | — |
| `brasil_degradation_col10_1` | degradation | 15 | 386 |
| `brasil_degradation_col9` | degradation | 6 | — |
| `brasil_lulc_col10` | land_cover | 7 | — |
| `brasil_lulc_col9` | land_cover | 7 | — |
| `brasil_soil` | soil | 1 | — |

## Territórios (`territories/*.yaml`)

```yaml
territories:
  - id: amazonia
    name: "Amazônia"
    type: biome
    ee_source: projects/mapbiomas-workspace/AUXILIAR/biomas-2019
    ee_filter: "CD_Bioma == 'AMAZONIA'"
    bbox: [-74.0, -18.0, -44.0, 5.0]
```

**45+ territórios em 5 tipos:**

| Tipo | Quantidade | Exemplo |
|---|---|---|
| countries | 2 | Brasil, Paraguay |
| biomes | 9 | Amazônia, Cerrado, Caatinga... |
| states | 27 | UF (siglas IBGE) |
| regions | 4+ | MATOPIBA, Centro-Oeste... |
| departments | 18 | Paraguay |

## Visualizações (`visualization.yaml`)

```yaml
fire_annual_burned:
  palette: ['#FF0000']
  min: 1
  max: 1
  cmap_type: binary
  discrete_labels:
    1: "Área queimada"
  units: null

fire_monthly:
  palette: ['#a900ff', '#6f02ff', ...]  # 12 cores
  min: 1
  max: 12
  cmap_type: categorical
  discrete_labels:
    1: "Janeiro"
    2: "Fevereiro"
    ...
  units: null
```

**Tipos de paleta suportados:**
- `categorical` — classes discretas com label por valor
- `sequential` — gradiente contínuo
- `binary` — presença/ausência (1 cor)
- `diverging` — divergente (ex: ganho/perda)

## ConfigLoader

- Suporte a `!include` para referenciar outros YAMLs
- Deep merge de configurações
- Auto-scan de `config/initiatives/` para descobrir datasets + territórios
- Propriedades: `datasets`, `territories`, `visualizations`, `paths`, `initiatives`, `categories`

## Conexões

- [[01 - Arquitetura do Pipeline]] — Como a config é consumida
- [[04 - Licoes para o SDK]] — Por que o SDK deveria adotar YAML config
- [[06 - Licoes para as Skills]] — Como as skills podem herdar esse catálogo
