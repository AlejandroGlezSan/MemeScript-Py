# tests/test_api_client.py
"""
Tests para el módulo api_client.py
"""

import sys
import json
import pytest
import requests
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from typing import Any, Dict, List

# Asegurar imports desde la raíz del repo
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api_client import (
    get_all_memes,
    get_random_meme,
    get_meme_image,
    clear_cache,
    get_cache_stats,
    ImgflipAPIError,
    _create_session
)
from src.cache import MemeCache

# Datos de ejemplo para tests
SAMPLE_MEMES_RESPONSE = {
    "success": True,
    "data": {
        "memes": [
            {
                "id": "123456",
                "name": "Test Meme 1",
                "url": "https://i.imgflip.com/test1.jpg",
                "width": 500,
                "height": 500
            },
            {
                "id": "789012",
                "name": "Test Meme 2",
                "url": "https://i.imgflip.com/test2.jpg",
                "width": 600,
                "height": 400
            }
        ]
    }
}

SAMPLE_ERROR_RESPONSE = {
    "success": False,
    "error_message": "API rate limit exceeded"
}

class TestApiClient:
    """Tests para las funciones de api_client.py"""

    def test_create_session_with_retries(self):
        """Verifica que la sesión se cree con la configuración de reintentos correcta."""
        session = _create_session()
        
        assert isinstance(session, requests.Session)
        # Verificar que los adapters están montados
        assert 'http://' in session.adapters
        assert 'https://' in session.adapters
        
        # Verificar configuración de reintentos (esto es un poco más complejo de testear directamente)
        http_adapter = session.adapters['http://']
        assert hasattr(http_adapter, 'max_retries')
        assert http_adapter._pool_connections == 10
        assert http_adapter._pool_maxsize == 10

    @patch('src.api_client._create_session')
    def test_get_all_memes_success(self, mock_create_session):
        """Test de obtención exitosa de memes."""
        # Configurar mock
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = SAMPLE_MEMES_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        
        # Ejecutar
        result = get_all_memes()
        
        # Verificar
        assert result is not None
        assert len(result) == 2
        assert result[0]['id'] == '123456'
        assert result[1]['name'] == 'Test Meme 2'
        mock_session.get.assert_called_once_with(
            'https://api.imgflip.com/get_memes',
            timeout=10
        )

    @patch('src.api_client._create_session')
    def test_get_all_memes_api_error(self, mock_create_session):
        """Test de error de API (success=False)."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = SAMPLE_ERROR_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        
        with pytest.raises(ImgflipAPIError) as exc_info:
            get_all_memes()
        
        assert "API rate limit exceeded" in str(exc_info.value)

    @patch('src.api_client._create_session')
    def test_get_all_memes_http_error(self, mock_create_session):
        """Test de error HTTP (404, 500, etc.)."""
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_create_session.return_value = mock_session
        
        with pytest.raises(ImgflipAPIError) as exc_info:
            get_all_memes()
        
        assert "Error al comunicarse" in str(exc_info.value)

    @patch('src.api_client._create_session')
    def test_get_all_memes_timeout(self, mock_create_session):
        """Test de timeout."""
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.Timeout("Connection timeout")
        mock_create_session.return_value = mock_session
        
        with pytest.raises(ImgflipAPIError) as exc_info:
            get_all_memes()
        
        assert "Tiempo de espera agotado" in str(exc_info.value)

    @patch('src.api_client._create_session')
    def test_get_all_memes_connection_error(self, mock_create_session):
        """Test de error de conexión."""
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        mock_create_session.return_value = mock_session
        
        with pytest.raises(ImgflipAPIError) as exc_info:
            get_all_memes()
        
        assert "No se pudo conectar" in str(exc_info.value)

    @patch('src.api_client.get_all_memes')
    def test_get_random_meme_success(self, mock_get_all_memes):
        """Test de obtención aleatoria de meme."""
        mock_get_all_memes.return_value = SAMPLE_MEMES_RESPONSE['data']['memes']
        
        result = get_random_meme()
        
        assert result is not None
        url, info = result
        assert url in ['https://i.imgflip.com/test1.jpg', 'https://i.imgflip.com/test2.jpg']
        assert 'id' in info

    @patch('src.api_client.get_all_memes')
    def test_get_random_meme_empty_list(self, mock_get_all_memes):
        """Test cuando la lista de memes está vacía."""
        mock_get_all_memes.return_value = []
        
        result = get_random_meme()
        
        assert result is None

    @patch('src.api_client.get_all_memes')
    def test_get_random_meme_none(self, mock_get_all_memes):
        """Test cuando get_all_memes devuelve None."""
        mock_get_all_memes.return_value = None
        
        result = get_random_meme()
        
        assert result is None

    @patch('src.api_client._meme_cache')
    @patch('src.api_client._create_session')
    def test_get_meme_image_from_cache(self, mock_create_session, mock_cache):
        """Test de obtención de imagen desde caché."""
        # Configurar mock del caché
        mock_cache.get.return_value = Path("/fake/cache/path/image.png")
        
        # Mock para lectura de archivo
        mock_image_data = b"fake_image_data"
        with patch('builtins.open', mock_open(read_data=mock_image_data)):
            result = get_meme_image("123456", "https://example.com/image.jpg")
        
        # Verificar que NO se intentó descargar
        mock_create_session.assert_not_called()
        assert result == mock_image_data

    @patch('src.api_client._meme_cache')
    @patch('src.api_client._create_session')
    @patch('src.api_client.get_all_memes')
    def test_get_meme_image_download(self, mock_get_all_memes, mock_create_session, mock_cache):
        """Test de descarga de imagen (no en caché)."""
        # Configurar mock del caché (no encontrado)
        mock_cache.get.return_value = None
        
        # Configurar mock de sesión para descarga
        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b"downloaded_image_data"
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        
        # Configurar mock para get_all_memes (necesario para guardar en caché)
        mock_get_all_memes.return_value = SAMPLE_MEMES_RESPONSE['data']['memes']
        
        result = get_meme_image("123456", "https://example.com/image.jpg")
        
        # Verificar que se descargó
        mock_session.get.assert_called_once_with(
            "https://example.com/image.jpg",
            timeout=10
        )
        # Verificar que se intentó guardar en caché
        mock_cache.put.assert_called_once()
        assert result == b"downloaded_image_data"

    @patch('src.api_client._meme_cache')
    @patch('src.api_client._create_session')
    def test_get_meme_image_download_error(self, mock_create_session, mock_cache):
        """Test de error en descarga de imagen."""
        mock_cache.get.return_value = None
        
        mock_session = Mock()
        mock_session.get.side_effect = Exception("Download failed")
        mock_create_session.return_value = mock_session
        
        result = get_meme_image("123456", "https://example.com/image.jpg")
        
        assert result is None

    @patch('src.api_client._meme_cache')
    def test_clear_cache(self, mock_cache):
        """Test de limpieza de caché."""
        clear_cache()
        mock_cache.clear.assert_called_once()

    @patch('src.api_client._meme_cache')
    def test_get_cache_stats(self, mock_cache):
        """Test de obtención de estadísticas de caché."""
        expected_stats = {
            "total_images": 5,
            "total_size_mb": 10.5,
            "max_size_mb": 500,
            "usage_percent": 2.1,
            "cache_dir": "/fake/cache/dir"
        }
        mock_cache.get_stats.return_value = expected_stats
        
        stats = get_cache_stats()
        
        assert stats == expected_stats
        mock_cache.get_stats.assert_called_once()


class TestMemeCache:
    """Tests para la clase MemeCache."""

    def test_cache_initialization(self, tmp_path):
        """Test de inicialización del caché."""
        cache = MemeCache(cache_dir=tmp_path, max_size_mb=100, max_age_days=7)
        
        assert cache.cache_dir == tmp_path
        assert cache.images_dir == tmp_path / "images"
        assert cache.metadata_file == tmp_path / "metadata.json"
        assert cache.max_size_bytes == 100 * 1024 * 1024
        assert cache.images_dir.exists()

    def test_cache_key_generation(self):
        """Test de generación de claves de caché."""
        cache = MemeCache()
        
        key1 = cache._get_cache_key("123")
        key2 = cache._get_cache_key("123")
        key3 = cache._get_cache_key("456")
        
        assert key1 == key2  # Misma entrada debe dar misma clave
        assert key1 != key3  # Diferente entrada debe dar diferente clave
        assert len(key1) == 32  # MD5 produce 32 caracteres hex

    def test_put_and_get(self, tmp_path):
        """Test de guardar y recuperar del caché."""
        cache = MemeCache(cache_dir=tmp_path)
        
        template_id = "test123"
        image_data = b"fake_image_data"
        template_info = {
            "name": "Test Template",
            "url": "https://example.com/test.jpg",
            "width": 500,
            "height": 500
        }
        
        # Guardar
        saved_path = cache.put(template_id, image_data, template_info)
        assert saved_path.exists()
        assert saved_path.parent == cache.images_dir
        
        # Recuperar
        retrieved_path = cache.get(template_id)
        assert retrieved_path == saved_path
        
        # Verificar contenido
        with open(retrieved_path, 'rb') as f:
            assert f.read() == image_data

    def test_cache_expiration(self, tmp_path):
        """Test de expiración de caché."""
        cache = MemeCache(cache_dir=tmp_path, max_age_days=0)  # Expira inmediatamente
        
        template_id = "test123"
        image_data = b"fake_image_data"
        template_info = {"name": "Test"}
        
        # Guardar
        cache.put(template_id, image_data, template_info)
        
        # Modificar timestamp en metadatos para simular expiración
        cache.metadata["templates"][cache._get_cache_key(template_id)]["cached_at"] = "2000-01-01T00:00:00"
        cache._save_metadata()
        
        # Intentar recuperar (debería fallar por expiración)
        result = cache.get(template_id)
        assert result is None

    def test_cache_lru_cleanup(self, tmp_path):
        """Test de limpieza LRU cuando se excede el tamaño."""
        # Caché muy pequeño (solo 1KB)
        cache = MemeCache(cache_dir=tmp_path, max_size_mb=0.001)  # ~1KB
        
        # Guardar primera imagen (500 bytes)
        data1 = b"x" * 500
        cache.put("id1", data1, {"name": "Test1"})
        
        # Guardar segunda imagen (600 bytes) - debería forzar limpieza
        data2 = b"y" * 600
        cache.put("id2", data2, {"name": "Test2"})
        
        # La primera imagen debería haber sido eliminada
        assert cache.get("id1") is None
        assert cache.get("id2") is not None

    def test_cache_clear(self, tmp_path):
        """Test de limpieza completa del caché."""
        cache = MemeCache(cache_dir=tmp_path)
        
        # Guardar algunas imágenes
        for i in range(3):
            cache.put(f"id{i}", b"data", {"name": f"Test{i}"})
        
        assert len(list(cache.images_dir.glob("*.png"))) == 3
        
        # Limpiar caché
        cache.clear()
        
        assert len(list(cache.images_dir.glob("*.png"))) == 0
        assert cache.metadata["templates"] == {}
        assert cache.metadata["size"] == 0

    def test_cache_stats(self, tmp_path):
        """Test de estadísticas del caché."""
        cache = MemeCache(cache_dir=tmp_path, max_size_mb=100)
        
        # Guardar algunas imágenes
        for i in range(3):
            cache.put(f"id{i}", b"x" * 1000, {"name": f"Test{i}"})
        
        stats = cache.get_stats()
        
        assert stats["total_images"] == 3
        assert stats["total_size_mb"] > 0
        assert stats["max_size_mb"] == 100
        assert stats["cache_dir"] == str(tmp_path)
        assert 0 <= stats["usage_percent"] <= 100

    def test_cache_metadata_persistence(self, tmp_path):
        """Test de persistencia de metadatos entre instancias."""
        # Crear primera instancia y guardar datos
        cache1 = MemeCache(cache_dir=tmp_path)
        cache1.put("test_id", b"data", {"name": "Test"})
        
        # Crear segunda instancia (debería cargar metadatos)
        cache2 = MemeCache(cache_dir=tmp_path)
        
        # Verificar que puede recuperar la imagen
        result = cache2.get("test_id")
        assert result is not None
        assert result.exists()