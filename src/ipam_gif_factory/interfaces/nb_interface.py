"""
M1 Interface — Construtor da UI (abas de datasets, produtos, territorios).
Usa PipelineStepUI e helpers de ui_components.

Uso:
    ui = GIFactoryUI(ctx)
    display(ui.build())
"""

import shutil
import ipywidgets as widgets
from IPython.display import display

from .ui_components import (
    PipelineStepUI, make_select_all_none, make_sync_button,
    make_empty_state, inline_confirm,
)
from .nb_setup import build_gif_cache


class GIFactoryUI(PipelineStepUI):
    """Interface completa de selecao de datasets, produtos e territorios."""

    def __init__(self, ctx):
        super().__init__(
            title="Fabrica de GIFs",
            description="Selecione dataset, produtos e territorios."
        )
        self.ctx = ctx
        self.chk_products = {}       # {(dataset_id, product_id): checkbox}
        self.chk_territories = {}    # {territory_id: checkbox}

        self.workers_tx = widgets.IntText(
            value=ctx.workers, description='Workers:',
            layout=widgets.Layout(width='150px'))
        self.resume_cb = widgets.Checkbox(value=True, description='Resume')
        self.collage_cb = widgets.Checkbox(value=True, description='Collage')
        self.dimension_tx = widgets.IntText(
            value=1560, description='Altura px:',
            layout=widgets.Layout(width='150px'))
        self.edit_cb = widgets.Checkbox(
            value=False, description='Modo Edicao (desbloqueia checkboxes)')

        self.delete_box = widgets.VBox(layout=widgets.Layout(display='none'))
        self._build_widgets()

    def _make_dataset_grid(self, category):
        ds_ids = sorted(self.ctx.dataset_categories.get(category, []))
        if not ds_ids:
            return make_empty_state("Nenhum dataset nesta categoria.")

        all_chks = []
        rows = []
        for ds_id in ds_ids:
            ds_data = self.ctx.config.datasets.get(ds_id, {})
            prods = sorted(ds_data.get('products', {}).keys())

            ds_label = widgets.HTML(
                f'<div style="font-weight:bold;margin:8px 0 4px 0;color:#333;">{ds_id}</div>')
            rows.append(ds_label)

            chk_row = []
            for prod_id in prods:
                key = (ds_id, prod_id)
                chk = widgets.Checkbox(
                    value=False, indent=False, description=prod_id,
                    layout=widgets.Layout(width='320px'),
                    disabled=False,
                    style={'description_width': 'initial'})
                chk._meta = {'dataset': ds_id, 'product': prod_id, 'exists': False}
                self.chk_products[key] = chk
                all_chks.append(chk)
                chk_row.append(chk)

            col_size = max(1, (len(chk_row) + 1) // 2)
            for i in range(0, len(chk_row), col_size):
                batch = chk_row[i:i + col_size]
                while len(batch) < col_size:
                    batch.append(widgets.HTML(''))
                rows.append(widgets.HBox(
                    batch, layout=widgets.Layout(margin='2px 10px')))

        def select_all(_):
            for c in all_chks:
                if not c.disabled:
                    c.value = True

        def select_none(_):
            for c in all_chks:
                c.value = False

        _, _, btns = make_select_all_none(select_all, select_none)
        return widgets.VBox([btns] + rows,
            layout=widgets.Layout(max_height='450px', overflow_y='auto', padding='5px'))

    def _make_territory_grid(self, group_key):
        tids = self.ctx.territory_groups.get(group_key, [])
        if not tids:
            return make_empty_state("Nenhum territorio neste grupo.")

        all_chks = []
        chk_list = []
        for tid in tids:
            chk = widgets.Checkbox(
                value=False, indent=False, description=tid,
                layout=widgets.Layout(width='180px'),
                style={'description_width': 'initial'})
            self.chk_territories[tid] = chk
            all_chks.append(chk)
            chk_list.append(chk)

        cols = 4
        rows_widgets = []
        for i in range(0, len(chk_list), cols):
            batch = chk_list[i:i + cols]
            while len(batch) < cols:
                batch.append(widgets.HTML(''))
            rows_widgets.append(widgets.HBox(
                batch, layout=widgets.Layout(margin='2px 5px')))

        def select_all(_):
            for c in all_chks:
                c.value = True

        def select_none(_):
            for c in all_chks:
                c.value = False

        _, _, btns = make_select_all_none(select_all, select_none)
        return widgets.VBox([btns] + rows_widgets,
            layout=widgets.Layout(max_height='400px', overflow_y='auto', padding='5px'))

    def _build_widgets(self):
        # Abas de dataset
        category_tabs = widgets.Tab()
        category_names = sorted(self.ctx.dataset_categories.keys())
        category_children = []
        for cat in category_names:
            grid = self._make_dataset_grid(cat)
            category_children.append(grid)
        category_tabs.children = category_children
        for i, cat in enumerate(category_names):
            category_tabs.set_title(i, cat)

        # Abas de territorio
        territory_tabs = widgets.Tab()
        territory_group_names = [
            'countries', 'biomes', 'ufs', 'custom_regions',
            'paraguay_departments', 'paraguay_regions', 'paraguay_full',
        ]
        territory_labels = [
            'Paises', 'Biomas', 'UFs', 'Regioes',
            'PY-Deptos', 'PY-Regioes', 'PY-Completo',
        ]
        territory_children = []
        for gkey in territory_group_names:
            grid = self._make_territory_grid(gkey)
            territory_children.append(grid)
        territory_tabs.children = territory_children
        for i, label in enumerate(territory_labels):
            territory_tabs.set_title(i, label)

        # Config row
        self.edit_cb.observe(self._on_edit_change, names='value')
        config_row = widgets.HBox(
            [self.workers_tx, self.resume_cb, self.collage_cb,
             self.dimension_tx, self.edit_cb],
            layout=widgets.Layout(gap='15px', margin='10px 0', align_items='center'))

        # Delete button
        self.delete_btn = widgets.Button(
            description="Excluir Selecionados", button_style='danger',
            layout=widgets.Layout(width='200px'))
        self.delete_btn.on_click(self._on_delete_click)
        self.delete_box.children = [self.delete_btn]

        # Refresh button
        refresh_btn = make_sync_button(
            "Atualizar Cache", self._refresh_cache, ui=self, width='180px')

        self.main_area.children = [
            PipelineStepUI.get_status_css(),
            widgets.HTML('<h4 style="margin:10px 0 5px 0;">Datasets & Produtos</h4>'),
            category_tabs,
            widgets.HTML('<h4 style="margin:15px 0 5px 0;">Territorios</h4>'),
            territory_tabs,
            config_row,
            widgets.HBox([refresh_btn, self.delete_box],
                         layout=widgets.Layout(gap='10px', margin='5px 0')),
        ]

    def _on_edit_change(self, change):
        editable = change['new']
        for chk in self.chk_products.values():
            if chk._meta.get('exists') and not editable:
                chk.disabled = True
                chk.value = False
            else:
                chk.disabled = False
        self.delete_box.layout.display = 'block' if editable else 'none'

    def _refresh_cache(self):
        build_gif_cache(self.ctx)
        for (ds_id, prod_id), chk in self.chk_products.items():
            chk._meta['exists'] = False
            chk.disabled = False
            chk.value = False
        total = sum(len(v) for v in self.ctx.gif_cache.values())
        self.log(f"Cache atualizado: {total} GIFs", "success")

    def _on_delete_click(self, b):
        def do_delete():
            output_base = self.ctx.config.get_output_dir()
            deleted = 0
            for (ds_id, prod_id), chk in self.chk_products.items():
                if chk.value:
                    for tid, tchk in self.chk_territories.items():
                        if tchk.value:
                            path = os.path.join(output_base, ds_id, prod_id, tid)
                            if os.path.exists(path):
                                shutil.rmtree(path)
                                deleted += 1
                                self.log(
                                    f"Excluido: {ds_id}/{prod_id}/{tid}", "warning")
            build_gif_cache(self.ctx)
            self.log(f"{deleted} diretorios excluidos. Cache atualizado.", "success")
            self.delete_box.layout.display = 'none'
        inline_confirm(self.delete_btn, do_delete)

    def build(self):
        """Renderiza a interface completa."""
        self.display()
        print("Pronto. Selecione os itens e va para a Celula 3.")
