import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from affine import Affine
from PIL import Image as PILImage

from ..config import ConfigLoader
from ..core import TerritoryManager


class GeoPDFBuilder:
    """Cria GeoTIFF e GeoPDF a partir de PNGs do pipeline + bounds do território."""

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.territories = TerritoryManager(config)

    def _get_bounds(self, territory_id: str) -> Dict[str, float]:
        bbox = self.territories.get_bbox(territory_id)
        if bbox and len(bbox) == 4:
            return {
                "lon_min": bbox[0],
                "lat_min": bbox[1],
                "lon_max": bbox[2],
                "lat_max": bbox[3],
            }
        try:
            import ee
            try:
                ee.Initialize(project=self.config.ee_project_id)
            except Exception:
                pass
            fc = self.territories.get_feature_collection(territory_id)
            if fc is None:
                raise ValueError(f"Não foi possível carregar FeatureCollection para '{territory_id}'")
            bounds_ee = fc.geometry().bounds().getInfo()
            coords = bounds_ee["coordinates"][0]
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            return {
                "lon_min": min(lons),
                "lon_max": max(lons),
                "lat_min": min(lats),
                "lat_max": max(lats),
            }
        except Exception as e:
            raise RuntimeError(
                f"Não foi possível calcular bounds para '{territory_id}': {e}. "
                "Defina bbox explícito no YAML do território."
            ) from e

    @staticmethod
    def _compute_geotransform(
        bounds: Dict[str, float], width: int, height: int
    ) -> Affine:
        lon_res = (bounds["lon_max"] - bounds["lon_min"]) / width
        lat_res = (bounds["lat_min"] - bounds["lat_max"]) / height
        return Affine(lon_res, 0.0, bounds["lon_min"], 0.0, lat_res, bounds["lat_max"])

    def create_geotiff(
        self, png_path: str, bounds: Dict[str, float], output_path: str,
        crop_box: Optional[Tuple[int, int, int, int]] = None,
    ) -> str:
        img = PILImage.open(png_path).convert("RGB")
        if crop_box:
            img = img.crop(crop_box)
        data = np.array(img)
        h, w = data.shape[:2]
        if data.ndim == 3 and data.shape[2] == 3:
            data = np.moveaxis(data, 2, 0)
        else:
            data = np.expand_dims(data, 0)

        transform = self._compute_geotransform(bounds, w, h)

        import rasterio

        with rasterio.open(
            output_path,
            "w",
            driver="GTiff",
            height=h,
            width=w,
            count=data.shape[0],
            dtype=rasterio.uint8,
            crs="EPSG:4326",
            transform=transform,
            compress="DEFLATE",
        ) as dst:
            dst.write(data)

        return output_path

    def _find_gdal_translate(self) -> Optional[str]:
        candidates = ["gdal_translate", "gdal_translate.exe"]
        for prog in candidates:
            try:
                r = subprocess.run(
                    [prog, "--version"],
                    capture_output=True, timeout=10,
                )
                if r.returncode == 0:
                    return prog
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        rio_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        site_pkg = os.path.dirname(rio_dir)
        for root, dirs, files in os.walk(os.path.join(site_pkg, "rasterio")):
            for f in files:
                if f.lower() in ("gdal_translate.exe", "gdal_translate"):
                    return os.path.join(root, f)
        return None

    def create_geopdf(
        self, geotiff_path: str, output_path: str
    ) -> Optional[str]:
        gdal_translate = self._find_gdal_translate()
        if gdal_translate is None:
            return None
        try:
            result = subprocess.run(
                [gdal_translate, "-of", "PDF", geotiff_path, output_path],
                capture_output=True, timeout=120,
            )
            if result.returncode == 0:
                return output_path
        except Exception:
            pass
        return None

    def process_frame(
        self,
        png_path: str,
        territory_id: str,
        bounds: Optional[Dict[str, float]] = None,
        output_dir: Optional[str] = None,
        crop_box: Optional[Tuple[int, int, int, int]] = None,
    ) -> Dict[str, Any]:
        if bounds is None:
            bounds = self._get_bounds(territory_id)

        base = os.path.splitext(png_path)[0]
        if output_dir is None:
            output_dir = os.path.dirname(png_path)

        geotiff_path = os.path.join(output_dir, os.path.basename(base) + "_geo.tif")
        geopdf_path = os.path.join(output_dir, os.path.basename(base) + "_geopdf.pdf")

        result = {
            "png": png_path,
            "geotiff": None,
            "geopdf": None,
            "status": "ok",
        }

        try:
            geotiff_path = self.create_geotiff(png_path, bounds, geotiff_path, crop_box=crop_box)
            result["geotiff"] = geotiff_path
        except Exception as e:
            result["status"] = "error"
            result["error_geotiff"] = str(e)
            return result

        try:
            geopdf = self.create_geopdf(geotiff_path, geopdf_path)
            result["geopdf"] = geopdf
        except Exception as e:
            result["error_geopdf"] = str(e)

        if result["geopdf"] is None and result["geotiff"] is not None:
            if os.path.exists(geotiff_path):
                result["note"] = "GeoPDF não gerado (GDAL CLI indisponível). GeoTIFF criado."

        return result

    def process_product(
        self,
        output_dir: str,
        product_id: str,
        territory_id: str,
        bounds: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        metadata_path = os.path.join(output_dir, f"metadata_{product_id}.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Metadata não encontrado: {metadata_path}")

        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)

        frame_names = metadata.get("output", {}).get("frames", [])
        png_paths = [os.path.join(output_dir, fn) for fn in frame_names]

        if bounds is None:
            bounds = self._get_bounds(territory_id)

        crop_box = None
        fl = metadata.get("frame_layout")
        if fl:
            lox = fl.get("map_offset_x", 30)
            loy = fl.get("map_offset_y", 260)
            w = fl.get("map_width")
            h = fl.get("map_height")
            if w is not None and h is not None:
                crop_box = (lox, loy, lox + w, loy + h)

        results = []
        for png_path in png_paths:
            if os.path.exists(png_path):
                r = self.process_frame(
                    png_path, territory_id, bounds=bounds,
                    output_dir=output_dir, crop_box=crop_box,
                )
                results.append(r)

        return results

    def process_all(
        self,
        dataset_id: Optional[str] = None,
        product_id: Optional[str] = None,
        territory_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        from ..core import DatasetManager
        dm = DatasetManager(self.config)
        output_base = self.config.get_output_dir()

        if dataset_id:
            datasets = [d for d in dm.list_datasets() if d["id"] == dataset_id]
        else:
            datasets = dm.list_datasets()

        results = []
        for ds in datasets:
            if product_id:
                products = [p for p in dm.list_products(ds["id"]) if p["id"] == product_id]
            else:
                products = dm.list_products(ds["id"])

            territory_list = self.territories.list_territories()
            if territory_id:
                territory_list = [t for t in territory_list if t["id"] == territory_id]

            for prod in products:
                for terr in territory_list:
                    dir_path = os.path.join(output_base, ds["id"], prod["id"], terr["id"])
                    meta_path = os.path.join(dir_path, f"metadata_{prod['id']}.json")
                    if not os.path.exists(meta_path):
                        continue
                    try:
                        bounds = self._get_bounds(terr["id"])
                        res = self.process_product(dir_path, prod["id"], terr["id"], bounds=bounds)
                        results.extend(res)
                    except Exception as e:
                        results.append({
                            "status": "error",
                            "dataset": ds["id"],
                            "product": prod["id"],
                            "territory": terr["id"],
                            "error": str(e),
                        })
        return results
