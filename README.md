# MemeScript-Py

**MemeScript-Py** es una aplicación de escritorio desarrollada en Python que genera memes automáticos combinando plantillas públicas de Imgflip con un pool local de frases.



## 🚀 Características Principales

* **Interfaz Gráfica (GUI):** Construida con `CustomTkinter` para una apariencia moderna y responsiva.
* **API Integrada:** Descarga automática de plantillas desde la API pública de Imgflip.
* **Renderizado Inteligente (Pillow):** Algoritmo propio que ajusta el tamaño de la fuente automáticamente para asegurar que el texto **nunca** se salga de los bordes de la imagen, sin importar la longitud de la frase.
* **Pool de Frases Personalizable:** Motor de texto multilínea con contorno negro (stroke) para máxima legibilidad.
* **Descarga Local:** Guarda tus creaciones directamente en tu ordenador con un timestamp único.

## 🛠️ Estructura del Proyecto

memeScript-py/
├── README.md
├── requirements.txt
├── src/
│   ├── main.py          # Punto de entrada y GUI
│   ├── api_client.py    # Conexión con Imgflip
│   ├── renderer.py      # Lógica de manipulación de imágenes (Pillow)
│   ├── text_pool.py     # Gestión de frases
│   └── assets/
│       └── phrases.json # Base de datos local de frases
└── tests/               # Pruebas unitarias

💻 Instalación y Uso
Se recomienda utilizar un entorno virtual para gestionar las dependencias.

1. Clonar el repositorio
git clone https://github.com/AlejandroGlezSan/MemeScript-Py
cd memeScript-py

3. Configurar entorno virtual e instalar dependencias

# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

3. Ejecutar la aplicación

python -m src.main

🛠️ Tecnologías Utilizadas
Python 3.10+

CustomTkinter: Interfaz gráfica.

Pillow (PIL): Procesamiento y renderizado de imágenes.

Requests: Consumo de APIs.

🤝 Contribuciones
¡Las contribuciones son bienvenidas! Si tienes ideas para nuevos algoritmos de renderizado o frases graciosas, por favor abre un Issue o envía un Pull Request.
