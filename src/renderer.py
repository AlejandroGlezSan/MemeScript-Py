from __future__ import annotations
import math
from pathlib import Path
from typing import Optional, Tuple, List, Final, Union, Any
from PIL import Image, ImageDraw, ImageFont

try:
    from PIL.Image import Resampling
    LANCZOS: Any = Resampling.LANCZOS
except (ImportError, AttributeError):
    LANCZOS = getattr(Image, "LANCZOS", getattr(Image, "BILINEAR", 2))

from PIL.ImageDraw import ImageDraw as PILImageDraw

AnyFont = Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]

MIN_FONT_SIZE: Final[int] = 12
MAX_IMAGE_PIXELS: Final[int] = 5000 * 5000
MAX_DIMENSION: Final[int] = 4000
DEFAULT_FONT_PATHS: Final[List[Path]] = [
    Path(__file__).parent / "assets" / "fonts" / "impact.ttf",
    Path("/usr/share/fonts/truetype/impact/impact.ttf"),
    Path("/usr/share/fonts/truetype/msttcorefonts/Impact.ttf"),
]

def _safe_load_font(font_path: Optional[str | Path], size: int) -> AnyFont:
    candidates: List[Path] = [Path(font_path)] if font_path else []
    candidates.extend(DEFAULT_FONT_PATHS)
    for p in candidates:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=int(size))
            except: continue
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size=int(size))
    except:
        return ImageFont.load_default()

def _reduce_image_if_needed(image: Image.Image, max_dim: int = MAX_DIMENSION) -> Image.Image:
    w, h = image.size
    scale = 1.0
    if w > max_dim or h > max_dim:
        scale = min(max_dim / w, max_dim / h)
    if scale < 1.0:
        return image.resize((max(1, int(w * scale)), max(1, int(h * scale))), resample=LANCZOS)
    return image

def _get_text_size(draw: PILImageDraw, text: str, font: AnyFont) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), str(text), font=font)
    return int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])

def _wrap_text_for_width(text: str, draw: PILImageDraw, font: AnyFont, max_width: int) -> List[str]:
    if not text: return []
    words = str(text).split()
    lines, current_line = [], ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        if _get_text_size(draw, test_line, font)[0] <= max_width:
            current_line = test_line
        else:
            if current_line: lines.append(current_line)
            current_line = word
    if current_line: lines.append(current_line)
    return lines

def render_meme(image: Image.Image, top_text: str = "", bottom_text: str = "", font_path: Optional[str] = None, 
                base_font_ratio: float = 0.1, max_text_height_ratio: float = 0.3, padding_ratio: float = 0.05) -> Image.Image:
    img = image.convert("RGBA")
    img = _reduce_image_if_needed(img)
    w, h = img.size
    draw = ImageDraw.Draw(img)
    
    max_w = int(w * 0.9)
    padding = int(h * padding_ratio)
    allowed_h = int(h * max_text_height_ratio)
    
    current_size = int(h * base_font_ratio)
    while current_size > MIN_FONT_SIZE:
        font = _safe_load_font(font_path, current_size)
        t_lines = _wrap_text_for_width(top_text, draw, font, max_w)
        b_lines = _wrap_text_for_width(bottom_text, draw, font, max_w)
        
        t_h = sum(_get_text_size(draw, l, font)[1] * 1.2 for l in t_lines)
        b_h = sum(_get_text_size(draw, l, font)[1] * 1.2 for l in b_lines)
        
        if t_h <= allowed_h and b_h <= allowed_h: break
        current_size -= 2

    font = _safe_load_font(font_path, current_size)
    stroke_w = max(1, int(current_size * 0.05))

    def draw_lines(lines, is_top):
        if not lines: return
        total_h = sum(_get_text_size(draw, l, font)[1] * 1.2 for l in lines)
        curr_y = padding if is_top else h - total_h - padding
        for l in lines:
            lw, lh = _get_text_size(draw, l, font)
            draw.text(((w - lw) // 2, curr_y), l, font=font, fill="white", stroke_width=stroke_w, stroke_fill="black")
            curr_y += int(lh * 1.2)

    draw_lines(_wrap_text_for_width(top_text, draw, font, max_w), True)
    draw_lines(_wrap_text_for_width(bottom_text, draw, font, max_w), False)
    return img