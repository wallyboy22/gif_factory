"""Interface Colab para explorar o catálogo existente e executar um GIF.

Não considera resultados existentes equivalentes: o caminho, sozinho, não
contém informação suficiente para comparar anos e demais parâmetros.
"""
import os
import json
from pathlib import Path

import ipywidgets as widgets
from IPython.display import display, Image

from ..core.pipeline import Pipeline
from ..core.theme import combo_dir
from .territory_search import search_features, register_selection


class ColabGIFs:
    def __init__(self, config):
        self.config = config
        self.initiative = widgets.Dropdown(description="Iniciativa:")
        self.category = widgets.Dropdown(description="Temática:")
        self.collection = widgets.Dropdown(description="Coleção:")
        self.product = widgets.SelectMultiple(description="Layers:", rows=8)
        self.territory = widgets.SelectMultiple(description="Territórios:", rows=8)
        self.source = widgets.Text(value="projects/ee-ipam/assets/ORIGINAIS/IBGE/limite_municipios_IBGE_2025", description="Asset:", layout=widgets.Layout(width="95%"))
        self.name_field = widgets.Text(value="NM_MUN", description="Nome:")
        self.id_field = widgets.Text(value="system:index", description="ID único:")
        self.query = widgets.Text(description="Buscar:", placeholder="Nome como aparece no asset")
        self.search_button = widgets.Button(description="Buscar")
        self.search_results = widgets.SelectMultiple(description="Encontrados:", rows=5)
        self.add_button = widgets.Button(description="Adicionar")
        self.remove_button = widgets.Button(description="Remover selecionados")
        self.selected = widgets.SelectMultiple(description="Adicionados:", rows=5)
        self.combine = widgets.Checkbox(value=False, description="Combinar adicionados em um recorte")
        self.dissolve = widgets.Checkbox(value=False, description="Dissolver limites internos")
        self.search_output = widgets.Output()
        self._found = []
        self._selected = {}
        self.search_button.on_click(self._search)
        self.add_button.on_click(self._add_selected)
        self.remove_button.on_click(self._remove_selected)
        self.theme = widgets.Dropdown(options=[("Claro", "light"), ("Escuro", "dark")], description="Tema:")
        self.years = widgets.Text(description="Anos:", placeholder="Vazio = todas as bandas; ex.: 2020 2021")
        self.collage = widgets.Checkbox(value=False, description="Gerar colagens")
        self.run_button = widgets.Button(description="Gerar GIFs", button_style="primary")
        self.output = widgets.Output()
        self.results_refresh = widgets.Button(description="Atualizar lista")
        self.results_list = widgets.Select(description="GIFs:", rows=10, layout=widgets.Layout(width="95%"))
        self.results_preview = widgets.Output()
        self.results_refresh.on_click(self._refresh_results)
        self.results_list.observe(self._show_result, names="value")
        inventory_path = Path(config.config_dir) / "reference_inventory.json"
        self.inventory = json.loads(inventory_path.read_text(encoding="utf-8"))["records"] if inventory_path.is_file() else []
        self.inventory_country = widgets.Dropdown(description="Iniciativa:", options=sorted({r["initiative"] for r in self.inventory}))
        self.inventory_theme = widgets.Dropdown(description="Temática:")
        self.inventory_collection = widgets.Dropdown(description="Coleção:")
        self.inventory_layers = widgets.Select(description="Layers:", rows=8, layout=widgets.Layout(width="95%"))
        self.inventory_details = widgets.Textarea(description="Detalhes:", layout=widgets.Layout(width="95%", height="130px"), disabled=True)
        self.inventory_country.observe(self._inventory_country_changed, names="value")
        self.inventory_theme.observe(self._inventory_theme_changed, names="value")
        self.inventory_collection.observe(self._inventory_collection_changed, names="value")
        self.inventory_layers.observe(self._inventory_layer_changed, names="value")
        self._inventory_country_changed()
        self.initiative.observe(self._initiative_changed, names="value")
        self.category.observe(self._category_changed, names="value")
        self.collection.observe(self._collection_changed, names="value")
        self.run_button.on_click(self._run)
        self.initiative.options = [(v.get("name", k), k) for k, v in config.initiatives.items()]
        if self.initiative.options:
            self.initiative.value = self.initiative.options[0][1]
        self._initiative_changed()

    def _initiative_changed(self, change=None):
        initiative = self.config.initiatives.get(self.initiative.value, {})
        collections = initiative.get("collections", [])
        categories = sorted({c.get("category") or "other" for c in collections})
        self.category.options = [(x, x) for x in categories]
        if categories:
            self.category.value = categories[0]
        territories = []
        for group in initiative.get("territory_groups", []):
            for tid in group.get("territory_ids", []):
                territories.append((f"{group.get('name', group['id'])} · {tid}", tid))
        self.territory.options = territories
        self._category_changed()

    def _inventory_country_changed(self, change=None):
        themes = sorted({r["theme"] for r in self.inventory if r["initiative"] == self.inventory_country.value})
        self.inventory_theme.options = themes
        if themes:
            self.inventory_theme.value = themes[0]
        self._inventory_theme_changed()

    def _inventory_theme_changed(self, change=None):
        collections = sorted({r["collection"] for r in self.inventory
                              if r["initiative"] == self.inventory_country.value and r["theme"] == self.inventory_theme.value})
        self.inventory_collection.options = collections
        if collections:
            self.inventory_collection.value = collections[0]
        self._inventory_collection_changed()

    def _inventory_collection_changed(self, change=None):
        self.inventory_layers.options = [(r["product"], i) for i, r in enumerate(self.inventory)
                                         if r["initiative"] == self.inventory_country.value
                                         and r["theme"] == self.inventory_theme.value
                                         and r["collection"] == self.inventory_collection.value]
        if self.inventory_layers.options:
            self.inventory_layers.value = self.inventory_layers.options[0][1]
        self._inventory_layer_changed()

    def _inventory_layer_changed(self, change=None):
        index = self.inventory_layers.value
        if index is None:
            self.inventory_details.value = ""
            return
        record = self.inventory[index]
        matches = ", ".join(f"{m['dataset']}/{m['product']}" for m in record["matching_assets"]) or "nenhuma por asset"
        self.inventory_details.value = (f"Asset: {record['asset']}\nTipo: {record['dtype']}  |  Escala: {record['scale']}\n"
                                        f"Correspondências no catálogo atual: {matches}\n"
                                        "Referência não validada; não é executável automaticamente.")

    def _category_changed(self, change=None):
        initiative = self.config.initiatives.get(self.initiative.value, {})
        self.collection.options = [
            (c.get("name", c["id"]), c["dataset_id"])
            for c in initiative.get("collections", [])
            if (c.get("category") or "other") == self.category.value
        ]
        if self.collection.options:
            self.collection.value = self.collection.options[0][1]
        self._collection_changed()

    def _collection_changed(self, change=None):
        products = self.config.datasets.get(self.collection.value, {}).get("products", {})
        self.product.options = [(f"{p.get('name', pid)} ({pid})", pid) for pid, p in products.items()]

    def _search(self, button):
        with self.search_output:
            self.search_output.clear_output()
            try:
                import ee
                self._found = search_features(ee, self.source.value, self.name_field.value,
                                              self.id_field.value, self.query.value)
                self.search_results.options = [
                    (f"{r['name']} · {r['id']}", i) for i, r in enumerate(self._found)
                ]
                print(f"{len(self._found)} resultado(s), até 30. A busca diferencia maiúsculas e minúsculas.")
            except Exception as exc:
                self._found = []
                self.search_results.options = []
                print(f"Busca indisponível: {exc}")

    def _refresh_selected(self):
        self.selected.options = [(f"{r['name']} · {r['id']}", key) for key, r in self._selected.items()]

    def _add_selected(self, button):
        for index in self.search_results.value:
            r = self._found[index]
            key = json.dumps([r["source"], r["id_field"], r["id"]], ensure_ascii=False)
            self._selected[key] = r
        self._refresh_selected()

    def _remove_selected(self, button):
        for key in self.selected.value:
            self._selected.pop(key, None)
        self._refresh_selected()

    def _refresh_results(self, button=None):
        root = Path(self.config.get_output_dir())
        self.results_list.options = [(p.relative_to(root).as_posix(), str(p))
                                     for p in sorted(root.rglob("*.gif")) if p.is_file()]

    def _show_result(self, change):
        with self.results_preview:
            self.results_preview.clear_output()
            path = change.get("new")
            if path and os.path.isfile(path):
                print(path)
                display(Image(filename=path))

    def _run(self, button):
        with self.output:
            if not self.product.value or not (self.territory.value or self._selected):
                print("Selecione pelo menos uma layer e um território.")
                return
            years = self.years.value.replace(",", " ").split()
            if any(not (len(year) == 4 and year.isdigit()) for year in years):
                print("Informe anos de quatro dígitos separados por espaços ou vírgulas.")
                return
            self.run_button.disabled = True
            try:
                extra = register_selection(self.config, list(self._selected.values()),
                                           self.combine.value, self.dissolve.value)
                territories = list(dict.fromkeys([*self.territory.value, *extra]))
                for product in self.product.value:
                    for territory in territories:
                        print(f"\n{self.collection.value} / {product} / {territory}")
                        destination = combo_dir(self.config.get_output_dir(), self.collection.value,
                                                product, territory, self.theme.value)
                        if os.path.isdir(destination) and os.listdir(destination):
                            print(f"[PULADO] Pasta já contém arquivos: {destination}. Equivalência ainda não verificada.")
                            continue
                        result = Pipeline(self.config).run(
                            self.collection.value, product, territory,
                            theme=self.theme.value, create_collage=self.collage.value,
                            band_names_filter=years or None,
                        )
                        if result.get("status") == "success":
                            path = result.get("gif_path")
                            print(f"GIF: {path}")
                            if path and os.path.isfile(path):
                                display(Image(filename=path))
                        else:
                            print(f"Erro: {result.get('error', 'desconhecido')}")
            finally:
                self.run_button.disabled = False

    def build(self):
        search = widgets.VBox([
            widgets.HTML("<b>Buscar na sua FeatureCollection</b><p>Exemplo inicial: municípios IBGE 2025. Para UC ou TI informe seu asset e seus campos. Busca por nome exato parcial, sensível a maiúsculas. Verifique o ID único.</p>"),
            self.source, widgets.HBox([self.name_field, self.id_field]),
            widgets.HBox([self.query, self.search_button]), self.search_results,
            self.add_button, self.selected, self.remove_button, self.combine,
            self.dissolve, self.search_output,
        ])
        executor = widgets.VBox([
            widgets.HTML("<h2>Fábrica de GIFs</h2><p>Catálogo atual; nem todas as combinações foram validadas.</p>"),
            self.initiative, self.category, self.collection, self.product,
            self.territory, search, self.theme, self.years, self.collage,
            widgets.HTML("<p>Seleção múltipla: Ctrl/Cmd + clique. Pastas existentes não vazias são puladas; isso não verifica equivalência.</p>"),
            self.run_button, self.output,
        ])
        catalog = widgets.VBox([
            widgets.HTML("<h3>Inventário da referência</h3><p>Dados para consulta; assets, bandas e legendas não foram validados para execução. Produtos com o mesmo asset podem ter tratamentos diferentes.</p>"),
            self.inventory_country, self.inventory_theme, self.inventory_collection,
            self.inventory_layers, self.inventory_details,
        ])
        results = widgets.VBox([
            widgets.HTML("<h3>GIFs na pasta de saída</h3><p>Lista local ou do Drive montado. A presença do arquivo não prova que os parâmetros sejam equivalentes.</p>"),
            self.results_refresh, self.results_list, self.results_preview,
        ])
        tabs = widgets.Tab(children=[executor, catalog, results])
        tabs.set_title(0, "Gerar GIF")
        tabs.set_title(1, "Inventário")
        tabs.set_title(2, "Resultados")
        return tabs
