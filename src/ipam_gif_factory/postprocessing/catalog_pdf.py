import glob
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib import colors as rl_colors

from ..config import ConfigLoader
from ..core import DatasetManager, TerritoryManager
from .frame_selector import FRAME_MODES, extract_year, select_frames
from .gif_qr import GIFQRCode

COR_MAPBIOMAS = "#1a5e2a"


class CatalogPDFBuilder:
    """Gera catálogos PDF no formato atlas: legenda → fichas técnicas → collages → links."""

    FRAME_MODES = FRAME_MODES

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.datasets = DatasetManager(config)
        self.territories = TerritoryManager(config)
        self.output_base = config.get_output_dir()

    # ── utils ──────────────────────────────────────────────────────────

    @staticmethod
    def _hc(v):
        v = str(v).strip()
        return rl_colors.HexColor(v if v.startswith("#") else f"#{v}")

    @staticmethod
    def _draw_footer(c, page_w, page_h, page_num, extra=""):
        c.saveState()
        c.setFont("Helvetica", 7)
        c.setFillColor(rl_colors.HexColor("#999999"))
        text = f"MapBiomas GIF Factory | {datetime.now().strftime('%d/%m/%Y %H:%M')} | Página {page_num}"
        if extra:
            text += f" | {extra}"
        c.drawString(20 * mm, 10 * mm, text[:200])
        c.restoreState()

    def _place_image(self, c, img_path, x, y, max_w, max_h):
        try:
            img = PILImage.open(img_path)
            iw, ih = img.size
            scale = min(max_w / iw, max_h / ih, 1.0)
            dw, dh = iw * scale, ih * scale
            cx, cy = x + max_w / 2, y + max_h / 2
            c.drawImage(ImageReader(img_path), cx - dw / 2, cy - dh / 2,
                        width=dw, height=dh, preserveAspectRatio=True)
        except Exception:
            c.saveState()
            c.setFont("Helvetica", 9)
            c.drawString(x, y + max_h / 2, f"[erro: {os.path.basename(img_path)}]")
            c.restoreState()

    @staticmethod
    def _draw_accent_bar(c, x, y, w, h=3):
        c.setFillColor(COR_MAPBIOMAS)
        c.rect(x, y, w, h, fill=1, stroke=0)

    # ── métodos incrementais ──────────────────────────────────────────

    @staticmethod
    def _needs_regeneration(output_path: str, run: dict) -> bool:
        if not os.path.exists(output_path):
            return True
        meta_path = os.path.join(
            run["output_dir"], f"metadata_{run['product_id']}.json"
        )
        if os.path.isfile(meta_path):
            if os.path.getmtime(meta_path) > os.path.getmtime(output_path):
                return True
        return False

    # ── descoberta de runs ──────────────────────────────────────────────

    def _discover_runs(
        self,
        dataset_id: Optional[str] = None,
        product_id: Optional[str] = None,
        territory_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        runs = []
        if not os.path.isdir(self.output_base):
            return runs

        ds_dirs = [os.path.join(self.output_base, ds["id"]) for ds in self.datasets.list_datasets()]
        if dataset_id:
            ds_dirs = [d for d in ds_dirs if os.path.basename(d) == dataset_id]
        ds_dirs = [d for d in ds_dirs if os.path.isdir(d)]

        for ds_dir in ds_dirs:
            ds_id = os.path.basename(ds_dir)
            prod_dirs = sorted([
                os.path.join(ds_dir, p)
                for p in os.listdir(ds_dir)
                if os.path.isdir(os.path.join(ds_dir, p))
            ])
            if product_id:
                prod_dirs = [d for d in prod_dirs if os.path.basename(d) == product_id]

            for prod_dir in prod_dirs:
                prod_id = os.path.basename(prod_dir)
                terr_dirs = sorted([
                    os.path.join(prod_dir, t)
                    for t in os.listdir(prod_dir)
                    if os.path.isdir(os.path.join(prod_dir, t))
                ])
                if territory_id:
                    terr_dirs = [d for d in terr_dirs if os.path.basename(d) == territory_id]

                for terr_dir in terr_dirs:
                    terr_id = os.path.basename(terr_dir)
                    meta_path = os.path.join(terr_dir, f"metadata_{prod_id}.json")
                    if not os.path.isfile(meta_path):
                        continue

                    with open(meta_path, encoding="utf-8") as f:
                        meta = json.load(f)

                    runs.append({
                        "dataset_id": ds_id,
                        "product_id": prod_id,
                        "territory_id": terr_id,
                        "output_dir": terr_dir,
                        "metadata": meta,
                    })
        return runs

    # ── collage PNG discovery ─────────────────────────────────────────

    @staticmethod
    def _find_collage_png(run: Dict[str, Any], mode: str) -> Optional[str]:
        output_dir = run["output_dir"]
        prod_id = run["product_id"]
        terr_id = run["territory_id"]

        path = os.path.join(output_dir, f"{prod_id}_{terr_id}_collage_{mode}.png")
        if os.path.isfile(path):
            return path

        pattern = os.path.join(output_dir, f"{prod_id}_{terr_id}_collage*.png")
        collages = sorted(glob.glob(pattern))
        return collages[-1] if collages else None

    @staticmethod
    def _find_all_collages(run: Dict[str, Any]) -> List[str]:
        output_dir = run["output_dir"]
        prod_id = run["product_id"]
        terr_id = run["territory_id"]
        pattern = os.path.join(output_dir, f"{prod_id}_{terr_id}_collage*.png")
        return sorted(glob.glob(pattern))

    @staticmethod
    def _collage_mode_label(img_path: str, run: Dict[str, Any]) -> str:
        base = os.path.basename(img_path).replace(".png", "")
        prefix = f"{run['product_id']}_{run['territory_id']}_collage"
        suffix = base.replace(prefix, "", 1).lstrip("_")
        return suffix if suffix else "principal"

    # ═══════════════════════════════════════════════════════════════════
    #  FRONT MATTER — LEGENDA
    # ═══════════════════════════════════════════════════════════════════

    def _make_legend_page(self, c, run, page_w, page_h, page_num):
        meta = run["metadata"]
        viz = meta.get("visualization", {})

        self._draw_footer(c, page_w, page_h, page_num)
        self._draw_accent_bar(c, 20 * mm, page_h - 25 * mm, page_w - 40 * mm)

        y = page_h - 30 * mm
        c.setFont("Helvetica-Bold", 22)
        c.setFillColor(COR_MAPBIOMAS)
        c.drawString(20 * mm, y, "LEGENDA")
        y -= 14 * mm

        c.setFont("Helvetica", 11)
        c.setFillColor(rl_colors.black)
        c.drawString(20 * mm, y, viz.get("name", "Dado") + " — " + viz.get("label", ""))
        y -= 10 * mm

        palette = viz.get("palette", [])
        discrete = viz.get("discrete_labels")
        cmap_type = viz.get("cmap_type", "sequential")
        is_discrete = bool(discrete and any(discrete))

        # Fallback: infer labels for binary/categorical vizz sem discrete_labels
        if not is_discrete and cmap_type in ("binary", "categorical") and palette:
            discrete = [f"Classe {i}" if i > 0 else "Não observado" for i in range(len(palette))]
            is_discrete = True

        if is_discrete:
            self._draw_discrete_legend(c, palette, discrete, cmap_type, 20 * mm, y, page_w)
        elif palette:
            self._draw_continuous_legend(c, palette, viz, 20 * mm, y, page_w)

        # Espaço restante: parâmetros de visualização
        if y > 25 * mm:
            y = max(y - 6 * mm, 25 * mm)
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(COR_MAPBIOMAS)
            c.drawString(20 * mm, y, "Parâmetros de visualização")
            y -= 14

            params = [
                ("cmap_type", viz.get("cmap_type")),
                ("min", str(viz.get("min"))),
                ("max", str(viz.get("max"))),
                ("palette", json.dumps(viz.get("palette", []))[:120]),
            ]
            c.setFont("Courier", 6)
            c.setFillColor(rl_colors.HexColor("#555555"))
            for key, val in params:
                if val:
                    c.drawString(20 * mm, y, f"  {key}: {val}")
                    y -= 9



    def _draw_discrete_legend(self, c, palette, discrete, cmap_type, x_start, y, page_w):
        col_w = (page_w - 2 * x_start) / 4
        row_h = 28
        mx = 8

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(rl_colors.HexColor("#555555"))
        c.drawString(x_start, y, "Valor")
        c.drawString(x_start + col_w, y, "Cor")
        c.drawString(x_start + 2 * col_w, y, "RGB")
        c.drawString(x_start + 3 * col_w, y, "Descrição")
        y -= row_h

        for i, lbl in enumerate(discrete):
            if not lbl:
                if i == 0:
                    lbl = "Não observado"
                else:
                    continue
            hex_c = palette[i] if i < len(palette) else "cccccc"
            hex_c = hex_c if hex_c.startswith("#") else f"#{hex_c}"
            rgb_hex = hex_c.lstrip("#").upper()

            c.setFont("Helvetica", 9)
            c.setFillColor(rl_colors.black)
            c.drawString(x_start + mx, y, str(i))

            c.setFillColor(self._hc(hex_c))
            c.roundRect(x_start + col_w + mx, y - 2, 16, 16, 3, fill=1, stroke=0)

            c.setFont("Courier", 7)
            c.setFillColor(rl_colors.HexColor("#666666"))
            c.drawString(x_start + 2 * col_w + mx, y, f"#{rgb_hex}")

            c.setFillColor(rl_colors.black)
            c.setFont("Helvetica", 9)
            c.drawString(x_start + 3 * col_w + mx, y, lbl)
            y -= row_h

    def _draw_continuous_legend(self, c, palette, viz, x_start, y, page_w):
        bar_w = page_w - 2 * x_start - 40 * mm
        bar_h = 10 * mm
        n = len(palette)
        seg_w = bar_w / max(n - 1, 1)

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(rl_colors.HexColor("#555555"))
        c.drawString(x_start, y, "Paleta de cores")
        y -= 8
        for i in range(n - 1):
            c.setFillColor(self._hc(palette[i]))
            c.rect(x_start + i * seg_w, y, seg_w, bar_h, fill=1, stroke=0)
        c.setFillColor(self._hc(palette[-1]))
        c.rect(x_start + (n - 1) * seg_w, y, seg_w, bar_h, fill=1, stroke=0)
        y -= bar_h + 4

        vmin = viz.get("min", 0)
        vmax = viz.get("max", 1)
        c.setFont("Helvetica", 8)
        c.setFillColor(rl_colors.black)
        c.drawString(x_start, y, str(vmin))
        c.drawRightString(x_start + bar_w, y, str(vmax))

    # ═══════════════════════════════════════════════════════════════════
    #  FRONT MATTER — FICHA TÉCNICA
    # ═══════════════════════════════════════════════════════════════════

    def _make_tech_page(self, c, run, page_w, page_h, page_num, territory_names=None):
        meta = run["metadata"]
        prod = meta.get("product", {})
        ds = meta.get("dataset", {})
        proc = meta.get("processor", {})

        self._draw_footer(c, page_w, page_h, page_num)
        self._draw_accent_bar(c, 20 * mm, page_h - 25 * mm, page_w - 40 * mm)

        y = page_h - 30 * mm
        c.setFont("Helvetica-Bold", 22)
        c.setFillColor(COR_MAPBIOMAS)
        c.drawString(20 * mm, y, "FICHA TÉCNICA")
        y -= 16 * mm

        lh = 20

        def draw_row(label, value, font_value="Helvetica", value_x=65 * mm):
            nonlocal y
            if not value:
                return
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(rl_colors.black)
            c.drawString(20 * mm, y, label)
            c.setFont(font_value, 8 if font_value == "Courier" else 10)
            c.drawString(value_x, y, str(value)[:120])
            y -= lh

        draw_row("Produto:", prod.get("name"))
        draw_row("Coleção:", ds.get("description"))
        draw_row("Processor:", proc.get("name"))
        desc = proc.get("description")
        if desc:
            c.setFont("Helvetica", 9)
            c.setFillColor(rl_colors.black)
            c.drawString(65 * mm, y + lh, desc[:120])
            y += 2
        draw_row("Asset:", prod.get("asset"), font_value="Courier", value_x=55 * mm)
        y -= 3 * mm

        temporal = prod.get("temporal_range", [])
        if temporal and len(temporal) == 2:
            draw_row("Período:", f"{temporal[0]} — {temporal[1]}")
            y -= 2 * mm

        # Estrutura das bandas
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(COR_MAPBIOMAS)
        c.drawString(20 * mm, y, "Estrutura das bandas")
        y -= lh
        c.setFont("Courier", 9)
        c.setFillColor(rl_colors.black)
        c.drawString(20 * mm, y, f"{prod.get('name', run['product_id'])}_YYYY")
        y -= lh - 2
        c.setFont("Helvetica", 8)
        c.setFillColor(rl_colors.HexColor("#555555"))
        c.drawString(20 * mm, y, "Cada banda corresponde a um ano (YYYY = ano do dado).")
        y -= 6 * mm

        # Territórios processados
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(COR_MAPBIOMAS)
        c.drawString(20 * mm, y, "Territórios processados")
        y -= lh

        names = territory_names or [t.get("name", t["id"]) for t in self.territories.list_territories()]
        c.setFont("Helvetica", 8)
        col_w = (page_w - 40 * mm) / 2
        for i, name in enumerate(names):
            col = i % 2
            row = i // 2
            ty = y - row * 12
            if ty < 15 * mm:
                break
            c.drawString(20 * mm + col * col_w, ty, f"• {name}")

    # ═══════════════════════════════════════════════════════════════════
    #  BODY — PÁGINA DE FRAME (um PNG por página)
    # ═══════════════════════════════════════════════════════════════════

    def _make_frame_page(self, c, img_path, run, page_w, page_h, page_num):
        meta = run["metadata"]
        prod_id = run["product_id"]
        terr_id = run["territory_id"]
        prod_name = meta.get("product", {}).get("name", prod_id)
        terr_name = meta.get("territory", {}).get("name", terr_id)

        year = extract_year(img_path)
        year_str = str(year) if year is not None else ""
        self._draw_footer(c, page_w, page_h, page_num, extra=f"{prod_id}/{terr_id}{'/' + year_str if year_str else ''}")

        usable_w = page_w - 40 * mm
        usable_h = page_h - 40 * mm - 12 * mm
        self._place_image(c, img_path, 20 * mm, 20 * mm, usable_w, usable_h)

        footer_text = f"{prod_name} · {terr_name}"
        if year_str:
            footer_text += f" · {year_str}"
        c.saveState()
        c.setFont("Helvetica", 8)
        c.setFillColor(rl_colors.HexColor("#555555"))
        c.drawCentredString(page_w / 2, 8 * mm, footer_text)
        c.restoreState()

    # ═══════════════════════════════════════════════════════════════════
    #  BODY — PÁGINA DE COLAGEM (um collage PNG por página)
    # ═══════════════════════════════════════════════════════════════════

    def _make_collage_page(self, c, img_path, run, page_w, page_h, page_num, mode="all"):
        meta = run["metadata"]
        prod_id = run["product_id"]
        terr_id = run["territory_id"]
        prod_name = meta.get("product", {}).get("name", prod_id)
        terr_name = meta.get("territory", {}).get("name", terr_id)

        self._draw_footer(c, page_w, page_h, page_num, extra=f"{prod_id}/{terr_id}/collage-{mode}")

        usable_w = page_w - 40 * mm
        usable_h = page_h - 40 * mm - 12 * mm
        self._place_image(c, img_path, 20 * mm, 20 * mm, usable_w, usable_h)

        footer_text = f"{prod_name} · {terr_name} · Collage {mode}"
        c.saveState()
        c.setFont("Helvetica", 8)
        c.setFillColor(rl_colors.HexColor("#555555"))
        c.drawCentredString(page_w / 2, 8 * mm, footer_text)
        c.restoreState()

    # ═══════════════════════════════════════════════════════════════════
    #  BACK MATTER — DOWNLOADS + CITAÇÃO
    # ═══════════════════════════════════════════════════════════════════

    def _make_back_matter(self, c, all_runs, mode, page_w, page_h, page_num):
        self._draw_footer(c, page_w, page_h, page_num)
        self._draw_accent_bar(c, 20 * mm, page_h - 25 * mm, page_w - 40 * mm)

        y = page_h - 30 * mm
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(COR_MAPBIOMAS)
        c.drawString(20 * mm, y, "Downloads e Referência")
        y -= 14 * mm

        # QR codes dos GIFs
        qr_per_row = 4
        qr_size = 40 * mm
        qr_gap = 6 * mm
        start_x = 20 * mm
        valid_runs = []

        for r in all_runs:
            od = r["output_dir"]
            pid = r["product_id"]
            tid = r["territory_id"]

            gif_path = os.path.join(od, f"{pid}_{tid}_gif_{mode}.gif")
            if not os.path.isfile(gif_path):
                pattern = os.path.join(od, f"{pid}_{tid}_*.gif")
                gifs = sorted(glob.glob(pattern))
                gif_path = gifs[-1] if gifs else None
            if gif_path and os.path.isfile(gif_path):
                try:
                    qr_img = GIFQRCode.make_gif_qr_from_path(
                        os.path.abspath(gif_path),
                        label=os.path.basename(gif_path),
                    )
                    qr_tmp = os.path.join(od, f".qr_backmatter_{pid}_{tid}.png")
                    qr_img.save(qr_tmp)
                    valid_runs.append((qr_tmp, pid, tid, os.path.basename(gif_path)))
                except Exception:
                    pass

        if valid_runs:
            for idx, (qr_tmp, pid, tid, gif_name) in enumerate(valid_runs):
                col = idx % qr_per_row
                row = idx // qr_per_row
                qx = start_x + col * (qr_size + qr_gap)
                qy = y - row * (qr_size + 18 * mm)

                if qy < 30 * mm:
                    c.showPage()
                    page_num += 1
                    self._draw_footer(c, page_w, page_h, page_num)
                    y = page_h - 20 * mm
                    qy = y
                    self._draw_accent_bar(c, 20 * mm, y - 5 * mm, page_w - 40 * mm)
                    y -= 10 * mm
                    qy = y

                try:
                    c.drawImage(ImageReader(qr_tmp), qx, qy - qr_size,
                                width=qr_size, height=qr_size)
                except Exception:
                    pass
                c.setFont("Helvetica", 6)
                c.setFillColor(rl_colors.black)
                c.drawString(qx, qy - qr_size - 8, f"{pid}/{tid}"[:30])

                try:
                    os.remove(qr_tmp)
                except OSError:
                    pass

            last_qr_row = (len(valid_runs) - 1) // qr_per_row
            y = y - (last_qr_row + 1) * (qr_size + 18 * mm) - 10 * mm
        else:
            y -= 6 * mm

        # Citação
        c.saveState()
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(COR_MAPBIOMAS)
        c.drawString(20 * mm, y, "Citação")
        y -= 12

        c.setFont("Helvetica", 8)
        c.setFillColor(rl_colors.black)
        citation = (
            '"MapBiomas – Coleção 5 do MapBiomas Fogo, '
            f'acessado em {datetime.now().strftime("%d/%m/%Y")} '
            'a partir de https://brasil.mapbiomas.org/mapbiomas-fogo/".'
        )
        c.drawString(20 * mm, y, citation[:120])
        y -= 10
        c.drawString(20 * mm, y, citation[120:] if len(citation) > 120 else "")
        y -= 12

        c.setFont("Helvetica", 8)
        c.drawString(20 * mm, y, "DOI: https://doi.org/10.58053/MapBiomas/DREUES")
        y -= 8 * mm

        # Observação sobre GeoTIFFs/GeoPDFs
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(COR_MAPBIOMAS)
        c.drawString(20 * mm, y, "Arquivos Geo")
        y -= 12
        c.setFont("Helvetica", 8)
        c.setFillColor(rl_colors.black)
        c.drawString(20 * mm, y, "Os arquivos GeoTIFF e GeoPDF de cada frame estão disponíveis nos diretórios de saída:")
        y -= 10
        c.setFont("Courier", 7)
        c.drawString(20 * mm, y, f"  {self.output_base}/<dataset>/<product>/<territory>/")

        c.restoreState()

    # ═══════════════════════════════════════════════════════════════════
    #  CONSTRUTOR DE CATÁLOGO
    # ═══════════════════════════════════════════════════════════════════

    def _make_catalog(self, runs, output_path, mode="all"):
        page_w, page_h = landscape(A4)
        c = pdf_canvas.Canvas(output_path, pagesize=landscape(A4))
        page_num = 0

        by_product = defaultdict(list)
        for r in runs:
            by_product[r["product_id"]].append(r)

        for pid, product_runs in by_product.items():
            ref = product_runs[0]

            page_num += 1
            self._make_legend_page(c, ref, page_w, page_h, page_num)
            c.showPage()

            page_num += 1
            terr_names = [r["metadata"].get("territory", {}).get("name", r["territory_id"]) for r in product_runs]
            self._make_tech_page(c, ref, page_w, page_h, page_num, territory_names=terr_names)
            c.showPage()

            for r in product_runs:
                if mode == "all":
                    collages = self._find_all_collages(r)
                    for cp in collages:
                        mlabel = self._collage_mode_label(cp, r)
                        page_num += 1
                        self._make_collage_page(c, cp, r, page_w, page_h, page_num, mode=mlabel)
                        c.showPage()
                else:
                    meta = r["metadata"]
                    output_dir = r["output_dir"]
                    frame_names = meta.get("output", {}).get("frames", [])
                    frame_paths = [os.path.join(output_dir, fn) for fn in frame_names]
                    frame_paths = [p for p in frame_paths if os.path.isfile(p)]

                    selected = select_frames(frame_paths, mode)
                    for fp in selected:
                        page_num += 1
                        self._make_frame_page(c, fp, r, page_w, page_h, page_num)
                        c.showPage()

                    collage_png = self._find_collage_png(r, mode)
                    if collage_png:
                        mlabel = self._collage_mode_label(collage_png, r)
                        page_num += 1
                        self._make_collage_page(c, collage_png, r, page_w, page_h, page_num, mode=mlabel)
                        c.showPage()

        page_num += 1
        self._make_back_matter(c, runs, mode, page_w, page_h, page_num)
        c.showPage()

        c.save()
        print(f"  [OK] {output_path} ({page_num} páginas)")

    # ═══════════════════════════════════════════════════════════════════
    #  BUILDERS PÚBLICOS
    # ═══════════════════════════════════════════════════════════════════

    def build_mega(self, output_dir, mode="all", filename="catalogo_completo.pdf"):
        os.makedirs(output_dir, exist_ok=True)
        runs = self._discover_runs()
        if not runs:
            print("  [SKIP] Nenhum run encontrado")
            return
        out_path = os.path.join(output_dir, filename)
        if not self._needs_regeneration(out_path, runs[0]):
            print(f"  [SKIP] {filename} já atualizado")
            return
        self._make_catalog(runs, out_path, mode=mode)

    def build_by_territory(self, output_dir, mode="all"):
        os.makedirs(output_dir, exist_ok=True)
        all_runs = self._discover_runs()
        by_territory: Dict[str, List[Dict[str, Any]]] = {}
        for r in all_runs:
            by_territory.setdefault(r["territory_id"], []).append(r)

        for tid, runs in by_territory.items():
            if not runs:
                continue
            out_path = os.path.join(output_dir, f"catalogo_{tid}.pdf")
            if not self._needs_regeneration(out_path, runs[0]):
                print(f"  [SKIP] catalogo_{tid}.pdf já atualizado")
                continue
            self._make_catalog(runs, out_path, mode=mode)

    def build_by_collection(self, output_dir, mode="all"):
        os.makedirs(output_dir, exist_ok=True)
        all_runs = self._discover_runs()
        by_product: Dict[str, List[Dict[str, Any]]] = {}
        for r in all_runs:
            by_product.setdefault(r["product_id"], []).append(r)

        for pid, runs in by_product.items():
            if not runs:
                continue
            out_path = os.path.join(output_dir, f"catalogo_{pid}.pdf")
            if not self._needs_regeneration(out_path, runs[0]):
                print(f"  [SKIP] catalogo_{pid}.pdf já atualizado")
                continue
            self._make_catalog(runs, out_path, mode=mode)

    def build_by_territory_collection(self, output_dir, mode="all"):
        os.makedirs(output_dir, exist_ok=True)
        all_runs = self._discover_runs()
        for r in all_runs:
            tid, pid = r["territory_id"], r["product_id"]
            out_path = os.path.join(output_dir, f"catalogo_{pid}_{tid}.pdf")
            if not self._needs_regeneration(out_path, r):
                print(f"  [SKIP] catalogo_{pid}_{tid}.pdf já atualizado")
                continue
            self._make_catalog([r], out_path, mode=mode)
