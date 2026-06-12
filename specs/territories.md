---
tags: [territories, config]
aliases: [Territórios, FeatureCollections]
date: 2026-06-01
---

[[config-system]] | [[batch-processing]]

# Territórios

## Hierarquia

```
countries/         (2)  ── Países
biomes/            (9)  ── Biomas + agregados
states/            (27) ── Unidades Federativas
custom_regions/    (7)  ── Regiões customizadas
```

## Lista Completa

### Países (2)
| ID | Nome |
|----|------|
| `brasil` | Brasil |
| `paraguay` | Paraguay |

### Biomas (9)
| ID | Nome |
|----|------|
| `biomas` | Todos os biomas |
| `amazonia` | Amazônia |
| `caatinga` | Caatinga |
| `cerrado` | Cerrado |
| `mata_atlantica` | Mata Atlântica |
| `pampa` | Pampa |
| `pantanal` | Pantanal |
| `bap` | BAP (Bacia do Alto Paraguai) |
| `bap_planalto` | BAP Planalto |

### Estados (27)
`acre`, `alagoas`, `amapa`, `amazonas`, `bahia`, `ceara`, `df`, `espirito_santo`, `goias`, `maranhao`, `mato_grosso`, `mato_grosso_do_sul`, `minas_gerais`, `para`, `paraiba`, `parana`, `pernambuco`, `piaui`, `rio_de_janeiro`, `rio_grande_do_norte`, `rio_grande_do_sul`, `rondonia`, `roraima`, `santa_catarina`, `sao_paulo`, `sergipe`, `tocantins`

### Regiões Customizadas (7)
| ID | Nome |
|----|------|
| `matopiba` | MATOPIBA completo |
| `matopiba_cerrado` | MATOPIBA apenas Cerrado |
| `centro_oeste` | Região Centro-Oeste |
| `nordeste` | Região Nordeste |
| `norte` | Região Norte |
| `sudeste` | Região Sudeste |
| `sul` | Região Sul |

## Estrutura de um Território

```yaml
<territory_id>:
  name: "Nome legível"
  type: "country" | "biome" | "state" | "custom_region"
  feature_collection: "projects/..."    # Asset GEE FeatureCollection
  filter: "<propriedade> == '<valor>'"  # Filtro EE opcional
  overlay:
    feature_collection: "projects/..."  # FC para borda/máscara
```

## TerritoryManager

Classe em `src/mapbiomas_data/core/territory_manager.py`.

Métodos principais:
- `get_territory(id)` — Retorna metadados do território
- `get_feature_collection(id)` — Retorna `ee.FeatureCollection` para máscara
- `get_overlay_fc(id)` — Retorna FC para desenhar bordas
- `list_territories(type=None)` — Lista todos ou filtra por tipo

O TerritoryManager usa `ee_utils.parse_filter_expression()` para converter strings de filtro em objetos `ee.Filter`.

## Uso no Pipeline

1. O território é usado como **máscara** (clip da imagem)
2. O overlay é desenhado como **borda** nos frames
3. Os bounds do território definem a **escala** e **seta norte**
4. O nome aparece nos **títulos** dos frames e collages

