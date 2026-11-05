#!/usr/bin/env python3
"""process_uf_and_upload.py - Processa e sobe cada UF (provincia da RDC) para o Google Drive.

Fluxo por territorio:
  1) processa os 3 produtos (nivel0/1/2) em paralelo (resume-safe)
  2) sobe os 3 produtos para o Drive (pula o que ja existe)
  3) segue para a proxima UF

Uso:
    python scripts/process_uf_and_upload.py                          # todas as UFs restantes
    python scripts/process_uf_and_upload.py --only drc_kwango        # so uma UF
    python scripts/process_uf_and_upload.py --start-from drc_tshopo  # comeca de uma UF
    python scripts/process_uf_and_upload.py --no-upload              # so processa, nao sobe
"""
import argparse
import os
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
SRC = os.path.join(PROJECT_ROOT, "src")
SYNC = os.path.join(HERE, "sync")
for p in (SRC, SYNC):
    if p not in sys.path:
        sys.path.insert(0, p)

warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")

from mapbiomas_data.config import ConfigLoader
from mapbiomas_data.core.pipeline import Pipeline
from mapbiomas_data.interfaces.cli import CLI
from upload_to_drive import upload_combo

DATASET = "drc_lulc_col1"
PRODUCTS = ["nivel0", "nivel1", "nivel2"]
VERTICAL_DIM = 2000
MAX_WORKERS = 3


def _drc_provinces(cfg) -> list:
    depts = cfg.territories.get("departments", {})
    return [t for t in depts if t.startswith("drc_") and t != "drc_kinshasa"]


def process_territory(terr: str) -> dict:
    cli = CLI()
    results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_process_one, cli, pid, terr): pid for pid in PRODUCTS}
        for fut in as_completed(futures):
            pid, status = fut.result()
            results[pid] = status
    return results


def _process_one(cli: CLI, pid: str, terr: str) -> tuple:
    try:
        pipe = Pipeline(cli.config)
        result = pipe.run(
            dataset_id=DATASET,
            product_id=pid,
            territory_id=terr,
            vertical_dimension=VERTICAL_DIM,
            add_labels=True,
            create_collage=True,
            resume=True,
        )
        status = result.get("status", "error")
        if status == "success":
            return (pid, f"OK  GIF={result.get('gif_path', 'N/A')}")
        return (pid, f"FAIL {result.get('error', status)}")
    except Exception as e:
        return (pid, f"EXCEPTION {e}")


def upload_territory(terr: str, output_dir) -> None:
    for pid in PRODUCTS:
        n = upload_combo(DATASET, pid, terr, output_dir)
        print(f"    -> {pid}: {n} arquivo(s) enviados")


def main():
    parser = argparse.ArgumentParser(description="Processa e sobe UFs da RDC para o Drive")
    parser.add_argument("--only", help="Processa apenas esta UF")
    parser.add_argument("--start-from", help="Comeca a partir desta UF (incluida)")
    parser.add_argument("--no-upload", action="store_true", help="So processa, nao sobe para o Drive")
    args = parser.parse_args()

    cfg = ConfigLoader().load_all()
    output_dir = Path(cfg.get_output_dir())
    provinces = _drc_provinces(cfg)

    if args.only:
        if args.only not in provinces:
            print(f"UF '{args.only}' nao encontrada. Disponiveis: {provinces}")
            sys.exit(1)
        provinces = [args.only]
    elif args.start_from:
        try:
            idx = provinces.index(args.start_from)
        except ValueError:
            print(f"UF '{args.start_from}' nao encontrada. Disponiveis: {provinces}")
            sys.exit(1)
        provinces = provinces[idx:]

    print(f"\n{'[PROCESS+UPLOAD]' if not args.no_upload else '[PROCESS ONLY]'} "
          f"{len(provinces)} UF(s): {provinces}\n")

    for i, terr in enumerate(provinces, 1):
        print(f"[{i}/{len(provinces)}] ==== {terr} ====")
        print(f"  -- processando {DATASET} / {terr} ...")
        results = process_territory(terr)
        for pid in PRODUCTS:
            print(f"     {pid:8s}: {results.get(pid, 'N/A')}")

        if not args.no_upload:
            print(f"  -- subindo {terr} para o Drive ...")
            upload_territory(terr, output_dir)
        else:
            print(f"  -- (no-upload) pulando upload de {terr}")

        print()

    print("=" * 60)
    print(f"  FINALIZADO: {len(provinces)} UF(s) processadas")
    print("=" * 60)


if __name__ == "__main__":
    main()