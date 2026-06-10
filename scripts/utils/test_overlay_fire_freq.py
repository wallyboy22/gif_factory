"""Testa sistema de overlay: fire_frequency Col5 DF (8 workers)."""
import os
import stat
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

cwd = os.getcwd()
if not os.path.exists(os.path.join(cwd, 'src')):
    parent = os.path.dirname(cwd)
    while not os.path.exists(os.path.join(parent, 'src')) and parent != os.path.dirname(parent):
        parent = os.path.dirname(parent)
    if os.path.exists(os.path.join(parent, 'src')):
        os.chdir(parent)

sys.path.insert(0, os.getcwd())

from src.ipam_gif_factory.config import ConfigLoader
from src.ipam_gif_factory.core.pipeline import Pipeline

DATASET = "brasil_fire_col5"
TERRITORY = "df"
WORKERS = 8

lock = threading.Lock()

# Coverage levels to test
PRODUCTS = [
    "accumulated_burned_coverage_nivel1_1",
]


def rmtree_onerror(func, path, exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def process_one(product_id, idx, total):
    config = ConfigLoader()
    pipeline = Pipeline(config)

    # Clean old data for this product+DF
    output_base = config.get_output_dir()
    df_dir = os.path.join(output_base, DATASET, product_id, TERRITORY)
    if os.path.exists(df_dir):
        shutil.rmtree(df_dir, onerror=rmtree_onerror)

    t0 = time.time()
    result = pipeline.run(
        dataset_id=DATASET,
        product_id=product_id,
        territory_id=TERRITORY,
        create_collage=True,
        add_labels=True,
        vertical_dimension=1560,
        cell_height=300,
        resume=False,
    )
    elapsed = time.time() - t0
    status = result.get("status", "?")
    with lock:
        if status == "success":
            print(f"\n[{idx}/{total}] OK  {product_id}  ({elapsed:.0f}s)")
            ol_dir = os.path.join(config.get_output_dir(), DATASET, product_id, TERRITORY)
            if os.path.exists(ol_dir):
                overlays = [f for f in os.listdir(ol_dir) if "legend" in f.lower()]
                if overlays:
                    for f in overlays:
                        size_kb = os.path.getsize(os.path.join(ol_dir, f)) / 1024
                        print(f"       {f} ({size_kb:.1f} KB)")
        else:
            print(f"\n[{idx}/{total}] FAIL  {product_id}: {result.get('error','?')}  ({elapsed:.0f}s)")
    return result


def main():
    total = len(PRODUCTS)
    print("=" * 55)
    print(f"TESTE OVERLAY: {total} produtos Fire Col5 DF")
    print(f"Workers: {WORKERS}")
    print("=" * 55)

    t0 = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(process_one, p, i + 1, total): p
            for i, p in enumerate(PRODUCTS)
        }
        for f in as_completed(futures):
            results.append(f.result())

    ok = sum(1 for r in results if r.get("status") == "success")
    fail = total - ok
    print(f"\n{'=' * 55}")
    print(f"OK={ok} FAIL={fail} TOTAL={total}  {time.time()-t0:.0f}s")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
