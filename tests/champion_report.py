"""
Collage dimension report for all DF products using champion settings.

Champion: M3.0_C2.0_T4.0_P2.0, D6x6_TS16x5, map at 50%, pure charts.
"""
import csv, os, sys, tempfile, shutil
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
DS_ID = "brasil_fire_col5"
TERRITORY = "uf_df"
PRODUCTS = ["annual_burned", "fire_frequency", "severity"]

# Champion settings
MAP_FS = 3.0
CHART_FS = 2.0
TS_FS = 4.0
COMP_FS = 2.0
DONUT_FIGSIZE = (6, 6)
TS_FIGSIZE = (16, 5)
MAP_SCALE = 0.5

# Territory bounds (from config)
TERR_BOUNDS = {
    "uf_df": [-48.2, -16.1, -47.3, -15.5],
}

OUT_ROOT = os.path.join(
    os.path.dirname(__file__), "test_outputs", "champion_report"
)


def sorted_pngs(d):
    if not os.path.isdir(d):
        return []
    return sorted(
        [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png")]
    )


def main():
    config = ConfigLoader()
    config.load_all()
    os.makedirs(OUT_ROOT, exist_ok=True)

    dm = DatasetManager(config)
    calc = AreaStatsCalculator(config)
    bounds = TERR_BOUNDS[TERRITORY]
    lon_min, lat_min, lon_max, lat_max = bounds

    results = []

    for prod_id in PRODUCTS:
        output_dir = os.path.join(
            config.get_output_dir(), DS_ID, prod_id, TERRITORY
        )
        if not os.path.isdir(output_dir):
            print(f"[SKIP] {prod_id}: no output dir")
            continue

        pinfo = dm.get_product(DS_ID, prod_id)
        viz_key = pinfo.get("visualization", "")
        ref_viz = calc.get_viz_reference(viz_key)
        class_labels = calc.get_class_labels(viz_key)

        # Viz params for chart generator
        cmap_type = ref_viz.get("cmap_type", "binary")
        cls_list = ref_viz.get("classes", [])
        palette = ref_viz.get("palette", ["fdfdfd", "800000"])
        discrete_labels = ref_viz.get("discrete_labels", [])
        label_text = ref_viz.get("label", "")

        class_colors = {}
        if cls_list:
            # From visualization_reference.yaml (has classes with value/color/label)
            for c in cls_list:
                val = c.get("value")
                color = c.get("color", "")
                if val is not None and color:
                    class_colors[val] = f"#{color}"
        elif palette:
            # From visualization.yaml fallback: build from palette + discrete_labels
            for i, p in enumerate(palette):
                lbl = discrete_labels[i] if i < len(discrete_labels) else str(i)
                class_colors[i] = f"#{p}"
                if i not in class_labels:
                    class_labels[i] = lbl

        is_binary = cmap_type == "binary"

        viz_params = {
            "cmap_type": cmap_type,
            "label": label_text,
            "classes": cls_list,
        }

        # Load area stats
        area_dir = os.path.join(output_dir, "area_stats")
        data = {}
        unified = [f for f in os.listdir(area_dir) if f.endswith("_area_stats.csv")]
        if not unified:
            print(f"[SKIP] {prod_id}: no area stats")
            continue
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
        if not is_binary and 0 in all_classes:
            all_classes = [c for c in all_classes if c != 0]
        map_vmax = max(all_classes) if all_classes else 1
        map_vmin = 0 if all_classes and all_classes[0] == 0 else 1
        plot_data = {}
        for cls_val in all_classes:
            vals = []
            for yr in years:
                recs = data.get(yr, [])
                match = next((r for r in recs if r["class"] == cls_val), None)
                vals.append(match["area_ha"] if match else 0)
            plot_data[cls_val] = vals
        first_year = years[0]

        # ---- Pure charts ----
        gen = ChartGenerator(
            class_labels=class_labels,
            class_colors=class_colors,
            viz_params=viz_params,
            font_scale=CHART_FS,
            timeseries_font_scale=TS_FS,
            donut_figsize=DONUT_FIGSIZE,
            donut_binary_figsize=DONUT_FIGSIZE,
            timeseries_figsize=TS_FIGSIZE,
        )
        cdir = tempfile.mkdtemp()
        try:
            annual_dir = os.path.join(cdir, "annual")
            os.makedirs(annual_dir, exist_ok=True)
            gen._plot_annual_donut(
                data[first_year], all_classes, class_colors,
                first_year, os.path.join(annual_dir, f"{first_year}.png"),
                prod_id, TERRITORY, is_binary,
            )
            ts_dir = os.path.join(cdir, "ts")
            os.makedirs(ts_dir, exist_ok=True)
            gen._plot_timeseries_single(
                plot_data, all_classes, class_colors,
                years, 0, os.path.join(ts_dir, f"{first_year}.png"),
                prod_id, TERRITORY,
            )
            donut_pil = PILImage.open(
                os.path.join(annual_dir, f"{first_year}.png")
            ).convert("RGBA")
            ts_pil = PILImage.open(
                os.path.join(ts_dir, f"{first_year}.png")
            ).convert("RGBA")
        finally:
            shutil.rmtree(cdir, ignore_errors=True)

        # ---- Map frame regen at M3.0 ----
        pure_dir = os.path.join(output_dir, "frames_pure")
        pure_paths = sorted_pngs(pure_dir)
        if not pure_paths:
            print(f"[SKIP] {prod_id}: no frames_pure")
            donut_pil.close()
            ts_pil.close()
            continue

        year_labels = {}
        for p in pure_paths:
            yr = os.path.basename(p).replace(".png", "").split("_")[-1]
            year_labels[p] = yr

        tmp_dir = tempfile.mkdtemp()
        try:
            yr_font = int(80 * MAP_FS)
            sc_font = int(50 * MAP_FS)
            for src_p in pure_paths:
                dst = os.path.join(tmp_dir, os.path.basename(src_p))
                shutil.copy2(src_p, dst)
                FrameProcessor.add_year_label(
                    dst, year_labels[src_p],
                    position="top_left",
                    font_size=yr_font,
                    padding_top=max(130, yr_font + 20),
                    bar_color=(255, 255, 255),
                    text_color=(0, 0, 0),
                )
            all_tmp = sorted_pngs(tmp_dir)
            FrameProcessor.batch_add_bottom_bars(
                all_tmp,
                lon_min, lon_max, lat_min, lat_max,
                palette=palette,
                vmin=map_vmin, vmax=map_vmax,
                font_size=sc_font,
                cmap_type=cmap_type,
                show_legend=False,
                show_scale=True,
            )
            map_pil = None
            for fp in all_tmp:
                yr = year_labels[os.path.join(pure_dir, os.path.basename(fp))]
                if yr == str(first_year):
                    img = PILImage.open(fp).convert("RGBA")
                    mw, mh = img.size
                    smw, smh = int(mw * MAP_SCALE), int(mh * MAP_SCALE)
                    map_pil = img.resize((smw, smh), PILImage.LANCZOS)
                    img.close()
                    break
            if map_pil is None:
                print(f"[SKIP] {prod_id}: no matching map")
                donut_pil.close()
                ts_pil.close()
                continue
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        # ---- Compose ----
        comp = Composer(font_scale=COMP_FS)
        legend_entries = []
        for c in cls_list:
            color_hex = c.get("color", "")
            if color_hex:
                from src.mapbiomas_data.core.composer import _parse_hex
                legend_entries.append((_parse_hex(f"#{color_hex}"), c.get("label", "")))

        canvas = comp._layout_map_donut_ts(
            map_pil, donut_pil, ts_pil,
            prod_id, TERRITORY,
            legend_entries,
        )
        cw, ch = canvas.size

        # Save sample
        sample_dir = os.path.join(OUT_ROOT, prod_id)
        os.makedirs(sample_dir, exist_ok=True)
        canvas.save(os.path.join(sample_dir, "composed_sample.png"))
        canvas.close()

        results.append({
            "product": prod_id,
            "viz": viz_key,
            "cmap_type": cmap_type,
            "map_px": f"{smw}x{smh}",
            "donut_px": f"{donut_pil.width}x{donut_pil.height}",
            "ts_px": f"{ts_pil.width}x{ts_pil.height}",
            "canvas_px": f"{cw}x{ch}",
            "map_pct": f"{smw / cw * 100:.1f}%",
            "donut_pct": f"{donut_pil.width / cw * 100:.1f}%",
        })

        donut_pil.close()
        ts_pil.close()
        map_pil.close()

    # Print table
    print(f"\n  Champion: M{MAP_FS:.0f}_C{CHART_FS:.0f}_T{TS_FS:.0f}_P{COMP_FS:.0f}  "
          f"D{DONUT_FIGSIZE[0]}x{DONUT_FIGSIZE[1]}_TS{TS_FIGSIZE[0]}x{TS_FIGSIZE[1]}  "
          f"map@50%  pure charts")
    print(f"\n  {'Product':20s} {'Viz':16s} {'Type':12s} {'Map':16s} "
          f"{'Donut':16s} {'TS':16s} {'Canvas':16s} {'Map%':8s} {'Donut%':8s}")
    print("  " + "-" * 128)
    for r in results:
        print(f"  {r['product']:20s} {r['viz']:16s} {r['cmap_type']:12s} "
              f"{r['map_px']:16s} {r['donut_px']:16s} {r['ts_px']:16s} "
              f"{r['canvas_px']:16s} {r['map_pct']:8s} {r['donut_pct']:8s}")

    # CSV
    csv_path = os.path.join(OUT_ROOT, "champion_dimensions.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "product", "viz", "cmap_type", "map_px", "donut_px",
            "ts_px", "canvas_px", "map_pct", "donut_pct"
        ])
        w.writeheader()
        w.writerows(results)
    print(f"\n  [CSV] {csv_path}")
    print(f"  Samples -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
