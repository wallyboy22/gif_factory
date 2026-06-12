"""Quick check viz references for non-binary products."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.mapbiomas_data.config import ConfigLoader
from src.mapbiomas_data.core.area_stats import AreaStatsCalculator
config = ConfigLoader()
config.load_all()
calc = AreaStatsCalculator(config)
for key in ["fire_col5_frequency", "fire_col5_severity", "fire"]:
    ref = calc.get_viz_reference(key)
    classes = ref.get("classes", [])
    palette = ref.get("palette", [])
    print(f"{key}:")
    print(f"  cmap_type: {ref.get('cmap_type', 'N/A')}")
    print(f"  classes: {len(classes)} entries -> {[c.get('label') for c in classes]}")
    print(f"  palette: {len(palette)} colors -> {palette[:3]}...")
    if classes:
        for c in classes:
            print(f"    v={c.get('value')} label={c.get('label')} color={c.get('color')}")
    print()
