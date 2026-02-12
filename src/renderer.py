# src/renderer.py
"""
Renderer para MemeScript-Py (versión corregida para evitar errores en VSCode)

Provee funciones para componer texto superior e inferior sobre una imagen PIL,
con ajuste de tamaño relativo a la imagen, wrapping, centrado, contorno (stroke)
y protección para que el texto no se dibuje fuera del área visible.
"""

from __future__ import annotations

import math
import textwrap
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageDraw import ImageDraw as PILImageDraw

# Configurables
DEFAULT_FONT_SIZE = 48
MIN_FONT_SIZE = 12
MAX_IMAGE_PIXELS = 5000 * 5000
MAX_DIMENSION = 4000
DEFAULT_FONT_PATHS: List[Path] = [
    Path(__file__).parent / "assets" / "fonts" / "impact.ttf",
    Path(__file__).parent / "assets" / "fonts" / "Impact.ttf",
    Path("/usr/share/fonts/truetype/impact/impact.ttf"),
    Path("/usr/share/fonts/truetype/msttcorefonts/Impact.ttf"),
]


def _safe_load_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    """
    Intenta cargar una fuente TrueType desde font_path o rutas por defecto.
    Si falla, devuelve ImageFont.load_default() como fallback.
    """
    candidates: List[Path] = []
    if font_path:
        candidates.append(Path(font_path))
    candidates.extend([p for p in DEFAULT_FONT_PATHS if p is not None])

    for p in candidates:
        try:
            if p and p.exists():
                return ImageFont.truetype(str(p), size=size)
        except Exception:
            continue

    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size=size)
    except Exception:
        return ImageFont.load_default()


def _reduce_image_if_needed(image: Image.Image, max_dim: int = MAX_DIMENSION) -> Image.Image:
    """
    Reduce la imagen si alguna dimensión supera max_dim, manteniendo aspecto.
    También evita imágenes con píxeles totales excesivos.
    """
    w, h = image.size
    if w > max_dim or h > max_dim:
        scale = min(max_dim / w, max_dim / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        return image.resize((new_w, new_h), Image.LANCZOS)

    if w * h > MAX_IMAGE_PIXELS:
        scale = math.sqrt(MAX_IMAGE_PIXELS / (w * h))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        return image.resize((new_w, new_h), Image.LANCZOS)
    return image


def _wrap_text_for_width(text: str, draw: PILImageDraw, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """
    Envuelve el texto en varias líneas para que quepa en max_width.
    Devuelve lista de líneas.
    """
    if not text:
        return []

    text = " ".join(text.split())
    words = text.split(" ")
    lines: List[str] = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)

    final_lines: List[str] = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            final_lines.append(line)
        else:
            avg_char_w = (bbox[2] - bbox[0]) / max(1, len(line))
            if avg_char_w <= 0:
                final_lines.append(line)
            else:
                est_chars = max(1, int(max_width / avg_char_w))
                wrapped = textwrap.wrap(line, width=est_chars)
                final_lines.extend(wrapped if wrapped else [line])
    return final_lines


def _draw_text_with_stroke(draw: PILImageDraw, pos: Tuple[int, int], text: str, font: ImageFont.FreeTypeFont,
                           fill: str, stroke_width: int, stroke_fill: str) -> None:
    """
    Dibuja texto con contorno. Usa stroke_width/stroke_fill si la versión de Pillow lo soporta,
    si no, hace un fallback dibujando el texto desplazado en 8 direcciones.
    """
    try:
        draw.text(pos, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
    except TypeError:
        x, y = pos
        offsets = [(-stroke_width, -stroke_width), (-stroke_width, 0), (-stroke_width, stroke_width),
                   (0, -stroke_width), (0, stroke_width),
                   (stroke_width, -stroke_width), (stroke_width, 0), (stroke_width, stroke_width)]
        for dx, dy in offsets:
            draw.text((x + dx, y + dy), text, font=font, fill=stroke_fill)
        draw.text(pos, text, font=font, fill=fill)


def render_meme(image: Image.Image,
                top_text: str = "",
                bottom_text: str = "",
                font_path: Optional[str] = None,
                font_size: Optional[int] = None,
                base_font_ratio: float = 0.06,
                max_text_height_ratio: float = 0.35,
                min_font_size: int = MIN_FONT_SIZE,
                padding_ratio: float = 0.02,
                stroke_width_ratio: float = 0.06,
                stroke_fill: str = "black",
                text_fill: str = "white",
                max_width_ratio: float = 0.95) -> Image.Image:
    """
    Renderiza un meme sobre la imagen dada con escalado dinámico de fuente y
    protección contra overflow del texto fuera de la imagen.
    """
    if image is None:
        raise ValueError("image no puede ser None")

    img = image.convert("RGBA")
    img = _reduce_image_if_needed(img)

    w, h = img.size
    draw = ImageDraw.Draw(img)  # type: ignore[assignment]

    max_text_width = max(10, int(w * max_width_ratio))
    padding = max(4, int(min(w, h) * padding_ratio))

    if font_size and font_size > 0:
        initial_font_size = int(font_size)
    else:
        initial_font_size = max(min_font_size, int(h * base_font_ratio))

    def _measure_block_height(lines: List[str], font: ImageFont.FreeTypeFont, line_spacing: float = 1.05) -> int:
        if not lines:
            return 0
        total = 0
        for ln in lines:
            bbox = draw.textbbox((0, 0), ln, font=font)
            line_h = bbox[3] - bbox[1]
            total += int(line_h * line_spacing)
        return total

    def _truncate_line_to_width(line: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
        if not line:
            return line
        bbox = draw.textbbox((0, 0), line, font=font)
        if bbox[2] - bbox[0] <= max_w:
            return line
        ellipsis = "…"
        low, high = 0, len(line)
        best = ""
        last_bbox = bbox
        while low <= high:
            mid = (low + high) // 2
            candidate = line[:mid].rstrip() + ellipsis
            last_bbox = draw.textbbox((0, 0), candidate, font=font)
            if last_bbox[2] - last_bbox[0] <= max_w:
                best = candidate
                low = mid + 1
            else:
                high = mid - 1
        if best:
            return best
        avg_char_w = (last_bbox[2] - last_bbox[0]) / max(1, len(line))
        est_chars = max(1, int(max_w / avg_char_w)) if avg_char_w > 0 else max(1, len(line) // 2)
        return line[:est_chars].rstrip() + ellipsis

    def _shrink_lines_to_height(lines: List[str], font: ImageFont.FreeTypeFont, allowed_h: int, max_w: int) -> List[str]:
        if _measure_block_height(lines, font) <= allowed_h:
            return lines
        new_lines = [_truncate_line_to_width(ln, font, max_w) for ln in lines]
        while _measure_block_height(new_lines, font) > allowed_h and len(new_lines) > 1:
            a = new_lines[-2]
            b = new_lines[-1]
            combined = (a + " " + b).strip()
            combined = _truncate_line_to_width(combined, font, max_w)
            new_lines = new_lines[:-2] + [combined]
        if _measure_block_height(new_lines, font) > allowed_h and len(new_lines) == 1:
            new_lines = [_truncate_line_to_width(new_lines[0], font, max_w)]
        return new_lines

    def _fit_font_and_lines(top: str, bottom: str, start_size: int) -> Tuple[ImageFont.FreeTypeFont, int, List[str], List[str]]:
        size = start_size
        allowed_total_h = max(10, int(h * max_text_height_ratio))
        while size >= min_font_size:
            f = _safe_load_font(font_path, size=size)
            top_lines = _wrap_text_for_width(top, draw, f, max_text_width - 2 * padding)
            bottom_lines = _wrap_text_for_width(bottom, draw, f, max_text_width - 2 * padding)
            top_h = _measure_block_height(top_lines, f)
            bottom_h = _measure_block_height(bottom_lines, f)
            total_h = top_h + bottom_h + 2 * padding
            if total_h <= allowed_total_h or size == min_font_size:
                top_lines = _shrink_lines_to_height(top_lines, f, max(0, allowed_total_h - bottom_h - padding), max_text_width - 2 * padding)
                bottom_lines = _shrink_lines_to_height(bottom_lines, f, max(0, allowed_total_h - top_h - padding), max_text_width - 2 * padding)
                return f, size, top_lines, bottom_lines
            size = max(min_font_size, size - 2)
            if size == min_font_size:
                f = _safe_load_font(font_path, size=size)
                top_lines = _wrap_text_for_width(top, draw, f, max_text_width - 2 * padding)
                bottom_lines = _wrap_text_for_width(bottom, draw, f, max_text_width - 2 * padding)
                top_lines = _shrink_lines_to_height(top_lines, f, max(0, allowed_total_h - _measure_block_height(bottom_lines, f) - padding), max_text_width - 2 * padding)
                bottom_lines = _shrink_lines_to_height(bottom_lines, f, max(0, allowed_total_h - _measure_block_height(top_lines, f) - padding), max_text_width - 2 * padding)
                return f, size, top_lines, bottom_lines
        f = _safe_load_font(font_path, size=min_font_size)
        top_lines = _wrap_text_for_width(top, draw, f, max_text_width - 2 * padding)
        bottom_lines = _wrap_text_for_width(bottom, draw, f, max_text_width - 2 * padding)
        top_lines = _shrink_lines_to_height(top_lines, f, int(h * max_text_height_ratio / 2), max_text_width - 2 * padding)
        bottom_lines = _shrink_lines_to_height(bottom_lines, f, int(h * max_text_height_ratio / 2), max_text_width - 2 * padding)
        return f, min_font_size, top_lines, bottom_lines

    font, used_font_size, top_lines, bottom_lines = _fit_font_and_lines(top_text, bottom_text, initial_font_size)
    stroke_width = max(1, int(max(1, used_font_size * stroke_width_ratio)))

    def _block_height(lines: List[str], font: ImageFont.FreeTypeFont, line_spacing: float = 1.05) -> int:
        return _measure_block_height(lines, font, line_spacing)

    top_block_h = _block_height(top_lines, font)
    bottom_block_h = _block_height(bottom_lines, font)

    # Dibujar top lines (asegurando límites)
    y = padding
    for ln in top_lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        line_w = bbox[2] - bbox[0]
        line_h = bbox[3] - bbox[1]
        x = max(0, (w - line_w) // 2)
        if y + line_h > h - padding:
            break
        _draw_text_with_stroke(draw, (x, y), ln, font, fill=text_fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        y += int(line_h * 1.05)

    # Dibujar bottom lines (desde abajo hacia arriba), evitando solapamientos
    y_bottom_start = h - bottom_block_h - padding
    if y_bottom_start < y + padding:
        y_bottom_start = max(y + padding, padding)
    y = y_bottom_start
    for ln in bottom_lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        line_w = bbox[2] - bbox[0]
        line_h = bbox[3] - bbox[1]
        x = max(0, (w - line_w) // 2)
        if y + line_h > h - padding:
            break
        _draw_text_with_stroke(draw, (x, y), ln, font, fill=text_fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        y += int(line_h * 1.05)

    return img


# Demo rápido si se ejecuta como script
if __name__ == "__main__":
    demo_img = Image.new("RGB", (800, 600), color=(60, 60, 60))
    top = "CUANDO EL CÓDIGO COMPILA"
    bottom = "Y NADIE SABE POR QUÉ"
    out = render_meme(demo_img, top, bottom, font_path=None, font_size=None, base_font_ratio=0.06, max_text_height_ratio=0.35, padding_ratio=0.02, stroke_width_ratio=0.06)
    tmp = Path(tempfile.gettempdir()) / "meme_demo_output.png"
    out.convert("RGB").save(tmp)
    print(f"Meme demo guardado en: {tmp}")
