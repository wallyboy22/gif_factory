# IPAM GIF Factory - Context for AI

## What Are We Building?
A modular Python system that downloads satellite imagery from Google Earth Engine and generates animated GIF visualizations for environmental monitoring.

## Source Material
- **Notebook original:** `ipam_fabrica_de_gifs_com_earth_engine.py` (1000+ lines, Colab)
- **Tasks:** `tasks.md` (4-phase roadmap)
- **Refactoring Plan:** `plano de refatoração.md` (analysis and gaps fixed)

## Key Observations from Notebook Analysis

### Current Pain Points
1. 40+ global variables for Earth Engine images - hard to manage
2. visParams dictionary with 500+ lines - difficult to edit
3. Nested loops mixing download + GIF generation - confusing logic
4. No version tracking for datasets (Col9 vs Col10)
5. 30+ products constantly commented/uncommented - no catalog
6. No caching - 2-3 hours per full execution
7. No public interface - only accessible via Google Drive

### Architecture Decisions Made
- YAML configs for all data (datasets, territories, visualization)
- Module-based instead of cell-based
- Local-first with optional Google Drive support
- Protocol: YAML → Data Classes → EE Processing → Output

### Gaps Already Addressed in Plan
| Gap | Fix |
|-----|-----|
| Missing get_territory_name() | Added to TerritoryManager |
| SOC is ImageCollection, not Image | asset_type: image_collection in YAML |
| Degradation products are composites | processor field + ee_transforms.py |
| only_coverage() had no home | Moved to ee_transforms.py |
| Frames not sorted before GIF | Sorted in GIFGenerator |
| No \_\_init\_\_.py files | Created in all packages |
| Monitor do Fogo too complex | status: em_desenvolvimento |

## Development Rules
1. Always test with DF first (smallest territory, fastest feedback)
2. Always validate YAML files after edits
3. Keep modules under 300 lines
4. Use type hints everywhere
5. Docstrings in Portuguese (project language)
6. Never hardcode values that go in YAML
7. Mock EE in unit tests, use real EE in integration tests

## Latest Changes

### Dashboard: File-Based Queue + IPAM Visual Identity (09/05/2026)
- **File-based queue**: Replaced `st.session_state` queue with `queue.json` and `status.json`
  - Queue persiste entre recarregamentos da página (F5 não reseta)
  - Worker thread escreve progresso em `status.json` em tempo real
  - Dashboard lê dos arquivos, não mais do `session_state`
  - Funções: `_queue_load()`, `_queue_save()`, `_status_load()`, `_status_save()`
- **"Processar Todos"**: Botão na aba Dev que adiciona todos os itens filtrados à fila de uma vez
- **Modo Dev sempre ativo**: Removeu checkbox, tab aparece sempre como 3ª aba
- **Identidade visual IPAM**:
  - Header gradiente verde (`#006b3f → #0d8642`) com logo IPAM 30 anos (branca)
  - Tabs estilo pill (bege inativo, verde ativo)
  - Expanders com borda lateral verde + hover bege, fechados por padrão
  - Cards de métrica com borda verde IPAM no monitoramento
  - Tipografia Roboto (Google Fonts)
  - Botões compactos para frames (checkbox + ano ⬇)
- **Footer**: "IPAM · Instituto de Pesquisa Ambiental da Amazônia"

### Pipeline & Frame Processing (Major Refactor)
- **Unified flow**: single sequential pipeline (no `--scale-in-cells`, no temp copies). Steps: download → scale+north+margins → grid → title+legend on grid → header(line1+subtitle+year) + legend on frames → GIF
- **`add_bottom_bar`**: added `show_legend` and `show_scale` params. Grid uses legend-only (`show_legend=True, show_scale=False`); frames get scale in step 1 + legend in step 2 via separate calls — no duplication
- **`add_year_label`**: added `subtitle` + `subtitle_size` for two-line titles (main text bigger, collection ref smaller)
- **`add_frame_header`**: added `subtitle` + `subtitle_size` for header with line1 + subtitle + big year (line2)
- **`add_scale_bar`**: existing compact scale+north method (120px) used in step 1 for grid frames
- **`_truncate_label()`**: truncates labels > 35 chars with terminal warning
- **`_wrap_text()`**: wraps text by pixel width using `draw.textbbox()`, supports multi-line
- **`_layout_discrete()`**: dynamic columns (2→1) and font reduction until legend text fits
- **`_make_font()`**: safe font loading with fallback
- **Font sizes reduced**: collage title 45, subtitle 30; frame header line1 36, subtitle 22, year 160

### Grid Layout
- **Dynamic columns**: formula `ceil(n / 5)`, capped at 10, min 2 — always horizontal (max 5 rows)
- **`cell_height`** param (CLI: `--cell-height`, default 300)
- **`cell_labels`**: used for year labels on grid cells (no duplicate year labels)
- **Grid title**: 2-line white header, no overlapping (padding_top=160)
- **Grid legend**: `show_scale=False` (no general scale — scale is per-frame only)

### Earth Engine Processors
- **`burned_at_least_once`**: class 3 (future fire) restricted to natural areas via `.And(natural)`; converted areas with future fire excluded
- **`decode_fire_frequency_col101`** / **`decode_fire_age_col101`**: added `.unmask(0).int8()` — value 0 rendered as gray background

### Configuration
- **Product names**: all 11 products stripped of "Degradação - " prefix (e.g., "Frequência do Fogo")
- **Dataset description**: `"MapBiomas Degradação Collection 10.1 - Brasil"` → `"Módulo de Degradação do MapBiomas · Coleção 10.1"`
- **Palettes**: `frequency_col101` and `fire_age` — palette[0] changed to `"808080"` (gray background for value 0)

### CLI Changes
- Removed `--scale-in-cells`, `--collage-cell-height`
- Added `--cell-height` (altura de cada célula na colagem)

### Products Tested & Generated (MATOPIBA Cerrado)
| Product | Frames | Status |
|---------|--------|--------|
| `fire_frequency` | 40 (1985–2024) | ✅ Grid + GIF |
| `fire_age` | 39 (1986–2024) | ✅ Grid + GIF |
| `burned_at_least_once` | 2 (1986, 2024) | ✅ Grid + GIF |
| `natural_coverage` | — | ✅ Processor |
| `burned_natural_coverage` | — | ✅ Processor |

## Current Focus
Generate remaining MATOPIBA products. Next: validate visual outputs, adjust colors/labels as needed.
