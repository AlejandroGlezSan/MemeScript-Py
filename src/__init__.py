"""
MemeScript-Py - Generador de memes automático
"""

__version__ = "2.0.0"
__author__ = "Contributor"
__description__ = "Aplicación de escritorio para generar memes con plantillas de Imgflip"

from src.api_client import get_random_meme, get_meme_image, clear_cache, ImgflipAPIError
from src.renderer import render_meme, get_available_fonts, RendererError
from src.text_pool import get_random_phrase, add_phrase, TextPoolError
from src.cache import MemeCache

__all__ = [
    'get_random_meme',
    'get_meme_image',
    'clear_cache',
    'render_meme',
    'get_available_fonts',
    'get_random_phrase',
    'add_phrase',
    'ImgflipAPIError',
    'RendererError',
    'TextPoolError',
    'MemeCache',
]