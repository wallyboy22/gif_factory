import argparse
import sys
sys.path.insert(0, "src")

from ipam_gif_factory.config import ConfigLoader
from ipam_gif_factory.core.pipeline import Pipeline

parser = argparse.ArgumentParser(description="GIFs de degradacao para MATOPIBA + Cerrado + DF")
parser.add_argument("--font-scale", type=float, default=1.0, help="Escala das fontes (padrao: 1.0)")
args = parser.parse_args()

config = ConfigLoader().load_all()
pipeline = Pipeline(config)

DATASET = "brasil_degradation_col10_1"

territory_products = {
    "matopiba_cerrado": [
        "burned_at_least_once",
    ],
    "df": [
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
    ],
    "cerrado": [
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
    ],
}

for territory, prods in territory_products.items():
    for prod in prods:
        print(f"\n\n{'#' * 70}")
        print(f"# Processando: {prod} | Territorio: {territory}")
        print(f"{'#' * 70}")

        result = pipeline.run(
            dataset_id=DATASET,
            product_id=prod,
            territory_id=territory,
            create_collage=True,
            add_labels=True,
            vertical_dimension=1560,
            cell_height=300,
            font_scale=args.font_scale,
        )

        status_sym = "OK" if result["status"] == "success" else "FALHA"
        print(f"\n  [{status_sym}] {prod} - {territory}")
        if result.get("frames"):
            print(f"  Frames: {len(result['frames'])}")
        if result.get("gif_path"):
            print(f"  GIF: {result['gif_path']}")
        if result.get("collage_path"):
            print(f"  Colagem: {result['collage_path']}")
        if result.get("error"):
            print(f"  Erro: {result['error']}")
        print(f"{'#' * 70}\n")
