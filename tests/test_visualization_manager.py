import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from ipam_gif_factory.config import ConfigLoader
from ipam_gif_factory.core import VisualizationManager


@pytest.fixture
def manager():
    config = ConfigLoader(config_dir="config").load_all()
    return VisualizationManager(config)


class TestVisualizationManager:
    def test_list_keys(self, manager):
        keys = manager.list_viz_keys()
        assert len(keys) > 10
        assert "fire" in keys
        assert "lulc" in keys
        assert "monthly" in keys
        assert "frequency" in keys

    def test_get_fire_viz(self, manager):
        params = manager.get_viz_params("fire")
        assert params["min"] == 0
        assert params["max"] == 1
        assert len(params["palette"]) == 2
        assert params["palette"][0] == "fdfdfd"
        assert params["palette"][1] == "800000"

    def test_get_lulc_viz(self, manager):
        params = manager.get_viz_params("lulc")
        assert params["min"] == 0
        assert params["max"] == 62
        assert len(params["palette"]) == 63

    def test_get_monthly_viz(self, manager):
        params = manager.get_viz_params("monthly")
        assert params["min"] == 0
        assert params["max"] == 12
        assert len(params["palette"]) == 13

    def test_get_invalid_viz(self, manager):
        with pytest.raises(KeyError):
            manager.get_viz_params("nonexistent_viz")

    def test_get_palette(self, manager):
        palette = manager.get_palette("fire")
        assert len(palette) == 2

    def test_get_range(self, manager):
        r = manager.get_range("frequency")
        assert r == (0, 11)

    def test_build_ee_vis_params(self, manager):
        vis = manager.build_ee_vis_params("fire", band="test_band")
        assert "min" in vis
        assert "max" in vis
        assert "palette" in vis
        assert vis["bands"] == ["test_band"]

    def test_validate_palette_valid(self, manager):
        assert manager.validate_palette("fire") == True

    def test_validate_palette_invalid(self, manager):
        assert manager.validate_palette("nonexistent") == False
