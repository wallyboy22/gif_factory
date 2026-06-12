---
tags: [html, interface]
aliases: [HTML Interface, Galeria Local]
date: 2026-06-01
---

# HTML Interface — Galeria Local + Disparo

## Objetivo

Interface web local para o desenvolvedor:
1. **Galeria:** visualizar GIFs existentes com filtros (dataset, território, produto)
2. **Disparo:** selecionar combinações e disparar geração de batches

## Arquitetura Proposta

```
HTML estático (single page) → servido localmente
     ↓ fetch CSV
GCS CSV (cache local ou proxy)
     ↓ parse
Renderiza galeria com filtros
     ↓ botão disparar
POST /api/generate → Flask API local (api.py existente)
     ↓
Pipeline.run() em background thread
     ↓
Poll status via SSE ou polling
```

## Tecnologias

- **Frontend:** HTML + CSS + JavaScript vanilla (sem framework)
- **Backend:** Flask API existente (`src/mapbiomas_data/interfaces/api.py`)
- **Dados:** CSV index no GCS (lido via fetch CORS ou servido pelo Flask)

## Funcionalidades da Galeria

1. **Grid de GIFs** com thumbnail, nome do produto e território
2. **Filtros:**
   - Dropdown: Dataset
   - Dropdown: Produto (cascade do dataset)
   - Dropdown: Território
   - Busca: texto livre
3. **Clique no GIF:** abre modal com:
   - GIF animado em tamanho maior
   - Collage PNG
   - Metadados (tempo de geração, dimensões, EE estimates)
   - Link direto GCS para download

## Funcionalidades do Disparo

1. **Seleção de dataset** → carrega produtos disponíveis
2. **Seleção de produto(s)** — múltiplos com checkboxes
3. **Seleção de território(s)** — múltiplos com checkboxes
4. **Configurações:**
   - `vertical_dimension` (default: 1560)
   - `create_collage` (checkbox, default: true)
   - `add_labels` (checkbox, default: true)
   - `resume` (checkbox, default: true)
5. **Botão "Gerar"** → submete batch para API
6. **Status bar:**
   - Progresso (X/Y concluído)
   - Tempo decorrido / estimado
   - Log das últimas execuções

## API Endpoints (Flask)

A API Flask existente já tem endpoints para:
- `GET /api/categories` — listar categorias
- `GET /api/datasets` — listar datasets
- `GET /api/datasets/<id>/products` — listar produtos
- `GET /api/territories` — listar territórios
- `GET /api/visualizations` — listar visualizações
- `POST /api/generate` — disparar geração

Precisa adicionar/ajustar:
- `GET /api/status` — status da fila de geração (queue.json)
- `GET /api/index` — servir CSV index (lê do GCS ou local)
- `POST /api/batch` — aceitar múltiplos combos de uma vez

## Como Servir

```powershell
# Subir API Flask
python -m src.mapbiomas_data.interfaces.api

# Servir HTML (pode ser a própria Flask servindo estáticos)
# Ou: servidor HTTP simples
python -m http.server 8080 --directory html/
```

## Estrutura de Arquivos (proposta)

```
html/
├── index.html          # Página principal (galeria + disparo)
├── css/
│   └── style.css       # Estilos (minimalista, funcional)
├── js/
│   ├── gallery.js      # Lógica da galeria e filtros
│   ├── dispatch.js     # Lógica de disparo de batches
│   └── api.js          # Wrapper fetch para API Flask
└── assets/
    └── logo.png        # Logo IPAM/MapBiomas
```

## Prioridade

Baixa — implementar após Fire Col 5 estar gerando GIFs consistentemente.

