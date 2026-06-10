"""
Teste local: gera todos os produtos Fire Col5 para DF.
Apaga dados antigos e gera do zero com paralelismo.
Uso: python scripts/test_fire_col5_df.py [--workers N]
"""
import argparse
import os
import shutil
import stat
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

DATASET_ID = "brasil_fire_col5"
TERRITORY_ID = "df"

PRODUCTS = [
    "annual_burned",
    "monthly_burned",
    "scar_size_range",
    "accumulated_burned",
    "fire_frequency",
    "year_last_fire",
    "time_after_fire",
    "annual_burned_coverage_nivel0",
    "annual_burned_coverage_nivel1",
    "annual_burned_coverage_nivel1_1",
    "annual_burned_coverage_nivel2",
    "annual_burned_coverage_nivel3",
    "annual_burned_coverage_nivel4",
    "accumulated_burned_coverage_nivel0",
    "accumulated_burned_coverage_nivel1",
    "accumulated_burned_coverage_nivel1_1",
    "accumulated_burned_coverage_nivel2",
    "accumulated_burned_coverage_nivel3",
    "accumulated_burned_coverage_nivel4",
    "severity",
    "fire_return_interval",
    "mean_fire_return_interval",
    "nbr_min",
]
DEFAULT_WORKERS = 8

lock = threading.Lock()
results = {}


def _remove_readonly(func, path, exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def delete_df_data(config):
    output_base = config.get_output_dir()
    base = os.path.join(output_base, DATASET_ID)
    deleted = 0
    for prod in PRODUCTS:
        df_dir = os.path.join(base, prod, TERRITORY_ID)
        if os.path.exists(df_dir):
            shutil.rmtree(df_dir, onerror=_remove_readonly)
            deleted += 1
    if deleted > 0:
        print(f"  {deleted} diretorios DF removidos\n")


def process_one(config, prod, idx, total):
    pipeline = Pipeline(config)
    t0 = time.time()
    result = pipeline.run(
        dataset_id=DATASET_ID,
        product_id=prod,
        territory_id=TERRITORY_ID,
        create_collage=True,
        add_labels=True,
        vertical_dimension=1560,
        cell_height=300,
        resume=False,
    )
    elapsed = time.time() - t0
    status = result["status"]
    with lock:
        results[prod] = result
        if status == "success":
            print(f"\n[{idx:02d}/{total:02d}] OK  {prod}  ({elapsed:.0f}s)")
        else:
            print(f"\n[{idx:02d}/{total:02d}] FALHA  {prod}: {result.get('error','?')}  ({elapsed:.0f}s)")


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()

    config = ConfigLoader()
    total = len(PRODUCTS)

    print("=" * 55)
    print(f"TESTE: Fire Col5 — DF ({total} produtos)")
    print(f"Workers: {args.workers}")
    print("=" * 55)

    print("\nApagando dados antigos do DF...")
    delete_df_data(config)

    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_one, config, prod, i + 1, total): prod
            for i, prod in enumerate(PRODUCTS)
        }
        for f in as_completed(futures):
            f.result()

    total_time = time.time() - t0
    ok = sum(1 for r in results.values() if r["status"] == "success")
    fail = total - ok

    print(f"\n{'=' * 55}")
    print(f"RESULTADO: {ok} OK | {fail} falha(s) | {total} total")
    print(f"Tempo total: {total_time:.0f}s ({total_time/60:.1f}min)")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    run()
