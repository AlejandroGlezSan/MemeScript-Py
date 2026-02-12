# src/main.py
"""
MemeScript-Py - GUI principal con generación de memes integrada.

Instrucciones rápidas para probar:
1. Crear y activar un entorno virtual.
2. Instalar dependencias: pip install -r requirements.txt
3. Ejecutar desde la raíz del repositorio:
   python -m src.main
   (o) python src/main.py  -- el script ajusta sys.path para permitir imports.
4. En la ventana: usar "Probar conexión Imgflip" para verificar API,
   luego "Generar meme" para descargar plantilla, renderizar y mostrar.

Notas:
- Se usa customtkinter. Para evitar la advertencia sobre HighDPI, las imágenes
  se envuelven en ctk.CTkImage antes de asignarlas a widgets y se mantiene una
  referencia en la instancia para evitar GC.
- Comportamiento de texto: ahora **solo una frase** por meme; la posición
  (arriba/abajo) se elige aleatoriamente. Si el usuario escribe "arriba|abajo"
  en el campo personalizado, se respetan ambas frases.
"""

from __future__ import annotations

import io
import logging
import threading
import traceback
import sys
import random
from typing import Optional, Tuple
from pathlib import Path

import customtkinter as ctk
import requests
from PIL import Image

# Asegurar que la raíz del proyecto esté en sys.path para imports consistentes
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Importar módulos del paquete src (funciona tanto con `python -m src.main` como con `python src/main.py`)
try:
    from src.api_client import get_random_meme_url
    from src.renderer import render_meme
    from src.text_pool import get_random_phrase
except Exception:
    # Fallback si se ejecuta en un entorno donde `src` no es tratado como paquete
    from api_client import get_random_meme_url  # type: ignore
    from renderer import render_meme  # type: ignore
    from text_pool import get_random_phrase  # type: ignore

# Configuración visual básica de CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Logging básico
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("memeScript")


class MemeApp(ctk.CTk):
    """Aplicación principal de MemeScript-Py."""

    def __init__(self, width: int = 1000, height: int = 700):
        super().__init__()
        self.title("MemeScript-Py")
        self.geometry(f"{width}x{height}")
        self.minsize(700, 500)

        # --- Layout frames ---
        self.frame_left = ctk.CTkFrame(master=self, width=320)
        self.frame_left.pack(side="left", fill="y", padx=12, pady=12)

        self.frame_right = ctk.CTkFrame(master=self)
        self.frame_right.pack(side="right", fill="both", expand=True, padx=12, pady=12)

        # --- Left: controles ---
        self.lbl_status = ctk.CTkLabel(master=self.frame_left, text="Estado: listo", wraplength=280, justify="left")
        self.lbl_status.pack(pady=(6, 12), padx=8)

        self.btn_test_api = ctk.CTkButton(master=self.frame_left, text="Probar conexión Imgflip", command=self._on_test_api)
        self.btn_test_api.pack(pady=(4, 8), padx=8, fill="x")

        self.btn_generate = ctk.CTkButton(master=self.frame_left, text="Generar meme", command=self._on_generate_meme)
        self.btn_generate.pack(pady=(4, 8), padx=8, fill="x")

        # Opciones simples: usar frases aleatorias o texto personalizado
        self.use_random_var = ctk.BooleanVar(value=True)
        self.chk_random = ctk.CTkCheckBox(master=self.frame_left, text="Usar frases aleatorias", variable=self.use_random_var)
        self.chk_random.pack(pady=(8, 8), padx=8, anchor="w")

        self.lbl_custom = ctk.CTkLabel(master=self.frame_left, text="Texto personalizado (opcional):")
        self.lbl_custom.pack(pady=(8, 4), padx=8, anchor="w")
        self.entry_custom = ctk.CTkEntry(master=self.frame_left, placeholder_text="Escribe texto para arriba|abajo (separa con |)")
        self.entry_custom.pack(pady=(0, 8), padx=8, fill="x")

        # Right: vista previa de imagen
        self.preview_frame = ctk.CTkFrame(master=self.frame_right)
        self.preview_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.canvas = ctk.CTkLabel(master=self.preview_frame, text="Aquí se mostrará la plantilla", anchor="center")
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)

        # Guardar referencia de la CTkImage para evitar GC y advertencias HighDPI
        self._current_ctk_image: Optional[ctk.CTkImage] = None

    # --- UI callbacks ---
    def _on_test_api(self):
        """Callback del botón: lanza la prueba en hilo para no bloquear la GUI."""
        self._set_status("Comprobando conexión a Imgflip...", info=True)
        self._set_buttons_state(False)
        thread = threading.Thread(target=self._test_api_thread, daemon=True)
        thread.start()

    def _test_api_thread(self):
        """Hilo que prueba la conexión a Imgflip y descarga una plantilla de ejemplo."""
        try:
            meme_url = get_random_meme_url()
            if not meme_url:
                raise RuntimeError("No se obtuvo URL de plantilla desde Imgflip.")

            # Descargar imagen en memoria con timeout y manejo de errores
            resp = requests.get(meme_url, timeout=12, stream=True)
            resp.raise_for_status()

            # Limitar tamaño máximo en memoria (ejemplo: 12 MB)
            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > 12 * 1024 * 1024:
                raise RuntimeError("Imagen demasiado grande (>12MB).")

            img_bytes = resp.content
            image = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

            # Redimensionar para vista previa manteniendo aspecto
            max_w, max_h = 900, 900
            image.thumbnail((max_w, max_h), Image.LANCZOS)

            # Crear CTkImage para evitar advertencias HighDPI y permitir escalado
            ctk_image = ctk.CTkImage(light_image=image, size=image.size)
            self._current_ctk_image = ctk_image

            # Actualizar UI en hilo principal
            self.after(0, lambda: self._show_ctk_image(ctk_image))
            self.after(0, lambda: self._set_status("Plantilla descargada correctamente.", success=True))
            logger.info("Prueba API exitosa: %s", meme_url)
        except Exception as e:
            tb = traceback.format_exc()
            logger.exception("Error en prueba API")
            self.after(0, lambda: self._set_status(f"Error prueba API: {str(e)}", error=True))
            print(tb)
        finally:
            self.after(0, lambda: self._set_buttons_state(True))

    def _on_generate_meme(self):
        """Callback para generar meme: descarga plantilla, renderiza y muestra."""
        self._set_status("Generando meme...", info=True)
        self._set_buttons_state(False)
        thread = threading.Thread(target=self._generate_meme_thread, daemon=True)
        thread.start()

    def _generate_meme_thread(self):
        """Hilo que realiza la descarga de plantilla, render y actualización UI."""
        try:
            meme_url = get_random_meme_url()
            if not meme_url:
                raise RuntimeError("No se obtuvo URL de plantilla desde Imgflip.")

            # Descargar imagen en memoria con timeout y manejo de errores
            resp = requests.get(meme_url, timeout=15, stream=True)
            resp.raise_for_status()

            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > 12 * 1024 * 1024:
                raise RuntimeError("Imagen demasiado grande (>12MB).")

            img_bytes = resp.content
            image = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

            # Preparar textos: ahora solo UNA frase por meme
            top_text = ""
            bottom_text = ""

            if self.use_random_var.get():
                # Obtener una sola frase del pool
                phrase = get_random_phrase()
                # Elegir aleatoriamente si va arriba o abajo
                position = random.choice(["top", "bottom"])
                if position == "top":
                    top_text = phrase
                else:
                    bottom_text = phrase
                # Actualizar estado para informar la posición elegida
                self.after(0, lambda pos=position: self._set_status(f"Generando meme (frase en {pos}).", info=True))
            else:
                # Texto personalizado: si contiene '|', respetar top|bottom
                custom = (self.entry_custom.get() or "").strip()
                if "|" in custom:
                    top_text, bottom_text = [s.strip() for s in custom.split("|", 1)]
                else:
                    # Si solo hay un texto personalizado, colocarlo en posición aleatoria
                    phrase = custom
                    if phrase:
                        position = random.choice(["top", "bottom"])
                        if position == "top":
                            top_text = phrase
                        else:
                            bottom_text = phrase
                        self.after(0, lambda pos=position: self._set_status(f"Generando meme (texto personalizado en {pos}).", info=True))
                    else:
                        # Si no hay texto personalizado, dejar ambos vacíos
                        top_text = ""
                        bottom_text = ""

            # Renderizar meme (usar parámetros compatibles con renderer actualizado)
            rendered = render_meme(
                image,
                top_text=top_text,
                bottom_text=bottom_text,
                font_size=None,  # dejar que renderer calcule según base_font_ratio
                base_font_ratio=0.06,
                max_text_height_ratio=0.35,
                padding_ratio=0.02,
                stroke_width_ratio=0.06,
            )

            # Redimensionar para vista previa si es muy grande
            max_w, max_h = 900, 900
            rendered.thumbnail((max_w, max_h), Image.LANCZOS)

            # Crear CTkImage para mostrar en la GUI (evita advertencias HighDPI)
            ctk_image = ctk.CTkImage(light_image=rendered, size=rendered.size)
            self._current_ctk_image = ctk_image

            self.after(0, lambda: self._show_ctk_image(ctk_image))
            self.after(0, lambda: self._set_status("Meme generado correctamente.", success=True))
            logger.info("Meme generado desde: %s", meme_url)
        except Exception as e:
            tb = traceback.format_exc()
            logger.exception("Error generando meme")
            self.after(0, lambda: self._set_status(f"Error generando meme: {str(e)}", error=True))
            print(tb)
        finally:
            self.after(0, lambda: self._set_buttons_state(True))

    def _show_ctk_image(self, ctk_image: ctk.CTkImage):
        """Muestra la CTkImage en el panel derecho."""
        self.canvas.configure(image=ctk_image, text="")

    def _set_buttons_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.btn_test_api.configure(state=state)
        self.btn_generate.configure(state=state)
        self.entry_custom.configure(state=state)

    def _set_status(self, message: str, info: bool = False, success: bool = False, error: bool = False):
        """Actualiza la etiqueta de estado con estilo simple."""
        prefix = ""
        if success:
            prefix = "OK: "
        elif error:
            prefix = "ERROR: "
        elif info:
            prefix = "INFO: "
        self.lbl_status.configure(text=f"Estado: {prefix}{message}")

    def run(self):
        self.mainloop()


def _print_startup_instructions():
    print("\nMemeScript-Py - Instrucciones rápidas de prueba")
    print("1) Asegúrate de tener un entorno virtual y dependencias instaladas:")
    print("   python -m venv .venv && source .venv/bin/activate  # o .venv\\Scripts\\activate en Windows")
    print("   pip install -r requirements.txt")
    print("2) Ejecuta desde la raíz del repo: python -m src.main  (o python src/main.py)")
    print("3) En la ventana: pulsa 'Probar conexión Imgflip' y luego 'Generar meme'.")
    print("4) Si algo falla, copia el texto del estado y pégalo como feedback.\n")


if __name__ == "__main__":
    _print_startup_instructions()
    app = MemeApp()
    app.run()
