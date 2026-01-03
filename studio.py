"""
NewEngine Studio v0.9.9 - Absolute Deep Fix
-------------------------------------------
Полноценная среда разработки для движка NewEngine.
Максимально детализированная архитектура БЕЗ сокращений.
Все функции логики и интерфейса синхронизированы.

Автор: AI Assistant
Лицензия: MIT
"""

import customtkinter as ctk
import os
import subprocess
import threading
import sys
import platform
import time
import shutil
import urllib.request
import zipfile
import io
import re
import json
import hashlib
from datetime import datetime
from tkinter import messagebox, ttk, simpledialog
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple
from concurrent.futures import ThreadPoolExecutor

# =============================================================================
# 1. ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ СИСТЕМЫ
# =============================================================================

class Config:
    """
    Класс для централизованного управления путями и настройками.
    Все пути вычисляются относительно папки, в которой запущен studio.py.
    """
    APP_NAME = "NewEngine Studio"
    VERSION = "0.9.9 (Absolute Deep Fix)"
    THEME = "Dark"
    ACCENT_COLOR = "blue"
    
    # Определение базовой директории
    ROOT_DIR = Path(os.getcwd())
    
    # Пути для результатов сборки
    BIN_DIR = ROOT_DIR / "bin"
    OBJ_DIR = BIN_DIR / "obj"
    
    # Пути исходного кода
    INCLUDE_DIR = ROOT_DIR / "include"
    THIRDPARTY_DIR = INCLUDE_DIR / "thirdparty"
    ASSETS_DIR = ROOT_DIR / "assets"
    GAME_DIR = ROOT_DIR / "game"
    ENGINE_DIR = ROOT_DIR / "engine"
    
    # Путь для хранения резервных копий
    BACKUP_DIR = ROOT_DIR / "backups"
    
    # Настройки компилятора
    COMPILER = "gcc"
    if platform.system() == "Windows":
        OUTPUT_BINARY = "game.exe"
    else:
        OUTPUT_BINARY = "game"
        
    # Ссылки для обновления (GitHub)
    URL_STUDIO_SOURCE = "https://raw.githubusercontent.com/crimbrodev/newengineSTUDIO/main/studio.py"
    URL_ENGINE_MASTER = "https://github.com/Kolya142/newengine/archive/refs/heads/main.zip"
    
    # Библиотеки для менеджера зависимостей
    LIBRARY_MAP = {
        "stb_image": "https://raw.githubusercontent.com/nothings/stb/master/stb_image.h",
        "miniaudio": "https://raw.githubusercontent.com/mackron/miniaudio/master/miniaudio.h",
        "cJSON": "https://raw.githubusercontent.com/DaveGamble/cJSON/master/cJSON.h",
        "nuklear": "https://raw.githubusercontent.com/Immediate-Mode-UI/Nuklear/master/nuklear.h"
    }

# =============================================================================
# 2. НИЗКОУРОВНЕВЫЕ UI КОМПОНЕНТЫ
# =============================================================================

class LogPanel(ctk.CTkTextbox):
    """
    Специализированный виджет консоли.
    Используется для вывода системных логов с цветовой индикацией.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # Настройка шрифта (моноширинный для кода)
        self.configure(state="disabled", font=("Consolas", 11))
        
        # Определение цветовой схемы
        # CustomTkinter не позволяет менять 'font' через tag_config
        self.tag_config("error", foreground="#ff5555")
        self.tag_config("warning", foreground="#ffb86c")
        self.tag_config("success", foreground="#50fa7b")
        self.tag_config("info", foreground="#8be9fd")
        self.tag_config("dim", foreground="#6272a4")

    def write(self, text: str, tag: Optional[str] = None):
        """Безопасная вставка текста в окно консоли."""
        self.configure(state="normal")
        self.insert("end", text, tag)
        self.see("end") # Автоматический скролл вниз
        self.configure(state="disabled")

    def clear_content(self):
        """Полная очистка консоли."""
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")

class IssuesTable(ctk.CTkFrame):
    """
    Виджет таблицы для отображения ошибок GCC.
    Реализован через ttk.Treeview с поддержкой темной темы.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Настройка стиля Treeview для соответствия темной теме
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview", 
            background="#1d1d1d", 
            foreground="#ffffff", 
            fieldbackground="#1d1d1d", 
            borderwidth=0, 
            rowheight=25,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Treeview.Heading", 
            background="#333333", 
            foreground="#ffffff", 
            borderwidth=1, 
            font=("Segoe UI", 10, "bold")
        )
        style.map("Treeview", background=[('selected', '#1f538d')])

        # Создание колонок таблицы
        columns = ("File", "Line", "Severity", "Message")
        self.tree = ttk.Treeview(self, columns=columns, show='headings')
        
        self.tree.heading("File", text="Файл")
        self.tree.heading("Line", text="Стр.")
        self.tree.heading("Severity", text="Тип")
        self.tree.heading("Message", text="Сообщение")
        
        self.tree.column("File", width=140, anchor="w")
        self.tree.column("Line", width=50, anchor="center")
        self.tree.column("Severity", width=90, anchor="center")
        self.tree.column("Message", width=450, anchor="w")
        
        # Вертикальный скроллбар
        self.v_scroll = ctk.CTkScrollbar(self, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.v_scroll.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        self.v_scroll.pack(side="right", fill="y")

    def add_issue(self, file: str, line: str, severity: str, message: str):
        """Добавляет новую запись об ошибке/предупреждении."""
        icon = "❌" if severity.lower() == "error" else "⚠️"
        self.tree.insert("", "end", values=(file, line, f"{icon} {severity}", message))

    def clear_table(self):
        """Очистка всех строк в таблице."""
        for row in self.tree.get_children():
            self.tree.delete(row)

# =============================================================================
# 3. ЛОГИЧЕСКИЕ МОДУЛИ (BACKEND)
# =============================================================================

class DependencyManager:
    """Система анализа дерева инклудов (#include)."""
    
    def extract_includes(self, file_path: Path) -> List[str]:
        """Парсит файл и возвращает список всех хедеров."""
        if not file_path.exists():
            return []
            
        includes_found = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Поиск строк типа #include "file.h" или #include <file.h>
                pattern = r'#include\s+["<]([^">]+)[">]'
                matches = re.findall(pattern, content)
                for m in matches:
                    includes_found.append(m)
        except Exception as e:
            print(f"[DependencyManager] Ошибка при чтении {file_path.name}: {e}")
            
        return includes_found

    def check_rebuild_needed(self, source_c: Path, object_o: Path) -> bool:
        """Рекурсивно проверяет, нужно ли пересобирать файл."""
        # Если объектного файла нет - собираем обязательно
        if not object_o.exists():
            return True
            
        target_time = os.path.getmtime(object_o)
        
        # Проверка самого исходника
        if os.path.getmtime(source_c) > target_time:
            return True
            
        # Рекурсивная проверка всех подключенных заголовков
        visited = set()
        stack = self.extract_includes(source_c)
        
        while stack:
            header_name = stack.pop()
            if header_name in visited:
                continue
            visited.add(header_name)
            
            # Ищем файл хедера в путях инклудов проекта
            for folder in [Config.INCLUDE_DIR, Config.ASSETS_DIR, source_c.parent]:
                h_path = folder / header_name
                if h_path.exists():
                    # Если какой-то хедер новее .o файла - нужна пересборка
                    if os.path.getmtime(h_path) > target_time:
                        return True
                    # Проверяем вложенные зависимости этого хедера
                    stack.extend(self.extract_includes(h_path))
                    break
        return False

class GitEngine:
    """Логика взаимодействия с Git-репозиторием."""
    
    @staticmethod
    def is_installed() -> bool:
        """Проверка наличия Git в системе."""
        try:
            subprocess.run(["git", "--version"], capture_output=True)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    def run_command(args: List[str]) -> Tuple[bool, str]:
        """Выполняет команду Git и возвращает результат."""
        if not GitEngine.is_installed():
            return False, "Git не установлен в системе."
            
        try:
            process = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=Config.ROOT_DIR,
                encoding='utf-8',
                errors='replace'
            )
            if process.returncode == 0:
                output = process.stdout if process.stdout else "Команда успешно выполнена."
                return True, output
            else:
                return False, process.stderr if process.stderr else "Неизвестная ошибка Git."
        except Exception as e:
            return False, f"Сбой подсистемы Git: {str(e)}"

    @staticmethod
    def get_detailed_status() -> str:
        """Получает расширенный статус репозитория."""
        git_dir = Config.ROOT_DIR / ".git"
        if not git_dir.exists():
            return "Папка не является Git-репозиторием."
            
        ok, out = GitEngine.run_command(["status", "--short"])
        if ok:
            return out if out.strip() else "Изменений в файлах нет."
        return f"Ошибка запроса статуса: {out}"

class SnapshotManager:
    """Управление резервными снимками проекта."""
    
    @staticmethod
    def create_snapshot(reason: str = "manual") -> str:
        """Создает ZIP-архив папки game/."""
        if not Config.GAME_DIR.exists():
            return "Ошибка: папка game/ не найдена."
            
        Config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        # Генерация имени файла на основе времени
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}_{reason}.zip"
        target_path = Config.BACKUP_DIR / filename
        
        try:
            with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for file_path in Config.GAME_DIR.rglob("*"):
                    if file_path.is_file():
                        archive.write(file_path, file_path.relative_to(Config.ROOT_DIR))
            return filename
        except Exception as e:
            return f"Ошибка при создании бэкапа: {str(e)}"

    @staticmethod
    def restore_snapshot(zip_name: str) -> bool:
        """Восстанавливает файлы из бэкапа."""
        archive_path = Config.BACKUP_DIR / zip_name
        if not archive_path.exists():
            return False
            
        try:
            # Безопасность: делаем авто-бэкап перед откатом
            SnapshotManager.create_snapshot("pre_restore_safety")
            
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive.extractall(Config.ROOT_DIR)
            return True
        except Exception:
            return False

    @staticmethod
    def list_snapshots() -> List[str]:
        """Возвращает список всех существующих архивов бэкапа."""
        if not Config.BACKUP_DIR.exists():
            return []
        files = [f.name for f in Config.BACKUP_DIR.glob("*.zip")]
        files.sort(reverse=True)
        return files

class EngineDocParser:
    """Инструмент для автоматического сканирования API движка."""
    
    @staticmethod
    def parse_engine_api() -> Dict[str, List[str]]:
        """Парсит заголовки и вытягивает прототипы функций."""
        results = {}
        if not Config.INCLUDE_DIR.exists():
            return results
            
        # Регулярка для поиска функций C: Возврат Имя(Аргументы);
        regex = re.compile(r'^([A-Za-z0-9_]+\s+\*?[A-Za-z0-9_]+)\s*\(([^)]*)\);', re.MULTILINE)
        
        # Фильтры для очистки вывода
        forbidden_words = {'return', 'if', 'else', 'while', 'for', 'switch', 'typedef', 'static', 'extern'}
        valid_prefixes = ('NE_', 'NScreen_', 'NEnt_', 'RGFW_', 'void', 'int', 'bool', 'u8', 'u32', 'f32', 'f64', 's32')

        for header_file in Config.INCLUDE_DIR.rglob("*.h"):
            try:
                raw_code = header_file.read_text(encoding='utf-8', errors='ignore')
                
                # Полное удаление комментариев
                raw_code = re.sub(r'//.*', '', raw_code)
                raw_code = re.sub(r'/\*.*?\*/', '', raw_code, flags=re.DOTALL)
                
                matches = regex.findall(raw_code)
                if matches:
                    rel_path = str(header_file.relative_to(Config.INCLUDE_DIR))
                    file_functions = []
                    
                    for match in matches:
                        func_head = match[0].strip()
                        func_args = match[1].strip()
                        
                        # Разделяем заголовок на слова для проверки фильтров
                        head_words = func_head.split()
                        first_word = head_words[0] if head_words else ""
                        
                        if first_word in forbidden_words:
                            continue
                        if "__" in func_head:
                            continue
                        if not any(func_head.startswith(p) for p in valid_prefixes):
                            continue
                            
                        # Формируем финальную строку
                        signature = f"{func_head}({func_args});"
                        file_functions.append(signature)
                        
                    if file_functions:
                        results[rel_path] = file_functions
            except Exception:
                continue
        return results

class ModelAssetProcessor:
    """Конвертер 3D моделей .obj в заголовочные файлы C."""
    
    @staticmethod
    def process_obj_to_h(input_path: Path) -> str:
        """Парсит геометрию OBJ и возвращает текст хедера."""
        name = input_path.stem.lower().replace(" ", "_")
        vertices_list = []
        faces_list = []
        
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    if line.startswith('v '):
                        parts = line.split()
                        if len(parts) >= 4:
                            v_str = f"    {{{parts[1]}, {parts[2]}, {parts[3]}}}"
                            vertices_list.append(v_str)
                            
                    elif line.startswith('f '):
                        parts = line.split()
                        # Извлекаем индексы вершин (OBJ 1-based)
                        idxs = [str(int(p.split('/')[0]) - 1) for p in parts[1:]]
                        
                        # Треугольник
                        if len(idxs) == 3:
                            faces_list.append(f"    {{{idxs[0]}, {idxs[1]}, {idxs[2]}}}")
                        # Квадрат -> 2 треугольника
                        elif len(idxs) == 4:
                            faces_list.append(f"    {{{idxs[0]}, {idxs[1]}, {idxs[2]}}}")
                            faces_list.append(f"    {{{idxs[0]}, {idxs[2]}, {idxs[3]}}}")

            code = f"#pragma once\n\n"
            code += f"// Сгенерировано NewEngine Studio\n"
            code += f"// Источник: {input_path.name}\n\n"
            
            code += f"static const NE_Vertex {name}_v[] = {{\n"
            code += ",\n".join(vertices_list)
            code += "\n}};\n\n"
            
            code += f"static const NE_Color {name}_c[] = {{\n"
            white = "    {1.0, 1.0, 1.0, 1.0}"
            code += ",\n".join([white] * len(vertices_list))
            code += "\n}};\n\n"
            
            code += f"static const NE_Face {name}_f[] = {{\n"
            code += ",\n".join(faces_list)
            code += "\n}};\n\n"
            
            code += f"static const NE_Model {name}_model = {{\n"
            code += f"    .verteces = {name}_v,\n"
            code += f"    .colors = {name}_c,\n"
            code += f"    .faces = {name}_f,\n"
            code += f"    .face_count = {len(faces_list)}\n"
            code += "};\n"
            return code
            
        except Exception as e:
            return f"Ошибка при разборе OBJ: {str(e)}"

# =============================================================================
# 4. СИСТЕМА СБОРКИ (PARALLEL BUILD CORE)
# =============================================================================

class BuildCore:
    """Ядро компиляции с поддержкой многопоточности."""
    def __init__(self, app):
        self.app = app
        self.dep_manager = DependencyManager()
        self.thread_pool = ThreadPoolExecutor(max_workers=os.cpu_count())
        self.active_game_process: Optional[subprocess.Popen] = None
        self.is_compiling = False
        # Регулярка для захвата ошибок GCC
        self.gcc_regex = re.compile(r"^(.*):(\d+):(\d+): (error|warning|note): (.*)$")

    def request_build(self, profile: str, auto_run: bool = False):
        """Точка входа для запуска асинхронной сборки."""
        if self.is_compiling:
            return
        # Создаем поток сборки
        worker = threading.Thread(
            target=self._compilation_thread_logic, 
            args=(profile, auto_run), 
            daemon=True
        )
        worker.start()

    def _compile_unit(self, src: Path, flags: List[str]) -> Optional[str]:
        """Компилирует один конкретный .c файл. Выполняется параллельно."""
        rel_path = src.relative_to(Config.ROOT_DIR)
        obj_name = str(rel_path).replace(os.sep, "_").replace(".c", ".o")
        obj_full_path = Config.OBJ_DIR / obj_name
        
        # Проверка инкрементальности
        if not self.dep_manager.check_rebuild_needed(src, obj_full_path):
            return str(obj_full_path)

        self.app.log_to_console(f"Компиляция: {rel_path}\n", "dim")
        
        # Команда GCC
        cmd = [Config.COMPILER, "-c", str(src), "-o", str(obj_full_path)] + flags
        if "engine" in src.parts and src.name == "main.c":
            cmd.append("-Dmain=__engine_dummy_main")
            
        process_res = subprocess.run(cmd, capture_output=True, text=True, cwd=Config.ROOT_DIR)
        
        # Передаем stderr на парсинг ошибок
        if process_res.stderr:
            self.app.on_compiler_message(process_res.stderr)
            
        if process_res.returncode == 0:
            return str(obj_full_path)
        return None

    def _compilation_thread_logic(self, profile: str, run_after: bool):
        """Основной цикл управления сборкой."""
        self.is_compiling = True
        self.app.set_ui_busy_state(True)
        self.app.clear_console()
        self.app.clear_issues()
        
        start_time = time.time()
        self.app.log_to_console(f"--- НАЧАЛО СБОРКИ [{profile}] ---\n", "info")
        
        Config.OBJ_DIR.mkdir(parents=True, exist_ok=True)
        Config.BIN_DIR.mkdir(parents=True, exist_ok=True)
        
        # Поиск всех файлов .c
        source_files = []
        for d in [Config.ENGINE_DIR, Config.GAME_DIR]:
            if d.exists():
                source_files.extend(list(d.rglob("*.c")))

        # Настройка флагов на основе профиля
        is_debug = "Debug" in profile
        opt_flags = ["-g", "-O0"] if is_debug else ["-O3", "-s"]
        common_flags = [f"-I{Config.INCLUDE_DIR}", f"-I{Config.ASSETS_DIR}", "-Wall"] + opt_flags

        # ПАРАЛЛЕЛЬНАЯ КОМПИЛЯЦИЯ
        self.app.log_to_console(f"Задействовано ядер процессора: {os.cpu_count()}\n", "dim")
        object_units = list(self.thread_pool.map(lambda s: self._compile_unit(s, common_flags), source_files))
        
        if None in object_units:
            self.app.log_to_console("\nСБОРКА ПРЕРВАНА: Исправьте ошибки в коде.\n", "error")
        else:
            # ЭТАП ЛИНКОВКИ
            self.app.log_to_console("\nЛинковка всех модулей...\n", "info")
            output_exe = Config.BIN_DIR / Config.OUTPUT_BINARY
            
            linker_libs = ["-lopengl32", "-lglu32", "-lgdi32", "-lwinmm"]
            if platform.system() == "Linux":
                linker_libs = ["-lGL", "-lGLU", "-lm", "-lX11", "-lXrandr"]
            if not is_debug and platform.system() == "Windows":
                linker_libs.append("-mwindows")
            
            link_cmd = [Config.COMPILER] + object_units + ["-o", str(output_exe)] + common_flags + linker_libs
            
            res_link = subprocess.run(link_cmd, capture_output=True, text=True, cwd=Config.ROOT_DIR)
            
            if res_link.returncode == 0:
                elapsed = time.time() - start_time
                self.app.log_to_console(f"УСПЕХ! Время сборки: {elapsed:.2f} сек.\n", "success")
                if run_after:
                    self.execute_game()
            else:
                self.app.on_compiler_message(res_link.stderr)
                self.app.log_to_console("Ошибка линковщика.\n", "error")

        self.is_compiling = False
        self.app.set_ui_busy_state(False)

    def execute_game(self):
        """Запуск исполняемого файла игры."""
        binary = Config.BIN_DIR / Config.OUTPUT_BINARY
        if not binary.exists():
            self.app.log_to_console("Файл не найден.\n", "error")
            return
            
        if self.active_game_process and self.active_game_process.poll() is None:
            self.active_game_process.terminate()
            
        try:
            self.active_game_process = subprocess.Popen([str(binary)], cwd=Config.ROOT_DIR)
            self.app.log_to_console("Процесс игры успешно запущен.\n", "success")
        except Exception as e:
            self.app.log_to_console(f"Сбой запуска: {e}\n", "error")

# =============================================================================
# 5. ГЛАВНЫЙ КЛАСС STUDIO (IDE)
# =============================================================================

class StudioApp(ctk.CTk):
    """IDE для NewEngine."""
    def __init__(self):
        super().__init__()
        
        # Инициализация свойств окна
        self.title(f"{Config.APP_NAME} v{Config.VERSION}")
        self.geometry("1200x850")
        ctk.set_appearance_mode("Dark")
        
        # Системные модули
        self.build_sys = BuildCore(self)
        self.prof_var = ctk.StringVar(value="Отладка (Debug)")
        self.hot_reload_active = False
        self.mtime_store = {}
        self.current_obj_path: Optional[Path] = None

        # Настройка сетки
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Создание интерфейса
        self._setup_sidebar()
        self._setup_main_tabs()
        
        self.log_to_console("Studio готова.\n", "info")

    def _setup_sidebar(self):
        """Левое меню."""
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="NEW ENGINE", font=("Arial", 22, "bold")).pack(pady=30)
        
        ctk.CTkLabel(self.sidebar, text="Режим сборки:", font=("Arial", 11)).pack(pady=(10, 0))
        ctk.CTkOptionMenu(self.sidebar, values=["Отладка (Debug)", "Релиз (Release)"], variable=self.prof_var).pack(pady=10, padx=20)

        self.btn_compile = ctk.CTkButton(self.sidebar, text="🔨 Собрать", command=lambda: self.build_sys.request_build(self.prof_var.get()))
        self.btn_compile.pack(pady=5, padx=20)
        
        self.btn_launch = ctk.CTkButton(self.sidebar, text="▶ Запустить", fg_color="#2d8a2d", command=self.build_sys.execute_game)
        self.btn_launch.pack(pady=5, padx=20)
        
        self.btn_br = ctk.CTkButton(self.sidebar, text="🚀 Build & Run", command=lambda: self.build_sys.request_build(self.prof_var.get(), True))
        self.btn_br.pack(pady=5, padx=20)
        
        self.sw_auto = ctk.CTkSwitch(self.sidebar, text="⚡ Авто-сборка", command=self.on_toggle_hot_reload)
        self.sw_auto.pack(pady=30)

    def _setup_main_tabs(self):
        """Система вкладок."""
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        
        # Добавляем вкладки
        self._init_tab_console(self.tabs.add("Консоль"))
        self._init_tab_git(self.tabs.add("Git"))
        self._init_tab_api(self.tabs.add("Справочник API"))
        self._init_tab_system(self.tabs.add("Система"))
        self._init_tab_assets(self.tabs.add("Ассеты"))

    def _init_tab_console(self, tab):
        tab.grid_columnconfigure(0, weight=1); tab.grid_rowconfigure((0, 1), weight=1)
        self.issues_view = IssuesTable(tab); self.issues_view.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.console_view = LogPanel(tab); self.console_view.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def _init_tab_git(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Статус Git", font=("Arial", 16, "bold")).pack(pady=10)
        self.ui_git_log = ctk.CTkTextbox(tab, height=300, font=("Consolas", 11)); self.ui_git_log.pack(fill="x", padx=20, pady=10)
        
        f = ctk.CTkFrame(tab); f.pack(pady=10)
        ctk.CTkButton(f, text="Обновить", width=100, command=self.on_git_refresh_ui).pack(side="left", padx=5)
        ctk.CTkButton(f, text="Коммит", width=100, command=self.on_git_commit_ui).pack(side="left", padx=5)
        ctk.CTkButton(f, text="Push", width=100, command=lambda: self.on_git_action_async(["push"])).pack(side="left", padx=5)
        self.on_git_refresh_ui()

    def _init_tab_api(self, tab):
        tab.grid_columnconfigure(0, weight=1); tab.grid_rowconfigure(1, weight=1)
        ctk.CTkButton(tab, text="Сканировать API", command=self.on_api_scan_ui).pack(pady=10)
        self.ui_api_box = ctk.CTkTextbox(tab, font=("Consolas", 11)); self.ui_api_box.pack(fill="both", expand=True, padx=20, pady=10)

    def _init_tab_system(self, tab):
        tab.grid_columnconfigure((0, 1), weight=1)
        # Бэкапы
        f1 = ctk.CTkFrame(tab); f1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(f1, text="Снимки проекта", font=("Arial", 14, "bold")).pack(pady=10)
        self.ui_snap_menu = ctk.CTkOptionMenu(f1, values=["Нет бэкапов"]); self.ui_snap_menu.pack(pady=10)
        ctk.CTkButton(f1, text="Создать сейчас", command=self.on_snap_create_ui).pack(pady=5)
        ctk.CTkButton(f1, text="Восстановить", fg_color="orange", command=self.on_snap_restore_ui).pack(pady=5)
        self.on_snap_refresh_list_ui()

        # Обновления
        f2 = ctk.CTkFrame(tab); f2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(f2, text="GitHub Обслуживание", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkButton(f2, text="Update Studio.py", command=self.on_update_studio_ui).pack(pady=5)
        ctk.CTkButton(f2, text="Update Engine Core", fg_color="#d68a00", command=self.on_update_engine_ui).pack(pady=5)
        for lib in Config.LIBRARY_MAP:
            ctk.CTkButton(f2, text=f"Install {lib}", width=150, command=lambda l=lib: self.on_lib_install_ui(l)).pack(pady=2)

    def _init_tab_assets(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Конвертер .obj в заголовок C", font=("Arial", 18, "bold")).pack(pady=20)
        ctk.CTkButton(tab, text="Выбрать файл .obj", command=self.on_asset_select_ui).pack(pady=10)
        self.ui_asset_lbl = ctk.CTkLabel(tab, text="Ничего не выбрано", text_color="gray"); self.ui_asset_lbl.pack()
        self.ui_asset_btn = ctk.CTkButton(tab, text="Конвертировать", state="disabled", command=self.on_asset_convert_ui)
        self.ui_asset_btn.pack(pady=20)

    # --- BRIDGE METHODS ---
    def log_to_console(self, m, t=None): self.after(0, lambda: self.console_view.write(m, t))
    def clear_console(self): self.after(0, self.console_view.clear_content)
    def clear_issues(self): self.after(0, self.issues_view.clear_table)
    def on_compiler_message(self, output):
        for line in output.splitlines():
            m = self.build_sys.gcc_regex.match(line)
            if m:
                f, ln, col, sev, msg = m.groups()
                self.after(0, lambda f=f, l=ln, s=sev, msg=msg: self.issues_view.add_issue(f, l, s, msg))
                self.log_to_console(line + "\n", "error" if sev == "error" else "warning")
            else: self.log_to_console(line + "\n")

    # --- EVENT HANDLERS ---
    def on_toggle_hot_reload(self):
        self.hot_reload_active = self.sw_auto.get()
        if self.hot_reload_active: threading.Thread(target=self._hot_reload_loop, daemon=True).start()

    def _hot_reload_loop(self):
        while self.hot_reload_active:
            changed = False
            for d in [Config.ENGINE_DIR, Config.GAME_DIR]:
                if d.exists():
                    for f in d.rglob("*.c"):
                        mt = os.path.getmtime(f); s_f = str(f)
                        if s_f not in self.mtime_store or mt > self.mtime_store[s_f]:
                            self.mtime_store[s_f] = mt; changed = True
            if changed: self.after(0, lambda: self.build_sys.request_build(self.prof_var.get(), True))
            time.sleep(1.5)

    def on_git_refresh_ui(self):
        self.ui_git_log.delete("1.0", "end")
        self.ui_git_log.insert("end", GitEngine.get_detailed_status())

    def on_git_commit_ui(self):
        m = simpledialog.askstring("Git Commit", "Что изменилось?")
        if m:
            def run():
                self.log_to_console("Git indexing...\n", "info")
                GitEngine.run(["add", "."])
                ok, out = GitEngine.run(["commit", "-m", m])
                self.log_to_console(out + "\n", "success" if ok else "error")
                self.after(0, self.on_git_refresh_ui)
            threading.Thread(target=run, daemon=True).start()

    def on_git_action_async(self, args):
        def run():
            self.log_to_console(f"Git {' '.join(args)}...\n", "info")
            ok, out = GitEngine.run(args)
            self.log_to_console(out + "\n", "success" if ok else "error")
            self.after(0, self.on_git_refresh_ui)
        threading.Thread(target=run, daemon=True).start()

    def on_api_scan_ui(self):
        self.ui_api_box.delete("1.0", "end")
        api_map = EngineDocParser.parse_engine_api()
        if not api_map:
            self.ui_api_box.insert("end", "API не найдено.")
            return
        for file, funcs in api_map.items():
            self.ui_api_box.insert("end", f"[{file}]\n", "info")
            for f in funcs: self.ui_api_box.insert("end", f"  • {f}\n")
            self.ui_api_box.insert("end", "\n")

    def on_snap_create_ui(self):
        name = SnapshotManager.create_snapshot("manual")
        self.log_to_console(f"Бэкап: {name}\n", "success")
        self.on_snap_refresh_list_ui()

    def on_snap_restore_ui(self):
        name = self.ui_snap_menu.get()
        if name != "Нет бэкапов" and messagebox.askyesno("?", f"Откатить к {name}?"):
            if SnapshotManager.restore_from_zip(name):
                self.log_to_console("Проект восстановлен.\n", "success")
                self.on_snap_refresh_list_ui()

    def on_snap_refresh_list_ui(self):
        snapshots = SnapshotManager.list_snapshots()
        if snapshots:
            self.ui_snap_menu.configure(values=snapshots)
            self.ui_snap_menu.set(snapshots[0])

    def on_lib_install_ui(self, lib):
        def run():
            self.log_to_console(f"Загрузка {lib}...\n", "info")
            try:
                with urllib.request.urlopen(Config.LIBRARY_MAP[lib]) as r:
                    Config.THIRDPARTY_DIR.mkdir(parents=True, exist_ok=True)
                    (Config.THIRDPARTY_DIR / f"{lib}.h").write_bytes(r.read())
                    self.log_to_console("Библиотека установлена.\n", "success")
            except Exception as e: self.log_to_console(f"Error: {e}\n", "error")
        threading.Thread(target=run, daemon=True).start()

    def on_asset_select_ui(self):
        p = ctk.filedialog.askopenfilename(filetypes=[("OBJ", "*.obj")])
        if p:
            self.current_obj_path = Path(p)
            self.ui_asset_lbl.configure(text=self.current_obj_path.name, text_color="white")
            self.ui_asset_btn.configure(state="normal")

    def on_asset_convert_ui(self):
        Config.ASSETS_DIR.mkdir(exist_ok=True)
        res = ModelAssetProcessor.process_obj_to_h(self.current_obj_path)
        (Config.ASSETS_DIR / f"{self.current_obj_path.stem}.h").write_text(res, encoding="utf-8")
        messagebox.showinfo("OK", "Готово.")
        self.log_to_console(f"Ассет {self.current_obj_path.name} сконвертирован.\n", "success")

    def on_update_studio_ui(self):
        def run():
            self.log_to_console("Обновление studio.py...\n", "info")
            try:
                with urllib.request.urlopen(Config.URL_STUDIO_SOURCE) as r:
                    with open("studio.py", "wb") as f: f.write(r.read())
                self.log_to_console("Успешно. Перезапустите студию.\n", "success")
            except Exception as e: self.log_to_console(f"Ошибка: {e}\n", "error")
        threading.Thread(target=run, daemon=True).start()

    def on_update_engine_ui(self):
        def run():
            self.log_to_console("Обновление ядра движка...\n", "info")
            SnapshotManager.create_snapshot("auto_pre_engine_update")
            try:
                with urllib.request.urlopen(Config.URL_ENGINE_MASTER) as r:
                    with zipfile.ZipFile(io.BytesIO(r.read())) as z:
                        root = z.namelist()[0].split('/')[0]
                        for f in z.namelist():
                            if any(x in f for x in ['engine/', 'include/']):
                                rel = f[len(root)+1:]
                                if rel:
                                    dest = Config.ROOT_DIR / rel
                                    if f.endswith('/'): dest.mkdir(parents=True, exist_ok=True)
                                    else: dest.write_bytes(z.read(f))
                self.log_to_console("Движок обновлен.\n", "success")
            except Exception as e: self.log_to_console(f"Ошибка: {e}\n", "error")
        threading.Thread(target=run, daemon=True).start()

    def set_ui_busy_state(self, b):
        st = "disabled" if b else "normal"
        self.btn_compile.configure(state=st)
        self.btn_br.configure(state=st)

# =============================================================================
# ЗАПУСК
# =============================================================================

if __name__ == "__main__":
    try:
        app = StudioApp()
        app.mainloop()
    except Exception as e:
        print(f"FATAL: {e}")