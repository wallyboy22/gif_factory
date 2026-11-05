"""Generate a minimum-NBR quality mosaic (Landsat) GIF for a custom point region.

Uses the brasil_fire_col5 nbr_min product (landsat-view QMNBR mosaic, RGB swir1/nir/red)
over the 'ponto_oeste_baiano' custom territory (center -44.52, -11.00; 2.5 km height, 16:9 landscape).
"""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from mapbiomas_data.core.pipeline import Pipeline
from mapbiomas_data.interfaces.cli import CLI

DATASET = "brasil_fire_col5"
PRODUCT = "nbr_min"
TERRITORY = "ponto_oeste_baiano"
VERTICAL_DIM = 1200

cli = CLI()

print(f"  Dataset: {DATASET}")
print(f"  Product: {PRODUCT}")
print(f"  Territory: {TERRITORY}")
print(f"  Vertical dim: {VERTICAL_DIM}px")
print()

try:
    pipe = Pipeline(cli.config)
    result = pipe.run(
        dataset_id=DATASET,
        product_id=PRODUCT,
        territory_id=TERRITORY,
        vertical_dimension=VERTICAL_DIM,
        add_labels=True,
        create_collage=True,
        resume=True,
    )
    print()
    print("=" * 60)
    print(f"  status: {result.get('status')}")
    if result.get("error"):
        print(f"  error: {result.get('error')}")
    if result.get("gif_path"):
        print(f"  gif: {result.get('gif_path')}")
    print("=" * 60)
except Exception:
    traceback.print_exc()
    sys.exit(1)