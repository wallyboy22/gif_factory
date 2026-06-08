import argparse
import sys
sys.path.insert(0, "src")

from ipam_gif_factory.config import ConfigLoader
from ipam_gif_factory.core.pipeline import Pipeline

parser = argparse.ArgumentParser(description="Teste rápido do pipeline (DF)")
parser.add_argument("--dataset", type=str, default="brasil_fire_col5", help="ID do dataset")
parser.add_argument("--product", type=str, default="annual_burned", help="ID do produto")
parser.add_argument("--viz", type=str, default=None, help="Chave de visualização")
parser.add_argument("--font-scale", type=float, default=1.0, help="Escala das fontes")
args = parser.parse_args()

config = ConfigLoader().load_all()
pipeline = Pipeline(config)

result = pipeline.run(
    dataset_id=args.dataset,
    product_id=args.product,
    territory_id="df",
    viz_key=args.viz,
    create_collage=True,
    add_labels=True,
    vertical_dimension=600,
    font_scale=args.font_scale,
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
