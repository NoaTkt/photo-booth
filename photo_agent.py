import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageOps


class PhotoAgent:
    def __init__(self, output_folder: str = "photos"):
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def save_photo(
        self,
        frame,
        prefix: str = "photo",
        background_path: Optional[str] = None,
        overlay_path: Optional[str] = None,
        corner_radius: int = 0,
        scale_percent: int = 85,
    ) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.jpg"
        output_path = self.output_folder / filename

        image = self.render_photo_image(
            frame,
            background_path=background_path,
            overlay_path=overlay_path,
            corner_radius=corner_radius,
            scale_percent=scale_percent,
        )
        image.save(output_path, quality=95)
        return str(output_path)

    def render_photo_image(
        self,
        frame,
        background_path: Optional[str] = None,
        overlay_path: Optional[str] = None,
        corner_radius: int = 0,
        scale_percent: int = 85,
    ) -> Image.Image:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)

        if background_path or overlay_path:
            try:
                return self._compose_with_background(
                    image,
                    Path(background_path) if background_path else None,
                    Path(overlay_path) if overlay_path else None,
                    corner_radius,
                    scale_percent,
                )
            except Exception:
                pass

        return image

    def _compose_with_background(
        self,
        image: Image.Image,
        background_path: Optional[Path],
        overlay_path: Optional[Path],
        corner_radius: int,
        scale_percent: int,
    ) -> Image.Image:
        """Compose image with optional bottom background and optional top overlay.

        Layer order (bottom->top): background_path, photo, overlay_path
        """
        output_size = image.size

        # Layer 1: background base (transparent if none provided)
        if background_path:
            background = Image.open(background_path).convert("RGBA")
            background = ImageOps.fit(background, output_size, Image.LANCZOS)
        else:
            background = Image.new("RGBA", output_size, (0, 0, 0, 0))

        # Layer 2: camera image, resized and centered according to the zoom setting
        scale = max(0.1, scale_percent / 100.0)
        target_size = (
            max(1, int(output_size[0] * scale)),
            max(1, int(output_size[1] * scale)),
        )
        photo = image.resize(target_size, Image.LANCZOS).convert("RGBA")

        if corner_radius > 0:
            mask = Image.new("L", photo.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle(
                [(0, 0), photo.size],
                radius=min(corner_radius, min(photo.size) // 2),
                fill=255,
            )
            photo.putalpha(mask)

        composed = background.copy()
        x = (output_size[0] - photo.width) // 2
        y = (output_size[1] - photo.height) // 2
        composed.alpha_composite(photo, (x, y))

        # Layer 3: overlay on top of the photo
        if overlay_path:
            try:
                overlay = Image.open(overlay_path).convert("RGBA")
                overlay = ImageOps.fit(overlay, output_size, Image.LANCZOS)
                composed.alpha_composite(overlay, (0, 0))
            except Exception:
                pass

        return composed.convert("RGB")

    def _load_font(self):
        try:
            return ImageFont.truetype("arial.ttf", 32)
        except Exception:
            return ImageFont.load_default()
