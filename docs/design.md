# Diseño técnico — MemeScript-Py

## Resumen
MemeScript-Py es una aplicación de escritorio en Python que genera memes automáticos combinando plantillas públicas de Imgflip con un pool local de frases. Está diseñada para ser modular, testeable y tolerante a fallos de red y archivos grandes.

## Objetivos de diseño
- **Modularidad:** separar API, gestión de texto, renderizado y GUI en módulos independientes.
- **Robustez:** timeouts, reintentos, límites de tamaño y manejo de excepciones.
- **UX responsiva:** operaciones de red y procesamiento en hilos o tareas asíncronas para no bloquear la GUI.
- **Portabilidad:** dependencias mínimas y uso de CustomTkinter para apariencia moderna.
- **Extensibilidad:** fácil incorporación de cache, soporte offline y exportación futura.

---

## Estructura propuesta
memeScript-py/
├── README.md
├── .gitignore
├── requirements.txt
├── src/
│   ├── main.py            # GUI principal
│   ├── api_client.py      # Lógica de consumo de Imgflip (get_random_meme_url, session/retries)
│   ├── text_pool.py       # Carga y gestión de frases (assets/phrases.json)
│   ├── renderer.py        # Renderizado de texto sobre imágenes (render_meme)
│   ├── cache.py           # (opcional) cache local de plantillas
│   └── assets/
│       └── phrases.json
├── tests/
│   ├── test_api_client.py
│   └── test_renderer.py
└── docs/
└── design.md

---

## Módulos y responsabilidades

### api_client.py
- **Responsabilidad:** obtener lista de plantillas desde `https://api.imgflip.com/get_memes` y devolver una URL aleatoria o metadatos.
- **Requisitos:** usar `requests.Session` con `HTTPAdapter` + `Retry` (urllib3) para reintentos; exponer parámetros `timeout` y `max_retries`.
- **Errores manejados:** HTTP errors, JSON decode errors, respuesta sin `success`, lista vacía.
- **Salida:** `dict` con `id`, `name`, `url`, `width`, `height` o `None` en fallo.

### text_pool.py
- **Responsabilidad:** cargar `assets/phrases.json`, exponer `get_random_phrase()` y funciones CRUD básicas (añadir, eliminar, validar).
- **Formato:** JSON simple: lista de strings.
- **Validaciones:** strings no vacíos; límite máximo por frase (ej. 200 chars).
- **Persistencia:** escritura segura (temp file + rename) para evitar corrupción.

### renderer.py
- **Responsabilidad:** componer texto superior/inferior sobre una imagen PIL y devolver `PIL.Image`.
- **Función principal:** `render_meme(image: Image, top_text: str, bottom_text: str, font_path: Optional[str]=None, font_size: Optional[int]=None) -> Image`
- **Características de renderizado:**
  - Escalado de imagen para evitar OOM (si imagen > X px, reducir manteniendo aspecto).
  - Texto centrado horizontalmente; ajuste de tamaño de fuente para que quepa en ancho con `textwrap`.
  - Contorno (stroke) para legibilidad: usar `ImageDraw.text(..., stroke_width=n, stroke_fill="black")` si Pillow lo soporta; fallback a dibujar múltiples pasadas del texto desplazado.
  - Sombra opcional y padding.
  - Soporte para múltiples líneas y separación entre líneas.
- **Optimización:** dibujar en una copia RGBA; evitar conversiones innecesarias.

### main.py (GUI)
- **Responsabilidad:** UI con CustomTkinter, interacción del usuario, hilos para operaciones de red y render.
- **Buenas prácticas:**
  - Todas las llamadas de red y procesamiento en `threading.Thread` o `concurrent.futures.ThreadPoolExecutor`.
  - Actualizaciones de widgets con `after()` para ejecutar en hilo principal.
  - Indicadores de estado y manejo de errores mostrados al usuario.
  - Botones deshabilitados durante operaciones largas.
  - Límite de tamaño de imagen y barra de progreso (si se desea).

### cache.py (opcional)
- **Responsabilidad:** cache local de plantillas descargadas (por id) en `~/.cache/memescript-py/` o `src/assets/cache/`.
- **Política:** LRU simple; límite por número de imágenes o tamaño total en MB.
- **Beneficio:** reduce ancho de banda y latencia; permite modo offline parcial.

---

## Flujo de datos (alto nivel)
1. Usuario pulsa "Generar" o "Probar conexión".
2. GUI lanza hilo que llama a `api_client.get_random_meme()` (o `get_random_meme_url()`).
3. Si hay URL, se descarga la imagen con `requests` (stream, timeout).
4. Se valida tamaño (Content-Length o len(content)).
5. Se crea `PIL.Image` y se pasa a `renderer.render_meme(...)` junto con frases de `text_pool.get_random_phrase()`.
6. Resultado se convierte a `ImageTk.PhotoImage` y se muestra en GUI mediante `after()`.

---

## Manejo de errores y límites
- **Timeouts:** 5–15s configurable; reintentos 2–3 con backoff exponencial.
- **Tamaño máximo:** rechazar imágenes > 10 MB o dimensiones > 5000 px; ofrecer reducción progresiva.
- **Excepciones:** capturar y mostrar mensajes legibles; loguear stacktrace en archivo `app.log`.
- **Fallbacks:** si Imgflip falla, usar plantilla local (si existe) o mensaje de error amigable.

---

## Renderizado de texto: algoritmo propuesto
1. **Preparación**
   - Convertir imagen a RGBA.
   - Calcular área útil (anchura - 2*padding).
2. **Fuente**
   - Preferir fuente embebida (p.ej. `assets/fonts/impact.ttf`) si está disponible.
   - Si no, usar `ImageFont.truetype` con fallback a `ImageFont.load_default()`.
3. **Ajuste de tamaño**
   - Empezar con `font_size` base (ej. 48).
   - Reducir iterativamente hasta que el texto envuelto quepa en el ancho permitido.
4. **Dibujo del contorno**
   - Si Pillow >= 8.2: usar `stroke_width` y `stroke_fill`.
   - Si no: dibujar el texto 8 veces desplazado (±1 px) en color de contorno y luego el texto principal.
5. **Posicionamiento**
   - **Top text:** y = padding
   - **Bottom text:** y = image_height - text_height - padding
   - Centrar horizontalmente por cada línea.
6. **Salida**
   - Retornar imagen compuesta.

---

## Pruebas recomendadas
- **Unit tests:**
  - `test_api_client.py`: mockear `requests.Session.get` para simular respuestas válidas, errores HTTP y JSON malformado.
  - `test_renderer.py`: comprobar que `render_meme` devuelve una imagen y que el texto aparece en píxeles (p. ej. detectar cambios en histogram).
  - `test_text_pool.py`: validar carga y persistencia de frases.
- **Integration tests:** test que simule descarga real (opcional, marcado como `integration`).

---

## Consideraciones de seguridad y privacidad
- No almacenar credenciales en repositorio.
- Validar y sanear cualquier entrada de usuario que se use para nombres de archivo.
- Evitar subir assets grandes al repositorio; usar `.gitignore` para excluirlos si procede.

---

## Próximos pasos sugeridos
1. Implementar `renderer.py` con `render_meme(...)`.
2. Mejorar `api_client.py` para usar `requests.Session` + `Retry`.
3. Añadir logging estructurado y archivo de logs.
4. Crear tests unitarios básicos y CI (GitHub Actions).

