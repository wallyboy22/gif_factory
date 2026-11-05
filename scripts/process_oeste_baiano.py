"""Generate GIFs for the 'oeste baiano' custom region (polygon rectangle).

Products (dataset: oeste_baiano):
  - landsat_swir                      : MapBiomas Landsat annual median, false color SWIR1/NIR/RED
  - landsat_rgb                       : MapBiomas Landsat annual median, natural R/G/B
  - lulc_nivel0/1/1_1/2               : MapBiomas Coleção 11, uso e cobertura por nível (coverage_v3)
  - desmatamento_vegetacao_secundaria : MapBiomas Coleção 11, mapa bruto 7 classes (deforestation_secondary_vegetation_v5)

Output goes to outputs/v002/oeste_baiano/ (NOT under brasil_fire_col5).

Usage:
  python scripts/process_oeste_baiano.py [--workers N] [produto1 produto2 ...]
"""
import os
import sys
import traceback
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from mapbiomas_data.core.pipeline import Pipeline
from mapbiomas_data.interfaces.cli import CLI

DATASET = "oeste_baiano"
TERRITORY = "oeste_baiano"
PRODUCTS = ["landsat_swir", "landsat_rgb", "nbr_min", "lulc_nivel0", "lulc_nivel1", "lulc_nivel1_1", "lulc_nivel2", "lulc_nivel3", "lulc_nivel4", "desmatamento_vegetacao_secundaria"]
VERTICAL_DIM = 1000


def run_one(product: str, territory: str) -> tuple:
    print(f"\n{'#'*60}\n# {product} / {territory}\n{'#'*60}", flush=True)
    try:
        cli = CLI()
        config = cli.config
        pipe = Pipeline(config)
        result = pipe.run(
            dataset_id=DATASET,
            product_id=product,
            territory_id=territory,
            vertical_dimension=VERTICAL_DIM,
            add_labels=True,
            create_collage=True,
            resume=True,
            font_scale=0.5,
        )
        status = result.get("status")
        print(f"\n{'='*60}\n  {product} / {territory}: status={status}")
        if result.get("error"):
            print(f"  error: {result.get('error')}")
        if result.get("gif_path"):
            print(f"  gif: {result.get('gif_path')}")
        print("=" * 60, flush=True)
        return (product, status)
    except Exception:
        traceback.print_exc()
        return (product, "error")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4,
                        help="produtos rodando em paralelo (default 4)")
    parser.add_argument("--territory", default=TERRITORY,
                        help="id do territorio (default 5000m)")
    parser.add_argument("product", nargs="*")
    args = parser.parse_args()

    products = args.product or PRODUCTS
    print(f"  Dataset: {DATASET}")
    print(f"  Territory: {args.territory}")
    print(f"  Products: {products}")
    print(f"  Workers: {args.workers}")
    print(f"  Vertical dim: {VERTICAL_DIM}px")
    print()

    ok, fail = [], []
    if args.workers <= 1 or len(products) == 1:
        for p in products:
            name, status = run_one(p, args.territory)
            (ok if status != "error" else fail).append(name)
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(run_one, p, args.territory): p for p in products}
            for fut in as_completed(futs):
                name, status = fut.result()
                (ok if status != "error" else fail).append(name)

    print()
    print("RESUMO")
    print(f"  OK:   {ok}")
    print(f"  FALHOU: {fail}")
    sys.exit(0 if not fail else 1)


if __name__ == "__main__":
    main()