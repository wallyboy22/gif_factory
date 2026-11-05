"""
Gera GIFs mensais de superficie de agua no Pantanal
a partir das imagens de classificacao mensal da Collection 11.

Uso: python scripts/pantanal_agua_mensal.py
"""
import os
import sys
import ee
import requests
import time
from PIL import Image as PILImage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mapbiomas_data.config import ConfigLoader
from mapbiomas_data.core.territory_manager import TerritoryManager
from mapbiomas_data.core.frame_processor import FrameProcessor
from mapbiomas_data.core.gif_generator import GIFGenerator
from mapbiomas_data.utils.file_utils import ensure_dir


ASSET_BASE = "projects/mapbiomas-brazil/assets/LAND-COVER/COLLECTION-11/GENERAL/SAMPLES/PANTANAL/mensal"
ASSET_TEMPLATE = f"{ASSET_BASE}/class_mensal_RF_{{year}}_v2"

ANOS = [1988, 2018]

PALETTE = ["FFFFFF", "519799", "2532e4"]
VIZ_MIN = 0
VIZ_MAX = 2

MESES = [
    "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

VERTICAL_DIMENSION = 2000
FRAME_DURATION = 500


def download_frame(image, band_name, region_fc, filepath):
    band_img = image.select(band_name).remap([33, 11], [2, 1], 0).rename(band_name)

    vis = {
        "min": VIZ_MIN,
        "max": VIZ_MAX,
        "palette": PALETTE,
        "bands": [band_name],
    }

    inside = ee.Image().paint(region_fc, 1).unmask(0).toUint8()

    viz = band_img.unmask().visualize(**vis)

    bg = ee.Image.constant([255, 255, 255]).toUint8().visualize(min=0, max=255)

    result = bg.where(inside.neq(0), viz)

    boundaries = ee.Image().byte().paint(featureCollection=region_fc, color=1, width=1)
    result = result.where(boundaries, 0)

    url = result.getThumbURL({
        "dimensions": str(VERTICAL_DIMENSION),
        "region": region_fc.geometry().bounds(),
    })

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def main():
    config = ConfigLoader("config")
    config.load_all()

    ee.Initialize(project=config.ee_project_id)

    tm = TerritoryManager(config)
    pantanal_fc = tm.get_feature_collection("bioma_pantanal")
    pantanal_info = tm.get_territory("bioma_pantanal")
    print(f"Territorio: {pantanal_info['name']}")

    gif_gen = GIFGenerator(frame_duration=FRAME_DURATION, loop_count=0, quality=95)

    for ano in ANOS:
        print(f"\n{'='*60}")
        print(f"Processando ano {ano}")
        print(f"{'='*60}")

        output_dir = os.path.join(config.get_output_dir(), "pantanal_agua_mensal", str(ano))
        frames_pure_dir = os.path.join(output_dir, "frames_pure")
        frames_clean_dir = os.path.join(output_dir, "frames_clean")
        gifs_dir = os.path.join(output_dir, "gifs")
        ensure_dir(frames_pure_dir)
        ensure_dir(frames_clean_dir)
        ensure_dir(gifs_dir)

        asset = ASSET_TEMPLATE.format(year=ano)
        print(f"Carregando: {asset}")
        image = ee.Image(asset)

        band_names = image.bandNames().getInfo()
        print(f"Bandas ({len(band_names)}):")

        frame_paths = []
        for i, band_name in enumerate(band_names):
            filename = f"{band_name}.png"
            filepath = os.path.join(frames_pure_dir, filename)
            mes = MESES[i]
            print(f"  [{i+1:02d}/12] {band_name} ({mes}) ...", end=" ", flush=True)

            max_attempts = 3
            downloaded = False
            for attempt in range(1, max_attempts + 1):
                try:
                    download_frame(image, band_name, pantanal_fc, filepath)
                    frame_paths.append(filepath)
                    print("OK")
                    downloaded = True
                    break
                except Exception as e:
                    if attempt < max_attempts:
                        wait = 2 ** attempt
                        print(f"RETRY {attempt}...", end=" ", flush=True)
                        time.sleep(wait)
                    else:
                        print(f"FALHA: {e}")

            if not downloaded:
                print(f"  ERRO: nao foi possivel baixar {band_name}")

        if not frame_paths:
            print(f"  ERRO: nenhum frame baixado para {ano}")
            continue

        print(f"\nRedimensionando {len(frame_paths)} frames...")
        FrameProcessor.batch_resize(frame_paths, VERTICAL_DIMENSION)

        print("Adicionando labels...")
        clean_paths = []
        for i, src_path in enumerate(frame_paths):
            month_label = f"{ano} {(i+1):02d}"
            clean_path = os.path.join(frames_clean_dir, os.path.basename(src_path))
            img = PILImage.open(src_path)
            img.save(clean_path)
            img.close()
            FrameProcessor.add_year_only(clean_path, month_label, font_size=100)
            clean_paths.append(clean_path)

        print(f"Criando GIF ({len(clean_paths)} frames)...")
        gif_path = gif_gen.create_gif(
            clean_paths,
            gifs_dir,
            filename=f"pantanal_agua_{ano}.gif",
            sort_frames=True,
            viz_palette=PALETTE,
        )
        print(f"  GIF: {gif_path}")

    print("\nConcluido!")


if __name__ == "__main__":
    main()
