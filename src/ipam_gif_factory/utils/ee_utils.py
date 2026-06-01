import re
from typing import Any, Dict


def parse_filter_expression(expression: str) -> Dict[str, Any]:
    parts = expression.split("==")
    if len(parts) == 2:
        field = parts[0].strip()
        value = parts[1].strip().strip("'\"")
        return {"field": field, "value": value}
    parts = expression.split("AND")
    if len(parts) == 2:
        left = parse_filter_expression(parts[0].strip())
        right = parse_filter_expression(parts[1].strip())
        return {"type": "and", "left": left, "right": right}
    raise ValueError(f"Cannot parse filter: {expression}")


def get_asset_type(asset_path: str) -> str:
    if "ImageCollection" in asset_path:
        return "image_collection"
    return "image"


def build_ee_filter(filter_config: Dict[str, Any]):
    try:
        import ee
    except ImportError:
        return None
    if "field" in filter_config and "value" in filter_config:
        return ee.Filter.equals(filter_config["field"], filter_config["value"])
    if "type" in filter_config and filter_config["type"] == "and":
        left = build_ee_filter(filter_config["left"])
        right = build_ee_filter(filter_config["right"])
        if left and right:
            return ee.Filter.and_(left, right)
    return None
