"""
Baixa metadata JSONs do GCS, gera CSVs do Looker Studio, sobe de volta ao GCS.

Fluxo:
  1. Lista metadata_*.json no GCS para o(s) dataset(s)
  2. Download -> pasta temp local
  3. Gera CSVs:
     - Raiz: 3 arquivos flat combinando TODOS os datasets (Looker Studio le estes)
     - Subpastas: raw/, pivot_territorios/, pivot_produtos/ (versoes por dataset)
  4. Upload para gs://.../gif-factory/looker studio/
  5. Limpa pasta temp

Uso:
  python scripts/build_looker_csvs_from_gcs.py --all                        # todos datasets
  python scripts/build_looker_csvs_from_gcs.py --dataset brasil_fire_col5   # um dataset
  python scripts/build_looker_csvs_from_gcs.py --all --no-upload            # sem GCS
"""

import os
import sys
import json
import shutil
import tempfile
import warnings
from pathlib import Path
from collections import OrderedDict

import csv as _csvmod
import yaml

# GCS Config
BUCKET_NAME = "mapbiomas-fire"
PROJECT_ID = "mapbiomas-fire-485203"
GCS_ROOT = "gif-factory"
GCS_BASE_URL = "https://storage.googleapis.com/mapbiomas-fire/gif-factory"
LOCAL_CSV_ROOT = "outputs/looker_studio"

warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")


def get_gcs_client():
    from google.cloud import storage
    return storage.Client(project=PROJECT_ID)


def list_metadata_files(dataset_id):
    """Lista todos os metadata_*.json no GCS para um dataset."""
    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    prefix = f"{GCS_ROOT}/{dataset_id}/"
    return [b for b in bucket.list_blobs(prefix=prefix)
            if b.name.endswith(".json") and "metadata_" in b.name]


def download_metadata_files(blobs, dest_dir):
    """Download dos metadata JSONs para um diretorio local."""
    bucket = get_gcs_client().bucket(BUCKET_NAME)
    count = 0
    for b in blobs:
        rel = b.name[len(f"{GCS_ROOT}/"):]
        local_path = Path(dest_dir) / rel
        local_path.parent.mkdir(parents=True, exist_ok=True)
        bucket.blob(b.name).download_to_filename(str(local_path))
        count += 1
    return count


def load_dataset_metadata(dataset_ids=None):
    """Baixa metadata de todos (ou alguns) datasets do GCS e retorna linhas CSV."""
    if dataset_ids is None:
        # Descobre todos os datasets no GCS
        client = get_gcs_client()
        bucket = client.bucket(BUCKET_NAME)
        prefixes = set()
        for b in bucket.list_blobs(prefix=f"{GCS_ROOT}/"):
            parts = b.name.split("/")
            if len(parts) >= 3 and parts[0] == GCS_ROOT:
                prefixes.add(parts[1])
        dataset_ids = sorted(p for p in prefixes if p and not p.startswith(".") and p not in ("looker studio", "outputs"))

    all_rows = []
    temp_dirs = []

    for ds_id in dataset_ids:
        blobs = list_metadata_files(ds_id)
        if not blobs:
            print(f"  {ds_id}: 0 metadata (pulando)")
            continue

        temp_dir = tempfile.mkdtemp(prefix=f"gif_looker_{ds_id}_")
        temp_dirs.append(temp_dir)
        count = download_metadata_files(blobs, temp_dir)
        print(f"  {ds_id}: {count} metadata JSONs baixados")

        rows = parse_metadata_dir(ds_id, temp_dir)
        all_rows.extend(rows)

    return all_rows, temp_dirs


def parse_metadata_dir(dataset_id, base_dir):
    """Le metadata JSONs de um diretorio e retorna linhas CSV."""
    # Territory type detection
    def load_ids(yaml_file, key):
        if not os.path.exists(yaml_file):
            return set()
        with open(yaml_file, encoding="utf-8") as f:
            return set(yaml.safe_load(f)["territories"].get(key, {}).keys())

    biome_ids = load_ids("config/territories_biomes.yaml", "biomes")
    custom_ids = load_ids("config/territories_custom.yaml", "custom_regions")
    state_ids = load_ids("config/territories_states.yaml", "ufs")
    country_ids = load_ids("config/territories_countries.yaml", "countries")

    def get_type(tid):
        if tid in biome_ids: return "biome"
        if tid in custom_ids: return "custom_region"
        if tid in state_ids: return "state"
        if tid in country_ids: return "country"
        return "unknown"

    # Dataset collection from config
    collection = "?"
    try:
        with open("config/datasets.yaml", encoding="utf-8") as f:
            datasets = yaml.safe_load(f).get("datasets", {})
            ds = datasets.get(dataset_id, {})
            collection = str(ds.get("collection", "?"))
    except Exception:
        pass

    base_path = os.path.join(base_dir, dataset_id)
    rows = []

    if not os.path.isdir(base_path):
        return rows

    for prod_id in sorted(os.listdir(base_path)):
        pp = os.path.join(base_path, prod_id)
        if not os.path.isdir(pp):
            continue
        for terr_id in sorted(os.listdir(pp)):
            meta = None
            meta_dir = os.path.join(pp, terr_id)
            if not os.path.isdir(meta_dir):
                continue
            for fn in os.listdir(meta_dir):
                if fn.startswith("metadata_") and fn.endswith(".json"):
                    with open(os.path.join(meta_dir, fn), encoding="utf-8") as f:
                        meta = json.load(f)
                    break
            if not meta:
                continue

            prod_name = meta["product"]["name"]
            terr_name = meta["territory"]["name"]
            trange = meta["product"].get("temporal_range", [1985, 2024])
            fcount = meta.get("output", {}).get("frames_count", 0)
            gen_at = meta.get("generated_at", "")
            fi = meta.get("files", {})
            timing = meta.get("timing", {})
            phases = timing.get("phases", {})
            ttotal = timing.get("total_seconds", 0)
            ee = meta.get("ee_estimate", {})
            dim = ee.get("frame_dimensions", {})
            dim_str = f"{dim.get('width', 0)}x{dim.get('height', 0)}"
            tpx = ee.get("total_pixels_processed", 0)
            gif_fn = f"{prod_id}_{terr_id}_0_3s.gif"
            url = f"{GCS_BASE_URL}/{dataset_id}/{prod_id}/{terr_id}/{gif_fn}"

            rows.append(OrderedDict([
                ("link_direto", url),
                ("dataset", dataset_id),
                ("colecao", collection),
                ("produto_id", prod_id),
                ("nome_produto", prod_name),
                ("territorio_id", terr_id),
                ("nome_territorio", terr_name),
                ("tipo_territorio", get_type(terr_id)),
                ("tipo_arquivo", "GIF animado"),
                ("arquivo", gif_fn),
                ("data_geracao", gen_at[:10] if gen_at else ""),
                ("bandas", fcount),
                ("ano_inicial", trange[0]),
                ("ano_final", trange[1]),
                ("gif_tamanho_mb", fi.get("gif_size_mb", "")),
                ("frames_total_mb", fi.get("frames_total_mb", "")),
                ("frames_count", fi.get("frames_count", fcount)),
                ("tempo_total_s", round(ttotal, 1) if ttotal else ""),
                ("tempo_download_s", round(phases.get("download", 0), 1) or ""),
                ("tempo_resize_s", round(phases.get("resize", 0), 1) or ""),
                ("tempo_colagem_s", round(phases.get("collage_build", 0), 1) or ""),
                ("tempo_gif_s", round(phases.get("gif_creation", 0), 1) or ""),
                ("ee_cu", ee.get("estimated_eecu", "")),
                ("pixels_por_frame", ee.get("pixels_per_frame", "")),
                ("total_pixels_m", round(tpx / 1_000_000, 1) if tpx else ""),
                ("dimensao_frame", dim_str),
            ]))
    return rows


def pivot_territorios(data, vc="link_direto"):
    prods = sorted(set(r["produto_id"] for r in data))
    terrs = sorted(set(r["territorio_id"] for r in data))
    fn = ["territorio_id", "nome_territorio", "tipo_territorio"] + prods
    out = []
    for tid in terrs:
        sub = [r for r in data if r["territorio_id"] == tid]
        if not sub: continue
        row = OrderedDict()
        row["territorio_id"] = tid
        row["nome_territorio"] = sub[0]["nome_territorio"]
        row["tipo_territorio"] = sub[0]["tipo_territorio"]
        for p in prods:
            match = [r for r in sub if r["produto_id"] == p]
            row[p] = match[0][vc] if match else ""
        out.append(row)
    return fn, out


def pivot_produtos(data, vc="link_direto"):
    terrs = sorted(set(r["territorio_id"] for r in data))
    prods = sorted(set(r["produto_id"] for r in data))
    fn = ["produto_id", "nome_produto"] + terrs
    out = []
    for pid in prods:
        sub = [r for r in data if r["produto_id"] == pid]
        if not sub: continue
        row = OrderedDict()
        row["produto_id"] = pid
        row["nome_produto"] = sub[0]["nome_produto"]
        for t in terrs:
            match = [r for r in sub if r["territorio_id"] == t]
            row[t] = match[0][vc] if match else ""
        out.append(row)
    return fn, out


def write_csv(path, fieldnames, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = _csvmod.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(data)


def generate_all_csvs(all_rows, full_dataset_ids):
    """Gera todos os CSVs: raiz combinada + subpastas por dataset."""
    FIELDS = list(all_rows[0].keys()) if all_rows else []

    ROOT = LOCAL_CSV_ROOT
    # Limpa CSVs anteriores
    for csv_path in Path(ROOT).rglob("*.csv"):
        try: csv_path.unlink()
        except Exception: pass
    for d in ["raw", "pivot_territorios", "pivot_produtos"]:
        Path(ROOT, d).mkdir(parents=True, exist_ok=True)

    # --- RAIZ: 3 arquivos flat (TODOS os datasets combinados) ---
    if all_rows:
        write_csv(f"{ROOT}/gif_index.csv", FIELDS, all_rows)
        flds_pt, data_pt = pivot_territorios(all_rows)
        write_csv(f"{ROOT}/gif_index_pivot_territorios.csv", flds_pt, data_pt)
        flds_pp, data_pp = pivot_produtos(all_rows)
        write_csv(f"{ROOT}/gif_index_pivot_produtos.csv", flds_pp, data_pp)
        print(f"  Raiz: 3 arquivos combinados ({len(all_rows)} linhas)")

    # --- SUBPASTAS: versoes por dataset / bioma / regiao ---
    for ds_id in full_dataset_ids:
        ds_rows = [r for r in all_rows if r["dataset"] == ds_id]
        if not ds_rows:
            continue
        for suffix, data in [
            ("", ds_rows),
            ("_biomes", [r for r in ds_rows if r["tipo_territorio"] == "biome"]),
            ("_custom_regions", [r for r in ds_rows if r["tipo_territorio"] == "custom_region"]),
            ("_states", [r for r in ds_rows if r["tipo_territorio"] == "state"]),
            ("_countries", [r for r in ds_rows if r["tipo_territorio"] == "country"]),
            (f"_{ds_id}", ds_rows),
        ]:
            write_csv(f"{ROOT}/raw/gif_index{suffix}.csv", FIELDS, data)
            flds_pt, data_pt = pivot_territorios(data)
            write_csv(f"{ROOT}/pivot_territorios/gif_index{suffix}.csv", flds_pt, data_pt)
            flds_pp, data_pp = pivot_produtos(data)
            write_csv(f"{ROOT}/pivot_produtos/gif_index{suffix}.csv", flds_pp, data_pp)


def upload_csvs_to_gcs():
    """Sobe todos os CSVs gerados para o GCS."""
    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    csv_root = Path(LOCAL_CSV_ROOT)
    if not csv_root.exists():
        return 0
    count = 0
    for fpath in csv_root.rglob("*.csv"):
        rel = fpath.relative_to(csv_root).as_posix()
        remote = f"{GCS_ROOT}/looker studio/{rel}"
        bucket.blob(remote).upload_from_filename(str(fpath))
        count += 1
    return count


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Looker Studio CSV builder from GCS")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Todos os datasets")
    group.add_argument("--dataset", type=str, help="Dataset especifico")
    parser.add_argument("--no-upload", action="store_true", help="Nao subir para GCS")
    args = parser.parse_args()

    skip_upload = args.no_upload

    print(f"\n{'=' * 60}")
    print(f"LOOKER STUDIO CSV — FROM GCS")
    print(f"{'=' * 60}")

    # Step 1: Download metadata
    print("[1/3] Baixando metadata do GCS...")
    if args.all:
        all_rows, temp_dirs = load_dataset_metadata()
    else:
        all_rows, temp_dirs = load_dataset_metadata(dataset_ids=[args.dataset])

    if not all_rows:
        print("  Nenhum metadata encontrado. Abortando.")
        return

    # Step 2: Generate CSVs
    print(f"\n[2/3] Gerando CSVs ({len(all_rows)} linhas)...")
    dataset_ids = sorted(set(r["dataset"] for r in all_rows))
    generate_all_csvs(all_rows, dataset_ids)

    # Step 3: Upload to GCS
    if not skip_upload:
        print(f"\n[3/3] Subindo CSVs para o GCS...")
        csv_count = upload_csvs_to_gcs()
        print(f"  {csv_count} CSVs enviados para gs://{BUCKET_NAME}/{GCS_ROOT}/looker studio/")
    else:
        print(f"\n[3/3] Upload skipado (--no-upload)")

    # Cleanup temp dirs
    for td in temp_dirs:
        shutil.rmtree(td, ignore_errors=True)

    print(f"\n{'=' * 60}")
    print(f"CONCLUIDO")
    print(f"{'=' * 60}")
    print(f"CSVs locais: {LOCAL_CSV_ROOT}/")
    if not skip_upload:
        print(f"GCS: gs://{BUCKET_NAME}/{GCS_ROOT}/looker studio/")
        print(f"Looker Studio: https://datastudio.google.com/u/0/reporting/179f6b47-8f6e-4f51-abd5-75b7ae018a2b/page/XDzxF")


if __name__ == "__main__":
    main()
