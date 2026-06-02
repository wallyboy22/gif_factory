"""
Teste: severidade + nbr_min Fire Col 5 para DF e Tocantins.
Primeiro e último ano de cada produto (2 frames).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.ipam_gif_factory.config import ConfigLoader
from src.ipam_gif_factory.core.pipeline import Pipeline

DATASET = "brasil_fire_col5"
TERRITORIES = ["df", "tocantins"]

PRODUCTS = [
    {"id": "severity",  "filter": ["1986", "2026"]},
    {"id": "nbr_min",   "filter": ["1985", "2025"]},
]

config = ConfigLoader()
pipeline = Pipeline(config)

for territory in TERRITORIES:
    for prod in PRODUCTS:
        print(f"\n{'#' * 60}")
        print(f"# {prod['id']} @ {territory}")
        print(f"{'#' * 60}")

        try:
            result = pipeline.run(
                dataset_id=DATASET,
                product_id=prod["id"],
                territory_id=territory,
                create_collage=False,
                add_labels=True,
                vertical_dimension=1560,
                band_names_filter=prod["filter"],
            )
            status = result.get("status", "?")
            gif = result.get("gif_path", "—")
            print(f"  Status: {status}")
            print(f"  GIF: {gif}")
            print(f"  Frames: {len(result.get('frames', []))}")
        except Exception as e:
            print(f"  [FALHA] {e}")
