import argparse
import concurrent.futures
import json
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import ConfigLoader
from ..core import (
    DatasetManager,
    TerritoryManager,
    VisualizationManager,
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

    def run(self, args: List[str] = None):
        parser = argparse.ArgumentParser(
            description="MapBiomas GIF Factory - Gerar GIFs animados do Earth Engine",
        )
        parser.add_argument("--list-categories", action="store_true", help="Listar categorias")
        parser.add_argument("--list-datasets", type=str, nargs="?", const="all", help="Listar datasets (opcional: filtrar por categoria)")
        parser.add_argument("--list-products", type=str, help="Listar produtos de um dataset")
        parser.add_argument("--list-territories", type=str, nargs="?", const="all", help="Listar territórios (opcional: filtrar por tipo: countries, biomes, states)")
        parser.add_argument("--list-viz", action="store_true", help="Listar visualizações disponíveis")
        parser.add_argument("--generate", action="store_true", help="Executar pipeline completo: download -> processar -> GIF")
        parser.add_argument("--dataset", type=str, help="ID do dataset")
        parser.add_argument("--product", type=str, help="ID do produto")
        parser.add_argument("--territory", type=str, default="df", help="ID do território (padrão: df)")
        parser.add_argument("--output", type=str, help="Diretório de saída")
        parser.add_argument("--viz", type=str, help="Chave de visualização (opcional - usa default do produto)")
        parser.add_argument("--max-bands", type=int, default=0, help="Limitar número de bandas (0=todas)")
        parser.add_argument("--band-names-filter", type=str, nargs="*", help="Filtrar bandas por sufixo (ex: 1986 2024)")
        parser.add_argument("--auth", action="store_true", help="Autenticar Earth Engine")
        parser.add_argument("--validate", action="store_true", help="Validar configuração")
        parser.add_argument("--cell-height", type=int, default=300, help="Altura de cada célula na colagem (padrão: 300)")
        parser.add_argument("--resume", action="store_true", help="Retomar processamento de onde parou")
        parser.add_argument("--frames-only", action="store_true", help="Apenas baixar frames, sem colagem/GIF")
        parser.add_argument("--batch", type=str, help="Caminho para arquivo batch.json com lista de itens para processar em lote")
        parser.add_argument("--workers", type=int, default=1, help="Processos paralelos no modo batch (padrão: 1, sequencial)")
        parser.add_argument("--no-upload", action="store_true", help="Pular upload para GCS apos cada combo")

        parsed = parser.parse_args(args)

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
        if parsed.list_viz:
            return self._list_viz()
        if parsed.auth:
            return self._auth()
        if parsed.validate:
            return self._validate()
        if parsed.generate:
            if parsed.batch:
                return self._execute_batch(
                    parsed.batch,
                    parsed.output,
                    parsed.cell_height,
                    parsed.resume,
                    parsed.workers,
                    parsed.no_upload,
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

    def _validate(self):
        print("Validando configuração completa...\n")
        errors = []

        ds_count = len(self.datasets.list_datasets())
        print(f"  Datasets: {ds_count}")
        for ds in self.datasets.list_datasets():
            products = self.datasets.list_products(ds["id"])
            for p in products:
                try:
                    info = self.datasets.get_product(ds["id"], p["id"])
                    if not info.get("asset") and not info.get("processor"):
                        errors.append(f"  {ds['id']}/{p['id']}: sem asset nem processor")
                except Exception as e:
                    errors.append(f"  {ds['id']}/{p['id']}: {e}")

        t_count = len(self.territories.list_territories())
        print(f"  Territórios: {t_count}")
        for t in self.territories.list_territories():
            valid, msg = self.territories.validate_territory(t["id"])
            if not valid:
                errors.append(f"  Território {t['id']}: {msg}")

        viz_count = len(self.visualizations.list_viz_keys())
        print(f"  Visualizações: {viz_count}")
        for key in self.visualizations.list_viz_keys():
            if not self.visualizations.validate_palette(key):
                errors.append(f"  Visualização '{key}': paleta inválida")

        if errors:
            print(f"\n  [ERRO] {len(errors)} problema(s) encontrado(s):")
            for e in errors:
                print(f"    - {e}")
            sys.exit(1)
        else:
            print(f"\n  [OK] Tudo válido! Pronto para processar.")

    def _execute_pipeline(self, dataset_id: str, product_id: str, territory_id: str,
                          output_dir: Optional[str], viz_key: Optional[str],
                          max_bands: int = 0, band_names_filter: Optional[List[str]] = None,
                          cell_height: int = 300, resume: bool = False,
                          frames_only: bool = False):
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
                       workers: int = 1, no_upload: bool = False):
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

        print()
        print("=" * 52)
        print(f"  MapBiomas GIF Factory  -  {total} iten{'s' if total > 1 else ''}"  )
        print(f"  Workers: {workers}  |  Modo: {'resume' if resume else 'fresh'}")
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
                )
                if do_upload:
                    from pathlib import Path
                    from scripts.upload_to_gcs import upload_combo
                    base = self.config.get_output_dir()
                    upload_combo(ds, prod, terr, Path(base))
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


def main(args: List[str] = None):
    cli = CLI()
    cli.run(args)


if __name__ == "__main__":
    main()
