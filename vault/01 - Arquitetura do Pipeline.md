# Arquitetura do Pipeline

## Fluxo de 5 Fases, 9 Etapas

```
[INPUT]                    [PROCESSING]                      [OUTPUT]
─────────────────────────────────────────────────────────────────────────
config/initiatives/        ConfigLoader                       outputs/v002/
  *.yaml                     └→ datasets dict                  └→ <dataset>/
                             └→ territories dict                  └→ <product>/
                             └→ visualizations dict                 └→ <territory>/
```

### Fase 1 — Download
1. **Auth**: `ee.Initialize(project="mapbiomas-fire-485203")`
2. **Resolve**: Dataset → produto (asset, bandas, processor) + território (FeatureCollection) + visualização (paleta, min/max)
3. **Download**: `image.visualize().getThumbURL()` → HTTP GET → PNGs em `frames_pure/`
4. **Territory Mask**: Clip ao território + overlay de bordas

### Fase 2 — Resize
5. **Resize**: Uniformiza altura (1560px), mantém aspect ratio, padding branco

### Fase 3 — Frames
6. **Frames Clean**: Adiciona ano (top-left), escala (km) + norte (bottom)
7. **Collage**: Grid com todos os frames, labels de produto + território + legenda
8. **Frames Maps**: Headers individuais (produto + ano), legenda + escala

### Fase 4 — GIF
9. **GIF**: Paleta 256 cores (viz colors + median cut) → animação 300ms/frame, loop 1000x

### Fase 5 — Postprocessing (opcional)
- **GeoPDF**: PNG → GeoTIFF (affine) → GeoPDF (GDAL)
- **Catalog PDF**: Catálogo organizado por território/coleção (ReportLab)
- **Special Collages**: Decadal, quinzenal, first_last, last_six
- **Charts**: Gráficos de barra anuais + linhas temporais (matplotlib)
- **GCS Sync**: Upload para `mapbiomas-fire` bucket

## Checkpoint/Resume

Arquivos `.state_<step>` como marcadores. 10 etapas no total. Suporte a `resume=True`.

## Múltiplas Interfaces

| Interface | Tipo | Status |
|---|---|---|
| CLI (`mapbiomas-data`) | Terminal | Primária |
| Colab Notebook | Jupyter | Funcional |
| Flask REST API | HTTP | Catálogo (read-only) |
| Batch JSON | Data-driven | 748 combinações |
| Looker Studio | Dashboard | CSV → GCS → Looker |

## Stack Técnica

| Camada | Tecnologia |
|---|---|
| GEE | `earthengine-api`, `ee.Image`, `getThumbURL()` |
| Imagem | PIL/Pillow (resize, composite, quantize) |
| Cartografia | Cálculo de escala km a partir de bounds geográficos |
| Config | YAML com `!include` e deep merge |
| Cli | argparse (992 linhas) |
| API | Flask (135 linhas, catalog-only) |
| Charts | matplotlib |
| PDF | ReportLab + GDAL CLI |
| Storage | Google Cloud Storage (`mapbiomas-fire` bucket) |

## Conexões

- [[02 - Sistema de Configuracao]] — Como datasets, territórios e visualizações são definidos
- [[03 - Processadores GEE]] — Funções que decodificam pixels MapBiomas
- [[04 - Licoes para o SDK]] — Padrões absorvíveis
