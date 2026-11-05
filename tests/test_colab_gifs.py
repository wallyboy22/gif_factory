import json
from pathlib import Path

from mapbiomas_data.config import ConfigLoader
from mapbiomas_data.core import DatasetManager, VisualizationManager
from mapbiomas_data.interfaces.colab_gifs import ColabGIFs
from scripts.sync import upload_to_gcs
from mapbiomas_data.interfaces.territory_search import register_selection, search_features
from scripts.build_reference_inventory import build_inventory


def test_theme_alias_and_palettes():
    config = ConfigLoader(config_dir="config").load_all()
    product = DatasetManager(config).get_product("brasil_degradation_col11", "edge_area_1000m_black")
    assert product["id"] == "edge_area_1000m"
    assert product["alias_theme"] == "dark"
    viz = VisualizationManager(config)
    assert viz.get_viz_params("edge_area_1000m", "light")["palette"][0] == "ffffff"
    dark = viz.get_viz_params("edge_area_1000m", "dark")["palette"]
    assert dark[0] == "000000"
    assert dark[-2:] == ["488153", "34673c"]
    assert viz.validate_palette("lulc")


def test_colab_catalog_filters_by_initiative():
    ui = ColabGIFs(ConfigLoader(config_dir="config").load_all())
    assert ui.initiative.value == "brasil"
    assert ui.product.options and ui.territory.options
    ui.initiative.value = "peru"
    assert ui.collection.value.startswith("peru_")
    assert all(value.startswith(("peru", "depart_")) for _, value in ui.territory.options)


def test_upload_light_does_not_include_dark(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(upload_to_gcs, "_get_bucket", lambda: None)
    base = tmp_path / "ds" / "prod" / "terr"
    (base / "dark").mkdir(parents=True)
    (base / "light.gif").write_bytes(b"light")
    (base / "dark" / "dark.gif").write_bytes(b"dark")
    assert upload_to_gcs.upload_combo("ds", "prod", "terr", tmp_path, True) == 1
    assert "/dark/" not in capsys.readouterr().out
    assert upload_to_gcs.upload_combo("ds", "prod", "terr", tmp_path, True, theme="dark") == 1
    assert "/terr/dark/dark.gif" in capsys.readouterr().out


def test_notebook_json():
    notebook = json.loads(Path("notebooks/fabrica_gifs_colab.ipynb").read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4


def test_reference_inventory_preserves_records_and_marks_unvalidated():
    config = ConfigLoader(config_dir="config").load_all()
    ref = {"pais": {"fogo": {"c1": [{"product": "anual", "assetid": "asset", "type": "byte"}]}}}
    record = build_inventory(ref, config)["records"][0]
    assert record["asset"] == "asset"
    assert record["status"] == "nao_validado"
    assert record["visualization"] is None


def test_register_selection_combines_in_one_collection():
    config = ConfigLoader(config_dir="config").load_all()
    records = [
        {"name": "A", "id": "1", "id_field": "codigo", "source": "asset"},
        {"name": "B", "id": "2", "id_field": "codigo", "source": "asset"},
    ]
    first = register_selection(config, records, combine=True, dissolve=True)
    second = register_selection(config, list(reversed(records)), combine=True, dissolve=True)
    assert first == second
    combined = config.territories["municipalities"][first[0]]
    assert len(combined["union_of"]) == 2
    assert combined["dissolve"] is True


def test_search_features_keeps_unique_identifier():
    class FC:
        def filter(self, value): return self
        def limit(self, value): return self
        def getInfo(self):
            return {"features": [{"id": "12", "properties": {"NM_MUN": "Petrolina"}}]}
    class Filter:
        @staticmethod
        def stringContains(field, value): return (field, value)
    class EE:
        FeatureCollection = staticmethod(lambda asset: FC())
    EE.Filter = Filter
    result = search_features(EE, "asset", "NM_MUN", "system:index", "Petro")
    assert result[0]["id"] == "12"
    assert result[0]["name"] == "Petrolina"
