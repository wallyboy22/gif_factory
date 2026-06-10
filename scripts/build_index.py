#!/usr/bin/env python3
"""
build_index.py - Varre output/ e gera index.json com metadados para o dashboard.

Uso:
    python scripts/build_index.py                        # gera index.json local
    python scripts/build_index.py --upload                # gera + sobe para GCS (prod)
    python scripts/build_index.py --upload --mode dev     # gera + sobe como dev
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ipam_gif_factory.config import ConfigLoader


def build_index(output_dir: str) -> dict:
    output_dir = Path(output_dir)
    entries = []

    for gif_path in sorted(output_dir.rglob("*.gif")):
        try:
            rel = gif_path.relative_to(output_dir)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) < 3:
            continue

        ds, prod, terr = parts[0], parts[1], parts[2]
        base_dir = output_dir / ds / prod / terr

        meta_path = base_dir / "metadata" / f"metadata_{prod}.json"
        metadata = {}
        if meta_path.exists():
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                metadata = {}

        collages = list((base_dir / "collages").glob("*collage*.png"))
        collage_rel = str(Path(ds) / prod / terr / "collages" / collages[0].name) if collages else None
        gif_rel = str(rel.as_posix())

        frames_count = metadata.get("output", {}).get("frames_count", 0)

        entry = {
            "dataset": ds,
            "product": prod,
            "territory": terr,
            "gif_rel": gif_rel,
            "collage_rel": collage_rel,
            "frames_count": frames_count,
            "product_name": metadata.get("product", {}).get("name", prod),
            "territory_name": metadata.get("territory", {}).get("name", terr),
            "duration_seconds": metadata.get("timing", {}).get("total_seconds", 0),
            "duration_formatted": metadata.get("timing", {}).get("total_formatted", ""),
            "eecu": metadata.get("ee_estimate", {}).get("estimated_eecu", 0),
            "gif_size_mb": metadata.get("files", {}).get("gif_size_mb", 0),
            "metadata": metadata,
        }
        entries.append(entry)

    datasets = sorted(set(e["dataset"] for e in entries))
    products = sorted(set(e["product"] for e in entries))
    territories = sorted(set(e["territory"] for e in entries))

    index = {
        "_meta": {
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_entries": len(entries),
            "datasets": datasets,
            "products": products,
            "territories": territories,
        },
        "entries": entries,
    }
    return index


def upload_to_gcs(index: dict, config, mode: str = "prod") -> str:
    from google.cloud import storage

    gcs_conf = config.paths.get("paths", {}).get("google_cloud_storage", {})
    bucket_name = gcs_conf.get("bucket", "mapbiomas-fire")
    hub_root = gcs_conf.get("hub_root", "gif-factory")
    project_id = gcs_conf.get("project_id", "mapbiomas-fire-485203")

    index["_meta"]["mode"] = mode
    blob_path = f"{hub_root}/dev/index.json" if mode == "dev" else f"{hub_root}/index.json"

    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        json.dumps(index, indent=2, ensure_ascii=False),
        content_type="application/json",
    )
    print(f"Uploaded: gs://{bucket_name}/{blob_path}")
    return f"gs://{bucket_name}/{blob_path}"


def main():
    parser = argparse.ArgumentParser(description="Build index.json for GIF Factory dashboard")
    parser.add_argument("--upload", action="store_true", help="Upload to GCS after building")
    parser.add_argument("--mode", choices=["prod", "dev"], default="prod", help="GCS mode prefix")
    args = parser.parse_args()

    config = ConfigLoader().load_all()
    output_dir = config.get_output_dir()

    print(f"Scanning: {output_dir}")
    index = build_index(output_dir)

    local_path = Path(output_dir) / "index.json"
    local_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    size_kb = local_path.stat().st_size / 1024
    print(f"Written: {local_path} ({size_kb:.1f} KB)")
    print(f"Entries: {index['_meta']['total_entries']}")
    print(f"Datasets: {len(index['_meta']['datasets'])}")
    print(f"Products: {len(index['_meta']['products'])}")
    print(f"Territories: {len(index['_meta']['territories'])}")

    if args.upload:
        try:
            upload_to_gcs(index, config, mode=args.mode)
        except Exception as e:
            print(f"Upload failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
