---
tags: [batch, pipeline]
aliases: [Batch, Processamento em Lote]
date: 2026-06-01
---

[[pipeline]] | [[territories]] | [[fire-col5]] | [[degradation-col101]]

# Processamento em Lote (Batch)

## Formato do Batch JSON

Arquivo JSON com array de objetos, cada um com 3 campos:

```json
[
    {
        "territory": "<territory_id>",
        "dataset": "<dataset_id>",
        "product": "<product_id>"
    }
]
```

## Arquivos de Batch Existentes

| Arquivo | Entradas | Escopo |
|---------|----------|--------|
| `batch_v001.json` | 150 | 10 territórios x 15 produtos (degradation_col10_1) |
| `batch_canopy.json` | 10 | 10 territórios x canopy_disturbance_frequency |
| `batch_patch_size.json` | 10 | 10 territórios x patch_size |

## Como Executar um Batch

### Via CLI (PowerShell)

```powershell
python -m src.ipam_gif_factory.interfaces.cli --generate --batch batch_v001.json --workers 6 --resume
```

### Via Python script

```python
from src.ipam_gif_factory.core.pipeline import Pipeline
from src.ipam_gif_factory.config import ConfigLoader
from concurrent.futures import ThreadPoolExecutor

config = ConfigLoader()
pipeline = Pipeline(config)

def process(entry):
    pipeline.run(
        dataset_id=entry["dataset"],
        product_id=entry["product"],
        territory_id=entry["territory"],
        create_collage=True,
        add_labels=True,
        vertical_dimension=1560,
        cell_height=300,
        resume=True,
    )

with ThreadPoolExecutor(max_workers=6) as ex:
    ex.map(process, batch_entries)
```

### Via Colab Notebook

```python
# Ver spec colab.md
```

## Scripts de Execução

| Script | Descrição |
|--------|-----------|
| `run_all_v001.ps1` | Gera batch_v001.json e dispara CLI com 6 workers, --resume |
| `run_degradacao_biomas.py` | Python: 13 produtos x 8 territórios, ThreadPoolExecutor |
| `run_matopiba_degradacao.py` | Python sequencial: matopiba/df/cerrado seletivo |
| `run_pipeline_df.py` | Teste único: fire_col3 annual_burned DF |
| `run_frequency_test.py` | Teste único: fire_col3 frequency DF |

## Workers e Paralelismo

- `--workers N`: Cada worker executa um combo dataset+produto+território
- Usa `ThreadPoolExecutor` (não ProcessPool) — GEE é I/O bound
- Cada worker tem seu próprio estado de autenticação GEE
- `--resume`: cada worker verifica seus próprios checkpoints

## Convenções para Criar um Novo Batch

1. Definir lista de territórios
2. Definir lista de produtos
3. Gerar produto cartesiano (territory × product)
4. Salvar JSON
5. Executar com `--resume` para tolerância a falhas

Exemplo para Fire Col 5:

```python
import json

territories = ["df", "amazonia", "cerrado", "caatinga", "pantanal",
               "mata_atlantica", "pampa", "biomas"]
products = ["annual_burned", "annual_burned_coverage", "monthly_burned",
            "scar_size_range", "accumulated_burned", "accumulated_burned_coverage",
            "fire_frequency", "year_last_fire", "time_after_fire"]

batch = []
for t in territories:
    for p in products:
        batch.append({"territory": t, "dataset": "brasil_fire_col5", "product": p})

with open("batch_fire_col5.json", "w") as f:
    json.dump(batch, f, indent=2)

print(f"Total: {len(batch)} combinações")
```

## Estimativas

- ~40 frames por produto (1985-2025 = 41 anos)
- ~45s-120s por combo (depende do território, resolução, rede)
- Com 6 workers: ~150 combos ≈ 30-60 minutos
- Tamanho por GIF: ~2-10 MB
- Armazenamento: ~150 combos × ~5 MB ≈ 750 MB
