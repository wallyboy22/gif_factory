"""Area stats export engine — standalone, inspired by toolkit_statisticas.js.

Dispatches a SINGLE ee.batch.Export.table.toCloudStorage per (product, territory)
with ALL years merged into one CSV. No waiting — caller polls later.
"""

from typing import Any, Dict, List, Optional, Tuple

import ee


def export_timeseries_csv(
    img: ee.Image,
    territory_fc: ee.FeatureCollection,
    year_bands: List[Tuple[int, str]],
    product_id: str,
    territory_id: str,
    dataset_id: str,
    bucket_name: str,
    gcs_prefix: str = "",
    selectors: Optional[List[str]] = None,
) -> ee.batch.Task:
    """Export all years of a product as a single CSV to GCS.

    For each (year, band):
        pixelArea + band → reduceRegion(sum.group('class'))
        compute class-0 area as total - sum(other classes)
    Merge all years into one FeatureCollection, export to Cloud Storage.

    Returns the started ``ee.batch.Task``.  Caller **must not wait** — poll later.
    """
    area_img = ee.Image.pixelArea()

    def _process_year(year: int, band_name: str):
        band = img.select(band_name)
        stacked = area_img.addBands(band)

        stats = stacked.reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName="class"),
            geometry=territory_fc,
            scale=30,
            bestEffort=True,
            maxPixels=1e13,
        )
        total = area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=territory_fc,
            scale=30,
            bestEffort=True,
            maxPixels=1e13,
        )
        groups = ee.List(stats.get("groups"))

        def _to_feature(g):
            d = ee.Dictionary(g)
            cls_val = ee.Number(
                ee.Algorithms.If(d.contains("class"), d.get("class"), d.get("group"))
            ).toInt()
            area_sqm = ee.Number(d.get("sum"))
            area_ha = area_sqm.divide(10000)
            return ee.Feature(
                None,
                {
                    "class_value": cls_val,
                    "area_ha": area_ha,
                    "year": ee.Number(year),
                    "dataset": dataset_id,
                    "product": product_id,
                    "territory_id": territory_id,
                },
            )

        fc = ee.FeatureCollection(groups.map(_to_feature))
        total_sqm = ee.Number(total.get("area"))
        sum_other = fc.aggregate_sum("area_ha").multiply(10000)
        zero_sqm = total_sqm.subtract(sum_other)
        zero_feat = ee.Feature(
            None,
            {
                "class_value": 0,
                "area_ha": zero_sqm.divide(10000),
                "year": ee.Number(year),
                "dataset": dataset_id,
                "product": product_id,
                "territory_id": territory_id,
            },
        )
        return fc.merge(ee.FeatureCollection([zero_feat]))

    year_fcs = [_process_year(y, b) for y, b in year_bands]
    merged = year_fcs[0]
    for fc in year_fcs[1:]:
        merged = merged.merge(fc)

    prefix = f"area_stats/{dataset_id}/{product_id}/{territory_id}"
    filename = f"{prefix}/all_years"

    task = ee.batch.Export.table.toCloudStorage(
        collection=merged,
        description=f"area_stats_{product_id}_{territory_id}_all",
        bucket=bucket_name,
        fileNamePrefix=filename,
        fileFormat="CSV",
        selectors=selectors,
    )
    task.start()
    return task


def check_task_state(task: ee.batch.Task) -> str:
    """Return the current state of an EE task."""
    try:
        return task.status().get("state", "UNKNOWN")
    except Exception:
        return "UNKNOWN"
