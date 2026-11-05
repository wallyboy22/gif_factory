"""Dispatch GEE area-stats exports for all MATOPIBA col5 products."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
os.environ["PYTHONIOENCODING"] = "utf-8"

from mapbiomas_data.interfaces.cli import CLI
from mapbiomas_data.core.area_stats import AreaStatsCalculator

DATASET = "brasil_fire_col5"
TERR = "regiao_matopiba"
SKIP = {"nbr_min"}

cli = CLI()
products = cli.datasets.list_products(DATASET)

for pinfo_short in products:
    pid = pinfo_short["id"]
    if pid in SKIP:
        print(f"\n[SKIP] {pid}")
        continue

    # Get full product info with asset
    pinfo = cli.datasets.get_product(DATASET, pid)

    print(f"\n{'='*60}")
    print(f"  {pid} / {TERR}")
    print(f"{'='*60}")

    try:
        calc = AreaStatsCalculator(cli.config)
        paths = calc.compute_and_save(DATASET, pid, TERR, pinfo, use_gcs=True, resume=True)
        if paths:
            print(f"  [OK] {len(paths)} CSV(s) (tasks dispatched)")
        else:
            print(f"  [SKIP] Nothing generated")
    except Exception as e:
        print(f"  [ERRO] {e}")
        continue

print(f"\nDone. All MATOPIBA exports dispatched.")
