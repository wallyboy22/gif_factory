"""
Sizing tests: font scales + element sizes across all visualizations.

Usage:
    python tests/test_sizing.py [--mode font|element|compose|all]

Output saved to tests/test_outputs/
"""

import argparse
import csv
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
from PIL import Image as PILImage

from src.mapbiomas_data.config import ConfigLoader
from src.mapbiomas_data.core.chart_generator import ChartGenerator
from src.mapbiomas_data.core.composer import Composer
from src.mapbiomas_data.core.area_stats import AreaStatsCalculator
from src.mapbiomas_data.core.dataset_manager import DatasetManager

TEST_ROOT = os.path.join(os.path.dirname(__file__), "test_outputs")
DATASET = "brasil_fire_col5"
TERRITORY = "uf_df"

PRODUCTS = [
    ("annual_burned",  "fire",               True,  "Binary gauge"),
    ("severity",       "fire_col5_severity",  False, "Multi-class donut (6 classes)"),
]

FONT_SCALES = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
DONUT_SIZES = [(4, 4), (5, 5), (6, 6), (7, 7), (8, 8)]
DONUT_BINARY_SIZES = [(3.5, 3.5), (4, 4), (5, 5), (6, 6), (7, 7)]
TS_SIZES = [(8, 3), (10, 3.5), (12, 4), (14, 4.5), (16, 5)]
DPI = 150


def _image_info(path: str) -> str:
    if not path or not os.path.exists(path):
        return "N/A"
    img = PILImage.open(path)
    w, h = img.size
    img.close()
    return f"{w}x{h}"


def _load_area_csv(area_dir: str, keep_zero: bool) -> Dict[str, List[Dict]]:
    data = {}
    if not os.path.isdir(area_dir):
        return data
    unified = [f for f in os.listdir(area_dir) if f.endswith("_area_stats.csv")]
    if unified:
        fpath = os.path.join(area_dir, sorted(unified)[-1])
        with open(fpath, newline="", encoding="utf-8") as f:
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


def _resolve_viz_params(config, product_id):
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
        classes_list = ref_viz.get("classes", [])
        for c in classes_list:
            val = c.get("value")
            color = c.get("color", "")
            if val is not None and color:
                class_colors[val] = f"#{color}"
        if not class_colors:
            palette = ref_viz.get("palette", [])
            discrete_labels = ref_viz.get("discrete_labels", [])
            for i, p in enumerate(palette):
                class_colors[i] = f"#{p}"
                if i < len(discrete_labels) and discrete_labels[i]:
                    class_labels[i] = discrete_labels[i]
        viz_params = {
            "cmap_type": ref_viz.get("cmap_type", "categorical"),
            "label": ref_viz.get("label", ""),
        }
        return class_labels, class_colors, viz_params
    except Exception as e:
        print(f"  [WARN] Viz resolve failed for {product_id}: {e}")
        return {}, {}, {}


class SizingTester:
    def __init__(self, config: ConfigLoader):
        self.config = config
        os.makedirs(TEST_ROOT, exist_ok=True)

    def _out_dir(self, *parts: str) -> str:
        p = os.path.join(TEST_ROOT, *parts)
        os.makedirs(p, exist_ok=True)
        return p

    # ==================================================================
    #  Font-Scale Tests
    # ==================================================================

    def run_font_scale_tests(self):
        print(f"\n{'='*60}")
        print("  FONT-SCALE TESTS")
        print(f"{'='*60}")
        results = []

        for prod_id, _, is_binary, desc in PRODUCTS:
            print(f"\n  --- {prod_id} ({desc}) ---")
            class_labels, class_colors, viz_params = self._resolve_viz(prod_id)
            area_dir = self._area_stats_dir(prod_id)
            data = _load_area_csv(area_dir, keep_zero=is_binary)
            if not data:
                print(f"  [SKIP] No area data")
                continue

            years = sorted(data.keys())
            all_classes = sorted(set(r["class"] for recs in data.values() for r in recs))

            for fs in FONT_SCALES:
                label = f"fs_{fs:.2f}".replace(".", "_")
                out = self._out_dir("font_scale_tests", prod_id, label)

                gen = ChartGenerator(
                    class_labels=class_labels,
                    class_colors=class_colors,
                    viz_params=viz_params,
                    font_scale=fs,
                )

                # Generate donut
                first_year = years[0]
                apath = os.path.join(out, f"annual_{first_year}.png")
                gen._plot_annual_donut(
                    data[first_year], all_classes, class_colors,
                    first_year, apath, prod_id, TERRITORY, is_binary,
                )

                # Generate timeseries
                plot_data = {}
                for cls_val in all_classes:
                    vals = []
                    for yr in years:
                        recs = data.get(yr, [])
                        match = next((r for r in recs if r["class"] == cls_val), None)
                        vals.append(match["area_ha"] if match else 0)
                    plot_data[cls_val] = vals

                tpath = os.path.join(out, f"ts_{first_year}.png")
                gen._plot_timeseries_single(
                    plot_data, all_classes, class_colors,
                    years, 0, tpath, prod_id, TERRITORY,
                )

                results.append((prod_id, fs, _image_info(apath), _image_info(tpath)))

        # Print summary
        print(f"\n  --- Font-Scale Summary ---")
        print(f"  {'Product':20s} {'Scale':6s} {'Donut (px)':15s} {'TS (px)':15s}")
        print(f"  {'-'*20} {'-'*6} {'-'*15} {'-'*15}")
        for prod_id, fs, dpx, tpx in results:
            print(f"  {prod_id:20s} {fs:<6.2f} {dpx:15s} {tpx:15s}")

    # ==================================================================
    #  Element Size Tests
    # ==================================================================

    def run_element_size_tests(self):
        print(f"\n{'='*60}")
        print("  ELEMENT SIZE TESTS")
        print(f"{'='*60}")
        results = []

        for prod_id, _, is_binary, desc in PRODUCTS:
            print(f"\n  --- {prod_id} ({desc}) ---")
            class_labels, class_colors, viz_params = self._resolve_viz(prod_id)
            area_dir = self._area_stats_dir(prod_id)
            data = _load_area_csv(area_dir, keep_zero=is_binary)
            if not data:
                print(f"  [SKIP] No area data")
                continue

            years = sorted(data.keys())
            all_classes = sorted(set(r["class"] for recs in data.values() for r in recs))
            first_year = years[0]

            plot_data = {}
            for cls_val in all_classes:
                vals = []
                for yr in years:
                    recs = data.get(yr, [])
                    match = next((r for r in recs if r["class"] == cls_val), None)
                    vals.append(match["area_ha"] if match else 0)
                plot_data[cls_val] = vals

            # -- Donut sizes --
            sizes = DONUT_BINARY_SIZES if is_binary else DONUT_SIZES
            for dw, dh in sizes:
                label = f"donut_{dw}x{dh}"
                out = self._out_dir("element_size_tests", prod_id, label)

                gen = ChartGenerator(
                    class_labels=class_labels,
                    class_colors=class_colors,
                    viz_params=viz_params,
                    donut_figsize=(dw, dh),
                    donut_binary_figsize=(dw, dh),
                )

                apath = os.path.join(out, f"annual_{first_year}.png")
                gen._plot_annual_donut(
                    data[first_year], all_classes, class_colors,
                    first_year, apath, prod_id, TERRITORY, is_binary,
                )
                results.append((prod_id, "donut", f"{dw}x{dh}", _image_info(apath)))

            # -- Timeseries sizes --
            for tw, th in TS_SIZES:
                label = f"ts_{tw}x{th}"
                out = self._out_dir("element_size_tests", prod_id, label)

                gen = ChartGenerator(
                    class_labels=class_labels,
                    class_colors=class_colors,
                    viz_params=viz_params,
                    timeseries_figsize=(tw, th),
                )

                tpath = os.path.join(out, f"ts_{first_year}.png")
                gen._plot_timeseries_single(
                    plot_data, all_classes, class_colors,
                    years, 0, tpath, prod_id, TERRITORY,
                )
                results.append((prod_id, "timeseries", f"{tw}x{th}", _image_info(tpath)))

        # Print summary
        print(f"\n  --- Element Size Summary ---")
        print(f"  {'Product':20s} {'Type':12s} {'Fig Size':10s} {'Output (px)':15s}")
        print(f"  {'-'*20} {'-'*12} {'-'*10} {'-'*15}")
        for prod_id, etype, figsize, px in results:
            print(f"  {prod_id:20s} {etype:12s} {figsize:10s} {px:15s}")

    # ==================================================================
    #  Compose Layout Tests
    # ==================================================================

    def run_compose_layout_tests(self):
        print(f"\n{'='*60}")
        print("  COMPOSE LAYOUT TESTS")
        print(f"{'='*60}")

        prod_id = "annual_burned"
        frames_dir = self._frames_dir(prod_id)
        if not os.path.isdir(frames_dir):
            print(f"  [SKIP] No frames_clean at {frames_dir}")
            return

        class_labels, class_colors, viz_params = self._resolve_viz(prod_id)
        area_dir = self._area_stats_dir(prod_id)
        data = _load_area_csv(area_dir, keep_zero=True)
        if not data:
            print(f"  [SKIP] No area data")
            return

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

        # Load first 5 map frames
        map_frames = []
        for fname in sorted(os.listdir(frames_dir)):
            if fname.endswith(".png"):
                map_frames.append(PILImage.open(os.path.join(frames_dir, fname)).convert("RGBA"))
        n_frames = min(len(map_frames), 5)

        if n_frames == 0:
            print("  [SKIP] No map frames")
            return

        combos = [
            ((5, 5), (8, 3), "default"),
            ((6, 6), (12, 4), "larger"),
            ((4, 4), (16, 5), "small_donut_max_ts"),
            ((6, 6), (10, 3.5), "large_donut_mid_ts"),
            ((7, 7), (14, 4.5), "xl_both"),
        ]

        results = []
        for (dw, dh), (tw, th), desc in combos:
            out = self._out_dir("compose_layout_tests", desc)

            gen = ChartGenerator(
                class_labels=class_labels,
                class_colors=class_colors,
                viz_params=viz_params,
                font_scale=1.0,
                donut_figsize=(dw, dh),
                donut_binary_figsize=(dw, dh),
                timeseries_figsize=(tw, th),
            )

            # Generate donut + clean for first n_frames years
            donut_clean_dir = os.path.join(out, "charts_annual_clean")
            ts_clean_dir = os.path.join(out, "charts_timeseries_clean")
            os.makedirs(donut_clean_dir, exist_ok=True)
            os.makedirs(ts_clean_dir, exist_ok=True)

            donut_raw = []
            for yr in years[:n_frames]:
                apath = os.path.join(out, "charts_annual", f"{yr}.png")
                os.makedirs(os.path.dirname(apath), exist_ok=True)
                gen._plot_annual_donut(
                    data[yr], all_classes, class_colors,
                    yr, apath, prod_id, TERRITORY, True,
                )
                donut_raw.append(apath)

            gen._generate_clean_charts(
                donut_raw, donut_clean_dir, years[:n_frames],
                prod_id, TERRITORY, True,
            )

            ts_raw = []
            for i in range(n_frames):
                tpath = os.path.join(out, "charts_timeseries", f"{years[i]}.png")
                os.makedirs(os.path.dirname(tpath), exist_ok=True)
                gen._plot_timeseries_single(
                    plot_data, all_classes, class_colors,
                    years, i, tpath, prod_id, TERRITORY,
                )
                ts_raw.append(tpath)

            gen._generate_clean_charts(
                ts_raw, ts_clean_dir, years[:n_frames],
                prod_id, TERRITORY, True,
            )

            # Compose using Composer directly with our pre-generated images
            comp = Composer()
            composed_dir = os.path.join(out, "charts_composed")
            os.makedirs(composed_dir, exist_ok=True)

            for i in range(n_frames):
                map_img = map_frames[i]

                donut_path = os.path.join(donut_clean_dir, f"{years[i]}.png")
                donut_img = PILImage.open(donut_path).convert("RGBA") if os.path.exists(donut_path) else None

                ts_path = os.path.join(ts_clean_dir, f"{years[i]}.png")
                ts_img = PILImage.open(ts_path).convert("RGBA") if os.path.exists(ts_path) else None

                legend_entries = [((128, 0, 0), "Queimado")]

                canvas = comp._layout_map_donut_ts(
                    map_img, donut_img, ts_img,
                    "Área queimada anual", "Distrito Federal",
                    legend_entries,
                )

                frame_path = os.path.join(composed_dir, f"{i:04d}.png")
                canvas.save(frame_path)

                if donut_img: donut_img.close()
                if ts_img: ts_img.close()

                if i == 0:
                    cw, ch = canvas.size
                    mw, mh = map_img.size
                    d_img = PILImage.open(donut_path)
                    t_img = PILImage.open(ts_path)
                    results.append({
                        "desc": desc,
                        "config": f"donut={dw}x{dh} ts={tw}x{th}",
                        "map_px": f"{mw}x{mh}",
                        "donut_px": f"{d_img.width}x{d_img.height}",
                        "ts_px": f"{t_img.width}x{t_img.height}",
                        "canvas_px": f"{cw}x{ch}",
                    })
                    d_img.close()
                    t_img.close()

            # Create GIF from composed frames
            composed_pngs = sorted(
                [f for f in os.listdir(composed_dir) if f.endswith(".png")]
            )
            if composed_pngs:
                frames = []
                for fname in composed_pngs:
                    img = PILImage.open(os.path.join(composed_dir, fname)).convert("P",
                        palette=PILImage.ADAPTIVE, colors=256)
                    frames.append(img)
                gif_path = os.path.join(composed_dir, "composed.gif")
                frames[0].save(gif_path, save_all=True, append_images=frames[1:],
                               duration=300, loop=0, optimize=False)

        # Print summary
        print(f"\n  --- Compose Layout Summary ---")
        print(f"  {'Combination':30s} {'Map (px)':15s} {'Donut (px)':15s} {'TS (px)':15s} {'Canvas (px)':15s}")
        print(f"  {'-'*30} {'-'*15} {'-'*15} {'-'*15} {'-'*15}")
        for r in results:
            print(f"  {r['desc']:30s} {r['map_px']:15s} {r['donut_px']:15s} {r['ts_px']:15s} {r['canvas_px']:15s}")

    # ==================================================================
    #  Helpers
    # ==================================================================

    def _area_stats_dir(self, product_id: str) -> str:
        return os.path.join(self.config.get_output_dir(), DATASET, product_id, TERRITORY, "area_stats")

    def _frames_dir(self, product_id: str) -> str:
        return os.path.join(self.config.get_output_dir(), DATASET, product_id, TERRITORY, "frames_clean")

    def _resolve_viz(self, product_id: str):
        return _resolve_viz_params(self.config, product_id)


def main():
    parser = argparse.ArgumentParser(description="Sizing tests: font + element sizes")
    parser.add_argument("--mode", choices=["font", "element", "compose", "all"],
                        default="all")
    args = parser.parse_args()

    config = ConfigLoader()
    config.load_all()

    tester = SizingTester(config)

    if args.mode in ("font", "all"):
        tester.run_font_scale_tests()
    if args.mode in ("element", "all"):
        tester.run_element_size_tests()
    if args.mode in ("compose", "all"):
        tester.run_compose_layout_tests()

    print(f"\nResults -> {TEST_ROOT}")


if __name__ == "__main__":
    main()
