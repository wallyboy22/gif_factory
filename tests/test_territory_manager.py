import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from mapbiomas_data.config import ConfigLoader
from mapbiomas_data.core import TerritoryManager


@pytest.fixture
def manager():
    config = ConfigLoader(config_dir="config").load_all()
    return TerritoryManager(config)


class TestTerritoryManager:
    def test_list_types(self, manager):
        types = manager.list_types()
        assert "regions" in types

    def test_list_all_territories(self, manager):
        territories = manager.list_territories()
        assert len(territories) > 30

    def test_list_ufs(self, manager):
        states = manager.list_territories("states")
        assert any(t["id"] == "uf_df" for t in states)

    def test_uf_df_exists(self, manager):
        df = manager.get_territory("uf_df")
        assert df["name"] == "Distrito Federal"
        assert df["type"] == "states"
        assert df["source"] == "projects/mapbiomas-workspace/AUXILIAR/estados-2017"
        assert df["filter"] == "NM_ESTADO == 'DISTRITO FEDERAL'"

    def test_uf_df_has_bbox(self, manager):
        df = manager.get_territory("uf_df")
        assert df["bbox"] is not None
        assert len(df["bbox"]) == 4
        assert df["bbox"][0] < df["bbox"][2]

    def test_get_territory_by_type(self, manager):
        info = manager.get_territory_info("states", "uf_df")
        assert info["name"] == "Distrito Federal"

    def test_get_territory_name(self, manager):
        name = manager.get_territory_name("states", "uf_df")
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

    def test_validate_uf_df(self, manager):
        valid, msg = manager.validate_territory("uf_df")
        assert valid == True

    def test_get_bbox(self, manager):
        bbox = manager.get_bbox("uf_df")
        assert bbox is not None
        assert len(bbox) == 4


class _FakeFC:
    """FeatureCollection falsa: registra as operações sem tocar no GEE."""

    def __init__(self, source=None):
        self.source = source
        self.ops = []

    def filter(self, filt):
        self.ops.append(("filter", filt))
        return self

    def merge(self, other):
        self.ops.append(("merge", other))
        return self

    def union(self, max_error):
        self.ops.append(("union", max_error))
        return self


def _fake_ee():
    import types
    mod = types.ModuleType("ee")
    mod.FeatureCollection = _FakeFC
    mod.Filter = types.SimpleNamespace(
        equals=lambda field, value: ("equals", field, value),
        inList=lambda field, values: ("inList", field, values),
    )
    return mod


class TestTerritoryUnion:
    def test_union_declared_in_yaml(self, manager):
        info = manager.get_territory("juazeiro_petrolina")
        assert info["union_of"] == ["juazeiro_ba", "petrolina_pe"]
        assert info["dissolve"] is True
        valid, _ = manager.validate_territory("juazeiro_petrolina")
        assert valid is True

    def test_union_builds_one_feature_collection(self, manager, monkeypatch):
        monkeypatch.setitem(sys.modules, "ee", _fake_ee())
        fc = manager.get_feature_collection("juazeiro_petrolina")
        assert isinstance(fc, _FakeFC)
        ops = [op for op, _ in fc.ops]
        assert ops.count("merge") == 1
        assert "union" in ops

    def test_union_accepts_inline_members(self, manager, monkeypatch):
        manager._territories["municipalities"]["inline_pair"] = {
            "name": "Inline",
            "union_of": [
                {"source": "src", "filter": "NM_MUN == 'A'"},
                {"source": "src", "filter_in": {"field": "NM_MUN", "values": ["B"]}},
            ],
        }
        monkeypatch.setitem(sys.modules, "ee", _fake_ee())
        fc = manager.get_feature_collection("inline_pair")
        assert "merge" in [op for op, _ in fc.ops]

    def test_union_cycle_raises(self, manager, monkeypatch):
        manager._territories["municipalities"]["loop_a"] = {"union_of": ["loop_b"]}
        manager._territories["municipalities"]["loop_b"] = {"union_of": ["loop_a"]}
        monkeypatch.setitem(sys.modules, "ee", _fake_ee())
        with pytest.raises(ValueError, match="Ciclo"):
            manager.get_feature_collection("loop_a")
