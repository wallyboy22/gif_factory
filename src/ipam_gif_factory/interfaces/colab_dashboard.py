"""
colab_dashboard.py - Versão Operacional em Lote (Tabelas)
Inclui seleção de tipo de mídia (GIF/Grid/Frames).
"""
import os
import json
import threading
import warnings
import base64
from pathlib import Path
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from google.cloud import storage

from ipam_gif_factory.config import ConfigLoader

# Silenciar avisos de quota do Google
warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")

class ColabStreamDash:
    def __init__(self):
        self.config = ConfigLoader().load_all()
        gcs_conf = self.config.paths.get('paths', {}).get('google_cloud_storage', {})
        self.bucket_name = gcs_conf.get('bucket', 'mapbiomas-fire')
        self.hub_root = gcs_conf.get('hub_root', 'gif-factory')
        self.project_id = gcs_conf.get('project_id', 'mapbiomas-fire-485203')
        
        # Estado Global
        self.gcs_index = {} 
        self.selected_rows = set() 
        self.is_loading = False
        
        # --- Filtros de Tabela ---
        self.f_ds = widgets.SelectMultiple(description='Datasets', layout=widgets.Layout(width='24%', height='80px'))
        self.f_cat = widgets.SelectMultiple(description='Produtos', layout=widgets.Layout(width='24%', height='80px'))
        self.f_ter = widgets.SelectMultiple(description='Territórios', layout=widgets.Layout(width='24%', height='80px'))
        self.f_type = widgets.Dropdown(options=[('GIF Animado', 'gif'), ('Grid (Collage)', 'grid'), ('Frames (PNGs)', 'frames')], value='gif', description='Mídia:', layout=widgets.Layout(width='24%'))
        
        for f in [self.f_ds, self.f_cat, self.f_ter, self.f_type]:
            f.observe(lambda x: self.render_tabela(), names='value')

        # --- Widgets de Saída ---
        self.output_geral = widgets.Output()
        self.output_tabela = widgets.Output()
        self.output_processamento = widgets.Output()
        self.output_visualizar = widgets.Output()
        
        self.loader = widgets.HTML(self._get_loader_html(False))
        self.header = widgets.HTML(self._get_header_html())
        
        # Sistema de Abas
        self.tab = widgets.Tab()
        self.tab.children = [self.output_geral, self.output_tabela, self.output_processamento, self.output_visualizar]
        titles = ['🏠 Início', '📑 Tabela de Dados', '⚙️ Processamento', '🎬 Visualizador']
        for i, t in enumerate(titles): self.tab.set_title(i, t)
        self.tab.observe(self.on_tab_change, names='selected_index')

        display(HTML(self._get_global_css()))
        self.ui = widgets.VBox([self.header, self.tab], layout=widgets.Layout(padding='10px'))

    def _get_client(self):
        return storage.Client(project=self.project_id)

    def _get_global_css(self):
        return """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            :root { --ipam-green: #006b3f; --st-border: #dfe2e6; }
            .jupyter-widgets { font-family: 'Inter', sans-serif !important; }
            .st-header { display: flex; align-items: center; padding: 10px 20px; background: white; border-bottom: 3px solid var(--ipam-green); margin-bottom: 10px; }
            .st-table-header { background:#f8f9fa; font-weight:700; padding:10px; display:flex; border-bottom:2px solid #ddd; font-size:12px; }
            .st-table-row { display:flex; padding:8px 10px; border-bottom:1px solid #eee; align-items:center; min-height:45px; background:white; }
            .st-table-row:hover { background: #f0f7f3; }
            .kpi-box { padding: 12px; background: white; border-radius: 6px; border-left: 4px solid var(--ipam-green); box-shadow: 0 1px 2px rgba(0,0,0,0.1); flex: 1; }
            .kpi-val { font-size: 22px; font-weight: 700; color: var(--ipam-green); }
            .kpi-lab { font-size: 10px; color: #888; text-transform: uppercase; }
            .cmd-box { background: #262730; color: #fafafa; font-family: monospace; padding: 15px; border-radius: 6px; font-size: 11px; }
        </style>
        """

    def _get_header_html(self):
        return f"""<div class="st-header"><div style="display:flex; align-items:center; gap:12px;"><h1 style="margin:0; font-size:20px; font-weight:800; color:#1a1a1a;">GIF Factory <span style="font-weight:300; color:#888;">BATCH CONTROL</span></h1></div><div style="margin-left:auto; text-align:right;"><code style="font-size:11px; color:var(--ipam-green);">gs://{self.bucket_name}/{self.hub_root}</code></div></div>"""

    def _get_loader_html(self, visible=True):
        display_style = "flex" if visible else "none"
        return f"""<div style="display:{display_style}; align-items:center; gap:8px; padding-left:20px;"><div class="st-spinner"></div><span style="font-size:11px; color:#666;">Sincronizando Hub...</span><style>.st-spinner{{width:14px; height:14px; border:2px solid #eee; border-top:2px solid var(--ipam-green); border-radius:50%; animation:st-spin 0.6s linear infinite;}} @keyframes st-spin{{0%{{transform:rotate(0deg);}} 100%{{transform:rotate(360deg);}}}}</style></div>"""

    def refresh_gcs(self):
        if self.is_loading: return
        self.is_loading = True
        self.loader.value = self._get_loader_html(True)
        self.update_main()
        
        def task():
            try:
                client = self._get_client()
                prefix = f"{self.hub_root}/"
                iterator = client.list_blobs(self.bucket_name, prefix=prefix, delimiter='/')
                list(iterator)
                new_index = {}
                for folder in iterator.prefixes:
                    ds_name = folder.rstrip('/').split('/')[-1]
                    if ds_name == "territories": continue
                    new_index[ds_name] = {}
                    cat_iterator = client.list_blobs(self.bucket_name, prefix=folder, delimiter='/')
                    list(cat_iterator)
                    for cat_folder in cat_iterator.prefixes:
                        cat_name = cat_folder.rstrip('/').split('/')[-1]
                        ter_iterator = client.list_blobs(self.bucket_name, prefix=cat_folder, delimiter='/')
                        list(ter_iterator)
                        new_index[ds_name][cat_name] = [t.rstrip('/').split('/')[-1] for t in ter_iterator.prefixes]
                self.gcs_index = new_index
                self.is_loading = False
                self.loader.value = self._get_loader_html(False)
                
                all_ds = sorted(self.gcs_index.keys())
                all_cat = sorted(list(set(c for ds in self.gcs_index.values() for c in ds.keys())))
                all_ter = sorted(list(set(t for ds in self.gcs_index.values() for c in ds.values() for t in c)))
                
                self.f_ds.options = all_ds
                self.f_cat.options = all_cat
                self.f_ter.options = all_ter
                
                self.f_ds.value = all_ds
                self.f_cat.value = all_cat
                if all_ter: self.f_ter.value = [all_ter[0]]
                self.update_main()
            except Exception as e:
                self.is_loading = False
                self.loader.value = self._get_loader_html(False)
                with self.output_geral: print(f"Erro GCS: {e}")
                self.update_main()
        threading.Thread(target=task).start()

    def on_tab_change(self, change):
        self.update_main()

    def update_main(self):
        idx = self.tab.selected_index
        if idx == 0: self.render_geral()
        elif idx == 1: self.render_tabela()
        elif idx == 2: self.render_processamento()
        elif idx == 3: self.render_visualizador()

    def render_geral(self):
        with self.output_geral:
            clear_output(wait=True)
            n_ds = len(self.gcs_index)
            n_total = sum(len(t) for c in self.gcs_index.values() for t in c.values())
            html = f"""<div style="display:flex; gap:15px; margin-bottom:20px;"><div class="kpi-box"><div class="kpi-val">{n_ds}</div><div class="kpi-lab">Datasets</div></div><div class="kpi-box"><div class="kpi-val">{n_total}</div><div class="kpi-lab">Resultados</div></div><div class="kpi-box"><div class="kpi-val">{len(self.selected_rows)}</div><div class="kpi-lab">Cesta de Download</div></div></div>"""
            display(widgets.HTML(html))
            sync_btn = widgets.Button(description="Sincronizar Hub GCS", button_style='success', icon='refresh')
            sync_btn.on_click(lambda x: self.refresh_gcs())
            display(widgets.HBox([sync_btn, self.loader]))

    def render_tabela(self):
        with self.output_tabela:
            clear_output(wait=True)
            if self.is_loading and not self.gcs_index:
                display(widgets.HTML("<p>Carregando...</p>"))
                return
            
            display(widgets.HTML("<b>Filtros de Visão:</b>"))
            display(widgets.HBox([self.f_ds, self.f_cat, self.f_ter, self.f_type], layout=widgets.Layout(margin='0 0 15px 0', align_items='flex-end')))

            btn_dl = widgets.Button(description="Gerar Batch Download", button_style='info', icon='download')
            btn_dl.on_click(self.on_batch_download)
            btn_clear = widgets.Button(description="Limpar Seleção", icon='times')
            btn_clear.on_click(self.on_clear_selection)
            display(widgets.HBox([btn_dl, btn_clear], layout=widgets.Layout(margin='0 0 10px 0')))

            display(widgets.HTML(f"""<div class="st-table-header"><div style="width:40px;"></div><div style="width:25%;">Dataset</div><div style="width:25%;">Produto</div><div style="width:25%;">Território</div><div>Ação ({self.f_type.value.upper()})</div></div>"""))

            rows = []
            sel_ds = self.f_ds.value or self.f_ds.options
            sel_cat = self.f_cat.value or self.f_cat.options
            sel_ter = self.f_ter.value or self.f_ter.options

            for ds, categories in self.gcs_index.items():
                if ds not in sel_ds: continue
                for cat, territories in categories.items():
                    if cat not in sel_cat: continue
                    for ter in territories:
                        if ter not in sel_ter: continue
                        rows.append(self._create_row(ds, cat, ter))
            
            if not rows:
                display(widgets.HTML("<p style='padding:20px; color:#999;'>Nenhum resultado.</p>"))
            else:
                vbox_rows = widgets.VBox(rows, layout=widgets.Layout(max_height='450px', overflow_y='auto', border='1px solid #eee'))
                display(vbox_rows)

    def _create_row(self, ds, cat, ter):
        key = (ds, cat, ter)
        cb = widgets.Checkbox(value=(key in self.selected_rows), indent=False, layout=widgets.Layout(width='40px'))
        def on_cb_change(change):
            if change['new']: self.selected_rows.add(key)
            else: self.selected_rows.discard(key)
            self.render_geral()
        cb.observe(on_cb_change, names='value')
        
        ds_l = widgets.HTML(f"<b>{ds}</b>", layout=widgets.Layout(width='25%'))
        ct_l = widgets.HTML(f"{cat}", layout=widgets.Layout(width='25%'))
        tr_l = widgets.HTML(f"{ter}", layout=widgets.Layout(width='25%'))
        
        btn_view = widgets.Button(description="🎬", layout=widgets.Layout(width='35px'))
        btn_view.on_click(lambda x: self._show_preview(ds, cat, ter))
        
        # Link Dinâmico baseado no tipo
        m_type = self.f_type.value
        filename = f"{cat}.gif" if m_type == 'gif' else (f"collage_{cat}.png" if m_type == 'grid' else "*.png")
        dl_url = f"https://storage.googleapis.com/{self.bucket_name}/{self.hub_root}/{ds}/{cat}/{ter}/{filename}"
        
        btn_dl_html = f'<a href="{dl_url}" target="_blank" style="text-decoration:none;"><button style="cursor:pointer; background:var(--ipam-green); color:white; border:none; border-radius:3px; padding:2px 6px;">⬇️</button></a>'
        if m_type == 'frames': btn_dl_html = '<span title="Use Batch Download para frames" style="cursor:help;">📁</span>'
        
        btn_dl = widgets.HTML(btn_dl_html)
        row = widgets.HBox([cb, ds_l, ct_l, tr_l, widgets.HBox([btn_view, btn_dl])], layout=widgets.Layout(border_bottom='1px solid #eee', align_items='center'))
        row.add_class('st-table-row')
        return row

    def on_batch_download(self, x):
        with self.output_visualizar:
            clear_output()
            if not self.selected_rows:
                display(widgets.HTML("<p style='color:red;'>Selecione itens na tabela.</p>"))
                return
            m_type = self.f_type.value
            commands = []
            for ds, cat, ter in self.selected_rows:
                if m_type == 'gif': target = f"{cat}.gif"
                elif m_type == 'grid': target = f"collage_{cat}.png"
                else: target = "*" # Baixa tudo (frames + outros)
                
                commands.append(f"gsutil cp gs://{self.bucket_name}/{self.hub_root}/{ds}/{cat}/{ter}/{target} ./downloads/{ds}/{cat}/{ter}/")
            
            display(widgets.HTML(f"<h3>Batch Download: {m_type.upper()}</h3><div class='cmd-box'>{' '.join(['mkdir -p ./downloads/ && '] if os.name != 'nt' else [])}{chr(10).join(commands)}</div>"))
            self.tab.selected_index = 3

    def _show_preview(self, ds, prod, ter):
        with self.output_visualizar:
            clear_output()
            m_type = self.f_type.value
            filename = f"{prod}.gif" if m_type == 'gif' else (f"collage_{prod}.png" if m_type == 'grid' else None)
            
            if not filename:
                display(widgets.HTML(f"<h3>Frames: {prod}</h3><p>Visualização individual de frames em lote não disponível aqui. Use o botão de Download.</p>"))
            else:
                url = f"https://storage.googleapis.com/{self.bucket_name}/{self.hub_root}/{ds}/{prod}/{ter}/{filename}"
                display(widgets.HTML(f"<h3>{prod} ({m_type.upper()})</h3><p>{ter}</p><img src='{url}' style='max-width:100%; border-radius:10px;'>"))
            self.tab.selected_index = 3

    def render_processamento(self):
        with self.output_processamento:
            clear_output(wait=True)
            display(widgets.HTML("<h3>🚀 Processamento</h3>"))
            if self.selected_rows:
                d = sorted(list(set(r[0] for r in self.selected_rows)))
                p = sorted(list(set(r[1] for r in self.selected_rows)))
                t = sorted(list(set(r[2] for r in self.selected_rows)))
                cmd = f"python main.py --generate --datasets {' '.join(d)} --products {' '.join(p)} --territories {' '.join(t)}"
                display(widgets.HTML(f"<div class='cmd-box'>{cmd}</div>"))
            
            display(widgets.HTML("<hr><h4>Gerar Manual</h4>"))
            ds_sel = widgets.SelectMultiple(options=sorted(self.config.datasets.keys()), description='Datasets:', layout=widgets.Layout(width='45%'))
            cat_sel = widgets.SelectMultiple(options=sorted(self.config.categories.keys()), description='Categorias:', layout=widgets.Layout(width='45%'))
            ter_sel = widgets.SelectMultiple(options=sorted(self.config.territories.keys()), description='Territórios:', layout=widgets.Layout(width='91%'))
            display(widgets.HBox([ds_sel, cat_sel]), ter_sel)
            
            out_cmd = widgets.Output()
            def get_cmd(x):
                cmd = f"python main.py --generate --datasets {' '.join(ds_sel.value)} --products {' '.join(cat_sel.value)} --territories {' '.join(ter_sel.value)}"
                with out_cmd: clear_output(); display(widgets.HTML(f"<div class='cmd-box'>{cmd}</div>"))
            btn = widgets.Button(description="Gerar Comando", button_style='primary')
            btn.on_click(get_cmd)
            display(btn, out_cmd)

    def render_visualizador(self):
        with self.output_visualizar:
            if not self.tab.selected_index == 3:
                clear_output()
                display(widgets.HTML("<h3>Visualizador</h3>"))

    def display(self):
        display(self.ui)
        self.update_main()
        self.refresh_gcs()

def start_dashboard():
    dash = ColabStreamDash()
    dash.display()
    return dash
