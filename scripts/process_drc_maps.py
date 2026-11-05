"""Generate map frames (thumbnails) and GIFs for DRC LULC Collection 1 (3 levels).

Runs the Pipeline for nivel0/nivel1/nivel2 over the whole DRC country.
Resume-safe: each combo's StateManager skips completed steps.
"""
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from mapbiomas_data.core.pipeline import Pipeline
from mapbiomas_data.interfaces.cli import CLI

DATASET = "drc_lulc_col1"
PRODUCTS = ["nivel0", "nivel1", "nivel2"]
VERTICAL_DIM = 2000
MAX_WORKERS = 3

import argparse

cli = CLI()

parser = argparse.ArgumentParser(description="Processa mapas DRC LULC Collection 1")
parser.add_argument("--territory", default="drc", help="Territory ID (default: drc)")
args = parser.parse_args()
TERRITORY = args.territory

combos = [(pid, TERRITORY) for pid in PRODUCTS]

total = len(combos)
print(f"  Total combos: {total}")
print(f"  Workers: {MAX_WORKERS}")
print()


def process_one(pid: str, terr: str) -> tuple:
    """Process maps for a single combo. Returns (pid, terr, status_str)."""
    try:
        pipe = Pipeline(cli.config)
        result = pipe.run(
            dataset_id=DATASET,
            product_id=pid,
            territory_id=terr,
            vertical_dimension=VERTICAL_DIM,
            add_labels=True,
            create_collage=True,
            resume=True,
        )
        status = result.get("status", "error")
        if status == "success":
            return (pid, terr, f"OK  GIF={result.get('gif_path', 'N/A')}")
        else:
            err = result.get("error", status)
            return (pid, terr, f"FAIL {err}")
    except Exception as e:
        return (pid, terr, f"EXCEPTION {e}")


with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
    futures = {pool.submit(process_one, pid, terr): (pid, terr) for pid, terr in combos}

    for future in as_completed(futures):
        pid, terr = futures[future]
        done_count = sum(1 for f in futures if f.done())
        try:
            p, t, status = future.result()
            print(f"  [{done_count:3d}/{total}] {p:15s} / {t:20s}: {status}")
        except Exception as e:
            print(f"  [{done_count:3d}/{total}] {pid:15s} / {terr:20s}: CRASH {e}")

# Summary
print(f"\n{'='*60}")
print(f"  DRC MAP RESULTS — {DATASET} / {TERRITORY}")
print(f"{'='*60}")
for pid, terr in combos:
    print(f"  [{pid}] -> outputs/v002/{DATASET}/{pid}/{terr}/gifs/")