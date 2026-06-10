import argparse
import sys
from typing import List, Optional

import os

from ..config import ConfigLoader
from .frame_selector import FRAME_MODES
from .geo_pdf import GeoPDFBuilder
from .catalog_pdf import CatalogPDFBuilder


def build_geopdfs(args):
    config = ConfigLoader().load_all()
    builder = GeoPDFBuilder(config)

    if args.all:
        results = builder.process_all(
            dataset_id=args.dataset,
            product_id=args.product,
            territory_id=args.territory,
        )
    elif args.input:
        if args.territory:
            bounds = builder._get_bounds(args.territory)
        else:
            bounds = None
        results = [builder.process_frame(args.input, args.territory or "", bounds=bounds)]
    else:
        print("Use --all ou --input + --territory")
        return

    ok = [r for r in results if r.get("status") == "ok"]
    errors = [r for r in results if r.get("status") != "ok"]
    geotiff_count = sum(1 for r in ok if r.get("geotiff"))
    geopdf_count = sum(1 for r in ok if r.get("geopdf"))

    print(f"\nGeoPDFs: {len(results)} processados")
    print(f"  GeoTIFFs gerados: {geotiff_count}")
    print(f"  GeoPDFs gerados:  {geopdf_count}")
    if errors:
        print(f"  Erros: {len(errors)}")
        for e in errors[:5]:
            print(f"    - {os.path.basename(e.get('png', '?'))}: {e.get('error', '?')}")
    if geotiff_count > 0 and geopdf_count == 0:
        print("  [AVISO] Nenhum GeoPDF gerado. Instale GDAL CLI para converter GeoTIFF -> GeoPDF.")


def build_catalogs(args):
    config = ConfigLoader().load_all()
    builder = CatalogPDFBuilder(config)
    mode = args.mode or "all"
    out_dir = args.output or config.get_output_dir()

    if args.mega:
        builder.build_mega(out_dir, mode=mode)
    if args.by_territory:
        builder.build_by_territory(os.path.join(out_dir, "catalogs", "por_territorio"), mode=mode)
    if args.by_collection:
        builder.build_by_collection(os.path.join(out_dir, "catalogs", "por_colecao"), mode=mode)
    if args.by_territory_collection:
        builder.build_by_territory_collection(
            os.path.join(out_dir, "catalogs", "por_territorio_colecao"), mode=mode
        )
    if not any([args.mega, args.by_territory, args.by_collection, args.by_territory_collection]):
        builder.build_mega(out_dir, mode=mode)
        builder.build_by_territory(os.path.join(out_dir, "catalogs", "por_territorio"), mode=mode)
        builder.build_by_collection(os.path.join(out_dir, "catalogs", "por_colecao"), mode=mode)
        builder.build_by_territory_collection(os.path.join(out_dir, "catalogs", "por_territorio_colecao"), mode=mode)

    print(f"\nCatálogos salvos em: {os.path.join(out_dir, 'catalogs')}")


def build_special_collages(args):
    config = ConfigLoader().load_all()
    from .special_collages import SpecialCollageBuilder
    from .frame_selector import FRAME_MODES
    builder = SpecialCollageBuilder(config)
    SPECIAL_MODES = [m for m in FRAME_MODES if m not in ("all", "collage")]

    modes = SPECIAL_MODES if args.all_modes else [args.mode]
    combined = []
    for mode in modes:
        print(f"\n--- Modo: {mode} ---")
        results = builder.build_all(
            mode=mode,
            dataset_id=args.dataset,
            product_id=args.product,
            territory_id=args.territory,
            cell_height=args.cell_height or 300,
        )
        combined.extend(results)
        print()
    total = len(combined)
    ok = sum(1 for r in combined if r["status"] == "ok")
    skipped = sum(1 for r in combined if r["status"] == "skipped")
    print(f"Special collages: {total} runs ({ok} ok, {skipped} skipped)")


def main(args: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(
        description="Pós-processamento MapBiomas GIF Factory: GeoPDFs e Catálogos"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comando")

    # --- geopdfs ---
    gp = subparsers.add_parser("build-geopdfs", help="Gerar GeoPDFs/GeoTIFFs dos frames PNG")
    gp.add_argument("--input", type=str, help="Caminho de um PNG específico")
    gp.add_argument("--territory", type=str, help="ID do território (obrigatório se --input)")
    gp.add_argument("--dataset", type=str, help="Filtrar por dataset")
    gp.add_argument("--product", type=str, help="Filtrar por produto")
    gp.add_argument("--all", action="store_true", help="Processar todos os outputs disponíveis")
    gp.set_defaults(func=build_geopdfs)

    # --- special collages ---
    sc = subparsers.add_parser("build-special-collages",
                                help="Gerar collages PNG + GIF com seleção especial de frames")
    sc.add_argument("--mode", type=str, default="first_last", choices=FRAME_MODES,
                    help="Modo de seleção de frames")
    sc.add_argument("--all-modes", action="store_true",
                    help="Gerar TODOS os modos especiais (decadal, quinzenal, first_last, last_six)")
    sc.add_argument("--dataset", type=str, help="Filtrar por dataset")
    sc.add_argument("--product", type=str, help="Filtrar por produto")
    sc.add_argument("--territory", type=str, help="Filtrar por território")
    sc.add_argument("--cell-height", type=int, default=300, help="Altura de cada célula na collage")
    sc.set_defaults(func=build_special_collages)

    # --- catalogs ---
    cp = subparsers.add_parser("build-catalogs", help="Gerar catálogos PDF")
    cp.add_argument("--mode", type=str, default="all", choices=CatalogPDFBuilder.FRAME_MODES,
                    help="Seleção de frames: all, decadal, quinzenal, first_last, collage")
    cp.add_argument("--output", type=str, help="Diretório de saída (padrão: output dir do config)")
    cp.add_argument("--mega", action="store_true", help="Apenas catálogo completo")
    cp.add_argument("--by-territory", action="store_true", help="Apenas por território")
    cp.add_argument("--by-collection", action="store_true", help="Apenas por coleção")
    cp.add_argument("--by-territory-collection", action="store_true", help="Apenas por par")
    cp.set_defaults(func=build_catalogs)

    parsed = parser.parse_args(args)
    if parsed.command is None:
        parser.print_help()
        return

    import os
    parsed.func(parsed)


if __name__ == "__main__":
    main()
