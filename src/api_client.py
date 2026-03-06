# src/api_client.py
"""
Módulo API: funciones para interactuar con Imgflip.
Incluye reintentos automáticos y soporte para caché.
"""

import random
import logging
from typing import Optional, Dict, List, Any, Tuple
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

import requests

from src.cache import MemeCache

logger = logging.getLogger(__name__)

IMGFLIP_MEMES_URL = "https://api.imgflip.com/get_memes"
DEFAULT_TIMEOUT = 10  # segundos
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0  # factor de backoff exponencial

# Inicializar caché global
_meme_cache = MemeCache()

class ImgflipAPIError(Exception):
    """Excepción personalizada para errores de la API de Imgflip."""
    pass

def _create_session() -> requests.Session:
    """
    Crea una sesión de requests con reintentos automáticos.
    
    Returns:
        requests.Session configurada con reintentos
    """
    session = requests.Session()
    
    # Configurar estrategia de reintentos
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    # Montar adaptador para HTTP y HTTPS
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def get_all_memes(timeout: int = DEFAULT_TIMEOUT) -> Optional[List[Dict[str, Any]]]:
    """
    Obtiene la lista completa de plantillas de memes de Imgflip.
    
    Args:
        timeout: Tiempo máximo de espera para la petición
        
    Returns:
        Lista de diccionarios con información de los memes o None si hay error
        
    Raises:
        ImgflipAPIError: Si hay un error en la API
    """
    session = _create_session()
    
    try:
        logger.info(f"Obteniendo lista de memes de {IMGFLIP_MEMES_URL}")
        resp = session.get(IMGFLIP_MEMES_URL, timeout=timeout)
        resp.raise_for_status()
        
        data = resp.json()
        
        if not data.get("success"):
            error_msg = data.get("error_message", "Error desconocido de la API")
            logger.error(f"API respondió con error: {error_msg}")
            raise ImgflipAPIError(f"Error de API: {error_msg}")
        
        memes = data.get("data", {}).get("memes", [])
        if not memes:
            logger.warning("La API devolvió una lista vacía de memes")
            return []
        
        logger.info(f"Obtenidos {len(memes)} memes correctamente")
        return memes
        
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout al conectar con Imgflip: {e}")
        raise ImgflipAPIError("Tiempo de espera agotado al conectar con Imgflip") from e
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Error de conexión con Imgflip: {e}")
        raise ImgflipAPIError("No se pudo conectar con Imgflip. Verifica tu conexión a internet.") from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la petición a Imgflip: {e}")
        raise ImgflipAPIError(f"Error al comunicarse con Imgflip: {str(e)}") from e
    except ValueError as e:
        logger.error(f"Error decodificando JSON de Imgflip: {e}")
        raise ImgflipAPIError("La respuesta de Imgflip no es válida") from e

def get_random_meme(timeout: int = DEFAULT_TIMEOUT) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Obtiene una plantilla aleatoria de Imgflip.
    
    Returns:
        Tupla (url_imagen, info_template) o None si no se pudo obtener
        
    Raises:
        ImgflipAPIError: Si hay un error en la API
    """
    memes = get_all_memes(timeout)
    
    if not memes:
        return None
    
    chosen = random.choice(memes)
    logger.info(f"Template seleccionado: {chosen.get('name')} (ID: {chosen.get('id')})")
    
    return chosen.get("url"), chosen

def get_meme_image(template_id: str, image_url: str, use_cache: bool = True) -> Optional[bytes]:
    """
    Descarga una imagen de meme, usando caché si está disponible.
    
    Args:
        template_id: ID del template
        image_url: URL de la imagen
        use_cache: Si se debe usar el sistema de caché
        
    Returns:
        Datos binarios de la imagen o None si hay error
    """
    # Intentar obtener del caché primero
    if use_cache:
        cached_path = _meme_cache.get(template_id)
        if cached_path:
            logger.info(f"Imagen {template_id} obtenida del caché")
            try:
                with open(cached_path, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error leyendo imagen del caché: {e}")
    
    # Descargar imagen
    session = _create_session()
    try:
        logger.info(f"Descargando imagen: {image_url}")
        resp = session.get(image_url, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        
        image_data = resp.content
        
        # Guardar en caché si se descargó correctamente
        if use_cache:
            try:
                # Necesitamos información del template para el caché
                memes = get_all_memes()
                template_info = next((m for m in memes if m["id"] == template_id), {})
                _meme_cache.put(template_id, image_data, template_info)
            except Exception as e:
                logger.error(f"Error guardando en caché: {e}")
        
        return image_data
        
    except Exception as e:
        logger.error(f"Error descargando imagen {image_url}: {e}")
        return None

def clear_cache():
    """Limpia el caché de imágenes."""
    _meme_cache.clear()

def get_cache_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del caché."""
    return _meme_cache.get_stats()