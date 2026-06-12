"""
Batch: unprecedented_fire — Brasil + Biomas + Biomas individuais + Regiões (17 territórios).
Gera GIFs completos (todos os anos) com colagem, labels, escala e norte.

Uso:
    python scripts/run_unprecedented_fire.py                          # fresco
    python scripts/run_unprecedented_fire.py --workers 6 --resume     # retomando
    python scripts/run_unprecedented_fire.py --no-upload              # sem upload GCS
"""

import sys
import os
import subprocess
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
cwd = os.getcwd()
if not os.path.exists(os.path.join(cwd, 'src')):
    parent = os.path.dirname(cwd)
    while not os.path.exists(os.path.join(parent, 'src')) and parent != os.path.dirname(parent):
        parent = os.path.dirname(parent)
    if os.path.exists(os.path.join(parent, 'src')):
        os.chdir(parent)
import ee
try:
    ee.Initialize(project='mapbiomas-fire-485203')
except Exception:
    pass

DATASET_ID = "brasil_fire_col5"
PRODUCT = "unprecedented_fire"

TERRITORIES = [
    "pais_brasil",
    "biomas_todos",
    "bioma_amazonia",
    "bioma_caatinga",
    "bioma_cerrado",
    "bioma_mata_atlantica",
    "bioma_pampa",
    "bioma_pantanal",
    "regiao_matopiba_cerrado",
    "regiao_matopiba",
    "regiao_centro_oeste",
    "regiao_nordeste",
    "regiao_norte",
    "regiao_sudeste",
    "regiao_sul",
    "regiao_bap",
    "regiao_bap_planalto",
]

CREATE_COLLAGE = True
ADD_LABELS = True
VERTICAL_DIMENSION = 1560
CELL_HEIGHT = 300

print_lock = threading.Lock()
results_lock = threading.Lock()
results_list = []


def detect_workers():
    return 12


def process_one(config, territory, resume, upload, font_scale=1.0):
    from pathlib import Path
    from scripts.upload_to_gcs import upload_combo
    from src.mapbiomas_data.core.pipeline import Pipeline

    pipeline = Pipeline(config)

    with print_lock:
        print(f"\n[INICIANDO] {PRODUCT} / {territory}")

    result = pipeline.run(
        dataset_id=DATASET_ID,
        product_id=PRODUCT,
        territory_id=territory,
        create_collage=CREATE_COLLAGE,
        add_labels=ADD_LABELS,
        vertical_dimension=VERTICAL_DIMENSION,
        cell_height=CELL_HEIGHT,
        resume=resume,
        font_scale=font_scale,
    )

    with print_lock:
        if result["status"] == "success":
            print(f"  [OK] {PRODUCT} / {territory}")
            if result.get("collage_path"):
                print(f"  Colagem: {result['collage_path']}")
            if upload:
                output_dir = Path(config.get_output_dir())
                n = upload_combo(DATASET_ID, PRODUCT, territory, output_dir)
                print(f"  Upload GCS: {n} arquivo(s)")
        else:
            print(f"  [FALHA] {PRODUCT} / {territory}")
            if result.get("error"):
                print(f"  Erro: {result['error']}")

    with results_lock:
        results_list.append(result)

    return result


def main():
    from src.mapbiomas_data.config import ConfigLoader

    parser = argparse.ArgumentParser(
        description="Batch unprecedented_fire — 17 territórios"
    )
    parser.add_argument("--workers", type=int, default=None,
                        help="Workers paralelos (padrao: 12)")
    parser.add_argument("--resume", action="store_true",
                        help="Retomar de onde parou")
    parser.add_argument("--no-upload", action="store_true",
                        help="Pular upload para GCS apos cada combo")
    parser.add_argument("--font-scale", type=float, default=1.0,
                        help="Escala das fontes (padrao: 1.0)")
    args = parser.parse_args()

    workers = args.workers or detect_workers()
    resume = args.resume
    do_upload = not args.no_upload
    font_scale = args.font_scale

    config = ConfigLoader()

    total = len(TERRITORIES)

    print(f"\n{'=' * 60}")
    print(f"FÁBRICA DE GIFS — UNPRECEDENTED FIRE")
    print(f"{'=' * 60}")
    print(f"Dataset: {DATASET_ID}")
    print(f"Produto: {PRODUCT}")
    print(f"Territórios: {len(TERRITORIES)}")
    print(f"Total: {total} execuções")
    print(f"Workers: {workers}")
    print(f"Resume: {resume}")
    print(f"Upload: {'sim' if do_upload else 'nao'}")
    print(f"{'=' * 60}\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(process_one, config, t, resume, do_upload, font_scale)
            for t in TERRITORIES
        ]
        for i, f in enumerate(as_completed(futures), 1):
            if i % 5 == 0 or i == total:
                print(f"\n--- Progresso: {i}/{total} ---")

    ok_count = sum(1 for r in results_list if r["status"] == "success")
    fail_count = sum(1 for r in results_list if r["status"] == "error")

    print(f"\n{'=' * 60}")
    print(f"RESUMO FINAL")
    print(f"{'=' * 60}")
    print(f"Total: {total} | OK: {ok_count} | Falha: {fail_count}")
    print(f"{'=' * 60}")

    if ok_count > 0:
        output_base = config.get_output_dir()
        print(f"\nOutput: {output_base}{DATASET_ID}/")
        root = os.path.dirname(os.path.dirname(__file__))
        print("Reconstruindo indice...")
        subprocess.run([sys.executable, "scripts/index/build_index.py", "--upload"],
                       cwd=root, check=True)
        print("\nProximos passos:")
        print("  python scripts/sync_fire_col5.py  # atualizar planilhas Looker")


if __name__ == "__main__":
    main()
