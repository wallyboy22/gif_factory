import sys
sys.path.insert(0, "src")

from ipam_gif_factory.config import ConfigLoader
from ipam_gif_factory.core.pipeline import Pipeline

config = ConfigLoader().load_all()
pipeline = Pipeline(config)

# Test fire frequency
result = pipeline.run(
    dataset_id="brasil_fire_col3",
    product_id="fire_frequency",
    territory_id="df",
    viz_key="frequency",
    create_collage=False,
    add_labels=True,
    vertical_dimension=600,
)
print("")
print("=" * 50)
print(f"Produto: Fire Frequency")
print(f"Status: {result['status']}")
if result.get("frames"):
    print(f"Frames: {len(result['frames'])}")
if result.get("gif_path"):
    print(f"GIF: {result['gif_path']}")
if result.get("error"):
    print(f"Erro: {result['error']}")
