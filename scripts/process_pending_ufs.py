#!/usr/bin/env python3
"""
process_pending_ufs.py - Processa tudo que está faltando no GCS para todas as UFs.

Gera a matriz completa (dataset(s) x produtos x 27 UFs) a partir da config,
subtrai o que já existe no GCS, e processa apenas os pendentes.

Uso:
    python scripts/process_pending_ufs.py --dataset brasil_degradation_col10_1
    python scripts/process_pending_ufs.py --dataset brasil_degradation_col10_1 --workers 8
    python scripts/process_pending_ufs.py --dataset brasil_degradation_col10_1 --dry-run
    python scripts/process_pending_ufs.py --dataset brasil_degradation_col10_1 --upload
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import warnings
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")

from ipam_gif_factory.config import ConfigLoader
from ipam_gif_factory.core import DatasetManager

GCS_BUCKET = "mapbiomas-fire"
GCS_HUB_ROOT = "gif-factory"
GCS_PROJECT = "mapbiomas-fire-485203"

UFS = [
    "acre", "alagoas", "amapa", "amazonas",
    "bahia", "ceara", "df", "espirito_santo",
    "goias", "maranhao", "mato_grosso", "mato_grosso_sul",
    "minas_gerais", "para", "paraiba", "parana",
    "pernambuco", "piaui", "rio_de_janeiro", "rio_grande_norte",
    "rio_grande_sul", "rondonia", "roraima", "santa_catarina",
    "sao_paulo", "sergipe", "tocantins",
]


_BUCKET = None


def _get_bucket():
    global _BUCKET
    if _BUCKET is None:
        from google.cloud import storage
        client = storage.Client(project=GCS_PROJECT)
        _BUCKET = client.bucket(GCS_BUCKET)
    return _BUCKET


def _gcs_existentes() -> set:
    bucket = _get_bucket()
    existentes = set()
    prefix = f"{GCS_HUB_ROOT}/"
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith("/"):
            continue
        parts = blob.name.replace(f"{GCS_HUB_ROOT}/", "").split("/")
        if len(parts) >= 3:
            existentes.add((parts[0], parts[1], parts[2]))
    return existentes


def main():
    parser = argparse.ArgumentParser(description="Process pending UFs")
    parser.add_argument("--dataset", required=True,
                        help="Dataset ID (ex: brasil_degradation_col10_1)")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers (default: 4)")
    parser.add_argument("--resume", action="store_true", help="Pular já processados localmente")
    parser.add_argument("--dry-run", action="store_true", help="Só mostrar o que seria processado")
    parser.add_argument("--upload", action="store_true", help="Subir para GCS após processar")
    parser.add_argument("--font-scale", type=float, default=1.0, help="Escala das fontes (padrao: 1.0)")
    args = parser.parse_args()

    config = ConfigLoader().load_all()
    dm = DatasetManager(config)

    # Validar dataset
    datasets = {d["id"]: d for d in dm.list_datasets()}
    if args.dataset not in datasets:
        print(f"Erro: dataset '{args.dataset}' não encontrado.")
        print(f"Datasets disponíveis: {', '.join(sorted(datasets))}")
        sys.exit(1)

    # Listar produtos do dataset
    produtos = [p["id"] for p in dm.list_products(args.dataset)]
    print(f"Dataset: {args.dataset}")
    print(f"Produtos ({len(produtos)}): {', '.join(produtos)}")
    print(f"UFs: {len(UFS)}")

    # Matriz completa: dataset x produto x UF
    total_esperado = len(produtos) * len(UFS)
    print(f"Total esperado: {total_esperado} combos")

    # Checar GCS
    print("Consultando GCS...")
    existentes = _gcs_existentes()

    pendentes = []
    for prod in produtos:
        for uf in UFS:
            if (args.dataset, prod, uf) not in existentes:
                pendentes.append((args.dataset, prod, uf))

    ja_no_gcs = total_esperado - len(pendentes)
    print(f"  Já no GCS: {ja_no_gcs}")
    print(f"  Pendentes: {len(pendentes)}")

    if not pendentes:
        print("Nada pendente. Tudo pronto no GCS!")
        return

    if args.dry_run:
        print("\nItens pendentes:")
        for ds, prod, terr in sorted(pendentes):
            print(f"  {ds} / {prod} / {terr}")
        print(f"\nTotal: {len(pendentes)}")
        return

    # Montar batch com tudo pendente
    items = [{"dataset": ds, "product": prod, "territory": terr}
             for ds, prod, terr in pendentes]
    batch = {
        "created_at": datetime.now().isoformat(),
        "total": len(items),
        "items": items,
    }

    fd, batch_path = tempfile.mkstemp(suffix=".json", prefix="batch_pending_ufs_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(batch, f, indent=2, ensure_ascii=False)

    print(f"\nProcessando {len(items)} itens pendentes com {args.workers} workers...\n")

    root = Path(__file__).resolve().parent.parent
    cmd = [
        sys.executable, "-m", "src.ipam_gif_factory.interfaces.cli",
        "--generate", "--batch", batch_path,
        "--workers", str(args.workers),
        "--font-scale", str(args.font_scale),
    ]
    if args.resume:
        cmd.append("--resume")

    result = subprocess.run(cmd, cwd=str(root))
    os.unlink(batch_path)

    if result.returncode != 0:
        print(f"\n  [ERRO] CLI retornou código {result.returncode}")
        sys.exit(result.returncode)

    print(f"\nProcessamento concluído!")

    if args.upload:
        print(f"\n  Enviando para GCS...")
        subprocess.run(
            [sys.executable, "scripts/upload_to_gcs.py", "--pending"],
            cwd=str(root), check=True)


if __name__ == "__main__":
    main()
