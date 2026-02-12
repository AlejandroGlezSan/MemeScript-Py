# src/api_client.py
"""
Módulo API: funciones para interactuar con Imgflip.
Separa la lógica de red del GUI para facilitar testing.
"""

import random
from typing import Optional

import requests


IMGFLIP_MEMES_URL = "https://api.imgflip.com/get_memes"
DEFAULT_TIMEOUT = 10  # segundos


def get_random_meme_url(timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """
    Llama a la API pública de Imgflip y devuelve la URL de una plantilla aleatoria.
    Retorna None si no se pudo obtener una URL válida.

    Parámetros:
    - timeout: tiempo máximo de espera para la petición (segundos).
    """
    try:
        resp = requests.get(IMGFLIP_MEMES_URL, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            return None
        memes = data.get("data", {}).get("memes", [])
        if not memes:
            return None
        chosen = random.choice(memes)
        return chosen.get("url")
    except Exception:
        # No propagar excepción para que el llamador (GUI) la maneje y muestre mensaje
        return None
