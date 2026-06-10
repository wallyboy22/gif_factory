"""
Processa degradacao col10.1 em paralelo com checkpoint.

Uso:
    python run_degradacao_biomas.py                      # fresco, do zero
    python run_degradacao_biomas.py --resume              # retoma de onde parou
    python run_degradacao_biomas.py --workers 6           # 6 em paralelo
    python run_degradacao_biomas.py --resume --workers 6  # retomando com 6 workers

Dica: se um produto falhar no meio, corrija o erro e rode com --resume
que ele pula as etapas ja concluidas.
"""

import sys
import argparse
import concurrent.futures
import threading
sys.path.insert(0, "src")

from ipam_gif_factory.config import ConfigLoader
from ipam_gif_factory.core.pipeline import Pipeline

DATASET = "brasil_degradation_col10_1"

PRODUCTS = [
    "fire_frequency",
    "natural_coverage",
    "burned_natural_coverage",
    "burned_at_least_once",
    "primary_natural_coverage",
    "fire_age",
    "patch_id",
    "patch_size",
    "edge_area",
    "edge_age",
    "landscape_morphology",
    "secondary_vegetation_age",
    "secondary_vegetation_coverage",
]

BIOMAS = [
    "amazonia",
    "caatinga",
    "cerrado",
    "mata_atlantica",
    "pampa",
    "pantanal",
]

TERRITORIOS = BIOMAS + ["biomas", "brasil"]

print_lock = threading.Lock()
results_lock = threading.Lock()
results_list = []


def process_one(config, territory, prod, resume, resume_from_gcs, upload, font_scale=1.0):
    from pathlib import Path
    from scripts.upload_to_gcs import upload_combo, is_combo_complete_on_gcs

    if resume_from_gcs:
        output_dir = Path(config.get_output_dir())
        if is_combo_complete_on_gcs(DATASET, prod, territory, output_dir):
            with print_lock:
                print(f"\n[SKIP GCS] {prod} / {territory} — completo no GCS")
            with results_lock:
                results_list.append({"status": "success", "skipped_gcs": True})
            return

    pipeline = Pipeline(config)

    with print_lock:
        modo = "resume" if resume else "fresh"
        print(f"\n[INICIANDO] {prod} / {territory} ({modo})")

    result = pipeline.run(
        dataset_id=DATASET,
        product_id=prod,
        territory_id=territory,
        create_collage=True,
        add_labels=True,
        vertical_dimension=2048,
        cell_height=300,
        resume=resume,
        font_scale=font_scale,
    )

    with print_lock:
        if result["status"] == "success":
            print(f"\n  [OK] {prod} - {territory}")
            if result.get("gif_path"):
                print(f"  GIF: {result['gif_path']}")
            if result.get("collage_path"):
                print(f"  Colagem: {result['collage_path']}")
            if upload:
                output_dir = Path(config.get_output_dir())
                n = upload_combo(DATASET, prod, territory, output_dir)
                print(f"  Upload GCS: {n} arquivo(s)")
        else:
            print(f"\n  [FALHA] {prod} - {territory}")
            if result.get("error"):
                print(f"  Erro: {result['error']}")

    with results_lock:
        results_list.append(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GIFs de degradacao para biomas + Brasil")
    parser.add_argument("--workers", type=int, default=4, help="Workers paralelos (padrao: 4)")
    parser.add_argument("--resume", action="store_true", help="Retomar de onde parou (checkpoint local)")
    parser.add_argument("--resume-from-gcs", action="store_true",
                        help="Pular combos já completos no GCS + resume local no resto")
    parser.add_argument("--no-upload", action="store_true",
                        help="Pular upload para GCS apos cada combo")
    parser.add_argument("--font-scale", type=float, default=1.0, help="Escala das fontes (padrao: 1.0)")
    args = parser.parse_args()

    config = ConfigLoader().load_all()
    do_upload = not args.no_upload
    resume = args.resume or args.resume_from_gcs

    combos = [(territory, prod) for territory in TERRITORIOS for prod in PRODUCTS]
    total = len(combos)
    print(f"Total de combinacoes: {total}")
    print(f"Workers: {args.workers}")
    print(f"Modo: {'resume' if args.resume else 'fresh'}")
    print(f"Resume from GCS: {args.resume_from_gcs}")
    print(f"Upload: {'sim' if do_upload else 'nao'}")
    print(f"Font scale: {args.font_scale}")
    print()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(process_one, config, territory, prod, resume, args.resume_from_gcs, do_upload, args.font_scale)
            for territory, prod in combos
        ]
        concurrent.futures.wait(futures)

    ok_count = sum(1 for r in results_list if r["status"] == "success")
    fail_count = sum(1 for r in results_list if r["status"] == "error")

    print(f"\n\n{'=' * 60}")
    print("RESUMO FINAL")
    print(f"{'=' * 60}")
    print(f"Total: {total} | OK: {ok_count} | Falha: {fail_count}")
    print(f"{'=' * 60}")

    if ok_count > 0:
        output_base = config.get_output_dir()
        print(f"\nOutput: {output_base}{DATASET}/")
        root = Path(__file__).resolve().parent.parent
        print("Reconstruindo indice...")
        import subprocess
        subprocess.run([sys.executable, "scripts/index/build_index.py", "--upload"],
                       cwd=str(root), check=True)
