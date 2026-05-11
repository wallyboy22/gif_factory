from typing import Any, Dict, List, Optional, Tuple
from ..config import ConfigLoader


class TerritoryManager:
    """Gerenciar territórios geográficos a partir da configuração YAML."""

    TYPES = ["countries", "biomes", "states", "custom_regions"]

    def __init__(self, config: ConfigLoader):
        self.config = config
        self._territories = config.territories

    def list_types(self) -> List[str]:
        return self.TYPES

    def list_territories(self, territory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        result = []
        territories = self._territories
        if territory_type:
            if territory_type not in territories:
                return []
            for tid, tinfo in territories.get(territory_type, {}).items():
                result.append(self._format_territory(tid, tinfo, territory_type))
        else:
            for ttype in self.TYPES:
                for tid, tinfo in territories.get(ttype, {}).items():
                    result.append(self._format_territory(tid, tinfo, ttype))
        return sorted(result, key=lambda x: (x["type"], x["name"]))

    def _format_territory(self, tid: str, tinfo: Dict, ttype: str) -> Dict[str, Any]:
        return {
            "id": tid,
            "name": tinfo.get("name", tid),
            "name_en": tinfo.get("name_en", ""),
            "type": ttype,
            "source": tinfo.get("source", ""),
            "filter": tinfo.get("filter", ""),
            "bbox": tinfo.get("bbox"),
        }

    def get_territory(self, territory_id: str) -> Dict[str, Any]:
        for ttype in self.TYPES:
            territories = self._territories.get(ttype, {})
            if territory_id in territories:
                return self._format_territory(territory_id, territories[territory_id], ttype)
        raise KeyError(f"Território '{territory_id}' não encontrado")

    def get_territory_info(self, territory_type: str, territory_id: str) -> Dict[str, Any]:
        territories = self._territories.get(territory_type, {})
        if territory_id not in territories:
            raise KeyError(f"Território '{territory_id}' não encontrado em '{territory_type}'")
        return self._format_territory(territory_id, territories[territory_id], territory_type)

    def get_territory_name(self, territory_type: str, territory_id: str) -> str:
        return self.get_territory_info(territory_type, territory_id)["name"]

    def get_feature_collection(self, territory_id: str):
        info = self.get_territory(territory_id)
        try:
            import ee
        except ImportError:
            return None
        fc = ee.FeatureCollection(info["source"])
        if info["filter"]:
            filter_info = self._parse_filter(info["filter"])
            if filter_info:
                fc = fc.filter(ee.Filter.equals(filter_info["field"], filter_info["value"]))
        return fc

    def _parse_filter(self, expression: str) -> Optional[Dict[str, str]]:
        if "==" in expression:
            parts = expression.split("==")
            return {
                "field": parts[0].strip(),
                "value": parts[1].strip().strip("'\""),
            }
        return None

    def get_overlay_fc(self, territory_id: str):
        info = self.get_raw_territory(territory_id)
        overlay_source = info.get("overlay_source")
        if not overlay_source:
            return None
        try:
            import ee
        except ImportError:
            return None
        return ee.FeatureCollection(overlay_source)

    def get_raw_territory(self, territory_id: str) -> Dict[str, Any]:
        for ttype in self.TYPES:
            territories = self._territories.get(ttype, {})
            if territory_id in territories:
                info = territories[territory_id]
                info["id"] = territory_id
                info["type"] = ttype
                return info
        raise KeyError(f"Território '{territory_id}' não encontrado")

    def get_bbox(self, territory_id: str) -> Optional[List[float]]:
        info = self.get_territory(territory_id)
        return info.get("bbox")

    def validate_territory(self, territory_id: str) -> Tuple[bool, str]:
        try:
            info = self.get_territory(territory_id)
            if not info.get("source"):
                return False, "Território sem fonte definida"
            return True, "OK"
        except KeyError as e:
            return False, str(e)
