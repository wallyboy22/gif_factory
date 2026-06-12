# MapBiomas Data Container

Automated pipeline for generating animated GIF visualizations, area statistics, and charts from Google Earth Engine satellite imagery, developed for [IPAM Amazônia](https://ipam.org.br) and [MapBiomas](https://mapbiomas.org).

## Overview

This project downloads time-series Earth Observation data and produces high-quality animated GIFs with cartographic frames, grids, legends, scale bars, and headers — ready for scientific communication and public dashboards.

### Supported Initiatives

| Initiative | Collections | Products | Status |
|-----------|-------------|----------|--------|
| **Brasil** | Degradação 10.1, Fire 3/5, LULC 9/10, Solo | 17 | Active |
| **Paraguay** | Fire 1 | 6 | Active |

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python -c "import ee; ee.Authenticate()"
```

## Usage

```powershell
# Run a quick test (DF territory, ~30s)
python scripts/run/run_pipeline_df.py

# Generate a batch
python -m mapbiomas_data.interfaces.cli --generate --batch config/batches/v002.json --workers 6 --resume

# List available datasets and territories
python -m mapbiomas_data.interfaces.cli --list-datasets
python -m mapbiomas_data.interfaces.cli --list-territories

# List initiatives and collections
python -m mapbiomas_data.interfaces.cli --list-initiatives
python -m mapbiomas_data.interfaces.cli --list-collections brasil

# Post-processing: GeoPDFs, special collages, PDF catalogs
python -m mapbiomas_data.postprocessing.cli build-geopdfs --all
python -m mapbiomas_data.postprocessing.cli build-special-collages --mode first_last
python -m mapbiomas_data.postprocessing.cli build-catalogs --mode all

# Upload to Google Cloud Storage
python scripts/sync/sync_to_hub.py

# Generate Looker Studio CSVs
python scripts/looker/build_looker_csvs_from_gcs.py

# Generate notebooks for initiatives
python scripts/generate_notebooks.py
```

## Project Structure

```
├── config/
│   ├── initiatives/          # Per-initiative YAML configs
│   │   ├── brasil/
│   │   └── paraguay/
│   ├── batches/              # Batch job definitions
│   └── visualization.yaml    # Color palettes and legends
├── src/
│   └── mapbiomas_data/     # Core Python package
│       ├── config/           # Configuration loader
│       ├── core/             # Pipeline, EE transforms, managers
│       ├── interfaces/       # CLI (Click), API
│       └── postprocessing/   # GeoPDF, collages, catalogs
├── notebooks/                # Generated per-initiative notebooks
├── scripts/                  # Utility scripts
├── specs/                    # Technical documentation
└── .opencode/                # AI agent context and skills
```

## Documentation

| Resource | Description |
|----------|-------------|
| `specs/overview.md` | Architecture and technology stack |
| `specs/pipeline.md` | Processing pipeline details |
| `specs/datasets.md` | Complete product catalog |
| `specs/visualization.md` | Color palettes and legend system |
| `specs/territories.md` | Territory definitions |
| `.opencode/AGENTS.md` | AI agent collaboration guide |

## License

[MIT](LICENSE) © 2026 Wallace Vieira da Silva / IPAM Amazônia

