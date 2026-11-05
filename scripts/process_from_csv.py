"""Generate charts + compose from downloaded unified area-stats CSVs.

Reads locally saved {product}_{territory}_area_stats.csv, runs ChartGenerator
and Composer. Only processes combos where the CSV is present.

Run AFTER download_stats_from_gcs.py has downloaded at least some CSVs.
Runs combos in parallel with ThreadPoolExecutor(4).
"""
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from mapbiomas_data.core.chart_generator import ChartGenerator
from mapbiomas_data.core.composer import Composer
from mapbiomas_data.core.area_stats import AreaStatsCalculator
from mapbiomas_data.interfaces.cli import CLI

DATASET = "brasil_fire_col5"
TERRITORIES = [
    "uf_df", "regiao_matopiba",
    "bioma_amazonia", "bioma_caatinga", "bioma_cerrado",
    "bioma_mata_atlantica", "bioma_pampa", "bioma_pantanal",
]
SKIP = {"nbr_min"}
MAX_WORKERS = 4

cli = CLI()
calc = AreaStatsCalculator(cli.config)

products = cli.datasets.list_products(DATASET)

combos = []
for pinfo_short in products:
    pid = pinfo_short["id"]
    if pid in SKIP:
        continue
    for terr in TERRITORIES:
        combos.append((pid, terr))

total = len(combos)
print(f"  Total combos: {total}")
print(f"  Workers: {MAX_WORKERS}")
print()

results = []
done_count = 0


def process_one(pid: str, terr: str) -> tuple:
    """Generate charts + compose for a single combo. Returns (pid, terr, status_str)."""
    output_dir = calc._get_output_dir(DATASET, pid, terr)
    area_stats_dir = calc._get_area_stats_dir(output_dir)
    unified_csv = os.path.join(area_stats_dir, f"{pid}_{terr}_area_stats.csv")

    if not os.path.exists(unified_csv):
        return (pid, terr, "SKIP no_csv")

    pinfo = cli.datasets.get_product(DATASET, pid)

    try:
        viz_key = pinfo.get("visualization", "")
        gen = ChartGenerator(font_scale=1.0)

        if viz_key:
            gen.class_labels = calc.get_class_labels(viz_key)
            ref_viz = calc.get_viz_reference(viz_key)
            gen.viz_params = {
                "cmap_type": ref_viz.get("cmap_type", "categorical"),
                "palette": ref_viz.get("palette", []),
                "label": ref_viz.get("label", ""),
                "min": ref_viz.get("min", 0),
                "max": ref_viz.get("max", 0),
            }
            classes_list = ref_viz.get("classes", [])
            gen.class_colors = {}
            for c in classes_list:
                val = c.get("value")
                color = c.get("color", "")
                if val is not None and color:
                    gen.class_colors[val] = f"#{color}"
            if not gen.class_colors:
                for i, p in enumerate(gen.viz_params.get("palette", [])):
                    gen.class_colors[i] = f"#{p}"

        charts_annual_dir = os.path.join(output_dir, "charts_annual")
        charts_timeseries_dir = os.path.join(output_dir, "charts_timeseries")
        annual, ts = gen.generate(
            area_stats_dir, charts_annual_dir, charts_timeseries_dir,
            pid, terr,
        )
        if not (annual or ts):
            return (pid, terr, "SKIP no_charts")

        comp = Composer(font_scale=1.0)
        viz_params_for_compose = gen.viz_params if viz_key else {}
        paths = comp.compose(
            output_dir,
            product_name=pinfo.get("name", pid),
            territory_name=terr,
            viz_params=viz_params_for_compose,
        )
        return (pid, terr, f"OK {len(annual)}a+{len(ts)}ts+{len(paths)}comp")

    except Exception as e:
        return (pid, terr, f"ERRO {e}")


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
            results.append((pid, terr, f"CRASH {e}"))
            print(f"  [{done_count:3d}/{total}] {pid:35s} / {terr:25s}: CRASH {e}")

ok = sum(1 for _, _, s in results if s.startswith("OK "))
skip = sum(1 for _, _, s in results if s.startswith("SKIP "))
fail = sum(1 for _, _, s in results if s.startswith("ERRO ") or s.startswith("CRASH "))

print(f"\n{'='*60}")
print(f"  CHARTS + COMPOSE RESULTS — {ok} OK, {skip} SKIP, {fail} FAIL")
print(f"{'='*60}")
for pid, terr, status in results:
    flag = "OK" if status.startswith("OK ") else ("--" if status.startswith("SKIP ") else "ERRO")
    print(f"  [{flag}] {pid:35s} / {terr:25s}: {status}")
