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

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")

from mapbiomas_data.config import ConfigLoader
from mapbiomas_data.core import theme as theme_mod

GCS_BUCKET = "mapbiomas-fire"
GCS_HUB_ROOT = "data-container"
GCS_PROJECT = "mapbiomas-fire-485203"

# Singleton: cria cliente uma vez só
_BUCKET = None


def _combo_dir(output_dir: Path, ds: str, prod: str, terr: str,
               theme: str = None) -> Path:
    return Path(theme_mod.combo_dir(str(output_dir), ds, prod, terr, theme))


def _blob_prefix(ds: str, prod: str, terr: str, theme: str = None) -> str:
    prefix = f"{GCS_HUB_ROOT}/{ds}/{prod}/{terr}"
    if theme_mod.normalize_theme(theme) != theme_mod.DEFAULT_THEME:
        prefix = f"{prefix}/{theme_mod.normalize_theme(theme)}"
    return f"{prefix}/"


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
        if len(parts) >= 4 and parts[3] == "dark":
            existentes.add((parts[0], parts[1], parts[2], "dark"))
        elif len(parts) >= 3:
            existentes.add((parts[0], parts[1], parts[2], "light"))
    return existentes


def _local_items(output_dir: Path) -> list:
    items = []
    for gif_path in output_dir.rglob("*.gif"):
        try:
            rel = gif_path.relative_to(output_dir)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) >= 4 and parts[3] == "dark":
            items.append((parts[0], parts[1], parts[2], "dark"))
        elif len(parts) >= 3:
            items.append((parts[0], parts[1], parts[2], "light"))
    return sorted(set(items))


def _list_local_metadata(output_dir: Path) -> list:
    """Lista todos os metadata_*.json locais: (ds, prod, terr, theme, Path)."""
    items = []
    for meta_path in output_dir.rglob("metadata_*.json"):
        try:
            rel = meta_path.relative_to(output_dir)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) >= 5 and parts[3] == "dark":
            items.append((parts[0], parts[1], parts[2], "dark", meta_path))
        elif len(parts) >= 4:
            items.append((parts[0], parts[1], parts[2], "light", meta_path))
    return sorted(items)


def is_combo_complete_on_gcs(ds: str, prod: str, terr: str, output_dir: Path,
                             theme: str = None) -> bool:
    """Verifica no GCS se todos os arquivos esperados de um combo existem."""
    local_dir = _combo_dir(output_dir, ds, prod, terr, theme)
    meta_local = local_dir / f"metadata_{prod}.json"
    if not meta_local.is_file():
        return False

    with open(meta_local, encoding="utf-8") as f:
        meta = json.load(f)

    bucket = _get_bucket()
    prefix = _blob_prefix(ds, prod, terr, theme)

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


def upload_combo(ds: str, prod: str, terr: str, output_dir: Path,
                 dry_run: bool = False, theme: str = None) -> int:
    local_dir = _combo_dir(output_dir, ds, prod, terr, theme)
    if not local_dir.exists():
        return 0

    bucket = _get_bucket()
    prefix = _blob_prefix(ds, prod, terr, theme)
    enviados = 0
    for fpath in sorted(local_dir.rglob("*")):
        if not fpath.is_file():
            continue
        name = fpath.name
        if name.startswith(".state"):
            continue
        rel = fpath.relative_to(local_dir).as_posix()
        if theme_mod.normalize_theme(theme) == "light" and rel.split("/", 1)[0] == "dark":
            continue
        blob_path = f"{prefix}{rel}"
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
    parser.add_argument("--theme", type=str, default=None,
                        choices=list(theme_mod.VALID_THEMES),
                        help="Tema dos combos (light/dark). Padrão: light")
    args = parser.parse_args()

    config = ConfigLoader().load_all()
    output_dir = Path(config.get_output_dir())
    if not output_dir.exists():
        print(f"Erro: diretório de saída não encontrado: {output_dir}")
        sys.exit(1)

    from mapbiomas_data.core import DatasetManager
    datasets = DatasetManager(config)

    def _resolve(ds: str, prod: str, item_theme=None):
        """Resolve alias *_black e o tema efetivo; retorna (prod_base, theme)."""
        try:
            pinfo = datasets.get_product(ds, prod)
        except KeyError:
            pinfo = {}
        base = pinfo.get("id", prod)
        resolved = theme_mod.resolve_theme(
            item_theme if item_theme is not None else args.theme,
            pinfo.get("alias_theme"),
        )
        return base, resolved

    combos = []

    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"Erro: batch não encontrado: {batch_path}")
            sys.exit(1)
        with open(batch_path, encoding="utf-8") as f:
            batch = json.load(f)
        for item in batch.get("items", []):
            base, theme = _resolve(item["dataset"], item["product"], item.get("theme"))
            combos.append((item["dataset"], base, item["territory"], theme))

    elif args.ds and args.prod and args.terr:
        base, theme = _resolve(args.ds, args.prod)
        combos.append((args.ds, base, args.terr, theme))

    elif args.ds and args.prod:
        for ds, prod, terr, theme in _local_items(output_dir):
            if ds == args.ds and prod == args.prod:
                combos.append((ds, prod, terr, theme))

    elif args.pending:
        existentes = _list_gcs_combos()
        todos = _local_items(output_dir)
        combos = [c for c in todos if c not in existentes]
        print(f"  Locais: {len(todos)}  |  No GCS: {len(existentes)}  |  Pendentes: {len(combos)}")

    elif args.reupload_missing_metadata:
        bucket = _get_bucket()
        metas = _list_local_metadata(output_dir)
        pendentes = []
        for ds, prod, terr, theme, local_path in metas:
            prefix = _blob_prefix(ds, prod, terr, theme)
            blob_path = f"{prefix}{local_path.name}"
            exists = bucket.blob(blob_path).exists()
            if not exists:
                pendentes.append((ds, prod, terr, theme, local_path))
        print(f"  Metadados locais: {len(metas)}  |  Faltando no GCS: {len(pendentes)}")
        if not pendentes:
            print("  Todos os metadados já estão no GCS.")
            return
        enviados = 0
        for ds, prod, terr, theme, local_path in pendentes:
            blob_path = f"{_blob_prefix(ds, prod, terr, theme)}{local_path.name}"
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
    for ds, prod, terr, theme in combos:
        suffix = f" [{theme}]" if theme != theme_mod.DEFAULT_THEME else ""
        label = f"{ds}/{prod}/{terr}{suffix}"
        print(f"  [{label}]")
        n = upload_combo(ds, prod, terr, output_dir, args.dry_run, theme=theme)
        total += n

    print(f"\n{'─' * 52}")
    if args.dry_run:
        print(f"  🔍 Dry-run: {len(combos)} combo(s), {total} arquivo(s)")
        print("  Execute sem --dry-run para enviar")
    else:
        print(f"  ✅ {len(combos)} combo(s), {total} arquivo(s) enviados")
        print("\n  Reconstruindo índice...")
        root = Path(__file__).resolve().parent.parent
        subprocess.run([sys.executable, "scripts/index/build_index.py", "--upload"],
                       cwd=str(root), check=True)
    print()


if __name__ == "__main__":
    main()
