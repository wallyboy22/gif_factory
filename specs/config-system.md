---
tags: [config, yaml]
aliases: [Config, YAML, ConfigLoader]
date: 2026-06-01
---

[[overview]] | [[datasets]] | [[visualization]]

# Sistema de Configuração

## Arquivos YAML

| Arquivo | Função |
|---------|--------|
| `config/datasets.yaml` | Catálogo de datasets, produtos, assets GEE, bandas |
| `config/territories.yaml` | Hub que inclui sub-arquivos de territórios |
| `config/territories/countries.yaml` | Países (brasil, paraguay) |
| `config/territories/biomes.yaml` | Biomas (amazonia, cerrado, etc.) |
| `config/territories/states.yaml` | 27 estados brasileiros + DF |
| `config/territories/custom_regions.yaml` | Regiões customizadas (matopiba, etc.) |
| `config/visualization.yaml` | Parâmetros visuais (paletas, ranges, legendas) |
| `config/visualization_col101.yaml` | Overrides específicos para Col 10.1 |
| `config/visualization_reference.yaml` | Referência mestra com metadados completos |
| `config/paths.yaml` | Caminhos, dimensões, durações, GCS |
| `config/visibility.json` | Toggles de visibilidade (JSON, não YAML) |

## ConfigLoader

Classe em `src/mapbiomas_data/config/config_loader.py`.

Características:
- Carrega todos os YAMLs no init
- Suporta diretiva `!include` para compor arquivos
- Deep merge de sobreposições
- Acessores tipados para paths, processamento, datasets

```python
config = ConfigLoader()
config.visualizations     # Dict de todas as visualizações
config.datasets           # Dict de datasets carregados
config.territories        # Dict de territórios
config.get_output_dir()   # output/ ou outputs/v001/
config.get_processing_config("gif_creation")  # {frame_duration, loop_count, quality}
config.ee_project_id      # "mapbiomas-fire-485203"
```

## Include e Merge

`visualization.yaml` inclui outros arquivos:
```yaml
!include visualization_col101.yaml
!include visualization_reference.yaml
```

O ConfigLoader faz deep merge: chaves definidas em arquivos incluídos são mescladas com as do arquivo principal. Overrides têm precedência sobre a base.

## paths.yaml — Configurações de Runtime

```yaml
vertical_dimension: 1560     # Altura padrão dos frames
frame_duration: 300          # ms por frame no GIF
output_dir: ./outputs/v001/
cache_dir: ./cache/
gcs:
  bucket: mapbiomas-fire
  root: gif-factory
ee:
  project: mapbiomas-fire-485203
  mode: local                # local | colab | service_account
```

## visibility.json — Toggles de Visibilidade

Controla quais produtos aparecem nas interfaces:

```json
{
  "<dataset_id>": {
    "<product_id>": { "visible": true | false }
  }
}
```

Produtos sem entrada = visíveis por padrão.
Atualmente só tem overrides para `brasil_degradation_col10_1` (ocultando `natural_coverage` e `primary_natural_coverage`).

