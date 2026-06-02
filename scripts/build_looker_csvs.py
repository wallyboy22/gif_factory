import os, csv, json, yaml, shutil
from collections import OrderedDict
from pathlib import Path

# ── config ───────────────────────────────────────────
DS_ID = os.environ.get("GIF_FACTORY_DS_ID", "brasil_degradation_col10_1")
GCS_BASE = "https://storage.googleapis.com/mapbiomas-fire/gif-factory"

with open("config/territories_biomes.yaml", encoding="utf-8") as f:
    biome_ids = set(yaml.safe_load(f)["territories"]["biomes"].keys())
with open("config/territories_custom.yaml", encoding="utf-8") as f:
    custom_ids = set(yaml.safe_load(f)["territories"]["custom_regions"].keys())
with open("config/territories_states.yaml", encoding="utf-8") as f:
    state_ids = set(yaml.safe_load(f)["territories"]["ufs"].keys())
with open("config/territories_countries.yaml", encoding="utf-8") as f:
    country_ids = set(yaml.safe_load(f)["territories"]["countries"].keys())

def get_type(tid):
    if tid in biome_ids: return "biome"
    if tid in custom_ids: return "custom_region"
    if tid in state_ids: return "state"
    if tid in country_ids: return "country"
    return "unknown"

# ── read all metadata ────────────────────────────────
BASE = f"outputs/v001/{DS_ID}"

def load_metadata(prod_id, terr_id):
    path = os.path.join(BASE, prod_id, terr_id)
    if not os.path.isdir(path): return None
    for fn in os.listdir(path):
        if fn.startswith("metadata_") and fn.endswith(".json"):
            with open(os.path.join(path, fn), encoding="utf-8") as f:
                return json.load(f)
    return None

FIELDS = [
    "link_direto","dataset","colecao",
    "produto_id","nome_produto",
    "territorio_id","nome_territorio","tipo_territorio",
    "tipo_arquivo","arquivo",
    "data_geracao",
    "bandas","ano_inicial","ano_final",
    "gif_tamanho_mb","frames_total_mb","frames_count",
    "tempo_total_s","tempo_download_s","tempo_resize_s",
    "tempo_colagem_s","tempo_gif_s",
    "ee_cu","pixels_por_frame","total_pixels_m","dimensao_frame",
]

rows = []
for prod_id in sorted(os.listdir(BASE)):
    pp = os.path.join(BASE, prod_id)
    if not os.path.isdir(pp): continue
    for terr_id in sorted(os.listdir(pp)):
        meta = load_metadata(prod_id, terr_id)
        if not meta: continue
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
        dim_str = f"{dim.get('width',0)}x{dim.get('height',0)}"
        tpx = ee.get("total_pixels_processed", 0)
        gif_fn = f"{prod_id}_{terr_id}_0_3s.gif"
        url = f"{GCS_BASE}/{DS_ID}/{prod_id}/{terr_id}/{gif_fn}"
        rows.append(OrderedDict([
            ("link_direto", url),
            ("dataset", DS_ID),
            ("colecao", "10.1"),
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
print(f"Total: {len(rows)} rows")

# ── CSV helpers ──────────────────────────────────────
def write_csv(path, fieldnames, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(data)

def pivot_territorios(data, vc="link_direto"):
    prods = sorted(set(r["produto_id"] for r in data))
    terrs = sorted(set(r["territorio_id"] for r in data))
    fn = ["territorio_id","nome_territorio","tipo_territorio"] + prods
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
    fn = ["produto_id","nome_produto"] + terrs
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

# ── generate flat root + subfolder structure ──────────
ROOT = "outputs/looker_studio"
for csv_path in Path(ROOT).rglob("*.csv"):
    try: csv_path.unlink()
    except Exception: pass
for d in ["raw", "pivot_territorios", "pivot_produtos"]:
    Path(ROOT, d).mkdir(parents=True, exist_ok=True)

# --- Root: 3 flat files (what Looker Studio reads) ---
write_csv(f"{ROOT}/gif_index.csv", FIELDS, rows)
flds_pt, data_pt = pivot_territorios(rows)
write_csv(f"{ROOT}/gif_index_pivot_territorios.csv", flds_pt, data_pt)
flds_pp, data_pp = pivot_produtos(rows)
write_csv(f"{ROOT}/gif_index_pivot_produtos.csv", flds_pp, data_pp)

# --- Subfolders: detailed versions ---
for suffix, data in [
    ("", rows),
    ("_biomes", [r for r in rows if r["tipo_territorio"] == "biome"]),
    ("_custom_regions", [r for r in rows if r["tipo_territorio"] == "custom_region"]),
    (f"_{DS_ID}", rows),
]:
    if suffix:
        write_csv(f"{ROOT}/raw/gif_index{suffix}.csv", FIELDS, data)
    flds_pt2, data_pt2 = pivot_territorios(data)
    write_csv(f"{ROOT}/pivot_territorios/gif_index{suffix}.csv", flds_pt2, data_pt2)
    flds_pp2, data_pp2 = pivot_produtos(data)
    write_csv(f"{ROOT}/pivot_produtos/gif_index{suffix}.csv", flds_pp2, data_pp2)

# show result
print("\nStructure:")
for d in ["raw", "pivot_territorios", "pivot_produtos"]:
    p = os.path.join(ROOT, d)
    print(f"\n{d}/")
    for fn in sorted(os.listdir(p)):
        print(f"  {fn}")
