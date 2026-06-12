import os
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image as PILImage, ImageDraw, ImageFont


def _parse_hex(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i: i + 2], 16) for i in (0, 2, 4))


class Composer:
    """Compose map frames + chart PNGs into composed frames + GIF.

    Layout:
      ┌─────────────────────────────────────┐
      │ TITLE BAR (product — territory)     │
      ├──────────────────────┬──────────────┤
      │                      │              │
      │  MAP (frame_clean)   │  DONUT       │
      │  ~65% width          │  ~35% width  │
      │                      │              │
      ├──────────────────────┴──────────────┤
      │  TIMESERIES (full width)            │
      ├─────────────────────────────────────┤
      │ LEGEND BAR (class colors + labels)  │
      └─────────────────────────────────────┘
    """

    def __init__(self, font_scale: float = 1.0):
        self.font_scale = font_scale

    @staticmethod
    def _make_font(size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except (IOError, OSError):
            try:
                return ImageFont.truetype("DejaVuSans.ttf", size)
            except (IOError, OSError):
                return ImageFont.load_default()

    def compose(
        self,
        output_dir: str,
        layout: str = "map-donut-timeseries",
        product_name: str = "",
        territory_name: str = "",
        viz_params: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Compose maps + charts for a (product, territory) container.

        Uses frame_clean as map base, pure charts_annual + charts_timeseries
        (without PIL title/legend overlay).
        Adds title bar + legend once via composer.
        Saves individual frames in composed/ and a composed GIF.

        Returns list of output paths.
        """
        frames_clean_dir = os.path.join(output_dir, "frames_clean")
        charts_annual_dir = os.path.join(output_dir, "charts_annual")
        charts_timeseries_dir = os.path.join(output_dir, "charts_timeseries")
        charts_composed_dir = os.path.join(output_dir, "charts_composed")
        charts_gifs_dir = os.path.join(output_dir, "charts_gifs")
        os.makedirs(charts_composed_dir, exist_ok=True)
        os.makedirs(charts_gifs_dir, exist_ok=True)

        # Load frames
        map_frames = self._load_sorted_pngs(frames_clean_dir)
        if not map_frames:
            print(f"  [SKIP] No frames in {frames_clean_dir}")
            return []

        annual_frames = self._load_sorted_pngs(charts_annual_dir)
        ts_frames = self._load_sorted_pngs(charts_timeseries_dir)

        n = len(map_frames)
        annual_frames = self._match_frames(annual_frames, n)
        ts_frames = self._match_frames(ts_frames, n)

        # Build legend entries from viz_params
        legend_entries = self._build_legend_entries(viz_params)

        # Compose each frame
        composed_paths = []
        composed_frames = []
        for i in range(n):
            map_img = map_frames[i]
            donut_img = annual_frames[i]
            ts_img = ts_frames[i]

            canvas = self._layout_map_donut_ts(
                map_img, donut_img, ts_img,
                product_name or "", territory_name or "",
                legend_entries,
            )
            composed_frames.append(canvas)

            frame_path = os.path.join(charts_composed_dir, f"{i:04d}.png")
            canvas.save(frame_path)
            composed_paths.append(frame_path)

        # Save GIF
        out_gif = os.path.join(charts_composed_dir, "composed.gif")
        duration = 300
        composed_frames[0].save(
            out_gif,
            save_all=True,
            append_images=composed_frames[1:],
            duration=duration,
            loop=0,
            optimize=False,
        )
        composed_paths.append(out_gif)

        # Copy to charts_gifs
        gif_copy = os.path.join(charts_gifs_dir, "composed.gif")
        composed_frames[0].save(
            gif_copy,
            save_all=True,
            append_images=composed_frames[1:],
            duration=duration,
            loop=0,
            optimize=False,
        )

        print(f"  [Composed] {out_gif}  ({n} frames)")
        return composed_paths

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_sorted_pngs(directory: str) -> List[PILImage.Image]:
        """Load PNGs from dir, sorted by filename."""
        if not os.path.isdir(directory):
            return []
        result = []
        for fname in sorted(os.listdir(directory)):
            if fname.endswith(".png"):
                img = PILImage.open(os.path.join(directory, fname)).convert("RGBA")
                result.append(img)
        return result

    @staticmethod
    def _match_frames(
        frames: List[PILImage.Image], target: int
    ) -> List[Optional[PILImage.Image]]:
        if not frames:
            return [None] * target
        if len(frames) >= target:
            return frames[:target]
        last = frames[-1]
        return frames + [last] * (target - len(frames))

    def _build_legend_entries(
        self, viz_params: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Tuple[int, int, int], str]]:
        """Build [(color_rgb, label), ...] from viz_params."""
        entries = []
        if not viz_params:
            return entries
        classes = viz_params.get("classes", [])
        if classes:
            for c in classes:
                val = c.get("value")
                label = c.get("label", str(val))
                color_hex = c.get("color", "")
                if color_hex:
                    entries.append((_parse_hex(f"#{color_hex}"), label))
        else:
            palette = viz_params.get("palette", [])
            discrete_labels = viz_params.get("discrete_labels", [])
            for i, p in enumerate(palette):
                label = discrete_labels[i] if i < len(discrete_labels) and discrete_labels[i] else str(i)
                entries.append((_parse_hex(f"#{p}"), label))
        return entries

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _layout_map_donut_ts(
        self,
        map_img: PILImage.Image,
        donut_img: Optional[PILImage.Image],
        ts_img: Optional[PILImage.Image],
        product_name: str,
        territory_name: str,
        legend_entries: List[Tuple[Tuple[int, int, int], str]],
    ) -> PILImage.Image:
        """Build a single composed frame. Charts pasted at natural size (no resize)."""
        mw, mh = map_img.size

        margin = 6
        gap_ts = 64
        title_h = int(52 * self.font_scale)
        leg_font_sz = int(35 * self.font_scale)
        legend_h = int(leg_font_sz * 2)

        # Donut panel: use donut_img natural width (no cap)
        donut_w = donut_img.width if donut_img else 0
        donut_panel_w = max(donut_w, 0)

        # Timeseries: use natural height, or default
        ts_h = ts_img.height if ts_img else max(180, int(mw * 0.22))
        ts_w = ts_img.width if ts_img else (mw + donut_panel_w + margin)

        map_w = mw
        canvas_w = map_w + donut_panel_w + margin
        if ts_w > canvas_w:
            canvas_w = ts_w

        canvas_h = title_h + mh + ts_h + legend_h + gap_ts

        canvas = PILImage.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        # --- Title bar ---
        self._draw_title(draw, canvas_w, title_h, product_name, territory_name)

        # --- Map (left) ---
        canvas.paste(map_img, (0, title_h), map_img)

        # --- Donut (right, lower than center) ---
        if donut_img:
            dx = map_w + margin
            donut_offset = int(mh * 0.12)
            dy = title_h + (mh - donut_img.height) // 2 + donut_offset
            canvas.paste(donut_img, (dx, max(title_h, dy)), donut_img)

        # --- Timeseries (bottom, full width, centered horizontally) ---
        ts_y = title_h + mh + gap_ts
        if ts_img:
            tx = (canvas_w - ts_img.width) // 2
            canvas.paste(ts_img, (max(0, tx), ts_y), ts_img)

        # --- Legend bar ---
        leg_y = ts_y + ts_h
        self._draw_legend(draw, canvas_w, leg_y, legend_h, legend_entries)

        # --- Separator lines ---
        sep_color = (180, 180, 180)
        draw.line([(0, title_h), (canvas_w, title_h)], fill=sep_color, width=1)
        if donut_panel_w > 0:
            draw.line([(map_w + margin, title_h), (map_w + margin, ts_y)], fill=sep_color, width=1)
        draw.line([(0, ts_y), (canvas_w, ts_y)], fill=sep_color, width=1)

        return canvas

    def _draw_title(
        self, draw: ImageDraw.Draw,
        w: int, h: int, product_name: str, territory_name: str,
    ):
        """Fill title bar with centered text."""
        draw.rectangle([(0, 0), (w, h)], fill=(245, 245, 245))
        title_font = self._make_font(int(24 * self.font_scale))
        text = f"{product_name} — {territory_name}" if product_name else territory_name
        tw = draw.textbbox((0, 0), text, font=title_font)
        draw.text(((w - tw[2]) // 2, (h - (tw[3] - tw[1])) // 2),
                  text, font=title_font, fill=(51, 51, 51))

    def _draw_legend(
        self, draw: ImageDraw.Draw,
        w: int, y: int, h: int,
        entries: List[Tuple[Tuple[int, int, int], str]],
    ):
        """Draw legend boxes + labels centered in the bar.

        Font size scales with self.font_scale to visually match the
        map scale bar text (which is ~69pt on the compose canvas at M3.0).
        """
        draw.rectangle([(0, y), (w, y + h)], fill=(248, 248, 248))
        draw.line([(0, y), (w, y)], fill=(200, 200, 200), width=1)

        if not entries:
            return

        margin = 12
        font_sz = int(35 * self.font_scale)
        leg_font = self._make_font(font_sz)
        box_size = max(16, int(font_sz * 0.55))
        row_h = box_size + 10

        max_cols = max(1, (w - 2 * margin) // (box_size + 100))
        n_cols = min(max_cols, len(entries))
        n_rows = (len(entries) + n_cols - 1) // n_cols
        col_w = (w - 2 * margin) // n_cols

        for idx, (color, label) in enumerate(entries):
            col = idx // n_rows if n_cols > 1 else 0
            row = idx % n_rows if n_cols > 1 else idx
            bx = margin + col * col_w
            by = y + (h - n_rows * row_h) // 2 + row * row_h
            draw.rectangle([bx, by, bx + box_size, by + box_size], fill=color)
            draw.rectangle([bx, by, bx + box_size, by + box_size],
                           outline=(100, 100, 100), width=1)
            lbl_bbox = draw.textbbox((0, 0), label, font=leg_font)
            lbl_h = lbl_bbox[3] - lbl_bbox[1]
            draw.text((bx + box_size + 8, by + (box_size - lbl_h) // 2),
                      label, font=leg_font, fill=(51, 51, 51))
