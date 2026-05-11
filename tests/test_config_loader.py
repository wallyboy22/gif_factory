import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from ipam_gif_factory.config import ConfigLoader


@pytest.fixture
def config():
    return ConfigLoader(config_dir="config").load_all()


class TestConfigLoader:
    def test_load_datasets(self, config):
        datasets = config.datasets
        assert isinstance(datasets, dict)
        assert len(datasets) > 0
        assert "brasil_fire_col3" in datasets

    def test_load_territories(self, config):
        territories = config.territories
        assert isinstance(territories, dict)
        assert "countries" in territories
        assert "biomes" in territories
        assert "states" in territories

    def test_df_territory_exists(self, config):
        states = config.territories.get("states", {})
        assert "df" in states, "DF (Distrito Federal) deve existir como território de teste"
        assert states["df"]["name"] == "Distrito Federal"

    def test_load_visualizations(self, config):
        viz = config.visualizations
        assert isinstance(viz, dict)
        assert "fire" in viz
        assert "monthly" in viz
        assert "frequency" in viz
        assert "lulc" in viz

    def test_viz_palettes_have_colors(self, config):
        viz = config.visualizations
        for key, v in viz.items():
            if v.get("random_viz", False):
                continue
            palette = v.get("palette", [])
            assert len(palette) > 0, f"Visualização '{key}' não tem paleta"

    def test_load_paths(self, config):
        paths = config.paths
        assert isinstance(paths, dict)
        assert "runtime" in paths

    def test_runtime_mode(self, config):
        assert config.runtime_mode in ("local", "colab")

    def test_get_output_dir(self, config):
        output = config.get_output_dir()
        assert isinstance(output, str)
        assert len(output) > 0

    def test_categories_structure(self, config):
        cats = config.categories
        assert isinstance(cats, dict)
        expected = ["fire", "land_cover"]
        for c in expected:
            assert c in cats, f"Categoria '{c}' não encontrada"

    def test_datasets_have_products(self, config):
        for ds_id, ds in config.datasets.items():
            products = ds.get("products", {})
            assert len(products) > 0, f"Dataset '{ds_id}' não tem produtos"
