import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from ipam_gif_factory.config import ConfigLoader
from ipam_gif_factory.core import TerritoryManager


@pytest.fixture
def manager():
    config = ConfigLoader(config_dir="config").load_all()
    return TerritoryManager(config)


class TestTerritoryManager:
    def test_list_types(self, manager):
        types = manager.list_types()
        assert "custom_regions" in types

    def test_list_all_territories(self, manager):
        territories = manager.list_territories()
        assert len(territories) > 30

    def test_list_states(self, manager):
        states = manager.list_territories("states")
        assert any(t["id"] == "df" for t in states)

    def test_df_exists_and_is_test_default(self, manager):
        df = manager.get_territory("df")
        assert df["name"] == "Distrito Federal"
        assert df["type"] == "states"
        assert df["source"] == "projects/mapbiomas-workspace/AUXILIAR/estados-2017"
        assert df["filter"] == "NM_ESTADO == 'DISTRITO FEDERAL'"

    def test_df_has_bbox(self, manager):
        df = manager.get_territory("df")
        assert df["bbox"] is not None
        assert len(df["bbox"]) == 4
        assert df["bbox"][0] < df["bbox"][2]

    def test_get_territory_by_type(self, manager):
        info = manager.get_territory_info("states", "df")
        assert info["name"] == "Distrito Federal"

    def test_get_territory_name(self, manager):
        name = manager.get_territory_name("states", "df")
        assert name == "Distrito Federal"

    def test_get_territory_invalid(self, manager):
        with pytest.raises(KeyError):
            manager.get_territory("nonexistent")

    def test_get_territory_info_invalid(self, manager):
        with pytest.raises(KeyError):
            manager.get_territory_info("states", "nonexistent")

    def test_list_biomes(self, manager):
        biomes = manager.list_territories("biomes")
        biome_names = [b["name"] for b in biomes]
        expected = ["Amazônia", "Caatinga", "Cerrado", "Mata Atlântica", "Pampa", "Pantanal"]
        for e in expected:
            assert e in biome_names, f"Bioma '{e}' não encontrado"

    def test_list_countries(self, manager):
        countries = manager.list_territories("countries")
        country_names = [c["name"] for c in countries]
        assert "Brasil" in country_names
        assert "Paraguai" in country_names

    def test_validate_df(self, manager):
        valid, msg = manager.validate_territory("df")
        assert valid == True

    def test_get_bbox(self, manager):
        bbox = manager.get_bbox("df")
        assert bbox is not None
        assert len(bbox) == 4
