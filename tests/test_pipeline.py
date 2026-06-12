import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from mapbiomas_data.config import ConfigLoader
from mapbiomas_data.core import Pipeline


@pytest.fixture
def pipeline():
    config = ConfigLoader(config_dir="config").load_all()
    return Pipeline(config)


class TestPipeline:
    def test_init(self, pipeline):
        assert pipeline.datasets is not None
        assert pipeline.territories is not None
        assert pipeline.visualizations is not None
        assert pipeline.downloader is not None
        assert pipeline.gif_generator is not None

    def test_list_available(self, pipeline):
        available = pipeline.list_available()
        assert len(available) > 0
        assert "brasil_fire_col3" in available
        assert "annual_burned" in available["brasil_fire_col3"]

    def test_list_available_degradation(self, pipeline):
        available = pipeline.list_available()
        assert "edge_area" in available.get("brasil_degradation_col9", [])

    def test_list_available_soil(self, pipeline):
        available = pipeline.list_available()
        assert "soc" in available.get("brasil_soil", [])

    def test_validate_combinations(self, pipeline):
        combinations = [
            ("brasil_fire_col3", "annual_burned", "uf_df", "fire"),
            ("brasil_fire_col3", "monthly_burned", "uf_df", "monthly"),
            ("brasil_lulc_col9", "integration", "uf_df", "lulc"),
            ("brasil_soil", "soc", "uf_df", "soc"),
            ("brasil_degradation_col9", "edge_area", "uf_df", "edge_area"),
            ("brasil_degradation_col9", "fragment_size", "uf_df", "patch_size"),
        ]
        for combo in combinations:
            try:
                info = pipeline.datasets.get_product(combo[0], combo[1])
                t_info = pipeline.territories.get_territory(combo[2])
                viz = pipeline.visualizations.get_viz_params(combo[3])
                assert info is not None
                assert t_info is not None
                assert len(viz["palette"]) > 0
            except Exception as e:
                pytest.fail(f"Combination {combo} failed: {e}")
