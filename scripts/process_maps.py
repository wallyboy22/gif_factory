"""Generate map frames (thumbnails) and GIFs for all brasil_fire_col5 products × territories.

Runs combos in parallel with ThreadPoolExecutor(8).
Independent of area stats — runs immediately without waiting for GEE exports.
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

DATASET = "brasil_fire_col5"
TERRITORIES = [
    "uf_df", "regiao_matopiba",
    "bioma_amazonia", "bioma_caatinga", "bioma_cerrado",
    "bioma_mata_atlantica", "bioma_pampa", "bioma_pantanal",
]
VERTICAL_DIM = 2000
MAX_WORKERS = 8

cli = CLI()

products = cli.datasets.list_products(DATASET)

# Build combo list
combos = []
for pinfo_short in products:
    pid = pinfo_short["id"]
    for terr in TERRITORIES:
        combos.append((pid, terr))

total = len(combos)
print(f"  Total combos: {total}")
print(f"  Workers: {MAX_WORKERS}")
print()

results = []
done_count = 0


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
        done_count += 1
        try:
            p, t, status = future.result()
            results.append((p, t, status))
            print(f"  [{done_count:3d}/{total}] {p:35s} / {t:25s}: {status}")
        except Exception as e:
            results.append((pid, terr, f"EXCEPTION {e}"))
            print(f"  [{done_count:3d}/{total}] {pid:35s} / {terr:25s}: CRASH {e}")

# Summary
ok = sum(1 for _, _, s in results if s.startswith("OK "))
fail = sum(1 for _, _, s in results if not s.startswith("OK "))

print(f"\n{'='*60}")
print(f"  MAP RESULTS — {ok} OK, {fail} FAIL")
print(f"{'='*60}")
for pid, terr, status in results:
    flag = "OK" if status.startswith("OK ") else "ERRO"
    print(f"  [{flag}] {pid:35s} / {terr:25s}: {status}")
