# src/text_pool.py
"""
Gestión del pool de frases con operaciones CRUD completas.
"""

import json
import random
import logging
import shutil
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

PHRASES_PATH = Path(__file__).parent / "assets" / "phrases.json"
MAX_PHRASE_LENGTH = 200  # Caracteres máximos por frase

class TextPoolError(Exception):
    """Excepción personalizada para errores del pool de texto."""
    pass

def load_phrases(path: Path = PHRASES_PATH) -> List[str]:
    """
    Carga las frases desde el archivo JSON.
    
    Args:
        path: Ruta al archivo de frases
        
    Returns:
        Lista de frases
    """
    if not path.exists():
        logger.warning(f"Archivo de frases no encontrado: {path}")
        return []
    
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        
        if isinstance(data, list):
            # Validar y limpiar frases
            phrases = []
            for item in data:
                if isinstance(item, str):
                    # Truncar frases muy largas
                    if len(item) > MAX_PHRASE_LENGTH:
                        logger.warning(f"Frase truncada (>{MAX_PHRASE_LENGTH} chars): {item[:50]}...")
                        item = item[:MAX_PHRASE_LENGTH]
                    phrases.append(item)
                else:
                    phrases.append(str(item))
            
            logger.info(f"Cargadas {len(phrases)} frases de {path}")
            return phrases
        else:
            logger.error(f"Formato inválido en {path}: se esperaba una lista")
            return []
            
    except json.JSONDecodeError as e:
        logger.error(f"Error decodificando JSON de {path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado cargando frases: {e}")
        return []

def save_phrases(phrases: List[str], path: Path = PHRASES_PATH) -> bool:
    """
    Guarda las frases en el archivo JSON de forma segura.
    
    Args:
        phrases: Lista de frases a guardar
        path: Ruta al archivo de frases
        
    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    # Validar frases
    validated_phrases = []
    for p in phrases:
        if not isinstance(p, str):
            p = str(p)
        if len(p) > MAX_PHRASE_LENGTH:
            logger.warning(f"Frase truncada al guardar: {p[:50]}...")
            p = p[:MAX_PHRASE_LENGTH]
        if p.strip():  # Solo guardar frases no vacías
            validated_phrases.append(p.strip())
    
    # Crear directorio si no existe
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardar usando archivo temporal + renombrado
    temp_path = path.with_suffix('.tmp')
    try:
        with open(temp_path, "w", encoding="utf-8") as fh:
            json.dump(validated_phrases, fh, indent=2, ensure_ascii=False)
        
        # Renombrar archivo temporal al destino
        shutil.move(str(temp_path), str(path))
        
        logger.info(f"Guardadas {len(validated_phrases)} frases en {path}")
        return True
        
    except Exception as e:
        logger.error(f"Error guardando frases en {path}: {e}")
        # Limpiar archivo temporal si existe
        if temp_path.exists():
            temp_path.unlink()
        return False

def get_random_phrase() -> str:
    """
    Obtiene una frase aleatoria del pool.
    
    Returns:
        Frase aleatoria o texto por defecto si no hay frases
    """
    phrases = load_phrases()
    if not phrases:
        logger.info("Pool de frases vacío, usando texto por defecto")
        return "Texto de ejemplo"
    
    return random.choice(phrases)

def add_phrase(phrase: str) -> bool:
    """
    Añade una nueva frase al pool.
    
    Args:
        phrase: La frase a añadir
        
    Returns:
        True si se añadió correctamente
    """
    if not phrase or not phrase.strip():
        raise TextPoolError("La frase no puede estar vacía")
    
    if len(phrase) > MAX_PHRASE_LENGTH:
        raise TextPoolError(f"La frase no puede tener más de {MAX_PHRASE_LENGTH} caracteres")
    
    phrases = load_phrases()
    phrases.append(phrase.strip())
    
    return save_phrases(phrases)

def update_phrase(index: int, new_phrase: str) -> bool:
    """
    Actualiza una frase existente.
    
    Args:
        index: Índice de la frase a actualizar
        new_phrase: Nuevo texto de la frase
        
    Returns:
        True si se actualizó correctamente
    """
    if not new_phrase or not new_phrase.strip():
        raise TextPoolError("La frase no puede estar vacía")
    
    if len(new_phrase) > MAX_PHRASE_LENGTH:
        raise TextPoolError(f"La frase no puede tener más de {MAX_PHRASE_LENGTH} caracteres")
    
    phrases = load_phrases()
    
    if index < 0 or index >= len(phrases):
        raise TextPoolError(f"Índice {index} fuera de rango")
    
    phrases[index] = new_phrase.strip()
    return save_phrases(phrases)

def delete_phrase(index: int) -> bool:
    """
    Elimina una frase del pool.
    
    Args:
        index: Índice de la frase a eliminar
        
    Returns:
        True si se eliminó correctamente
    """
    phrases = load_phrases()
    
    if index < 0 or index >= len(phrases):
        raise TextPoolError(f"Índice {index} fuera de rango")
    
    deleted = phrases.pop(index)
    logger.info(f"Frase eliminada: {deleted[:50]}...")
    
    return save_phrases(phrases)

def get_phrases_count() -> int:
    """
    Obtiene el número de frases en el pool.
    
    Returns:
        Número de frases
    """
    return len(load_phrases())