# src/main.py
"""
Interfaz gráfica principal de MemeScript-Py.
Incluye todas las mejoras: caché, gestión de frases, selector de fuentes, etc.
"""

from __future__ import annotations

import io
import logging
import threading
import random
import os
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageTk

from src.api_client import (
    get_random_meme, get_meme_image, get_all_memes,
    clear_cache, get_cache_stats, ImgflipAPIError
)
from src.renderer import render_meme, get_available_fonts, RendererError
from src.text_pool import (
    get_random_phrase, add_phrase, update_phrase, delete_phrase,
    load_phrases, get_phrases_count, TextPoolError
)
from src.cache import MemeCache

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('memescript.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constantes de la GUI
PREVIEW_SIZE = (800, 600)
WINDOW_SIZE = "1300x900"
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PhrasesManagerWindow(ctk.CTkToplevel):
    """Ventana para gestionar el pool de frases."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Gestor de Frases")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()
        
        # Variables
        self.phrases = load_phrases()
        self.selected_index = None
        
        # Crear UI
        self._create_ui()
        self._load_phrases_to_list()
        
    def _create_ui(self):
        """Crea la interfaz de la ventana."""
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Lista de frases
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.phrases_listbox = ctk.CTkTextbox(list_frame, wrap="word")
        self.phrases_listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = ctk.CTkScrollbar(list_frame, command=self.phrases_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.phrases_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Frame de botones
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=5)
        
        self.btn_add = ctk.CTkButton(
            button_frame,
            text="Añadir Frase",
            command=self._add_phrase_dialog,
            width=120
        )
        self.btn_add.pack(side="left", padx=5)
        
        self.btn_edit = ctk.CTkButton(
            button_frame,
            text="Editar Seleccionada",
            command=self._edit_phrase_dialog,
            width=120,
            state="disabled"
        )
        self.btn_edit.pack(side="left", padx=5)
        
        self.btn_delete = ctk.CTkButton(
            button_frame,
            text="Eliminar Seleccionada",
            command=self._delete_phrase,
            width=120,
            fg_color="#aa2222",
            hover_color="#cc3333",
            state="disabled"
        )
        self.btn_delete.pack(side="left", padx=5)
        
        self.btn_refresh = ctk.CTkButton(
            button_frame,
            text="Actualizar",
            command=self._refresh_list,
            width=100
        )
        self.btn_refresh.pack(side="right", padx=5)
        
        # Info
        self.lbl_count = ctk.CTkLabel(
            main_frame,
            text=f"Total de frases: {len(self.phrases)}"
        )
        self.lbl_count.pack(pady=5)
        
        # Bind selección
        self.phrases_listbox.bind("<ButtonRelease-1>", self._on_select)
        
    def _load_phrases_to_list(self):
        """Carga las frases en la lista."""
        self.phrases_listbox.delete("1.0", "end")
        for i, phrase in enumerate(self.phrases, 1):
            self.phrases_listbox.insert("end", f"{i}. {phrase}\n\n")
    
    def _on_select(self, event):
        """Maneja la selección de una frase."""
        try:
            index = self.phrases_listbox.index("insert").split(".")[0]
            if index and index.isdigit():
                self.selected_index = int(index) - 1
                self.btn_edit.configure(state="normal")
                self.btn_delete.configure(state="normal")
        except:
            pass
    
    def _add_phrase_dialog(self):
        """Muestra diálogo para añadir frase."""
        dialog = ctk.CTkInputDialog(
            text="Introduce la nueva frase:",
            title="Añadir Frase"
        )
        phrase = dialog.get_input()
        
        if phrase:
            try:
                add_phrase(phrase)
                self._refresh_list()
                self.lbl_count.configure(text=f"Total de frases: {len(self.phrases)}")
                logger.info(f"Frase añadida: {phrase[:50]}...")
            except TextPoolError as e:
                self._show_error(str(e))
    
    def _edit_phrase_dialog(self):
        """Muestra diálogo para editar frase."""
        if self.selected_index is None:
            return
        
        current = self.phrases[self.selected_index]
        dialog = ctk.CTkInputDialog(
            text="Edita la frase:",
            title="Editar Frase",
            default_value=current
        )
        new_phrase = dialog.get_input()
        
        if new_phrase and new_phrase != current:
            try:
                update_phrase(self.selected_index, new_phrase)
                self._refresh_list()
                logger.info(f"Frase actualizada: {new_phrase[:50]}...")
            except TextPoolError as e:
                self._show_error(str(e))
    
    def _delete_phrase(self):
        """Elimina la frase seleccionada."""
        if self.selected_index is None:
            return
        
        # Confirmar eliminación
        confirm = ctk.CTkMessagebox(
            title="Confirmar",
            message="¿Estás seguro de eliminar esta frase?",
            icon="warning",
            option_1="Sí",
            option_2="No"
        )
        
        if confirm.get() == "Sí":
            try:
                delete_phrase(self.selected_index)
                self._refresh_list()
                self.selected_index = None
                self.btn_edit.configure(state="disabled")
                self.btn_delete.configure(state="disabled")
                self.lbl_count.configure(text=f"Total de frases: {len(self.phrases)}")
                logger.info("Frase eliminada")
            except TextPoolError as e:
                self._show_error(str(e))
    
    def _refresh_list(self):
        """Actualiza la lista de frases."""
        self.phrases = load_phrases()
        self._load_phrases_to_list()
        self.lbl_count.configure(text=f"Total de frases: {len(self.phrases)}")
    
    def _show_error(self, message: str):
        """Muestra un mensaje de error."""
        ctk.CTkMessagebox(
            title="Error",
            message=message,
            icon="cancel"
        )

class CacheInfoWindow(ctk.CTkToplevel):
    """Ventana con información del caché."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Información del Caché")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()
        
        self._create_ui()
        self._refresh_stats()
        
    def _create_ui(self):
        """Crea la interfaz de la ventana."""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Estadísticas
        self.stats_text = ctk.CTkTextbox(main_frame, wrap="word", height=150)
        self.stats_text.pack(fill="x", pady=(0, 20))
        self.stats_text.configure(state="disabled")
        
        # Botones
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x")
        
        self.btn_refresh = ctk.CTkButton(
            btn_frame,
            text="Actualizar",
            command=self._refresh_stats,
            width=100
        )
        self.btn_refresh.pack(side="left", padx=5)
        
        self.btn_clear = ctk.CTkButton(
            btn_frame,
            text="Limpiar Caché",
            command=self._clear_cache,
            width=100,
            fg_color="#aa2222",
            hover_color="#cc3333"
        )
        self.btn_clear.pack(side="left", padx=5)
        
    def _refresh_stats(self):
        """Actualiza las estadísticas del caché."""
        stats = get_cache_stats()
        
        self.stats_text.configure(state="normal")
        self.stats_text.delete("1.0", "end")
        
        text = (
            f"Imágenes en caché: {stats['total_images']}\n"
            f"Tamaño total: {stats['total_size_mb']} MB\n"
            f"Tamaño máximo: {stats['max_size_mb']} MB\n"
            f"Uso: {stats['usage_percent']}%\n"
            f"Directorio: {stats['cache_dir']}"
        )
        
        self.stats_text.insert("1.0", text)
        self.stats_text.configure(state="disabled")
    
    def _clear_cache(self):
        """Limpia el caché."""
        confirm = ctk.CTkMessagebox(
            title="Confirmar",
            message="¿Estás seguro de limpiar el caché?",
            icon="warning",
            option_1="Sí",
            option_2="No"
        )
        
        if confirm.get() == "Sí":
            clear_cache()
            self._refresh_stats()
            ctk.CTkMessagebox(
                title="Éxito",
                message="Caché limpiado correctamente",
                icon="check"
            )

class MemeApp(ctk.CTk):
    """Aplicación principal de generación de memes."""
    
    def __init__(self):
        super().__init__()
        
        # Configuración ventana
        self.title("MemeScript-Py v2.0 - Generador de Memes Profesional")
        self.geometry(WINDOW_SIZE)
        
        # Variables de estado
        self.last_rendered_meme: Optional[Image.Image] = None
        self.current_template_info: Optional[Dict[str, Any]] = None
        self.available_templates: List[Dict[str, Any]] = []
        self.available_fonts: List[str] = []
        
        # Inicializar UI
        self._create_menu()
        self._create_widgets()
        self._load_initial_data()
        
        logger.info("Aplicación iniciada correctamente")
    
    def _create_menu(self):
        """Crea el menú superior."""
        # Frame del menú
        self.menu_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.menu_frame.pack(fill="x", padx=0, pady=0)
        self.menu_frame.pack_propagate(False)
        
        # Botones del menú
        self.btn_phrases = ctk.CTkButton(
            self.menu_frame,
            text="📝 Gestionar Frases",
            command=self._open_phrases_manager,
            width=140,
            height=30
        )
        self.btn_phrases.pack(side="left", padx=10, pady=5)
        
        self.btn_cache = ctk.CTkButton(
            self.menu_frame,
            text="💾 Info Caché",
            command=self._open_cache_info,
            width=120,
            height=30
        )
        self.btn_cache.pack(side="left", padx=5, pady=5)
        
        self.btn_templates = ctk.CTkButton(
            self.menu_frame,
            text="🖼️ Actualizar Plantillas",
            command=self._refresh_templates,
            width=140,
            height=30
        )
        self.btn_templates.pack(side="left", padx=5, pady=5)
    
    def _create_widgets(self):
        """Crea los widgets principales."""
        
        # --- Panel Izquierdo (Controles) ---
        self.frame_left = ctk.CTkFrame(self, width=380)
        self.frame_left.pack(side="left", fill="y", padx=10, pady=10)
        self.frame_left.pack_propagate(False)
        
        # Título
        self.lbl_title = ctk.CTkLabel(
            self.frame_left,
            text="🎭 Generador de Memes",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.lbl_title.pack(pady=(20, 10))
        
        # Estado
        self.lbl_status = ctk.CTkLabel(
            self.frame_left,
            text="✅ Listo para crear",
            wraplength=300,
            font=ctk.CTkFont(size=12)
        )
        self.lbl_status.pack(pady=(0, 20))
        
        # Barra de progreso
        self.progress_bar = ctk.CTkProgressBar(self.frame_left, width=300)
        self.progress_bar.pack(pady=(0, 20))
        self.progress_bar.set(0)
        
        # --- Selector de plantilla ---
        template_frame = ctk.CTkFrame(self.frame_left)
        template_frame.pack(fill="x", padx=20, pady=10)
        
        self.lbl_template = ctk.CTkLabel(
            template_frame,
            text="Plantilla:",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_template.pack(anchor="w", pady=(5, 0))
        
        self.template_var = ctk.StringVar(value="aleatoria")
        self.template_menu = ctk.CTkOptionMenu(
            template_frame,
            values=["🔄 Aleatoria", "Cargando..."],
            variable=self.template_var,
            command=self._on_template_change
        )
        self.template_menu.pack(fill="x", pady=5)
        
        # --- Textos ---
        text_frame = ctk.CTkFrame(self.frame_left)
        text_frame.pack(fill="x", padx=20, pady=10)
        
        self.lbl_texts = ctk.CTkLabel(
            text_frame,
            text="Textos del Meme:",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_texts.pack(anchor="w", pady=(5, 5))
        
        # Texto superior
        self.lbl_top = ctk.CTkLabel(text_frame, text="Superior:", anchor="w")
        self.lbl_top.pack(anchor="w")
        
        self.entry_top = ctk.CTkEntry(
            text_frame,
            placeholder_text="Texto superior..."
        )
        self.entry_top.pack(fill="x", pady=(0, 10))
        
        # Texto inferior
        self.lbl_bottom = ctk.CTkLabel(text_frame, text="Inferior:", anchor="w")
        self.lbl_bottom.pack(anchor="w")
        
        self.entry_bottom = ctk.CTkEntry(
            text_frame,
            placeholder_text="Texto inferior..."
        )
        self.entry_bottom.pack(fill="x", pady=(0, 5))
        
        # Checkbox frase aleatoria
        self.random_text_var = ctk.BooleanVar(value=False)
        self.chk_random = ctk.CTkCheckBox(
            text_frame,
            text="Usar frase aleatoria",
            variable=self.random_text_var,
            command=self._toggle_random_text
        )
        self.chk_random.pack(pady=5)
        
        # Selector de posición de frase aleatoria
        self.random_position_var = ctk.StringVar(value="arriba")
        self.random_position_frame = ctk.CTkFrame(text_frame, fg_color="transparent")
        
        self.rb_top = ctk.CTkRadioButton(
            self.random_position_frame,
            text="Arriba",
            variable=self.random_position_var,
            value="arriba",
            state="disabled"
        )
        self.rb_top.pack(side="left", padx=5)
        
        self.rb_bottom = ctk.CTkRadioButton(
            self.random_position_frame,
            text="Abajo",
            variable=self.random_position_var,
            value="abajo",
            state="disabled"
        )
        self.rb_bottom.pack(side="left", padx=5)
        
        self.rb_random = ctk.CTkRadioButton(
            self.random_position_frame,
            text="Aleatorio",
            variable=self.random_position_var,
            value="aleatorio",
            state="disabled"
        )
        self.rb_random.pack(side="left", padx=5)
        
        self.random_position_frame.pack(pady=(0, 10))
        
        # --- Opciones de renderizado ---
        render_frame = ctk.CTkFrame(self.frame_left)
        render_frame.pack(fill="x", padx=20, pady=10)
        
        self.lbl_render = ctk.CTkLabel(
            render_frame,
            text="Opciones de renderizado:",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_render.pack(anchor="w", pady=(5, 5))
        
        # Selector de fuente
        font_frame = ctk.CTkFrame(render_frame, fg_color="transparent")
        font_frame.pack(fill="x", pady=5)
        
        self.lbl_font = ctk.CTkLabel(font_frame, text="Fuente:", width=60)
        self.lbl_font.pack(side="left")
        
        self.font_var = ctk.StringVar(value="Impact")
        self.font_menu = ctk.CTkOptionMenu(
            font_frame,
            values=["Impact", "Arial Black", "Comic Sans MS"],
            variable=self.font_var,
            width=180
        )
        self.font_menu.pack(side="right")
        
        # Tamaño de fuente
        size_frame = ctk.CTkFrame(render_frame, fg_color="transparent")
        size_frame.pack(fill="x", pady=5)
        
        self.lbl_size = ctk.CTkLabel(size_frame, text="Tamaño:", width=60)
        self.lbl_size.pack(side="left")
        
        self.size_slider = ctk.CTkSlider(
            size_frame,
            from_=0.05,
            to=0.2,
            number_of_steps=15,
            command=self._on_size_change
        )
        self.size_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.size_slider.set(0.1)
        
        self.size_label = ctk.CTkLabel(size_frame, text="10%", width=40)
        self.size_label.pack(side="right")
        
        # Sombra
        self.shadow_var = ctk.BooleanVar(value=False)
        self.chk_shadow = ctk.CTkCheckBox(
            render_frame,
            text="Añadir sombra",
            variable=self.shadow_var
        )
        self.chk_shadow.pack(anchor="w", pady=2)
        
        # --- Botones de acción ---
        action_frame = ctk.CTkFrame(self.frame_left)
        action_frame.pack(fill="x", padx=20, pady=20)
        
        self.btn_generate = ctk.CTkButton(
            action_frame,
            text="🎨 Generar Meme",
            command=self._on_generate_meme,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.btn_generate.pack(fill="x", pady=5)
        
        self.btn_download = ctk.CTkButton(
            action_frame,
            text="💾 Descargar Meme",
            command=self._on_download,
            state="disabled",
            fg_color="#2c7a2c",
            hover_color="#1e5a1e",
            height=40
        )
        self.btn_download.pack(fill="x", pady=5)
        
        # --- Panel Derecho (Vista Previa) ---
        self.canvas_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
        self.canvas_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.canvas = ctk.CTkLabel(
            self.canvas_frame,
            text="✨ La vista previa aparecerá aquí ✨\n\nHaz clic en 'Generar Meme' para comenzar",
            text_color="#888888",
            font=ctk.CTkFont(size=16)
        )
        self.canvas.pack(fill="both", expand=True)
    
    def _load_initial_data(self):
        """Carga datos iniciales en segundo plano."""
        threading.Thread(target=self._load_templates_thread, daemon=True).start()
        threading.Thread(target=self._load_fonts_thread, daemon=True).start()
    
    def _load_templates_thread(self):
        """Carga la lista de plantillas."""
        try:
            self.available_templates = get_all_memes() or []
            template_names = ["🔄 Aleatoria"] + [
                f"{t.get('name', 'Unknown')}" for t in self.available_templates[:50]
            ]
            
            self.after(0, lambda: self._update_template_menu(template_names))
            logger.info(f"Cargadas {len(self.available_templates)} plantillas")
            
        except ImgflipAPIError as e:
            logger.error(f"Error cargando plantillas: {e}")
            self.after(0, lambda: self.lbl_status.configure(
                text=f"⚠️ Error cargando plantillas: {str(e)}"
            ))
    
    def _load_fonts_thread(self):
        """Carga la lista de fuentes disponibles."""
        self.available_fonts = get_available_fonts()
        if self.available_fonts:
            self.after(0, lambda: self.font_menu.configure(values=self.available_fonts))
            if "Impact" in self.available_fonts:
                self.font_var.set("Impact")
            elif self.available_fonts:
                self.font_var.set(self.available_fonts[0])
        
        logger.info(f"Fuentes disponibles: {self.available_fonts}")
    
    def _update_template_menu(self, names: List[str]):
        """Actualiza el menú de plantillas."""
        self.template_menu.configure(values=names)
        self.template_var.set("🔄 Aleatoria")
    
    def _on_template_change(self, choice: str):
        """Maneja cambio de plantilla."""
        if choice != "🔄 Aleatoria":
            # Buscar template seleccionado
            for t in self.available_templates:
                if t.get('name') == choice:
                    self.current_template_info = t
                    logger.info(f"Plantilla seleccionada: {t.get('name')}")
                    break
    
    def _on_size_change(self, value):
        """Maneja cambio en el slider de tamaño."""
        percent = int(value * 100)
        self.size_label.configure(text=f"{percent}%")
    
    def _toggle_random_text(self):
        """Activa/desactiva opciones de texto aleatorio."""
        state = "normal" if self.random_text_var.get() else "disabled"
        self.rb_top.configure(state=state)
        self.rb_bottom.configure(state=state)
        self.rb_random.configure(state=state)
        
        # Limpiar entradas si se activa aleatorio
        if self.random_text_var.get():
            self.entry_top.delete(0, "end")
            self.entry_bottom.delete(0, "end")
            self.entry_top.configure(state="disabled")
            self.entry_bottom.configure(state="disabled")
        else:
            self.entry_top.configure(state="normal")
            self.entry_bottom.configure(state="normal")
    
    def _open_phrases_manager(self):
        """Abre el gestor de frases."""
        PhrasesManagerWindow(self)
    
    def _open_cache_info(self):
        """Abre la ventana de información del caché."""
        CacheInfoWindow(self)
    
    def _refresh_templates(self):
        """Actualiza la lista de plantillas."""
        self.lbl_status.configure(text="🔄 Actualizando plantillas...")
        self.btn_templates.configure(state="disabled")
        threading.Thread(target=self._load_templates_thread, daemon=True).start()
        self.after(2000, lambda: self.btn_templates.configure(state="normal"))
    
    def _on_generate_meme(self):
        """Inicia el proceso de generación del meme."""
        self.btn_generate.configure(state="disabled")
        self.btn_download.configure(state="disabled")
        self.progress_bar.start()
        self.lbl_status.configure(text="🎨 Generando meme...")
        
        threading.Thread(target=self._generate_thread, daemon=True).start()
    
    def _generate_thread(self):
        """Hilo de generación del meme."""
        try:
            # Obtener plantilla
            template_url = None
            template_info = None
            
            if self.template_var.get() == "🔄 Aleatoria":
                result = get_random_meme()
                if result:
                    template_url, template_info = result
            else:
                # Usar plantilla seleccionada
                template_name = self.template_var.get()
                for t in self.available_templates:
                    if t.get('name') == template_name:
                        template_info = t
                        template_url = t.get('url')
                        break
            
            if not template_url or not template_info:
                raise Exception("No se pudo obtener una plantilla válida")
            
            # Descargar imagen (con caché)
            img_data = get_meme_image(template_info['id'], template_url)
            if not img_data:
                raise Exception("No se pudo descargar la imagen")
            
            base_img = Image.open(io.BytesIO(img_data))
            
            # Obtener textos
            top_text = ""
            bottom_text = ""
            
            if self.random_text_var.get():
                phrase = get_random_phrase()
                position = self.random_position_var.get()
                
                if position == "arriba":
                    top_text = phrase
                elif position == "abajo":
                    bottom_text = phrase
                else:  # aleatorio
                    if random.choice([True, False]):
                        top_text = phrase
                    else:
                        bottom_text = phrase
            else:
                top_text = self.entry_top.get().strip()
                bottom_text = self.entry_bottom.get().strip()
            
            # Renderizar meme
            rendered = render_meme(
                image=base_img,
                top_text=top_text,
                bottom_text=bottom_text,
                font_name=self.font_var.get(),
                font_size_ratio=self.size_slider.get(),
                shadow=self.shadow_var.get()
            )
            
            self.last_rendered_meme = rendered
            
            # Preparar vista previa
            preview_img = rendered.copy()
            preview_img.thumbnail(PREVIEW_SIZE, Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(
                light_image=preview_img,
                size=preview_img.size
            )
            
            self.after(0, lambda: self._update_ui(ctk_img, template_info))
            
        except ImgflipAPIError as e:
            logger.error(f"Error de API: {e}")
            self.after(0, lambda: self.lbl_status.configure(
                text=f"❌ Error de conexión: {str(e)}"
            ))
        except RendererError as e:
            logger.error(f"Error de renderizado: {e}")
            self.after(0, lambda: self.lbl_status.configure(
                text=f"❌ Error al renderizar: {str(e)}"
            ))
        except Exception as e:
            logger.error(f"Error inesperado: {e}", exc_info=True)
            self.after(0, lambda: self.lbl_status.configure(
                text=f"❌ Error: {str(e)[:100]}"
            ))
        finally:
            self.after(0, self._generation_finished)
    
    def _update_ui(self, ctk_img, template_info):
        """Actualiza la UI con el meme generado."""
        self.canvas.configure(image=ctk_img, text="")
        self.btn_download.configure(state="normal")
        
        template_name = template_info.get('name', 'Desconocida')
        self.lbl_status.configure(
            text=f"✅ Meme generado con: {template_name}"
        )
        
        logger.info(f"Meme generado correctamente usando {template_name}")
    
    def _generation_finished(self):
        """Llamado cuando termina la generación."""
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.btn_generate.configure(state="normal")
    
    def _on_download(self):
        """Guarda el meme en disco."""
        if not self.last_rendered_meme:
            return
        
        try:
            # Crear directorio de salida si no existe
            output_dir = Path.home() / "Pictures" / "Memescript"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generar nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            template_name = self.current_template_info.get('name', 'meme') if self.current_template_info else 'meme'
            # Limpiar nombre para archivo
            template_name = "".join(c for c in template_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            template_name = template_name.replace(' ', '_')[:30]
            
            filename = f"{template_name}_{timestamp}.png"
            save_path = output_dir / filename
            
            # Guardar
            self.last_rendered_meme.save(save_path, "PNG", quality=95)
            
            self.lbl_status.configure(
                text=f"✅ Guardado en:\n{output_dir.name}/{filename}"
            )
            
            logger.info(f"Meme guardado: {save_path}")
            
            # Preguntar si quiere abrir la carpeta
            response = ctk.CTkMessagebox(
                title="Descarga completada",
                message=f"Meme guardado como:\n{filename}\n\n¿Abrir carpeta?",
                icon="info",
                option_1="Sí",
                option_2="No"
            )
            
            if response.get() == "Sí":
                import subprocess
                import platform
                
                if platform.system() == "Windows":
                    os.startfile(str(output_dir))
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", str(output_dir)])
                else:  # Linux
                    subprocess.run(["xdg-open", str(output_dir)])
                    
        except Exception as e:
            logger.error(f"Error guardando meme: {e}")
            self.lbl_status.configure(text=f"❌ Error al guardar: {str(e)[:50]}")

def main():
    """Punto de entrada principal."""
    app = MemeApp()
    app.mainloop()

if __name__ == "__main__":
    main()