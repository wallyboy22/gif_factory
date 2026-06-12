"""
Variations of a_half_map: map half scale, larger charts.
"""
import csv, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
from PIL import Image as PILImage

from src.mapbiomas_data.config import ConfigLoader
from src.mapbiomas_data.core.chart_generator import ChartGenerator
from src.mapbiomas_data.core.composer import Composer
from src.mapbiomas_data.core.area_stats import AreaStatsCalculator
from src.mapbiomas_data.core.dataset_manager import DatasetManager

DPI = 150

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

config = ConfigLoader()
config.load_all()

out_root = os.path.join(os.path.dirname(__file__), "test_outputs", "variations")
os.makedirs(out_root, exist_ok=True)

prod_id = "annual_burned"
territory = "uf_df"

# Viz resolve
dm = DatasetManager(config)
calc = AreaStatsCalculator(config)
pinfo = dm.get_product("brasil_fire_col5", prod_id)
viz_key = pinfo.get("visualization", "")
ref_viz = calc.get_viz_reference(viz_key)
class_labels = calc.get_class_labels(viz_key)
class_colors = {}
for c in ref_viz.get("classes", []):
    val = c.get("value")
    color = c.get("color", "")
    if val is not None and color:
        class_colors[val] = f"#{color}"
viz_params = {"cmap_type": "binary", "label": "Queimado", "classes": ref_viz.get("classes", [])}

# Area data
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

# Map frame
frames_dir = os.path.join(config.get_output_dir(), "brasil_fire_col5", prod_id, territory, "frames_clean")
map_path = first_png(frames_dir)
map_img = PILImage.open(map_path).convert("RGBA")
mw_ref, mh_ref = map_img.size
smw, smh = int(mw_ref * 0.5), int(mh_ref * 0.5)
scaled_map = map_img.resize((smw, smh), PILImage.LANCZOS)

# Variations from a_half_map_rank3 (D5x5 TS12x4), increasing chart sizes
configs = [
    # (label, donut_in, ts_in)
    ("D5x5_TS12x4",   (5, 5),   (12, 4)),    # baseline
    ("D6x6_TS12x4",   (6, 6),   (12, 4)),    # bigger donut
    ("D7x7_TS12x4",   (7, 7),   (12, 4)),    # bigger donut
    ("D8x8_TS12x4",   (8, 8),   (12, 4)),    # bigger donut
    ("D5x5_TS14x4.5", (5, 5),   (14, 4.5)),  # bigger ts
    ("D5x5_TS16x5",   (5, 5),   (16, 5)),    # bigger ts
    ("D6x6_TS14x4.5", (6, 6),   (14, 4.5)),  # both bigger
    ("D6x6_TS16x5",   (6, 6),   (16, 5)),    # both bigger
    ("D7x7_TS14x4.5", (7, 7),   (14, 4.5)),  # both bigger
    ("D7x7_TS16x5",   (7, 7),   (16, 5)),    # both bigger
    ("D8x8_TS14x4.5", (8, 8),   (14, 4.5)),  # both bigger
    ("D8x8_TS16x5",   (8, 8),   (16, 5)),    # both bigger
]

print(f"Map half scale: {smw}x{smh}")
print()
print(f"{'Config':25s} {'Map(px)':14s} {'Donut(px)':14s} {'TS(px)':14s} {'Canvas(px)':16s} {'Map%':6s} {'D%':6s}")
print("-" * 95)

for label, (dw_in, dh_in), (tw_in, th_in) in configs:
    dw_px, dh_px = int(dw_in * DPI), int(dh_in * DPI)
    tw_px, th_px = int(tw_in * DPI), int(th_in * DPI)

    gen = ChartGenerator(
        class_labels=class_labels, class_colors=class_colors,
        viz_params=viz_params, font_scale=1.0,
        donut_figsize=(dw_in, dh_in), donut_binary_figsize=(dw_in, dh_in),
        timeseries_figsize=(tw_in, th_in),
    )

    sample_dir = os.path.join(out_root, label)
    os.makedirs(sample_dir, exist_ok=True)

    # Donut raw
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

    # TS raw
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

    dw_actual, dh_actual = donut_clean.size
    tw_actual, th_actual = ts_clean.size
    map_pct = round(smw / cw * 100, 1)
    donut_pct = round(dw_actual / cw * 100, 1)

    print(f"{label:25s} {f'{smw}x{smh}':14s} {f'{dw_actual}x{dh_actual}':14s} "
          f"{f'{tw_actual}x{th_actual}':14s} {f'{cw}x{ch}':16s} {map_pct:5.1f}% {donut_pct:5.1f}%")

    donut_clean.close()
    ts_clean.close()
    canvas.close()

scaled_map.close()
map_img.close()
print(f"\nSamples -> {out_root}")
