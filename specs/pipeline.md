---
tags: [pipeline]
aliases: [Pipeline, Fluxo de Geração]
date: 2026-06-01
---

[[overview]] | [[config-system]] | [[batch-processing]]

# Pipeline

## Orquestrador Principal

`Pipeline.run()` em `src/mapbiomas_data/core/pipeline.py` — ponto central de toda geração.

```python
pipeline.run(
    dataset_id="brasil_degradation_col10_1",
    product_id="fire_frequency",
    territory_id="amazonia",
    viz_key=None,              # auto-resolve do dataset
    output_dir=None,           # auto: outputs/v001/<dataset>/<product>/<territory>/
    create_collage=True,
    add_labels=True,
    vertical_dimension=1560,   # altura padrão dos frames
    max_bands=0,               # 0 = todas as bandas
    band_names_filter=None,    # filtra por sufixo (ex: ["2024"])
    cell_height=300,           # altura das células na collage
    resume=False,              # retoma de checkpoint
)
```

## Fluxo de 9 Etapas

Cada etapa é rastreada por `StateManager` (arquivos `.state_*` no output dir).

```
[1] DOWNLOAD         Baixa thumbnails do GEE via getThumbURL()
                     Um PNG por banda/ano (~40 frames para 1985-2024)
                     Aplica vizParams (min, max, palette)
                     Aplica overlay de território (máscara + borda)

[2] RESIZE           Redimensiona todos os frames para altura uniforme
                     Mantém aspect ratio (largura proporcional)

[3a] COLLAGE_SCALE   Adiciona barra de escala + seta norte nos frames
                     (apenas quando create_collage=True e add_labels=True)

[3b] COLLAGE_MARGINS Adiciona margens brancas de 30px nos frames

[3c] COLLAGE         Monta grid multi-célula (ex: 8 colunas x 5 linhas)
                     Uma célula por ano, com label do ano

[3d] COLLAGE_LABELS  Adiciona título, subtítulo e legenda à collage
                     Título: "<produto> · <território>"
                     Subtítulo: descrição do dataset

[4a] FRAME_HEADERS   Adiciona título + ano em cada frame individual
                     (apenas quando add_labels=True)

[4b] FRAME_BOTTOMS   Adiciona legenda + escala em cada frame individual

[5] GIF              Cria GIF animado a partir dos frames processados
                     frame_duration=300ms → arquivo "_0_3s.gif"
                     loop_count=1000, optimize=True
```

## Sistema de Checkpoint (StateManager)

Arquivos de estado salvos no diretório de output:

```
.state_download
.state_resize
.state_collage_scale_north
.state_collage_margins
.state_collage
.state_collage_labels
.state_frame_headers
.state_frame_bottom_bars
.state_gif
```

Comportamento com `resume=True`:
- Pula etapas cujo `.state_*` existe
- Continua da primeira etapa pendente
- `resume=False` limpa todos os estados e começa do zero

## Classes Envolvidas

| Classe | Arquivo | Função |
|--------|---------|--------|
| `Pipeline` | `core/pipeline.py` | Orquestrador principal |
| `ConfigLoader` | `config/config_loader.py` | Carrega todos os YAMLs |
| `DatasetManager` | `core/dataset_manager.py` | Resolve datasets/produtos |
| `TerritoryManager` | `core/territory_manager.py` | Resolve territórios, FCs, overlays |
| `VisualizationManager` | `core/visualization_manager.py` | Resolve paletas, ranges, cmap |
| `EEDownloader` | `core/ee_downloader.py` | Download thumbnails GEE |
| `FrameProcessor` | `core/frame_processor.py` | Labels, escala, norte, legendas, resize |
| `GIFGenerator` | `core/gif_generator.py` | Cria GIF e collage |
| `StateManager` | `core/state_manager.py` | Checkpoint/resume |

## Estrutura de Output

```
outputs/v001/
└── <dataset>/
    └── <product>/
        └── <territory>/
            ├── <product>_<band>.png       (frames individuais)
            ├── <product>_<territory>_0_3s.gif
            ├── <product>_<territory>_collage.png
            ├── metadata_<product>.json
            └── .state_*                    (checkpoints)
```

## Metadados (metadata JSON)

Cada execução gera `metadata_<product>.json` com:
- `dataset`, `product`, `territory` (IDs e nomes)
- `visualization` (viz_key, palette, range)
- `bounds` (lon_min, lon_max, lat_min, lat_max)
- `files` (gif, collage, frames com paths e tamanhos)
- `timings` (tempo de cada etapa + total)
- `ee_estimates` (estimativas de consumo GEE)
- `pixel_info` (dimensões, resolução)

