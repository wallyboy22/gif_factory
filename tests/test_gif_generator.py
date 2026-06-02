import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from PIL import Image
from ipam_gif_factory.core import GIFGenerator


@pytest.fixture
def generator():
    return GIFGenerator(frame_duration=200, loop_count=0)


@pytest.fixture
def sample_images():
    images = []
    for i in range(3):
        img = Image.new("RGBA", (100, 100), (255, i * 100, 0, 255))
        img_path = f"/tmp/test_frame_{i}.png"
        img.save(img_path)
        images.append(img_path)
    yield images
    for p in images:
        if os.path.exists(p):
            os.remove(p)


class TestGIFGenerator:
    def test_create_gif(self, generator, sample_images, tmp_path):
        output = generator.create_gif(sample_images, str(tmp_path), "test.gif")
        assert os.path.exists(output)
        assert output.endswith(".gif")

    def test_create_gif_empty(self, generator, tmp_path):
        with pytest.raises(ValueError):
            generator.create_gif([], str(tmp_path), "empty.gif")

    def test_create_gif_sort(self, generator, sample_images, tmp_path):
        unsorted = list(reversed(sample_images))
        output = generator.create_gif(unsorted, str(tmp_path), "sorted.gif", sort_frames=True)
        assert os.path.exists(output)

    def test_create_collage(self, generator, sample_images, tmp_path):
        output = generator.create_collage(sample_images, str(tmp_path), "collage.png")
        assert os.path.exists(output)
        assert output.endswith(".png")

    def test_create_collage_empty(self, generator, tmp_path):
        with pytest.raises(ValueError):
            generator.create_collage([], str(tmp_path), "empty.png")

    def test_collage_grid_size(self, generator, sample_images, tmp_path):
        output = generator.create_collage(sample_images, str(tmp_path), "grid.png", grid_size=2)
        assert os.path.exists(output)
