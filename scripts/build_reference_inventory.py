"""Inventaria a referência local sem promover assets a produtos executáveis.

Execute na raiz: python scripts/build_reference_inventory.py
O arquivo references/config.py deve ser confiável: runpy executa código Python.
"""
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mapbiomas_data.config import ConfigLoader


def build_inventory(reference, config):
    existing = {}
    for dataset, info in config.datasets.items():
        for product, details in info.get("products", {}).items():
            asset = details.get("asset")
            if asset:
                existing.setdefault(asset, []).append({"dataset": dataset, "product": product})
    records = []
    for initiative, themes in reference.items():
        for theme, collections in themes.items():
            for collection, products in collections.items():
                for item in products:
                    asset = item.get("assetid")
                    records.append({
                        "initiative": initiative, "theme": theme,
                        "collection": collection, "product": item.get("product"),
                        "asset": asset, "dtype": item.get("type"),
                        "scale": item.get("scale"), "decode": item.get("decode"),
                        "visible": item.get("visible", True),
                        "matching_assets": existing.get(asset, []),
                        "status": "nao_validado",
                        "visualization": None,
                    })
    return {"source": "references/config.py:OBJ", "records": records}


def main():
    reference = runpy.run_path(str(ROOT / "references/config.py"))["OBJ"]
    config = ConfigLoader(config_dir=str(ROOT / "config")).load_all()
    inventory = build_inventory(reference, config)
    path = ROOT / "config/reference_inventory.json"
    path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(inventory['records'])} registros: {path}")


if __name__ == "__main__":
    main()
