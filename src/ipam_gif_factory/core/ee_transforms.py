import ee
from typing import List, Optional


REFERENCE_LANDCOVER = "projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/reference_native/reference_col9_v1"

LANDCOVER_FOREST_CLASSES = [3, 5, 6]


def build_edge_area() -> ee.Image:
    landcover_base = ee.Image(REFERENCE_LANDCOVER)
    return (
        landcover_base.where(landcover_base.gte(1), 9)
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/edge_area/edge_1000m_col9_v1").gt(1).multiply(8))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/edge_area/edge_600m_col9_v1").gt(1).multiply(7))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/edge_area/edge_300m_col9_v1").gt(1).multiply(6))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/edge_area/edge_150m_col9_v1").gt(1).multiply(5))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/edge_area/edge_120m_col9_v1").gt(1).multiply(4))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/edge_area/edge_90m_col9_v1").gt(1).multiply(3))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/edge_area/edge_60m_col9_v1").gt(1).multiply(2))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/edge_area/edge_30m_col9_v1").gt(1).multiply(1))
    )


def build_fragment_size() -> ee.Image:
    landcover_base = ee.Image(REFERENCE_LANDCOVER)
    return (
        landcover_base.multiply(0)
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/patch_size/size_75ha_col9_v1").gt(1).multiply(6))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/patch_size/size_50ha_col9_v1").gt(1).multiply(5))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/patch_size/size_25ha_col9_v1").gt(1).multiply(4))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/patch_size/size_10ha_col9_v1").gt(1).multiply(3))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/patch_size/size_5ha_col9_v1").gt(1).multiply(2))
        .blend(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/patch_size/size_3ha_col9_v1").gt(1).multiply(1))
    )


def build_distance_100ha() -> ee.Image:
    landcover_base = ee.Image(REFERENCE_LANDCOVER)
    return (
        landcover_base.multiply(0)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/BR_Distance/natural_mask_maior100ha_85_234"), 10)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag50_dist05k_100_v7_85_23"), 2)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag25_dist05k_100_v7_85_23"), 3)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag50_dist10k_100_v7_85_23"), 5)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag25_dist10k_100_v7_85_23"), 6)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag50_dist20k_100_v7_85_23"), 8)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag25_dist20k_100_v7_85_23"), 9)
    )


def build_distance_500ha() -> ee.Image:
    landcover_base = ee.Image(REFERENCE_LANDCOVER)
    return (
        landcover_base.multiply(0)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/BR_Distance/natural_mask_maior500ha_85_234"), 11)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag100_dist05k_500_v7_85_23"), 1)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag50_dist05k_500_v7_85_23"), 2)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag25_dist05k_500_v7_85_23"), 3)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag100_dist10k_500_v7_85_23"), 4)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag50_dist10k_500_v7_85_23"), 5)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag25_dist10k_500_v7_85_23"), 6)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag50_dist20k_500_v7_85_23"), 8)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag25_dist20k_500_v7_85_23"), 9)
    )


def build_distance_1000ha() -> ee.Image:
    landcover_base = ee.Image(REFERENCE_LANDCOVER)
    return (
        landcover_base.multiply(0)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/BR_Distance/natural_mask_maior1000ha_85_234"), 12)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag100_dist05k_1000_v7_85_23"), 1)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag50_dist05k_1000_v7_85_23"), 2)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag25_dist05k_1000_v7_85_23"), 3)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag100_dist10k_1000_v7_85_23"), 4)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag50_dist10k_1000_v7_85_23"), 5)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag25_dist10k_1000_v7_85_23"), 6)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag100_dist20k_1000_v7_85_23"), 7)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag50_dist20k_1000_v7_85_23"), 8)
        .where(ee.Image("projects/mapbiomas-workspace/DEGRADACAO/ISOLATION_col9_v2/nat_uso_frag25_dist20k_1000_v7_85_23"), 9)
    )


def build_secondary_vegetation_coverage() -> ee.Image:
    return (
        ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/secondary_vegetation/secondary_vegetation_age_col9_v1")
        .mod(100)
        .int8()
    )


def build_secondary_vegetation_age() -> ee.Image:
    return (
        ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/secondary_vegetation/secondary_vegetation_age_col9_v1")
        .divide(100)
        .int8()
    )


def build_fire_frequency() -> ee.Image:
    return (
        ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/fire/recurrence_col9_v1")
        .divide(100)
        .int8()
    )


def build_fire_age() -> ee.Image:
    return (
        ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/fire/recurrence_col9_v1")
        .multiply(0)
        .add(
            ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/fire/age_col9_v1")
            .divide(100)
            .int8()
        )
    )


def build_accumulated_burned_coverage() -> ee.Image:
    return (
        ee.Image("projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/fire/recurrence_col9_v1")
        .mod(100)
        .int8()
    )


COL101_FIRE_FREQ = "projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_degradation_fire_frequency_v1"
COL101_FIRE_AGE = "projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_degradation_fire_age_v1"
COL101_VEG_SEC = "projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_degradation_secondary_vegetation_age_v1"
COL101_EDGE_AREA = "projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_degradation_edge_area_v1"
COL101_EDGE_AGE = "projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_degradation_edge_age_v1"
COL101_MORPHOLOGY = "projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_degradation_landscape_morphology_v1"
COL101_PATCH_ID = "projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_degradation_patch_id_v1"
COL101_PATCH_SIZE = "projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_degradation_patch_size_v1"


def decode_fire_frequency_col101() -> ee.Image:
    return ee.Image(COL101_FIRE_FREQ).divide(100).round().unmask(0).int8()


def decode_fire_age_col101() -> ee.Image:
    return ee.Image(COL101_FIRE_AGE).divide(100).round().unmask(0).int8()


def decode_secondary_vegetation_age_col101() -> ee.Image:
    return ee.Image(COL101_VEG_SEC).divide(100).round().unmask(0).int8()


def build_secondary_vegetation_coverage_col101() -> ee.Image:
    img = ee.Image(COL101_VEG_SEC)
    age = img.divide(100).round().int8()
    klass = img.mod(100).unmask(0).int8()
    return klass.where(age.lte(1), 0).int8()


def build_fire_frequency_coverage_col101() -> ee.Image:
    return ee.Image(COL101_FIRE_FREQ).mod(100).unmask(0).int8()


def build_burned_natural_coverage_col101() -> ee.Image:
    img = ee.Image(COL101_FIRE_FREQ)
    freq = img.divide(100).round().int8()
    klass = img.mod(100).unmask(0).int8()
    return klass.where(freq.lt(1), 0)


def build_burned_at_least_once_col101() -> ee.Image:
    img = ee.Image(COL101_FIRE_FREQ)
    freq = img.divide(100).round().unmask(0).int8()
    klass = img.mod(100).unmask(0).int8()
    natural = (klass.eq(3).Or(klass.eq(4)).Or(klass.eq(5)).Or(klass.eq(6))
        .Or(klass.eq(11)).Or(klass.eq(12)).Or(klass.eq(32))
        .Or(klass.eq(49)).Or(klass.eq(50)))
    bands = ee.List(freq.bandNames())

    def iter_cummax(src_list):
        src = ee.List(src_list)
        init = ee.List([ee.Image(0).rename("cm")])
        def fn(cur, prv):
            prv_list = ee.List(prv)
            prev_val = ee.Image(prv_list.get(-1))
            new_val = ee.Image(cur).max(prev_val).rename("cm")
            return prv_list.add(new_val)
        result = ee.List(src.iterate(fn, init))
        result = result.slice(1)
        return ee.ImageCollection.fromImages(result).toBands().rename(bands)

    band_list = bands.map(lambda b: freq.select([b]))
    nat_list = bands.map(lambda b: natural.select([b]))

    burned_so_far = iter_cummax(band_list)

    # ever_natural using the same per-band natural images
    ever_natural = iter_cummax(nat_list)

    # cummax from the end (reverse)
    rev_band_list = ee.List(band_list).reverse()
    cummax_rev = iter_cummax(rev_band_list)
    rev_bands = cummax_rev.bandNames()
    cummax = cummax_rev.select(ee.List(rev_bands).reverse()).rename(bands)

    return (
        freq.multiply(0)
        .where(freq.gte(2), 1)
        .where(freq.eq(1), 2)
        .where(freq.eq(0).And(cummax.gt(freq)).And(natural), 3)
        .where(burned_so_far.gt(0).And(ever_natural.gt(0)).And(natural.Not()), 4)
    )


def build_primary_natural_coverage_col101() -> ee.Image:
    f = ee.Image(COL101_FIRE_FREQ)
    s = ee.Image(COL101_VEG_SEC)
    klass = f.mod(100).unmask(0).int8()
    sec_klass = s.mod(100).unmask(0).int8()
    sec_age = s.divide(100).round().int8()
    natural = (klass.eq(3).Or(klass.eq(4)).Or(klass.eq(5)).Or(klass.eq(6))
        .Or(klass.eq(11)).Or(klass.eq(12)).Or(klass.eq(32))
        .Or(klass.eq(49)).Or(klass.eq(50)))
    is_secondary = sec_klass.gt(0).And(sec_age.gt(1))
    return klass.where(natural.And(is_secondary.Not()).Not(), 0).int8()


def decode_edge_area_col101() -> ee.Image:
    img = ee.Image(COL101_EDGE_AREA)
    classified = (
        img.multiply(0)
        .where(img.gt(0).And(img.lte(30)), 1)
        .where(img.gt(30).And(img.lte(60)), 2)
        .where(img.gt(60).And(img.lte(90)), 3)
        .where(img.gt(90).And(img.lte(120)), 4)
        .where(img.gt(120).And(img.lte(150)), 5)
        .where(img.gt(150).And(img.lte(300)), 6)
        .where(img.gt(300).And(img.lte(600)), 7)
        .where(img.gt(600).And(img.lte(1000)), 8)
        .unmask(0)
        .int8()
    )
    return classified


def decode_edge_age_col101() -> ee.Image:
    return ee.Image(COL101_EDGE_AGE).unmask(0).int8()


def decode_morphology_col101() -> ee.Image:
    return ee.Image(COL101_MORPHOLOGY).unmask(0).int8()


def decode_patch_id_col101() -> ee.Image:
    return ee.Image(COL101_PATCH_ID).unmask(0).toInt32()


def decode_patch_size_col101() -> ee.Image:
    return ee.Image(COL101_PATCH_SIZE).unmask(0).int8()


def only_coverage(class_list: List[int], image: ee.Image, landcover: ee.Image) -> ee.Image:
    container = image.multiply(0)
    for cls in class_list:
        container = container.where(landcover.eq(cls).selfMask(), image)
    return ee.Image(container).selfMask()


PROCESSOR_REGISTRY = {
    "build_edge_area": build_edge_area,
    "build_fragment_size": build_fragment_size,
    "build_distance_100ha": build_distance_100ha,
    "build_distance_500ha": build_distance_500ha,
    "build_distance_1000ha": build_distance_1000ha,
    "build_secondary_vegetation_coverage": build_secondary_vegetation_coverage,
    "build_secondary_vegetation_age": build_secondary_vegetation_age,
    "build_fire_frequency": build_fire_frequency,
    "build_fire_age": build_fire_age,
    "build_accumulated_burned_coverage": build_accumulated_burned_coverage,
    "decode_fire_frequency_col101": decode_fire_frequency_col101,
    "decode_fire_age_col101": decode_fire_age_col101,
    "decode_secondary_vegetation_age_col101": decode_secondary_vegetation_age_col101,
    "build_secondary_vegetation_coverage_col101": build_secondary_vegetation_coverage_col101,
    "build_fire_frequency_coverage_col101": build_fire_frequency_coverage_col101,
    "build_burned_natural_coverage_col101": build_burned_natural_coverage_col101,
    "build_burned_at_least_once_col101": build_burned_at_least_once_col101,
    "build_primary_natural_coverage_col101": build_primary_natural_coverage_col101,
    "decode_edge_area_col101": decode_edge_area_col101,
    "decode_edge_age_col101": decode_edge_age_col101,
    "decode_morphology_col101": decode_morphology_col101,
    "decode_patch_id_col101": decode_patch_id_col101,
    "decode_patch_size_col101": decode_patch_size_col101,
}


def run_processor(processor_name: str, **kwargs) -> ee.Image:
    if processor_name not in PROCESSOR_REGISTRY:
        raise KeyError(f"Processador '{processor_name}' não encontrado. Disponíveis: {list(PROCESSOR_REGISTRY.keys())}")
    return PROCESSOR_REGISTRY[processor_name](**kwargs)
