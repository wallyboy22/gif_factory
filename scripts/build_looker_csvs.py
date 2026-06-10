#!/usr/bin/env python3
"""Merge per-product CSVs from pipeline and generate Looker Studio CSVs."""
import os, csv, sys
from collections import OrderedDict
from pathlib import Path

DS_IDS = [
    "brasil_degradation_col10_1",
    "brasil_fire_col5",
]
OUTPUT_BASE = "outputs/v002"
ROOT = "outputs/looker_studio"
GCS_BASE = "https://storage.googleapis.com/mapbiomas-fire/data-container"

FIELDS = [
    "link_direto", "dataset", "colecao",
    "produto_id", "nome_produto",
    "territorio_id", "nome_territorio", "tipo_territorio",
    "tipo_arquivo", "arquivo", "ano",
    "data_geracao",
    "bandas", "ano_inicial", "ano_final",
    "gif_tamanho_mb", "frames_total_mb", "frames_count",
    "tempo_total_s", "tempo_download_s", "tempo_resize_s",
    "tempo_colagem_s", "tempo_gif_s",
    "ee_cu", "pixels_por_frame", "total_pixels_m", "dimensao_frame",
]

def merge_csvs():
    rows = []
    csv_dir = Path(OUTPUT_BASE)
    for fpath in sorted(csv_dir.rglob("metadata/csv/product.csv")):
        ds = fpath.relative_to(OUTPUT_BASE).parts[0]
        prod = fpath.relative_to(OUTPUT_BASE).parts[1]
        terr = fpath.relative_to(OUTPUT_BASE).parts[2]
        seen = set()
        with open(fpath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                key = (r["tipo_arquivo"], r.get("ano", ""))
                if key not in seen:
                    seen.add(key)
                    r["link_direto"] = f"{GCS_BASE}/{ds}/{prod}/{terr}/{r['arquivo']}"
                    r.setdefault("dataset", ds)
                    rows.append(OrderedDict((k, r.get(k, "")) for k in FIELDS))
    return rows

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

def main():
    for csv_path in Path(ROOT).rglob("*.csv"):
        try: csv_path.unlink()
        except Exception: pass
    for d in ["raw", "pivot_territorios", "pivot_produtos"]:
        Path(ROOT, d).mkdir(parents=True, exist_ok=True)

    rows = merge_csvs()
    print(f"Merged: {len(rows)} rows")

    write_csv(f"{ROOT}/gif_index.csv", FIELDS, rows)
    flds_pt, data_pt = pivot_territorios(rows)
    write_csv(f"{ROOT}/gif_index_pivot_territorios.csv", flds_pt, data_pt)
    flds_pp, data_pp = pivot_produtos(rows)
    write_csv(f"{ROOT}/gif_index_pivot_produtos.csv", flds_pp, data_pp)

    for suffix, data in [
        ("", rows),
        ("_biomes", [r for r in rows if r["tipo_territorio"] == "biome"]),
        ("_custom_regions", [r for r in rows if r["tipo_territorio"] == "custom_region"]),
    ]:
        if suffix:
            write_csv(f"{ROOT}/raw/gif_index{suffix}.csv", FIELDS, data)
        flds_pt2, data_pt2 = pivot_territorios(data)
        write_csv(f"{ROOT}/pivot_territorios/gif_index{suffix}.csv", flds_pt2, data_pt2)
        flds_pp2, data_pp2 = pivot_produtos(data)
        write_csv(f"{ROOT}/pivot_produtos/gif_index{suffix}.csv", flds_pp2, data_pp2)

    print("\nStructure:")
    for d in ["raw", "pivot_territorios", "pivot_produtos"]:
        p = os.path.join(ROOT, d)
        print(f"\n{d}/")
        for fn in sorted(os.listdir(p)):
            print(f"  {fn}")

if __name__ == "__main__":
    main()
