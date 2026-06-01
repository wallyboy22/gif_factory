import math
import os
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image as PILImage, ImageDraw, ImageFont


def _parse_color(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _find_font() -> Optional[str]:
    candidates = [
        "C:\\Windows\\Fonts\\Arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\Calibri.ttf",
        "C:\\Windows\\Fonts\\DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _ensure_rgb(image: PILImage.Image) -> PILImage.Image:
    if image.mode == "RGBA":
        bg = PILImage.new("RGB", image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[3])
        return bg
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


class FrameProcessor:
    """Processar frames individuais (labels, redimensionamento, etc)."""

    FONT_PATH = _find_font()

    @staticmethod
    def add_year_label(
        image_path: str,
        text: str,
        position: str = "top_left",
        font_size: int = 48,
        text_color: Tuple[int, int, int] = (255, 255, 255),
        outline_color: Tuple[int, int, int] = (0, 0, 0),
        padding_top: int = 0,
        bar_color: Optional[Tuple[int, int, int]] = None,
        max_width: Optional[int] = None,
        subtitle: Optional[str] = None,
        subtitle_size: Optional[int] = None,
    ) -> None:
        image = _ensure_rgb(PILImage.open(image_path))

        font1 = FrameProcessor._make_font(font_size)
        font2 = FrameProcessor._make_font(subtitle_size or font_size - 10) if subtitle else None

        if padding_top > 0:
            bg = bar_color if bar_color else (0, 0, 0)
            padded = PILImage.new("RGB", (image.width, image.height + padding_top), bg)
            padded.paste(image, (0, padding_top))
            image = padded

        draw = ImageDraw.Draw(image)

        if max_width is None:
            max_width = image.width - 40

        positions = {
            "top_left": (20, 20),
            "top_right": (image.width - 200, 20),
            "bottom_left": (20, image.height - font_size - 20),
            "bottom_right": (image.width - 200, image.height - font_size - 20),
        }
        pos = positions.get(position, (20, 20))

        l1_lines = FrameProcessor._wrap_text(draw, text, font1, max_width)
        l1_h = draw.textbbox((0, 0), "Ay", font=font1)[3] + 4
        l2_lines = FrameProcessor._wrap_text(draw, subtitle, font2, max_width) if subtitle and font2 else []
        l2_h = draw.textbbox((0, 0), "Ay", font=font2)[3] + 4 if l2_lines else 0

        gap_between = 8
        total_lines = l1_lines + l2_lines
        line_heights = [l1_h] * len(l1_lines) + [l2_h] * len(l2_lines)
        total_w = max(draw.textbbox((0, 0), l, font=font1)[2] for l in l1_lines + [""]) if l1_lines else 0
        if l2_lines:
            total_w = max(total_w, max(draw.textbbox((0, 0), l, font=font2)[2] for l in l2_lines))
        total_h = len(l1_lines) * l1_h + (gap_between if l2_lines else 0) + len(l2_lines) * l2_h

        if bar_color is None:
            bar_padding = 12
            draw.rectangle(
                [pos[0] - bar_padding, pos[1] - bar_padding,
                 pos[0] + total_w + bar_padding, pos[1] + total_h + bar_padding],
                fill=(40, 40, 40),
            )

            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                cy = pos[1]
                for l in l1_lines:
                    draw.text((pos[0] + dx, cy + dy), l, font=font1, fill=outline_color)
                    cy += l1_h
                cy += gap_between
                for l in l2_lines:
                    draw.text((pos[0] + dx, cy + dy), l, font=font2, fill=outline_color)
                    cy += l2_h

        cy = pos[1]
        for l in l1_lines:
            draw.text((pos[0], cy), l, font=font1, fill=text_color)
            cy += l1_h
        cy += gap_between
        for l in l2_lines:
            draw.text((pos[0], cy), l, font=font2, fill=text_color)
            cy += l2_h

        image.save(image_path)

    @staticmethod
    def batch_add_labels(
        image_paths: Dict[str, str],
        position: str = "top_left",
        font_size: int = 48,
        padding_top: int = 0,
        **kwargs,
    ) -> None:
        for path, label in image_paths.items():
            try:
                FrameProcessor.add_year_label(path, label, position, font_size=font_size, padding_top=padding_top, **kwargs)
            except Exception as e:
                print(f"Erro ao adicionar label em {path}: {e}")

    @staticmethod
    def add_frame_header(
        image_path: str,
        line1: str,
        line2: str,
        line1_size: int = 80,
        line2_size: int = 80,
        padding_top: int = 160,
        gap: int = 10,
        subtitle: Optional[str] = None,
        subtitle_size: Optional[int] = None,
    ) -> None:
        image = _ensure_rgb(PILImage.open(image_path))
        padded = PILImage.new("RGB", (image.width, image.height + padding_top + gap), (255, 255, 255))
        padded.paste(image, (0, padding_top + gap))
        draw = ImageDraw.Draw(padded)

        font1 = FrameProcessor._make_font(line1_size)
        font2 = FrameProcessor._make_font(line2_size)
        font_sub = FrameProcessor._make_font(subtitle_size or line1_size - 10) if subtitle else None

        max_w = padded.width - 40
        l1_lines = FrameProcessor._wrap_text(draw, line1, font1, max_w)
        l1_h = draw.textbbox((0, 0), "Ay", font=font1)[3] + 6
        sub_lines = FrameProcessor._wrap_text(draw, subtitle, font_sub, max_w) if subtitle and font_sub else []
        sub_h = draw.textbbox((0, 0), "Ay", font=font_sub)[3] + 4 if sub_lines else 0

        y = 20
        for l in l1_lines:
            draw.text((20, y), l, font=font1, fill=(0, 0, 0))
            y += l1_h
        if sub_lines:
            y += 4
            for l in sub_lines:
                draw.text((20, y), l, font=font_sub, fill=(80, 80, 80))
                y += sub_h
        l2_y = y + 8
        draw.text((20, l2_y), line2, font=font2, fill=(0, 0, 0))

        draw.line([(0, padding_top - 1), (padded.width, padding_top - 1)], fill=(200, 200, 200), width=1)

        image.close()
        padded.save(image_path)
        padded.save(image_path)

    @staticmethod
    def batch_add_frame_headers(
        image_paths: List[str],
        line1: str,
        label_map: Dict[str, str],
        line1_size: int = 80,
        line2_size: int = 80,
        padding_top: int = 150,
        gap: int = 20,
        subtitle: Optional[str] = None,
        subtitle_size: Optional[int] = None,
    ) -> None:
        for path in image_paths:
            try:
                line2 = label_map.get(path, "")
                FrameProcessor.add_frame_header(path, line1, line2, line1_size, line2_size, padding_top, gap=gap, subtitle=subtitle, subtitle_size=subtitle_size)
            except Exception as e:
                print(f"Erro ao adicionar header em {path}: {e}")

    @staticmethod
    def _truncate_label(lbl: str, max_chars: int = 35) -> str:
        if len(lbl) > max_chars:
            print(f"  [AVISO] Label truncada ({len(lbl)} chars, max {max_chars}): '{lbl}'")
            return lbl[:max_chars-3].rstrip() + "..."
        return lbl

    @staticmethod
    def _make_font(size: int) -> ImageFont.FreeTypeFont:
        try:
            if FrameProcessor.FONT_PATH:
                return ImageFont.truetype(FrameProcessor.FONT_PATH, size)
        except (IOError, OSError):
            pass
        return ImageFont.load_default()

    @staticmethod
    def _wrap_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        words = text.split()
        if not words:
            return [""]
        lines = []
        cur = ""
        for w in words:
            test = f"{cur} {w}".strip()
            if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    @staticmethod
    def _layout_discrete(
        width: int, entries: List[Tuple[Tuple[int,int,int], str]],
        tfont: ImageFont.FreeTypeFont,
        box_size: int, gap: int, margin: int,
        min_font: int = 8, max_cols: int = 4,
    ) -> Tuple[int, int, ImageFont.FreeTypeFont, int]:
        max_lbl = max(tfont.getlength(lbl) for _, lbl in entries)
        entry_w = box_size + gap
        tfs = tfont.size

        for try_cols in range(min(max_cols, len(entries)), 0, -1):
            avail = (width - 2 * margin) // try_cols - entry_w
            fs = tfs
            while fs > min_font and max_lbl > avail:
                fs -= 2
                tfont = FrameProcessor._make_font(fs)
                max_lbl = max(tfont.getlength(lbl) for _, lbl in entries)
            if max_lbl <= avail:
                return try_cols, math.ceil(len(entries) / try_cols), tfont, fs

        return 1, len(entries), tfont, tfs

    @staticmethod
    def add_legend(
        image_path: str,
        palette: List[str],
        vmin: float = 0,
        vmax: float = 1,
        label: str = "",
        font_size: int = 50,
        discrete_labels: Optional[List[str]] = None,
        cmap_type: str = "sequential",
    ) -> None:
        image = _ensure_rgb(PILImage.open(image_path))
        width = image.width

        colors = [_parse_color(c) for c in palette]
        n = len(colors)
        is_discrete = (n <= 2) or (cmap_type == "categorical")

        margin = 25
        label_h = 55 if label else 0

        if is_discrete:
            box_size = 28
            row_h = 40
            entries = []
            for i in range(n):
                if discrete_labels and i < len(discrete_labels):
                    lbl = discrete_labels[i]
                    if not lbl:
                        continue
                elif n == 2 and vmin == 0 and vmax == 1:
                    lbl = ["Não queimado", "Queimado"][i]
                else:
                    val = vmin + (vmax - vmin) * i / (n - 1) if n > 1 else vmin
                    lbl = str(int(val))
                lbl = FrameProcessor._truncate_label(lbl)
                entries.append((colors[i], lbl))
            n_entries = len(entries)

            tfont = FrameProcessor._make_font(font_size - 8)
            cols, rows, tfont, _ = FrameProcessor._layout_discrete(
                width, entries, tfont, box_size, 8, margin, max_cols=3)
            content_h = rows * row_h
        else:
            box_size = 50
            content_h = box_size + 50

        legend_h = label_h + content_h + margin * 2

        padded = PILImage.new("RGB", (width, image.height + legend_h), (255, 255, 255))
        padded.paste(image, (0, 0))
        draw = ImageDraw.Draw(padded)

        sep_y = image.height
        draw.line([(0, sep_y), (width, sep_y)], fill=(200, 200, 200), width=1)

        try:
            lfont = ImageFont.truetype(FrameProcessor.FONT_PATH, font_size) if FrameProcessor.FONT_PATH else ImageFont.load_default()
        except (IOError, OSError):
            lfont = ImageFont.load_default()

        y = image.height + margin

        if label:
            draw.text((20, y), label, font=lfont, fill=(0, 0, 0))
        y += label_h

        if is_discrete:
            col_w = (width - 2 * margin) // cols
            for idx, (color, lbl) in enumerate(entries):
                col = idx // rows if cols > 1 else idx // n_entries
                row = idx % rows if cols > 1 else idx
                bx = margin + col * col_w
                by = y + row * row_h
                draw.rectangle([bx, by, bx + box_size, by + box_size], fill=color)
                draw.rectangle([bx, by, bx + box_size, by + box_size], outline=(100, 100, 100), width=2)
                draw.text((bx + box_size + 10, by + 2), lbl, font=tfont, fill=(0, 0, 0))
        else:
            bar_x, bar_y = margin, y
            bar_w = width - 2 * margin
            for i in range(n - 1):
                x0 = int(bar_x + i * bar_w / (n - 1))
                x1 = int(bar_x + (i + 1) * bar_w / (n - 1))
                draw.rectangle([x0, bar_y, x1, bar_y + box_size], fill=colors[i])
            draw.rectangle([int(bar_x + (n - 1) * bar_w / (n - 1)), bar_y, int(bar_x + bar_w), bar_y + box_size], fill=colors[-1])

            num_ticks = min(n, 6)
            for i in range(num_ticks):
                val = vmin + (vmax - vmin) * i / (num_ticks - 1) if num_ticks > 1 else vmin
                xi = int(bar_x + i * bar_w / (num_ticks - 1))
                lbl = str(int(val))
                bbox = draw.textbbox((0, 0), lbl, font=tfont)
                lw = bbox[2] - bbox[0]
                draw.text((xi - lw // 2, bar_y + box_size + 5), lbl, font=tfont, fill=(0, 0, 0))
                draw.line([(xi, bar_y + box_size), (xi, bar_y + box_size + 5)], fill=(0, 0, 0))

        image.close()
        padded.save(image_path)

    @staticmethod
    def batch_add_legends(
        image_paths: List[str],
        palette: List[str],
        vmin: float = 0,
        vmax: float = 1,
        label: str = "",
        font_size: int = 50,
        cmap_type: str = "sequential",
    ) -> None:
        for path in image_paths:
            try:
                FrameProcessor.add_legend(path, palette, vmin, vmax, label, font_size, cmap_type=cmap_type)
            except Exception as e:
                print(f"Erro ao adicionar legenda em {path}: {e}")

    @staticmethod
    def add_bottom_bar(
        image_path: str,
        lon_min: float,
        lon_max: float,
        lat_min: float,
        lat_max: float,
        palette: List[str],
        vmin: float = 0,
        vmax: float = 1,
        font_size: int = 50,
        discrete_labels: Optional[List[str]] = None,
        cmap_type: str = "sequential",
        show_legend: bool = True,
        show_scale: bool = True,
    ) -> None:
        image = _ensure_rgb(PILImage.open(image_path))
        width = image.width

        colors = [_parse_color(c) for c in palette]
        n = len(colors)
        is_discrete = (n <= 2) or (cmap_type == "categorical")

        margin = 25
        gap = 45

        north_w = 100
        north_gap = 60
        north_zone = north_w + margin + north_gap

        row1_h = 60
        tfont = FrameProcessor._make_font(font_size - 22)
        if not show_legend:
            legend_content_h = 0
            entries = []
        elif n == 0:
            box_size = 28
            legend_content_h = 90
            entries = []
        elif is_discrete:
            box_size = 28
            row_h = 50
            entries = []
            for i in range(n):
                if discrete_labels and i < len(discrete_labels):
                    lbl = discrete_labels[i]
                    if not lbl:
                        continue
                elif n == 2 and vmin == 0 and vmax == 1:
                    lbl = ["Não queimado", "Queimado"][i]
                else:
                    val = vmin + (vmax - vmin) * i / (n - 1) if n > 1 else vmin
                    lbl = str(int(val))
                lbl = FrameProcessor._truncate_label(lbl)
                entries.append((colors[i], lbl))
            n_entries = len(entries)

            tfont = FrameProcessor._make_font(font_size - 22)
            cols, rows, tfont, tfs = FrameProcessor._layout_discrete(
                width, entries, tfont, box_size, 8, margin, max_cols=3)
            legend_content_h = rows * row_h
        else:
            box_size = 50
            legend_content_h = box_size + 50
        row2_h = legend_content_h + 10

        s1 = margin + row1_h + margin if show_scale else 0
        s2 = gap + row2_h + margin if show_legend else 0
        section_h = s1 + s2

        padded = PILImage.new("RGB", (width, image.height + section_h), (255, 255, 255))
        padded.paste(image, (0, 0))
        draw = ImageDraw.Draw(padded)

        sep_y = image.height
        if show_scale:
            draw.line([(0, sep_y), (width, sep_y)], fill=(200, 200, 200), width=1)

        sfont = FrameProcessor._make_font(font_size - 12)

        y = sep_y + margin

        if show_scale:
            center_lat = (lat_min + lat_max) / 2
            km_per_deg = 111.32 * math.cos(math.radians(center_lat))
            map_km = (lon_max - lon_min) * km_per_deg
            km_per_px = map_km / width

            scale_max_w = width - margin - north_zone
            nice = [1, 2, 5, 10, 15, 20, 25, 50, 100, 150, 200, 500]
            target_km = km_per_px * scale_max_w
            scale_km = min(nice, key=lambda x: abs(x - target_km))
            bar_px = int(scale_km / km_per_px) if km_per_px > 0 else scale_max_w
            bar_px = min(bar_px, scale_max_w)

            sbx = margin
            sby = y + 5
            bar_cy = sby + 20

            lbl0 = "0"
            lbl1 = f"{int(scale_km)} km"
            b0 = draw.textbbox((0, 0), lbl0, font=sfont)
            b1 = draw.textbbox((0, 0), lbl1, font=sfont)
            b0w = b0[2] - b0[0]
            b1w = b1[2] - b1[0]

            draw.line([(sbx, bar_cy), (sbx + bar_px, bar_cy)], fill=(60, 60, 60), width=3)
            draw.line([(sbx, bar_cy - 5), (sbx, bar_cy + 5)], fill=(60, 60, 60), width=3)
            draw.line([(sbx + bar_px, bar_cy - 5), (sbx + bar_px, bar_cy + 5)], fill=(60, 60, 60), width=3)

            draw.text((sbx - b0w // 2, bar_cy + 8), lbl0, font=sfont, fill=(60, 60, 60))
            draw.text((sbx + bar_px - b1w // 2, bar_cy + 8), lbl1, font=sfont, fill=(60, 60, 60))

            right_cx = width - margin - north_w // 2
            nac = bar_cy - 8
            arrow_size = 14
            draw.polygon([(right_cx, nac - arrow_size), (right_cx - 7, nac - 2), (right_cx + 7, nac - 2)], fill=(80, 80, 80))
            draw.line([(right_cx, nac - 2), (right_cx, nac + 4)], fill=(80, 80, 80), width=2)
            draw.line([(right_cx - 6, nac + 4), (right_cx + 6, nac + 4)], fill=(80, 80, 80), width=2)
            nlabel = "N"
            nb = draw.textbbox((0, 0), nlabel, font=tfont)
            nw = nb[2] - nb[0]
            nh = nb[3] - nb[1]
            draw.text((right_cx - nw // 2, bar_cy + 8), nlabel, font=tfont, fill=(80, 80, 80))

        ly = y + (row1_h + gap if show_scale else 0)

        if show_legend:
            if n == 0:
                bx = margin
                by = ly + 5
                draw.rectangle([bx, by, bx + box_size, by + box_size], fill=(128, 128, 128))
                draw.rectangle([bx, by, bx + box_size, by + box_size], outline=(100, 100, 100), width=2)
                draw.text((bx + box_size + 10, by), "Sem vegetação", font=tfont, fill=(0, 0, 0))
                draw.text((margin, by + box_size + 10), "Cada mancha de vegetação possui uma cor única", font=tfont, fill=(100, 100, 100))
            elif is_discrete:
                col_w = (width - 2 * margin) // cols
                for idx, (color, lbl) in enumerate(entries):
                    col = idx % cols
                    row = idx // cols
                    bx = margin + col * col_w
                    by = ly + row * row_h
                    draw.rectangle([bx, by, bx + box_size, by + box_size], fill=color)
                    draw.rectangle([bx, by, bx + box_size, by + box_size], outline=(100, 100, 100), width=2)
                    draw.text((bx + box_size + 8, by + 2), lbl, font=tfont, fill=(0, 0, 0))
            else:
                bar_x = margin
                bar_w = width - 2 * margin
                bar_y_pos = ly
                for i in range(n - 1):
                    x0 = int(bar_x + i * bar_w / (n - 1))
                    x1 = int(bar_x + (i + 1) * bar_w / (n - 1))
                    draw.rectangle([x0, bar_y_pos, x1, bar_y_pos + box_size], fill=colors[i])
                draw.rectangle([int(bar_x + (n - 1) * bar_w / (n - 1)), bar_y_pos, int(bar_x + bar_w), bar_y_pos + box_size], fill=colors[-1])

                num_ticks = min(n, 6)
                for i in range(num_ticks):
                    val = vmin + (vmax - vmin) * i / (num_ticks - 1) if num_ticks > 1 else vmin
                    xi = int(bar_x + i * bar_w / (num_ticks - 1))
                    lbl = str(int(val))
                    bbox = draw.textbbox((0, 0), lbl, font=tfont)
                    lw = bbox[2] - bbox[0]
                    if i == 0:
                        tx = margin
                    elif i == num_ticks - 1:
                        tx = width - margin - lw
                    else:
                        tx = xi - lw // 2
                    draw.text((tx, bar_y_pos + box_size + 5), lbl, font=tfont, fill=(0, 0, 0))
                    draw.line([(xi, bar_y_pos + box_size), (xi, bar_y_pos + box_size + 5)], fill=(0, 0, 0))

        image.close()
        padded.save(image_path)

    @staticmethod
    def batch_add_bottom_bars(
        image_paths: List[str],
        lon_min: float,
        lon_max: float,
        lat_min: float,
        lat_max: float,
        palette: List[str],
        vmin: float = 0,
        vmax: float = 1,
        font_size: int = 50,
        discrete_labels: Optional[List[str]] = None,
        cmap_type: str = "sequential",
        show_legend: bool = True,
        show_scale: bool = True,
    ) -> None:
        for path in image_paths:
            try:
                FrameProcessor.add_bottom_bar(path, lon_min, lon_max, lat_min, lat_max, palette, vmin, vmax, font_size, discrete_labels=discrete_labels, cmap_type=cmap_type, show_legend=show_legend, show_scale=show_scale)
            except Exception as e:
                print(f"Erro ao adicionar barra inferior em {path}: {e}")

    @staticmethod
    def add_scale_bar(
        image_path: str,
        lon_min: float,
        lon_max: float,
        lat_min: float,
        lat_max: float,
        bar_width_px: int = 350,
        font_size: int = 40,
    ) -> None:
        image = _ensure_rgb(PILImage.open(image_path))
        width = image.width
        center_lat = (lat_min + lat_max) / 2
        km_per_deg = 111.32 * _math.cos(_math.radians(center_lat))
        map_km = (lon_max - lon_min) * km_per_deg
        km_per_px = map_km / width
        target_km = km_per_px * bar_width_px
        nice = [1, 2, 5, 10, 15, 20, 25, 50, 100, 150, 200, 500]
        scale_km = min(nice, key=lambda x: abs(x - target_km))
        bar_px = int(scale_km / km_per_px) if km_per_px > 0 else bar_width_px

        bar_h = 120
        padded = PILImage.new("RGB", (width, image.height + bar_h), (255, 255, 255))
        padded.paste(image, (0, 0))
        draw = ImageDraw.Draw(padded)

        try:
            font = ImageFont.truetype(FrameProcessor.FONT_PATH, font_size) if FrameProcessor.FONT_PATH else ImageFont.load_default()
            sfont = ImageFont.truetype(FrameProcessor.FONT_PATH, font_size - 8) if FrameProcessor.FONT_PATH else ImageFont.load_default()
        except (IOError, OSError):
            font = sfont = ImageFont.load_default()

        bx = width - bar_px - 120
        by = image.height + 56

        draw.line([(bx, by), (bx + bar_px, by)], fill=(60, 60, 60), width=3)
        draw.line([(bx, by - 6), (bx, by + 6)], fill=(60, 60, 60), width=3)
        draw.line([(bx + bar_px, by - 6), (bx + bar_px, by + 6)], fill=(60, 60, 60), width=3)

        lbl0 = "0"
        lbl1 = f"{int(scale_km)} km"
        b0 = draw.textbbox((0, 0), lbl0, font=font)
        draw.text((bx - (b0[2] - b0[0]) // 2, by + 12), lbl0, font=font, fill=(60, 60, 60))
        b1 = draw.textbbox((0, 0), lbl1, font=font)
        draw.text((bx + bar_px - (b1[2] - b1[0]) // 2, by + 12), lbl1, font=font, fill=(60, 60, 60))

        ncx = width - 45
        ncy = by
        arrow_size = 14
        draw.polygon([(ncx, ncy - arrow_size), (ncx - 7, ncy), (ncx + 7, ncy)], fill=(80, 80, 80))
        nlabel = "N"
        nb = draw.textbbox((0, 0), nlabel, font=sfont)
        nw = nb[2] - nb[0]
        nh = nb[3] - nb[1]
        draw.text((ncx - nw // 2, ncy - arrow_size - nh - 4), nlabel, font=sfont, fill=(80, 80, 80))

        image.close()
        padded.save(image_path)

    @staticmethod
    def batch_add_scale_bars(
        image_paths: List[str],
        lon_min: float,
        lon_max: float,
        lat_min: float,
        lat_max: float,
    ) -> None:
        for path in image_paths:
            try:
                FrameProcessor.add_scale_bar(path, lon_min, lon_max, lat_min, lat_max)
            except Exception as e:
                print(f"Erro ao adicionar escala em {path}: {e}")

    @staticmethod
    def add_margin(image_path: str, margin_px: int = 30) -> None:
        image = _ensure_rgb(PILImage.open(image_path))
        padded = PILImage.new("RGB", (image.width + margin_px * 2, image.height + margin_px * 2), (255, 255, 255))
        padded.paste(image, (margin_px, margin_px))
        image.close()
        padded.save(image_path)

    @staticmethod
    def batch_add_margins(image_paths: List[str], margin_px: int = 30) -> None:
        for path in image_paths:
            try:
                FrameProcessor.add_margin(path, margin_px)
            except Exception as e:
                print(f"Erro ao adicionar margem em {path}: {e}")

    @staticmethod
    def resize_image(image_path: str, target_height: int) -> str:
        image = PILImage.open(image_path)
        aspect = image.width / image.height
        new_w = int(target_height * aspect)
        resized = image.resize((new_w, target_height), PILImage.Resampling.LANCZOS)
        resized.save(image_path)
        return image_path

    @staticmethod
    def batch_resize(image_paths: List[str], target_height: int) -> List[str]:
        result = []
        for path in image_paths:
            try:
                result.append(FrameProcessor.resize_image(path, target_height))
            except Exception as e:
                print(f"Erro ao redimensionar {path}: {e}")
        return result
