"""Copia apenas os GIFs de uma pasta de outputs, preservando a estrutura relativa.

O destino recebe uma subpasta com o nome da pasta de origem (ex.: peru_fire_col2),
para que varios datasets possam conviver no mesmo destino.

Uso:
    python scripts/copy_gifs_clean.py
    python scripts/copy_gifs_clean.py --src outputs/v002/brasil_fire_col5
    python scripts/copy_gifs_clean.py --src outputs/v002/peru_fire_col2 --dst outputs/v002_gif_clean --flat
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

DEFAULT_SRC = Path("outputs/v002/peru_fire_col2")
DEFAULT_DST = Path("outputs/v002_gif_clean")


def _strip_product_suffix(rel: Path, suffix: str) -> Path:
    """Remove `suffix` do nome do produto (1o nivel), juntando variantes numa pasta so."""
    if not suffix:
        return rel
    parts = list(rel.parts)
    if parts and parts[0].endswith(suffix):
        parts[0] = parts[0][: -len(suffix)]
    return Path(*parts)


def copy_gifs(
    src: Path,
    dst: Path,
    suffix: str = ".gif",
    strip_gifs_dir: bool = True,
    strip_suffix: str = "",
) -> tuple[int, int]:
    """Copia arquivos com `suffix` de `src` para `dst` mantendo a estrutura relativa.

    Com `strip_gifs_dir`, remove o nivel `gifs/` do caminho: como o destino so
    recebe GIFs, `<produto>/<territorio>/gifs/x.gif` vira `<produto>/<territorio>/x.gif`.

    Retorna (quantidade_copiada, bytes_totais).
    """
    if not src.is_dir():
        raise SystemExit(f"Pasta de origem nao encontrada: {src}")

    count = 0
    total_bytes = 0

    for file in src.rglob(f"*{suffix}"):
        if not file.is_file():
            continue
        rel = file.relative_to(src)
        if strip_gifs_dir and rel.parent.name == "gifs":
            rel = rel.parent.parent / rel.name
        rel = _strip_product_suffix(rel, strip_suffix)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        count += 1
        total_bytes += file.stat().st_size

    return count, total_bytes


def copy_collages(
    src: Path,
    dst: Path,
    source_dir: str = "collages_combined",
    target_dir: str = "",
    strip_suffix: str = "",
) -> tuple[int, int]:
    """Copia as colagens (PNG) de `source_dir` para o mesmo nivel dos GIFs."""
    if not src.is_dir():
        raise SystemExit(f"Pasta de origem nao encontrada: {src}")

    count = 0
    total_bytes = 0

    for file in src.rglob("*.png"):
        if not file.is_file():
            continue
        parts = file.relative_to(src).parts
        if source_dir not in parts:
            continue
        rel_parts = [p for p in parts if p != source_dir]
        base = dst / _strip_product_suffix(Path(*rel_parts[:-1]), strip_suffix)
        target = (base / target_dir / rel_parts[-1]) if target_dir else (base / rel_parts[-1])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        count += 1
        total_bytes += file.stat().st_size

    return count, total_bytes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copia apenas GIFs preservando a estrutura de pastas."
    )
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC, help="Pasta de origem")
    parser.add_argument("--dst", type=Path, default=DEFAULT_DST, help="Pasta raiz de destino")
    parser.add_argument("--suffix", default=".gif", help="Extensao a copiar (padrao: .gif)")
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Copia direto na pasta de destino, sem criar subpasta com o nome da origem",
    )
    parser.add_argument(
        "--keep-gifs-dir",
        action="store_true",
        help="Mantem o nivel 'gifs/' no caminho de destino",
    )
    parser.add_argument(
        "--collages",
        action="store_true",
        help="Copia tambem as colagens PNG de collages_combined/ para a mesma pasta dos GIFs",
    )
    parser.add_argument(
        "--merge-black",
        action="store_true",
        help="Junta as variantes '_black' na mesma pasta do produto sem o sufixo",
    )
    args = parser.parse_args()

    dst = args.dst if args.flat else args.dst / args.src.name
    strip_suffix = "_black" if args.merge_black else ""

    count, total_bytes = copy_gifs(
        args.src, dst, args.suffix,
        strip_gifs_dir=not args.keep_gifs_dir,
        strip_suffix=strip_suffix,
    )

    mb = total_bytes / (1024 * 1024)
    print(f"Origem : {args.src.resolve()}")
    print(f"Destino: {dst.resolve()}")
    print(f"Copiados: {count} arquivo(s) {args.suffix} ({mb:.2f} MB)")

    if args.collages:
        c_count, c_bytes = copy_collages(args.src, dst, strip_suffix=strip_suffix)
        print(f"Colagens: {c_count} arquivo(s) .png ({c_bytes / (1024 * 1024):.2f} MB)")


if __name__ == "__main__":
    main()
