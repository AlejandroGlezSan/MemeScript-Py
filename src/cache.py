# src/cache.py
"""
Sistema de caché para plantillas de memes.
Almacena imágenes localmente para reducir descargas y permitir modo offline.
"""

import os
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class MemeCache:
    """Gestiona el caché de imágenes de plantillas."""
    
    def __init__(self, cache_dir: Optional[Path] = None, max_size_mb: int = 500, max_age_days: int = 30):
        """
        Inicializa el sistema de caché.
        
        Args:
            cache_dir: Directorio para el caché. Por defecto: ~/.cache/memescript-py/
            max_size_mb: Tamaño máximo del caché en MB
            max_age_days: Edad máxima de los archivos en días
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "memescript-py"
        
        self.cache_dir = cache_dir
        self.images_dir = cache_dir / "images"
        self.metadata_file = cache_dir / "metadata.json"
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_age = timedelta(days=max_age_days)
        
        # Crear directorios si no existen
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar metadatos
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict[str, Any]:
        """Carga los metadatos del caché desde el archivo JSON."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando metadatos del caché: {e}")
        return {"templates": {}, "access_times": {}, "size": 0}
    
    def _save_metadata(self):
        """Guarda los metadatos del caché en el archivo JSON."""
        try:
            # Guardar en archivo temporal y renombrar para evitar corrupción
            temp_file = self.metadata_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
            temp_file.replace(self.metadata_file)
        except Exception as e:
            logger.error(f"Error guardando metadatos del caché: {e}")
    
    def _get_cache_key(self, template_id: str) -> str:
        """Genera una clave única para el template."""
        return hashlib.md5(template_id.encode()).hexdigest()
    
    def _get_image_path(self, template_id: str) -> Path:
        """Obtiene la ruta donde se debería almacenar la imagen."""
        cache_key = self._get_cache_key(template_id)
        return self.images_dir / f"{cache_key}.png"
    
    def get(self, template_id: str) -> Optional[Path]:
        """
        Obtiene la ruta de una imagen del caché si existe y es válida.
        
        Args:
            template_id: ID del template de Imgflip
            
        Returns:
            Path al archivo de imagen o None si no está en caché
        """
        cache_key = self._get_cache_key(template_id)
        metadata = self.metadata["templates"].get(cache_key)
        
        if not metadata:
            return None
        
        # Verificar si el archivo existe
        image_path = self._get_image_path(template_id)
        if not image_path.exists():
            # Limpiar metadatos huérfanos
            del self.metadata["templates"][cache_key]
            self.metadata["size"] -= metadata.get("size", 0)
            self._save_metadata()
            return None
        
        # Verificar edad
        cache_time = datetime.fromisoformat(metadata["cached_at"])
        if datetime.now() - cache_time > self.max_age:
            # Archivo expirado
            self._remove(cache_key)
            return None
        
        # Actualizar tiempo de acceso para LRU
        self.metadata["access_times"][cache_key] = time.time()
        self._save_metadata()
        
        return image_path
    
    def put(self, template_id: str, image_data: bytes, template_info: Dict[str, Any]) -> Path:
        """
        Almacena una imagen en el caché.
        
        Args:
            template_id: ID del template
            image_data: Datos binarios de la imagen
            template_info: Información adicional del template (nombre, dimensiones, etc.)
            
        Returns:
            Path al archivo guardado
        """
        cache_key = self._get_cache_key(template_id)
        image_path = self._get_image_path(template_id)
        file_size = len(image_data)
        
        # Verificar espacio y hacer limpieza si es necesario
        self._ensure_space(file_size)
        
        # Guardar la imagen
        try:
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            # Actualizar metadatos
            self.metadata["templates"][cache_key] = {
                "template_id": template_id,
                "name": template_info.get("name", "Unknown"),
                "url": template_info.get("url", ""),
                "width": template_info.get("width", 0),
                "height": template_info.get("height", 0),
                "size": file_size,
                "cached_at": datetime.now().isoformat()
            }
            self.metadata["access_times"][cache_key] = time.time()
            self.metadata["size"] = self.metadata.get("size", 0) + file_size
            
            self._save_metadata()
            logger.info(f"Imagen {template_id} guardada en caché: {image_path}")
            
        except Exception as e:
            logger.error(f"Error guardando imagen en caché: {e}")
            if image_path.exists():
                image_path.unlink()
            raise
        
        return image_path
    
    def _remove(self, cache_key: str):
        """Elimina un elemento del caché."""
        if cache_key in self.metadata["templates"]:
            size = self.metadata["templates"][cache_key].get("size", 0)
            self.metadata["size"] -= size
            del self.metadata["templates"][cache_key]
        
        if cache_key in self.metadata["access_times"]:
            del self.metadata["access_times"][cache_key]
        
        # Eliminar archivo físico
        image_path = self.images_dir / f"{cache_key}.png"
        if image_path.exists():
            image_path.unlink()
    
    def _ensure_space(self, needed_bytes: int):
        """
        Asegura que haya suficiente espacio en el caché, eliminando elementos
        usando política LRU (Least Recently Used).
        """
        current_size = self.metadata.get("size", 0)
        
        # Si hay suficiente espacio, no hacer nada
        if current_size + needed_bytes <= self.max_size_bytes:
            return
        
        # Ordenar por tiempo de acceso (los más antiguos primero)
        items = sorted(
            self.metadata["access_times"].items(),
            key=lambda x: x[1]
        )
        
        # Eliminar hasta tener espacio suficiente
        for cache_key, _ in items:
            if current_size + needed_bytes <= self.max_size_bytes:
                break
            
            item_size = self.metadata["templates"][cache_key].get("size", 0)
            self._remove(cache_key)
            current_size -= item_size
            logger.info(f"Eliminado del caché LRU: {cache_key}")
        
        self._save_metadata()
    
    def clear(self):
        """Limpia todo el caché."""
        for file in self.images_dir.glob("*.png"):
            file.unlink()
        
        self.metadata = {"templates": {}, "access_times": {}, "size": 0}
        self._save_metadata()
        logger.info("Caché limpiado completamente")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché."""
        total_images = len(self.metadata["templates"])
        total_size_mb = self.metadata.get("size", 0) / (1024 * 1024)
        
        return {
            "total_images": total_images,
            "total_size_mb": round(total_size_mb, 2),
            "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
            "usage_percent": round((total_size_mb / (self.max_size_bytes / (1024 * 1024))) * 100, 1),
            "cache_dir": str(self.cache_dir)
        }