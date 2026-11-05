"""Download area-stats CSVs from GCS and assemble unified CSVs.

Two modes:
  default:   Reads _tasks.json, checks each task's state via EE API (listOperations),
             downloads COMPLETED tasks, and writes unified CSVs.
  --gcs-only: Skips EE polling entirely. Checks blob existence directly on GCS.
             If blob exists → downloads. If not → marks PENDING.

Run in a loop (2×) to catch tasks that finish between iterations.
Already-downloaded combos are skipped on subsequent runs.
"""
import argparse
import csv
import json
import os
import sys
import time

import ee

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from google.cloud import storage
from mapbiomas_data.core.area_stats import AreaStatsCalculator
from mapbiomas_data.interfaces.cli import CLI

DATASET = "brasil_fire_col5"

parser = argparse.ArgumentParser(description="Download area-stats CSVs from GCS")
parser.add_argument("--gcs-only", action="store_true",
                    help="Skip EE polling, check blob existence directly on GCS")
args = parser.parse_args()

cli = CLI()
calc = AreaStatsCalculator(cli.config)
gcs_bucket_name = calc._get_gcs_bucket()

if not gcs_bucket_name:
    print("[ERRO] GCS bucket not configured")
    sys.exit(1)

output_base = os.path.join(cli.config.get_output_dir(), DATASET)
tasks_path = os.path.join(output_base, "_tasks.json")

if not os.path.exists(tasks_path):
    print(f"[SKIP] No tasks file at {tasks_path}")
    sys.exit(0)

with open(tasks_path) as f:
    tasks = json.load(f)

if not tasks:
    print("[SKIP] No tasks to check")
    sys.exit(0)

storage_client = storage.Client()
bucket = storage_client.bucket(gcs_bucket_name)

pending = [t for t in tasks if t.get("state") in ("STARTED", "RUNNING", "UNKNOWN")]
already = [t for t in tasks if t.get("state") == "COMPLETED"]
failed_pre = [t for t in tasks if t.get("state") in ("FAILED", "CANCELLED")]

new_completed = 0
new_failed = 0

print(f"Tasks: {len(tasks)} total, {len(pending)} pending, {len(already)} already completed")

for task_entry in tasks:
    state = task_entry.get("state", "UNKNOWN")
    if state == "COMPLETED":
        continue  # already downloaded
    if state in ("FAILED", "CANCELLED"):
        continue  # already marked

    pid = task_entry["product"]
    terr = task_entry["territory"]

    if args.gcs_only:
        # --- GCS-only mode: check blob existence directly, no EE polling ---
        gcs_blob_path = f"area_stats/{DATASET}/{pid}/{terr}/all_years.csv"
        blob = bucket.blob(gcs_blob_path)

        if blob.exists():
            current_state = "COMPLETED"
        else:
            current_state = "PENDING"

        task_entry["state"] = current_state
        print(f"  [{pid:35s} / {terr:20s}] {current_state}")

        if current_state != "COMPLETED":
            continue

        # Check if already downloaded locally
        output_dir = calc._get_output_dir(DATASET, pid, terr)
        area_stats_dir = calc._get_area_stats_dir(output_dir)
        unified_csv = os.path.join(area_stats_dir, f"{pid}_{terr}_area_stats.csv")

        if os.path.exists(unified_csv):
            print(f"    Already downloaded, skipping")
            new_completed += 1
            continue

        territory_info = calc.territory_manager.get_territory(terr)
        territory_name = territory_info.get("name", terr) if territory_info else terr

        pinfo = cli.datasets.get_product(DATASET, pid)
        viz_key = pinfo.get("visualization", "fire")
        class_labels = calc.get_class_labels(viz_key)

        tmp_csv = os.path.join(area_stats_dir, "_all_years.csv")
        os.makedirs(area_stats_dir, exist_ok=True)
        blob.download_to_filename(tmp_csv)

        all_records = []
        with open(tmp_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cls_val = int(row.get("class_value", 0))
                all_records.append({
                    "dataset": DATASET,
                    "product": pid,
                    "territory_id": terr,
                    "territory_name": territory_name,
                    "year": row.get("year", "static"),
                    "class_value": cls_val,
                    "class_name": class_labels.get(cls_val, f"Class {cls_val}"),
                    "area_ha": float(row.get("area_ha", 0)),
                })
        os.remove(tmp_csv)

        all_records.sort(key=lambda r: (r["year"], r["class_value"]))
        with open(unified_csv, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "dataset", "product", "territory_id", "territory_name",
                "year", "class_value", "class_name", "area_ha",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)

        print(f"    [OK] CSV salvo: {unified_csv} ({len(all_records)} rows)")
        new_completed += 1
        time.sleep(0.3)

    else:
        # --- Original mode: poll EE task state via listOperations ---
        search_prefix = f"area_stats_{pid}_{terr}_all"
        current_state = "NOT_FOUND"
        try:
            root = ee.data.getAssetRoots()[0]["id"].replace("projects/", "")
            operations = ee.data.listOperations(root)
            for op in (operations or []):
                meta = op.get("metadata", {})
                if meta.get("description") == search_prefix:
                    current_state = meta.get("state", "UNKNOWN")
                    break
        except Exception as exc:
            print(f"    [WARN] EE listOperations error: {exc}")

        task_entry["state"] = current_state
        print(f"  [{pid:35s} / {terr:20s}] {current_state}")

        if current_state == "COMPLETED":
            output_dir = calc._get_output_dir(DATASET, pid, terr)
            area_stats_dir = calc._get_area_stats_dir(output_dir)
            unified_csv = os.path.join(area_stats_dir, f"{pid}_{terr}_area_stats.csv")

            if os.path.exists(unified_csv):
                print(f"    Already downloaded, skipping")
                new_completed += 1
                continue

            gcs_blob_path = f"area_stats/{DATASET}/{pid}/{terr}/all_years.csv"
            blob = bucket.blob(gcs_blob_path)

            if not blob.exists():
                print(f"    Blob not found yet, will retry")
                task_entry["state"] = "STARTED"
                continue

            territory_info = calc.territory_manager.get_territory(terr)
            territory_name = territory_info.get("name", terr) if territory_info else terr

            pinfo = cli.datasets.get_product(DATASET, pid)
            viz_key = pinfo.get("visualization", "fire")
            class_labels = calc.get_class_labels(viz_key)

            tmp_csv = os.path.join(area_stats_dir, "_all_years.csv")
            os.makedirs(area_stats_dir, exist_ok=True)
            blob.download_to_filename(tmp_csv)

            all_records = []
            with open(tmp_csv, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cls_val = int(row.get("class_value", 0))
                    all_records.append({
                        "dataset": DATASET,
                        "product": pid,
                        "territory_id": terr,
                        "territory_name": territory_name,
                        "year": row.get("year", "static"),
                        "class_value": cls_val,
                        "class_name": class_labels.get(cls_val, f"Class {cls_val}"),
                        "area_ha": float(row.get("area_ha", 0)),
                    })
            os.remove(tmp_csv)

            all_records.sort(key=lambda r: (r["year"], r["class_value"]))
            with open(unified_csv, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "dataset", "product", "territory_id", "territory_name",
                    "year", "class_value", "class_name", "area_ha",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_records)

            print(f"    [OK] CSV salvo: {unified_csv} ({len(all_records)} rows)")
            new_completed += 1
            time.sleep(0.3)

        elif current_state in ("FAILED", "CANCELLED"):
            new_failed += 1

# Save updated states
with open(tasks_path, "w") as f:
    json.dump(tasks, f, indent=2)

# Re-count for summary
final_completed = sum(1 for t in tasks if t.get("state") == "COMPLETED")
final_failed = sum(1 for t in tasks if t.get("state") in ("FAILED", "CANCELLED"))
final_pending = sum(1 for t in tasks if t.get("state") in ("STARTED", "RUNNING", "UNKNOWN", "NOT_FOUND", "PENDING"))

print(f"\n{'='*50}")
print(f"  COMPLETED: {final_completed}")
print(f"  FAILED:    {final_failed}")
print(f"  PENDING:   {final_pending}")
print(f"{'='*50}")

if final_failed > 0:
    sys.exit(1)
