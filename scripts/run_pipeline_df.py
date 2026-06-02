import sys
sys.path.insert(0, "src")

from ipam_gif_factory.config import ConfigLoader
from ipam_gif_factory.core.pipeline import Pipeline

config = ConfigLoader().load_all()
pipeline = Pipeline(config)

result = pipeline.run(
    dataset_id="brasil_fire_col3",
    product_id="annual_burned",
    territory_id="df",
    viz_key="fire",
    create_collage=True,
    add_labels=True,
    vertical_dimension=600,
)
print("")
print("=" * 50)
print(f"Status: {result['status']}")
if result.get("frames"):
    print(f"Frames baixados: {len(result['frames'])}")
if result.get("gif_path"):
    print(f"GIF gerado: {result['gif_path']}")
if result.get("collage_path"):
    print(f"Colagem: {result['collage_path']}")
if result.get("error"):
    print(f"Erro: {result['error']}")
print("=" * 50)
