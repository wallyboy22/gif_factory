"""
sync_fire_col5.py - Varre metadados no GCS e atualiza planilhas do Looker Studio.

Uso:
    python scripts/sync_fire_col5.py              # sync completo
    python scripts/sync_fire_col5.py --no-upload  # gera CSVs local, nao sobe
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Sync Fire Col5: atualiza Looker CSVs do GCS")
    parser.add_argument("--no-upload", action="store_true",
                        help="Gerar CSVs localmente sem subir para GCS")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    python = sys.executable

    print(f"\n{'=' * 60}")
    print(f"SYNC FIRE COLLECTION 5 — LOOKER STUDIO")
    print(f"{'=' * 60}")

    cmd = [
        python, "scripts/looker/build_looker_csvs_from_gcs.py",
        "--dataset", "brasil_fire_col5",
    ]
    if args.no_upload:
        cmd.append("--no-upload")

    result = subprocess.run(cmd, cwd=str(root))
    if result.returncode != 0:
        print("[ERRO] build_looker_csvs_from_gcs.py falhou")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"SYNC CONCLUIDO")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
