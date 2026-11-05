"""Process all col5 products for uf_df territory: area-stats + charts + compose + GCS."""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
os.environ["PYTHONIOENCODING"] = "utf-8"

from pathlib import Path
from mapbiomas_data.interfaces.cli import CLI
from mapbiomas_data.core.area_stats import AreaStatsCalculator

from mapbiomas_data.core.chart_generator import ChartGenerator
from mapbiomas_data.core.composer import Composer
sys.path.insert(0, PROJECT_ROOT)
from scripts.sync.upload_to_gcs import upload_combo

DATASET = "brasil_fire_col5"
TERR = "uf_df"
ROOT = Path("outputs/v002")
SKIP = {"nbr_min"}

cli = CLI()
products = cli.datasets.list_products(DATASET)

for pinfo_short in products:
    pid = pinfo_short["id"]
    pinfo = cli.datasets.get_product(DATASET, pid)
    if pid in SKIP:
        print(f"\n[SKIP] {pid}")
        continue

    print(f"\n{'='*60}")
    print(f"  {pid} / {TERR}")
    print(f"{'='*60}")

    # 1. Area stats (local)
    try:
        calc = AreaStatsCalculator(cli.config)
        paths = calc.compute_and_save(DATASET, pid, TERR, pinfo, use_gcs=False, resume=False)
        if not paths:
            print(f"  [SKIP] No area stats")
            continue
        print(f"  [OK] Area stats: {len(paths)} CSV(s)")
    except Exception as e:
        print(f"  [ERRO] Area stats: {e}")
        continue

    # 2. Charts
    try:
        gen = ChartGenerator(
            viz_params={"cmap_type": "categorical", "palette": [], "label": ""},
            font_scale=1.0,
        )
        output_dir = calc._get_output_dir(DATASET, pid, TERR)
        area_stats_dir = calc._get_area_stats_dir(output_dir)

        viz_key = pinfo.get("visualization", "")
        if viz_key and isinstance(viz_key, dict):
            gen.viz_params = {
                "cmap_type": viz_key.get("cmap_type", "categorical"),
                "palette": viz_key.get("palette", []),
                "label": viz_key.get("label", ""),
                "min": viz_key.get("min", 0),
                "max": viz_key.get("max", 0),
            }
            gen.class_colors = {}
            for c in viz_key.get("classes", []):
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
            pid, TERR,
        )
        if not annual and not ts:
            print(f"  [SKIP] No charts")
            continue
        print(f"  [OK] Charts: {len(annual)} annual + {len(ts)} timeseries")
    except Exception as e:
        print(f"  [ERRO] Charts: {e}")
        continue

    # 3. Compose
    try:
        comp = Composer(font_scale=1.0)
        paths = comp.compose(
            output_dir,
            product_name=pinfo.get("name", pid),
            territory_name=TERR,
            viz_params=getattr(gen, "viz_params", {}),
        )
        print(f"  [OK] Compose: {len(paths)} frame(s)")
    except Exception as e:
        print(f"  [ERRO] Compose: {e}")
        continue

    # 4. Upload
    try:
        n = upload_combo(DATASET, pid, TERR, ROOT)
        print(f"  [OK] GCS: {n} file(s)")
    except Exception as e:
        print(f"  [ERRO] GCS: {e}")
        continue

    print(f"  [DONE] {pid} / {TERR}")
