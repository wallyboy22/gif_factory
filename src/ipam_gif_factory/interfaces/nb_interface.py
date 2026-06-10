"""
M1 Interface — Construtor da UI (projeto -> GT -> colecao -> produtos).
Usa PipelineStepUI e helpers de ui_components.

Uso:
    ui = GIFactoryUI(ctx)
    display(ui.build())
"""

import os
import shutil
import ipywidgets as widgets
from IPython.display import display

from .ui_components import (
    PipelineStepUI, make_select_all_none, make_sync_button,
    make_empty_state, inline_confirm,
)
from .nb_setup import build_gif_cache


class GIFactoryUI(PipelineStepUI):
    """Interface completa de selecao com hierarquia projeto -> GT -> colecao."""

    def __init__(self, ctx):
        super().__init__(
            title="Fabrica de GIFs",
            description="Selecione projeto, GT, colecao, produtos e territorios."
        )
        self.ctx = ctx
        self.chk_products = {}
        self.chk_territories = {}

        self.workers_tx = widgets.IntText(
            value=ctx.workers, description='Workers:',
            layout=widgets.Layout(width='150px'))
        self.resume_cb = widgets.Checkbox(value=True, description='Resume')
        self.collage_cb = widgets.Checkbox(value=True, description='Collage')
        self.dimension_tx = widgets.IntText(
            value=2048, description='Altura px:',
            layout=widgets.Layout(width='150px'))
        self.edit_cb = widgets.Checkbox(
            value=False, description='Modo Edicao (desbloqueia checkboxes)')

        self.delete_box = widgets.VBox(layout=widgets.Layout(display='none'))
        self._build_widgets()

    def _make_product_grid(self, ds_ids):
        """Cria grid de checkboxes para uma lista de datasets (produtos agrupados)."""
        all_chks = []
        rows = []
        for ds_id in sorted(ds_ids):
            ds_data = self.ctx.config.datasets.get(ds_id, {})
            prods = sorted(ds_data.get('products', {}).keys())
            if not prods:
                continue

            ds_label = widgets.HTML(
                f'<div style="font-weight:bold;margin:6px 0 2px 0;color:#333;font-size:11px;">{ds_id}</div>')
            rows.append(ds_label)

            chk_row = []
            for prod_id in prods:
                key = (ds_id, prod_id)
                chk = widgets.Checkbox(
                    value=False, indent=False, description=prod_id,
                    layout=widgets.Layout(width='300px'),
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
                rows.append(widgets.HBox(batch, layout=widgets.Layout(margin='1px 8px')))

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

    def _make_territory_grid(self, tids):
        """Cria grid de checkboxes para uma lista de territory IDs."""
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
            rows_widgets.append(widgets.HBox(batch, layout=widgets.Layout(margin='2px 5px')))

        def select_all(_):
            for c in all_chks:
                c.value = True

        def select_none(_):
            for c in all_chks:
                c.value = False

        _, _, btns = make_select_all_none(select_all, select_none)
        return widgets.VBox([btns] + rows_widgets,
            layout=widgets.Layout(max_height='400px', overflow_y='auto', padding='5px'))

    def _build_product_tabs(self):
        """Constroi tabs hierarquicas: Projeto -> GT -> Colecao -> Produtos."""
        hierarchy = self.ctx.project_hierarchy
        if not hierarchy:
            return make_empty_state("Nenhum projeto configurado. Verifique ACTIVE_PROJECTS/ACTIVE_GTS.")

        project_tabs = widgets.Tab()
        project_names = sorted(hierarchy.keys())
        project_children = []

        for pi, project_id in enumerate(project_names):
            gts = hierarchy[project_id]
            gt_tabs = widgets.Tab()
            gt_names = sorted(gts.keys())
            gt_children = []

            for gi, gt in enumerate(gt_names):
                collections = gts[gt]
                col_tabs = widgets.Tab()
                col_names = sorted(collections.keys())
                col_children = []

                for ci, col in enumerate(col_names):
                    ds_ids = collections[col]
                    grid = self._make_product_grid(ds_ids)
                    col_children.append(grid)
                    col_tabs.set_title(ci, f"Col {col}")

                col_tabs.children = col_children
                gt_children.append(col_tabs)
                gt_tabs.set_title(gi, gt)

            gt_tabs.children = gt_children
            project_children.append(gt_tabs)
            project_tabs.set_title(pi, project_id)

        project_tabs.children = project_children
        return project_tabs

    def _build_territory_tabs(self):
        """Constroi tabs de territorio por pais: Brasil / Paraguay."""
        tg = self.ctx.territory_groups
        territory_tabs = widgets.Tab()
        territory_children = []

        # Brasil: UFs + Biomas + Regioes
        br_sub_tabs = widgets.Tab()
        br_children = []
        for group_key, label in [('ufs', 'UFs'), ('biomes', 'Biomas'), ('custom_regions', 'Regioes')]:
            tids = tg.get(group_key, [])
            br_children.append(self._make_territory_grid(tids))
            br_sub_tabs.set_title(len(br_children) - 1, label)
        br_sub_tabs.children = br_children
        territory_children.append(br_sub_tabs)
        territory_tabs.set_title(0, 'Brasil')

        # Paraguay: Departamentos + Regioes + Completo
        py_sub_tabs = widgets.Tab()
        py_children = []
        for group_key, label in [('paraguay_departments', 'Deptos'), ('paraguay_regions', 'Regioes'), ('paraguay_full', 'Completo')]:
            tids = tg.get(group_key, [])
            py_children.append(self._make_territory_grid(tids))
            py_sub_tabs.set_title(len(py_children) - 1, label)
        py_sub_tabs.children = py_children
        territory_children.append(py_sub_tabs)
        territory_tabs.set_title(1, 'Paraguai')

        territory_tabs.children = territory_children
        return territory_tabs

    def _build_widgets(self):
        product_tabs = self._build_product_tabs()
        territory_tabs = self._build_territory_tabs()

        self.edit_cb.observe(self._on_edit_change, names='value')
        config_row = widgets.HBox(
            [self.workers_tx, self.resume_cb, self.collage_cb,
             self.dimension_tx, self.edit_cb],
            layout=widgets.Layout(gap='15px', margin='10px 0', align_items='center'))

        self.delete_btn = widgets.Button(
            description="Excluir Selecionados", button_style='danger',
            layout=widgets.Layout(width='200px'))
        self.delete_btn.on_click(self._on_delete_click)
        self.delete_box.children = [self.delete_btn]

        refresh_btn = make_sync_button(
            "Atualizar Cache", self._refresh_cache, ui=self, width='180px')

        self.main_area.children = [
            PipelineStepUI.get_status_css(),
            widgets.HTML('<h4 style="margin:10px 0 5px 0;">Projetos & Produtos</h4>'),
            product_tabs,
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
                                self.log(f"Excluido: {ds_id}/{prod_id}/{tid}", "warning")
            build_gif_cache(self.ctx)
            self.log(f"{deleted} diretorios excluidos. Cache atualizado.", "success")
            self.delete_box.layout.display = 'none'
        inline_confirm(self.delete_btn, do_delete)

    def build(self):
        """Renderiza a interface completa."""
        self.display()
        print("Pronto. Selecione os itens e va para a Celula 3.")
