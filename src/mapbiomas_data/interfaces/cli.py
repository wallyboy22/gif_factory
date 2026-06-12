import argparse
import concurrent.futures
import json
import os
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import ConfigLoader
from ..postprocessing.frame_selector import FRAME_MODES
from ..core import (
    DatasetManager,
    TerritoryManager,
    VisualizationManager,
    InitiativeManager,
    GIFGenerator,
    FrameProcessor,
)


class CLI:
    """Interface de linha de comando para o MapBiomas GIF Factory."""

    def __init__(self):
        self.config = ConfigLoader()
        self.config.load_all()
        self.datasets = DatasetManager(self.config)
        self.territories = TerritoryManager(self.config)
        self.visualizations = VisualizationManager(self.config)
        self.initiatives = InitiativeManager(self.config)

    def run(self, args: List[str] = None):
        parser = argparse.ArgumentParser(
            description="MapBiomas GIF Factory - Gerar GIFs animados do Earth Engine",
        )
        parser.add_argument("--list-initiatives", action="store_true", help="Listar iniciativas (Brasil, Paraguay)")
        parser.add_argument("--list-categories", action="store_true", help="Listar categorias")
        parser.add_argument("--list-datasets", type=str, nargs="?", const="all", help="Listar datasets (opcional: filtrar por categoria)")
        parser.add_argument("--list-products", type=str, help="Listar produtos de um dataset")
        parser.add_argument("--list-territories", type=str, nargs="?", const="all", help="Listar territórios (opcional: filtrar por tipo: countries, biomes, states, regions, departments)")
        parser.add_argument("--list-collections", type=str, help="Listar coleções de uma iniciativa (ex: brasil)")
        parser.add_argument("--list-territory-groups", type=str, help="Listar grupos de território de uma iniciativa (ex: brasil)")
        parser.add_argument("--list-viz", action="store_true", help="Listar visualizações disponíveis")
        parser.add_argument("--generate", action="store_true", help="Executar pipeline completo: download -> processar -> GIF")
        parser.add_argument("--initiative", type=str, help="ID da iniciativa (ex: brasil, paraguay)")
        parser.add_argument("--collection", type=str, help="ID da coleção dentro da iniciativa")
        parser.add_argument("--territory-group", type=str, help="ID do grupo de território dentro da iniciativa")
        parser.add_argument("--dataset", type=str, help="ID do dataset")
        parser.add_argument("--product", type=str, help="ID do produto")
        parser.add_argument("--territory", type=str, default="uf_df", help="ID do território (padrão: uf_df)")
        parser.add_argument("--output", type=str, help="Diretório de saída")
        parser.add_argument("--viz", type=str, help="Chave de visualização (opcional - usa default do produto)")
        parser.add_argument("--max-bands", type=int, default=0, help="Limitar número de bandas (0=todas)")
        parser.add_argument("--band-names-filter", type=str, nargs="*", help="Filtrar bandas por sufixo (ex: 1986 2024)")
        parser.add_argument("--auth", action="store_true", help="Autenticar Earth Engine")
        parser.add_argument("--validate", action="store_true", help="Validar configuração completa")
        parser.add_argument("--check-assets", action="store_true", help="Validar assets do Earth Engine (requer autenticação)")
        parser.add_argument("--area-stats", action="store_true", help="Computar estatísticas de área por classe (consulta EE)")
        parser.add_argument("--charts", action="store_true", help="Gerar gráficos a partir de area_stats (anual + série temporal)")
        parser.add_argument("--compose", action="store_true", help="Compor mapas + gráficos lado a lado em GIF")
        parser.add_argument("--gcs", action="store_true", help="Exportar/upload para GCS (storage permanente)")
        parser.add_argument("--cell-height", type=int, default=300, help="Altura de cada célula na colagem (padrão: 300)")
        parser.add_argument("--resume", action="store_true", help="Retomar processamento de onde parou (checkpoint local)")
        parser.add_argument("--resume-from-gcs", action="store_true",
                            help="Pular combos já completos no GCS + resume local no resto")
        parser.add_argument("--frames-only", action="store_true", help="Apenas baixar frames, sem colagem/GIF")
        parser.add_argument("--batch", type=str, help="Caminho para arquivo batch.json com lista de itens para processar em lote")
        parser.add_argument("--workers", type=int, default=1, help="Processos paralelos no modo batch (padrão: 1, sequencial)")
        parser.add_argument("--no-upload", action="store_true", help="Pular upload para GCS apos cada combo")
        parser.add_argument("--font-scale", type=float, default=1.0, help="Escala das fontes (padrão: 1.0)")
        parser.add_argument("--postprocess", type=str,
                            choices=["geopdfs", "catalogs", "special-collages"],
                            help="Pós-processamento: gerar GeoPDFs, catálogos ou collages especiais")
        parser.add_argument("--all", action="store_true", help="Processar todos (para --postprocess geopdfs)")
        parser.add_argument("--mega", action="store_true", help="Apenas catálogo mega")
        parser.add_argument("--by-territory", action="store_true", help="Apenas catálogo por território")
        parser.add_argument("--by-collection", action="store_true", help="Apenas catálogo por coleção")
        parser.add_argument("--by-territory-collection", action="store_true", help="Apenas catálogo por par")
        parser.add_argument("--catalog-mode", type=str, default="all", choices=FRAME_MODES,
                            help="Modo de seleção de frames para catálogos")
        parser.add_argument("--special-mode", type=str, default="first_last", choices=FRAME_MODES,
                            help="Modo para special collages")

        parsed = parser.parse_args(args)

        if parsed.list_initiatives:
            return self._list_initiatives()
        if parsed.list_categories:
            return self._list_categories()
        if parsed.list_datasets:
            category = None if parsed.list_datasets == "all" else parsed.list_datasets
            return self._list_datasets(category)
        if parsed.list_products:
            return self._list_products(parsed.list_products)
        if parsed.list_territories:
            ttype = None if parsed.list_territories == "all" else parsed.list_territories
            return self._list_territories(ttype)
        if parsed.list_collections:
            return self._list_collections(parsed.list_collections)
        if parsed.list_territory_groups:
            return self._list_territory_groups(parsed.list_territory_groups)
        if parsed.list_viz:
            return self._list_viz()
        if parsed.auth:
            return self._auth()
        if parsed.validate:
            return self._validate(check_assets=parsed.check_assets)
        if parsed.area_stats:
            if parsed.batch:
                return self._execute_area_stats_batch(
                    parsed.batch, use_gcs=parsed.gcs, resume=parsed.resume
                )
            return self._execute_area_stats(
                parsed.dataset, parsed.product, parsed.territory,
                use_gcs=parsed.gcs, resume=parsed.resume
            )
        if parsed.charts:
            if parsed.batch:
                return self._execute_charts_batch(parsed.batch, font_scale=parsed.font_scale)
            return self._execute_charts(
                parsed.dataset, parsed.product, parsed.territory,
                font_scale=parsed.font_scale,
            )
        if parsed.compose:
            if parsed.batch:
                return self._execute_compose_batch(parsed.batch, font_scale=parsed.font_scale)
            return self._execute_compose(
                parsed.dataset, parsed.product, parsed.territory,
                font_scale=parsed.font_scale,
            )
        if parsed.postprocess:
            if parsed.postprocess == "geopdfs":
                from ..postprocessing.cli import main as pp_main
                pp_main(["build-geopdfs"] + (["--all"] if parsed.all else []))
            elif parsed.postprocess == "catalogs":
                from ..postprocessing.cli import main as pp_main
                mode = parsed.catalog_mode or "all"
                pp_main(["build-catalogs"] + (["--mega"] if parsed.mega else []) +
                        (["--by-territory"] if parsed.by_territory else []) +
                        (["--by-collection"] if parsed.by_collection else []) +
                        (["--by-territory-collection"] if parsed.by_territory_collection else []) +
                        ["--mode", mode])
            elif parsed.postprocess == "special-collages":
                from ..postprocessing.cli import main as pp_main
                pp_main(["build-special-collages", "--mode", parsed.special_mode or "first_last",
                         "--dataset", parsed.dataset or "",
                         "--product", parsed.product or "",
                         "--territory", parsed.territory or ""])
            return

        if parsed.generate:
            if parsed.initiative and (parsed.collection or parsed.territory_group):
                return self._execute_pipeline_by_initiative(
                    initiative_id=parsed.initiative,
                    collection_id=parsed.collection,
                    territory_group_id=parsed.territory_group,
                    territory_id=parsed.territory,
                    product_id=parsed.product,
                    output_dir=parsed.output,
                    viz_key=parsed.viz,
                    max_bands=parsed.max_bands,
                    band_names_filter=parsed.band_names_filter,
                    cell_height=parsed.cell_height,
                    resume=parsed.resume,
                    frames_only=parsed.frames_only,
                    font_scale=parsed.font_scale,
                )
            if parsed.batch:
                return self._execute_batch(
                    parsed.batch,
                    parsed.output,
                    parsed.cell_height,
                    parsed.resume,
                    parsed.workers,
                    parsed.no_upload,
                    resume_from_gcs=parsed.resume_from_gcs,
                    font_scale=parsed.font_scale,
                )
            return self._execute_pipeline(
                parsed.dataset,
                parsed.product,
                parsed.territory,
                parsed.output,
                parsed.viz,
                parsed.max_bands,
                band_names_filter=parsed.band_names_filter,
                cell_height=parsed.cell_height,
                resume=parsed.resume,
                frames_only=parsed.frames_only,
                font_scale=parsed.font_scale,
            )

        parser.print_help()

    def _list_categories(self):
        cats = self.datasets.list_categories()
        if not cats:
            print("Nenhuma categoria encontrada.")
            return
        print("\nCategorias disponíveis:")
        for c in cats:
            print(f"  {c['id']:20s} - {c['label']}")

    def _list_datasets(self, category: str = None):
        datasets = self.datasets.list_datasets(category)
        if not datasets:
            print("Nenhum dataset encontrado.")
            return
        print(f"\nDatasets disponíveis{' (categoria: ' + category + ')' if category else ''}:")
        for ds in datasets:
            print(f"  {ds['id']:30s} - {ds['description'][:60]}")

    def _list_products(self, dataset_id: str):
        try:
            products = self.datasets.list_products(dataset_id)
        except KeyError as e:
            print(f"Erro: {e}")
            return
        if not products:
            print(f"Nenhum produto encontrado para '{dataset_id}'.")
            return
        print(f"\nProdutos de '{dataset_id}':")
        for p in products:
            bands = ", ".join(p["bands"][:5])
            if len(p["bands"]) > 5:
                bands += "..."
            print(f"  {p['id']:35s} - {p['name']:40s} | bandas: {bands}")

    def _list_territories(self, territory_type: str = None):
        territories = self.territories.list_territories(territory_type)
        if not territories:
            print("Nenhum território encontrado.")
            return
        print(f"\nTerritórios disponíveis:")
        for t in territories:
            print(f"  {t['id']:25s} - {t['name']:30s} ({t['type']})")

    def _list_initiatives(self):
        initiatives = self.initiatives.list_initiatives()
        if not initiatives:
            print("Nenhuma iniciativa encontrada.")
            return
        print("\nIniciativas disponíveis:")
        for ini in initiatives:
            print(f"  {ini['id']:20s} - {ini['name']:30s} | {ini['collection_count']} coleções, {ini['territory_group_count']} grupos")

    def _list_collections(self, initiative_id: str):
        try:
            collections = self.initiatives.list_collections(initiative_id)
        except KeyError as e:
            print(f"Erro: {e}")
            return
        if not collections:
            print(f"Nenhuma coleção encontrada para '{initiative_id}'.")
            return
        print(f"\nColeções de '{initiative_id}':")
        for coll in collections:
            print(f"  {coll['id']:25s} - {coll['name']:40s} | dataset: {coll['dataset_id']}")

    def _list_territory_groups(self, initiative_id: str):
        try:
            groups = self.initiatives.list_territory_groups(initiative_id)
        except KeyError as e:
            print(f"Erro: {e}")
            return
        if not groups:
            print(f"Nenhum grupo encontrado para '{initiative_id}'.")
            return
        print(f"\nGrupos de território de '{initiative_id}':")
        for g in groups:
            print(f"  {g['id']:25s} - {g['name']:30s} ({len(g['territory_ids'])} territórios) | type: {g['type']}")

    def _list_viz(self):
        keys = self.visualizations.list_viz_keys()
        print("\nVisualizações disponíveis:")
        for key in keys:
            params = self.visualizations.get_viz_params(key)
            print(f"  {key:30s} - {params['name']:30s} [{params['min']}..{params['max']}] ({len(params['palette'])} cores)")

    def _auth(self):
        print("Autenticando Earth Engine...")
        try:
            import ee
            ee.Authenticate()
            ee.Initialize(project=self.config.ee_project_id)
            print("  [OK] Autenticado com sucesso!")
            print(f"  Projeto: {self.config.ee_project_id}")
        except Exception as e:
            print(f"  [ERRO] Falha na autenticação: {e}")
            print("  Visite https://developers.google.com/earth-engine/guides/access para ajuda")
            sys.exit(1)

    def _validate(self, check_assets: bool = False):
        from scripts.validate_config import (
            check_yaml_syntax, check_initiatives, check_visualizations,
            check_collections, check_territories, check_batches,
            check_gee_assets, ValidationResult, CONFIG_DIR,
            _find_yaml_files,
        )

        result = ValidationResult()

        print(f"\n{'=' * 56}")
        print(f"  IPAM GIF Factory — Configuration Health Check")
        print(f"{'=' * 56}")

        print("\n\033[96m[1] YAML Syntax\033[0m")
        check_yaml_syntax(result)

        print("\n\033[96m[2] Initiatives\033[0m")
        check_initiatives(result)

        print("\n\033[96m[3] Territories\033[0m")
        check_territories(result)

        print("\n\033[96m[4] Visualizations\033[0m")
        check_visualizations(result)

        print("\n\033[96m[5] Collections & Products\033[0m")
        check_collections(result)

        print("\n\033[96m[6] Batch Files\033[0m")
        check_batches(result)

        if check_assets:
            print("\n\033[96m[7] GEE Assets\033[0m")
            check_gee_assets(result)

        print()
        print(f"{'=' * 56}")
        if result.errors:
            print(f"\033[91m!  {len(result.errors)} error(s) found:\033[0m")
            for err in result.errors:
                print(f"    - {err}")
            print()
            sys.exit(1)
        else:
            print(f"\033[92m+  All checks passed!\033[0m")
            print(f"     {len(_find_yaml_files(CONFIG_DIR))} YAML files, "
                  f"{result.counts.get('initiatives', 0)} initiatives, "
                  f"{result.counts.get('collections', 0)} collections")
            print(f"     {result.counts.get('products', 0)} products, "
                  f"{result.counts.get('territories', 0)} territory groups, "
                  f"{result.counts.get('territory_ids', 0)} territories")
            if result.counts.get('assets'):
                print(f"     {result.counts.get('assets', 0)} GEE assets checked")
            print()

    def _execute_pipeline_by_initiative(self, initiative_id: str, collection_id: str = None,
                                        territory_group_id: str = None, territory_id: str = None,
                                        product_id: str = None, output_dir: Optional[str] = None,
                                        viz_key: Optional[str] = None, max_bands: int = 0,
                                        band_names_filter: Optional[List[str]] = None,
                                        cell_height: int = 300, resume: bool = False,
                                        frames_only: bool = False, font_scale: float = 1.0):
        try:
            if collection_id:
                dataset_id = self.initiatives.get_collection_dataset_id(initiative_id, collection_id)
            else:
                dataset_id = None

            if territory_group_id and not territory_id:
                terr_ids = self.initiatives.get_group_territory_ids(initiative_id, territory_group_id)
                if len(terr_ids) == 1:
                    territory_id = terr_ids[0]
                elif len(terr_ids) > 1:
                    print(f"Grupo '{territory_group_id}' tem {len(terr_ids)} territórios. Use --territory para especificar um:")
                    for tid in terr_ids:
                        print(f"  {tid}")
                    return
        except KeyError as e:
            print(f"Erro: {e}")
            return

        if not dataset_id and not product_id:
            print("Erro: --collection (ou --dataset) e --product são obrigatórios")
            return

        self._execute_pipeline(
            dataset_id=dataset_id,
            product_id=product_id,
            territory_id=territory_id,
            output_dir=output_dir,
            viz_key=viz_key,
            max_bands=max_bands,
            band_names_filter=band_names_filter,
            cell_height=cell_height,
            resume=resume,
            frames_only=frames_only,
            font_scale=font_scale,
        )

    def _execute_pipeline(self, dataset_id: str, product_id: str, territory_id: str,
                          output_dir: Optional[str], viz_key: Optional[str],
                          max_bands: int = 0, band_names_filter: Optional[List[str]] = None,
                          cell_height: int = 300, resume: bool = False,
                          frames_only: bool = False, font_scale: float = 1.0):
        if not dataset_id or not product_id:
            print("Erro: --dataset e --product são obrigatórios")
            return

        from ..core.pipeline import Pipeline
        pipeline = Pipeline(self.config)
        result = pipeline.run(
            dataset_id=dataset_id,
            product_id=product_id,
            territory_id=territory_id,
            viz_key=viz_key,
            output_dir=output_dir,
            create_collage=not frames_only,
            add_labels=not frames_only,
            max_bands=max_bands,
            band_names_filter=band_names_filter,
            cell_height=cell_height,
            resume=resume,
            font_scale=font_scale,
        )

        if result["status"] == "error":
            print(f"\n  [ERRO] Pipeline falhou: {result.get('error', 'desconhecido')}")
            sys.exit(1)
        else:
            print(f"\n  [OK] Pipeline concluído!")
            print(f"  Frames: {len(result.get('frames', []))}")
            print(f"  GIF: {result.get('gif_path', 'N/A')}")

    def _execute_batch(self, batch_path: str, output_dir: Optional[str],
                       cell_height: int = 300, resume: bool = False,
                       workers: int = 1, no_upload: bool = False,
                       resume_from_gcs: bool = False,
                       font_scale: float = 1.0):
        try:
            with open(batch_path, encoding="utf-8") as f:
                batch = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Erro ao ler batch '{batch_path}': {e}")
            sys.exit(1)

        items = batch.get("items", [])
        total = len(items)
        if not items:
            print("Batch vazio. Nada a processar.")
            return

        do_upload = not no_upload
        r = resume or resume_from_gcs

        print()
        print("=" * 52)
        print(f"  MapBiomas GIF Factory  -  {total} iten{'s' if total > 1 else ''}"  )
        print(f"  Workers: {workers}  |  Modo: {'resume' if r else 'fresh'}")
        print(f"  Resume from GCS: {resume_from_gcs}")
        print(f"  Upload: {'sim' if do_upload else 'nao'}")
        print(f"  Inicio: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print("-" * 52)

        start_all = time.time()
        errors = 0
        done = 0
        lock = threading.Lock()

        def process_one(item):
            nonlocal errors, done
            ds = item.get("dataset", "")
            prod = item.get("product", "")
            terr = item.get("territory", "")
            if not all([ds, prod, terr]):
                with lock:
                    errors += 1
                return

            try:
                pinfo = self.datasets.get_product(ds, prod)
                pname = pinfo.get("name", prod)
            except Exception:
                pname = prod

            # Resume-from-GCS check
            if resume_from_gcs:
                from pathlib import Path
                from scripts.upload_to_gcs import is_combo_complete_on_gcs
                base = Path(self.config.get_output_dir())
                if is_combo_complete_on_gcs(ds, prod, terr, base):
                    with lock:
                        done += 1
                        i = done
                    print(f"\n[{i:02d}/{total:02d}] [SKIP GCS] {pname} — completo no GCS")
                    return

            with lock:
                done += 1
                i = done
            print(f"\n[{i:02d}/{total:02d}] {pname}")
            print(f"  +-> Dataset: {ds}  |  Territorio: {terr}")

            item_start = time.time()
            try:
                self._execute_pipeline(
                    ds, prod, terr,
                    output_dir=output_dir,
                    viz_key=None,
                    max_bands=0,
                    band_names_filter=None,
                    cell_height=cell_height,
                    resume=resume,
                    font_scale=font_scale,
                )
                if do_upload:
                    from pathlib import Path
                    from scripts.upload_to_gcs import upload_combo
                    base = Path(self.config.get_output_dir())
                    upload_combo(ds, prod, terr, base)
            except SystemExit:
                with lock:
                    errors += 1
            item_elapsed = time.time() - item_start
            total_elapsed = time.time() - start_all

            remaining = total - done
            if remaining > 0:
                avg = total_elapsed / done
                eta = avg * remaining
                print(f"  +-> {item_elapsed:.1f}s  |  "
                      f"decorrido: {total_elapsed:.1f}s  |  "
                      f"restante: ~{eta:.0f}s  |  "
                      f"ultimo: {item_elapsed:.1f}s")
            else:
                print(f"  +-> OK {item_elapsed:.1f}s")

        if workers > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(process_one, item) for item in items]
                concurrent.futures.wait(futures)
        else:
            for item in items:
                process_one(item)

        total_time = time.time() - start_all
        print("-" * 52)
        if errors:
            print(f"  ** {total - errors} concluido(s), {errors} erro(s)  |  {total_time:.1f}s")
        else:
            print(f"  OK {total} iten{'s' if total > 1 else ''} concluido{'s' if total > 1 else ''}  |  {total_time:.1f}s")
        print()


    def _execute_area_stats(
        self, dataset_id: str, product_id: str, territory_id: str,
        use_gcs: bool = False, resume: bool = False
    ):
        if not dataset_id or not product_id or not territory_id:
            print("Erro: --dataset, --product e --territory sao obrigatorios")
            return
        try:
            product_info = self.datasets.get_product(dataset_id, product_id)
        except KeyError as e:
            print(f"Erro: {e}")
            return

        from ..core.area_stats import AreaStatsCalculator
        calc = AreaStatsCalculator(self.config)
        paths = calc.compute_and_save(
            dataset_id, product_id, territory_id, product_info,
            use_gcs=use_gcs, resume=resume,
        )
        if use_gcs:
            output_dir = calc._get_output_dir(dataset_id, product_id, territory_id)
            calc.wait_all_tasks(output_dir)

        print(f"\n  [OK] {len(paths)} CSV(s) salvos em {calc._get_output_dir(dataset_id, product_id, territory_id)}/area_stats/")

    def _execute_area_stats_batch(
        self, batch_path: str, use_gcs: bool = False, resume: bool = False
    ):
        try:
            with open(batch_path, encoding="utf-8") as f:
                batch = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Erro ao ler batch '{batch_path}': {e}")
            sys.exit(1)

        items = batch.get("items", [])
        total = len(items)
        if not items:
            print("Batch vazio.")
            return

        from ..core.area_stats import AreaStatsCalculator
        calc = AreaStatsCalculator(self.config)

        print("=" * 52)
        print(f"  Area Stats  —  {total} itens")
        print(f"  GCS: {'sim' if use_gcs else 'nao'}  |  Resume: {'sim' if resume else 'nao'}")
        print("-" * 52)

        ok = 0
        errors = 0
        for i, item in enumerate(items, 1):
            ds = item.get("dataset", "")
            prod = item.get("product", "")
            terr = item.get("territory", "")
            if not all([ds, prod, terr]):
                print(f"\n[{i:02d}/{total:02d}] [SKIP] Item invalido: {item}")
                errors += 1
                continue

            try:
                pinfo = self.datasets.get_product(ds, prod)
                pname = pinfo.get("name", prod)
            except KeyError:
                print(f"\n[{i:02d}/{total:02d}] [SKIP] Produto '{prod}' nao encontrado")
                errors += 1
                continue

            print(f"\n[{i:02d}/{total:02d}] {pname} — {ds}/{prod}/{terr}")
            try:
                paths = calc.compute_and_save(
                    ds, prod, terr, pinfo, use_gcs=use_gcs, resume=resume,
                )
                if paths:
                    ok += 1
                    print(f"  +-> {len(paths)} CSV(s)")
                else:
                    print(f"  +-> Nenhum dado computado")
            except Exception as e:
                print(f"  [ERRO] {e}")
                errors += 1

        if use_gcs:
            for item in items:
                ds = item.get("dataset", "")
                prod = item.get("product", "")
                terr = item.get("territory", "")
                if all([ds, prod, terr]):
                    output_dir = calc._get_output_dir(ds, prod, terr)
                    calc.wait_all_tasks(output_dir)

        print("-" * 52)
        print(f"  OK: {ok}  |  Erros: {errors}  |  Total: {total}")


    def _execute_charts(
        self, dataset_id: str, product_id: str, territory_id: str,
        font_scale: float = 1.0,
    ):
        if not dataset_id or not product_id or not territory_id:
            print("Erro: --dataset, --product e --territory sao obrigatorios")
            return
        try:
            product_info = self.datasets.get_product(dataset_id, product_id)
        except KeyError as e:
            print(f"Erro: {e}")
            return

        from ..core.chart_generator import ChartGenerator
        gen = ChartGenerator(font_scale=font_scale)
        annual, timeseries = gen.generate_all_for_batch(
            self.config, dataset_id, product_id, territory_id, product_info
        )
        print(f"\n  [OK] Annual: {len(annual)}  |  Timeseries: {len(timeseries)}")
        output_dir = os.path.join(
            self.config.get_output_dir(), dataset_id, product_id, territory_id
        )
        self._print_chart_summary(output_dir)

    def _print_chart_summary(self, output_dir: str):
        """Print summary of chart output folders."""
        import glob as gmod
        for folder in ["charts_annual_clean", "charts_timeseries_clean", "charts_gifs"]:
            path = os.path.join(output_dir, folder)
            if os.path.isdir(path):
                files = [f for f in os.listdir(path) if f.endswith((".png", ".gif"))]
                if files:
                    print(f"  +-> {folder}/: {len(files)} arquivo(s)")

    def _execute_charts_batch(self, batch_path: str, font_scale: float = 1.0):
        try:
            with open(batch_path, encoding="utf-8") as f:
                batch = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Erro ao ler batch '{batch_path}': {e}")
            sys.exit(1)

        items = batch.get("items", [])
        total = len(items)
        if not items:
            print("Batch vazio.")
            return

        from ..core.chart_generator import ChartGenerator

        print("=" * 52)
        print(f"  Charts  —  {total} itens")
        print("-" * 52)

        ok = 0
        for i, item in enumerate(items, 1):
            ds = item.get("dataset", "")
            prod = item.get("product", "")
            terr = item.get("territory", "")
            if not all([ds, prod, terr]):
                continue
            try:
                pinfo = self.datasets.get_product(ds, prod)
                pname = pinfo.get("name", prod)
            except KeyError:
                print(f"\n[{i:02d}/{total:02d}] [SKIP] Produto '{prod}' nao encontrado")
                continue
            print(f"\n[{i:02d}/{total:02d}] {pname}")
            try:
                gen = ChartGenerator(font_scale=font_scale)
                annual, ts = gen.generate_all_for_batch(
                    self.config, ds, prod, terr, pinfo
                )
                if annual or ts:
                    ok += 1
                    print(f"  +-> Annual: {len(annual)}  |  Timeseries: {len(ts)}")
                    output_dir = os.path.join(
                        self.config.get_output_dir(), ds, prod, terr
                    )
                    self._print_chart_summary(output_dir)
            except Exception as e:
                import traceback
                print(f"  [ERRO] {e}")
                traceback.print_exc()

        print("-" * 52)
        print(f"  OK: {ok}  |  Total: {total}")

    def _resolve_viz_params_for_compose(
        self, dataset_id: str, product_id: str,
    ) -> Dict[str, Any]:
        """Resolve viz params (classes with colors/labels) for the composer legend."""
        from ..core.area_stats import AreaStatsCalculator
        calc = AreaStatsCalculator(self.config)
        try:
            pinfo = self.datasets.get_product(dataset_id, product_id)
            viz_key = pinfo.get("visualization", "")
            if viz_key:
                ref_viz = calc.get_viz_reference(viz_key)
                if ref_viz:
                    return ref_viz
        except Exception:
            pass
        return {}

    def _execute_compose(
        self, dataset_id: str, product_id: str, territory_id: str,
        font_scale: float = 1.0,
    ):
        if not dataset_id or not product_id or not territory_id:
            print("Erro: --dataset, --product e --territory sao obrigatorios")
            return

        try:
            pinfo = self.datasets.get_product(dataset_id, product_id)
        except KeyError as e:
            print(f"Erro: {e}")
            return

        pname = pinfo.get("name", product_id)
        try:
            tinfo = self.territories.get_territory(territory_id)
            tname = tinfo.get("name", territory_id)
        except KeyError:
            tname = territory_id

        viz_params = self._resolve_viz_params_for_compose(dataset_id, product_id)

        from ..core.composer import Composer
        comp = Composer(font_scale=font_scale)
        output_dir = os.path.join(
            self.config.get_output_dir(), dataset_id, product_id, territory_id
        )
        paths = comp.compose(
            output_dir,
            product_name=pname,
            territory_name=tname,
            viz_params=viz_params,
        )
        print(f"\n  [OK] {len(paths)} composicao(oes) gerada(s)")

    def _execute_compose_batch(self, batch_path: str, font_scale: float = 1.0):
        try:
            with open(batch_path, encoding="utf-8") as f:
                batch = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Erro ao ler batch '{batch_path}': {e}")
            sys.exit(1)

        items = batch.get("items", [])
        total = len(items)
        if not items:
            print("Batch vazio.")
            return

        from ..core.composer import Composer

        print("=" * 52)
        print(f"  Compose  —  {total} itens")
        print("-" * 52)

        ok = 0
        for item in items:
            ds = item.get("dataset", "")
            prod = item.get("product", "")
            terr = item.get("territory", "")
            if not all([ds, prod, terr]):
                continue
            try:
                pinfo = self.datasets.get_product(ds, prod)
                pname = pinfo.get("name", prod)
            except KeyError:
                print(f"\n  [SKIP] Produto '{prod}' não encontrado")
                continue
            try:
                tinfo = self.territories.get_territory(terr)
                tname = tinfo.get("name", terr)
            except KeyError:
                tname = terr

            viz_params = self._resolve_viz_params_for_compose(ds, prod)
            output_dir = os.path.join(
                self.config.get_output_dir(), ds, prod, terr
            )
            try:
                comp = Composer(font_scale=font_scale)
                paths = comp.compose(
                    output_dir,
                    product_name=pname,
                    territory_name=tname,
                    viz_params=viz_params,
                )
                if paths:
                    ok += 1
                    print(f"  +-> {len(paths)} arquivo(s)")
            except Exception as e:
                print(f"  [ERRO] {ds}/{prod}/{terr}: {e}")

        print("-" * 52)
        print(f"  OK: {ok}  |  Total: {total}")

    def _execute_area_stats(
        self, dataset_id: str, product_id: str, territory_id: str,
        use_gcs: bool = False, resume: bool = False
    ):
        if not dataset_id or not product_id or not territory_id:
            print("Erro: --dataset, --product e --territory sao obrigatorios")
            return
        try:
            product_info = self.datasets.get_product(dataset_id, product_id)
        except KeyError as e:
            print(f"Erro: {e}")
            return

        from ..core.area_stats import AreaStatsCalculator
        calc = AreaStatsCalculator(self.config)
        paths = calc.compute_and_save(
            dataset_id, product_id, territory_id, product_info,
            use_gcs=use_gcs, resume=resume,
        )
        if use_gcs:
            output_dir = calc._get_output_dir(dataset_id, product_id, territory_id)
            calc.wait_all_tasks(output_dir)

        print(f"\n  [OK] {len(paths)} CSV(s) salvos em {calc._get_output_dir(dataset_id, product_id, territory_id)}/area_stats/")

    def _execute_area_stats_batch(
        self, batch_path: str, use_gcs: bool = False, resume: bool = False
    ):
        try:
            with open(batch_path, encoding="utf-8") as f:
                batch = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Erro ao ler batch '{batch_path}': {e}")
            sys.exit(1)

        items = batch.get("items", [])
        total = len(items)
        if not items:
            print("Batch vazio.")
            return

        from ..core.area_stats import AreaStatsCalculator
        calc = AreaStatsCalculator(self.config)

        print("=" * 52)
        print(f"  Area Stats  —  {total} itens")
        print(f"  GCS: {'sim' if use_gcs else 'nao'}  |  Resume: {'sim' if resume else 'nao'}")
        print("-" * 52)

        ok = 0
        errors = 0
        for i, item in enumerate(items, 1):
            ds = item.get("dataset", "")
            prod = item.get("product", "")
            terr = item.get("territory", "")
            if not all([ds, prod, terr]):
                print(f"\n[{i:02d}/{total:02d}] [SKIP] Item invalido: {item}")
                errors += 1
                continue

            try:
                pinfo = self.datasets.get_product(ds, prod)
                pname = pinfo.get("name", prod)
            except KeyError:
                print(f"\n[{i:02d}/{total:02d}] [SKIP] Produto '{prod}' nao encontrado")
                errors += 1
                continue

            print(f"\n[{i:02d}/{total:02d}] {pname} — {ds}/{prod}/{terr}")
            try:
                paths = calc.compute_and_save(
                    ds, prod, terr, pinfo, use_gcs=use_gcs, resume=resume,
                )
                if paths:
                    ok += 1
                    print(f"  +-> {len(paths)} CSV(s)")
                else:
                    print(f"  +-> Nenhum dado computado")
            except Exception as e:
                print(f"  [ERRO] {e}")
                errors += 1

        if use_gcs:
            for item in items:
                ds = item.get("dataset", "")
                prod = item.get("product", "")
                terr = item.get("territory", "")
                if all([ds, prod, terr]):
                    output_dir = calc._get_output_dir(ds, prod, terr)
                    calc.wait_all_tasks(output_dir)

        print("-" * 52)
        print(f"  OK: {ok}  |  Erros: {errors}  |  Total: {total}")


def main(args: List[str] = None):
    cli = CLI()
    cli.run(args)


if __name__ == "__main__":
    main()
