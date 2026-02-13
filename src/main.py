from __future__ import annotations

import io
import logging
import threading
import random
import os
from datetime import datetime
from typing import Optional, Tuple

import customtkinter as ctk
import requests
from PIL import Image

from api_client import get_random_meme_url
from renderer import render_meme
from text_pool import get_random_phrase

# Configuración de constantes
PREVIEW_SIZE = (800, 600)
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class MemeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MemeScript-Py (Portfolio Version)")
        self.geometry("1100x800")
        
        self.last_rendered_meme: Optional[Image.Image] = None

        # --- Layout ---
        self.frame_left = ctk.CTkFrame(self, width=320)
        self.frame_left.pack(side="left", fill="y", padx=15, pady=15)

        self.lbl_status = ctk.CTkLabel(self.frame_left, text="Estado: Listo para crear", wraplength=250)
        self.lbl_status.pack(pady=20)

        self.btn_generate = ctk.CTkButton(self.frame_left, text="Generar Meme", command=self._on_generate_meme)
        self.btn_generate.pack(pady=10, fill="x", padx=20)

        self.btn_download = ctk.CTkButton(self.frame_left, text="Descargar Meme", command=self._on_download, state="disabled", fg_color="#2c7a2c")
        self.btn_download.pack(pady=10, fill="x", padx=20)

        self.use_random_var = ctk.BooleanVar(value=True)
        self.chk_random = ctk.CTkCheckBox(self.frame_left, text="Frase Aleatoria", variable=self.use_random_var)
        self.chk_random.pack(pady=15)

        self.entry_custom = ctk.CTkEntry(self.frame_left, placeholder_text="Texto arriba|abajo")
        self.entry_custom.pack(pady=10, fill="x", padx=20)

        # --- Vista Previa ---
        self.canvas_frame = ctk.CTkFrame(self, fg_color="black")
        self.canvas_frame.pack(side="right", fill="both", expand=True, padx=15, pady=15)
        
        self.canvas = ctk.CTkLabel(self.canvas_frame, text="La vista previa aparecerá aquí", text_color="white")
        self.canvas.pack(fill="both", expand=True)

    def _on_generate_meme(self):
        self.btn_generate.configure(state="disabled")
        self.lbl_status.configure(text="Generando...")
        threading.Thread(target=self._generate_thread, daemon=True).start()

    def _generate_thread(self):
        try:
            url = get_random_meme_url()
            if not url:
                raise Exception("No se pudo conectar con Imgflip")
            
            img_data = requests.get(url, timeout=10).content
            base_img = Image.open(io.BytesIO(img_data))
            
            top, bottom = "", ""
            if self.use_random_var.get():
                phrase = get_random_phrase()
                if random.choice([True, False]): top = phrase
                else: bottom = phrase
            else:
                txt = self.entry_custom.get().strip()
                if "|" in txt:
                    parts = txt.split("|", 1)
                    top, bottom = parts[0], parts[1]
                else:
                    top = txt

            # Renderizado a alta resolución
            rendered = render_meme(base_img, top, bottom)
            self.last_rendered_meme = rendered
            
            # Preparar vista previa escalada
            preview_img = rendered.copy()
            preview_img.thumbnail(PREVIEW_SIZE, Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=preview_img, size=preview_img.size)
            
            self.after(0, lambda: self._update_ui(ctk_img))
        except Exception as e:
            self.after(0, lambda: self.lbl_status.configure(text=f"Error: {str(e)}"))
        finally:
            self.after(0, lambda: self.btn_generate.configure(state="normal"))

    def _update_ui(self, ctk_img):
        self.canvas.configure(image=ctk_img, text="")
        self.btn_download.configure(state="normal")
        self.lbl_status.configure(text="Meme listo para descargar")

    def _on_download(self):
        if self.last_rendered_meme:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"meme_{timestamp}.png"
                # Guardar en el directorio actual (donde se ejecuta el script)
                save_path = os.path.join(os.getcwd(), filename)
                self.last_rendered_meme.save(save_path, "PNG")
                self.lbl_status.configure(text=f"Guardado en:\n{filename}")
            except Exception as e:
                self.lbl_status.configure(text=f"Error al guardar: {e}")

if __name__ == "__main__":
    app = MemeApp()
    app.mainloop()