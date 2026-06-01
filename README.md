---
tags: [readme, overview]
aliases: [Home, Fábrica de GIFs]
date: 2026-06-01
---

# Fábrica de GIFs — IPAM MapBiomas

Pipeline automatizado para gerar GIFs animados de dados ambientais do MapBiomas via **Google Earth Engine**.

## Coleções Suportadas

| Dataset | Status |
|---------|--------|
| Degradação Col 10.1 | 386 GIFs gerados |
| Fire Col 5 | Configurado (em ajuste) |
| Fire Col 3 | Configurado |
| Paraguay Fire Col 1 | Configurado |
| LULC Col 9/10 | Configurado |
| Soil Carbon | Configurado |

## Setup Rápido

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "import ee; ee.Authenticate()"
```

## Gerar GIFs

```powershell
# Teste rápido (DF)
python run_pipeline_df.py

# Batch completo
python -m src.ipam_gif_factory.interfaces.cli --generate --batch batch_v001.json --workers 6 --resume
```

## Interfaces

- **Looker Studio** (público): dashboard com CSVs servidos via GCS
- **HTML local** (dev): galeria + disparo de batches (em desenvolvimento)

## Documentação

- `AGENTS.md` — Guia para agentes de IA
- `specs/` — Especificações detalhadas por feature
