"""
Baixa metadata JSONs do GCS, gera CSVs do Looker Studio, sobe de volta ao GCS.

Fluxo:
  1. Lista metadata_*.json no GCS para o dataset
  2. Download → pasta temp local
  3. Gera CSVs em outputs/looker_studio/
  4. Upload dos CSVs para gs://.../gif-factory/looker_studio/
  5. Limpa pasta temp

Uso:
  python scripts/build_looker_csvs_from_gcs.py brasil_fire_col5
  python scripts/build_looker_csvs_from_gcs.py brasil_degradation_col10_1
  python scripts/build_looker_csvs_from_gcs.py brasil_fire_col5 --no-upload
"""

import os
import sys
import json
import shutil
import tempfile
import warnings
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import csv as _csvmod
from collections import OrderedDict
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
    blobs = list(bucket.list_blobs(prefix=prefix))
    return [b for b in blobs if b.name.endswith(".json") and "metadata_" in b.name]


def download_metadata_files(blobs, dest_dir):
    """Download dos metadata JSONs para um diretorio local."""
    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    count = 0
    for b in blobs:
        rel = b.name[len(f"{GCS_ROOT}/"):]
        local_path = Path(dest_dir) / rel
        local_path.parent.mkdir(parents=True, exist_ok=True)
        bucket.blob(b.name).download_to_filename(str(local_path))
        count += 1
    return count


def generate_csvs(dataset_id, metadata_dir):
    """Gera CSVs do Looker Studio a partir dos metadata JSONs baixados."""
    # Reproduz a logica do build_looker_csvs.py com diretorio customizado
    BASE = str(Path(metadata_dir) / dataset_id)

    # Territory type detection
    def load_territory_ids(yaml_file, key):
        if not os.path.exists(yaml_file):
            return set()
        with open(yaml_file, encoding="utf-8") as f:
            return set(yaml.safe_load(f)["territories"].get(key, {}).keys())

    biome_ids = load_territory_ids("config/territories_biomes.yaml", "biomes")
    custom_ids = load_territory_ids("config/territories_custom.yaml", "custom_regions")
    state_ids = load_territory_ids("config/territories_states.yaml", "ufs")
    country_ids = load_territory_ids("config/territories_countries.yaml", "countries")

    def get_type(tid):
        if tid in biome_ids: return "biome"
        if tid in custom_ids: return "custom_region"
        if tid in state_ids: return "state"
        if tid in country_ids: return "country"
        return "unknown"

    def load_metadata(prod_id, terr_id):
        path = os.path.join(BASE, prod_id, terr_id)
        if not os.path.isdir(path):
            return None
        for fn in os.listdir(path):
            if fn.startswith("metadata_") and fn.endswith(".json"):
                with open(os.path.join(path, fn), encoding="utf-8") as f:
                    return json.load(f)
        return None

    FIELDS = [
        "link_direto", "dataset", "colecao",
        "produto_id", "nome_produto",
        "territorio_id", "nome_territorio", "tipo_territorio",
        "tipo_arquivo", "arquivo",
        "data_geracao",
        "bandas", "ano_inicial", "ano_final",
        "gif_tamanho_mb", "frames_total_mb", "frames_count",
        "tempo_total_s", "tempo_download_s", "tempo_resize_s",
        "tempo_colagem_s", "tempo_gif_s",
        "ee_cu", "pixels_por_frame", "total_pixels_m", "dimensao_frame",
    ]

    rows = []
    if not os.path.isdir(BASE):
        print(f"  Nenhum metadata encontrado em {BASE}")
        return 0

    for prod_id in sorted(os.listdir(BASE)):
        pp = os.path.join(BASE, prod_id)
        if not os.path.isdir(pp):
            continue
        for terr_id in sorted(os.listdir(pp)):
            meta = load_metadata(prod_id, terr_id)
            if not meta:
                continue
            prod_name = meta["product"]["name"]
            terr_name = meta["territory"]["name"]
            trange = meta["product"].get("temporal_range", [1985, 2024])
            fcount = meta["output"].get("frames_count", 0)
            gen_at = meta.get("generated_at", "")
            fi = meta.get("files", {})
            timing = meta.get("timing", {}).get("phases", {})
            ttotal = meta.get("timing", {}).get("total_seconds", 0)
            ee = meta.get("ee_estimate", {})
            dim = ee.get("frame_dimensions", {})
            dim_str = f"{dim.get('width', 0)}x{dim.get('height', 0)}"
            tpx = ee.get("total_pixels_processed", 0)
            gif_fn = f"{prod_id}_{terr_id}_0_3s.gif"
            url = f"{GCS_BASE_URL}/{dataset_id}/{prod_id}/{terr_id}/{gif_fn}"
            rows.append(OrderedDict([
                ("link_direto", url),
                ("dataset", dataset_id),
                ("colecao", str(meta["product"].get("collection", ""))),
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
                ("tempo_download_s", round(timing.get("download", 0), 1) or ""),
                ("tempo_resize_s", round(timing.get("resize", 0), 1) or ""),
                ("tempo_colagem_s", round(timing.get("collage_build", 0), 1) or ""),
                ("tempo_gif_s", round(timing.get("gif_creation", 0), 1) or ""),
                ("ee_cu", ee.get("estimated_eecu", "")),
                ("pixels_por_frame", ee.get("pixels_per_frame", "")),
                ("total_pixels_m", round(tpx / 1_000_000, 1) if tpx else ""),
                ("dimensao_frame", dim_str),
            ]))

    print(f"  Total rows: {len(rows)}")

    def write_csv(path, fieldnames, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = _csvmod.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(data)

    def pivot_territorios(data, vc="link_direto"):
        prods = sorted(set(r["produto_id"] for r in data))
        terrs = sorted(set(r["territorio_id"] for r in data))
        fn = ["territorio_id", "nome_territorio", "tipo_territorio"] + prods
        out = []
        for tid in terrs:
            sub = [r for r in data if r["territorio_id"] == tid]
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
            row = OrderedDict()
            row["produto_id"] = pid
            row["nome_produto"] = sub[0]["nome_produto"]
            for t in terrs:
                match = [r for r in sub if r["territorio_id"] == t]
                row[t] = match[0][vc] if match else ""
            out.append(row)
        return fn, out

    ROOT = LOCAL_CSV_ROOT
    for d in ["raw", "pivot_territorios", "pivot_produtos"]:
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            try:
                shutil.rmtree(p)
            except PermissionError:
                for f in Path(p).rglob("*"):
                    try:
                        f.unlink()
                    except Exception:
                        pass

    for suffix, data in [
        ("", rows),
        ("_biomes", [r for r in rows if r["tipo_territorio"] == "biome"]),
        ("_custom_regions", [r for r in rows if r["tipo_territorio"] == "custom_region"]),
        ("_states", [r for r in rows if r["tipo_territorio"] == "state"]),
        ("_countries", [r for r in rows if r["tipo_territorio"] == "country"]),
        (f"_{dataset_id}", rows),
    ]:
        write_csv(f"{ROOT}/raw/gif_index{suffix}.csv", FIELDS, data)
        flds_pt, data_pt = pivot_territorios(data)
        write_csv(f"{ROOT}/pivot_territorios/gif_index{suffix}.csv", flds_pt, data_pt)
        flds_pp, data_pp = pivot_produtos(data)
        write_csv(f"{ROOT}/pivot_produtos/gif_index{suffix}.csv", flds_pp, data_pp)

    # Cleanup flat files
    for fn in os.listdir(ROOT):
        fp = os.path.join(ROOT, fn)
        if os.path.isfile(fp) and fn.endswith(".csv"):
            os.remove(fp)

    return len(rows)


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
        remote = f"{GCS_ROOT}/{csv_root.name}/{rel}"
        bucket.blob(remote).upload_from_filename(str(fpath))
        count += 1

    return count


def main():
    if len(sys.argv) < 2:
        print("Uso: python build_looker_csvs_from_gcs.py <dataset_id> [--no-upload]")
        print("Ex:  python build_looker_csvs_from_gcs.py brasil_fire_col5")
        sys.exit(1)

    dataset_id = sys.argv[1]
    skip_upload = "--no-upload" in sys.argv

    print(f"\n{'=' * 60}")
    print(f"LOOKER STUDIO CSV — FROM GCS")
    print(f"{'=' * 60}")
    print(f"Dataset: {dataset_id}")
    print(f"Upload GCS: {'Sim' if not skip_upload else 'Nao'}")
    print()

    # 1. List GCS
    print("[1/4] Listando metadata no GCS...")
    blobs = list_metadata_files(dataset_id)
    print(f"  Encontrados: {len(blobs)} metadata JSONs")

    if not blobs:
        print("  Nenhum metadata encontrado. Abortando.")
        return

    # 2. Download
    print("[2/4] Baixando metadata...")
    temp_dir = tempfile.mkdtemp(prefix="gif_factory_looker_")
    count = download_metadata_files(blobs, temp_dir)
    print(f"  Baixados: {count} arquivos -> {temp_dir}")

    # 3. Generate CSVs
    print("[3/4] Gerando CSVs...")
    rows = generate_csvs(dataset_id, temp_dir)
    print(f"  {rows} linhas processadas")

    # 4. Upload CSVs to GCS
    if not skip_upload and rows > 0:
        print("[4/4] Subindo CSVs para o GCS...")
        csv_count = upload_csvs_to_gcs()
        print(f"  {csv_count} CSVs enviados para gs://{BUCKET_NAME}/{GCS_ROOT}/{LOCAL_CSV_ROOT}/")
    else:
        print("[4/4] Upload skipado (--no-upload)")

    # Cleanup temp
    shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\n{'=' * 60}")
    print(f"CONCLUIDO")
    print(f"{'=' * 60}")
    print(f"CSVs locais: {LOCAL_CSV_ROOT}/")
    if not skip_upload:
        print(f"GCS: gs://{BUCKET_NAME}/{GCS_ROOT}/{LOCAL_CSV_ROOT}/")
        print(f"Looker Studio: https://datastudio.google.com/u/0/reporting/179f6b47-8f6e-4f51-abd5-75b7ae018a2b/page/XDzxF")


if __name__ == "__main__":
    main()
