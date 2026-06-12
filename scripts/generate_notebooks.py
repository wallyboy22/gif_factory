#!/usr/bin/env python3
"""
Generate one Colab notebook per (initiative, collection) pair.

Reads config/initiatives/ to discover initiatives, territory groups, and
collections, then produces ready-to-run .ipynb files in notebooks/<initiative>/.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.mapbiomas_data.config import ConfigLoader
from src.mapbiomas_data.core import InitiativeManager

NB_VERSION = 4
NB_MINOR = 4

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "notebooks")


def md_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [source],
    }


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [source],
    }


def escape_latex(s: str) -> str:
    return s.replace("_", r"\_")


def build_product_table(collection: dict) -> str:
    ds_id = collection["dataset_id"]
    ds_entry = config.datasets.get(ds_id, {})
    products = ds_entry.get("products", {})
    if not products:
        return ""
    lines = [
        "| # | Produto | Descrição | Viz |",
        "|---:|---|---|---|",
    ]
    for i, (pid, pinfo) in enumerate(sorted(products.items()), 1):
        name = pinfo.get("name", pid)
        viz = pinfo.get("visualization", "—")
        lines.append(f"| {i} | `{pid}` | {name} | {viz} |")
    return "\n".join(lines)


def build_territory_table(initiative: dict) -> str:
    groups = initiative.get("territory_groups", [])
    if not groups:
        return ""
    lines = [
        "| Grupo | ID | Territórios | Qtd |",
        "|---|---:|---:|---:|",
    ]
    for g in groups:
        gid = g["id"]
        name = g["name"]
        count = len(g["territory_ids"])
        examples = ", ".join(g["territory_ids"][:3])
        if count > 3:
            examples += " …"
        lines.append(f"| {name} | `{gid}` | {examples} | {count} |")
    return "\n".join(lines)


def make_notebook(initiative: dict, collection: dict) -> list:
    init_name = initiative.get("name", initiative["id"])
    coll_name = collection.get("name", collection["id"])
    ds_id = collection["dataset_id"]
    groups = initiative.get("territory_groups", [])
    all_territory_ids = []
    for g in groups:
        all_territory_ids.extend(g.get("territory_ids", []))

    cells = []

    # --- Title ---
    cells.append(md_cell(
        f"# {init_name} — {coll_name}\n\n"
        f"Pipeline completo: mapas → área stats → gráficos → composição.\n"
        f"Dados **{coll_name}** do [MapBiomas](https://mapbiomas.org/) via "
        f"[Google Earth Engine](https://earthengine.google.com/).\n"
    ))

    # --- Territory table ---
    terr_table = build_territory_table(initiative)
    if terr_table:
        cells.append(md_cell(
            f"## Territórios disponíveis\n\n{terr_table}\n"
        ))

    # --- Product catalog ---
    prod_table = build_product_table(collection)
    if prod_table:
        cells.append(md_cell(
            f"## Catálogo de produtos\n\n{prod_table}\n"
        ))

    # --- Validation cell ---
    cells.append(md_cell(
        "## Validação de configuração\n\n"
        "Verifica a consistência dos arquivos YAML e batch antes de executar.\n"
    ))
    cells.append(code_cell(
        "# Validar configuracao YAML e batch\n"
        "import os\n"
        '!python -m src.mapbiomas_data.interfaces.cli --validate\n'
    ))

    # --- Setup cell ---
    setup_code = (
        "# ============================================================\n"
        "# SETUP — roda uma vez no inicio da sessao\n"
        "# ============================================================\n\n"
        'import sys, os, subprocess\n\n'
        'repo = "gif_factory"\n'
        "if os.path.exists(repo):\n"
        '    subprocess.run(["git", "-C", repo, "pull"], check=True)\n'
        "else:\n"
        '    subprocess.run(["git", "clone", '
        '"https://github.com/wallyboy22/gif_factory.git"], check=True)\n'
        "%cd gif_factory\n\n"
        "# Limpar cache bytecode\n"
        '!find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; '
        'echo "Cache limpo"\n\n'
        "# Garantir fontes\n"
        '!apt-get install -qq fonts-dejavu-core 2>/dev/null; echo "OK"\n\n'
        '!pip install -q earthengine-api pillow pyyaml google-cloud-storage\n\n'
        "from google.colab import auth\n"
        "auth.authenticate_user()\n\n"
        "import ee\n"
        "ee.Authenticate()\n"
        f'ee.Initialize(project="{config.ee_project_id}")\n\n'
        'print("\\nSetup concluido.")\n'
    )
    cells.append(code_cell(setup_code))

    # --- Per-group batch cells ---
    for group in groups:
        gid = group["id"]
        gname = group["name"]
        tids = group.get("territory_ids", [])
        n_prods = len(config.datasets.get(ds_id, {}).get("products", {}).keys())

        md_comment = (
            f"### Grupo: {gname} ({gid})\n\n"
            f"**{len(tids)} territórios × {n_prods} produtos**\n\n"
            "Sequência completa:\n"
            "1. **Pipeline** — download EE → frames → collages → GIFs\n"
            "2. **Area Stats** — (assíncrono) consulta EE, exporta área por classe para GCS\n"
            "3. **Charts** — gera PNGs: distribuição anual + série temporal\n"
            "4. **Compose** — funde mapas + gráficos lado a lado em GIF\n\n"
            "Cada comando usa `--gcs` para salvar no storage permanente.\n"
            "Use `--resume` para retomar se o ambiente cair.\n"
        )
        cells.append(md_cell(md_comment))

        batch_python = (
            "# (1) Gerar batch JSON para este grupo\n"
            "import json, tempfile, os\n"
            f'collection_ds = "{ds_id}"\n'
            f'group_id = "{gid}"\n\n'
            "from src.mapbiomas_data.config import ConfigLoader\n"
            "cfg = ConfigLoader()\n"
            "cfg.load_all()\n"
            "ds = cfg.datasets.get(collection_ds, {})\n"
            "product_ids = sorted(ds.get(\"products\", {}).keys())\n\n"
            f"territory_ids = {json.dumps(tids)}\n\n"
            "items = []\n"
            "for tid in territory_ids:\n"
            "    for pid in product_ids:\n"
            '        items.append({"dataset": collection_ds, '
            '"product": pid, "territory": tid})\n\n'
            f'n_terr = {len(tids)}\n'
            f'n_prod = {n_prods}\n'
            'print(f"Batch: {len(items)} combos '
            '({group_id}: {n_terr} territorios x {n_prod} produtos)")\n\n'
            'tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", '
            'delete=False)\n'
            "json.dump({\"items\": items}, tmp)\n"
            "tmp.close()\n"
            "os.environ[\"OPTBATCH\"] = tmp.name\n"
        )
        cells.append(code_cell(batch_python))

        # Pipeline
        cells.append(code_cell(
            "# (2) Pipeline: download EE → frames → collages → GIFs\n"
            "# Pre-requisito: batch gerado, autenticacao EE OK\n"
            "import os\n"
            '!python -m src.mapbiomas_data.interfaces.cli '
            "--generate --batch $OPTBATCH "
            "--workers 6 --resume-from-gcs --font-scale 1.0 --gcs\n"
        ))

        # Area stats
        cells.append(code_cell(
            "# (3) Area stats: computa area por classe (assincrono, EE task)\n"
            "# Pre-requisito: pipeline executado (para config/territorios validos)\n"
            "# Exporta CSV para GCS. Monitora tasks ate completar.\n"
            "import os\n"
            '!python -m src.mapbiomas_data.interfaces.cli '
            "--area-stats --batch $OPTBATCH --resume --gcs\n"
        ))

        # Charts
        cells.append(code_cell(
            "# (4) Charts: gera graficos anual + serie temporal\n"
            "# Pre-requisito: area_stats CSVs disponiveis em area_stats/\n"
            "# Gera PNGs em charts_annual/ e charts_timeseries/\n"
            "import os\n"
            '!python -m src.mapbiomas_data.interfaces.cli '
            "--charts --batch $OPTBATCH\n"
        ))

        # Compose
        cells.append(code_cell(
            "# (5) Compose: funde GIF do mapa + graficos lado a lado\n"
            "# Pre-requisito: charts PNGs + GIFs gerados\n"
            "# Gera GIF final em composed/\n"
            "import os\n"
            '!python -m src.mapbiomas_data.interfaces.cli '
            "--compose --batch $OPTBATCH\n"
        ))

    # --- "Tudo" cell (all groups at once) ---
    if len(groups) > 1:
        all_batch_python = (
            "# Gerar batch para TODOS os grupos\n"
            "import json, tempfile, os\n"
            f'collection_ds = "{ds_id}"\n\n'
            "from src.mapbiomas_data.config import ConfigLoader\n"
            "cfg = ConfigLoader()\n"
            "cfg.load_all()\n"
            "ds = cfg.datasets.get(collection_ds, {})\n"
            "product_ids = sorted(ds.get(\"products\", {}).keys())\n\n"
            f"all_territories = {json.dumps(all_territory_ids)}\n\n"
            "items = []\n"
            "for tid in all_territories:\n"
            "    for pid in product_ids:\n"
            '        items.append({"dataset": collection_ds, '
            '"product": pid, "territory": tid})\n\n'
            "n_terr = len(all_territories)\n"
            "n_prod = len(product_ids)\n"
            f'print(f"Batch total: {{len(items)}} combos'
            f' ({{n_terr}} territorios x {{n_prod}} produtos)")\n\n'
            'tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", '
            'delete=False)\n'
            "json.dump({\"items\": items}, tmp)\n"
            "tmp.close()\n"
            "os.environ[\"OPTBATCH\"] = tmp.name\n"
        )
        cells.append(code_cell(all_batch_python))

        cells.append(md_cell(
            "### Executar tudo (todos os grupos)\n\n"
            "Sequência completa: pipeline → area stats → charts → compose.\n"
        ))

        cells.append(code_cell(
            "# Pipeline: todos os grupos\n"
            "import os\n"
            '!python -m src.mapbiomas_data.interfaces.cli '
            "--generate --batch $OPTBATCH "
            "--workers 6 --resume-from-gcs --font-scale 1.0 --gcs\n"
        ))

        cells.append(code_cell(
            "# Area stats: todos os grupos\n"
            "import os\n"
            '!python -m src.mapbiomas_data.interfaces.cli '
            "--area-stats --batch $OPTBATCH --resume --gcs\n"
        ))

        cells.append(code_cell(
            "# Charts: todos os grupos\n"
            "import os\n"
            '!python -m src.mapbiomas_data.interfaces.cli '
            "--charts --batch $OPTBATCH\n"
        ))

        cells.append(code_cell(
            "# Compose: todos os grupos\n"
            "import os\n"
            '!python -m src.mapbiomas_data.interfaces.cli '
            "--compose --batch $OPTBATCH\n"
        ))

    # --- Sync cell ---
    cells.append(code_cell(
        "# Sync final: index + Looker CSVs\n"
        "# Os dados ja foram para o GCS via --gcs em cada etapa.\n"
        '!python scripts/index/build_index.py --upload\n'
        f'!python scripts/looker/build_looker_csvs_from_gcs.py '
        f'--dataset {ds_id}\n'
    ))

    # --- Links ---
    cells.append(md_cell(
        "---\n"
        "## Links úteis\n\n"
        "| Recurso | Link |\n"
        "|---|---|\n"
        "| **Looker Studio** | "
        "[Abrir dashboard](https://datastudio.google.com/u/0/reporting/"
        "179f6b47-8f6e-4f51-abd5-75b7ae018a2b/page/XDzxF) |\n"
        "| **GitHub** | "
        "[github.com/wallyboy22/gif_factory]"
        "(https://github.com/wallyboy22/gif_factory) |\n"
        "| **MapBiomas** | "
        "[plataforma.brasil.mapbiomas.org]"
        "(https://plataforma.brasil.mapbiomas.org) |\n\n"
        "---\n\n"
        "*Gerado por [Fábrica de GIFs — IPAM / MapBiomas]"
        "(https://github.com/wallyboy22/gif_factory)*\n"
    ))

    return cells


def generate_notebooks():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    initiatives = im.list_initiatives()
    if not initiatives:
        print("Nenhuma iniciativa encontrada.")
        return

    for init_summary in initiatives:
        iid = init_summary["id"]
        initiative = im.get_initiative(iid)
        collections = initiative.get("collections", [])

        init_out = os.path.join(OUTPUT_DIR, iid)
        os.makedirs(init_out, exist_ok=True)

        for coll in collections:
            cid = coll["id"]
            cells = make_notebook(initiative, coll)

            notebook = {
                "nbformat": NB_VERSION,
                "nbformat_minor": NB_MINOR,
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3",
                    },
                    "language_info": {
                        "name": "python",
                        "version": "3.10.0",
                    },
                },
                "cells": cells,
            }

            fname = f"{iid}_{cid}.ipynb"
            fpath = os.path.join(init_out, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(notebook, f, ensure_ascii=False, indent=1)

            ds_entry = config.datasets.get(coll["dataset_id"], {})
            n_coll = len(ds_entry.get("products", {}))
            n_groups = len(initiative.get("territory_groups", []))
            n_terr = sum(
                len(g.get("territory_ids", []))
                for g in initiative.get("territory_groups", [])
            )
            print(f"  [OK] {fname}  |  {n_coll} produtos, "
                  f"{n_groups} grupos, {n_terr} territorios")


if __name__ == "__main__":
    global config, im
    config = ConfigLoader()
    config.load_all()
    im = InitiativeManager(config)

    print("Gerando notebooks por iniciativa/colecao...\n")
    generate_notebooks()
    print("\nPronto!")
