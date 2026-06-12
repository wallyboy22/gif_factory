import json
import os
import time
import csv
import re
from typing import Any, Dict, List, Optional, Tuple
import ee
from ..config import ConfigLoader
from ..core import TerritoryManager
from ..core.ee_transforms import run_processor


class AreaStatsCalculator:
    """Compute per-class area statistics from Earth Engine images.

    For each (product, territory) combination, computes per-class pixel area
    using ee.Image.pixelArea() + reduceRegion(group) and exports as CSV.

    Products are raster stacks (years as bands), NOT ImageCollections.
    """

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.territory_manager = TerritoryManager(config)
        self._class_labels: Dict[str, Dict[int, str]] = {}
        self._viz_reference: Dict[str, Dict[str, Any]] = {}
        self._load_class_labels()
        try:
            ee.Initialize(project=self.config.ee_project_id)
        except Exception:
            pass

    def _load_class_labels(self):
        """Load class labels and viz reference from visualization_reference.yaml
        with fallback to visualization.yaml."""
        import yaml
        self._viz_reference = {}

        # Primary: visualization_reference.yaml
        ref_path = os.path.join(self.config.config_dir, "visualization_reference.yaml")
        if os.path.exists(ref_path):
            with open(ref_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            ref = data.get("visualization_reference", {})
            self._viz_reference.update(ref)
            for viz_key, viz_data in ref.items():
                classes = viz_data.get("classes", [])
                if classes:
                    self._class_labels[viz_key] = {c["value"]: c["label"] for c in classes}

        # Fallback: visualization.yaml (for keys not in primary)
        viz_path = os.path.join(self.config.config_dir, "visualization.yaml")
        if os.path.exists(viz_path):
            with open(viz_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            viz_entries = data.get("visualizations", {})
            for viz_key, viz_data in viz_entries.items():
                if viz_key not in self._viz_reference:
                    self._viz_reference[viz_key] = viz_data
                    # Build class_labels from discrete_labels if present
                    labels = viz_data.get("discrete_labels", [])
                    if labels:
                        self._class_labels[viz_key] = {i: lbl for i, lbl in enumerate(labels)}

    def get_class_labels(self, viz_key: str) -> Dict[int, str]:
        return self._class_labels.get(viz_key, {})

    def get_viz_reference(self, viz_key: str) -> Dict[str, Any]:
        return self._viz_reference.get(viz_key, {})

    def _load_image(self, product_info: Dict[str, Any]) -> ee.Image:
        processor_name = product_info.get("processor")
        if processor_name:
            return run_processor(processor_name)
        asset_id = product_info.get("asset", "")
        if not asset_id:
            raise ValueError(f"Product has no asset: {product_info.get('id')}")
        return ee.Image(asset_id)

    def _map_years_to_bands(
        self, img: ee.Image, yaml_bands: List[str],
        temporal_range: Tuple[int, int], bands_slice: Optional[List[int]]
    ) -> List[Tuple[int, str]]:
        """Map each year to its corresponding band name in the EE image.

        Returns list of (year, band_name) tuples. Year == 0 means static (no temporal).
        """
        real_band_names = img.bandNames().getInfo()

        if bands_slice and len(bands_slice) == 2:
            real_band_names = real_band_names[
                bands_slice[0]:bands_slice[1]
            ]

        # Filter to YAML bands if they exist in the image
        if yaml_bands:
            valid = [b for b in yaml_bands if b in real_band_names]
            if valid:
                pass
            else:
                valid = real_band_names
        else:
            valid = real_band_names

        if not temporal_range or len(temporal_range) != 2:
            return [(0, b) for b in valid]

        tr_start, tr_end = temporal_range
        num_years = tr_end - tr_start + 1
        num_bands = len(valid)

        # Strategy 1: band names contain year suffix (most common)
        candidate = []
        for year in range(tr_start, tr_end + 1):
            for band in valid:
                if re.search(rf'(?:_|^){year}(?:_|$)', band):
                    candidate.append((year, band))
                    break
        if len(candidate) == num_years:
            return candidate

        # Strategy 2: sequential match (N bands = N years)
        if num_bands == num_years:
            return [(tr_start + i, valid[i]) for i in range(num_years)]
        elif num_bands > num_years:
            return [(tr_start + i, valid[i]) for i in range(num_years)]

        # Fallback: use whatever we have
        return [(tr_start + i if i < num_years else 0, valid[i])
                for i in range(num_bands)]

    def _get_output_dir(self, dataset_id: str, product_id: str, territory_id: str) -> str:
        base = self.config.get_output_dir()
        return os.path.join(base, dataset_id, product_id, territory_id)

    def _get_area_stats_dir(self, output_dir: str) -> str:
        d = os.path.join(output_dir, "area_stats")
        os.makedirs(d, exist_ok=True)
        return d

    def _get_tasks_path(self, output_dir: str) -> str:
        return os.path.join(self._get_area_stats_dir(output_dir), "_tasks.json")

    def _save_tasks(self, output_dir: str, tasks: List[Dict]):
        path = self._get_tasks_path(output_dir)
        existing = []
        if os.path.exists(path):
            with open(path) as f:
                existing = json.load(f)
        existing.extend(tasks)
        with open(path, "w") as f:
            json.dump(existing, f, indent=2)

    def _load_tasks(self, output_dir: str) -> List[Dict]:
        path = self._get_tasks_path(output_dir)
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return []

    def compute_and_save(
        self,
        dataset_id: str,
        product_id: str,
        territory_id: str,
        product_info: Dict[str, Any],
        use_gcs: bool = False,
        resume: bool = False,
    ) -> List[str]:
        """Compute area stats for a (product, territory) and save unified CSV.

        Returns list of CSV paths that were saved (single unified CSV).
        """
        territory_info = self.territory_manager.get_territory(territory_id)
        if territory_info is None:
            print(f"  [SKIP] Territory '{territory_id}' not found")
            return []
        territory_name = territory_info.get("name", territory_id)
        territory_fc = self.territory_manager.get_feature_collection(territory_id)

        viz_key = product_info.get("visualization", "fire")
        class_labels = self.get_class_labels(viz_key)

        output_dir = self._get_output_dir(dataset_id, product_id, territory_id)
        area_stats_dir = self._get_area_stats_dir(output_dir)
        tasks_record = []

        yaml_bands = product_info.get("bands", [])
        temporal_range = product_info.get("temporal_range")
        bands_slice = product_info.get("bands_slice")

        img = self._load_image(product_info)
        year_bands = self._map_years_to_bands(
            img, yaml_bands, temporal_range, bands_slice
        )

        if not year_bands:
            print(f"  [SKIP] No bands to process for '{product_id}'")
            return []

        unified_csv = os.path.join(area_stats_dir, f"{product_id}_{territory_id}_area_stats.csv")

        # Resume: unified CSV exists
        if resume and os.path.exists(unified_csv):
            print(f"  Unified CSV exists, skipping")
            return [unified_csv]

        all_records: List[Dict] = []

        for year, band_name in year_bands:
            year_str = str(year) if year > 0 else "static"

            # Resume via per-year local CSV (backward compat)
            per_year_csv = os.path.join(area_stats_dir, f"{year_str}.csv")
            if resume and os.path.exists(per_year_csv):
                with open(per_year_csv, newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        all_records.append({
                            "dataset": dataset_id,
                            "product": product_id,
                            "territory_id": territory_id,
                            "territory_name": territory_name,
                            "year": year_str,
                            "class_value": int(row.get("class", row.get("class_value", 0))),
                            "class_name": class_labels.get(
                                int(row.get("class", row.get("class_value", 0))),
                                row.get("class_name", f"Class {row.get('class', row.get('class_value', 0))}"),
                            ),
                            "area_ha": float(row.get("area_ha", row.get("area_sqm", 0))) / 10000
                            if "area_sqm" in row and "area_ha" not in row
                            else float(row.get("area_ha", 0)),
                        })
                print(f"  [{year_str}] Loaded from per-year CSV")
                continue

            # Resume: GCS per-year
            gcs_path = None
            if resume and use_gcs:
                from google.cloud import storage
                paths_cfg = getattr(self.config, "paths", {})
                gcs_cfg = paths_cfg.get("paths", {}).get("google_cloud_storage", {})
                bucket_name = gcs_cfg.get("bucket")
                gcs_prefix = gcs_cfg.get("hub_root", "")
                if bucket_name:
                    gcs_path = self._gcs_csv_path(
                        bucket_name, gcs_prefix, dataset_id,
                        product_id, territory_id, f"{year_str}.csv"
                    )
                    try:
                        client = storage.Client()
                        blob = client.bucket(bucket_name).blob(gcs_path)
                        if blob.exists():
                            tmp_csv = os.path.join(area_stats_dir, f"_{year_str}.csv")
                            blob.download_to_filename(tmp_csv)
                            with open(tmp_csv, newline="") as f:
                                reader = csv.DictReader(f)
                                for row in reader:
                                    all_records.append({
                                        "dataset": dataset_id,
                                        "product": product_id,
                                        "territory_id": territory_id,
                                        "territory_name": territory_name,
                                        "year": year_str,
                                        "class_value": int(row.get("class", row.get("class_value", 0))),
                                        "class_name": class_labels.get(
                                            int(row.get("class", row.get("class_value", 0))),
                                            row.get("class_name", f"Class {row.get('class', row.get('class_value', 0))}"),
                                        ),
                                        "area_ha": float(row.get("area_ha", row.get("area_sqm", 0))) / 10000
                                        if "area_sqm" in row and "area_ha" not in row
                                        else float(row.get("area_ha", 0)),
                                    })
                            os.remove(tmp_csv)
                            print(f"  [{year_str}] Downloaded from GCS")
                            continue
                    except Exception:
                        pass

            # Resume: EE task
            if resume:
                task_status = self._check_ee_task(product_id, territory_id, year_str)
                if task_status == "COMPLETED" and use_gcs and gcs_path:
                    tmp_csv = os.path.join(area_stats_dir, f"_{year_str}.csv")
                    self._download_from_gcs(gcs_path, tmp_csv)
                    with open(tmp_csv, newline="") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            all_records.append({
                                "dataset": dataset_id,
                                "product": product_id,
                                "territory_id": territory_id,
                                "territory_name": territory_name,
                                "year": year_str,
                                "class_value": int(row.get("class", row.get("class_value", 0))),
                                "class_name": class_labels.get(
                                    int(row.get("class", row.get("class_value", 0))),
                                    row.get("class_name", f"Class {row.get('class', row.get('class_value', 0))}"),
                                ),
                                "area_ha": float(row.get("area_ha", row.get("area_sqm", 0))) / 10000
                                if "area_sqm" in row and "area_ha" not in row
                                else float(row.get("area_ha", 0)),
                            })
                    os.remove(tmp_csv)
                    print(f"  [{year_str}] Downloaded (task COMPLETED)")
                    continue
                elif task_status == "RUNNING":
                    print(f"  [{year_str}] Task RUNNING, waiting...")
                    self._wait_for_task(product_id, territory_id, year_str)
                    if use_gcs and gcs_path:
                        tmp_csv = os.path.join(area_stats_dir, f"_{year_str}.csv")
                        self._download_from_gcs(gcs_path, tmp_csv)
                        with open(tmp_csv, newline="") as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                all_records.append({
                                    "dataset": dataset_id,
                                    "product": product_id,
                                    "territory_id": territory_id,
                                    "territory_name": territory_name,
                                    "year": year_str,
                                    "class_value": int(row.get("class", row.get("class_value", 0))),
                                    "class_name": class_labels.get(
                                        int(row.get("class", row.get("class_value", 0))),
                                        row.get("class_name", f"Class {row.get('class', row.get('class_value', 0))}"),
                                    ),
                                    "area_ha": float(row.get("area_ha", row.get("area_sqm", 0))) / 10000
                                    if "area_sqm" in row and "area_ha" not in row
                                    else float(row.get("area_ha", 0)),
                                })
                        os.remove(tmp_csv)
                    continue

            # --- Compute ---
            year_img = img.select(band_name)

            if use_gcs:
                bucket_name = self._get_gcs_bucket()
                if bucket_name:
                    task = self._export_to_gcs(
                        year_img, territory_fc, product_id, territory_id,
                        year_str, dataset_id, bucket_name
                    )
                    tasks_record.append({
                        "task_id": task.id,
                        "product": product_id,
                        "territory": territory_id,
                        "year": year_str,
                        "state": "STARTED",
                    })
                    print(f"  [{year_str}] Export task started: {task.id}")
                else:
                    print(f"  [WARN] No GCS bucket configured, computing locally")
                    records = self._compute_local(year_img, territory_fc)
                    for r in records:
                        r.update({
                            "dataset": dataset_id,
                            "product": product_id,
                            "territory_id": territory_id,
                            "territory_name": territory_name,
                            "year": year_str,
                            "class_name": class_labels.get(r["class_value"], f"Class {r['class_value']}"),
                        })
                    all_records.extend(records)
            else:
                records = self._compute_local(year_img, territory_fc)
                for r in records:
                    r.update({
                        "dataset": dataset_id,
                        "product": product_id,
                        "territory_id": territory_id,
                        "territory_name": territory_name,
                        "year": year_str,
                        "class_name": class_labels.get(r["class_value"], f"Class {r['class_value']}"),
                    })
                all_records.extend(records)
                print(f"  [{year_str}] Local computation done")

        if tasks_record:
            self._save_tasks(output_dir, tasks_record)

        # Sort by year, class_value
        all_records.sort(key=lambda r: (r["year"], r["class_value"]))

        # Write unified CSV
        os.makedirs(area_stats_dir, exist_ok=True)
        fieldnames = ["dataset", "product", "territory_id", "territory_name",
                       "year", "class_value", "class_name", "area_ha"]
        with open(unified_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)

        print(f"  Unified CSV: {unified_csv} ({len(all_records)} rows)")
        return [unified_csv]

    def _get_gcs_bucket(self) -> Optional[str]:
        paths_cfg = getattr(self.config, "paths", {})
        return paths_cfg.get("paths", {}).get("google_cloud_storage", {}).get("bucket")

    def _gcs_csv_path(
        self, bucket: str, prefix: str, dataset_id: str,
        product_id: str, territory_id: str, filename: str
    ) -> str:
        return f"{prefix}/area_stats/{dataset_id}/{product_id}/{territory_id}/{filename}"

    def _compute_local(
        self, img: ee.Image, territory_fc: ee.FeatureCollection,
    ) -> List[Dict]:
        area_img = ee.Image.pixelArea()
        stacked = area_img.addBands(img.select(0))

        # Class-grouped area
        stats = stacked.reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName="class"),
            geometry=territory_fc,
            scale=30,
            bestEffort=True,
            maxPixels=1e13,
        )
        result = stats.getInfo()
        groups = result.get("groups", [])

        # Total territory pixel area (for computing unburned class 0)
        total = area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=territory_fc,
            scale=30,
            bestEffort=True,
            maxPixels=1e13,
        )
        total_sqm = total.getInfo().get("area", 0)

        records = []
        sum_other_sqm = 0.0
        for g in groups:
            cls_val = int(g.get("group", g.get("class", 0)))
            area_sqm = float(g.get("sum", 0))
            if area_sqm > 0 and cls_val > 0:
                records.append({
                    "class_value": cls_val,
                    "area_ha": round(area_sqm / 10000, 4),
                })
                sum_other_sqm += area_sqm

        # Add class 0 (unburned / no-data) as remainder
        zero_sqm = total_sqm - sum_other_sqm
        if zero_sqm > 0:
            records.insert(0, {
                "class_value": 0,
                "area_ha": round(zero_sqm / 10000, 4),
            })

        records.sort(key=lambda r: r["class_value"])
        return records

    def _export_to_gcs(
        self, img: ee.Image, territory_fc: ee.FeatureCollection,
        product_id: str, territory_id: str, year_str: str,
        dataset_id: str, bucket_name: str
    ) -> ee.batch.Task:
        area_img = ee.Image.pixelArea()
        stacked = area_img.addBands(img.select(0))

        stats = stacked.reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName="class"),
            geometry=territory_fc,
            scale=30,
            bestEffort=True,
            maxPixels=1e13,
        )

        total = area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=territory_fc,
            scale=30,
            bestEffort=True,
            maxPixels=1e13,
        )

        groups = ee.List(stats.get("groups"))

        def to_feature(g):
            d = ee.Dictionary(g)
            cls_val = ee.Number(d.get("group")).toInt()
            area_sqm = ee.Number(d.get("sum"))
            area_ha = area_sqm.divide(10000)
            return ee.Feature(None, {
                "class_value": cls_val,
                "area_ha": area_ha,
                "year": year_str,
                "dataset": dataset_id,
                "product": product_id,
                "territory_id": territory_id,
            })

        fc = ee.FeatureCollection(groups.map(to_feature))
        total_sqm = ee.Number(total.get("area"))
        sum_other = fc.aggregate_sum("area_ha").multiply(10000)
        zero_sqm = total_sqm.subtract(sum_other)
        zero_feat = ee.Feature(None, {
            "class_value": 0,
            "area_ha": zero_sqm.divide(10000),
            "year": year_str,
            "dataset": dataset_id,
            "product": product_id,
            "territory_id": territory_id,
        })
        all_fc = fc.merge(ee.FeatureCollection([zero_feat]))

        prefix = f"area_stats/{dataset_id}/{product_id}/{territory_id}"
        filename = f"{prefix}/{year_str}.csv"

        task = ee.batch.Export.table.toCloudStorage(
            collection=all_fc,
            description=f"area_stats_{product_id}_{territory_id}_{year_str}",
            bucket=bucket_name,
            fileNamePrefix=filename,
            fileFormat="CSV",
        )
        task.start()
        return task

    def _download_from_gcs(self, gcs_path: str, local_path: str):
        from google.cloud import storage
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        client = storage.Client()
        parts = gcs_path.split("/", 1)
        bucket_name = parts[0]
        blob_path = parts[1] if len(parts) > 1 else ""
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.download_to_filename(local_path)

    def _check_ee_task(self, product_id: str, territory_id: str, year: str) -> str:
        prefix = f"area_stats_{product_id}_{territory_id}_{year}"
        try:
            root = ee.data.getAssetRoots()[0]["id"].replace("projects/", "")
            tasks = ee.data.listOperations(root)
            for t in (tasks or []):
                meta = t.get("metadata", {})
                if meta.get("description") == prefix:
                    return meta.get("state", "UNKNOWN")
        except Exception:
            pass
        return "NOT_FOUND"

    def _wait_for_task(
        self, product_id: str, territory_id: str, year: str, timeout: int = 3600
    ) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self._check_ee_task(product_id, territory_id, year)
            if status == "COMPLETED":
                return True
            elif status in ("FAILED", "CANCELLED"):
                return False
            time.sleep(30)
        return False

    def wait_all_tasks(self, output_dir: str, poll_interval: int = 30) -> Dict[str, str]:
        tasks = self._load_tasks(output_dir)
        if not tasks:
            return {}

        results = {t["year"]: t.get("state", "UNKNOWN") for t in tasks}
        pending = [t for t in tasks if t.get("state") in ("STARTED", "RUNNING")]
        if not pending:
            return results

        print(f"  Monitoring {len(pending)} tasks...")
        while pending:
            for t in list(pending):
                state = self._check_ee_task(
                    t["product"], t["territory"], t["year"]
                )
                if state in ("COMPLETED", "FAILED", "CANCELLED"):
                    t["state"] = state
                    results[t["year"]] = state
                    pending.remove(t)
                    print(f"    [{t['year']}] {state}")
            if pending:
                time.sleep(poll_interval)

        self._save_tasks(output_dir, tasks)
        return results
