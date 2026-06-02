#!/usr/bin/env python3
"""IPAM GIF Factory - Entry point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from src.ipam_gif_factory.interfaces.cli import main as cli_main


def main():
    if len(sys.argv) > 1:
        cli_main(sys.argv[1:])
    else:
        print("IPAM GIF Factory v0.1.0")
        print("Use --help para ver os comandos disponíveis.")
        print()
        print("Exemplos:")
        print("  python main.py --list-categories")
        print("  python main.py --list-datasets")
        print("  python main.py --list-products brasil_fire_col3")
        print("  python main.py --list-territories")
        print("  python main.py --list-viz")
        print("  python scripts/main.py --generate --dataset brasil_fire_col3 --product annual_burned --territory df")
        print()


if __name__ == "__main__":
    main()
