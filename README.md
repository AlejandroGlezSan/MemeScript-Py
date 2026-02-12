# MemeScript-Py

**MemeScript-Py** es una aplicación de escritorio que genera memes automáticos combinando plantillas públicas de Imgflip con un pool local de frases.

## Características
- Interfaz gráfica con **CustomTkinter**.
- Descarga de plantillas desde la API pública de Imgflip.
- Pool local de frases en `src/assets/phrases.json`.
- Motor de render (Pillow) para componer texto con contorno y centrarlo.

## Estructura
memeScript-py/
├── README.md
├── .gitignore
├── requirements.txt
├── src/
│   ├── main.py
│   ├── api_client.py
│   ├── text_pool.py
│   ├── renderer.py
│   └── assets/
│       └── phrases.json
├── tests/
│   ├── test_api_client.py
│   └── test_text_pool.py
└── docs/
    └── design.md


## Instalación (entorno virtual recomendado)
```bash
python -m venv .venv
source .venv/bin/activate    # Linux / macOS
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```