---
tags: [colab, interface, notebook]
aliases: [Colab Notebook, Notebook Colaborativo]
date: 2026-06-01
---

# Colab Notebook — Disparo Colaborativo

**STATUS: Implementado. Ver `notebooks/fabrica_fire_col5.ipynb`.**

## Objetivo

Notebook interativo para gerar GIFs animados de dados do MapBiomas via Google Earth Engine.
Funciona no Google Colab e no VS Code (Jupyter extension).

## Por que Colab?

- RAM ampliada (até 25GB com Colab Pro)
- Acesso direto ao GEE (já autenticado no ambiente Google)
- Permite 8 workers paralelos (CPU virtualizada generosa)
- Compartilhável: um link resolve
- Sem instalação local

## Estrutura (4 células)

```
┌─ Célula 1: Setup ─────────────────────────────┐
│ • Detecta Colab vs VS Code                     │
│ • Colab: clone repo, pip install, autentica    │
│ • VS Code: usa venv local                      │
│ • Auto-detect workers (cpu_count - 1, max 12)  │
│ • ConfigLoader                                 │
├─ Célula 2: Seleção ───────────────────────────┤
│ • ipywidgets (funciona em ambos)               │
│ • Dropdown dataset (default: brasil_fire_col5) │
│ • SelectMultiple produtos (auto-popula)        │
│ • SelectMultiple territórios (pré-seleciona)   │
│ • IntText workers, Checkbox resume/collage     │
│ • Botão "Gerar Batch"                          │
├─ Célula 3: Execução ──────────────────────────┤
│ • ThreadPoolExecutor (N workers)               │
│ • pipeline.run() p/ cada combo                 │
│ • Progresso real-time [i/total]                │
│ • Resumo final: OK/Falha                       │
├─ Célula 4: Resultados ────────────────────────┤
│ • Lista de GIFs gerados (nome + tamanho)       │
│ • Preview dos 3 primeiros GIFs                 │
│ • Links GCS                                    │
└────────────────────────────────────────────────┘
```

## Dual-Mode (Colab + VS Code)

```python
try:
    import google.colab
    IN_COLAB = True
    # clone, pip install, ee.Authenticate()
except ImportError:
    IN_COLAB = False
    # sys.path.insert, usa venv local
```

## Auto-detect Workers

```python
WORKERS = max(1, min((os.cpu_count() or 4) - 1, 12))
# Guarda 1 core pro sistema, máximo 12
```

## Widgets

- `ipywidgets` — Dropdown, SelectMultiple, Checkbox, Button
- `IPython.display` — display, clear_output
- Compatível com Colab e VS Code Jupyter

## Como usar (colegas)

1. Abrir notebook no Colab ou VS Code
2. Rodar Célula 1 (setup)
3. Na Célula 2, selecionar dataset, produtos, territórios
4. Clicar "Gerar Batch"
5. Ver resultados na Célula 4

## Para adicionar datasets/territórios novos

Ver templates:
- `scripts/_template_batch.py` — template de batch com seções editáveis
- `scripts/_template_dataset.py` — como adicionar dataset ao YAML
- `scripts/_template_territory.py` — como adicionar território ao YAML
