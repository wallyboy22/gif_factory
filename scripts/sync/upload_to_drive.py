#!/usr/bin/env python3
"""
upload_to_drive.py - Sobe arquivos de mídia locais (GIF, collage, frames, metadata) para o Google Drive.

Uso:
    python scripts/upload_to_drive.py --pending                          # tudo que falta no Drive
    python scripts/upload_to_drive.py --ds drc_lulc_col1 --prod nivel1 --terr drc_kinshasa
    python scripts/upload_to_drive.py --pending --dry-run                # só mostrar
    python scripts/upload_to_drive.py --force                            # sobrescreve mesmo se existir
"""
import argparse
import json
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")

from mapbiomas_data.config import ConfigLoader

DRIVE_ROOT_FOLDER_ID = "1QWd3SmKRJ2l-OYw2gf7JXJVQr2z42gG6"

_SERVICE = None


def _get_service():
    global _SERVICE
    if _SERVICE is None:
        from google.auth import default
        from googleapiclient.discovery import build

        creds, _ = default(scopes=["https://www.googleapis.com/auth/drive"])
        _SERVICE = build("drive", "v3", credentials=creds)
    return _SERVICE


def _find_child(folder_id: str, name: str) -> dict | None:
    svc = _get_service()
    res = svc.files().list(
        q=f"'{folder_id}' in parents and name = '{name}' and trashed = false",
        fields="files(id, name, mimeType)",
        pageSize=10,
    ).execute()
    files = res.get("files", [])
    return files[0] if files else None


def _get_or_create_folder(parent_id: str, name: str) -> str:
    svc = _get_service()
    existing = _find_child(parent_id, name)
    if existing:
        return existing["id"]
    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    created = svc.files().create(body=body, fields="id").execute()
    return created["id"]


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


def _file_names_on_drive(folder_id: str) -> set:
    svc = _get_service()
    names = set()
    page_token = None
    while True:
        res = svc.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(name), nextPageToken",
            pageSize=500,
            pageToken=page_token,
        ).execute()
        names.update(f["name"] for f in res.get("files", []))
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return names


def _upload_file(parent_id: str, name: str, local_path: Path, dry_run: bool, force: bool) -> bool:
    svc = _get_service()
    existing = _find_child(parent_id, name)
    if existing and not force:
        print(f"     (existe, pula) {name}")
        return False
    if dry_run:
        print(f"     [DRY-RUN] {name}")
        return True
    media = None
    if not dry_run:
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(str(local_path), resumable=True)
    body = {"name": name, "parents": [parent_id]}
    if existing and force:
        svc.files().update(fileId=existing["id"], body=body, media_body=media).execute()
    else:
        svc.files().create(body=body, media_body=media).execute()
    print(f"     OK {name}")
    return True


def upload_combo(ds: str, prod: str, terr: str, output_dir: Path, dry_run: bool = False, force: bool = False) -> int:
    local_dir = output_dir / ds / prod / terr
    if not local_dir.exists():
        return 0

    svc = _get_service()
    root = DRIVE_ROOT_FOLDER_ID
    prod_folder = _get_or_create_folder(root, prod)
    terr_folder = _get_or_create_folder(prod_folder, terr)

    enviados = 0
    for rel_dir in sorted(p for p in local_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        folder_path = local_dir / rel_dir.name
        sub_folder = _get_or_create_folder(terr_folder, rel_dir.name)
        for fpath in sorted(folder_path.iterdir()):
            if not fpath.is_file():
                continue
            if fpath.name.startswith(".state"):
                continue
            if _upload_file(sub_folder, fpath.name, fpath, dry_run, force):
                enviados += 1
    return enviados


def main():
    parser = argparse.ArgumentParser(description="Upload media files to Google Drive")
    parser.add_argument("--ds", help="Dataset ID (ex.: drc_lulc_col1)")
    parser.add_argument("--prod", help="Product ID (ex.: nivel0)")
    parser.add_argument("--terr", help="Territory ID (ex.: drc, drc_kinshasa)")
    parser.add_argument("--pending", action="store_true", help="Upload tudo que existe local mas não no Drive")
    parser.add_argument("--force", action="store_true", help="Sobrescrever arquivos que já existem no Drive")
    parser.add_argument("--dry-run", action="store_true", help="Simular sem enviar")
    args = parser.parse_args()

    config = ConfigLoader().load_all()
    output_dir = Path(config.get_output_dir())
    if not output_dir.exists():
        print(f"Erro: diretório de saída não encontrado: {output_dir}")
        sys.exit(1)

    combos = []

    if args.ds and args.prod and args.terr:
        combos.append((args.ds, args.prod, args.terr))
    elif args.ds and args.prod:
        for ds, prod, terr in _local_items(output_dir):
            if ds == args.ds and prod == args.prod:
                combos.append((ds, prod, terr))
    elif args.pending:
        combos = _local_items(output_dir)
    else:
        parser.print_help()
        sys.exit(1)

    if not combos:
        print("Nada para enviar.")
        return

    print(f"\n{'[DRY-RUN]' if args.dry_run else '[UPLOAD]'} {len(combos)} combo(s) para o Drive...\n")
    total = 0
    for ds, prod, terr in combos:
        print(f"  [{ds}/{prod}/{terr}]")
        total += upload_combo(ds, prod, terr, output_dir, args.dry_run, args.force)

    print(f"\n{'-' * 52}")
    if args.dry_run:
        print(f"  [DRY-RUN] {len(combos)} combo(s), {total} arquivo(s)")
        print("  Execute sem --dry-run para enviar")
    else:
        print(f"  OK: {len(combos)} combo(s), {total} arquivo(s) enviados")
    print()


if __name__ == "__main__":
    main()
