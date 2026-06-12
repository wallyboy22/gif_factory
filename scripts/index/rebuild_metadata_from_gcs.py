#!/usr/bin/env python3
"""
rebuild_metadata_from_gcs.py - Reconstrói metadata_*.json a partir dos blobs no GCS.

Os metadados originais (gerados pelo pipeline) foram perdidos porque o
upload_to_gcs.py os ignorava. Este script lê os arquivos que estão no GCS
e regera os JSONs localmente em outputs/v001/.

Uso:
    python scripts/rebuild_metadata_from_gcs.py --dataset brasil_fire_col5
    python scripts/rebuild_metadata_from_gcs.py --dataset brasil_degradation_col10_1
    python scripts/rebuild_metadata_from_gcs.py --all
    python scripts/rebuild_metadata_from_gcs.py --dataset brasil_fire_col5 --dry-run

Depois rode:
    python scripts/upload_to_gcs.py --reupload-missing-metadata
    python scripts/sync_fire_col5.py
"""
import json
import os
import re
import sys
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")

from google.cloud import storage

GCS_BUCKET = "mapbiomas-fire"
GCS_ROOT = "data-container"
GCS_PROJECT = "mapbiomas-fire-485203"
OUTPUT_DIR = "outputs/v001"

# Cache para configs
_datasets_config = None
_territories_config = None
_viz_config = None


def _load_datasets():
    global _datasets_config
    if _datasets_config is None:
        from mapbiomas_data.config import ConfigLoader
        loader = ConfigLoader()
        loader.load_all()
        _datasets_config = loader.datasets
    return _datasets_config


def _load_territories():
    global _territories_config
    if _territories_config is None:
        from mapbiomas_data.config import ConfigLoader
        loader = ConfigLoader()
        loader.load_all()
        _territories_config = loader.territories
    return _territories_config


def _load_visualizations():
    global _viz_config
    if _viz_config is None:
        from mapbiomas_data.config import ConfigLoader
        loader = ConfigLoader()
        loader.load_all()
        _viz_config = loader.visualizations
    return _viz_config


def _find_territory_name(territory_id: str) -> str:
    terr = _load_territories()
    for group_name, group in terr.items():
        if not isinstance(group, dict):
            continue
        # Unify nested groups (paraguay has departments/regions/full)
        if any(k in group for k in ("departments", "regions", "full")):
            for subgroup in group.values():
                if isinstance(subgroup, dict) and territory_id in subgroup:
                    return subgroup[territory_id].get("name", territory_id)
        elif territory_id in group:
            return group[territory_id].get("name", territory_id)
    return territory_id


def _get_product_info(dataset_id: str, product_id: str):
    ds = _load_datasets().get(dataset_id, {})
    prod = ds.get("products", {}).get(product_id, {})
    return prod


def _get_viz_params(viz_key: str):
    viz = _load_visualizations().get(viz_key, {})
    return viz


def _parse_frame_year(filename: str) -> str:
    years = re.findall(r"\d{4}", filename)
    return years[-1] if years else "?"


def rebuild_metadata_for_dataset(dataset_id: str, output_base: str, dry_run: bool = False):
    client = storage.Client(project=GCS_PROJECT)
    bucket = client.bucket(GCS_BUCKET)

    prefix = f"{GCS_ROOT}/{dataset_id}/"
    print(f"\nListando blobs em gs://{GCS_BUCKET}/{prefix}...")
    all_blobs = list(bucket.list_blobs(prefix=prefix))
    print(f"  Total de blobs: {len(all_blobs)}")

    if not all_blobs:
        print("  Nenhum blob encontrado. Verifique se o dataset existe no GCS.")
        return

    # Group by (product, territory)
    groups = defaultdict(list)
    for blob in all_blobs:
        rel = blob.name.replace(prefix, "")
        parts = rel.split("/")
        if len(parts) >= 3:
            prod, terr = parts[0], parts[1]
            groups[(prod, terr)].append(blob)

    print(f"  Combos (prod × terr) encontrados: {len(groups)}\n")

    ds_config = _load_datasets().get(dataset_id, {})
    collection = str(ds_config.get("collection", "?"))

    total = len(groups)
    for idx, ((prod_id, terr_id), blobs) in enumerate(sorted(groups.items()), 1):
        label = f"{dataset_id}/{prod_id}/{terr_id}"
        print(f"  [{idx}/{total}] {label}")

        if dry_run:
            print(f"     [DRY-RUN] metadata seria gerado")
            continue

        # Separate files by type
        gif_blob = None
        collage_blob = None
        frame_blobs = []

        for b in blobs:
            fname = b.name.split("/")[-1]
            if fname.endswith("_0_3s.gif"):
                gif_blob = b
            elif fname.endswith("_collage.png"):
                collage_blob = b
            elif fname.endswith(".png"):
                frame_blobs.append(b)
            # Ignore .json (metadata, index) and .gif that are not _0_3s (unlikely)

        frame_blobs.sort(key=lambda b: b.name)

        # Product info from YAML
        prod_info = _get_product_info(dataset_id, prod_id)
        prod_name = prod_info.get("name", prod_id)
        asset_id = prod_info.get("asset", "")
        temporal_range = prod_info.get("temporal_range", [1985, 2025])
        viz_key = prod_info.get("visualization", "")
        viz_params = _get_viz_params(viz_key)

        # Territory name
        terr_name = _find_territory_name(terr_id)

        # File sizes from blob metadata
        gif_size_mb = round(gif_blob.size / (1024 * 1024), 2) if gif_blob else None
        collage_size_mb = round(collage_blob.size / (1024 * 1024), 2) if collage_blob else None

        # Frame info
        frame_fnames = [b.name.split("/")[-1] for b in frame_blobs]
        frames_count = len(frame_fnames)
        frames_total_mb = 0.0
        frame_sizes = {}
        for b in frame_blobs:
            fname = b.name.split("/")[-1]
            mb = round(b.size / (1024 * 1024), 2)
            frame_sizes[fname] = mb
            frames_total_mb += mb
        frames_total_mb = round(frames_total_mb, 2)

        # Generated date = oldest file's creation time or current
        timestamps = [b.time_created for b in blobs if b.time_created]
        gen_at = min(timestamps).isoformat() if timestamps else datetime.now().isoformat()

        # Build metadata JSON
        metadata = {
            "metadata_version": "1.1",
            "generated_at": gen_at,
            "dataset": {
                "id": dataset_id,
                "description": ds_config.get("description", ""),
                "source": ds_config.get("source", ""),
            },
            "product": {
                "id": prod_id,
                "name": prod_name,
                "asset": asset_id,
                "asset_type": prod_info.get("asset_type", "image"),
                "bands": prod_info.get("bands", []),
                "bands_slice": prod_info.get("bands_slice"),
                "temporal_range": temporal_range,
            },
            "processor": {
                "name": prod_info.get("processor"),
                "description": None,
                "divide_by": None,
            },
            "visualization": {
                "key": viz_key,
                "name": viz_params.get("name", viz_key),
                "cmap_type": viz_params.get("cmap_type", "sequential"),
                "min": viz_params.get("min", 0),
                "max": viz_params.get("max", 1),
                "palette": viz_params.get("palette", []),
                "label": viz_params.get("label", ""),
                "unit": viz_params.get("unit", ""),
            },
            "territory": {
                "id": terr_id,
                "name": terr_name,
            },
            "output": {
                "gif_path": f"outputs/v001/{dataset_id}/{prod_id}/{terr_id}/{gif_blob.name.split('/')[-1]}" if gif_blob else None,
                "gif_relative_path": f"{prod_id}_{terr_id}_0_3s.gif",
                "frames_count": frames_count,
                "frames": frame_fnames,
                "frame_duration_ms": 300,
            },
            "files": {
                "gif_size_mb": gif_size_mb,
                "collage_size_mb": collage_size_mb,
                "frames_total_mb": frames_total_mb,
                "frames_count": frames_count,
                "frames_sizes_mb": frame_sizes,
            },
            "timing": {
                "phases": {},
                "total_seconds": 0,
                "total_formatted": "0s",
            },
        }

        # Guess frame dimensions from first frame blob metadata
        if frame_blobs:
            try:
                first_blob = frame_blobs[0]
                raw = bucket.blob(first_blob.name).download_as_string(start=0, end=32)
                if len(raw) >= 24:
                    import struct
                    w = struct.unpack(">I", raw[16:20])[0]
                    h = struct.unpack(">I", raw[20:24])[0]
                    pixels_per_frame = w * h
                    total_pixels = pixels_per_frame * frames_count
                    metadata["ee_estimate"] = {
                        "frame_dimensions": {"width": w, "height": h},
                        "pixels_per_frame": pixels_per_frame,
                        "total_pixels_processed": total_pixels,
                        "gee_thumbnail_requests": frames_count,
                    }
            except Exception:
                pass

        # Save to disk
        dest_dir = Path(output_base) / dataset_id / prod_id / terr_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        meta_filename = f"metadata_{prod_id}.json"
        meta_path = dest_dir / meta_filename
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"     -> {meta_path} ({len(frame_fnames)} frames, {gif_size_mb} MB GIF)" if gif_size_mb else
              f"     -> {meta_path} ({len(frame_fnames)} frames)")

    print(f"\n  Concluído: {total} metadados gerados em {output_base}/{dataset_id}/")


def rebuild_all_datasets(output_base: str, dry_run: bool = False):
    client = storage.Client(project=GCS_PROJECT)
    bucket = client.bucket(GCS_BUCKET)

    prefix = f"{GCS_ROOT}/"
    dataset_ids = set()
    for blob in bucket.list_blobs(prefix=prefix):
        parts = blob.name.replace(prefix, "").split("/")
        if len(parts) >= 1 and parts[0]:
            dataset_ids.add(parts[0])

    # Filter out non-dataset prefixes (like "looker studio", ".", etc.)
    dataset_ids = sorted(d for d in dataset_ids if d and not d.startswith(".") and d != "looker studio")

    print(f"Datasets encontrados no GCS: {len(dataset_ids)}")
    for ds_id in dataset_ids:
        rebuild_metadata_for_dataset(ds_id, output_base, dry_run)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Reconstroi metadata_*.json a partir dos blobs no GCS")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dataset", type=str, help="Dataset ID específico")
    group.add_argument("--all", action="store_true", help="Todos os datasets do GCS")
    parser.add_argument("--dry-run", action="store_true", help="Só mostrar o que seria gerado")
    args = parser.parse_args()

    output_base = Path(OUTPUT_DIR)
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"{'=' * 60}")
    print(f"RECONSTRUIR METADATA DO GCS")
    print(f"{'=' * 60}")

    if args.all:
        rebuild_all_datasets(output_base, args.dry_run)
    else:
        rebuild_metadata_for_dataset(args.dataset, output_base, args.dry_run)

    print(f"\nPronto! Agora rode:")
    print(f"  python scripts/upload_to_gcs.py --reupload-missing-metadata")
    print(f"  python scripts/sync_fire_col5.py")


if __name__ == "__main__":
    main()