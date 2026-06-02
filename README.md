---
tags: [readme, overview]
aliases: [Home, Fabrica de GIFs]
date: 2026-06-01
---

# Fabrica de GIFs — IPAM MapBiomas

Pipeline automatizado para gerar GIFs animados de dados ambientais do MapBiomas via **Google Earth Engine**.

## Colecoes Suportadas

| Dataset | Status |
|---------|--------|
| Degradacao Col 10.1 | 386 GIFs gerados |
| Fire Col 5 | Configurado (em ajuste) |
| Fire Col 3 | Configurado |
| Paraguay Fire Col 1 | Configurado |
| LULC Col 9/10 | Configurado |
| Soil Carbon | Configurado |

## Setup Rapido

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "import ee; ee.Authenticate()"
```

## Gerar GIFs

```powershell
# Teste rapido (DF)
python scripts/run_pipeline_df.py

# Batch completo
python -m src.ipam_gif_factory.interfaces.cli --generate --batch config/batches/v001.json --workers 6 --resume

# Notebook interativo (Colab / VS Code)
# Abrir notebooks/fabrica_fire_col5.ipynb
```

## Interfaces

- **Looker Studio** (publico): dashboard com CSVs servidos via GCS
- **Colab Notebook** (colaborativo): `notebooks/fabrica_fire_col5.ipynb`

## Documentacao

- `AGENTS.md` — Guia para agentes de IA
- `specs/` — Especificacoes detalhadas por feature
