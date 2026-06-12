"""
M2 Dispatch — Execucao do batch a partir da UI.
Le os checkboxes da GIFactoryUI, dispara ThreadPoolExecutor,
e loga progresso via ui.log().
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.mapbiomas_data.core.pipeline import Pipeline
from .nb_setup import build_gif_cache


def start_batch(ui, ctx):
    """
    Le os checkboxes da interface e dispara o batch.

    Args:
        ui: instancia de GIFactoryUI (com chk_products, chk_territories, log)
        ctx: NotebookContext (config, workers, gif_cache)
    """
    selected_products = [
        (ds_id, prod_id)
        for (ds_id, prod_id), chk in ui.chk_products.items()
        if chk.value
    ]
    selected_territories = [
        tid for tid, chk in ui.chk_territories.items() if chk.value
    ]

    if not selected_products:
        ui.log("Selecione pelo menos 1 produto.", "error")
        return
    if not selected_territories:
        ui.log("Selecione pelo menos 1 territorio.", "error")
        return

    combos = [
        (ds_id, prod_id, tid)
        for ds_id, prod_id in selected_products
        for tid in selected_territories
    ]
    total = len(combos)
    workers = ui.workers_tx.value
    resume = ui.resume_cb.value
    collage = ui.collage_cb.value
    dimension = ui.dimension_tx.value

    ui.clear_logs()
    ui.show_loader(f"Iniciando {total} combos...")
    ui.log(f"Produtos: {len(selected_products)}", "info")
    ui.log(f"Territorios: {len(selected_territories)}", "info")
    ui.log(f"Total: {total} combinacoes | Workers: {workers} | Resume: {resume}", "info")

    ok = 0
    fail = 0

    def process_one(dataset_id, prod_id, territory_id, resume):
        pipeline = Pipeline(ctx.config)
        return pipeline.run(
            dataset_id=dataset_id,
            product_id=prod_id,
            territory_id=territory_id,
            create_collage=collage,
            add_labels=True,
            vertical_dimension=dimension,
            cell_height=300,
            resume=resume,
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_one, ds_id, prod_id, tid, resume): (ds_id, prod_id, tid)
            for ds_id, prod_id, tid in combos
        }
        for i, f in enumerate(as_completed(futures), 1):
            ds_id, prod_id, tid = futures[f]
            result = f.result()
            status = result.get('status', '?')
            if status == 'success':
                ok += 1
                ui.log(f"[{i}/{total}] {prod_id} / {tid}  OK", "success")
            else:
                fail += 1
                err = result.get('error', '')
                ui.log(f"[{i}/{total}] {prod_id} / {tid}  FALHA: {err}", "error")

    ui.hide_loader()
    ui.log(f"RESUMO: {ok} OK / {fail} Falha / {total} Total",
           "success" if fail == 0 else "warning")

    build_gif_cache(ctx)
    total_gifs = sum(len(v) for v in ctx.gif_cache.values())
    ui.log(f"Cache atualizado: {total_gifs} GIFs", "info")
