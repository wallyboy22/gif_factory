import math
import os
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image as PILImage, ImageDraw, ImageFont
from ..utils.file_utils import ensure_dir, clean_filename


class GIFGenerator:
    """Gerar GIFs animados a partir de frames de imagens."""

    def __init__(self, frame_duration: int = 300, loop_count: int = 0, quality: int = 95):
        self.frame_duration = frame_duration
        self.loop_count = loop_count
        self.quality = quality

    def create_gif(
        self,
        image_paths: List[str],
        output_dir: str,
        filename: str = "output.gif",
        sort_frames: bool = True,
    ) -> str:
        if not image_paths:
            raise ValueError("Nenhuma imagem fornecida para o GIF")

        if sort_frames:
            image_paths = sorted(image_paths)

        missing = [p for p in image_paths if not os.path.exists(p)]
        if missing:
            raise FileNotFoundError(
                f"{len(missing)}/{len(image_paths)} frames ausentes para o GIF: "
                f"{missing[0]}" + (f", ..." if len(missing) > 1 else "")
            )

        images = []
        for path in image_paths:
            img = PILImage.open(path)
            if img.mode == "RGBA":
                bg = PILImage.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)

        if not images:
            raise ValueError("Nenhuma imagem pôde ser carregada")

        common_size = self._get_common_size(images)
        resized = [img.resize(common_size, PILImage.Resampling.LANCZOS) for img in images]

        first = resized[0].convert("P", palette=PILImage.Palette.ADAPTIVE)
        resized_rgb = [first]
        for img in resized[1:]:
            resized_rgb.append(img.quantize(method=0, palette=first))

        ensure_dir(output_dir)
        output_path = os.path.join(output_dir, clean_filename(filename))
        if not output_path.endswith(".gif"):
            output_path += ".gif"

        resized_rgb[0].save(
            output_path,
            format="GIF",
            save_all=True,
            append_images=resized_rgb[1:],
            duration=self.frame_duration,
            loop=self.loop_count,
            optimize=True,
        )
        return output_path

    def _get_common_size(self, images: List[PILImage.Image]) -> tuple:
        sizes = [img.size for img in images]
        min_w = min(s[0] for s in sizes)
        min_h = min(s[1] for s in sizes)
        return (min_w, min_h)

    def create_collage(
        self,
        image_paths: List[str],
        output_dir: str,
        filename: str = "collage.png",
        grid_size: Optional[int] = None,
        cell_labels: Optional[List[str]] = None,
        font_path: Optional[str] = None,
        cell_height: int = 300,
    ) -> str:
        if not image_paths:
            raise ValueError("Nenhuma imagem fornecida para a colagem")

        missing = [p for p in image_paths if not os.path.exists(p)]
        if missing:
            raise FileNotFoundError(
                f"{len(missing)}/{len(image_paths)} frames ausentes para a colagem: "
                f"{missing[0]}" + (f", ..." if len(missing) > 1 else "")
            )

        images = []
        for p in image_paths:
            img = PILImage.open(p)
            if img.mode == "RGBA":
                bg = PILImage.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)
        if not images:
            raise ValueError("Nenhuma imagem pôde ser carregada")

        n = len(images)
        if grid_size is None:
            if n <= 3:
                n_cols = n
            else:
                n_cols = min(max(math.ceil(n / 5), 2), 10)
            n_rows = math.ceil(n / n_cols)
        else:
            n_cols = grid_size
            n_rows = math.ceil(n / n_cols)

        target_h = cell_height
        cell_pad = 75 if cell_labels else 0

        resized = []
        for img in images:
            aspect = img.width / img.height
            new_w = int(target_h * aspect)
            small = img.resize((new_w, target_h), PILImage.Resampling.LANCZOS)
            if cell_labels:
                padded = PILImage.new("RGB", (new_w, target_h + cell_pad), color="white")
                padded.paste(small, (0, cell_pad))
                resized.append(padded)
            else:
                resized.append(small)

        frame_w = max(img.width for img in resized)
        frame_h = max(img.height for img in resized)

        grid_w = n_cols * frame_w
        grid_h = n_rows * frame_h

        collage = PILImage.new("RGB", (grid_w, grid_h), color="white")

        for idx, img in enumerate(resized):
            row = idx // n_cols
            col = idx % n_cols
            x = col * frame_w
            y = row * frame_h
            collage.paste(img, (x, y))

        if cell_labels:
            draw = ImageDraw.Draw(collage)
            try:
                if font_path and os.path.exists(font_path):
                    label_font = ImageFont.truetype(font_path, 60)
                else:
                    label_font = ImageFont.load_default()
            except (IOError, OSError):
                label_font = ImageFont.load_default()

            for idx, label in enumerate(cell_labels):
                if idx >= len(images):
                    break
                row = idx // n_cols
                col = idx % n_cols
                cx = col * frame_w
                cy = row * frame_h
                draw.text((cx + 10, cy + 10), label, font=label_font, fill=(0, 0, 0))

        ensure_dir(output_dir)
        output_path = os.path.join(output_dir, clean_filename(filename))
        collage.save(output_path, quality=self.quality)
        return output_path
