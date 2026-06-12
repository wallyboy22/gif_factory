import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from mapbiomas_data.config import ConfigLoader
from mapbiomas_data.core import DatasetManager


@pytest.fixture
def manager():
    config = ConfigLoader(config_dir="config").load_all()
    return DatasetManager(config)


class TestDatasetManager:
    def test_list_categories(self, manager):
        cats = manager.list_categories()
        assert len(cats) > 0
        assert any(c["id"] == "fire" for c in cats)

    def test_list_datasets(self, manager):
        datasets = manager.list_datasets()
        assert len(datasets) > 0
        assert any(d["id"] == "brasil_fire_col3" for d in datasets)

    def test_list_datasets_by_category(self, manager):
        fire_datasets = manager.list_datasets("fire")
        for ds in fire_datasets:
            assert ds["category"] == "fire"

    def test_list_products(self, manager):
        products = manager.list_products("brasil_fire_col3")
        assert len(products) > 0
        assert any(p["id"] == "annual_burned" for p in products)

    def test_list_products_invalid(self, manager):
        with pytest.raises(KeyError):
            manager.list_products("nonexistent_dataset")

    def test_get_product(self, manager):
        product = manager.get_product("brasil_fire_col3", "annual_burned")
        assert product["id"] == "annual_burned"
        assert "asset" in product
        assert "mapbiomas" in product["asset"]

    def test_get_product_with_territory_info(self, manager):
        product = manager.get_product("brasil_fire_col3", "annual_burned")
        assert "dataset_id" in product
        assert "dataset_source" in product

    def test_get_asset_id(self, manager):
        asset = manager.get_asset_id("brasil_fire_col3", "annual_burned")
        assert asset.startswith("projects/mapbiomas")

    def test_search_fire(self, manager):
        results = manager.search("fire")
        assert len(results) > 0

    def test_search_monthly(self, manager):
        results = manager.search("monthly")
        assert len(results) > 0

    def test_paraguay_products(self, manager):
        products = manager.list_products("paraguay_fire_col1")
        assert len(products) > 0

    def test_soil_product(self, manager):
        product = manager.get_product("brasil_soil", "soc")
        assert product["asset_type"] == "image_collection"
        assert product["mosaic"] == True
        assert product["mask_value"] == -2
