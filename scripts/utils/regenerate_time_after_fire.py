"""
Regenera time_after_fire (Fire Col 5) com nova paleta — 0 = branco.
Apaga dados antigos e gera do zero para todos os territorios.

Uso:
    python scripts/regenerate_time_after_fire.py
    python scripts/regenerate_time_after_fire.py --workers 6
"""

import argparse
import os
import shutil
import stat
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

cwd = os.getcwd()
if not os.path.exists(os.path.join(cwd, 'src')):
    parent = os.path.dirname(cwd)
    while not os.path.exists(os.path.join(parent, 'src')) and parent != os.path.dirname(parent):
        parent = os.path.dirname(parent)
    if os.path.exists(os.path.join(parent, 'src')):
        os.chdir(parent)

sys.path.insert(0, os.getcwd())

from src.ipam_gif_factory.config import ConfigLoader
from src.ipam_gif_factory.core.pipeline import Pipeline

DATASET_ID = "brasil_fire_col5"
PRODUCT_ID = "time_after_fire"

TERRITORIES = [
    "brasil",
    "acre", "alagoas", "amapa", "amazonas", "bahia", "ceara",
    "espirito_santo", "goias", "maranhao", "mato_grosso", "mato_grosso_do_sul",
    "minas_gerais", "para", "paraiba", "parana", "pernambuco", "piaui",
    "rio_de_janeiro", "rio_grande_do_norte", "rio_grande_do_sul",
    "rondonia", "roraima", "santa_catarina", "sao_paulo", "sergipe", "tocantins",
    "df",
    "amazonia", "caatinga", "cerrado", "mata_atlantica", "pampa", "pantanal",
    "biomas",
    "bap", "bap_planalto",
    "matopiba", "matopiba_cerrado",
    "centro_oeste", "nordeste", "norte", "sudeste", "sul",
]

print_lock = threading.Lock()


def _remove_readonly(func, path, exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def delete_outputs(config):
    output_base = config.get_output_dir()
    product_dir = os.path.join(output_base, DATASET_ID, PRODUCT_ID)

    if not os.path.exists(product_dir):
        print(f"  Nenhum dado anterior encontrado em: {product_dir}")
        return

    print(f"\nApagando dados antigos de:\n  {product_dir}")
    shutil.rmtree(product_dir, onerror=_remove_readonly)
    print("  [OK] Dados antigos removidos.\n")


def process_one(config, territory):
    pipeline = Pipeline(config)

    with print_lock:
        print(f"\n[INICIANDO] time_after_fire / {territory}")

    result = pipeline.run(
        dataset_id=DATASET_ID,
        product_id=PRODUCT_ID,
        territory_id=territory,
        create_collage=True,
        add_labels=True,
        vertical_dimension=1560,
        cell_height=300,
        resume=False,
    )

    status = result.get("status", "erro")
    with print_lock:
        if status == "success":
            gif = result.get("gif_path", "?")
            print(f"  [OK] {territory} -> {gif}")
        else:
            erro = result.get("error", "desconhecido")
            print(f"  [FALHA] {territory}: {erro}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Regenera time_after_fire (Fire Col5) com paleta corrigida (0=#ffffff)"
    )
    parser.add_argument("--workers", type=int, default=4,
                        help="Workers paralelos (padrao: 4)")
    args = parser.parse_args()

    config = ConfigLoader()

    print("=" * 60)
    print("REGENERACAO: Time After Fire (Col5)")
    print("  Corrigido: valor 0 = #ffffff (branco)")
    print(f"  Territorios: {len(TERRITORIES)}")
    print(f"  Workers: {args.workers}")
    print("=" * 60)

    delete_outputs(config)

    total = len(TERRITORIES)
    ok = 0
    fail = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_one, config, t): t
            for t in TERRITORIES
        }
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            if r.get("status") == "success":
                ok += 1
            else:
                fail += 1
            if i % 5 == 0 or i == total:
                print(f"\n--- Progresso: {i}/{total} | OK: {ok} | Falha: {fail} ---")

    print(f"\n{'=' * 60}")
    print(f"CONCLUIDO: {ok} OK | {fail} falha(s) | {total} total")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
