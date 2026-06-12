"""
Quick simulation: Approach A (map half size) vs Approach B (charts ~2x).
"""
import csv, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
from PIL import Image as PILImage

from src.mapbiomas_data.config import ConfigLoader
from src.mapbiomas_data.core.chart_generator import ChartGenerator
from src.mapbiomas_data.core.composer import Composer

DPI = 150
MARGIN, TITLE_H, LEGEND_H = 6, 52, 56


def in_to_px(w, h):
    return int(w * DPI), int(h * DPI)


def estimate(mw, mh, dw, dh, tw, th):
    dpw = dw if dw > 0 else 0
    th_a = th if th > 0 else max(180, int(mw * 0.22))
    tw_a = tw if tw > 0 else (mw + dpw + MARGIN)
    cw = max(mw + dpw + MARGIN, tw_a)
    ch = TITLE_H + mh + th_a + LEGEND_H
    return {"canvas_w": cw, "canvas_h": ch, "donut_panel_w": dpw,
            "map_pct": round(mw / cw * 100, 1), "donut_pct": round(dpw / cw * 100, 1)}


def measure_img(path):
    if not path or not os.path.exists(path):
        return (0, 0)
    with PILImage.open(path) as img:
        return img.size


def first_png(d):
    if not os.path.isdir(d):
        return None
    for f in sorted(os.listdir(d)):
        if f.endswith(".png"):
            return os.path.join(d, f)
    return None


def main():
    config = ConfigLoader()
    config.load_all()

    MW, MH = 3552, 2240  # reference map for annual_burned/uf_df

    out = os.path.join(os.path.dirname(__file__), "test_outputs", "simulation2")
    os.makedirs(out, exist_ok=True)

    # Chart size ranges
    donut_sizes = [(4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10)]
    ts_sizes = [(8, 3), (10, 3.5), (12, 4), (14, 4.5), (16, 5), (18, 5.5), (20, 6)]

    combos = []

    # Approach A: map_scale=0.5, various donut x ts
    for dw, dh in donut_sizes:
        for tw, th in ts_sizes:
            dw_px, dh_px = in_to_px(dw, dh)
            tw_px, th_px = in_to_px(tw, th)
            smw, smh = int(MW * 0.5), int(MH * 0.5)
            e = estimate(smw, smh, dw_px, dh_px, tw_px, th_px)
            combos.append(("A_half_map", f"D{dw}x{dh} TS{tw}x{th}", smw, smh, dw_px, dh_px, tw_px, th_px, e))

    # Approach B: map full size, charts increasing to ~2x
    for dw, dh in [(6, 6), (7, 7), (8, 8), (9, 9), (10, 10)]:
        for tw, th in [(12, 4), (14, 4.5), (16, 5), (18, 5.5), (20, 6)]:
            dw_px, dh_px = in_to_px(dw, dh)
            tw_px, th_px = in_to_px(tw, th)
            e = estimate(MW, MH, dw_px, dh_px, tw_px, th_px)
            combos.append(("B_double_charts", f"D{dw}x{dh} TS{tw}x{th}", MW, MH, dw_px, dh_px, tw_px, th_px, e))

    # CSV
    csv_path = os.path.join(out, "simulation2.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Approach", "Config", "Map(px)", "Donut(px)", "TS(px)", "Canvas(px)", "Map%", "Donut%"])
        for app, cfg, smw, smh, dw_px, dh_px, tw_px, th_px, e in combos:
            w.writerow([app, cfg, f"{smw}x{smh}", f"{dw_px}x{dh_px}", f"{tw_px}x{th_px}",
                        f"{e['canvas_w']}x{e['canvas_h']}", e["map_pct"], e["donut_pct"]])

    # Print best 10 of each approach
    for approach, label in [("A_half_map", "APPROACH A: MAP HALF SIZE"),
                            ("B_double_charts", "APPROACH B: CHARTS ~2x SIZE")]:
        subset = [c for c in combos if c[0] == approach]
        subset.sort(key=lambda c: abs(c[-1]["donut_pct"] - 30))
        print(f"\n{'='*90}")
        print(f"  {label}")
        print(f"{'='*90}")
        print(f"  {'Config':35s} {'Map(px)':14s} {'Donut(px)':14s} {'TS(px)':14s} {'Canvas':16s} {'M%':6s} {'D%':6s}")
        print(f"  {'-'*35} {'-'*14} {'-'*14} {'-'*14} {'-'*16} {'-'*6} {'-'*6}")
        for c in subset[:10]:
            app, cfg, smw, smh, dw_px, dh_px, tw_px, th_px, e = c
            cw_str = f"{e['canvas_w']}x{e['canvas_h']}"
            print(f"  {cfg:35s} {f'{smw}x{smh}':14s} {f'{dw_px}x{dh_px}':14s} {f'{tw_px}x{th_px}':14s} "
                  f"{cw_str:16s} {e['map_pct']:5.1f}% {e['donut_pct']:5.1f}%")

    # Generate samples for best 3 of each approach
    print(f"\n  --- Generating samples ---")
    prod_id = "annual_burned"
    territory = "uf_df"

    # Load reference data
    from src.mapbiomas_data.core.area_stats import AreaStatsCalculator
    from src.mapbiomas_data.core.dataset_manager import DatasetManager
    dm = DatasetManager(config)
    pinfo = dm.get_product("brasil_fire_col5", prod_id)
    viz_key = pinfo.get("visualization", "")
    calc = AreaStatsCalculator(config)
    ref_viz = calc.get_viz_reference(viz_key)
    class_labels = calc.get_class_labels(viz_key)
    class_colors = {}
    for c in ref_viz.get("classes", []):
        val = c.get("value")
        color = c.get("color", "")
        if val is not None and color:
            class_colors[val] = f"#{color}"
    viz_params = {"cmap_type": "binary", "label": "Queimado", "classes": ref_viz.get("classes", [])}

    # Load area data
    area_dir = os.path.join(config.get_output_dir(), "brasil_fire_col5", prod_id, territory, "area_stats")
    data = {}
    unified = [f for f in os.listdir(area_dir) if f.endswith("_area_stats.csv")]
    if unified:
        with open(os.path.join(area_dir, sorted(unified)[-1]), newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                year = row.get("year", "static")
                if year not in data:
                    data[year] = []
                data[year].append({
                    "class": int(row.get("class_value", row.get("class", 0))),
                    "area_ha": float(row.get("area_ha", 0)),
                })

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

    # Load map frame
    frames_dir = os.path.join(config.get_output_dir(), "brasil_fire_col5", prod_id, territory, "frames_clean")
    map_path = first_png(frames_dir)
    if not map_path:
        print("  [SKIP] No map frame")
        return
    map_img = PILImage.open(map_path).convert("RGBA")

    for approach, label in [("A_half_map", "a_half_map"), ("B_double_charts", "b_double_charts")]:
        subset = [c for c in combos if c[0] == approach]
        subset.sort(key=lambda c: abs(c[-1]["donut_pct"] - 30))
        for rank, c in enumerate(subset[:3]):
            app, cfg, smw, smh, dw_px, dh_px, tw_px, th_px, e = c
            parts = cfg.split()
            dp = parts[0]  # D6x6
            tp = parts[1]  # TS12x4
            dw_in = int(dp[1:].split("x")[0])
            dh_in = int(dp[1:].split("x")[1])
            tw_in = int(tp[2:].split("x")[0])
            th_in = float(tp[2:].split("x")[1])
            scale = 0.5 if approach == "A_half_map" else 1.0

            sample_dir = os.path.join(out, f"{label}_rank{rank+1}_{cfg.replace(' ','_')}")
            os.makedirs(sample_dir, exist_ok=True)

            gen = ChartGenerator(
                class_labels=class_labels, class_colors=class_colors,
                viz_params=viz_params, font_scale=1.0,
                donut_figsize=(dw_in, dh_in), donut_binary_figsize=(dw_in, dh_in),
                timeseries_figsize=(tw_in, th_in),
            )

            # Donut
            annual_dir = os.path.join(sample_dir, "charts_annual")
            os.makedirs(annual_dir, exist_ok=True)
            gen._plot_annual_donut(data[first_year], all_classes, class_colors,
                first_year, os.path.join(annual_dir, f"{first_year}.png"),
                prod_id, territory, True)

            # Donut clean
            clean_d = os.path.join(sample_dir, "charts_annual_clean")
            os.makedirs(clean_d, exist_ok=True)
            gen._generate_clean_charts([os.path.join(annual_dir, f"{first_year}.png")],
                clean_d, [first_year], prod_id, territory, True)

            # Timeseries
            ts_dir = os.path.join(sample_dir, "charts_timeseries")
            os.makedirs(ts_dir, exist_ok=True)
            gen._plot_timeseries_single(plot_data, all_classes, class_colors,
                years, 0, os.path.join(ts_dir, f"{first_year}.png"),
                prod_id, territory)

            # TS clean
            clean_ts = os.path.join(sample_dir, "charts_timeseries_clean")
            os.makedirs(clean_ts, exist_ok=True)
            gen._generate_clean_charts([os.path.join(ts_dir, f"{first_year}.png")],
                clean_ts, [first_year], prod_id, territory, True)

            # Compose
            scaled_map = map_img.resize((smw, smh), PILImage.LANCZOS) if scale == 0.5 else map_img
            donut_clean = PILImage.open(os.path.join(clean_d, f"{first_year}.png")).convert("RGBA")
            ts_clean = PILImage.open(os.path.join(clean_ts, f"{first_year}.png")).convert("RGBA")

            comp = Composer()
            canvas = comp._layout_map_donut_ts(
                scaled_map, donut_clean, ts_clean,
                "Área queimada anual", "Distrito Federal",
                [((128, 0, 0), "Queimado")],
            )
            sample_path = os.path.join(sample_dir, "composed_sample.png")
            canvas.save(sample_path)
            cw, ch = canvas.size
            print(f"  [{label} rank{rank+1}] {cfg} -> canvas={cw}x{ch} -> {sample_path}")
            donut_clean.close()
            ts_clean.close()
            canvas.close()

    map_img.close()

    print(f"\n  CSV: {csv_path}")
    print(f"  Samples: {out}/samples/")


if __name__ == "__main__":
    main()
