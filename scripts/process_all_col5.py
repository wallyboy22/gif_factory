"""Process all col5 products: area-stats + charts + compose + GCS upload."""
import sys, os, json, time
sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

os.environ["PYTHONIOENCODING"] = "utf-8"

from mapbiomas_data.interfaces.cli import CLI
from mapbiomas_data.core.area_stats import AreaStatsCalculator
from mapbiomas_data.core.chart_generator import ChartGenerator
from mapbiomas_data.core.composer import Composer
from pathlib import Path
from sync.upload_to_gcs import upload_combo

DATASET = "brasil_fire_col5"
TERRITORIES = ["uf_df"]
ROOT = Path("outputs/v002")

# Skip products that are RGB / can't have area stats
SKIP_PRODUCTS = {"nbr_min"}

cli = CLI()

# Patch area-stats to skip waiting for GCS
_orig_wait = AreaStatsCalculator.wait_all_tasks
AreaStatsCalculator.wait_all_tasks = lambda self, *a, **kw: None

products = cli.datasets.list_products(DATASET)
results = []

for pinfo in products:
    pid = pinfo["id"]
    if pid in SKIP_PRODUCTS:
        print(f"\n[SKIP] {pid} - RGB product, no area stats")
        continue

    for terr in TERRITORIES:
        print(f"\n{'='*60}")
        print(f"  {pid} / {terr}")
        print(f"{'='*60}")

        # 1. Area stats
        try:
            calc = AreaStatsCalculator(cli.config)
            paths = calc.compute_and_save(DATASET, pid, terr, pinfo, use_gcs=False, resume=False)
            if not paths:
                print(f"  [SKIP] No area stats generated")
                continue
            print(f"  [OK] Area stats: {len(paths)} CSV(s)")
        except Exception as e:
            print(f"  [ERRO] Area stats: {e}")
            import traceback; traceback.print_exc()
            continue

        # 2. Charts
        try:
            gen = ChartGenerator(
                viz_params={"cmap_type": "categorical", "palette": [], "label": ""},
                font_scale=1.0,
            )
            output_dir = calc._get_output_dir(DATASET, pid, terr)
            area_stats_dir = calc._get_area_stats_dir(output_dir)

            # Load viz params for chart generator
            viz_key = pinfo.get("visualization", "")
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
            if annual or ts:
                print(f"  [OK] Charts: {len(annual)} annual + {len(ts)} timeseries")
            else:
                print(f"  [SKIP] No charts generated")
                continue
        except Exception as e:
            print(f"  [ERRO] Charts: {e}")
            import traceback; traceback.print_exc()
            continue

        # 3. Compose
        try:
            comp = Composer(font_scale=1.0)
            viz_params_for_compose = gen.viz_params if viz_key else {}
            paths = comp.compose(
                output_dir,
                product_name=pinfo.get("name", pid),
                territory_name=terr,
                viz_params=viz_params_for_compose,
            )
            print(f"  [OK] Compose: {len(paths)} frame(s)")
        except Exception as e:
            print(f"  [ERRO] Compose: {e}")
            import traceback; traceback.print_exc()
            continue

        # 4. Upload to GCS
        try:
            n = upload_combo(DATASET, pid, terr, ROOT)
            print(f"  [OK] GCS upload: {n} file(s)")
        except Exception as e:
            print(f"  [ERRO] GCS upload: {e}")
            continue

        results.append((pid, terr, "OK"))

print(f"\n{'='*60}")
print(f"  RESULTADO FINAL")
print(f"{'='*60}")
for pid, terr, status in results:
    print(f"  {pid:40s} / {terr:20s}: {status}")
