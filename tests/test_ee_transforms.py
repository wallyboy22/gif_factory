import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from mapbiomas_data.config import ConfigLoader
from mapbiomas_data.core.ee_transforms import (
    PROCESSOR_REGISTRY,
    run_processor,
)


class TestEETransforms:
    def test_processor_registry_has_all(self):
        assert "build_edge_area" in PROCESSOR_REGISTRY
        assert "build_fragment_size" in PROCESSOR_REGISTRY
        assert "build_distance_100ha" in PROCESSOR_REGISTRY
        assert "build_distance_500ha" in PROCESSOR_REGISTRY
        assert "build_distance_1000ha" in PROCESSOR_REGISTRY
        assert "build_secondary_vegetation_coverage" in PROCESSOR_REGISTRY
        assert "build_secondary_vegetation_age" in PROCESSOR_REGISTRY
        assert "build_fire_frequency" in PROCESSOR_REGISTRY
        assert "build_fire_age" in PROCESSOR_REGISTRY
        assert "build_accumulated_burned_coverage" in PROCESSOR_REGISTRY

    def test_run_processor_invalid(self):
        with pytest.raises(KeyError):
            run_processor("nonexistent_processor")

    def test_run_processor_valid_names(self):
        for name in ["build_edge_area", "build_fragment_size", "build_fire_frequency", "build_fire_age"]:
            assert name in PROCESSOR_REGISTRY
            assert callable(PROCESSOR_REGISTRY[name])

    def test_col101_processors_in_registry(self):
        col101_names = [
            "decode_fire_frequency_col101",
            "decode_fire_age_col101",
            "decode_secondary_vegetation_age_col101",
            "build_secondary_vegetation_coverage_col101",
            "build_fire_frequency_coverage_col101",
            "build_burned_natural_coverage_col101",
            "build_burned_at_least_once_col101",
            "decode_edge_area_col101",
            "decode_edge_age_col101",
            "decode_morphology_col101",
            "decode_patch_id_col101",
            "decode_patch_size_col101",
        ]
        for name in col101_names:
            assert name in PROCESSOR_REGISTRY, f"{name} missing from PROCESSOR_REGISTRY"
            assert callable(PROCESSOR_REGISTRY[name]), f"{name} is not callable"

    def test_burned_at_least_once_logic_natural_filter(self):
        from mapbiomas_data.core.ee_transforms import build_burned_at_least_once_col101
        from inspect import getsource
        source = getsource(build_burned_at_least_once_col101)
        assert "natural" in source.split(".where(freq.eq(0).And(cummax.gt(freq))")[1].split(",")[0], \
            "Class 3 condition should include .And(natural) to exclude converted pixels"
