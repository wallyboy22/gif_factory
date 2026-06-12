"""
Componentes de UI reutilizaveis para notebooks (ipywidgets).
Adaptado do M_ui_components.py (MapBiomas Fire Monitor / peru-fire).
"""
import re
import ipywidgets as widgets
from IPython.display import display, clear_output


_SPINNER_CSS = """
<style>
.mfm-loader-mini {
    border: 2px solid #f3f3f3;
    border-top: 2px solid #3498db;
    border-radius: 50%;
    width: 14px;
    height: 14px;
    animation: mfm-spin 0.8s linear infinite;
    display: inline-block;
    vertical-align: middle;
}
@keyframes mfm-spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>"""


class PipelineStepUI:
    """Wrapper visual para uma etapa do pipeline (titulo, descricao, spinner, log)."""

    def __init__(self, title="", description=""):
        self.title = title
        self.description = description

        self.loader_html = widgets.HTML(value='''
            <div id="gif-loader" style="display:none; align-items:center; margin-left:15px;">
                <div class="spinner"></div>
                <span style="margin-left:8px; font-size:11px; color:#666;">Carregando...</span>
            </div>
            <style>
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #3498db;
                border-radius: 50%;
                width: 16px; height: 16px;
                animation: gif-spin 1s linear infinite;
                display: inline-block; vertical-align: middle;
            }
            @keyframes gif-spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            </style>
        ''')

        self.header_title = widgets.HTML(
            value=f"<h3 style='margin-bottom:0; display:inline-block;'>{self.title}</h3>",
            layout=widgets.Layout(margin='0')
        )
        self.header_box = widgets.HBox(
            [self.header_title, self.loader_html],
            layout=widgets.Layout(align_items='center')
        )
        self.header_desc = widgets.HTML(
            value=f"<p style='color:#666; margin-top:5px;'>{self.description}</p>"
        )
        self.main_area = widgets.VBox()
        self.log_output = widgets.Output()

        self.container = widgets.VBox([
            self.header_box,
            self.header_desc,
            self.main_area,
            self.log_output,
        ], layout=widgets.Layout(
            border='1px solid #ccc', padding='10px',
            border_radius='5px', margin='10px 0'
        ))

    def display(self):
        display(self.container)

    def show_loader(self, message=None):
        if message is None:
            message = "Processando..."
        self.loader_html.value = self.loader_html.value.replace(
            'display:none', 'display:flex')
        self.loader_html.value = re.sub(
            r'<span.*?>.*?</span>',
            f'<span style="margin-left:8px; font-size:11px; color:#666;">{message}</span>',
            self.loader_html.value)

    def hide_loader(self):
        self.loader_html.value = self.loader_html.value.replace(
            'display:flex', 'display:none')

    def log(self, message, type="info"):
        color = "black"
        if type == "error":
            color = "red"
        elif type == "success":
            color = "green"
        elif type == "warning":
            color = "orange"
        with self.log_output:
            display(widgets.HTML(
                f"<span style='color:{color}'>[{type.upper()}] {message}</span>"))

    def clear_logs(self):
        self.log_output.clear_output()

    def clear_main(self):
        self.main_area.children = []

    @staticmethod
    def get_status_css():
        return widgets.HTML('''<style>
            .gif-ok   { background:#d4edda !important; border:1px solid #c3e6cb !important; }
            .gif-run  { background:#fff3cd !important; border:1px solid #ffeaa8 !important; }
            .gif-miss { background:#f8f9fa !important; border:1px solid #dee2e6 !important; }
        </style>''')

    @staticmethod
    def make_status_cell(chk, status, css_class, width='auto'):
        status_html = widgets.HTML(
            f'<span style="font-size:10px;font-weight:700;color:#155724">{status}</span>'
            if css_class == 'gif-ok' else
            f'<span style="font-size:10px;font-weight:700;color:#856404">{status}</span>'
            if css_class == 'gif-run' else
            f'<span style="font-size:10px;color:#adb5bd">{status}</span>',
            layout=widgets.Layout(width='32px')
        )
        cell = widgets.HBox(
            [chk, status_html],
            layout=widgets.Layout(
                width=width, min_height='34px',
                justify_content='center', align_items='center',
                padding='0', overflow='hidden', margin='1px'
            )
        )
        cell.add_class(css_class)
        return cell


def make_spinner(msg=None):
    if msg is None:
        msg = "Carregando..."
    return widgets.HTML(f"""
        <div style="display: flex; align-items: center; gap: 8px;">
            <div class="mfm-loader-mini"></div>
            <span style="color: #666; font-size: 11px; font-weight: bold;">{msg}</span>
        </div>
        {_SPINNER_CSS}
    """)


def make_select_all_none(on_all=None, on_none=None, width='70px'):
    btn_all = widgets.Button(
        description="Todos", icon='check-square',
        layout=widgets.Layout(width=width), button_style='info')
    btn_none = widgets.Button(
        description="Nenhum", icon='square-o',
        layout=widgets.Layout(width='75px'), button_style='warning')
    if on_all:
        btn_all.on_click(on_all)
    if on_none:
        btn_none.on_click(on_none)
    return btn_all, btn_none, widgets.HBox([btn_all, btn_none])


def make_empty_state(message, padding="20px"):
    return widgets.HTML(
        f"<div style='padding:{padding}; text-align:center; color:#999; "
        f"border:1px dashed #ccc;'><i>{message}</i></div>")


def make_sync_button(description, on_click_callback, ui=None,
                     width='220px', button_style='success'):
    btn = widgets.Button(
        description=description, icon='refresh',
        button_style=button_style,
        layout=widgets.Layout(width=width))

    def _handler(b):
        if ui:
            ui.show_loader("Sincronizando...")
        btn.description = "Sincronizando..."
        btn.disabled = True
        try:
            on_click_callback()
        finally:
            btn.description = description
            btn.disabled = False
            if ui:
                ui.hide_loader()

    btn.on_click(_handler)
    return btn


def inline_confirm(btn, on_confirm, on_cancel=None):
    container = getattr(btn, 'parent', None)
    if container is None:
        return
    children = list(container.children)
    try:
        idx = children.index(btn)
    except ValueError:
        return

    btn_back = widgets.Button(
        description="Voltar", button_style='',
        layout=widgets.Layout(width='70px', height='26px',
                              padding='0', font_size='11px'))
    btn_ok = widgets.Button(
        description="OK", button_style='danger',
        layout=widgets.Layout(width='50px', height='26px',
                              padding='0', font_size='11px'))
    confirm_box = widgets.HBox(
        [btn_back, btn_ok],
        layout=widgets.Layout(align_items='center', gap='3px'))
    spinner = make_spinner(msg="Excluindo...")

    def _restore(_):
        if on_cancel:
            on_cancel()
        container.children = tuple(
            children[:idx] + [btn] + children[idx + 1:])

    def _do_confirm(_):
        container.children = tuple(
            children[:idx] + [spinner] + children[idx + 1:])
        on_confirm()

    btn_back.on_click(_restore)
    btn_ok.on_click(_do_confirm)
    container.children = tuple(
        children[:idx] + [confirm_box] + children[idx + 1:])
