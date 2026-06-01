---
tags: [hub, index]
aliases: [Home, Especificações, Specs]
date: 2026-06-01
---

# Especificações — Fábrica de GIFs

## Arquitetura
- [[overview]] — Visão geral, stack, estrutura, status
- [[pipeline]] — Pipeline 9 etapas, checkpoint/resume
- [[config-system]] — Sistema YAML, ConfigLoader, merge
- [[datasets]] — Catálogo de datasets e produtos
- [[visualization]] — Paletas, legendas, cmap types
- [[territories]] — Territórios, FeatureCollections
- [[batch-processing]] — Batch JSON, workers, scripts

## Coleções
- [[degradation-col101]] — Degradação Col 10.1 (386 GIFs)
- [[fire-col5]] — Fire Col 5 (em ajuste)

## Interfaces
- [[looker]] — Looker Studio (CSV → GCS)
- [[html-interface]] — Galeria local + disparo
- [[colab]] — Notebook colaborativo

---

```dataview
TABLE tags, aliases, date
FROM "specs"
SORT date DESC
```
