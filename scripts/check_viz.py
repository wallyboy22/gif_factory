import sys, os
sys.path.insert(0, "src")
os.environ["PYTHONIOENCODING"] = "utf-8"

from mapbiomas_data.interfaces.cli import CLI
import json

cli = CLI()
prods = cli.datasets.list_products("brasil_fire_col5")
for p in prods:
    viz = p.get("visualization", {})
    has_viz = bool(viz)
    zone_stats = False
    if has_viz:
        if isinstance(viz, str):
            zone_stats = False
        else:
            zone_stats = "zone_statistics" in str(viz)
    print(f"{p['id']:45s} viz={'yes' if has_viz else 'no':5s} zone_stats={'yes' if zone_stats else 'no':5s} temporal={p.get('temporal_range','?')}")
