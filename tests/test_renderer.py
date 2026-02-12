# tests/test_renderer.py
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops

# Asegurar imports desde la raíz del repo
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.renderer import render_meme  # noqa: E402


def _diff_bbox(original: Image.Image, modified: Image.Image):
    """
    Devuelve el bounding box (left, upper, right, lower) del área que difiere
    entre original y modified. Si no hay diferencias, devuelve None.
    """
    # Convertir a modo que incluya alpha si es necesario
    o = original.convert("RGBA")
    m = modified.convert("RGBA")
    diff = ImageChops.difference(o, m)
    return diff.getbbox()


def test_render_meme_returns_image_and_same_size():
    img = Image.new("RGB", (800, 600), color=(60, 60, 60))
    top = "TEXTO ARRIBA"
    bottom = "TEXTO ABAJO"
    out = render_meme(img, top_text=top, bottom_text=bottom, base_font_ratio=0.06, max_text_height_ratio=0.35)
    assert isinstance(out, Image.Image)
    assert out.size == img.size


def test_text_area_within_allowed_ratio_small_image():
    # Imagen pequeña donde antes el texto podía salirse
    w, h = 300, 180
    img = Image.new("RGB", (w, h), color=(60, 60, 60))
    long_phrase = " ".join(["MUCHO TEXTO"] * 12)  # texto largo para forzar ajuste/truncado

    max_text_height_ratio = 0.35
    out = render_meme(
        img,
        top_text=long_phrase,
        bottom_text="",
        base_font_ratio=0.08,
        max_text_height_ratio=max_text_height_ratio,
        padding_ratio=0.02,
        stroke_width_ratio=0.06,
    )

    bbox = _diff_bbox(img, out)
    assert bbox is not None, "No se detectó texto dibujado (diff bbox es None)"
    left, upper, right, lower = bbox
    # El área ocupada por el texto no debe superar el ratio permitido (con un pequeño margen)
    occupied_height = lower - upper
    allowed = int(h * max_text_height_ratio) + 4
    assert occupied_height <= allowed, f"Bloque de texto demasiado alto: {occupied_height} > {allowed}"
    # Asegurar que el bbox está dentro de la imagen
    assert 0 <= left < right <= w
    assert 0 <= upper < lower <= h


def test_text_area_within_allowed_ratio_large_image():
    # Imagen grande; el texto debe adaptarse y no exceder el ratio
    w, h = 1200, 900
    img = Image.new("RGB", (w, h), color=(60, 60, 60))
    long_phrase_top = " ".join(["ARRIBA"] * 20)
    long_phrase_bottom = " ".join(["ABAJO"] * 20)

    max_text_height_ratio = 0.35
    out = render_meme(
        img,
        top_text=long_phrase_top,
        bottom_text=long_phrase_bottom,
        base_font_ratio=0.06,
        max_text_height_ratio=max_text_height_ratio,
        padding_ratio=0.02,
        stroke_width_ratio=0.06,
    )

    bbox = _diff_bbox(img, out)
    assert bbox is not None, "No se detectó texto dibujado (diff bbox es None)"
    left, upper, right, lower = bbox
    occupied_height = lower - upper
    allowed = int(h * max_text_height_ratio) + 8
    assert occupied_height <= allowed, f"Bloque de texto demasiado alto: {occupied_height} > {allowed}"
    assert 0 <= left < right <= w
    assert 0 <= upper < lower <= h
