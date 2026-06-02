"""
M0 Setup — Ambiente, autenticacao, config, cache.
Usado pelo notebook da Fabrica de GIFs.

Uso:
    from nb_setup import setup
    ctx = setup()  # NotebookContext com todos os atributos
"""

import sys
import os
import glob
import multiprocessing
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class NotebookContext:
    config: any
    workers: int
    in_colab: bool
    gif_cache: Dict[Tuple[str, str], Set[str]] = field(default_factory=lambda: defaultdict(set))
    territory_groups: Dict[str, List[str]] = field(default_factory=dict)
    dataset_categories: Dict[str, List[str]] = field(default_factory=dict)
    all_territories: List[str] = field(default_factory=list)


def detect_colab() -> bool:
    try:
        import google.colab
        return True
    except ImportError:
        return False


def detect_workers() -> int:
    cores = os.cpu_count() or 4
    return max(1, min(cores - 1, 12))


def find_project_root() -> str:
    cwd = os.getcwd()
    sys.path.insert(0, cwd)
    if not os.path.exists(os.path.join(cwd, 'src')):
        parent = os.path.dirname(cwd)
        if os.path.exists(os.path.join(parent, 'src')):
            sys.path.insert(0, parent)
            os.chdir(parent)
            return parent
    return cwd


def authenticate_gee(in_colab: bool):
    import ee
    if in_colab:
        ee.Authenticate()
        ee.Initialize(project='ee-ipam')
    else:
        try:
            ee.Initialize(project='ee-ipam')
        except Exception:
            pass


def build_gif_cache(ctx: NotebookContext):
    ctx.gif_cache.clear()
    output_base = ctx.config.get_output_dir()
    for gif_path in glob.glob(os.path.join(output_base, '**', '*.gif'), recursive=True):
        rel = os.path.relpath(gif_path, output_base).replace('\\', '/')
        parts = rel.split('/')
        if len(parts) >= 3:
            ds, prod, terr = parts[0], parts[1], parts[2]
            ctx.gif_cache[(ds, prod)].add(terr)
    for state_path in glob.glob(os.path.join(output_base, '**', '.state_gif'), recursive=True):
        d = os.path.dirname(state_path)
        rel = os.path.relpath(d, output_base).replace('\\', '/')
        parts = rel.split('/')
        if len(parts) >= 3:
            ds, prod, terr = parts[0], parts[1], parts[2]
            ctx.gif_cache[(ds, prod)].add(terr)


def flatten_territories(territories_dict) -> List[str]:
    result = []
    for group_name, group in territories_dict.items():
        if isinstance(group, dict):
            for tid in group.keys():
                result.append(tid)
    return sorted(result)


def build_territory_groups(territories_dict) -> Dict[str, List[str]]:
    groups = {'countries': [], 'biomes': [], 'states': [], 'custom_regions': []}
    for gname, group in territories_dict.items():
        if isinstance(group, dict):
            if gname == 'countries':
                groups['countries'] = sorted(group.keys())
            elif gname == 'biomes':
                groups['biomes'] = sorted(group.keys())
            elif gname == 'states':
                groups['states'] = sorted(group.keys())
            elif gname == 'custom_regions':
                groups['custom_regions'] = sorted(group.keys())
    return groups


def build_dataset_categories(datasets_dict) -> Dict[str, List[str]]:
    categories = {}
    for ds_id, ds_data in datasets_dict.items():
        cat = ds_data.get('category', 'other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(ds_id)
    return categories


def setup() -> NotebookContext:
    """Inicializa ambiente, autentica, carrega config e cache.
       Retorna NotebookContext com todos os dados prontos."""
    from src.ipam_gif_factory.config import ConfigLoader

    in_colab = detect_colab()
    root = find_project_root()
    authenticate_gee(in_colab)

    if in_colab:
        print(f"[COLAB] Ambiente detectado. Root: {root}")

    config = ConfigLoader()
    workers = detect_workers()

    ctx = NotebookContext(
        config=config,
        workers=workers,
        in_colab=in_colab,
    )

    build_gif_cache(ctx)
    ctx.all_territories = flatten_territories(config.territories)
    ctx.territory_groups = build_territory_groups(config.territories)
    ctx.dataset_categories = build_dataset_categories(config.datasets)

    total_gifs = sum(len(v) for v in ctx.gif_cache.values())
    print(f"Ambiente: {'Google Colab' if in_colab else 'VS Code'}")
    print(f"Workers auto-detectados: {workers}")
    print(f"Datasets: {len(list(config.datasets.keys()))} | Territorios: {len(ctx.all_territories)}")
    print(f"Cache: {total_gifs} GIFs encontrados")
    print("Pronto!")

    return ctx
