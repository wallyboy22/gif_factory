"""
Batch Fire Collection 5: Brasil + Biomas + Estados (35 territórios × 23 produtos).
Gera GIFs completos (todos os anos) com colagem, labels, escala e norte.

Uso:
    python run_fire_col5_batch.py                          # fresco, auto-detect workers
    python run_fire_col5_batch.py --workers 6 --resume     # retomando com 6 workers
    python run_fire_col5_batch.py --workers 8              # 8 workers, sem resume

Auto-detecta ambiente: VS Code (local) ou Google Colab.
"""

import sys
import os
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# AMBIENTE (auto-detecta VS Code vs Google Colab)
# ============================================================

IN_COLAB = False
try:
    import google.colab
    IN_COLAB = True
except ImportError:
    pass

if IN_COLAB:
    !pip install -q earthengine-api pillow pyyaml 2>/dev/null
    import ee
    ee.Authenticate()
    ee.Initialize(project='ee-ipam')
else:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    import ee
    try:
        ee.Initialize(project='ee-ipam')
    except Exception:
        pass

# ============================================================
# CONFIGURAÇÃO
# ============================================================

DATASET_ID = "brasil_fire_col5"

PRODUCTS = [
    # Base (7)
    "annual_burned",
    "monthly_burned",
    "scar_size_range",
    "accumulated_burned",
    "fire_frequency",
    "year_last_fire",
    "time_after_fire",
    # Coverage annual (6)
    "annual_burned_coverage_nivel0",
    "annual_burned_coverage_nivel1",
    "annual_burned_coverage_nivel1_1",
    "annual_burned_coverage_nivel2",
    "annual_burned_coverage_nivel3",
    "annual_burned_coverage_nivel4",
    # Coverage accumulated (6)
    "accumulated_burned_coverage_nivel0",
    "accumulated_burned_coverage_nivel1",
    "accumulated_burned_coverage_nivel1_1",
    "accumulated_burned_coverage_nivel2",
    "accumulated_burned_coverage_nivel3",
    "accumulated_burned_coverage_nivel4",
    # Novos (4)
    "severity",
    "fire_return_interval",
    "mean_fire_return_interval",
    "nbr_min",
]

TERRITORIES = [
    # País
    "brasil",
    # Biomas (7)
    "biomas",
    "amazonia",
    "caatinga",
    "cerrado",
    "mata_atlantica",
    "pampa",
    "pantanal",
    # Estados (27)
    "df",
    "acre",
    "alagoas",
    "amapa",
    "amazonas",
    "bahia",
    "ceara",
    "espirito_santo",
    "goias",
    "maranhao",
    "mato_grosso",
    "mato_grosso_do_sul",
    "minas_gerais",
    "para",
    "paraiba",
    "parana",
    "pernambuco",
    "piaui",
    "rio_de_janeiro",
    "rio_grande_do_norte",
    "rio_grande_do_sul",
    "rondonia",
    "roraima",
    "santa_catarina",
    "sao_paulo",
    "sergipe",
    "tocantins",
]

CREATE_COLLAGE = True
ADD_LABELS = True
VERTICAL_DIMENSION = 1560
CELL_HEIGHT = 300

# ============================================================
# PIPELINE
# ============================================================

print_lock = threading.Lock()
results_lock = threading.Lock()
results_list = []


def detect_workers():
    cores = os.cpu_count() or 4
    return max(1, min(cores - 1, 12))


def process_one(config, territory, prod, resume):
    from src.ipam_gif_factory.core.pipeline import Pipeline

    pipeline = Pipeline(config)

    with print_lock:
        print(f"\n[INICIANDO] {prod} / {territory}")

    result = pipeline.run(
        dataset_id=DATASET_ID,
        product_id=prod,
        territory_id=territory,
        create_collage=CREATE_COLLAGE,
        add_labels=ADD_LABELS,
        vertical_dimension=VERTICAL_DIMENSION,
        cell_height=CELL_HEIGHT,
        resume=resume,
    )

    with print_lock:
        if result["status"] == "success":
            print(f"  [OK] {prod} / {territory}")
            if result.get("collage_path"):
                print(f"  Colagem: {result['collage_path']}")
        else:
            print(f"  [FALHA] {prod} / {territory}")
            if result.get("error"):
                print(f"  Erro: {result['error']}")

    with results_lock:
        results_list.append(result)

    return result


def main():
    from src.ipam_gif_factory.config import ConfigLoader

    parser = argparse.ArgumentParser(
        description="Batch Fire Col5 — 35 territórios × 23 produtos"
    )
    parser.add_argument("--workers", type=int, default=None,
                        help="Workers paralelos (padrao: auto-detect)")
    parser.add_argument("--resume", action="store_true",
                        help="Retomar de onde parou")
    args = parser.parse_args()

    workers = args.workers or detect_workers()
    resume = args.resume

    config = ConfigLoader()

    combos = [(t, p) for t in TERRITORIES for p in PRODUCTS]
    total = len(combos)

    print(f"\n{'=' * 60}")
    print(f"FÁBRICA DE GIFS — FIRE COLLECTION 5")
    print(f"{'=' * 60}")
    print(f"Produtos: {len(PRODUCTS)}")
    print(f"Territórios: {len(TERRITORIES)}")
    print(f"Total: {total} combinações")
    print(f"Workers: {workers}")
    print(f"Resume: {resume}")
    print(f"Colab: {'Sim' if IN_COLAB else 'Não (VS Code)'}")
    print(f"{'=' * 60}\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(process_one, config, t, p, resume)
            for t, p in combos
        ]
        for i, f in enumerate(as_completed(futures), 1):
            if i % 10 == 0 or i == total:
                print(f"\n--- Progresso: {i}/{total} ---")

    ok = sum(1 for r in results_list if r["status"] == "success")
    fail = sum(1 for r in results_list if r["status"] == "error")

    print(f"\n{'=' * 60}")
    print(f"RESUMO FINAL")
    print(f"{'=' * 60}")
    print(f"Total: {total} | OK: {ok} | Falha: {fail}")
    print(f"{'=' * 60}")

    if ok > 0:
        output_base = config.get_output_dir()
        print(f"\nOutput: {output_base}{DATASET_ID}/")
        print("\nPróximos passos:")
        print("  python sync_to_hub.py        # upload para GCS")
        print("  python build_looker_csvs.py  # CSVs Looker Studio")


if __name__ == "__main__":
    main()
