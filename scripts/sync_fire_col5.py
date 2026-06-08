"""
sync_fire_col5.py - Sobe pendentes, rebuilda index e CSVs do Looker Studio.

Uso:
    python scripts/sync_fire_col5.py                    # sync completo
    python scripts/sync_fire_col5.py --dry-run          # só simular
    python scripts/sync_fire_col5.py --skip-upload      # upload GCS não, só CSVs
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Sync Fire Col5: upload + index + Looker CSVs")
    parser.add_argument("--dry-run", action="store_true", help="Simular sem enviar")
    parser.add_argument("--skip-upload", action="store_true",
                        help="Pular etapa de upload para GCS")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    python = sys.executable

    print(f"\n{'=' * 60}")
    print(f"SYNC FIRE COLLECTION 5")
    print(f"{'=' * 60}")

    # ── Step 1: Upload pendentes ──────────────────────────
    if args.skip_upload:
        print("\n[1/3] Upload pulado (--skip-upload)")
    else:
        print("\n[1/3] Subindo arquivos pendentes para o GCS...")
        upload_cmd = [python, "scripts/upload_to_gcs.py", "--pending"]
        if args.dry_run:
            upload_cmd.append("--dry-run")
        result = subprocess.run(upload_cmd, cwd=str(root))
        if result.returncode != 0:
            print("[ERRO] upload_to_gcs.py falhou")
            sys.exit(1)

    # ── Step 2: Rebuild index ─────────────────────────────
    print("\n[2/3] Reconstruindo índice...")
    index_cmd = [python, "scripts/build_index.py"]
    if not args.dry_run:
        index_cmd.append("--upload")
    result = subprocess.run(index_cmd, cwd=str(root))
    if result.returncode != 0:
        print("[ERRO] build_index.py falhou")
        sys.exit(1)

    # ── Step 3: Rebuild Looker CSVs ───────────────────────
    print("\n[3/3] Gerando CSVs do Looker Studio...")
    looker_cmd = [
        python, "scripts/build_looker_csvs_from_gcs.py",
        "--dataset", "brasil_fire_col5",
    ]
    if args.dry_run:
        looker_cmd.append("--no-upload")
    result = subprocess.run(looker_cmd, cwd=str(root))
    if result.returncode != 0:
        print("[ERRO] build_looker_csvs_from_gcs.py falhou")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"SYNC CONCLUÍDO")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
