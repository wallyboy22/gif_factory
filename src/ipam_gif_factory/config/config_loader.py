import os
import yaml
import warnings
from typing import Any, Dict


def _deep_merge(base: Dict, overlay: Dict) -> Dict:
    """Mesclar overlay em base recursivamente."""
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigLoader:
    """Carregar e acessar configurações do sistema."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self._datasets: Dict[str, Any] = {}
        self._territories: Dict[str, Any] = {}
        self._visualizations: Dict[str, Any] = {}
        self._paths: Dict[str, Any] = {}
        self._settings: Dict[str, Any] = {}

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        path = os.path.join(self.config_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_yaml_with_includes(self, filename: str) -> Dict[str, Any]:
        """Carregar YAML suportando includes de arquivos externos."""
        data = self._load_yaml(filename)
        includes = data.pop("includes", [])
        for inc in includes:
            inc_path = os.path.join(self.config_dir, inc)
            if not os.path.exists(inc_path):
                warnings.warn(f"Include not found, skipping: {inc}")
                continue
            inc_data = self._load_yaml(inc)
            data = _deep_merge(data, inc_data)
        return data

    def load_all(self):
        self._datasets = self._load_yaml("datasets.yaml")
        self._territories = self._load_yaml_with_includes("territories.yaml")
        self._visualizations = self._load_yaml_with_includes("visualization.yaml")
        self._paths = self._load_yaml("paths.yaml")
        return self

    @property
    def datasets(self) -> Dict[str, Any]:
        if not self._datasets:
            self._datasets = self._load_yaml("datasets.yaml")
        return self._datasets.get("datasets", self._datasets)

    @property
    def categories(self) -> Dict[str, Any]:
        return self._datasets.get("categories", {})

    @property
    def territories(self) -> Dict[str, Any]:
        if not self._territories:
            self._territories = self._load_yaml_with_includes("territories.yaml")
        return self._territories.get("territories", self._territories)

    @property
    def visualizations(self) -> Dict[str, Any]:
        if not self._visualizations:
            self._visualizations = self._load_yaml_with_includes("visualization.yaml")
        return self._visualizations.get("visualizations", self._visualizations)

    @property
    def paths(self) -> Dict[str, Any]:
        if not self._paths:
            self._paths = self._load_yaml("paths.yaml")
        return self._paths

    @property
    def runtime_mode(self) -> str:
        return self.paths.get("runtime", {}).get("mode", "local")

    @property
    def ee_project_id(self) -> str:
        return (
            self.paths.get("paths", self.paths)
            .get("earth_engine", {})
            .get("project_id", "workspace-ipam")
        )

    def get_output_dir(self) -> str:
        paths = self.paths.get("paths", self.paths)
        mode = self.runtime_mode
        if mode == "colab":
            return paths.get("google_drive", {}).get("output_root", "/content/drive/MyDrive/IPAM FRAMES AND GIFS/")
        return paths.get("local", {}).get("output_dir", "./output/")

    def get_cache_dir(self) -> str:
        paths = self.paths.get("paths", self.paths)
        return paths.get("local", {}).get("cache_dir", "./cache/")

    def get_processing_config(self, key: str) -> Dict[str, Any]:
        proc = self.paths.get("processing", {})
        return proc.get(key, {})
