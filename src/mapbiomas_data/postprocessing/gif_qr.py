import os
import tempfile
from typing import Optional

import qrcode
from PIL import Image as PILImage


class GIFQRCode:
    """Gera QR code para link de GIF, para embutir em PDF."""

    @staticmethod
    def make_qr(
        data: str,
        box_size: int = 10,
        border: int = 4,
        fill_color: str = "black",
        back_color: str = "white",
    ) -> PILImage.Image:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill_color=fill_color, back_color=back_color)

    @staticmethod
    def make_gif_qr_from_path(
        gif_path: str,
        label: Optional[str] = None,
    ) -> PILImage.Image:
        abs_path = os.path.abspath(gif_path)
        if label:
            data = f"{label}\n{abs_path}"
        else:
            data = abs_path

        qr_img = GIFQRCode.make_qr(data)
        if label:
            from PIL import ImageDraw, ImageFont
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except IOError:
                font = ImageFont.load_default()
            qr_w, qr_h = qr_img.size
            text_img = PILImage.new("RGB", (qr_w, qr_h + 40), "white")
            text_img.paste(qr_img.convert("RGB"), (0, 0))
            draw = ImageDraw.Draw(text_img)
            draw.text((qr_w // 2, qr_h + 5), label, fill="black", font=font, anchor="mt")
            return text_img
        return qr_img

    @staticmethod
    def make_url_qr(
        gcs_url: str,
        territory_name: str = "",
        product_name: str = "",
    ) -> PILImage.Image:
        from urllib.parse import quote
        safe_url = quote(gcs_url, safe=":/")
        label_parts = [p for p in [product_name, territory_name] if p]
        label = " | ".join(label_parts) if label_parts else None
        return GIFQRCode.make_qr(safe_url)
