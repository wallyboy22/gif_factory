import json, os, sys, tempfile
from PIL import Image as PILImage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mapbiomas_data.core.gif_generator import GIFGenerator
from mapbiomas_data.core.frame_processor import FrameProcessor

PROD = "annual_burned"
TERR = "uf_df"
BASE = os.path.join(
    os.path.dirname(__file__), "..",
    "outputs", "v002", "brasil_fire_col5", PROD, TERR
)
OUT = os.path.join(os.path.dirname(__file__), "test_outputs", "collage_test")
os.makedirs(OUT, exist_ok=True)

meta = json.load(open(os.path.join(BASE, "metadata", f"metadata_{PROD}.json")))
viz = meta["visualization"]
title_line1 = meta["product"]["name"]
title_line2 = f'{meta["dataset"]["description"]} \u00b7 {meta["territory"]["name"]}'

frames_clean = sorted([
    os.path.join(BASE, "frames_clean", f)
    for f in os.listdir(os.path.join(BASE, "frames_clean"))
    if f.endswith(".png")
])
frames_clean = frames_clean[-9:]  # 9 frames = ~3x3 grid

gen = GIFGenerator()
collage_path = gen.create_collage(
    image_paths=frames_clean,
    output_dir=OUT,
    filename="test_collage.png",
    cell_labels=None,
    cell_height=150,
)

cw = PILImage.open(collage_path).width
cscale = max(1, cw // 2000)
sub_font = int(28 * cscale)
title_font = int(36 * cscale)

legend_path = FrameProcessor.render_legend_overlay(
    width=cw,
    palette=viz.get("palette", ["fdfdfd", "800000"]),
    vmin=viz.get("min", 0), vmax=viz.get("max", 1),
    font_size=sub_font,
    discrete_labels=viz.get("discrete_labels"),
    cmap_type=viz.get("cmap_type", "binary"),
    label=viz.get("label", ""),
)

FrameProcessor.add_year_label(
    collage_path, title_line1,
    position="top_left",
    font_size=title_font,
    padding_top=max(130, title_font + sub_font + 60),
    bar_color=(255, 255, 255),
    text_color=(0, 0, 0),
    subtitle=title_line2,
    subtitle_size=sub_font,
)

FrameProcessor.paste_overlay_below(collage_path, legend_path)
FrameProcessor.add_margin(collage_path, 30)

try:
    os.remove(legend_path)
except OSError:
    pass

print(f"Collage: {collage_path}")
