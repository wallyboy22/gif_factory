import glob
import json
import os
from typing import Any, Dict, List, Optional

from ..config import ConfigLoader
from ..core import DatasetManager, GIFGenerator, TerritoryManager
from ..core.frame_processor import FrameProcessor
from .frame_selector import FRAME_MODES, extract_year, select_frames


class SpecialCollageBuilder:
    """Gera collages PNG e GIFs com seleção especial de frames."""

    # grid config por modo
    GRID_CONFIG = {
        "decadal":   {"grid_size": 2},             # 2×2
        "quinzenal": {"force_horizontal": True},    # 3×1
        "first_last": {"force_horizontal": True},   # 2×1
        "last_six":  {"grid_size": 3},             # 3×2
    }

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.datasets = DatasetManager(config)
        self.territories = TerritoryManager(config)
        self.output_base = config.get_output_dir()
        self.gif_generator = GIFGenerator(
            frame_duration=config.get_processing_config("gif_creation").get("frame_duration", 300),
            loop_count=config.get_processing_config("gif_creation").get("loop_count", 0),
            quality=config.get_processing_config("gif_creation").get("quality", 95),
        )

    def _discover_runs(
        self,
        dataset_id: Optional[str] = None,
        product_id: Optional[str] = None,
        territory_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        runs = []
        if not os.path.isdir(self.output_base):
            return runs

        ds_dirs = [os.path.join(self.output_base, ds["id"]) for ds in self.datasets.list_datasets()]
        if dataset_id:
            ds_dirs = [d for d in ds_dirs if os.path.basename(d) == dataset_id]
        ds_dirs = [d for d in ds_dirs if os.path.isdir(d)]

        for ds_dir in ds_dirs:
            ds_id = os.path.basename(ds_dir)
            prod_dirs = sorted([
                os.path.join(ds_dir, p)
                for p in os.listdir(ds_dir)
                if os.path.isdir(os.path.join(ds_dir, p))
            ])
            if product_id:
                prod_dirs = [d for d in prod_dirs if os.path.basename(d) == product_id]

            for prod_dir in prod_dirs:
                prod_id = os.path.basename(prod_dir)
                terr_dirs = sorted([
                    os.path.join(prod_dir, t)
                    for t in os.listdir(prod_dir)
                    if os.path.isdir(os.path.join(prod_dir, t))
                ])
                if territory_id:
                    terr_dirs = [d for d in terr_dirs if os.path.basename(d) == territory_id]

                for terr_dir in terr_dirs:
                    terr_id = os.path.basename(terr_dir)
                    meta_path = os.path.join(terr_dir, f"metadata_{prod_id}.json")
                    if not os.path.isfile(meta_path):
                        continue

                    with open(meta_path, encoding="utf-8") as f:
                        meta = json.load(f)

                    frame_names = meta.get("output", {}).get("frames", [])
                    frame_paths = [os.path.join(terr_dir, fn) for fn in frame_names]
                    frame_paths = [p for p in frame_paths if os.path.isfile(p)]

                    if not frame_paths:
                        continue

                    runs.append({
                        "dataset_id": ds_id,
                        "product_id": prod_id,
                        "territory_id": terr_id,
                        "output_dir": terr_dir,
                        "metadata": meta,
                        "frame_paths": frame_paths,
                    })
        return runs

    @staticmethod
    def _clean_frames(output_dir: str, selected: List[str]) -> List[str]:
        clean_dir = os.path.join(output_dir, "frames_clean")
        if not os.path.isdir(clean_dir):
            return []
        clean_selected = [
            os.path.join(clean_dir, os.path.basename(p)) for p in selected
        ]
        return [p for p in clean_selected if os.path.isfile(p)]

    def _gif_filename(self, product_id: str, territory_id: str, mode: str) -> str:
        return f"{product_id}_{territory_id}_gif_{mode}.gif"

    def _collage_filename(self, product_id: str, territory_id: str, mode: str) -> str:
        return f"{product_id}_{territory_id}_collage_{mode}.png"

    def build_for_run(
        self,
        run: Dict[str, Any],
        mode: str,
        cell_height: int = 300,
    ) -> Dict[str, Any]:
        prod_id = run["product_id"]
        terr_id = run["territory_id"]
        output_dir = run["output_dir"]
        all_frame_paths = run["frame_paths"]
        meta = run["metadata"]

        selected = select_frames(all_frame_paths, mode)
        if not selected:
            return {
                "status": "skipped",
                "product_id": prod_id,
                "territory_id": terr_id,
                "reason": "Nenhum frame selecionado",
            }

        result = {
            "status": "ok",
            "product_id": prod_id,
            "territory_id": terr_id,
            "mode": mode,
            "frames_selected": len(selected),
            "collage_path": None,
            "gif_path": None,
        }

        # GIF usa frames processados (completos, com headers/legendas)
        gif_name = self._gif_filename(prod_id, terr_id, mode)
        try:
            gif_path = self.gif_generator.create_gif(
                image_paths=selected,
                output_dir=output_dir,
                filename=gif_name,
                sort_frames=True,
            )
            result["gif_path"] = gif_path
        except Exception as e:
            result["error_gif"] = str(e)

        # Collage usa frames_clean/ quando disponível (já têm ano estampado)
        using_clean = bool(self._clean_frames(output_dir, selected))
        collage_frames = self._clean_frames(output_dir, selected) or selected
        collage_name = self._collage_filename(prod_id, terr_id, mode)
        short_labels = None if using_clean else [str(extract_year(p) or i + 1) for i, p in enumerate(collage_frames)]

        grid_cfg = self.GRID_CONFIG.get(mode, {})
        try:
            collage_path = self.gif_generator.create_collage(
                image_paths=collage_frames,
                output_dir=output_dir,
                filename=collage_name,
                cell_labels=short_labels,
                cell_height=cell_height,
                grid_size=grid_cfg.get("grid_size"),
                force_horizontal=grid_cfg.get("force_horizontal", False),
            )
            result["collage_path"] = collage_path

            prod_name = meta.get("product", {}).get("name", prod_id)
            terr_name = meta.get("territory", {}).get("name", terr_id)
            title = f"{prod_name} — {terr_name}"

            try:
                FrameProcessor.add_year_label(
                    collage_path, title,
                    position="top_left",
                    font_size=34,
                    padding_top=130,
                    bar_color=(255, 255, 255),
                    text_color=(0, 0, 0),
                )
            except Exception as e:
                result["error_collage_title"] = str(e)

            try:
                FrameProcessor.add_margin(collage_path, 30)
            except Exception as e:
                result["error_collage_margin"] = str(e)

        except Exception as e:
            result["error_collage"] = str(e)

        return result

    def build_all(
        self,
        mode: str,
        dataset_id: Optional[str] = None,
        product_id: Optional[str] = None,
        territory_id: Optional[str] = None,
        cell_height: int = 300,
    ) -> List[Dict[str, Any]]:
        if mode not in FRAME_MODES:
            raise ValueError(f"Modo inválido: {mode}. Opções: {FRAME_MODES}")

        runs = self._discover_runs(dataset_id, product_id, territory_id)
        results = []
        for run in runs:
            res = self.build_for_run(run, mode, cell_height=cell_height)
            results.append(res)
            status_icon = "OK" if res["status"] == "ok" else "SKIP"
            print(f"  [{status_icon}] {run['product_id']}/{run['territory_id']} "
                  f"({res.get('frames_selected', 0)} frames)")
            if res.get("collage_path"):
                print(f"         collage: {os.path.basename(res['collage_path'])}")
            if res.get("gif_path"):
                print(f"         gif:     {os.path.basename(res['gif_path'])}")
        return results
