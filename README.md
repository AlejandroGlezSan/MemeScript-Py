# MemeScript-Py v2.0 🎭

**MemeScript-Py** es una aplicación de escritorio profesional para generar memes automáticos, combinando plantillas de Imgflip con un pool local de frases. Desarrollada en Python con CustomTkinter.

## ✨ Características Principales

- 🖼️ **Selección de plantillas**: Elige entre más de 100 plantillas de Imgflip o usa una aleatoria
- 📝 **Gestor de frases**: Añade, edita y elimina frases desde la interfaz gráfica
- 💾 **Sistema de caché**: Las imágenes se guardan localmente para acceso offline y mayor velocidad
- 🎨 **Personalización**: Selecciona fuente, tamaño de texto y estilo (con/sin sombra)
- 🔄 **Reintentos automáticos**: La API maneja timeouts y errores de red gracefulmente
- 📁 **Exportación**: Guarda tus memes en la carpeta Pictures/Memescript/
- 🌓 **Tema oscuro/claro**: Se adapta a la configuración de tu sistema

## 🚀 Instalación Rápida

1. Clonar el repositorio:
   git clone https://github.com/AlejandroGlezSan/MemeScript-Py
   cd memescript-py

2. Crear y activar entorno virtual:
   python -m venv .venv
   source .venv/bin/activate  (Linux/macOS)
   .venv\Scripts\activate      (Windows)

3. Instalar dependencias:
   pip install -r requirements.txt

4. Ejecutar la aplicación:
   python -m src.main

## 📦 Estructura del Proyecto

memescript-py/
├── src/
│   ├── main.py              (GUI principal)
│   ├── api_client.py        (Cliente API Imgflip con caché)
│   ├── text_pool.py         (Gestor de frases CRUD)
│   ├── renderer.py          (Motor de renderizado con Pillow)
│   ├── cache.py             (Sistema de caché LRU)
│   └── assets/
│       └── phrases.json     (Pool de frases por defecto)
├── tests/
│   ├── test_api_client.py   (Tests de API)
│   ├── test_text_pool.py    (Tests de gestión de frases)
│   └── test_renderer.py     (Tests de renderizado)
├── docs/
│   └── design.md            (Documentación de diseño)
├── requirements.txt         (Dependencias)
└── README.md                (Este archivo)

## 🎯 Uso de la Aplicación

1. **Inicio**: La aplicación carga automáticamente las plantillas y fuentes disponibles
2. **Selecciona plantilla**: Elige una específica o usa "Aleatoria"
3. **Introduce textos**: 
   - Escribe manualmente texto superior e inferior
   - O activa "Frase aleatoria" y elige posición
4. **Personaliza**: Ajusta fuente, tamaño y activa sombra si lo deseas
5. **Genera**: Haz clic en "Generar Meme" y espera unos segundos
6. **Guarda**: Usa "Descargar Meme" para guardar en tu disco

## 🧪 Tests y Calidad de Código

Ejecutar todos los tests:
pytest tests/ -v

Con cobertura:
pytest tests/ --cov=src --cov-report=html

Linting:
flake8 src/

Type checking:
mypy src/

## 📊 Sistema de Caché

Las imágenes se almacenan en ~/.cache/memescript-py/ con política LRU:
- Límite por defecto: 500 MB
- Expiración: 30 días
- Limpieza automática cuando se excede el tamaño

## 🛠️ Desarrollo y Contribución

1. Fork el proyecto
2. Crea tu rama de características (git checkout -b feature/amazing-feature)
3. Ejecuta tests y linting antes de commit
4. Commit tus cambios (git commit -m 'Add amazing feature')
5. Push a la rama (git push origin feature/amazing-feature)
6. Abre un Pull Request

## 📝 Notas Técnicas

- Python 3.8+ requerido
- Las fuentes TrueType (Impact, Arial, etc.) deben estar instaladas en el sistema
- En Linux: sudo apt install ttf-mscorefonts-installer
- En macOS: Las fuentes vienen preinstaladas
- En Windows: Vienen con el sistema

## 👨‍💻 Autor

Desarrollado como proyecto de portfolio. Demuestra:
- Programación orientada a objetos
- Manejo de APIs y caché
- Interfaz gráfica moderna
- Tests unitarios y de integración
- Documentación técnica
- Buenas prácticas de Python

## 📄 Licencia

MIT License - uso libre para fines educativos y de portfolio.

---

**Hecho con ☕ y ❤️ para la comunidad de memes**
