"""
Analyze composed frame dimensions — actual + simulated configurations.

Usage:
    # Actual: measure existing outputs
    python tests/analyze_dimensions.py --batch test_df.json

    # Simulate: compare alternative sizes
    python tests/analyze_dimensions.py --simulate

    # Simulate + generate sample compose frames
    python tests/analyze_dimensions.py --simulate --generate
"""

import argparse
import csv
import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
from PIL import Image as PILImage

from src.mapbiomas_data.config import ConfigLoader
from src.mapbiomas_data.core.chart_generator import ChartGenerator
from src.mapbiomas_data.core.composer import Composer
from src.mapbiomas_data.core.area_stats import AreaStatsCalculator
from src.mapbiomas_data.core.dataset_manager import DatasetManager

REPORT_DIR = os.path.join(os.path.dirname(__file__), "test_outputs")
BATCH_DIR = os.path.join(os.path.dirname(__file__), "..", "config", "batches")

# Composer constants
MARGIN = 6
TITLE_H = 52
LEGEND_H = 56
DPI = 150

# Reference data
DATASET = "brasil_fire_col5"
TERRITORY = "uf_df"
PRODUCTS_DIM = [
    ("annual_burned",  "fire",              True),
    ("fire_frequency", "frequency",         True),
    ("severity",       "fire_col5_severity", False),
]

# Simulated configurations
DONUT_SIZES_IN = [(4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9)]
DONUT_BINARY_IN = [(3.5, 3.5), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8)]
TS_SIZES_IN = [(8, 3), (10, 3.5), (12, 4), (14, 4.5), (16, 5), (18, 5.5)]
MAP_SCALES = [1.0, 0.75, 0.65, 0.5, 0.4]


def in_to_px(w, h):
    return int(w * DPI), int(h * DPI)


def estimate_compose(mw, mh, donut_w, donut_h, ts_w, ts_h):
    donut_panel_w = donut_w if donut_w > 0 else 0
    ts_h_actual = ts_h if ts_h > 0 else max(180, int(mw * 0.22))
    ts_w_actual = ts_w if ts_w > 0 else (mw + donut_panel_w + MARGIN)
    canvas_w = max(mw + donut_panel_w + MARGIN, ts_w_actual)
    canvas_h = TITLE_H + mh + ts_h_actual + LEGEND_H
    return {
        "canvas_w": canvas_w,
        "canvas_h": canvas_h,
        "donut_panel_w": donut_panel_w,
        "map_ratio": round(mw / canvas_w * 100, 1) if canvas_w else 0,
        "donut_ratio": round(donut_panel_w / canvas_w * 100, 1) if canvas_w else 0,
        "ts_ratio": round(ts_w_actual / canvas_w * 100, 1) if canvas_w else 0,
    }


def measure_img(path):
    if not path or not os.path.exists(path):
        return (0, 0)
    with PILImage.open(path) as img:
        return img.size


# ==================================================================
#  Actual measurement (existing outputs)
# ==================================================================

def get_combo_dirs(config, dataset, product, territory):
    base = os.path.join(config.get_output_dir(), dataset, product, territory)
    return {
        "frames_clean": os.path.join(base, "frames_clean"),
        "charts_annual_clean": os.path.join(base, "charts_annual_clean"),
        "charts_timeseries_clean": os.path.join(base, "charts_timeseries_clean"),
        "charts_composed": os.path.join(base, "charts_composed"),
    }


def first_png(d):
    if not os.path.isdir(d):
        return None
    for f in sorted(os.listdir(d)):
        if f.endswith(".png"):
            return os.path.join(d, f)
    return None


def analyze_combo(config, dataset, product, territory):
    dirs = get_combo_dirs(config, dataset, product, territory)
    mw, mh = measure_img(first_png(dirs["frames_clean"]))
    dw, dh = measure_img(first_png(dirs["charts_annual_clean"]))
    tw, th = measure_img(first_png(dirs["charts_timeseries_clean"]))
    cw, ch = measure_img(first_png(dirs["charts_composed"]))
    calc = estimate_compose(mw, mh, dw, dh, tw, th)

    row = OrderedDict()
    row["dataset"] = dataset
    row["product"] = product
    row["territory"] = territory
    row["has_data"] = "Y" if (mw > 0 and dw > 0 and tw > 0) else "N"
    row["map_px"] = f"{mw}x{mh}"
    row["donut_px"] = f"{dw}x{dh}" if dw else "-"
    row["ts_px"] = f"{tw}x{th}" if tw else "-"
    row["actual_composed"] = f"{cw}x{ch}" if cw else "-"
    row["est_canvas_px"] = f"{calc['canvas_w']}x{calc['canvas_h']}"
    row["map_%"] = calc["map_ratio"]
    row["donut_%"] = calc["donut_ratio"]
    row["ts_%"] = calc["ts_ratio"]
    return row


def analyze_batch(config, batch_path):
    with open(batch_path, encoding="utf-8") as f:
        items = json.load(f).get("items", [])
    results = []
    for item in items:
        ds = item.get("dataset", "")
        prod = item.get("product", "")
        terr = item.get("territory", "")
        if all([ds, prod, terr]):
            results.append(analyze_combo(config, ds, prod, terr))
    return results


# ==================================================================
#  Simulation mode
# ==================================================================

def resolve_viz(config, product_id):
    try:
        calc = AreaStatsCalculator(config)
        dm = DatasetManager(config)
        pinfo = dm.get_product(DATASET, product_id)
        viz_key = pinfo.get("visualization", "")
        if not viz_key:
            return {}, {}, {}
        ref_viz = calc.get_viz_reference(viz_key)
        if not ref_viz:
            return {}, {}, {}
        class_labels = calc.get_class_labels(viz_key)
        class_colors = {}
        for c in ref_viz.get("classes", []):
            val = c.get("value")
            color = c.get("color", "")
            if val is not None and color:
                class_colors[val] = f"#{color}"
        if not class_colors:
            for i, p in enumerate(ref_viz.get("palette", [])):
                class_colors[i] = f"#{p}"
        viz_params = {
            "cmap_type": ref_viz.get("cmap_type", "categorical"),
            "label": ref_viz.get("label", ""),
            "classes": ref_viz.get("classes", []),
        }
        return class_labels, class_colors, viz_params
    except Exception:
        return {}, {}, {}


def load_area_data(area_dir, keep_zero=False):
    data = {}
    if not os.path.isdir(area_dir):
        return data
    unified = [f for f in os.listdir(area_dir) if f.endswith("_area_stats.csv")]
    if unified:
        with open(os.path.join(area_dir, sorted(unified)[-1]), newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cls_val = int(row.get("class_value", row.get("class", 0)))
                if not keep_zero and cls_val == 0:
                    continue
                year = row.get("year", "static")
                if year not in data:
                    data[year] = []
                data[year].append({
                    "class": cls_val,
                    "area_ha": float(row.get("area_ha", 0)),
                    "label": row.get("class_name", str(cls_val)),
                })
    return data


def simulate(config, generate=False):
    """Simulate different size combos and optionally generate sample frames."""
    print(f"\n{'='*120}")
    print("  SIZE SIMULATION")
    print(f"{'='*120}")

    # Use annual_burned as reference (has binary data + frames)
    prod_id = "annual_burned"
    class_labels, class_colors, viz_params = resolve_viz(config, prod_id)
    area_dir = os.path.join(config.get_output_dir(), DATASET, prod_id, TERRITORY, "area_stats")
    data = load_area_data(area_dir, keep_zero=True)
    frames_dir = os.path.join(config.get_output_dir(), DATASET, prod_id, TERRITORY, "frames_clean")

    if not data or not os.path.isdir(frames_dir):
        print("  [SKIP] Missing data or frames_clean")
        return

    years = sorted(data.keys())
    first_year = years[0]
    all_classes = sorted(set(r["class"] for recs in data.values() for r in recs))

    plot_data = {}
    for cls_val in all_classes:
        vals = []
        for yr in years:
            recs = data.get(yr, [])
            match = next((r for r in recs if r["class"] == cls_val), None)
            vals.append(match["area_ha"] if match else 0)
        plot_data[cls_val] = vals

    # Measure reference map dimensions
    ref_map = first_png(frames_dir)
    mw, mh = measure_img(ref_map)
    print(f"\n  Reference map: {mw}x{mh}px\n")

    sim_out = os.path.join(REPORT_DIR, "simulation")
    os.makedirs(sim_out, exist_ok=True)

    results = []
    donut_sizes = DONUT_BINARY_IN

    for (dw_in, dh_in), (tw_in, th_in), scale in [
        (d, t, s) for d in donut_sizes for t in TS_SIZES_IN for s in MAP_SCALES
        if s == 1.0 or (d == (5, 5) and t == (8, 3))  # full factorial for scale=1.0, rest limited
    ]:
        dw_px, dh_px = in_to_px(dw_in, dh_in)
        tw_px, th_px = in_to_px(tw_in, th_in)

        # Scaled map
        smw, smh = int(mw * scale), int(mh * scale)

        calc = estimate_compose(smw, smh, dw_px, dh_px, tw_px, th_px)

        label = f"donut_{dw_in}x{dh_in}_ts_{tw_in}x{th_in}_map{scale:.2f}".replace(".", "_")

        results.append(OrderedDict([
            ("config", f"D{dw_in}x{dh_in} TS{tw_in}x{th_in} M{scale:.0%}"),
            ("donut_px", f"{dw_px}x{dh_px}"),
            ("ts_px", f"{tw_px}x{th_px}"),
            ("map_px", f"{smw}x{smh}"),
            ("canvas_px", f"{calc['canvas_w']}x{calc['canvas_h']}"),
            ("map_%", calc["map_ratio"]),
            ("donut_%", calc["donut_ratio"]),
            ("ts_%", calc["ts_ratio"]),
            ("donut_w", dw_px),
            ("map_w", smw),
            ("canvas_w", calc["canvas_w"]),
            ("canvas_h", calc["canvas_h"]),
        ]))

    # Also add full factorial for all scales with best donut/ts sizes
    best_donut_sizes = [(6, 6), (7, 7)]
    best_ts_sizes = [(12, 4), (14, 4.5), (16, 5)]
    for (dw_in, dh_in), (tw_in, th_in), scale in [
        (d, t, s) for d in best_donut_sizes for t in best_ts_sizes for s in MAP_SCALES
    ]:
        dw_px, dh_px = in_to_px(dw_in, dh_in)
        tw_px, th_px = in_to_px(tw_in, th_in)
        smw, smh = int(mw * scale), int(mh * scale)
        calc = estimate_compose(smw, smh, dw_px, dh_px, tw_px, th_px)
        results.append(OrderedDict([
            ("config", f"D{dw_in}x{dh_in} TS{tw_in}x{th_in} M{scale:.0%}"),
            ("donut_px", f"{dw_px}x{dh_px}"),
            ("ts_px", f"{tw_px}x{th_px}"),
            ("map_px", f"{smw}x{smh}"),
            ("canvas_px", f"{calc['canvas_w']}x{calc['canvas_h']}"),
            ("map_%", calc["map_ratio"]),
            ("donut_%", calc["donut_ratio"]),
            ("ts_%", calc["ts_ratio"]),
            ("donut_w", dw_px),
            ("map_w", smw),
            ("canvas_w", calc["canvas_w"]),
            ("canvas_h", calc["canvas_h"]),
        ]))

    # Save CSV
    csv_path = os.path.join(sim_out, "simulation.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print(f"\n  [CSV] {csv_path}  ({len(results)} combos)")

    # Print 20 best-balanced combos
    print(f"\n  {'='*110}")
    print(f"  TOP 20 BEST BALANCED COMBOS (sorted by donut% closest to 30%)")
    print(f"{'='*110}")
    sorted_r = sorted(results, key=lambda r: abs(r["donut_%"] - 30))
    hdr = ["Configuration", "Map (px)", "Donut (px)", "TS (px)", "Canvas (px)",
           "Map%", "Donut%", "TS%"]
    col_w = [32, 14, 14, 14, 16, 6, 7, 6]
    print(f"  {'  '.join(f'{h:<{w}}' for h, w in zip(hdr, col_w))}")
    print(f"  {'  '.join('-'*w for w in col_w)}")
    for r in sorted_r[:20]:
        vals = [r["config"], r["map_px"], r["donut_px"], r["ts_px"],
                r["canvas_px"], f"{r['map_%']}%", f"{r['donut_%']}%", f"{r['ts_%']}%"]
        print(f"  {'  '.join(f'{v:<{w}}' for v, w in zip(vals, col_w))}")

    # Also print default for comparison
    print(f"\n  --- Current default for reference ---")
    dw_px, dh_px = in_to_px(5, 5)
    tw_px, th_px = in_to_px(8, 3)
    calc = estimate_compose(mw, mh, dw_px, dh_px, tw_px, th_px)
    print(f"  D5x5 TS8x3 M100%: map={mw}x{mh} donut={dw_px}x{dh_px} ts={tw_px}x{th_px} "
          f"canvas={calc['canvas_w']}x{calc['canvas_h']}  "
          f"map={calc['map_ratio']}% donut={calc['donut_ratio']}% ts={calc['ts_ratio']}%")

    # Generate sample frames for best 5 combos
    if generate:
        _generate_samples(config, prod_id, data, plot_data, all_classes,
                          class_labels, class_colors, viz_params, mw, mh, frames_dir,
                          sorted_r[:5], sim_out)


def _generate_samples(config, prod_id, data, plot_data, all_classes,
                      class_labels, class_colors, viz_params,
                      mw, mh, frames_dir, top_configs, sim_out):
    """Generate actual compose frames for top configs."""
    print(f"\n  --- Generating sample frames for top 5 configs ---")

    # Load first map frame
    map_path = first_png(frames_dir)
    if not map_path:
        print("  [SKIP] No map frame")
        return
    map_img = PILImage.open(map_path).convert("RGBA")

    # Load first year data
    years = sorted(data.keys())
    first_year = years[0]

    for r in top_configs:
        config_label = r["config"].replace(" ", "_").replace("%", "p")
        out_dir = os.path.join(sim_out, "samples", config_label)
        os.makedirs(out_dir, exist_ok=True)

        # Parse config
        parts = r["config"].split()
        donut_part = parts[0]  # e.g. D6x6
        ts_part = parts[1]     # e.g. TS12x4
        map_part = parts[2]    # e.g. M75%

        dw_in = int(donut_part[1:].split("x")[0])
        dh_in = int(donut_part[1:].split("x")[1])
        tw_in = int(ts_part[2:].split("x")[0])
        th_in = float(ts_part[2:].split("x")[1])
        scale = int(map_part[1:-1]) / 100.0

        # Generate donut at this size
        gen = ChartGenerator(
            class_labels=class_labels,
            class_colors=class_colors,
            viz_params=viz_params,
            font_scale=1.0,
            donut_figsize=(dw_in, dh_in),
            donut_binary_figsize=(dw_in, dh_in),
            timeseries_figsize=(tw_in, th_in),
        )

        # Donut — name by year so clean overlay picks up correct basename
        annual_dir = os.path.join(out_dir, "charts_annual")
        os.makedirs(annual_dir, exist_ok=True)
        donut_raw = os.path.join(annual_dir, f"{first_year}.png")
        gen._plot_annual_donut(
            data[first_year], all_classes, class_colors,
            first_year, donut_raw, prod_id, TERRITORY, True,
        )

        # Donut clean
        donut_clean_dir = os.path.join(out_dir, "charts_annual_clean")
        os.makedirs(donut_clean_dir, exist_ok=True)
        gen._generate_clean_charts(
            [donut_raw], donut_clean_dir, [first_year],
            prod_id, TERRITORY, True,
        )

        # Timeseries — name by year
        ts_dir = os.path.join(out_dir, "charts_timeseries")
        os.makedirs(ts_dir, exist_ok=True)
        ts_raw = os.path.join(ts_dir, f"{first_year}.png")
        gen._plot_timeseries_single(
            plot_data, all_classes, class_colors,
            years, 0, ts_raw, prod_id, TERRITORY,
        )

        # Timeseries clean
        ts_clean_dir = os.path.join(out_dir, "charts_timeseries_clean")
        os.makedirs(ts_clean_dir, exist_ok=True)
        gen._generate_clean_charts(
            [ts_raw], ts_clean_dir, [first_year],
            prod_id, TERRITORY, True,
        )

        # Load clean images
        donut_clean_path = os.path.join(donut_clean_dir, f"{first_year}.png")
        ts_clean_path = os.path.join(ts_clean_dir, f"{first_year}.png")
        donut_clean = PILImage.open(donut_clean_path).convert("RGBA")
        ts_clean = PILImage.open(ts_clean_path).convert("RGBA")

        # Scale map
        if scale != 1.0:
            new_w = int(mw * scale)
            new_h = int(mh * scale)
            scaled_map = map_img.resize((new_w, new_h), PILImage.LANCZOS)
        else:
            scaled_map = map_img

        # Compose
        comp = Composer()
        legend_entries = [((128, 0, 0), "Queimado")]
        canvas = comp._layout_map_donut_ts(
            scaled_map, donut_clean, ts_clean,
            "Área queimada anual", "Distrito Federal",
            legend_entries,
        )

        sample_path = os.path.join(out_dir, "composed_sample.png")
        canvas.save(sample_path)
        cw, ch = canvas.size
        print(f"  [{config_label}] canvas={cw}x{ch} -> {sample_path}")

        donut_clean.close()
        ts_clean.close()
        scaled_map.close()
        canvas.close()

    map_img.close()


def main():
    parser = argparse.ArgumentParser(description="Analyze composed dimensions")
    parser.add_argument("--batch", type=str, default=None, help="Batch JSON file")
    parser.add_argument("--all", action="store_true", help="All batches")
    parser.add_argument("--simulate", action="store_true", help="Run size simulation")
    parser.add_argument("--generate", action="store_true", help="Generate sample compose frames")
    parser.add_argument("--output", type=str, default=None, help="CSV output path")
    args = parser.parse_args()

    config = ConfigLoader()
    config.load_all()
    os.makedirs(REPORT_DIR, exist_ok=True)

    if args.simulate:
        simulate(config, generate=args.generate)
        return

    if args.all:
        batches = sorted(f for f in os.listdir(BATCH_DIR) if f.endswith(".json"))
    elif args.batch:
        batches = [os.path.basename(args.batch)]
    else:
        parser.print_help()
        return

    all_results = []
    for bname in batches:
        bpath = os.path.join(BATCH_DIR, bname)
        if not os.path.exists(bpath):
            continue
        print(f"\n  Batch: {bname}")
        results = analyze_batch(config, bpath)
        all_results.extend(results)
        print(f"  -> {len(results)} combos")

    if not all_results:
        print("\n  No data found.")
        return

    csv_path = args.output or os.path.join(REPORT_DIR, "dimensions_report.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_results[0].keys()))
        w.writeheader()
        w.writerows(all_results)
    print(f"\n  [CSV] {csv_path}")

    # Print table
    headers = ["Dataset", "Product", "Territory", "Map", "Donut", "TS", "Canvas",
               "Map%", "Donut%", "TS%"]
    cw = [14, 22, 16, 14, 14, 14, 16, 6, 7, 6]
    print(f"\n  {'  '.join(f'{h:<{w}}' for h, w in zip(headers, cw))}")
    print(f"  {'  '.join('-'*w for w in cw)}")
    for r in all_results:
        vals = [r["map_px"], r["donut_px"], r["ts_px"], r["est_canvas_px"],
                f"{r['map_%']}%", f"{r['donut_%']}%", f"{r['ts_%']}%"]
        if r["has_data"] == "Y":
            print(f"  {r['dataset'][:cw[0]]:<{cw[0]}}  {r['product'][:cw[1]]:<{cw[1]}}  "
                  f"{r['territory'][:cw[2]]:<{cw[2]}}  {'  '.join(f'{v:<{w}}' for v, w in zip(vals, cw[3:]))}")
        else:
            print(f"  {r['dataset'][:cw[0]]:<{cw[0]}}  {r['product'][:cw[1]]:<{cw[1]}}  "
                  f"{r['territory'][:cw[2]]:<{cw[2]}}  [no data]")

    valid = [r for r in all_results if r["has_data"] == "Y"]
    if valid:
        avg_cw = sum(int(r["est_canvas_px"].split("x")[0]) for r in valid) / len(valid)
        avg_ch = sum(int(r["est_canvas_px"].split("x")[1]) for r in valid) / len(valid)
        print(f"\n  Avg canvas: {avg_cw:.0f}x{avg_ch:.0f}  "
              f"Map: {sum(r['map_%'] for r in valid)/len(valid):.1f}%  "
              f"Donut: {sum(r['donut_%'] for r in valid)/len(valid):.1f}%  "
              f"TS: {sum(r['ts_%'] for r in valid)/len(valid):.1f}%")


if __name__ == "__main__":
    main()
