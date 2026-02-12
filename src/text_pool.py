# src/text_pool.py
"""
Gestión del pool de frases.
Lectura simple desde JSON; interfaz para obtener frases aleatorias.
"""

import json
import random
from pathlib import Path
from typing import List

PHRASES_PATH = Path(__file__).parent / "assets" / "phrases.json"


def load_phrases(path: Path = PHRASES_PATH) -> List[str]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return [str(x) for x in data]
    return []


def get_random_phrase() -> str:
    phrases = load_phrases()
    if not phrases:
        return "Texto de ejemplo"
    return random.choice(phrases)
