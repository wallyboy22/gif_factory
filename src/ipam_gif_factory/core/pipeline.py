import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import ee
from PIL import Image as PILImage

from ..config import ConfigLoader
from ..core import (
    DatasetManager,
    TerritoryManager,
    VisualizationManager,
    GIFGenerator,
    FrameProcessor,
)
from ..core.ee_downloader import EEDownloader
from ..core.ee_transforms import run_processor, PROCESSOR_REGISTRY, only_coverage
from ..core.state_manager import StateManager
from ..utils.file_utils import ensure_dir


class Pipeline:
    """Orquestrador completo do pipeline: download -> processar -> GIF."""

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.datasets = DatasetManager(config)
        self.territories = TerritoryManager(config)
        self.visualizations = VisualizationManager(config)
        self.downloader = EEDownloader(config)
        self.gif_generator = GIFGenerator(
            frame_duration=config.get_processing_config("gif_creation").get("frame_duration", 300),
            loop_count=config.get_processing_config("gif_creation").get("loop_count", 0),
            quality=config.get_processing_config("gif_creation").get("quality", 95),
        )
        self.frame_processor = FrameProcessor()

    def run(
        self,
        dataset_id: str,
        product_id: str,
        territory_id: str,
        viz_key: Optional[str] = None,
        output_dir: Optional[str] = None,
        create_collage: bool = True,
        add_labels: bool = True,
        vertical_dimension: int = 1560,
        max_bands: int = 0,
        band_names_filter: Optional[List[str]] = None,
        cell_height: int = 300,
        resume: bool = False,
    ) -> Dict[str, Any]:
        result = {
            "dataset": dataset_id,
            "product": product_id,
            "territory": territory_id,
            "status": "started",
            "frames": [],
            "gif_path": None,
        }

        timings = {}
        t_start = time.perf_counter()

        try:
            try:
                ee.Initialize(project=self.config.ee_project_id)
            except Exception:
                pass
            product_info = self.datasets.get_product(dataset_id, product_id)
            territory_info = self.territories.get_territory(territory_id)
            region_fc = self.territories.get_feature_collection(territory_id)
            overlay_fc = self.territories.get_overlay_fc(territory_id)

            if region_fc is None:
                return {**result, "status": "error", "error": "EE não disponível"}

            bounds_ee = region_fc.geometry().bounds().getInfo()
            coords = bounds_ee['coordinates'][0]
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            bounds = {
                'lon_min': min(lons), 'lon_max': max(lons),
                'lat_min': min(lats), 'lat_max': max(lats),
            }

            if not viz_key:
                viz_key = product_info.get("visualization")
            if not viz_key:
                viz_key = "fire"
            viz_params = self.visualizations.get_viz_params(viz_key)

            if not output_dir:
                output_dir = os.path.join(
                    self.config.get_output_dir(),
                    dataset_id,
                    product_id,
                    territory_id,
                )
            ensure_dir(output_dir)

            state = StateManager(output_dir)
            if not resume:
                state.clear_all()

            print(f"\n{'='*60}")
            print(f"Pipeline: {product_info.get('name', product_id)}")
            print(f"Território: {territory_info['name']}")
            print(f"Visualização: {viz_params.get('name', viz_key)}")
            print(f"Saída: {output_dir}")
            if resume:
                print(f"Modo: resume (pulando etapas ja concluidas)")
            print(f"{'='*60}")

            image = self._load_product_image(product_info)

            bands_slice = product_info.get("bands_slice")
            if bands_slice and len(bands_slice) == 2:
                image = image.slice(bands_slice[0], bands_slice[1])
                print(f"Bandas fatiadas: [{bands_slice[0]}:{bands_slice[1]}]")

            real_band_names = self.downloader.get_band_names(image)
            yaml_bands = product_info.get("bands", [])
            if yaml_bands:
                valid = [b for b in yaml_bands if b in real_band_names]
                if valid:
                    band_names = valid
                else:
                    band_names = real_band_names
            else:
                band_names = real_band_names
            if band_names_filter:
                band_names = [b for b in band_names if any(b.endswith(s) for s in band_names_filter)]
                print(f"  Filtradas para anos específicos: {band_names_filter}")
            if max_bands > 0 and len(band_names) > max_bands:
                band_names = band_names[:max_bands]
            print(f"Bandas: {len(band_names)} (de {len(real_band_names)} disponíveis)")

            is_rgb = product_info.get("rgb", False)
            rgb_band_groups = None
            if is_rgb:
                groups = {}
                for b in band_names:
                    match = re.search(r'(\d{4})$', b)
                    if match:
                        year = match.group(1)
                        if year not in groups:
                            groups[year] = []
                        groups[year].append(b)
                CHANNEL_ORDER = {'swir1': 0, 'nir': 1, 'red': 2}
                rgb_band_groups = [
                    (y, sorted(grp, key=lambda b: CHANNEL_ORDER.get(b.split('_')[0], 99)))
                    for y, grp in sorted(groups.items())
                ]

            self.downloader.vertical_dimension = vertical_dimension
            prefix = f"{product_id}_"

            if not state.is_complete("download"):
                print(f"\n[1/4] Baixando frames...")
                t1 = time.perf_counter()
                if is_rgb and rgb_band_groups:
                    frame_paths = self.downloader.download_rgb_frames(
                        image=image,
                        band_groups=rgb_band_groups,
                        viz_params=viz_params,
                        region_fc=region_fc,
                        output_dir=output_dir,
                        prefix=prefix,
                        overlay_fc=overlay_fc,
                    )
                else:
                    frame_paths = self.downloader.download_frames(
                        image=image,
                        band_names=band_names,
                        viz_params=viz_params,
                        region_fc=region_fc,
                        output_dir=output_dir,
                        prefix=prefix,
                    add_labels=add_labels,
                    overlay_fc=overlay_fc,
                )
                timings["download"] = round(time.perf_counter() - t1, 1)
                print(f"  ({timings['download']}s)")

                if not frame_paths:
                    return {**result, "status": "error", "error": "Nenhum frame baixado"}

                result["frames"] = frame_paths

                for fp in frame_paths:
                    if not os.path.exists(fp):
                        return {**result, "status": "error", "error": f"Frame faltando apos download: {fp}"}

                state.mark_complete("download")
            else:
                completed = state.get_completed()
                print(f"\n[1/4] Download ja concluido (resume)")
                frame_paths = self._load_existing_frames(output_dir, f"{product_id}_")
                result["frames"] = frame_paths
                timings["download"] = 0

            if not state.is_complete("resize"):
                print(f"\n[2/4] Redimensionando frames...")
                t2 = time.perf_counter()
                FrameProcessor.batch_resize(frame_paths, vertical_dimension)
                timings["resize"] = round(time.perf_counter() - t2, 1)
                print(f"  ({timings['resize']}s)")
                state.mark_complete("resize")
            else:
                print(f"\n[2/4] Redimensionamento ja concluido (resume)")
                timings["resize"] = 0

            product_label = product_info.get("name", product_id)
            territory_name = territory_info["name"]
            dataset_desc = product_info.get("dataset_description", dataset_id)
            title_line1 = f"{product_label} \u00b7 {territory_name}"
            title_line2 = dataset_desc

            label_map = {}
            for fp in frame_paths:
                band_name = os.path.splitext(os.path.basename(fp))[0]
                if band_name.startswith(prefix):
                    band_name = band_name[len(prefix):]
                year_part = re.sub(r"^[a-z_]+", "", band_name).replace("_", "\u2192")
                label_map[fp] = year_part

            if create_collage:
                collage_filename = f"{product_id}_{territory_id}_collage.png"
                collage_path = os.path.join(output_dir, collage_filename)
                cell_year_labels = [label_map.get(fp, "") for fp in frame_paths]

                if add_labels:
                    if not state.is_complete("collage_scale_north"):
                        print(f"\n[3a/4] Adicionando escala e norte aos frames...")
                        t3a = time.perf_counter()
                        FrameProcessor.batch_add_bottom_bars(frame_paths, bounds['lon_min'], bounds['lon_max'], bounds['lat_min'], bounds['lat_max'], palette=viz_params.get("palette", ["fdfdfd", "800000"]), vmin=viz_params.get("min", 0), vmax=viz_params.get("max", 1), font_size=50, discrete_labels=viz_params.get("discrete_labels"), cmap_type=viz_params.get("cmap_type", "sequential"), show_legend=False, show_scale=True)
                        timings["collage_scale_north"] = round(time.perf_counter() - t3a, 1)
                        print(f"    escala/norte: {timings['collage_scale_north']}s")
                        state.mark_complete("collage_scale_north")
                    else:
                        print(f"\n[3a/4] Escala/norte ja adicionados (resume)")
                        timings["collage_scale_north"] = 0

                if not state.is_complete("collage"):
                    print(f"\n[3b/4] Criando colagem...")
                    t3b = time.perf_counter()
                    collage_path = self.gif_generator.create_collage(
                        image_paths=frame_paths,
                        output_dir=output_dir,
                        filename=collage_filename,
                        cell_labels=cell_year_labels,
                        font_path=FrameProcessor.FONT_PATH,
                        cell_height=cell_height,
                    )
                    timings["collage_build"] = round(time.perf_counter() - t3b, 1)
                    print(f"    grid: {timings['collage_build']}s")
                    state.mark_complete("collage")
                else:
                    print(f"\n[3b/4] Colagem ja criada (resume)")
                    timings["collage_build"] = 0

                if add_labels:
                    if not state.is_complete("collage_labels"):
                        print(f"\n[3c/4] Adicionando titulo e legenda ao grid...")
                        t3c = time.perf_counter()
                        FrameProcessor.add_year_label(collage_path, title_line1, position="top_left", font_size=34, padding_top=130, bar_color=(255, 255, 255), text_color=(0, 0, 0), subtitle=title_line2, subtitle_size=30)
                        FrameProcessor.add_bottom_bar(collage_path, bounds['lon_min'], bounds['lon_max'], bounds['lat_min'], bounds['lat_max'], palette=viz_params.get("palette", ["fdfdfd", "800000"]), vmin=viz_params.get("min", 0), vmax=viz_params.get("max", 1), font_size=60, discrete_labels=viz_params.get("discrete_labels"), cmap_type=viz_params.get("cmap_type", "sequential"), show_legend=True, show_scale=True)
                        FrameProcessor.add_margin(collage_path, 30)
                        timings["collage_labels"] = round(time.perf_counter() - t3c, 1)
                        print(f"    titulo/legenda: {timings['collage_labels']}s")
                        state.mark_complete("collage_labels")
                    else:
                        print(f"\n[3c/4] Titulo/legenda do grid ja adicionados (resume)")
                        timings["collage_labels"] = 0

                result["collage_path"] = collage_path
                print(f"  Colagem: {collage_path}")

            if add_labels:
                if not state.is_complete("frame_margins"):
                    print(f"  Adicionando margens...")
                    t_marg = time.perf_counter()
                    FrameProcessor.batch_add_margins(frame_paths, 30)
                    timings["frame_margins"] = round(time.perf_counter() - t_marg, 1)
                    print(f"    margens: {timings['frame_margins']}s")
                    state.mark_complete("frame_margins")
                else:
                    timings["frame_margins"] = 0

                if not state.is_complete("frame_headers"):
                    print(f"\n[3d/4] Adicionando titulo aos frames...")
                    t4a = time.perf_counter()
                    FrameProcessor.batch_add_frame_headers(frame_paths, title_line1, label_map, line1_size=36, line2_size=80, padding_top=220, gap=10, subtitle=title_line2, subtitle_size=22)
                    timings["frame_headers"] = round(time.perf_counter() - t4a, 1)
                    print(f"    headers: {timings['frame_headers']}s")
                    state.mark_complete("frame_headers")
                else:
                    timings["frame_headers"] = 0

                if not state.is_complete("frame_bottom_bars"):
                    print(f"  Adicionando legenda aos frames...")
                    t4b = time.perf_counter()
                    FrameProcessor.batch_add_bottom_bars(frame_paths, bounds['lon_min'], bounds['lon_max'], bounds['lat_min'], bounds['lat_max'], palette=viz_params.get("palette", ["fdfdfd", "800000"]), vmin=viz_params.get("min", 0), vmax=viz_params.get("max", 1), font_size=50, discrete_labels=viz_params.get("discrete_labels"), cmap_type=viz_params.get("cmap_type", "sequential"), show_legend=True, show_scale=True)
                    timings["frame_bottom_bars"] = round(time.perf_counter() - t4b, 1)
                    print(f"    legendas: {timings['frame_bottom_bars']}s")
                    state.mark_complete("frame_bottom_bars")
                else:
                    timings["frame_bottom_bars"] = 0

            if create_collage or add_labels:
                if not state.is_complete("gif"):
                    print(f"\n[4/4] Criando GIF...")
                    t5 = time.perf_counter()
                    frame_ms = self.config.get_processing_config("gif_creation").get("frame_duration", 300)
                    secs = frame_ms / 1000
                    sec_str = f"{secs:.1f}s".replace(".", "_")
                    gif_filename = f"{product_id}_{territory_id}_{sec_str}.gif"
                    gif_path = self.gif_generator.create_gif(
                        image_paths=frame_paths,
                        output_dir=output_dir,
                        filename=gif_filename,
                        sort_frames=True,
                    )
                    timings["gif_creation"] = round(time.perf_counter() - t5, 1)
                    print(f"  ({timings['gif_creation']}s)")
                    result["gif_path"] = gif_path
                    result["status"] = "success"
                    print(f"  GIF: {gif_path}")
                    state.mark_complete("gif")
                else:
                    print(f"\n[4/4] GIF ja criado (resume)")
                    timings["gif_creation"] = 0
                    gif_path = result.get("gif_path")

            if not result.get("gif_path"):
                gif_path = self._find_existing_gif(output_dir, product_id, territory_id)
                result["gif_path"] = gif_path

            result["status"] = "success"
            print(f"\nSalvando metadados...")
            t6 = time.perf_counter()
            timings["total"] = round(time.perf_counter() - t_start, 1)
            metadata = self._build_metadata(
                dataset_id=dataset_id,
                product_id=product_id,
                product_info=product_info,
                territory_id=territory_id,
                territory_info=territory_info,
                viz_key=viz_key,
                viz_params=viz_params,
                gif_path=gif_path,
                frame_paths=frame_paths,
                output_dir=output_dir,
                timings=timings,
            )
            self._save_metadata_json(metadata, output_dir, product_id)
            timings["metadata_save"] = round(time.perf_counter() - t6, 1)
            result["metadata"] = metadata

            print(f"\n{'='*60}")
            print(f"Pipeline concluido com sucesso!")
            print(f"Frames: {len(frame_paths)}")
            print(f"GIF: {gif_path}")
            print(f"\nTempos:")
            for phase, secs in timings.items():
                if secs:
                    print(f"  {phase}: {secs}s")
            print(f"{'='*60}")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"\n  [ERRO] Pipeline falhou: {e}")

        return result

    def _load_product_image(self, product_info: Dict[str, Any]) -> Any:
        import ee

        asset_id = product_info.get("asset", "")
        processor_name = product_info.get("processor")

        if processor_name:
            return run_processor(processor_name)
        if not asset_id:
            raise ValueError(f"Produto sem asset_id: {product_info.get('id')}")

        asset_type = product_info.get("asset_type", "image")
        mosaic = product_info.get("mosaic", False)
        mask_value = product_info.get("mask_value")

        return self.downloader.load_image(asset_id, asset_type, mosaic, mask_value)

    def _describe_processor(self, processor_name: Optional[str]) -> Optional[Dict[str, Any]]:
        if not processor_name:
            return None
        descs = {
            "build_edge_area":        {"processing": "empilhamento hierárquico de bordas (30-1000m)", "divide_by": None},
            "build_fragment_size":    {"processing": "empilhamento hierárquico de tamanhos (3-75ha)", "divide_by": None},
            "build_distance_100ha":   {"processing": "distância de isolamento para fragmentos >100ha", "divide_by": None},
            "build_distance_500ha":   {"processing": "distância de isolamento para fragmentos >500ha", "divide_by": None},
            "build_distance_1000ha":  {"processing": "distância de isolamento para fragmentos >1000ha", "divide_by": None},
            "build_secondary_vegetation_coverage": {"processing": "mod 100 (cobertura VS)", "divide_by": None, "mod_by": 100},
            "build_secondary_vegetation_age":      {"processing": "÷ 100 (idade VS)", "divide_by": 100},
            "build_fire_frequency":   {"processing": "÷ 100 (frequência de fogo col9)", "divide_by": 100},
            "build_fire_age":         {"processing": "÷ 100 (idade do fogo col9)", "divide_by": 100},
            "build_accumulated_burned_coverage":   {"processing": "mod 100 (cobertura queimada)", "divide_by": None, "mod_by": 100},
            "decode_fire_frequency_col101":        {"processing": "÷ 100, round (frequência col10.1)", "divide_by": 100},
            "decode_fire_age_col101":              {"processing": "÷ 100, round (idade fogo col10.1)", "divide_by": 100},
            "decode_secondary_vegetation_age_col101": {"processing": "÷ 100, round (idade VS col10.1)", "divide_by": 100},
            "build_secondary_vegetation_coverage_col101": {"processing": "mod 100 (cobertura VS col10.1)", "divide_by": None, "mod_by": 100},
            "build_fire_frequency_coverage_col101": {"processing": "mod 100 (cobertura freq fogo col10.1)", "divide_by": None, "mod_by": 100},
            "build_burned_natural_coverage_col101": {"processing": "mod 100, masked by freq≥1 (cobertura em áreas queimadas)", "divide_by": None},
            "build_burned_at_least_once_col101": {"processing": "÷ 100, ternary (0=não queimado, 1=recorrente, 2=primeira vez)", "divide_by": 100},
            "decode_edge_area_col101": {"processing": "reclassifica distância contínua em 8 bins (≤30 a ≤1000m), unmask=0 (cinza)", "divide_by": None},
            "decode_edge_age_col101": {"processing": "unmask(0) para fundo cinza, valores originais preservados (1-40 anos)", "divide_by": None},
            "decode_morphology_col101": {"processing": "unmask(0) para fundo cinza, valores originais preservados (1-6)", "divide_by": None},
            "decode_patch_id_col101": {"processing": "unmask(0) para fundo cinza, randomVisualizer para cores distintas por fragmento", "divide_by": None},
            "decode_patch_size_col101": {"processing": "unmask(0) para fundo cinza, valores 0-11 (tamanho do fragmento)", "divide_by": None},
            "decode_patch_size_fragments_col101": {"processing": "discretiza 0-10k ha em 10 bins + unmask(0)", "divide_by": None},
            "decode_patch_size_massifs_col101": {"processing": "discretiza >10k ha em 10 bins + unmask(0)", "divide_by": None},
            "decode_canopy_disturbance_col101": {"processing": "unmask(0) para fundo cinza, valores 0-12 (frequência de distúrbio de dossel)", "divide_by": None},
            "decode_logging_col101": {"processing": "unmask(0) para fundo cinza, binário corte seletivo", "divide_by": None},
            "build_natural_coverage_col101": {"processing": "remapa cobertura MapBiomas col10.1 para classes naturais (1=floresta, 2=não-florestal), demais=0", "divide_by": None},
        }
        return descs.get(processor_name, {"processing": processor_name, "divide_by": None})

    def _build_metadata(
        self,
        dataset_id: str,
        product_id: str,
        product_info: Dict[str, Any],
        territory_id: str,
        territory_info: Dict[str, Any],
        viz_key: str,
        viz_params: Dict[str, Any],
        gif_path: str,
        frame_paths: List[str],
        output_dir: str,
        timings: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        processor_name = product_info.get("processor")
        asset_id = product_info.get("asset", "")
        processor_desc = self._describe_processor(processor_name)

        def _file_size_mb(path):
            try:
                return round(os.path.getsize(path) / (1024 * 1024), 2)
            except (OSError, TypeError):
                return None

        frame_sizes = {}
        total_frames_mb = 0.0
        for fp in frame_paths:
            mb = _file_size_mb(fp)
            if mb is not None:
                frame_sizes[os.path.basename(fp)] = mb
                total_frames_mb += mb

        gif_size_mb = _file_size_mb(gif_path)

        collage_filename = f"{product_id}_{territory_id}_collage.png"
        collage_path = os.path.join(output_dir, collage_filename)
        collage_size_mb = _file_size_mb(collage_path)

        metadata = {
            "metadata_version": "1.1",
            "generated_at": datetime.now().isoformat(),
            "dataset": {
                "id": dataset_id,
                "description": product_info.get("dataset_description", ""),
                "source": product_info.get("dataset_source", ""),
            },
            "product": {
                "id": product_id,
                "name": product_info.get("name", product_id),
                "asset": asset_id,
                "asset_type": product_info.get("asset_type", "image"),
                "bands": product_info.get("bands", []),
                "bands_slice": product_info.get("bands_slice"),
                "temporal_range": product_info.get("temporal_range"),
            },
            "processor": {
                "name": processor_name,
                "description": processor_desc.get("processing") if processor_desc else None,
                "divide_by": processor_desc.get("divide_by") if processor_desc else None,
            },
            "visualization": {
                "key": viz_key,
                "name": viz_params.get("name", viz_key),
                "cmap_type": viz_params.get("cmap_type", "sequential"),
                "min": viz_params.get("min", 0),
                "max": viz_params.get("max", 1),
                "palette": viz_params.get("palette", []),
                "label": viz_params.get("label", ""),
                "unit": viz_params.get("unit", ""),
            },
            "territory": {
                "id": territory_id,
                "name": territory_info.get("name", territory_id),
            },
            "output": {
                "gif_path": gif_path,
                "gif_relative_path": os.path.relpath(gif_path, output_dir) if gif_path else None,
                "frames_count": len(frame_paths),
                "frames": [os.path.basename(f) for f in frame_paths],
                "frame_duration_ms": self.config.get_processing_config("gif_creation").get("frame_duration", 300),
            },
            "files": {
                "gif_size_mb": gif_size_mb,
                "collage_size_mb": collage_size_mb,
                "frames_total_mb": round(total_frames_mb, 2),
                "frames_count": len(frame_paths),
                "frames_sizes_mb": frame_sizes,
            },
        }

        if timings:
            metadata["timing"] = {
                "phases": {k: v for k, v in timings.items() if k != "total"},
                "total_seconds": timings.get("total"),
                "total_formatted": self._format_seconds(timings.get("total", 0)),
            }

        if frame_paths:
            try:
                first = PILImage.open(frame_paths[0])
                w, h = first.size
                pixels_per_frame = w * h
                total_pixels = pixels_per_frame * len(frame_paths)
                metadata["ee_estimate"] = {
                    "frame_dimensions": {"width": w, "height": h},
                    "pixels_per_frame": pixels_per_frame,
                    "total_pixels_processed": total_pixels,
                    "gee_thumbnail_requests": len(frame_paths),
                }

                tile_size = 256 * 256
                tile_equivalent = total_pixels / tile_size
                complexity_factor = self._processor_complexity(product_info.get("processor"))
                eecu = round(tile_equivalent * 0.001 * complexity_factor, 4)
                eecu_hours = round(eecu / 3600, 6)
                metadata["ee_estimate"]["tile_equivalent"] = round(tile_equivalent, 1)
                metadata["ee_estimate"]["complexity_factor"] = complexity_factor
                metadata["ee_estimate"]["estimated_eecu"] = eecu
                metadata["ee_estimate"]["estimated_eecu_hours"] = eecu_hours
            except Exception:
                pass

        return metadata

    @staticmethod
    def _processor_complexity(processor_name: Optional[str]) -> float:
        if not processor_name:
            return 1.0
        simple = {
            "decode_fire_frequency_col101",
            "decode_fire_age_col101",
            "decode_secondary_vegetation_age_col101",
            "build_fire_frequency_coverage_col101",
            "decode_edge_area_col101",
            "decode_edge_age_col101",
            "decode_morphology_col101",
            "decode_patch_id_col101",
            "decode_patch_size_col101",
            "decode_patch_size_fragments_col101",
            "decode_patch_size_massifs_col101",
        }
        moderate = {
            "build_secondary_vegetation_coverage_col101",
            "build_secondary_vegetation_coverage",
            "build_secondary_vegetation_age",
            "build_burned_natural_coverage_col101",
            "build_primary_natural_coverage_col101",
        }
        if processor_name in simple:
            return 1.0
        if processor_name in moderate:
            return 1.5
        return 2.0

    @staticmethod
    def _format_seconds(total_secs: float) -> str:
        mins = int(total_secs // 60)
        secs = int(total_secs % 60)
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"

    @staticmethod
    def _load_existing_frames(output_dir: str, prefix: str) -> List[str]:
        import glob as glob_mod
        pattern = os.path.join(output_dir, f"{prefix}*.png")
        paths = sorted(glob_mod.glob(pattern))
        if not paths:
            raise FileNotFoundError(f"Nenhum frame existente encontrado em {output_dir}/{prefix}*.png")
        return paths

    @staticmethod
    def _find_existing_gif(output_dir: str, product_id: str, territory_id: str) -> Optional[str]:
        import glob as glob_mod
        pattern = os.path.join(output_dir, f"{product_id}_{territory_id}_*.gif")
        gifs = sorted(glob_mod.glob(pattern))
        return gifs[-1] if gifs else None

    @staticmethod
    def _save_metadata_json(metadata: Dict[str, Any], output_dir: str, product_id: str) -> str:
        filename = f"metadata_{product_id}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"  Metadata salvo: {filepath}")
        return filepath

    def run_batch(self, combinations: List[Tuple[str, str, str, Optional[str]]],
                  output_dir: Optional[str] = None,
                  cell_height: int = 300,
                  resume: bool = False) -> List[Dict[str, Any]]:
        results = []
        for combo in combinations:
            dataset_id, product_id, territory_id = combo[:3]
            viz_key = combo[3] if len(combo) > 3 else None
            result = self.run(dataset_id, product_id, territory_id, viz_key, output_dir,
                            cell_height=cell_height, resume=resume)
            results.append(result)
        return results

    def list_available(self) -> Dict[str, List[str]]:
        available = {}
        for ds in self.datasets.list_datasets():
            ds_id = ds["id"]
            products = self.datasets.list_products(ds_id)
            available[ds_id] = [p["id"] for p in products]
        return available
