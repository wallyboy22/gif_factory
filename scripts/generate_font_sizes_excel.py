#!/usr/bin/env python3
"""
Gera docs/font_sizes_reference_{timestamp}.xlsx com uma linha por artefato final,
tamanhos de fonte consolidados e thumbnails de múltiplos territórios/produtos.

Lê dinamicamente as colunas exemplo_local, exemplo_local_2, ... do CSV
e gera uma coluna de thumbnail embedada para cada uma.
"""
import csv
from datetime import datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from PIL import Image as PilImage

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "docs" / "font_sizes_reference.csv"
XLSX_PATH = ROOT / "docs" / f"font_sizes_reference_{datetime.now():%Y%m%d_%H%M%S}.xlsx"

HEADER_FILL = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
ALT_FILL = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
FONT_CELL = Font(name="Consolas", size=9)
FONT_BODY = Font(name="Calibri", size=10)
FONT_BOLD = Font(name="Calibri", bold=True, size=11)

THUMB_WIDTH = 800

# Mapeamento de nomes de colunas do CSV para títulos no Excel e largura
DATA_COLUMN_MAP = {
    "artefato": ("Artefato", 24),
    "tamanhos_fonte": ("Tamanhos de Fonte", 80),
    "arquivo_config": ("Arquivo Config", 22),
    "recomendacoes_tamanho": ("Recomendações de Tamanho", 50),
    "outras_recomendacoes": ("Outras Recomendações", 40),
}

# Colunas de exemplo são dinâmicas — detectadas pelo prefixo "exemplo_local"
# Cada uma ganha uma coluna de dados + uma coluna de thumbnail


def make_thumbnail(path: str) -> XlImage | None:
    try:
        with PilImage.open(path) as pil:
            ow, oh = pil.size
            nw = min(ow, THUMB_WIDTH)
            nh = int(oh * (nw / ow))
            pil = pil.resize((nw, nh), PilImage.LANCZOS)
            buf = BytesIO()
            pil.save(buf, format="PNG")
            buf.seek(0)
            img = XlImage(buf)
            img.width = nw
            img.height = nh
            return img
    except Exception as e:
        print(f"  [WARN] Falha no thumbnail '{path}': {e}")
        return None


def build_columns(exemplo_cols: list[str]):
    """Retorna lista de (title, width, is_thumbnail, csv_key) para cada coluna do Excel."""
    cols = []
    # Colunas de dados fixas (na ordem desejada)
    for csv_key in ["artefato", "tamanhos_fonte"]:
        title, width = DATA_COLUMN_MAP[csv_key]
        cols.append((title, width, False, csv_key))
    # Colunas de dados para cada exemplo
    for ec in exemplo_cols:
        label = ec.replace("exemplo_local", "Exemplo Local").strip()
        if not label:
            label = "Exemplo Local"
        cols.append((label, 60, False, ec))
    # Demais colunas fixas
    for csv_key in ["arquivo_config", "recomendacoes_tamanho", "outras_recomendacoes"]:
        if csv_key in DATA_COLUMN_MAP:
            title, width = DATA_COLUMN_MAP[csv_key]
            cols.append((title, width, False, csv_key))
    # Colunas de thumbnail para cada exemplo
    for ec in exemplo_cols:
        label = ec.replace("exemplo_local", "Thumbnail").strip()
        if not label:
            label = "Thumbnail"
        cols.append((label, 90, True, ec))
    return cols


def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    # Detecta colunas de exemplo dinamicamente
    exemplo_cols = sorted([c for c in fieldnames if c.startswith("exemplo_local")],
                          key=lambda x: (len(x), x))

    cols = build_columns(exemplo_cols)
    ncols = len(cols)

    wb = Workbook()
    ws = wb.active
    ws.title = "Referência de Fontes"

    for col_idx, (title, width, is_thumb, csv_key) in enumerate(cols, 1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        ws.column_dimensions[chr(64 + col_idx) if col_idx <= 26 else "?"].width = width

    ws.freeze_panes = "A2"
    last_col_letter = chr(64 + ncols)
    ws.auto_filter.ref = f"A1:{last_col_letter}{len(rows) + 1}"

    for row_idx, row in enumerate(rows, 2):
        artefato = row.get("artefato", "").strip()

        for col_idx, (title, width, is_thumb, csv_key) in enumerate(cols, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = THIN_BORDER
            if row_idx % 2 == 0:
                cell.fill = ALT_FILL

            if is_thumb:
                # Coluna de thumbnail — insere imagem
                path_str = row.get(csv_key, "").strip()
                if path_str:
                    full_path = ROOT / path_str
                    if full_path.exists():
                        img = make_thumbnail(str(full_path))
                        if img:
                            ws.add_image(img, f"{chr(64 + col_idx)}{row_idx}")
                            height_pt = round(img.height * 72 / 96 + 2)
                            ws.row_dimensions[row_idx].height = max(
                                ws.row_dimensions[row_idx].height or 0, height_pt
                            )
                    else:
                        print(f"  [WARN] Arquivo nao encontrado: {full_path}")
                        cell.value = "(arquivo não encontrado)"
                        cell.font = Font(name="Calibri", size=9, color="999999")
            else:
                # Coluna de dados
                val = row.get(csv_key, "")
                cell.value = val.replace("\\n", "\n") if isinstance(val, str) else val
                if title == "Tamanhos de Fonte" or csv_key == "tamanhos_fonte":
                    cell.font = FONT_CELL
                elif title == "Artefato" or csv_key == "artefato":
                    cell.font = FONT_BOLD
                else:
                    cell.font = FONT_BODY
                cell.alignment = Alignment(vertical="top", wrap_text=True)

    wb.save(str(XLSX_PATH))
    print(f"Excel salvo: {XLSX_PATH}")
    print(f"  {len(rows)} linha(s) processada(s)")
    print(f"  {len(exemplo_cols)} coluna(s) de thumbnail")


if __name__ == "__main__":
    main()
