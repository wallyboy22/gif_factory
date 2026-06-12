#!/usr/bin/env python3
"""
process_uf.py - Processa todas as 27 Unidades da Federação para um dataset+produto.

Uso:
    python scripts/process_uf.py --ds brasil_degradation_col10_1 --prod secondary_vegetation_coverage
    python scripts/process_uf.py --ds X --prod Y --workers 8
    python scripts/process_uf.py --ds X --prod Y --resume
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

UFS = [
    "uf_acre", "uf_alagoas", "uf_amapa", "uf_amazonas",
    "uf_bahia", "uf_ceara", "uf_df", "uf_espirito_santo",
    "uf_goias", "uf_maranhao", "uf_mato_grosso", "uf_mato_grosso_do_sul",
    "uf_minas_gerais", "uf_para", "uf_paraiba", "uf_parana",
    "uf_pernambuco", "uf_piaui", "uf_rio_de_janeiro", "uf_rio_grande_do_norte",
    "uf_rio_grande_do_sul", "uf_rondonia", "uf_roraima", "uf_santa_catarina",
    "uf_sao_paulo", "uf_sergipe", "uf_tocantins",
]


def main():
    parser = argparse.ArgumentParser(description="Process all 27 Brazilian states for a product")
    parser.add_argument("--ds", required=True, help="Dataset ID")
    parser.add_argument("--prod", required=True, help="Product ID")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers (default: 4)")
    parser.add_argument("--resume", action="store_true", help="Pular itens já processados")
    parser.add_argument("--font-scale", type=float, default=1.0, help="Escala das fontes (padrao: 1.0)")
    args = parser.parse_args()

    items = [
        {"dataset": args.ds, "product": args.prod, "territory": uf}
        for uf in UFS
    ]

    batch = {
        "created_at": datetime.now().isoformat(),
        "total": len(items),
        "items": items,
    }

    fd, batch_path = tempfile.mkstemp(suffix=".json", prefix="batch_uf_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(batch, f, indent=2, ensure_ascii=False)

    print(f"🎬 Processando {args.ds} / {args.prod} para {len(UFS)} UFs")
    print(f"   Workers: {args.workers}  |  Resume: {args.resume}")
    print()

    root = Path(__file__).resolve().parent.parent
    cmd = [
        sys.executable, "-m", "src.mapbiomas_data.interfaces.cli",
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


if __name__ == "__main__":
    main()
