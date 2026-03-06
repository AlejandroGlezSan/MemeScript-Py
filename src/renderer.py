# src/renderer.py
"""
Motor de renderizado de memes con soporte para múltiples fuentes y estilos.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Final, Union, Any, Dict
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

try:
    from PIL.Image import Resampling
    LANCZOS: Any = Resampling.LANCZOS
except (ImportError, AttributeError):
    LANCZOS = getattr(Image, "LANCZOS", getattr(Image, "BILINEAR", 2))

# Constantes
MIN_FONT_SIZE: Final[int] = 8
MAX_FONT_SIZE: Final[int] = 200
MAX_IMAGE_PIXELS: Final[int] = 5000 * 5000
MAX_DIMENSION: Final[int] = 4000

# Fuentes disponibles
AVAILABLE_FONTS: Final[Dict[str, List[Path]]] = {
    "Impact": [
        Path(__file__).parent / "assets" / "fonts" / "impact.ttf",
        Path("/usr/share/fonts/truetype/impact/impact.ttf"),
        Path("/usr/share/fonts/truetype/msttcorefonts/Impact.ttf"),
        Path("C:/Windows/Fonts/impact.ttf"),
    ],
    "Arial Black": [
        Path(__file__).parent / "assets" / "fonts" / "arialbd.ttf",
        Path("/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ],
    "Comic Sans MS": [
        Path(__file__).parent / "assets" / "fonts" / "comic.ttf",
        Path("/usr/share/fonts/truetype/msttcorefonts/Comic_Sans_MS.ttf"),
        Path("C:/Windows/Fonts/comic.ttf"),
    ],
    "Roboto": [
        Path("/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf"),
    ],
}

AnyFont = Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]

class RendererError(Exception):
    """Excepción personalizada para errores de renderizado."""
    pass

def get_available_fonts() -> List[str]:
    """
    Obtiene la lista de fuentes disponibles en el sistema.
    
    Returns:
        Lista de nombres de fuentes que se pueden usar
    """
    available = []
    for font_name, paths in AVAILABLE_FONTS.items():
        for path in paths:
            if path.exists():
                available.append(font_name)
                break
    return available

def _safe_load_font(font_name: Optional[str], size: int) -> AnyFont:
    """
    Carga una fuente de forma segura, con fallbacks.
    
    Args:
        font_name: Nombre de la fuente a cargar
        size: Tamaño de la fuente
        
    Returns:
        Objeto fuente de PIL
    """
    # Si se especificó una fuente, intentar cargarla
    if font_name and font_name in AVAILABLE_FONTS:
        for path in AVAILABLE_FONTS[font_name]:
            if path.exists():
                try:
                    logger.debug(f"Cargando fuente: {path}")
                    return ImageFont.truetype(str(path), size=int(size))
                except Exception as e:
                    logger.warning(f"Error cargando fuente {path}: {e}")
                    continue
    
    # Intentar fuentes del sistema comunes
    system_fonts = [
        ("DejaVuSans-Bold.ttf", "DejaVu Sans Bold"),
        ("Arial.ttf", "Arial"),
        ("arial.ttf", "Arial"),
        ("LiberationSans-Bold.ttf", "Liberation Sans Bold"),
    ]
    
    for font_file, font_name in system_fonts:
        try:
            return ImageFont.truetype(font_file, size=int(size))
        except:
            try:
                return ImageFont.truetype(font_name, size=int(size))
            except:
                continue
    
    # Fallback final
    logger.warning("Usando fuente por defecto (no TrueType)")
    return ImageFont.load_default()

def _reduce_image_if_needed(image: Image.Image, max_dim: int = MAX_DIMENSION) -> Image.Image:
    """
    Reduce la imagen si excede las dimensiones máximas.
    """
    w, h = image.size
    scale = 1.0
    
    if w > max_dim or h > max_dim:
        scale = min(max_dim / w, max_dim / h)
        logger.info(f"Reduciendo imagen: {w}x{h} -> {int(w*scale)}x{int(h*scale)}")
    
    if scale < 1.0:
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        return image.resize(new_size, resample=LANCZOS)
    
    return image

def _get_text_size(draw: ImageDraw.ImageDraw, text: str, font: AnyFont) -> Tuple[int, int]:
    """
    Obtiene el tamaño del texto de forma segura.
    """
    try:
        bbox = draw.textbbox((0, 0), str(text), font=font)
        return int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])
    except Exception as e:
        logger.error(f"Error calculando tamaño del texto: {e}")
        return (0, 0)

def _wrap_text_for_width(text: str, draw: ImageDraw.ImageDraw, font: AnyFont, max_width: int) -> List[str]:
    """
    Envuelve el texto para que quepa en el ancho máximo.
    """
    if not text or not text.strip():
        return []
    
    words = str(text).strip().split()
    if not words:
        return []
    
    lines = []
    current_line = words[0]
    
    for word in words[1:]:
        test_line = f"{current_line} {word}"
        text_width, _ = _get_text_size(draw, test_line, font)
        
        if text_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    
    lines.append(current_line)
    return lines

def render_meme(
    image: Image.Image,
    top_text: str = "",
    bottom_text: str = "",
    font_name: Optional[str] = None,
    font_size_ratio: float = 0.1,
    max_text_height_ratio: float = 0.35,
    padding_ratio: float = 0.03,
    stroke_width_ratio: float = 0.05,
    text_color: str = "white",
    stroke_color: str = "black",
    shadow: bool = False
) -> Image.Image:
    """
    Renderiza un meme con texto superior e inferior.
    
    Args:
        image: Imagen base
        top_text: Texto superior
        bottom_text: Texto inferior
        font_name: Nombre de la fuente a usar
        font_size_ratio: Ratio del tamaño de fuente respecto a la altura
        max_text_height_ratio: Ratio máximo de altura del texto
        padding_ratio: Ratio de padding respecto a la altura
        stroke_width_ratio: Ratio del ancho del contorno
        text_color: Color del texto
        stroke_color: Color del contorno
        shadow: Si se debe añadir sombra al texto
        
    Returns:
        Imagen con el texto renderizado
    """
    try:
        # Preparar imagen
        img = image.convert("RGBA")
        img = _reduce_image_if_needed(img)
        w, h = img.size
        
        logger.info(f"Renderizando meme: {w}x{h}, fuente={font_name or 'default'}")
        
        # Crear capa de texto separada para mejor control
        text_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        # Calcular dimensiones
        max_width = int(w * 0.9)  # 90% del ancho
        padding = int(h * padding_ratio)
        max_text_height = int(h * max_text_height_ratio)
        
        # Calcular tamaño de fuente óptimo
        current_size = int(h * font_size_ratio)
        current_size = max(MIN_FONT_SIZE, min(current_size, MAX_FONT_SIZE))
        
        optimal_size = current_size
        for test_size in range(current_size, MIN_FONT_SIZE - 1, -2):
            font = _safe_load_font(font_name, test_size)
            
            # Envolver texto y calcular alturas
            top_lines = _wrap_text_for_width(top_text, draw, font, max_width)
            bottom_lines = _wrap_text_for_width(bottom_text, draw, font, max_width)
            
            # Calcular altura total del texto (con espaciado)
            line_spacing = 1.2
            top_height = 0
            for line in top_lines:
                _, lh = _get_text_size(draw, line, font)
                top_height += int(lh * line_spacing)
            
            bottom_height = 0
            for line in bottom_lines:
                _, lh = _get_text_size(draw, line, font)
                bottom_height += int(lh * line_spacing)
            
            if top_height <= max_text_height and bottom_height <= max_text_height:
                optimal_size = test_size
                break
        
        # Cargar fuente con el tamaño óptimo
        font = _safe_load_font(font_name, optimal_size)
        stroke_width = max(1, int(optimal_size * stroke_width_ratio))
        
        logger.debug(f"Tamaño de fuente óptimo: {optimal_size}, stroke: {stroke_width}")
        
        def draw_lines(lines: List[str], is_top: bool):
            """Dibuja las líneas de texto en la posición correcta."""
            if not lines:
                return
            
            # Calcular altura total
            line_spacing = 1.2
            total_height = 0
            line_heights = []
            
            for line in lines:
                _, lh = _get_text_size(draw, line, font)
                line_heights.append(lh)
                total_height += int(lh * line_spacing)
            
            # Posición Y inicial
            if is_top:
                current_y = padding
            else:
                current_y = h - total_height - padding
            
            # Dibujar cada línea
            for i, line in enumerate(lines):
                line_width, line_height = _get_text_size(draw, line, font)
                x = (w - line_width) // 2
                
                if shadow:
                    # Dibujar sombra
                    shadow_offset = max(2, stroke_width // 2)
                    draw.text(
                        (x + shadow_offset, current_y + shadow_offset),
                        line,
                        font=font,
                        fill=(0, 0, 0, 180)
                    )
                
                # Dibujar texto principal con contorno
                draw.text(
                    (x, current_y),
                    line,
                    font=font,
                    fill=text_color,
                    stroke_width=stroke_width,
                    stroke_fill=stroke_color
                )
                
                current_y += int(line_height * line_spacing)
        
        # Dibujar textos
        draw_lines(_wrap_text_for_width(top_text, draw, font, max_width), True)
        draw_lines(_wrap_text_for_width(bottom_text, draw, font, max_width), False)
        
        # Combinar capa de texto con imagen original
        result = Image.alpha_composite(img, text_layer)
        
        return result
        
    except Exception as e:
        logger.error(f"Error en renderizado: {e}", exc_info=True)
        raise RendererError(f"Error al renderizar el meme: {str(e)}") from e