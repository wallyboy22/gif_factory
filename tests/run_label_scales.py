"""
Systematic font scale test for the winning compose size D6x6_TS16x5.

Varies map_font_scale (year, scale, north), chart_font_scale (donut, ts),
and composer_font_scale (title, legend) to find visually balanced proportions.

Map overlays regenerated ONCE per map_fs, charts ONCE per chart_fs, then
composed across all combinations.
"""
import csv, os, shutil, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
from PIL import Image as PILImage

from src.mapbiomas_data.config import ConfigLoader
from src.mapbiomas_data.core.chart_generator import ChartGenerator
from src.mapbiomas_data.core.composer import Composer
from src.mapbiomas_data.core.area_stats import AreaStatsCalculator
from src.mapbiomas_data.core.dataset_manager import DatasetManager
from src.mapbiomas_data.core.frame_processor import FrameProcessor

DPI = 150
PROD_ID = "annual_burned"
TERRITORY = "uf_df"
DS_ID = "brasil_fire_col5"

# Grid
MAP_FS_VALS = [1.5, 2.0, 2.5, 3.0]
CHART_FS_VALS = [1.5, 2.0]
COMPOSER_FS_VALS = [1.5, 2.0]

# Champion chart sizes
DONUT_FIGSIZE = (6, 6)
TS_FIGSIZE = (16, 5)

# Territory bounds (from config/initiatives/brasil/territories/states.yaml)
LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = -48.2, -16.1, -47.3, -15.5

# Map scale in compose (50%)
MAP_SCALE = 0.5

# Viz ref for annual_burned (binary "fire")
VIZ_PALETTE = ["fdfdfd", "800000"]
VIZ_CMAP_TYPE = "binary"


def sorted_pngs(d):
    if not os.path.isdir(d):
        return []
    return sorted(
        [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png")]
    )


def generate_chart(first_year, data, all_classes, class_colors, plot_data,
                   years, chart_fs):
    """Generate pure (raw) charts and return them as PIL images."""
    gen = ChartGenerator(
        class_labels=class_labels,
        class_colors=class_colors,
        viz_params=viz_params,
        font_scale=chart_fs,
        donut_figsize=DONUT_FIGSIZE,
        donut_binary_figsize=DONUT_FIGSIZE,
        timeseries_figsize=TS_FIGSIZE,
    )
    cdir = tempfile.mkdtemp(prefix=f"charts_{chart_fs}_")
    try:
        annual_dir = os.path.join(cdir, "annual")
        os.makedirs(annual_dir, exist_ok=True)
        gen._plot_annual_donut(
            data[first_year], all_classes, class_colors,
            first_year, os.path.join(annual_dir, f"{first_year}.png"),
            PROD_ID, TERRITORY, True,
        )
        ts_dir = os.path.join(cdir, "ts")
        os.makedirs(ts_dir, exist_ok=True)
        gen._plot_timeseries_single(
            plot_data, all_classes, class_colors,
            years, 0, os.path.join(ts_dir, f"{first_year}.png"),
            PROD_ID, TERRITORY,
        )
        donut = PILImage.open(
            os.path.join(annual_dir, f"{first_year}.png")
        ).convert("RGBA")
        ts = PILImage.open(
            os.path.join(ts_dir, f"{first_year}.png")
        ).convert("RGBA")
        return donut, ts
    finally:
        shutil.rmtree(cdir, ignore_errors=True)


def generate_map(first_year, pure_paths, year_labels, map_fs):
    """Regenerate map overlays at given font_scale and return scaled map PIL."""
    tmp_dir = tempfile.mkdtemp(prefix=f"map_{map_fs}_")
    try:
        yr_font_size = int(80 * map_fs)
        scale_font_size = int(50 * map_fs)
        first_map = None
        for src_p in pure_paths:
            dst = os.path.join(tmp_dir, os.path.basename(src_p))
            shutil.copy2(src_p, dst)
            FrameProcessor.add_year_label(
                dst, year_labels[src_p],
                position="top_left",
                font_size=yr_font_size,
                padding_top=max(130, yr_font_size + 20),
                bar_color=(255, 255, 255),
                text_color=(0, 0, 0),
            )
        all_tmp = sorted_pngs(tmp_dir)
        FrameProcessor.batch_add_bottom_bars(
            all_tmp,
            LON_MIN, LON_MAX, LAT_MIN, LAT_MAX,
            palette=VIZ_PALETTE,
            vmin=0, vmax=1,
            font_size=scale_font_size,
            cmap_type=VIZ_CMAP_TYPE,
            show_legend=False,
            show_scale=True,
        )
        for fp in all_tmp:
            yr = year_labels[
                os.path.join(pure_dir, os.path.basename(fp))
            ]
            if yr == str(first_year):
                img = PILImage.open(fp).convert("RGBA")
                mw, mh = img.size
                smw, smh = int(mw * MAP_SCALE), int(mh * MAP_SCALE)
                first_map = img.resize((smw, smh), PILImage.LANCZOS)
                img.close()
                break
        return first_map
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    global class_labels, class_colors, viz_params, pure_dir, year_labels

    config = ConfigLoader()
    config.load_all()

    out_root = os.path.join(
        os.path.dirname(__file__), "test_outputs", "label_scales"
    )
    os.makedirs(out_root, exist_ok=True)

    # Resolve viz
    dm = DatasetManager(config)
    calc = AreaStatsCalculator(config)
    pinfo = dm.get_product(DS_ID, PROD_ID)
    viz_key = pinfo.get("visualization", "")
    ref_viz = calc.get_viz_reference(viz_key)
    class_labels = calc.get_class_labels(viz_key)
    class_colors = {}
    for c in ref_viz.get("classes", []):
        val = c.get("value")
        color = c.get("color", "")
        if val is not None and color:
            class_colors[val] = f"#{color}"
    viz_params = {
        "cmap_type": "binary",
        "label": "Queimado",
        "classes": ref_viz.get("classes", []),
    }

    # Area data
    area_dir = os.path.join(
        config.get_output_dir(), DS_ID, PROD_ID, TERRITORY, "area_stats"
    )
    data = {}
    unified = [f for f in os.listdir(area_dir) if f.endswith("_area_stats.csv")]
    if unified:
        with open(
            os.path.join(area_dir, sorted(unified)[-1]),
            newline="", encoding="utf-8",
        ) as f:
            for row in csv.DictReader(f):
                year = row.get("year", "static")
                if year not in data:
                    data[year] = []
                data[year].append({
                    "class": int(row.get("class_value", 0)),
                    "area_ha": float(row.get("area_ha", 0)),
                })

    years = sorted(data.keys())
    all_classes = sorted(set(r["class"] for recs in data.values() for r in recs))
    plot_data = {}
    for cls_val in all_classes:
        vals = []
        for yr in years:
            recs = data.get(yr, [])
            match = next((r for r in recs if r["class"] == cls_val), None)
            vals.append(match["area_ha"] if match else 0)
        plot_data[cls_val] = vals
    first_year = years[0]

    # Map base: frames_pure
    pure_dir = os.path.join(os.path.dirname(area_dir), "frames_pure")
    pure_paths = sorted_pngs(pure_dir)
    if not pure_paths:
        print("ERROR: No frames_pure found")
        sys.exit(1)

    year_labels = {}
    for p in pure_paths:
        fname = os.path.basename(p)
        yr = fname.replace(".png", "").split("_")[-1]
        year_labels[p] = yr

    print(f"Map base: {len(pure_paths)} frames_pure files\n")

    # Pre-generate pure charts for each chart_fs
    chart_cache = {}
    for chart_fs in CHART_FS_VALS:
        donut, ts = generate_chart(first_year, data, all_classes, class_colors,
                                   plot_data, years, chart_fs)
        chart_cache[chart_fs] = (donut, ts)

    # Pre-generate map overlays for each map_fs
    map_cache = {}
    for map_fs in MAP_FS_VALS:
        scaled = generate_map(first_year, pure_paths, year_labels, map_fs)
        if scaled is not None:
            map_cache[map_fs] = scaled

    # Compose all combinations
    print(
        f"{'Label':45s} {'MapFS':6s} {'ChartFS':6s} {'CompFS':6s} "
        f"{'Map(px)':14s} {'Donut(px)':14s} {'TS(px)':14s} "
        f"{'Canvas(px)':16s}"
    )
    print("-" * 120)

    total = len(MAP_FS_VALS) * len(CHART_FS_VALS) * len(COMPOSER_FS_VALS)
    count = 0
    for map_fs in MAP_FS_VALS:
        scaled_map = map_cache.get(map_fs)
        if scaled_map is None:
            continue
        for chart_fs in CHART_FS_VALS:
            donut, ts = chart_cache.get(chart_fs, (None, None))
            if donut is None or ts is None:
                continue
            for comp_fs in COMPOSER_FS_VALS:
                count += 1
                label = f"M{map_fs:.1f}_C{chart_fs:.1f}_P{comp_fs:.1f}"
                sample_dir = os.path.join(out_root, label)
                os.makedirs(sample_dir, exist_ok=True)

                comp = Composer(font_scale=comp_fs)
                canvas = comp._layout_map_donut_ts(
                    scaled_map, donut, ts,
                    PROD_ID, TERRITORY,
                    [((128, 0, 0), "Queimado")],
                )

                sample_path = os.path.join(sample_dir, "composed_sample.png")
                canvas.save(sample_path)
                cw, ch = canvas.size

                print(
                    f"{label:45s} {map_fs:5.1f}  {chart_fs:5.1f}  "
                    f"{comp_fs:5.1f}  "
                    f"{f'{scaled_map.width}x{scaled_map.height}':14s} "
                    f"{f'{donut.width}x{donut.height}':14s} "
                    f"{f'{ts.width}x{ts.height}':14s} "
                    f"{f'{cw}x{ch}':16s}"
                )
                canvas.close()

    for donut, ts in chart_cache.values():
        donut.close()
        ts.close()
    for m in map_cache.values():
        m.close()

    print(f"\n{total} samples -> {out_root}")


if __name__ == "__main__":
    main()
