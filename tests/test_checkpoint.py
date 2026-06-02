import sys, os, time
sys.path.insert(0, "src")
from ipam_gif_factory.config import ConfigLoader
from ipam_gif_factory.core.pipeline import Pipeline
from ipam_gif_factory.core.state_manager import StateManager

config = ConfigLoader().load_all()
pipeline = Pipeline(config)

DATASET = "brasil_degradation_col10_1"
PROD = "fire_frequency"
TERR = "cerrado"

output_dir = os.path.join(config.get_output_dir(), DATASET, PROD, TERR)

# Test 1: Resume on a completed product (must skip ALL steps)
print("=== TEST 1: resume on completed product ===")
t0 = time.perf_counter()
r = pipeline.run(
    dataset_id=DATASET, product_id=PROD, territory_id=TERR,
    create_collage=True, add_labels=True, vertical_dimension=1560,
    resume=True,
)
dt = time.perf_counter() - t0
print(f"Status: {r['status']} | Tempo: {dt:.1f}s")
if dt < 10:
    print("OK: resume pulou todas as etapas")
else:
    print(f"ATENCAO: demorou {dt:.1f}s - algo foi reprocessado")

# Test 2: Check state files exist
state = StateManager(output_dir)
completed = state.get_completed()
print(f"\nStates encontrados: {completed}")
expected = {"download", "resize", "collage_scale_north", "collage_margins",
            "collage", "collage_labels", "frame_headers", "frame_bottom_bars", "gif"}
missing = expected - set(completed)
if missing:
    print(f"FALTANDO: {missing}")
else:
    print("OK: todos os 9 states estao presentes")

print("\nTestes concluidos!")
