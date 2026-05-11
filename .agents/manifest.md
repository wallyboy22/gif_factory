# IPAM GIF Factory - IA-First Project Manifest

## Project Identity
- **Name:** IPAM GIF Factory
- **Purpose:** Automated generation of animated GIFs from Earth Engine satellite imagery for environmental monitoring
- **Domain:** Geospatial data visualization, remote sensing, fire ecology

## Core Principles (IA-First)

### 1. Configuration-Driven Development
- All data definitions in YAML, not code
- Adding a dataset = editing YAML, not Python
- Adding a territory = editing YAML, not Python

### 2. Testability First
- Every module must be testable in isolation
- Use DF (Distrito Federal) as the default test territory
- Tests must run without Earth Engine authentication when possible (mocked)

### 3. Modular Architecture
- Clear separation: Config Layer → Data Layer → Processing Layer → Interface Layer
- Each layer has a single responsibility
- Dependencies flow inward (UI depends on Processing, never the reverse)

### 4. AI Collaboration Ready
- All decisions documented in `.agents/`
- Code is self-documenting (clear names, no ambiguous comments)
- Configuration schemas are explicit and validated

### 5. Developer Experience
- CLI, Dashboard, and API from the same codebase
- Local-first development (no Colab dependency)
- Fast feedback loops with DF test territory

## Project Architecture

```
┌──────────────────────────────────────────────────┐
│                  INTERFACE LAYER                  │
│  CLI (Click)  │  Dashboard (Streamlit)  │  API   │
├──────────────────────────────────────────────────┤
│                 PROCESSING LAYER                  │
│  GIFGenerator │ ImageDownloader │ FrameProcessor │
├──────────────────────────────────────────────────┤
│                   DATA LAYER                      │
│  DatasetManager │ TerritoryManager │ VizManager  │
├──────────────────────────────────────────────────┤
│                 CONFIGURATION LAYER               │
│  datasets.yaml │ territories.yaml │ viz.yaml     │
│  paths.yaml    │ settings.yaml                   │
└──────────────────────────────────────────────────┘
```

## Testing Strategy
- **Unit Tests:** Mock Earth Engine responses
- **Integration Tests:** Use DF territory as lightweight validation
- **E2E Tests:** Full pipeline with small territory (DF)
- **Test datasets:** Use only 1-2 bands for speed

## Adding New Datasets (Recipe)
1. Edit `config/datasets.yaml` - add product entry
2. Edit `config/visualization.yaml` - add viz params if needed
3. Run `python main.py --list-products` to validate
4. Test with `python main.py --dataset <id> --territory df`
5. Done - appears automatically in Dashboard

## Adding New Territories (Recipe)
1. Edit `config/territories.yaml` - add territory entry
2. Run `python main.py --list-territories` to validate
3. Test with any dataset using `--territory <id>`
4. Done - appears automatically in Dashboard

## Critical Files
- `config/datasets.yaml` - All available datasets
- `config/territories.yaml` - All territory boundaries
- `config/visualization.yaml` - Color palettes and ranges
- `src/ipam_gif_factory/` - Main package
- `.agents/skills/` - Reusable AI skills

## Current State
- Phase: Implementation
- Test territory: DF (Distrito Federal)
- Priority: Complete core engine first, then interfaces
