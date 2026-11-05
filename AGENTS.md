# Session Learnings — Fábrica de GIFs (brasil_fire_col5)

## EE Area Stats (no `frequencyHistogram`)
- O JS toolkit **não usa** `frequencyHistogram`. Usa `reduceRegion` com `ee.Reducer.sum().group(groupField=1, groupName='class')`.
- Export único por combo (product × territory) via `ee.batch.Export.table.toCloudStorage()` com parâmetro `selectors` para controlar colunas.
- Não fazer decode dos pixels durante export — produtos compostos já têm `processor` próprio.

## Pipeline Architecture
- **dispatch_all_stats.py**: dispara 184 tasks GEE (23 produtos × 8 territórios), 1s delay entre cada.
- **process_maps.py**: independente, roda com `ThreadPoolExecutor(8)`, `resume=True`. Gera thumbnails + GIFs de cada combo.
- **download_stats_from_gcs.py**: lê `_tasks.json`, checa estado via `ee.data.listOperations(root)`, baixa CSVs COMPLETOS do GCS.
- **process_from_csv.py**: lê CSV unificado → ChartGenerator + Composer, `ThreadPoolExecutor(4)`.
- Loop: download_stats → process_from_csv (2× para capturar tasks que terminam entre runs).

## Territories (8)
```python
TERRITORIES = [
    "uf_df", "regiao_matopiba",
    "bioma_amazonia", "bioma_caatinga", "bioma_cerrado",
    "bioma_mata_atlantica", "bioma_pampa", "bioma_pantanal",
]
```
- `biomas_todos` é redundante (soma dos 6 biomas) — skip.

## EE Task Polling
```python
root = ee.data.getAssetRoots()[0]["id"].replace("projects/", "")
operations = ee.data.listOperations(root)
for op in operations:
    meta = op.get("metadata", {})
    if meta.get("description") == search_prefix:
        state = meta.get("state", "UNKNOWN")
```
- Usar `getAssetRoots()` — `listOperations()` sem argumento não funciona.

## GCS Paths
- Pattern: `area_stats/{dataset}/{product}/{territory}/all_years.csv`
- Bucket: `mapbiomas-fire`

## selectors default
```python
["class_value", "area_ha", "year", "dataset", "product", "territory_id"]
```

## Product Info
- `list_products(dataset)` retorna dict **sem** `asset`.
- Usar `get_product(dataset, pid)` para info completa (asset, bands, visualization, etc.).
- `_load_image()` checa `product_info.get("asset", "")` — se vazio, levanta `ValueError`.

## Products ativos: 23 (24 total, skip `nbr_min`)
annual_burned, monthly_burned, scar_size_range, accumulated_burned, fire_frequency, year_last_fire, time_after_fire, unprecedented_fire, annual_burned_coverage_nivel0..4, accumulated_burned_coverage_nivel0..4, severity, fire_return_interval, mean_fire_return_interval. (nbr_min é produto RGB sem stats.)

## Composer Legend Fix
- `legend_h` de `leg_font_sz * 2` → `leg_font_sz * 3` para dar espaço ao label.
- `viz_min` padding: `+4`.
- Label_text em linha separada (não mais na mesma linha do bloco de cor).

## Idempotência
- `process_maps.py` com `resume=True` — StateManager salva progresso, pode reiniciar.
- `download_stats_from_gcs.py` pula CSVs já baixados localmente.
- `process_from_csv.py` verifica se CSV unificado existe antes de processar.

## Environment
- Python 3.x com `ee`, `google-cloud-storage`, `Pillow`, `matplotlib`.
- PYTHONPATH precisa incluir `src/` (`$env:PYTHONPATH = "src"` no PowerShell).
- Output dir: `./outputs/v002/brasil_fire_col5/`.
- `_tasks.json` em `{output_dir}/_tasks.json`.
