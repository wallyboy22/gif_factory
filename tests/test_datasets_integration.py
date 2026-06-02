import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from ipam_gif_factory.config import ConfigLoader


class TestDatasetManagerDegradation:
    def setup_method(self):
        self.config = ConfigLoader(config_dir="config").load_all()

    def test_degradation_dataset_exists(self):
        from ipam_gif_factory.core import DatasetManager
        dm = DatasetManager(self.config)
        datasets = dm.list_datasets("degradation")
        assert any(d["id"] == "brasil_degradation_col9" for d in datasets)

    def test_degradation_products_use_processor(self):
        from ipam_gif_factory.core import DatasetManager
        dm = DatasetManager(self.config)
        products = dm.list_products("brasil_degradation_col9")
        assert len(products) > 0
        for prod_id in ["edge_area", "fragment_size", "distance_100ha"]:
            info = dm.get_product("brasil_degradation_col9", prod_id)
            assert "processor" in info, f"{prod_id} should have a processor"
            assert info["processor"] is not None

    def test_all_products_have_visualization(self):
        from ipam_gif_factory.core import DatasetManager
        dm = DatasetManager(self.config)
        for ds in dm.list_datasets():
            for p in dm.list_products(ds["id"]):
                info = dm.get_product(ds["id"], p["id"])
                assert "visualization" in info, f"{ds['id']}/{p['id']} missing visualization"
                assert info["visualization"] is not None
