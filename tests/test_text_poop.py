# tests/test_text_pool.py
"""
Tests para el módulo text_pool.py
"""

import sys
import json
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Asegurar imports desde la raíz del repo
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.text_pool import (
    load_phrases,
    save_phrases,
    get_random_phrase,
    add_phrase,
    update_phrase,
    delete_phrase,
    get_phrases_count,
    TextPoolError,
    PHRASES_PATH,
    MAX_PHRASE_LENGTH
)

# Datos de ejemplo
SAMPLE_PHRASES = [
    "Frase de prueba 1",
    "Frase de prueba 2",
    "Frase de prueba 3",
    "Esta es una frase más larga para probar el wrapping",
    "Otra frase con acentos y caracteres especiales: ñ, á, é, í, ó, ú"
]

class TestTextPool:
    """Tests para las funciones de text_pool.py"""

    def test_load_phrases_success(self, tmp_path):
        """Test de carga exitosa de frases."""
        phrases_file = tmp_path / "phrases.json"
        
        # Crear archivo de prueba
        with open(phrases_file, 'w', encoding='utf-8') as f:
            json.dump(SAMPLE_PHRASES, f, ensure_ascii=False)
        
        # Cargar frases
        loaded = load_phrases(phrases_file)
        
        assert loaded == SAMPLE_PHRASES
        assert len(loaded) == 5

    def test_load_phrases_file_not_found(self, tmp_path):
        """Test cuando el archivo no existe."""
        phrases_file = tmp_path / "nonexistent.json"
        
        loaded = load_phrases(phrases_file)
        
        assert loaded == []

    def test_load_phrases_invalid_json(self, tmp_path):
        """Test con JSON inválido."""
        phrases_file = tmp_path / "phrases.json"
        
        # Escribir JSON inválido
        with open(phrases_file, 'w') as f:
            f.write("{esto no es json valido")
        
        loaded = load_phrases(phrases_file)
        
        assert loaded == []

    def test_load_phrases_not_a_list(self, tmp_path):
        """Test cuando el JSON no es una lista."""
        phrases_file = tmp_path / "phrases.json"
        
        # Guardar un diccionario en lugar de lista
        with open(phrases_file, 'w') as f:
            json.dump({"key": "value"}, f)
        
        loaded = load_phrases(phrases_file)
        
        assert loaded == []

    def test_load_phrases_with_long_texts(self, tmp_path):
        """Test con frases que exceden la longitud máxima."""
        phrases_file = tmp_path / "phrases.json"
        
        # Crear frase muy larga
        long_phrase = "x" * (MAX_PHRASE_LENGTH + 100)
        test_data = ["normal", long_phrase, "otra normal"]
        
        with open(phrases_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        loaded = load_phrases(phrases_file)
        
        # La frase larga debería estar truncada
        assert len(loaded) == 3
        assert len(loaded[1]) <= MAX_PHRASE_LENGTH
        assert loaded[0] == "normal"
        assert loaded[2] == "otra normal"

    def test_save_phrases_success(self, tmp_path):
        """Test de guardado exitoso de frases."""
        phrases_file = tmp_path / "phrases.json"
        
        # Guardar frases
        result = save_phrases(SAMPLE_PHRASES, phrases_file)
        
        assert result is True
        assert phrases_file.exists()
        
        # Verificar contenido
        with open(phrases_file, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        
        assert saved == SAMPLE_PHRASES

    def test_save_phrases_creates_directory(self, tmp_path):
        """Test que verifica que se crea el directorio si no existe."""
        deep_path = tmp_path / "subdir" / "deep" / "phrases.json"
        
        result = save_phrases(SAMPLE_PHRASES, deep_path)
        
        assert result is True
        assert deep_path.exists()
        assert deep_path.parent.exists()

    def test_save_phrases_empty_and_long(self, tmp_path):
        """Test de guardado con frases vacías y muy largas."""
        phrases_file = tmp_path / "phrases.json"
        
        long_phrase = "x" * (MAX_PHRASE_LENGTH + 50)
        test_data = [
            "normal",
            "",  # vacía
            "   ",  # solo espacios
            long_phrase,
            None,  # no string
            123,  # número
        ]
        
        result = save_phrases(test_data, phrases_file)  # type: ignore
        
        assert result is True
        
        with open(phrases_file, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        
        # Las frases vacías y espacios deberían omitirse
        # Las largas deberían truncarse
        # Los no strings deberían convertirse
        assert "normal" in saved
        assert "" not in saved
        assert "   " not in saved
        assert len([p for p in saved if "x" in p][0]) <= MAX_PHRASE_LENGTH
        assert "123" in saved

    def test_save_phrases_permission_error(self, tmp_path):
        """Test de error de permisos al guardar."""
        phrases_file = tmp_path / "phrases.json"
        
        # Simular error de permisos
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = save_phrases(SAMPLE_PHRASES, phrases_file)
        
        assert result is False

    def test_get_random_phrase(self):
        """Test de obtención de frase aleatoria."""
        with patch('src.text_pool.load_phrases') as mock_load:
            mock_load.return_value = SAMPLE_PHRASES
            
            phrase = get_random_phrase()
            
            assert phrase in SAMPLE_PHRASES

    def test_get_random_phrase_empty_pool(self):
        """Test cuando el pool está vacío."""
        with patch('src.text_pool.load_phrases') as mock_load:
            mock_load.return_value = []
            
            phrase = get_random_phrase()
            
            assert phrase == "Texto de ejemplo"

    def test_add_phrase_success(self):
        """Test de añadir frase exitosamente."""
        with patch('src.text_pool.load_phrases') as mock_load, \
             patch('src.text_pool.save_phrases') as mock_save:
            
            mock_load.return_value = SAMPLE_PHRASES.copy()
            mock_save.return_value = True
            
            result = add_phrase("Nueva frase de prueba")
            
            assert result is True
            mock_save.assert_called_once()
            # Verificar que la nueva frase se añadió
            args = mock_save.call_args[0][0]
            assert "Nueva frase de prueba" in args

    def test_add_phrase_empty(self):
        """Test de añadir frase vacía."""
        with pytest.raises(TextPoolError) as exc_info:
            add_phrase("")
        
        assert "vacía" in str(exc_info.value).lower()
        
        with pytest.raises(TextPoolError):
            add_phrase("   ")

    def test_add_phrase_too_long(self):
        """Test de añadir frase demasiado larga."""
        long_phrase = "x" * (MAX_PHRASE_LENGTH + 1)
        
        with pytest.raises(TextPoolError) as exc_info:
            add_phrase(long_phrase)
        
        assert str(MAX_PHRASE_LENGTH) in str(exc_info.value)

    def test_update_phrase_success(self):
        """Test de actualizar frase exitosamente."""
        with patch('src.text_pool.load_phrases') as mock_load, \
             patch('src.text_pool.save_phrases') as mock_save:
            
            phrases = SAMPLE_PHRASES.copy()
            mock_load.return_value = phrases
            mock_save.return_value = True
            
            result = update_phrase(1, "Frase actualizada")
            
            assert result is True
            assert phrases[1] == "Frase actualizada"

    def test_update_phrase_invalid_index(self):
        """Test de actualizar con índice inválido."""
        with patch('src.text_pool.load_phrases') as mock_load:
            mock_load.return_value = SAMPLE_PHRASES.copy()
            
            with pytest.raises(TextPoolError) as exc_info:
                update_phrase(999, "nuevo texto")
            
            assert "fuera de rango" in str(exc_info.value).lower()

    def test_delete_phrase_success(self):
        """Test de eliminar frase exitosamente."""
        with patch('src.text_pool.load_phrases') as mock_load, \
             patch('src.text_pool.save_phrases') as mock_save:
            
            phrases = SAMPLE_PHRASES.copy()
            original_length = len(phrases)
            mock_load.return_value = phrases
            mock_save.return_value = True
            
            result = delete_phrase(2)
            
            assert result is True
            assert len(phrases) == original_length - 1
            assert SAMPLE_PHRASES[2] not in phrases

    def test_delete_phrase_invalid_index(self):
        """Test de eliminar con índice inválido."""
        with patch('src.text_pool.load_phrases') as mock_load:
            mock_load.return_value = SAMPLE_PHRASES.copy()
            
            with pytest.raises(TextPoolError) as exc_info:
                delete_phrase(-1)
            
            assert "fuera de rango" in str(exc_info.value).lower()

    def test_get_phrases_count(self):
        """Test de contar frases."""
        with patch('src.text_pool.load_phrases') as mock_load:
            mock_load.return_value = SAMPLE_PHRASES
            
            count = get_phrases_count()
            
            assert count == len(SAMPLE_PHRASES)

    def test_transaction_safety(self, tmp_path):
        """Test de seguridad en escritura (archivo temporal + rename)."""
        phrases_file = tmp_path / "phrases.json"
        
        # Guardar frases
        save_phrases(SAMPLE_PHRASES, phrases_file)
        
        # Verificar que no hay archivos temporales
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0
        
        # Verificar contenido
        with open(phrases_file, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        assert saved == SAMPLE_PHRASES

    @patch('src.text_pool.shutil.move')
    def test_save_phrases_rename_failure(self, mock_move, tmp_path):
        """Test de fallo en el renombrado del archivo temporal."""
        phrases_file = tmp_path / "phrases.json"
        mock_move.side_effect = Exception("Rename failed")
        
        result = save_phrases(SAMPLE_PHRASES, phrases_file)
        
        assert result is False
        # Verificar que se limpió el archivo temporal
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0


class TestPhrasesManagerWindow:
    """Tests para la ventana de gestión de frases (integración)."""
    
    @pytest.fixture
    def mock_ctk(self):
        """Fixture para mockear CustomTkinter."""
        with patch('src.main.ctk') as mock:
            # Configurar mocks básicos
            mock.CTkToplevel = MagicMock()
            mock.CTkFrame = MagicMock()
            mock.CTkButton = MagicMock()
            mock.CTkLabel = MagicMock()
            mock.CTkTextbox = MagicMock()
            mock.CTkScrollbar = MagicMock()
            mock.CTkInputDialog = MagicMock()
            mock.CTkMessagebox = MagicMock()
            yield mock

    def test_phrases_window_creation(self, mock_ctk):
        """Test de creación de la ventana de frases."""
        from src.main import PhrasesManagerWindow
        
        # Crear mock del parent
        parent = MagicMock()
        
        # Crear ventana
        window = PhrasesManagerWindow(parent)
        
        # Verificar que se llamaron los métodos correctos
        assert window.title.call_args[0][0] == "Gestor de Frases"
        assert window.geometry.call_args[0][0] == "600x500"

    def test_load_phrases_to_list(self, mock_ctk):
        """Test de carga de frases en la lista."""
        from src.main import PhrasesManagerWindow
        
        parent = MagicMock()
        window = PhrasesManagerWindow(parent)
        
        # Mock del textbox
        window.phrases_listbox = MagicMock()
        
        # Mock de load_phrases
        with patch('src.main.load_phrases') as mock_load:
            mock_load.return_value = SAMPLE_PHRASES
            
            # Llamar al método
            window._load_phrases_to_list()
        
        # Verificar que se insertaron las frases
        assert window.phrases_listbox.delete.called
        assert window.phrases_listbox.insert.call_count == len(SAMPLE_PHRASES)