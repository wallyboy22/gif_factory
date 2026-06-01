"""
TEMPLATE: Script de Batch da Fábrica de GIFs
============================================

Para usar:
  1. Copie este arquivo (ex: meus_gifs.py)
  2. Edite as seções abaixo: DATASET, PRODUTOS, TERRITÓRIOS
  3. Rode: python meus_gifs.py --workers 6 --resume

Suporta:
  - VS Code (local, usa venv)
  - Google Colab (auto-detecta, instala deps, autentica)

O output vai para: outputs/v001/<dataset>/<produto>/<territorio>/
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
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    import ee
    try:
        ee.Initialize(project='ee-ipam')
    except Exception:
        pass

# ============================================================
# EDITAR AQUI: Dataset
# ============================================================
# ID do dataset no config/datasets.yaml
DATASET_ID = "brasil_fire_col5"

# ============================================================
# EDITAR AQUI: Produtos
# ============================================================
# IDs dos produtos (do config/datasets.yaml)
PRODUCTS = [
    "annual_burned",
    "monthly_burned",
    "scar_size_range",
    "accumulated_burned",
    "fire_frequency",
    "year_last_fire",
    "time_after_fire",
    # coverage (descomente os níveis que quiser)
    # "annual_burned_coverage_nivel0",
    # "annual_burned_coverage_nivel1",
    # "annual_burned_coverage_nivel2",
    # "annual_burned_coverage_nivel3",
    # "accumulated_burned_coverage_nivel0",
    # "accumulated_burned_coverage_nivel1",
    # "accumulated_burned_coverage_nivel2",
    # "accumulated_burned_coverage_nivel3",
]

# ============================================================
# EDITAR AQUI: Territórios
# ============================================================
# IDs dos territórios (do config/territories_*.yaml)
TERRITORIES = [
    "df",
    "brasil",
    "amazonia",
    "caatinga",
    "cerrado",
    "mata_atlantica",
    "pampa",
    "pantanal",
    # estados (descomente os que quiser)
    # "acre", "alagoas", "amapa", "amazonas", "bahia", "ceara",
    # "espirito_santo", "goias", "maranhao", "mato_grosso",
    # "mato_grosso_do_sul", "minas_gerais", "para", "paraiba",
    # "parana", "pernambuco", "piaui", "rio_de_janeiro",
    # "rio_grande_do_norte", "rio_grande_do_sul", "rondonia",
    # "roraima", "santa_catarina", "sao_paulo", "sergipe", "tocantins",
]

# ============================================================
# EDITAR AQUI: Opções
# ============================================================

CREATE_COLLAGE = True        # Criar imagem de colagem (grid anual)
ADD_LABELS = True            # Adicionar títulos, legendas, escala
VERTICAL_DIMENSION = 1560    # Altura dos frames (px)
CELL_HEIGHT = 300            # Altura das células na colagem (px)
RESUME = True                # Retomar de onde parou (checkpoint)
WORKERS = None               # None = auto-detectar (cpu_count - 1, max 12)

# ============================================================
# NÃO EDITAR ABAIXO (pipeline automático)
# ============================================================

print_lock = threading.Lock()
results_list = []
total_combos = 0


def detect_workers():
    """Auto-detecta número de workers baseado em CPU."""
    cores = os.cpu_count() or 4
    return max(1, min(cores - 1, 12))


def process_one(config, territory, prod, resume, workers_count):
    """Executa um combo dataset+produto+territorio."""
    from src.ipam_gif_factory.core.pipeline import Pipeline

    pipeline = Pipeline(config)

    with print_lock:
        print(f"\n[INICIANDO] {prod} / {territory} "
              f"(resume={resume}, workers={workers_count})")

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
            if result.get("gif_path"):
                print(f"  GIF: {result['gif_path']}")
            if result.get("collage_path"):
                print(f"  Colagem: {result['collage_path']}")
        else:
            print(f"  [FALHA] {prod} / {territory}")
            if result.get("error"):
                print(f"  Erro: {result['error']}")

    with print_lock:
        results_list.append(result)

    return result


def main():
    global total_combos
    from src.ipam_gif_factory.config import ConfigLoader

    parser = argparse.ArgumentParser(description="Fábrica de GIFs — Batch")
    parser.add_argument("--workers", type=int, default=None,
                        help="Workers paralelos (padrao: auto-detect)")
    parser.add_argument("--resume", action="store_true", default=None,
                        help="Retomar de onde parou")
    args = parser.parse_args()

    workers = args.workers or WORKERS or detect_workers()
    resume = args.resume if args.resume is not None else RESUME

    config = ConfigLoader()

    combos = [(t, p) for t in TERRITORIES for p in PRODUCTS]
    total_combos = len(combos)

    print(f"\n{'=' * 60}")
    print(f"FÁBRICA DE GIFS — BATCH")
    print(f"{'=' * 60}")
    print(f"Dataset: {DATASET_ID}")
    print(f"Produtos: {len(PRODUCTS)}")
    print(f"Territórios: {len(TERRITORIES)}")
    print(f"Total: {total_combos} combinações")
    print(f"Workers: {workers}")
    print(f"Resume: {resume}")
    print(f"Colagem: {CREATE_COLLAGE}")
    print(f"Colab: {'Sim' if IN_COLAB else 'Não (VS Code)'}")
    print(f"{'=' * 60}\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(process_one, config, t, p, resume, workers)
            for t, p in combos
        ]
        for _ in as_completed(futures):
            pass

    ok = sum(1 for r in results_list if r["status"] == "success")
    fail = sum(1 for r in results_list if r["status"] == "error")

    print(f"\n{'=' * 60}")
    print(f"RESUMO FINAL")
    print(f"{'=' * 60}")
    print(f"Total: {total_combos} | OK: {ok} | Falha: {fail}")
    print(f"{'=' * 60}")

    if ok > 0:
        output_base = config.get_output_dir()
        print(f"\nOutput: {output_base}{DATASET_ID}/")
        print("\nPróximos passos:")
        print("  python sync_to_hub.py        # upload para GCS")
        print("  python build_looker_csvs.py  # CSVs Looker Studio")


if __name__ == "__main__":
    main()
