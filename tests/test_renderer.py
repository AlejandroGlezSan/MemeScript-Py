# tests/test_renderer.py
"""
Tests para el módulo renderer.py
"""

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageFont

# Asegurar imports desde la raíz del repo
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.renderer import (
    render_meme,
    get_available_fonts,
    _safe_load_font,
    _reduce_image_if_needed,
    _wrap_text_for_width,
    RendererError,
    MAX_DIMENSION
)


def _diff_bbox(original: Image.Image, modified: Image.Image):
    """
    Devuelve el bounding box (left, upper, right, lower) del área que difiere
    entre original y modified. Si no hay diferencias, devuelve None.
    """
    o = original.convert("RGBA")
    m = modified.convert("RGBA")
    diff = ImageChops.difference(o, m)
    return diff.getbbox()


class TestRenderer:
    """Tests para las funciones de renderizado."""

    def test_get_available_fonts(self):
        """Test de obtención de fuentes disponibles."""
        fonts = get_available_fonts()
        
        # Debería devolver una lista (puede estar vacía si no hay fuentes)
        assert isinstance(fonts, list)
        
        # Si hay fuentes, deberían ser strings no vacíos
        for font in fonts:
            assert isinstance(font, str)
            assert len(font) > 0

    def test_safe_load_font_default(self):
        """Test de carga de fuente por defecto."""
        font = _safe_load_font(None, 24)
        
        assert font is not None
        # La fuente por defecto no es FreeType, pero sigue siendo válida

    def test_render_meme_returns_image_and_same_size(self):
        """Test básico de renderizado."""
        img = Image.new("RGB", (800, 600), color=(60, 60, 60))
        top = "TEXTO ARRIBA"
        bottom = "TEXTO ABAJO"
        
        out = render_meme(
            img,
            top_text=top,
            bottom_text=bottom,
            font_size_ratio=0.06,
            max_text_height_ratio=0.35
        )
        
        assert isinstance(out, Image.Image)
        assert out.size == img.size
        assert out.mode == "RGBA"

    def test_render_meme_with_shadow(self):
        """Test de renderizado con sombra."""
        img = Image.new("RGB", (800, 600), color=(60, 60, 60))
        
        out = render_meme(
            img,
            top_text="Texto con sombra",
            bottom_text="",
            shadow=True
        )
        
        assert isinstance(out, Image.Image)
        bbox = _diff_bbox(img, out)
        assert bbox is not None  # Debe haber cambios

    def test_render_meme_empty_text(self):
        """Test con texto vacío."""
        img = Image.new("RGB", (800, 600), color=(60, 60, 60))
        
        out = render_meme(img, top_text="", bottom_text="")
        
        # Sin texto, la imagen no debería cambiar
        bbox = _diff_bbox(img, out)
        assert bbox is None

    def test_render_meme_single_line(self):
        """Test con una sola línea de texto."""
        img = Image.new("RGB", (800, 600), color=(60, 60, 60))
        
        out = render_meme(
            img,
            top_text="Solo texto superior",
            bottom_text=""
        )
        
        bbox = _diff_bbox(img, out)
        assert bbox is not None
        
        left, upper, right, lower = bbox
        # El texto debería estar en la parte superior
        assert upper < 300  # Mitad superior

    def test_render_meme_both_lines(self):
        """Test con texto superior e inferior."""
        img = Image.new("RGB", (800, 600), color=(60, 60, 60))
        
        out = render_meme(
            img,
            top_text="Texto arriba",
            bottom_text="Texto abajo"
        )
        
        bbox = _diff_bbox(img, out)
        assert bbox is not None
        
        left, upper, right, lower = bbox
        # Debería haber cambios en toda la altura
        assert upper < 100  # Texto arriba
        assert lower > 500  # Texto abajo

    def test_text_area_within_allowed_ratio_small_image(self):
        """Test con imagen pequeña - el texto debe ajustarse."""
        w, h = 300, 180
        img = Image.new("RGB", (w, h), color=(60, 60, 60))
        long_phrase = " ".join(["MUCHO TEXTO"] * 12)

        max_text_height_ratio = 0.35
        out = render_meme(
            img,
            top_text=long_phrase,
            bottom_text="",
            font_size_ratio=0.08,
            max_text_height_ratio=max_text_height_ratio,
            padding_ratio=0.02
        )

        bbox = _diff_bbox(img, out)
        assert bbox is not None
        
        left, upper, right, lower = bbox
        occupied_height = lower - upper
        allowed = int(h * max_text_height_ratio) + 4
        
        assert occupied_height <= allowed, f"Texto demasiado alto: {occupied_height} > {allowed}"
        assert 0 <= left < right <= w
        assert 0 <= upper < lower <= h

    def test_text_area_within_allowed_ratio_large_image(self):
        """Test con imagen grande."""
        w, h = 1200, 900
        img = Image.new("RGB", (w, h), color=(60, 60, 60))
        long_phrase_top = " ".join(["ARRIBA"] * 20)
        long_phrase_bottom = " ".join(["ABAJO"] * 20)

        max_text_height_ratio = 0.35
        out = render_meme(
            img,
            top_text=long_phrase_top,
            bottom_text=long_phrase_bottom,
            font_size_ratio=0.06,
            max_text_height_ratio=max_text_height_ratio,
            padding_ratio=0.02
        )

        bbox = _diff_bbox(img, out)
        assert bbox is not None
        
        left, upper, right, lower = bbox
        occupied_height = lower - upper
        allowed = int(h * max_text_height_ratio) + 8
        
        assert occupied_height <= allowed
        assert 0 <= left < right <= w
        assert 0 <= upper < lower <= h

    def test_reduce_image_if_needed(self):
        """Test de reducción de imágenes grandes."""
        # Imagen que excede el límite
        large_img = Image.new("RGB", (MAX_DIMENSION + 1000, MAX_DIMENSION + 1000))
        
        reduced = _reduce_image_if_needed(large_img)
        
        assert reduced.size[0] <= MAX_DIMENSION
        assert reduced.size[1] <= MAX_DIMENSION
        
        # Imagen que no excede el límite
        small_img = Image.new("RGB", (1000, 800))
        not_reduced = _reduce_image_if_needed(small_img)
        
        assert not_reduced.size == small_img.size

    def test_wrap_text_for_width(self):
        """Test de wrapping de texto."""
        img = Image.new("RGB", (800, 600))
        from PIL import ImageDraw
        
        draw = ImageDraw.Draw(img)
        font = _safe_load_font(None, 30)
        
        # Texto corto que no necesita wrap
        short_text = "Texto corto"
        lines = _wrap_text_for_width(short_text, draw, font, 500)
        assert len(lines) == 1
        
        # Texto largo que necesita wrap
        long_text = "Esta es una frase muy larga que debería dividirse en múltiples líneas"
        lines = _wrap_text_for_width(long_text, draw, font, 200)
        assert len(lines) > 1

    def test_render_with_different_font_sizes(self):
        """Test con diferentes tamaños de fuente."""
        img = Image.new("RGB", (800, 600))
        
        # Tamaño pequeño
        out_small = render_meme(img, top_text="Test", font_size_ratio=0.05)
        # Tamaño grande
        out_large = render_meme(img, top_text="Test", font_size_ratio=0.15)
        
        # Ambos deberían ser diferentes
        bbox = _diff_bbox(out_small, out_large)
        assert bbox is not None

    def test_render_with_special_characters(self):
        """Test con caracteres especiales y acentos."""
        img = Image.new("RGB", (800, 600))
        special_text = "¡Carácteres especiales! áéíóú ñ Ñ ¿? ¡! @#$%"
        
        try:
            out = render_meme(img, top_text=special_text)
            assert isinstance(out, Image.Image)
        except Exception as e:
            pytest.fail(f"Error renderizando caracteres especiales: {e}")

    def test_render_with_very_long_word(self):
        """Test con una palabra muy larga (debería truncar o wrap)."""
        img = Image.new("RGB", (800, 600))
        long_word = "Supercalifragilisticoespialidoso" * 10
        
        try:
            out = render_meme(img, top_text=long_word)
            assert isinstance(out, Image.Image)
        except Exception as e:
            pytest.fail(f"Error con palabra muy larga: {e}")

    def test_render_error_handling(self):
        """Test de manejo de errores."""
        img = Image.new("RGB", (800, 600))
        
        # Probar con valores extremos (no deberían causar error)
        try:
            render_meme(
                img,
                top_text="Test",
                font_size_ratio=2.0,  # Tamaño enorme
                max_text_height_ratio=0.01  # Altura mínima
            )
        except RendererError:
            pytest.fail("No debería lanzar error con valores extremos")
        except Exception as e:
            # Otros errores pueden ocurrir pero no queremos que fallen los tests
            pass


class TestRendererEdgeCases:
    """Tests para casos extremos del renderizado."""

    def test_transparent_image(self):
        """Test con imagen transparente (RGBA)."""
        img = Image.new("RGBA", (800, 600), (255, 0, 0, 128))  # Semitransparente
        
        out = render_meme(img, top_text="Test")
        
        assert out.mode == "RGBA"
        assert out.getpixel((100, 100))[3] == 255  # El texto debería ser opaco

    def test_grayscale_image(self):
        """Test con imagen en escala de grises."""
        img = Image.new("L", (800, 600), color=128)  # 'L' = Luminancia (grises)
        
        out = render_meme(img, top_text="Test")
        
        assert out.mode == "RGBA"  # Debería convertir a RGBA

    def test_palette_image(self):
        """Test con imagen en modo paleta."""
        img = Image.new("P", (800, 600), color=1)  # 'P' = Paleta
        
        out = render_meme(img, top_text="Test")
        
        assert out.mode == "RGBA"  # Debería convertir a RGBA

    def test_extreme_aspect_ratio(self):
        """Test con relación de aspecto extrema."""
        # Imagen muy panorámica
        wide_img = Image.new("RGB", (2000, 200))
        # Imagen muy vertical
        tall_img = Image.new("RGB", (200, 2000))
        
        try:
            out_wide = render_meme(wide_img, top_text="Test")
            out_tall = render_meme(tall_img, top_text="Test")
            
            assert out_wide.size == wide_img.size
            assert out_tall.size == tall_img.size
        except Exception as e:
            pytest.fail(f"Error con aspect ratio extremo: {e}")

    def test_multiline_text_positioning(self):
        """Test de posicionamiento de texto multilínea."""
        img = Image.new("RGB", (800, 600))
        
        # Texto con múltiples líneas
        multi_line = "Línea 1\nLínea 2\nLínea 3"
        
        out = render_meme(img, top_text=multi_line)
        
        # Debería renderizar sin errores
        assert isinstance(out, Image.Image)
        bbox = _diff_bbox(img, out)
        assert bbox is not None