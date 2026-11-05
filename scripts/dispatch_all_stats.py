"""Dispatch GEE area-stats exports for ALL brasil_fire_col5 products × territories.

Dispatches 1 task per combo (22 products × 8 territories = 176 tasks).
Does NOT wait — saves task metadata for later polling.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from mapbiomas_data.core.area_stats import AreaStatsCalculator
from mapbiomas_data.core.area_stats_engine import export_timeseries_csv
from mapbiomas_data.interfaces.cli import CLI

DATASET = "brasil_fire_col5"
TERRITORIES = [
    "uf_df", "regiao_matopiba",
    "bioma_amazonia", "bioma_caatinga", "bioma_cerrado",
    "bioma_mata_atlantica", "bioma_pampa", "bioma_pantanal",
]
SKIP = {"nbr_min"}

cli = CLI()
calc = AreaStatsCalculator(cli.config)
gcs_bucket = calc._get_gcs_bucket()

if not gcs_bucket:
    print("[ERRO] GCS bucket not configured")
    sys.exit(1)

print(f"GCS bucket: {gcs_bucket}")
print(f"DATASET: {DATASET}")
print(f"Territories ({len(TERRITORIES)}): {TERRITORIES}")
print()

products = cli.datasets.list_products(DATASET)
tasks_meta = []

for pinfo_short in products:
    pid = pinfo_short["id"]
    if pid in SKIP:
        print(f"  [SKIP] {pid} — RGB product, no area stats")
        continue

    pinfo = cli.datasets.get_product(DATASET, pid)

    for terr in TERRITORIES:
        territory_info = calc.territory_manager.get_territory(terr)
        if territory_info is None:
            print(f"  [SKIP] {pid} / {terr} — territory not found")
            continue

        territory_fc = calc.territory_manager.get_feature_collection(terr)

        print(f"\n  {'='*50}")
        print(f"  {pid} / {terr}")
        print(f"  {'='*50}")

        try:
            img = calc._load_image(pinfo)
            year_bands = calc._map_years_to_bands(
                img,
                pinfo.get("bands", []),
                pinfo.get("temporal_range"),
                pinfo.get("bands_slice"),
            )

            if not year_bands:
                print(f"  [SKIP] No bands to process")
                continue

            selectors = ["class_value", "area_ha", "year", "dataset", "product", "territory_id"]

            task = export_timeseries_csv(
                img=img,
                territory_fc=territory_fc,
                year_bands=year_bands,
                product_id=pid,
                territory_id=terr,
                dataset_id=DATASET,
                bucket_name=gcs_bucket,
                selectors=selectors,
            )

            tasks_meta.append({
                "task_id": task.id,
                "product": pid,
                "territory": terr,
                "state": "STARTED",
            })
            print(f"  [OK] Task started: {task.id}")

            # Rate limit: 1 task per second
            time.sleep(1)

        except Exception as e:
            print(f"  [ERRO] {e}")
            import traceback
            traceback.print_exc()
            continue

# Save global task list
output_base = os.path.join(cli.config.get_output_dir(), DATASET)
os.makedirs(output_base, exist_ok=True)
tasks_path = os.path.join(output_base, "_tasks.json")
existing = []
if os.path.exists(tasks_path):
    with open(tasks_path) as f:
        existing = json.load(f)

existing_ids = {t["task_id"] for t in existing}
for t in tasks_meta:
    if t["task_id"] not in existing_ids:
        existing.append(t)
        existing_ids.add(t["task_id"])

with open(tasks_path, "w") as f:
    json.dump(existing, f, indent=2)

print(f"\n{'='*50}")
print(f"  Done. {len(tasks_meta)} new tasks dispatched.")
print(f"  Total tasks tracked: {len(existing)}")
print(f"  Tasks file: {tasks_path}")
