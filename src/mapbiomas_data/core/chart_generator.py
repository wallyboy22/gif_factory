import csv
import os
from typing import Any, Dict, List, Optional, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from PIL import Image as PILImage, ImageDraw, ImageFont

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.family": "sans-serif",
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#333333",
    "text.color": "#333333",
    "xtick.color": "#555555",
    "ytick.color": "#555555",
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def _parse_hex(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i: i + 2], 16) for i in (0, 2, 4))


class ChartGenerator:
    """Generate chart PNGs from area stats CSVs.

    Produces two chart types per (product, territory):
      - Annual: donut chart (class distribution or binary gauge)
      - Timeseries: stacked area chart with current year highlight
    """

    def __init__(self, class_labels: Dict[int, str] = None,
                 class_colors: Dict[int, str] = None,
                 viz_params: Dict[str, Any] = None,
                 product_name: str = "",
                 territory_name: str = "",
                 font_scale: float = 1.0,
                 timeseries_font_scale: Optional[float] = None,
                 donut_figsize: Optional[Tuple[float, float]] = None,
                 donut_binary_figsize: Optional[Tuple[float, float]] = None,
                 timeseries_figsize: Optional[Tuple[float, float]] = None):
        self.class_labels = class_labels or {}
        self.class_colors = class_colors or {}
        self.viz_params = viz_params or {}
        self.product_name = product_name
        self.territory_name = territory_name
        self.font_scale = font_scale
        self.timeseries_font_scale = timeseries_font_scale if timeseries_font_scale is not None else font_scale
        self.donut_figsize = donut_figsize or (6, 6)
        self.donut_binary_figsize = donut_binary_figsize or (5, 5)
        self.timeseries_figsize = timeseries_figsize or (8, 3)

    @staticmethod
    def _make_font(size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except (IOError, OSError):
            try:
                return ImageFont.truetype("DejaVuSans.ttf", size)
            except (IOError, OSError):
                return ImageFont.load_default()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_area_data(self, area_stats_dir: str,
                       keep_class_zero: bool = False) -> Dict[str, List[Dict]]:
        """Load area stats from unified or per-year CSVs.

        Returns {year: [{class_value, area_ha, label}, ...]}.
        By default filters out class 0; set keep_class_zero=True to keep it.
        """
        data = {}
        if not os.path.isdir(area_stats_dir):
            return data

        unified = [f for f in os.listdir(area_stats_dir)
                   if f.endswith("_area_stats.csv")]
        if unified:
            fpath = os.path.join(area_stats_dir, sorted(unified)[-1])
            with open(fpath, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cls_val = int(row.get("class_value", row.get("class", 0)))
                    if not keep_class_zero and cls_val == 0:
                        continue
                    year = row.get("year", "static")
                    if year not in data:
                        data[year] = []
                    data[year].append({
                        "class": cls_val,
                        "area_ha": float(row.get("area_ha", 0)),
                        "label": row.get("class_name",
                                        self.class_labels.get(cls_val, str(cls_val))),
                    })
            return data

        for fname in sorted(os.listdir(area_stats_dir)):
            if not fname.endswith(".csv") or fname == "_tasks.json":
                continue
            year = fname.replace(".csv", "")
            fpath = os.path.join(area_stats_dir, fname)
            records = []
            with open(fpath, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cls_val = int(row.get("class_value", row.get("class", 0)))
                    if not keep_class_zero and cls_val == 0:
                        continue
                    records.append({
                        "class": cls_val,
                        "area_ha": float(row.get("area_ha", 0)),
                        "label": row.get("class_name",
                                        self.class_labels.get(cls_val, str(cls_val))),
                    })
            if records:
                data[year] = records
        return data

    # ------------------------------------------------------------------
    # Main generation
    # ------------------------------------------------------------------

    def generate(
        self,
        area_stats_dir: str,
        charts_annual_dir: str,
        charts_timeseries_dir: str,
        product_id: str = "",
        territory_id: str = "",
        n_colors: int = 12,
    ) -> Tuple[List[str], List[str]]:
        """Generate chart PNGs + clean versions + GIFs.

        Returns (annual_paths, timeseries_paths).
        Also populates clean dirs and gifs_charts dir.
        """
        os.makedirs(charts_annual_dir, exist_ok=True)
        os.makedirs(charts_timeseries_dir, exist_ok=True)

        cmap_type = self.viz_params.get("cmap_type", "categorical")
        is_binary = cmap_type in ("binary",)

        keep_zero = is_binary
        data = self.load_area_data(area_stats_dir, keep_class_zero=keep_zero)
        if not data:
            return [], []

        years = sorted(data.keys())
        annual_paths = []
        timeseries_paths = []

        all_classes = set()
        for recs in data.values():
            for r in recs:
                all_classes.add(r["class"])
        all_classes = sorted(all_classes)

        if not self.class_colors:
            self.class_colors = self._pick_colors(all_classes, n_colors)

        # --- Annual donut charts ---
        for year in years:
            records = data[year]
            path = os.path.join(charts_annual_dir, f"{year}.png")
            self._plot_annual_donut(
                records, all_classes, self.class_colors,
                year, path, product_id, territory_id, is_binary,
            )
            annual_paths.append(path)

        # --- Timeseries charts (fixed full range, highlight current) ---
        self._generate_timeseries_frames(
            data, all_classes, self.class_colors,
            years, charts_timeseries_dir, product_id, territory_id,
            timeseries_paths,
        )

        # --- Clean versions ---
        output_root = os.path.dirname(area_stats_dir)
        clean_annual_dir = os.path.join(output_root, "charts_annual_clean")
        clean_timeseries_dir = os.path.join(output_root, "charts_timeseries_clean")
        self._generate_clean_charts(
            annual_paths, clean_annual_dir, years,
            product_id, territory_id, is_binary,
        )
        self._generate_clean_charts(
            timeseries_paths, clean_timeseries_dir, years,
            product_id, territory_id, is_binary,
        )

        # --- Chart GIFs ---
        charts_gifs_dir = os.path.join(output_root, "charts_gifs")
        self._generate_chart_gifs(
            clean_annual_dir, clean_timeseries_dir,
            charts_gifs_dir, years,
        )

        return annual_paths, timeseries_paths

    # ------------------------------------------------------------------
    # Color helpers
    # ------------------------------------------------------------------

    def _pick_colors(self, classes: List[int], n: int) -> Dict[int, str]:
        """Fallback: assign consistent tab20 colors to classes."""
        cmap = plt.cm.tab20
        colors = {}
        for i, cls_val in enumerate(classes):
            rgb = cmap(i % n)
            colors[cls_val] = f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
        return colors

    # ------------------------------------------------------------------
    # Annual donut chart
    # ------------------------------------------------------------------

    def _plot_annual_donut(
        self, records: List[Dict], all_classes: List[int],
        class_colors: Dict[int, str], year: str, path: str,
        product_id: str = "", territory_id: str = "",
        is_binary: bool = False,
    ):
        figsize = self.donut_figsize if not is_binary else self.donut_binary_figsize
        fig, ax = plt.subplots(figsize=figsize)

        if is_binary:
            self._plot_binary_gauge(records, class_colors, ax)
        else:
            self._plot_multiclass_donut(records, all_classes, class_colors, ax)

        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    def _plot_binary_gauge(self, records: List[Dict],
                           class_colors: Dict[int, str], ax):
        """Two-slice donut: burned + unburned."""
        fs = lambda n: int(n * self.font_scale)
        burned_area = 0
        unburned_area = 0
        for r in records:
            if r["class"] == 1:
                burned_area = r["area_ha"]
            elif r["class"] == 0:
                unburned_area = r["area_ha"]

        if burned_area == 0 and unburned_area == 0:
            ax.text(0.5, 0.5, "Sem dados", ha="center", va="center",
                    fontsize=fs(10), color="#999")
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)
            return

        burned_color = class_colors.get(1, "#800000")
        unburned_color = class_colors.get(0, "#e0e0e0")

        if unburned_area > 0:
            wedges, texts = ax.pie(
                [unburned_area, burned_area],
                colors=[unburned_color, burned_color],
                startangle=90,
                counterclock=False,
                wedgeprops=dict(width=0.35, edgecolor="white", linewidth=2),
            )
        else:
            wedges, texts = ax.pie(
                [1.0],
                colors=[burned_color],
                startangle=90,
                counterclock=False,
                wedgeprops=dict(width=0.35, edgecolor="white", linewidth=2),
            )

        ax.text(0, 0, f"{burned_area:,.0f} ha", ha="center", va="center",
                fontsize=fs(13), fontweight="bold", color="#333")

    def _plot_multiclass_donut(self, records: List[Dict],
                                all_classes: List[int],
                                class_colors: Dict[int, str],
                                ax):
        """Multi-slice donut showing class distribution."""
        fs = lambda n: int(n * self.font_scale)
        class_areas = {c: 0 for c in all_classes}
        for r in records:
            class_areas[r["class"]] = r["area_ha"]

        slices = [(c, class_areas[c]) for c in all_classes if class_areas[c] > 0]
        if not slices:
            ax.text(0.5, 0.5, "Sem dados", ha="center", va="center",
                    fontsize=fs(10), color="#999")
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)
            return

        classes, areas = zip(*slices)
        colors = [class_colors.get(c, "#cccccc") for c in classes]
        total = sum(areas)

        wedges, texts = ax.pie(
            areas, colors=colors,
            startangle=90,
            wedgeprops=dict(width=0.35, edgecolor="white", linewidth=1),
        )

        ax.text(0, 0, f"{total:,.0f}\nha", ha="center", va="center",
                fontsize=fs(10), fontweight="bold", color="#333")

    # ------------------------------------------------------------------
    # Timeseries: fixed stacked area with current-year highlight
    # ------------------------------------------------------------------

    def _generate_timeseries_frames(
        self, data: Dict[str, List[Dict]],
        all_classes: List[int], class_colors: Dict[int, str],
        all_years: List[str], output_dir: str,
        product_id: str, territory_id: str,
        paths_out: List[str],
    ):
        """One PNG per year — same full-range chart, current year highlighted."""
        # Build plot_data: {class_val: [area_ha for each year]}
        plot_data = {}
        for cls_val in all_classes:
            vals = []
            for yr in all_years:
                recs = data.get(yr, [])
                match = next((r for r in recs if r["class"] == cls_val), None)
                vals.append(match["area_ha"] if match else 0)
            plot_data[cls_val] = vals

        for i, current_year in enumerate(all_years):
            path = os.path.join(output_dir, f"{current_year}.png")
            self._plot_timeseries_single(
                plot_data, all_classes, class_colors,
                all_years, i, path, product_id, territory_id,
            )
            paths_out.append(path)

    def _plot_timeseries_single(
        self, plot_data: Dict[int, List[float]],
        all_classes: List[int], class_colors: Dict[int, str],
        all_years: List[str], current_idx: int, path: str,
        product_id: str = "", territory_id: str = "",
    ):
        fs_l = lambda n: int(n * self.timeseries_font_scale)
        fig, ax = plt.subplots(figsize=self.timeseries_figsize)

        x = list(range(len(all_years)))
        x_labels = [str(y) for y in all_years]

        y_layers = []
        layer_colors = []
        for cls_val in reversed(all_classes):
            vals = plot_data.get(cls_val, [0] * len(all_years))
            if sum(vals) == 0:
                continue
            y_layers.append(vals)
            layer_colors.append(class_colors.get(cls_val, "#cccccc"))

        if y_layers:
            ax.stackplot(x, y_layers, colors=layer_colors, alpha=0.75)

        ax.axvline(x=current_idx, color="#e74c3c", linewidth=2,
                   linestyle="--", alpha=0.7, zorder=5)
        ax.axvspan(current_idx - 0.35, current_idx + 0.35,
                   alpha=0.08, color="#e74c3c", zorder=4)

        # Value label for current year at fixed position (top of chart)
        current_vals = [layer[current_idx] for layer in y_layers] if y_layers else [0]
        total_at_current = sum(current_vals)
        if total_at_current > 0:
            ax.text(current_idx, 0.92, f"{total_at_current:,.0f} ha",
                    ha="center", va="top", fontsize=fs_l(7),
                    color="#333", fontweight="bold",
                    transform=ax.get_xaxis_transform(),
                    bbox=dict(boxstyle="round,pad=0.2",
                              facecolor="white", edgecolor="none", alpha=0.7))

        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, rotation=45, fontsize=fs_l(6))
        n_ticks = min(len(x_labels), 15)
        step = max(1, len(x_labels) // n_ticks)
        visible = set(range(0, len(x_labels), step))
        visible.add(current_idx)
        tick_labels = ax.get_xticklabels()
        for idx in range(len(x_labels)):
            if idx < len(tick_labels):
                tick_labels[idx].set_visible(idx in visible)
                if idx == current_idx:
                    tick_labels[idx].set_ha("right")

        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
        ax.tick_params(axis="y", labelsize=fs_l(6))
        ax.set_ylabel("ha", fontsize=fs_l(8), labelpad=2)
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    # ------------------------------------------------------------------
    # Clean chart versions (PIL title bar + legend overlay)
    # ------------------------------------------------------------------

    def _generate_clean_charts(
        self, chart_paths: List[str], clean_dir: str,
        years: List[str], product_id: str, territory_id: str,
        is_binary: bool = False,
    ):
        """For each chart PNG, add PIL title bar + legend -> clean dir."""
        if not chart_paths:
            return
        os.makedirs(clean_dir, exist_ok=True)

        # Build legend entries from class_colors + class_labels
        entries = []
        for cls_val in sorted(self.class_colors.keys()):
            if is_binary and cls_val == 0:
                label = "Não queimado"
            else:
                label = self.class_labels.get(cls_val, str(cls_val))
            color_hex = self.class_colors.get(cls_val, "#cccccc").lstrip("#")
            entries.append((_parse_hex(f"#{color_hex}"), label))

        for src_path, year in zip(chart_paths, years):
            fname = os.path.basename(src_path)
            dst_path = os.path.join(clean_dir, fname)
            self._add_chart_overlay(
                src_path, dst_path, year,
                product_id, territory_id, entries,
            )

    def _add_chart_overlay(
        self, src_path: str, dst_path: str,
        year: str, product_id: str, territory_id: str,
        legend_entries: List[Tuple[Tuple[int, int, int], str]],
    ):
        """Add title bar at top and legend at bottom to a chart PNG."""
        fs = lambda n: int(n * self.font_scale)
        chart = PILImage.open(src_path).convert("RGBA")
        cw, ch = chart.size

        title_h = 46
        margin = 10
        box_size = fs(16)
        row_h = fs(26)
        n_cols = min(3, max(1, len(legend_entries)))
        n_rows = (len(legend_entries) + n_cols - 1) // n_cols
        legend_h = n_rows * row_h + margin * 2

        canvas_h = title_h + ch + legend_h
        canvas = PILImage.new("RGBA", (cw, canvas_h), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        # --- Title bar ---
        title_font = self._make_font(fs(20))
        title_text = f"{year} — {product_id} — {territory_id}"
        draw.rectangle([(0, 0), (cw, title_h)], fill=(245, 245, 245))
        draw.line([(0, title_h), (cw, title_h)], fill=(200, 200, 200), width=1)
        tw = draw.textbbox((0, 0), title_text, font=title_font)
        draw.text(((cw - tw[2]) // 2, (title_h - (tw[3] - tw[1])) // 2),
                  title_text, font=title_font, fill=(51, 51, 51))

        # --- Chart ---
        canvas.paste(chart, (0, title_h), chart)

        # --- Legend ---
        leg_y = title_h + ch + margin
        col_w = (cw - 2 * margin) // n_cols
        leg_font = self._make_font(fs(12))

        for idx, (color, label) in enumerate(legend_entries):
            col = idx // n_rows if n_cols > 1 else 0
            row = idx % n_rows if n_cols > 1 else idx
            bx = margin + col * col_w
            by = leg_y + row * row_h
            draw.rectangle([bx, by, bx + box_size, by + box_size], fill=color)
            draw.rectangle([bx, by, bx + box_size, by + box_size],
                           outline=(100, 100, 100), width=1)
            lbl_bbox = draw.textbbox((0, 0), label, font=leg_font)
            lbl_h = lbl_bbox[3] - lbl_bbox[1]
            draw.text((bx + box_size + 6, by + (box_size - lbl_h) // 2),
                      label, font=leg_font, fill=(51, 51, 51))

        chart.close()
        canvas.save(dst_path)

    # ------------------------------------------------------------------
    # Chart GIFs
    # ------------------------------------------------------------------

    def _generate_chart_gifs(
        self, clean_annual_dir: str, clean_timeseries_dir: str,
        charts_gifs_dir: str, years: List[str],
    ):
        """Create animated GIFs from clean chart images."""
        os.makedirs(charts_gifs_dir, exist_ok=True)
        frame_duration = 300

        self._images_to_gif(
            clean_annual_dir, charts_gifs_dir,
            "annual.gif", frame_duration,
        )
        self._images_to_gif(
            clean_timeseries_dir, charts_gifs_dir,
            "timeseries.gif", frame_duration,
        )

    @staticmethod
    def _images_to_gif(
        src_dir: str, dst_dir: str,
        gif_name: str, duration: int = 300,
    ):
        if not os.path.isdir(src_dir):
            return
        pngs = sorted(
            [f for f in os.listdir(src_dir) if f.endswith(".png")]
        )
        if not pngs:
            return
        frames = []
        for fname in pngs:
            img = PILImage.open(os.path.join(src_dir, fname)).convert("P",
                palette=PILImage.ADAPTIVE, colors=256)
            frames.append(img)

        out_path = os.path.join(dst_dir, gif_name)
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            optimize=True,
        )
        print(f"  [GIF] {out_path}  ({len(frames)} frames)")

    # ------------------------------------------------------------------
    # Batch convenience
    # ------------------------------------------------------------------

    def generate_all_for_batch(
        self,
        config,
        dataset_id: str,
        product_id: str,
        territory_id: str,
        product_info: Dict[str, Any],
    ) -> Tuple[List[str], List[str]]:
        """Compute chart PNGs for a (dataset, product, territory).

        Returns (annual_paths, timeseries_paths).
        """
        from ..core.area_stats import AreaStatsCalculator
        calc = AreaStatsCalculator(config)

        self.product_name = product_info.get("name", product_id)

        viz_key = product_info.get("visualization", "")
        if viz_key:
            self.class_labels = calc.get_class_labels(viz_key)
            ref_viz = calc.get_viz_reference(viz_key)
            self.viz_params = {
                "cmap_type": ref_viz.get("cmap_type", "categorical"),
                "palette": ref_viz.get("palette", []),
                "label": ref_viz.get("label", ""),
            }
            classes_list = ref_viz.get("classes", [])
            self.class_colors = {}
            for c in classes_list:
                val = c.get("value")
                color = c.get("color", "")
                if val is not None and color:
                    self.class_colors[val] = f"#{color}"
            if not self.class_colors:
                for i, p in enumerate(self.viz_params.get("palette", [])):
                    self.class_colors[i] = f"#{p}"

        output_dir = calc._get_output_dir(dataset_id, product_id, territory_id)
        area_stats_dir = calc._get_area_stats_dir(output_dir)

        charts_annual_dir = os.path.join(output_dir, "charts_annual")
        charts_timeseries_dir = os.path.join(output_dir, "charts_timeseries")

        return self.generate(
            area_stats_dir, charts_annual_dir, charts_timeseries_dir,
            product_id, territory_id,
        )
