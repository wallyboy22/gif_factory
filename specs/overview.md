---
tags: [overview]
aliases: [Visão Geral, Overview]
date: 2026-06-01
---

# Overview — Fábrica de GIFs

## Propósito

Pipeline automatizado para gerar GIFs animados a partir de dados raster do **Google Earth Engine (GEE)**.
Mostra mudanças ambientais temporais em biomas e territórios brasileiros.
Produto do **IPAM** com dados do **MapBiomas**.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Dados | Google Earth Engine (Python API `ee`) |
| Processamento | PIL/Pillow |
| Configuração | YAML (com includes e deep merge) |
| Orquestração | Python 3 (pipeline próprio) |
| Distribuição | Google Cloud Storage |
| Visualização pública | Looker Studio (CSV → GCS) |
| Visualização local | HTML estático (lê CSV do GCS) |
| Execução colaborativa | Google Colab Notebook |

## Estrutura de Diretórios

```
FABRICA DE GIFS/
├── config/                     # Configurações YAML
│   ├── datasets.yaml           # Catálogo de datasets e produtos
│   ├── territories.yaml        # Territórios (biomas, estados, regiões)
│   ├── visualization.yaml      # Parâmetros visuais (paletas, ranges)
│   ├── visualization_col101.yaml  # Overrides visuais Col 10.1
│   ├── visualization_reference.yaml  # Referência mestra de legendas
│   ├── paths.yaml              # Caminhos, dimensões, durações
│   └── visibility.json         # Toggles de visibilidade
├── src/ipam_gif_factory/       # Pacote Python principal
│   ├── config/                 # ConfigLoader
│   ├── core/                   # Pipeline, managers, processors
│   ├── interfaces/             # CLI, Dashboard, API (Flask), Colab
│   └── utils/                  # file_utils, ee_utils
├── specs/                      # Especificações (esta pasta)
├── scripts/                    # Scripts auxiliares
├── notebooks/                  # Jupyter notebooks
├── references/                 # Logos, legendas, fact sheets
├── referencia_mbfire_col5/     # Legendas oficiais MapBiomas Fire Col5
├── outputs/                    # Saída gerada (v001/)
├── tests/                      # Testes unitários
└── cache/                      # Cache local
```

## Coleções / Datasets

| Dataset | Categoria | Coleção | Status GIFs |
|---------|-----------|---------|-------------|
| `brasil_degradation_col10_1` | degradation | 10.1 | **386 GIFs gerados** |
| `brasil_fire_col5` | fire | 5 | Configurado, **pendente** |
| `brasil_fire_col3` | fire | 3 | Configurado, pendente |
| `paraguay_fire_col1` | fire | 1 | Configurado, pendente |
| `brasil_lulc_col9` | land_cover | 9 | Configurado, pendente |
| `brasil_lulc_col10` | land_cover | 10 | Configurado, pendente |
| `brasil_soil` | soil | — | Configurado, pendente |
| `brasil_degradation_col9` | degradation | 9 | Configurado, pendente |

## Interfaces

| Interface | Público | Tecnologia | Status |
|-----------|---------|------------|--------|
| Looker Studio | Público | CSV → GCS | Parcial |
| HTML local | Desenvolvedor | HTML + JS (lê CSV GCS) | Planejado |
| Colab Notebook | Colegas | Python + GEE | Planejado |

## Estado Atual (Jun 2026)

- Pipeline completo e funcional com 9 etapas e checkpoint/resume
- 386 GIFs de degradação Col 10.1 gerados (27 estados + 9 biomas)
- Fire Col 5 totalmente configurado, aguardando ajuste visual e geração
- Foco atual: **ajustar visualização Fire Col 5** → gerar → expandir
