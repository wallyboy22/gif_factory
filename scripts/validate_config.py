"""Health check for all YAML configuration files.

Usage:
    python scripts/validate_config.py
    python scripts/validate_config.py --check-assets
    python scripts/validate_config.py --initiative brasil
"""

import argparse
import json
import os
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Windows-safe symbols
CHECK = "+"
CROSS = "x"
WARN_SYM = "!"
ARROW = "->"
BULLET = "*"

CONFIG_DIR = "config"

KNOWN_TERRITORY_TYPES = {"countries", "regions", "states", "biomes", "departments"}


def _find_yaml_files(root: str) -> List[str]:
    files = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.endswith(".yaml"):
                files.append(os.path.join(dirpath, f))
    return sorted(files)


def _try_load_yaml(path: str) -> Optional[Dict]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _iter_collection_yamls() -> List[Tuple[str, str, str, Dict]]:
    initiatives_dir = Path(CONFIG_DIR) / "initiatives"
    results = []
    if not initiatives_dir.is_dir():
        return results
    for init_dir in sorted(initiatives_dir.iterdir()):
        if not init_dir.is_dir():
            continue
        coll_dir = init_dir / "collections"
        if not coll_dir.is_dir():
            continue
        for f in sorted(coll_dir.iterdir()):
            if not f.name.endswith(".yaml"):
                continue
            data = _try_load_yaml(str(f))
            if data:
                results.append((init_dir.name, f.stem, str(f), data))
    return results


def _iter_territory_yamls() -> List[Tuple[str, str, str, Dict]]:
    initiatives_dir = Path(CONFIG_DIR) / "initiatives"
    results = []
    if not initiatives_dir.is_dir():
        return results
    for init_dir in sorted(initiatives_dir.iterdir()):
        if not init_dir.is_dir():
            continue
        terr_dir = init_dir / "territories"
        if not terr_dir.is_dir():
            continue
        for f in sorted(terr_dir.iterdir()):
            if not f.name.endswith(".yaml"):
                continue
            data = _try_load_yaml(str(f))
            if data:
                results.append((init_dir.name, f.stem, str(f), data))
    return results


def _load_visualizations() -> Dict[str, Any]:
    viz = _try_load_yaml(os.path.join(CONFIG_DIR, "visualization.yaml")) or {}
    includes = viz.pop("includes", [])
    all_viz = dict(viz.get("visualizations", {}))
    for inc in includes:
        inc_path = os.path.join(CONFIG_DIR, inc)
        if os.path.exists(inc_path):
            inc_data = _try_load_yaml(inc_path) or {}
            all_viz.update(inc_data.get("visualizations", {}))
    return all_viz


def _load_categories() -> Dict[str, Any]:
    cat_data = _try_load_yaml(os.path.join(CONFIG_DIR, "categories.yaml")) or {}
    return cat_data.get("categories", {})


def _load_initiatives_meta() -> Dict[str, Dict]:
    initiatives_dir = Path(CONFIG_DIR) / "initiatives"
    result = {}
    if not initiatives_dir.is_dir():
        return result
    for init_dir in sorted(initiatives_dir.iterdir()):
        if not init_dir.is_dir():
            continue
        meta = _try_load_yaml(str(init_dir / "initiative.yaml"))
        if meta:
            result[meta.get("id", init_dir.name)] = {
                "dir": init_dir.name,
                "data": meta,
            }
    return result


def _load_processor_registry() -> Dict[str, Any]:
    try:
        sys.path.insert(0, "src")
        from mapbiomas_data.core.ee_transforms import PROCESSOR_REGISTRY
        return PROCESSOR_REGISTRY
    except ImportError:
        return {}


def _load_visualization_reference() -> Dict[str, Any]:
    ref = _try_load_yaml(os.path.join(CONFIG_DIR, "visualization_reference.yaml"))
    return ref or {}


def _load_batch_files() -> List[Tuple[str, List[Dict]]]:
    batches_dir = Path(CONFIG_DIR) / "batches"
    results = []
    if not batches_dir.is_dir():
        return results
    for f in sorted(batches_dir.iterdir()):
        if not f.name.endswith(".json"):
            continue
        try:
            with open(str(f), "r", encoding="utf-8") as fh:
                data = json.load(fh)
            items = data.get("items", [])
            results.append((f.name, items))
        except (json.JSONDecodeError, IOError) as e:
            results.append((f.name, [{"_error": str(e)}]))
    return results


def _all_territory_ids() -> Dict[str, str]:
    ids = {}
    for _, _, _, data in _iter_territory_yamls():
        for tid, info in data.get("territories", {}).items():
            ids[tid] = info.get("name", tid)
    return ids


def _all_dataset_info() -> Dict[str, Dict]:
    info = {}
    for _, _, _, data in _iter_collection_yamls():
        ds_id = data.get("dataset")
        if ds_id:
            info[ds_id] = {
                "products": list(data.get("products", {}).keys()),
                "name": data.get("name", ds_id),
            }
    return info


class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.counts: Dict[str, int] = {}

    def ok(self, label: str, detail: str = "") -> None:
        icon = f"{GREEN}{CHECK}{RESET}"
        msg = f"  {icon}  {label}"
        if detail:
            msg += f"  -  {detail}"
        print(msg)

    def fail(self, label: str, detail: str = "") -> None:
        icon = f"{RED}{CROSS}{RESET}"
        msg = f"  {icon}  {label}"
        if detail:
            msg += f"  -  {detail}"
        print(msg)

    def warn(self, label: str, detail: str = "") -> None:
        icon = f"{YELLOW}{WARN_SYM}{RESET}"
        msg = f"  {icon}  {label}"
        if detail:
            msg += f"  -  {detail}"
        print(msg)


def check_yaml_syntax(result: ValidationResult) -> None:
    files = _find_yaml_files(CONFIG_DIR)
    ok = 0
    for path in files:
        rel = os.path.relpath(path)
        try:
            _try_load_yaml(path)
            ok += 1
        except yaml.YAMLError as e:
            detail = str(e).split("\n")[0]
            result.fail(f"YAML syntax  {rel}", detail)
            result.errors.append(f"{rel}: {detail}")
    result.counts["yaml"] = len(files)
    result.ok(f"YAML syntax  —  {ok}/{len(files)} files valid")


def check_initiatives(result: ValidationResult) -> None:
    metas = _load_initiatives_meta()
    ids = set()
    ok = 0
    for iid, info in sorted(metas.items()):
        data = info["data"]
        missing = [f for f in ["name", "description", "id"] if f not in data]
        if missing:
            result.fail(f"Initiative '{iid}'", f"missing fields: {missing}")
            result.errors.append(f"initiative {iid}: missing {missing}")
        else:
            ok += 1
        if iid in ids:
            result.fail(f"Initiative id '{iid}'", "duplicate id")
            result.errors.append(f"initiative {iid}: duplicate id")
        ids.add(iid)
    result.counts["initiatives"] = len(metas)
    result.ok(f"Initiatives  —  {ok}/{len(metas)} valid" if metas else "Initiatives  —  none found")


def check_territories(result: ValidationResult, initiative_filter: Optional[str] = None) -> None:
    groups = _iter_territory_yamls()
    seen_ids = {}
    total_territories = 0
    ok_groups = 0

    for init_name, fname, path, data in groups:
        if initiative_filter and init_name != initiative_filter:
            continue

        missing = [f for f in ["name", "description", "type", "territories"] if f not in data]
        if missing:
            result.fail(f"Territory group '{fname}' ({init_name})", f"missing fields: {missing}")
            result.errors.append(f"territory {init_name}/{fname}: missing {missing}")
            continue

        ttype = data.get("type", "")
        if ttype not in KNOWN_TERRITORY_TYPES:
            result.fail(f"Territory group '{fname}' ({init_name})", f"invalid type '{ttype}'")
            result.errors.append(f"territory {init_name}/{fname}: invalid type '{ttype}'")
            continue

        terrs = data.get("territories", {})
        group_ok = True
        for tid, tinfo in terrs.items():
            total_territories += 1
            if "name" not in tinfo:
                result.fail(f"Territory '{tid}' in {fname} ({init_name})", "missing 'name'")
                result.errors.append(f"territory {init_name}/{fname}/{tid}: missing name")
                group_ok = False
            if "source" not in tinfo:
                result.fail(f"Territory '{tid}' in {fname} ({init_name})", "missing 'source'")
                result.errors.append(f"territory {init_name}/{fname}/{tid}: missing source")
                group_ok = False
            if tid in seen_ids:
                result.fail(f"Territory id '{tid}'", f"duplicate (also in {seen_ids[tid]})")
                result.errors.append(f"territory {tid}: duplicate in {seen_ids[tid]} and {init_name}/{fname}")
            else:
                seen_ids[tid] = f"{init_name}/{fname}"

        if group_ok:
            ok_groups += 1

    result.counts["territories"] = len(groups)
    result.counts["territory_ids"] = total_territories
    result.ok(f"Territory groups  —  {ok_groups}/{len(groups)} groups, {total_territories} territories")


def check_collections(result: ValidationResult, initiative_filter: Optional[str] = None) -> None:
    categories = _load_categories()
    vizes = _load_visualizations()
    processors = _load_processor_registry()
    collections = _iter_collection_yamls()
    seen_datasets = set()
    total_products = 0
    ok_colls = 0

    for init_name, fname, path, data in collections:
        if initiative_filter and init_name != initiative_filter:
            continue

        missing = [f for f in ["name", "description", "dataset", "project", "category", "products"] if f not in data]
        if missing:
            result.fail(f"Collection '{fname}' ({init_name})", f"missing fields: {missing}")
            result.errors.append(f"collection {init_name}/{fname}: missing {missing}")
            continue

        ds_id = data.get("dataset", "")
        if ds_id in seen_datasets:
            result.fail(f"Dataset '{ds_id}' ({init_name}/{fname})", "dataset id already used in another collection")
            result.errors.append(f"dataset {ds_id}: duplicate (collection {init_name}/{fname})")
        seen_datasets.add(ds_id)

        cat = data.get("category", "")
        if cat and cat not in categories:
            result.warn(f"Collection '{fname}' ({init_name})", f"category '{cat}' not found in categories.yaml")

        prods = data.get("products", {})
        coll_ok = True
        for pid, pinfo in prods.items():
            total_products += 1
            if "name" not in pinfo:
                result.fail(f"Product '{pid}' in {fname}", "missing 'name'")
                result.errors.append(f"product {init_name}/{fname}/{pid}: missing name")
                coll_ok = False
            if "visualization" not in pinfo:
                result.fail(f"Product '{pid}' in {fname}", "missing 'visualization'")
                result.errors.append(f"product {init_name}/{fname}/{pid}: missing visualization")
                coll_ok = False
            else:
                viz_ref = pinfo.get("visualization", "")
                if viz_ref not in vizes:
                    result.fail(f"Product '{pid}' in {fname}", f"visualization '{viz_ref}' not found")
                    result.errors.append(f"product {init_name}/{fname}/{pid}: unknown visualization '{viz_ref}'")

            has_asset = bool(pinfo.get("asset"))
            has_processor = bool(pinfo.get("processor"))
            if not has_asset and not has_processor:
                result.fail(f"Product '{pid}' in {fname}", "neither 'asset' nor 'processor' defined")
                result.errors.append(f"product {init_name}/{fname}/{pid}: no asset/processor")
                coll_ok = False
            elif has_processor and pinfo["processor"] not in processors:
                result.fail(f"Product '{pid}' in {fname}", f"processor '{pinfo['processor']}' not in PROCESSOR_REGISTRY")
                result.errors.append(f"product {init_name}/{fname}/{pid}: unknown processor '{pinfo['processor']}'")
                coll_ok = False

        if coll_ok:
            ok_colls += 1

    result.counts["collections"] = len(collections)
    result.counts["products"] = total_products
    result.ok(f"Collections  —  {ok_colls}/{len(collections)} collections, {total_products} products")


def check_visualizations(result: ValidationResult) -> None:
    vizes = _load_visualizations()
    ok = 0
    for vid, vinfo in vizes.items():
        if "name" not in vinfo:
            result.fail(f"Visualization '{vid}'", "missing 'name'")
            result.errors.append(f"viz {vid}: missing name")
            continue
        if "cmap_type" not in vinfo and "rgb" not in vinfo:
            result.warn(f"Visualization '{vid}'", "missing 'cmap_type' (ok if RGB)")
        if "palette" not in vinfo and "rgb" not in vinfo:
            result.warn(f"Visualization '{vid}'", "missing 'palette' (ok if RGB)")
        ok += 1
    result.counts["visualizations"] = len(vizes)
    result.ok(f"Visualizations  —  {ok}/{len(vizes)} valid")


def check_visualization_reference(result: ValidationResult) -> None:
    ref = _load_visualization_reference()
    vizes = ref.get("visualizations", {})
    if not vizes:
        result.warn("Visualization Reference", "no visualizations found in visualization_reference.yaml")
        return

    ok = 0
    for vid, vinfo in vizes.items():
        if "name" not in vinfo:
            result.fail(f"Ref Viz '{vid}'", "missing 'name'")
            result.errors.append(f"ref_viz {vid}: missing name")
            continue
        classes = vinfo.get("classes", [])
        if not classes:
            result.warn(f"Ref Viz '{vid}'", "no classes defined (needed for area-stats)")
        for cls in classes:
            if "value" not in cls:
                result.fail(f"Ref Viz '{vid}'", f"class missing 'value': {cls}")
                result.errors.append(f"ref_viz {vid}: class missing value")
            if "label" not in cls:
                result.fail(f"Ref Viz '{vid}'", f"class missing 'label' (value={cls.get('value')})")
                result.errors.append(f"ref_viz {vid}: class missing label")
        ok += 1
    result.counts["ref_visualizations"] = len(vizes)
    result.ok(f"Visualization Reference  —  {ok}/{len(vizes)} valid (with class labels)")


def check_batches(result: ValidationResult) -> None:
    all_ds = _all_dataset_info()
    all_terrs = _all_territory_ids()
    batch_files = _load_batch_files()
    ok_files = 0
    total_items = 0
    bad_items = 0

    for fname, items in batch_files:
        file_ok = True
        for item in items:
            if "_error" in item:
                result.fail(f"Batch '{fname}'", f"JSON parse error: {item['_error']}")
                result.errors.append(f"batch {fname}: {item['_error']}")
                file_ok = False
                continue

            total_items += 1
            ds = item.get("dataset", "")
            prod = item.get("product", "")
            terr = item.get("territory", "")

            if ds not in all_ds:
                result.fail(f"Batch '{fname}'", f"dataset '{ds}' not found")
                result.errors.append(f"batch {fname}: unknown dataset '{ds}'")
                file_ok = False
                bad_items += 1
                continue

            if prod and prod not in all_ds[ds]["products"]:
                result.fail(f"Batch '{fname}'", f"product '{prod}' not in dataset '{ds}'")
                result.errors.append(f"batch {fname}: unknown product '{prod}' for '{ds}'")
                file_ok = False
                bad_items += 1

            if terr and terr not in all_terrs:
                result.fail(f"Batch '{fname}'", f"territory '{terr}' not found")
                result.errors.append(f"batch {fname}: unknown territory '{terr}'")
                file_ok = False
                bad_items += 1

        if file_ok:
            ok_files += 1

    result.counts["batches"] = len(batch_files)
    result.counts["batch_items"] = total_items
    result.ok(f"Batch files  —  {ok_files}/{len(batch_files)} files, {total_items} items"
              f"{'' if not bad_items else f', {bad_items} errors'}")


def check_gee_assets(result: ValidationResult) -> None:
    try:
        import ee
        ee.Initialize()
    except Exception as e:
        result.warn("GEE Assets", f"could not authenticate: {e}")
        return

    assets_to_check = {}

    for init_name, fname, path, data in _iter_territory_yamls():
        for tid, tinfo in data.get("territories", {}).items():
            source = tinfo.get("source")
            if source:
                assets_to_check[f"territory:{init_name}/{fname}/{tid}"] = source

    for init_name, fname, path, data in _iter_collection_yamls():
        for pid, pinfo in data.get("products", {}).items():
            asset = pinfo.get("asset")
            if asset:
                assets_to_check[f"product:{init_name}/{fname}/{pid}"] = asset

    ok_count = 0
    fail_count = 0
    for label, path in sorted(assets_to_check.items()):
        try:
            ee.data.getAsset(path)
            ok_count += 1
        except Exception as e:
            msg = str(e)
            if "NOT_FOUND" in msg or "404" in msg:
                result.fail(f"Asset  {label}", f"NOT_FOUND: {path}")
                result.errors.append(f"asset {label}: {path} — NOT_FOUND")
                fail_count += 1
            elif "ImageCollection" in msg or "Image" in msg or "FeatureCollection" in msg:
                ok_count += 1
            else:
                result.warn(f"Asset  {label}", f"{msg[:100]}")
                ok_count += 1

    result.counts["assets"] = len(assets_to_check)
    result.ok(f"GEE Assets  —  {ok_count}/{len(assets_to_check)} found"
              f"{'' if not fail_count else f', {fail_count} missing'}")


def main():
    parser = argparse.ArgumentParser(
        description="MapBiomas Container — Configuration Health Check",
    )
    parser.add_argument("--check-assets", action="store_true",
                        help="Validate Earth Engine assets (requires authentication)")
    parser.add_argument("--initiative", type=str,
                        help="Filter checks to a specific initiative (ex: brasil)")
    args = parser.parse_args()

    result = ValidationResult()

    print()
    print(f"{BOLD}{'=' * 56}{RESET}")
    print(f"{BOLD}  MapBiomas Container — Configuration Health Check{RESET}")
    print(f"{BOLD}{'=' * 56}{RESET}")

    print(f"\n{CYAN}[1] YAML Syntax{RESET}")
    check_yaml_syntax(result)

    print(f"\n{CYAN}[2] Initiatives{RESET}")
    check_initiatives(result)

    print(f"\n{CYAN}[3] Territories{RESET}")
    check_territories(result, args.initiative)

    print(f"\n{CYAN}[4] Visualizations{RESET}")
    check_visualizations(result)

    print(f"\n{CYAN}[5] Collections{RESET}")
    check_collections(result, args.initiative)

    print(f"\n{CYAN}[6] Visualization Reference{RESET}")
    check_visualization_reference(result)

    print(f"\n{CYAN}[7] Batch Files{RESET}")
    check_batches(result)

    if args.check_assets:
        print(f"\n{CYAN}[8] GEE Assets{RESET}")
        check_gee_assets(result)

    print()
    print(f"{BOLD}{'=' * 56}{RESET}")
    if result.errors:
        print(f"  {RED}{CROSS}  {len(result.errors)} error(s) found:{RESET}")
        for err in result.errors:
            print(f"    {BULLET} {err}")
        print()
        sys.exit(1)
    else:
        print(f"  {GREEN}{CHECK}  All checks passed!{RESET}")
        print(f"     {result.counts.get('yaml', 0)} YAML files, "
              f"{result.counts.get('initiatives', 0)} initiatives, "
              f"{result.counts.get('ref_visualizations', 0)} ref visualizations, "
              f"{result.counts.get('collections', 0)} collections")
        print(f"     {result.counts.get('products', 0)} products, "
              f"{result.counts.get('territories', 0)} territory groups, "
              f"{result.counts.get('territory_ids', 0)} territories")
        if result.counts.get('assets'):
            print(f"     {result.counts.get('assets', 0)} GEE assets checked")
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
