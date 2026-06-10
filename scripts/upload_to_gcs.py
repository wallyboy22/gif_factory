#!/usr/bin/env python3
"""
upload_to_gcs.py - Sobe arquivos de mídia locais (GIF, collage, frames, metadata) para o GCS.

Uso:
    python scripts/upload_to_gcs.py --pending                                # tudo que falta no GCS
    python scripts/upload_to_gcs.py --batch batch.json                       # itens de um batch
    python scripts/upload_to_gcs.py --ds X --prod Y --terr Z                # combo específico
    python scripts/upload_to_gcs.py --pending --dry-run                      # só mostrar
    python scripts/upload_to_gcs.py --reupload-missing-metadata              # sobe metadados faltantes
    python scripts/upload_to_gcs.py --reupload-missing-metadata --dry-run    # preview
"""
import argparse
import json
import subprocess
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")

from ipam_gif_factory.config import ConfigLoader

GCS_BUCKET = "mapbiomas-fire"
GCS_HUB_ROOT = "data-container"
GCS_PROJECT = "mapbiomas-fire-485203"

# Singleton: cria cliente uma vez só
_BUCKET = None


def _get_bucket():
    global _BUCKET
    if _BUCKET is None:
        from google.cloud import storage
        client = storage.Client(project=GCS_PROJECT)
        _BUCKET = client.bucket(GCS_BUCKET)
    return _BUCKET


def _list_gcs_combos() -> set:
    existentes = set()
    prefix = f"{GCS_HUB_ROOT}/"
    for blob in _get_bucket().list_blobs(prefix=prefix):
        if blob.name.endswith("/"):
            continue
        rel = blob.name.replace(f"{GCS_HUB_ROOT}/", "")
        parts = rel.split("/")
        if len(parts) >= 3:
            existentes.add((parts[0], parts[1], parts[2]))
    return existentes


def _local_items(output_dir: Path) -> list:
    items = []
    for gif_path in output_dir.rglob("*.gif"):
        try:
            rel = gif_path.relative_to(output_dir)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) >= 3:
            items.append((parts[0], parts[1], parts[2]))
    return sorted(set(items))


def _list_local_metadata(output_dir: Path) -> list:
    """Lista todos os metadata_*.json locais: (ds, prod, terr, Path)."""
    items = []
    for meta_path in output_dir.rglob("metadata_*.json"):
        try:
            rel = meta_path.relative_to(output_dir)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) >= 4:
            ds, prod, terr = parts[0], parts[1], parts[2]
            items.append((ds, prod, terr, meta_path))
    return sorted(items)


def is_combo_complete_on_gcs(ds: str, prod: str, terr: str, output_dir: Path) -> bool:
    """Verifica no GCS se todos os arquivos esperados de um combo existem."""
    meta_local = output_dir / ds / prod / terr / f"metadata_{prod}.json"
    if not meta_local.is_file():
        return False

    with open(meta_local, encoding="utf-8") as f:
        meta = json.load(f)

    bucket = _get_bucket()
    prefix = f"{GCS_HUB_ROOT}/{ds}/{prod}/{terr}/"

    # Arquivos essenciais
    expected = [
        f"{prod}_{terr}_0_3s.gif",
        f"{prod}_{terr}_collage.png",
        f"{prod}_{terr}_collage_decadal.png",
        f"{prod}_{terr}_collage_quinzenal.png",
        f"{prod}_{terr}_collage_first_last.png",
        f"{prod}_{terr}_collage_last_six.png",
        f"metadata_{prod}.json",
    ]
    # Frames individuais
    for fn in meta.get("output", {}).get("frames", []):
        expected.append(fn.split("/")[-1])

    for filename in expected:
        if not bucket.blob(f"{prefix}{filename}").exists():
            return False
    return True


def upload_combo(ds: str, prod: str, terr: str, output_dir: Path, dry_run: bool = False) -> int:
    local_dir = output_dir / ds / prod / terr
    if not local_dir.exists():
        return 0

    bucket = _get_bucket()
    enviados = 0
    for fpath in sorted(local_dir.rglob("*")):
        if not fpath.is_file():
            continue
        name = fpath.name
        if name.startswith(".state"):
            continue
        rel = fpath.relative_to(local_dir).as_posix()
        blob_path = f"{GCS_HUB_ROOT}/{ds}/{prod}/{terr}/{rel}"
        if dry_run:
            print(f"     [DRY-RUN] {blob_path}")
        else:
            bucket.blob(blob_path).upload_from_filename(str(fpath))
        enviados += 1
    return enviados


def main():
    parser = argparse.ArgumentParser(description="Upload media files to GCS")
    parser.add_argument("--ds", help="Dataset ID")
    parser.add_argument("--prod", help="Product ID")
    parser.add_argument("--terr", help="Territory ID")
    parser.add_argument("--batch", type=str, help="Batch JSON file")
    parser.add_argument("--pending", action="store_true", help="Upload tudo que existe local mas não no GCS")
    parser.add_argument("--reupload-missing-metadata", action="store_true",
                        help="Sobe metadata_*.json locais que ainda não existem no GCS")
    parser.add_argument("--dry-run", action="store_true", help="Simular sem enviar")
    args = parser.parse_args()

    config = ConfigLoader().load_all()
    output_dir = Path(config.get_output_dir())
    if not output_dir.exists():
        print(f"Erro: diretório de saída não encontrado: {output_dir}")
        sys.exit(1)

    combos = []

    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"Erro: batch não encontrado: {batch_path}")
            sys.exit(1)
        with open(batch_path, encoding="utf-8") as f:
            batch = json.load(f)
        for item in batch.get("items", []):
            combos.append((item["dataset"], item["product"], item["territory"]))

    elif args.ds and args.prod and args.terr:
        combos.append((args.ds, args.prod, args.terr))

    elif args.ds and args.prod:
        for ds, prod, terr in _local_items(output_dir):
            if ds == args.ds and prod == args.prod:
                combos.append((ds, prod, terr))

    elif args.pending:
        existentes = _list_gcs_combos()
        todos = _local_items(output_dir)
        combos = [c for c in todos if c not in existentes]
        print(f"  Locais: {len(todos)}  |  No GCS: {len(existentes)}  |  Pendentes: {len(combos)}")

    elif args.reupload_missing_metadata:
        bucket = _get_bucket()
        metas = _list_local_metadata(output_dir)
        pendentes = []
        for ds, prod, terr, local_path in metas:
            blob_path = f"{GCS_HUB_ROOT}/{ds}/{prod}/{terr}/{local_path.name}"
            exists = bucket.blob(blob_path).exists()
            if not exists:
                pendentes.append((ds, prod, terr, local_path))
        print(f"  Metadados locais: {len(metas)}  |  Faltando no GCS: {len(pendentes)}")
        if not pendentes:
            print("  Todos os metadados já estão no GCS.")
            return
        enviados = 0
        for ds, prod, terr, local_path in pendentes:
            blob_path = f"{GCS_HUB_ROOT}/{ds}/{prod}/{terr}/{local_path.name}"
            if args.dry_run:
                print(f"     [DRY-RUN] {blob_path}")
            else:
                bucket.blob(blob_path).upload_from_filename(str(local_path))
                enviados += 1
        print(f"\n  ✅ {enviados} metadata(s) reenviado(s)")
        return

    else:
        parser.print_help()
        sys.exit(1)

    if not combos:
        print("Nada para enviar.")
        return

    print(f"\n{'🔍' if args.dry_run else '🚀'} Upload de {len(combos)} combo(s)...\n")
    total = 0
    for ds, prod, terr in combos:
        label = f"{ds}/{prod}/{terr}"
        print(f"  [{label}]")
        n = upload_combo(ds, prod, terr, output_dir, args.dry_run)
        total += n

    print(f"\n{'─' * 52}")
    if args.dry_run:
        print(f"  🔍 Dry-run: {len(combos)} combo(s), {total} arquivo(s)")
        print("  Execute sem --dry-run para enviar")
    else:
        print(f"  ✅ {len(combos)} combo(s), {total} arquivo(s) enviados")
        print("\n  Reconstruindo índice...")
        root = Path(__file__).resolve().parent.parent
        subprocess.run([sys.executable, "scripts/build_index.py", "--upload"],
                       cwd=str(root), check=True)
    print()


if __name__ == "__main__":
    main()
