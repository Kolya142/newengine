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
from tkinter import messagebox, ttk
from pathlib import Path
from typing import List, Optional, Dict, Set
from concurrent.futures import ThreadPoolExecutor

# --- КОНФИГУРАЦИЯ ---
class Config:
    APP_NAME = "NewEngine Studio"
    VERSION = "0.8.0 (Глубокая версия)"
    THEME = "Dark"
    
    ROOT_DIR = Path(os.getcwd())
    CONFIG_FILE = ROOT_DIR / "studio_config.json"
    LIB_MANIFEST = ROOT_DIR / "include" / "thirdparty" / "libs.json"
    
    BIN_DIR = ROOT_DIR / "bin"
    OBJ_DIR = BIN_DIR / "obj"
    INCLUDE_DIR = ROOT_DIR / "include"
    THIRDPARTY_DIR = INCLUDE_DIR / "thirdparty"
    ASSETS_DIR = ROOT_DIR / "assets"
    GAME_DIR = ROOT_DIR / "game"
    ENGINE_DIR = ROOT_DIR / "engine"
    
    COMPILER = "gcc"
    OUTPUT_NAME = "game.exe" if platform.system() == "Windows" else "game"
    
    URL_STUDIO_RAW = "https://raw.githubusercontent.com/crimbrodev/newengineSTUDIO/main/studio.py"
    URL_ENGINE_ZIP = "https://github.com/Kolya142/newengine/archive/refs/heads/main.zip"
    
    # Список библиотек для менеджера
    REMOTE_LIBS = {
        "stb_image": "https://raw.githubusercontent.com/nothings/stb/master/stb_image.h",
        "miniaudio": "https://raw.githubusercontent.com/mackron/miniaudio/master/miniaudio.h",
        "cJSON": "https://raw.githubusercontent.com/DaveGamble/cJSON/master/cJSON.h"
    }

# --- АНАЛИЗАТОР ЗАВИСИМОСТЕЙ (Deep Tracking) ---
class DependencyTracker:
    """Глубокий анализ связей между файлами для умной пересборки."""
    
    def get_includes(self, file_path: Path) -> List[str]:
        """Парсит файл и находит все локальные #include."""
        includes = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Ищем #include "..." или #include <...>
                found = re.findall(r'#include\s+["<]([^">]+)[">]', content)
                for inc in found:
                    includes.append(inc)
        except Exception: pass
        return includes

    def needs_rebuild(self, source_path: Path, object_path: Path) -> bool:
        """Рекурсивно проверяет, нужно ли пересобирать файл."""
        if not object_path.exists():
            return True
            
        obj_mtime = os.path.getmtime(object_path)
        
        # Проверка самого .c файла
        if os.path.getmtime(source_path) > obj_mtime:
            return True
            
        # Рекурсивная проверка всех хедеров (.h)
        visited = set()
        stack = self.get_includes(source_path)
        
        while stack:
            inc = stack.pop()
            if inc in visited: continue
            visited.add(inc)
            
            # Ищем хедер в папках проекта
            for p in [Config.INCLUDE_DIR, Config.ASSETS_DIR, source_path.parent]:
                h_path = p / inc
                if h_path.exists():
                    if os.path.getmtime(h_path) > obj_mtime:
                        return True
                    stack.extend(self.get_includes(h_path))
                    break
        return False

# --- СИСТЕМА СБОРКИ (Параллельная) ---
class BuildSystem:
    def __init__(self, app):
        self.app = app
        self.tracker = DependencyTracker()
        # Пул потоков: используем все ядра процессора для компиляции
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count())
        self.game_process: Optional[subprocess.Popen] = None
        self.is_building = False
        self.err_pattern = re.compile(r"^(.*):(\d+):(\d+): (error|warning|note): (.*)$")

    def build(self, profile="Отладка (Debug)", run_after=False):
        if self.is_building: return
        threading.Thread(target=self._run_build, args=(profile, run_after), daemon=True).start()

    def _compile_single_file(self, src_path: Path, common_flags: List[str]) -> Optional[str]:
        """Компиляция одного файла."""
        rel = src_path.relative_to(Config.ROOT_DIR)
        obj_path = Config.OBJ_DIR / str(rel).replace(os.sep, "_").replace(".c", ".o")
        
        if not self.tracker.needs_rebuild(src_path, obj_path):
            return str(obj_path)

        cmd = [Config.COMPILER, "-c", str(src_path), "-o", str(obj_path)] + common_flags
        # Трюк для подавления main в движке
        if "engine" in src_path.parts and src_path.name == "main.c":
            cmd.append("-Dmain=__engine_dummy_main")

        self.app.log_to_console(f"Компиляция: {rel}\n", "dim")
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=Config.ROOT_DIR)
        
        if proc.stderr:
            self.app.parse_gcc_output(proc.stderr)
        
        return str(obj_path) if proc.returncode == 0 else None

    def _run_build(self, profile, run_after):
        self.is_building = True
        self.app.set_ui_busy(True)
        self.app.clear_console()
        self.app.clear_issues()
        
        start_time = time.time()
        self.app.log_to_console(f"=== ЗАПУСК СБОРКИ ({profile}) ===\n", "info")
        
        Config.OBJ_DIR.mkdir(parents=True, exist_ok=True)
        
        sources = []
        for d in [Config.ENGINE_DIR, Config.GAME_DIR]:
            if d.exists(): sources.extend(list(d.rglob("*.c")))

        # Флаги в зависимости от профиля
        is_debug = "Debug" in profile or "Отладка" in profile
        p_flags = ["-g", "-O0"] if is_debug else ["-O3", "-s"]
        common = [f"-I{Config.INCLUDE_DIR}", f"-I{Config.ASSETS_DIR}", "-Wall"] + p_flags

        # Запускаем параллельную компиляцию
        results = list(self.executor.map(lambda s: self._compile_single_file(s, common), sources))
        
        if None in results:
            self.app.log_to_console("\nОШИБКА: Сборка прервана из-за ошибок компиляции.\n", "error")
        else:
            self.app.log_to_console("\nЛинковка (сборка в один файл)...\n", "info")
            out = Config.BIN_DIR / Config.OUTPUT_NAME
            l_flags = ["-lopengl32", "-lglu32", "-lgdi32", "-lwinmm"] if platform.system() == "Windows" else ["-lGL", "-lGLU", "-lm", "-lX11", "-lXrandr"]
            if not is_debug and platform.system() == "Windows": 
                l_flags.append("-mwindows") # Прячем консоль в релизе
            
            cmd = [Config.COMPILER] + results + ["-o", str(out)] + common + l_flags
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=Config.ROOT_DIR)
            
            if proc.returncode == 0:
                elapsed = time.time() - start_time
                self.app.log_to_console(f"УСПЕХ! Собрано за {elapsed:.2f} сек.\n", "success")
                if run_after: self.run_game()
            else:
                self.app.parse_gcc_output(proc.stderr)
                self.app.log_to_console("ОШИБКА: Линковщик завершился со сбоем.\n", "error")

        self.is_building = False
        self.app.set_ui_busy(False)

    def run_game(self):
        exe = Config.BIN_DIR / Config.OUTPUT_NAME
        if not exe.exists(): 
            self.app.log_to_console("ОШИБКА: Сначала скомпилируйте игру.\n", "error")
            return
        if self.game_process and self.game_process.poll() is None:
            self.game_process.terminate()
        try:
            self.game_process = subprocess.Popen([str(exe)], cwd=Config.ROOT_DIR)
            self.app.log_to_console("Игра запущена.\n", "success")
        except Exception as e: self.app.log_to_console(f"Сбой запуска: {e}\n", "error")

# --- МЕНЕДЖЕР БИБЛИОТЕК ---
class LibraryManager:
    def __init__(self, log_func):
        self.log = log_func
        self.manifest: Dict = {}
        self._load()

    def _load(self):
        if Config.LIB_MANIFEST.exists():
            try: self.manifest = json.loads(Config.LIB_MANIFEST.read_text())
            except: self.manifest = {}

    def _save(self):
        Config.THIRDPARTY_DIR.mkdir(parents=True, exist_ok=True)
        Config.LIB_MANIFEST.write_text(json.dumps(self.manifest, indent=4))

    def install(self, name: str, url: str):
        self.log(f"Загрузка библиотеки {name}...\n", "info")
        try:
            with urllib.request.urlopen(url) as r:
                content = r.read()
                dest = Config.THIRDPARTY_DIR / (name + ".h")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
                
                self.manifest[name] = {
                    "installed_at": time.ctime(),
                    "hash": hashlib.md5(content).hexdigest()
                }
                self._save()
                self.log(f"Библиотека {name} установлена.\n", "success")
        except Exception as e: self.log(f"Ошибка сети: {e}\n", "error")

# --- ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
class LogPanel(ctk.CTkTextbox):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(state="disabled", font=("Consolas", 11))
        self.tag_config("error", foreground="#ff5555")
        self.tag_config("warning", foreground="#ffb86c")
        self.tag_config("success", foreground="#50fa7b")
        self.tag_config("info", foreground="#8be9fd")
        self.tag_config("dim", foreground="#6272a4")

    def write(self, t, g=None):
        self.configure(state="normal"); self.insert("end", t, g); self.see("end"); self.configure(state="disabled")
    def clear(self):
        self.configure(state="normal"); self.delete("1.0", "end"); self.configure(state="disabled")

class StudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{Config.APP_NAME} v{Config.VERSION}")
        self.geometry("1100x850")
        ctk.set_appearance_mode("Dark")
        
        # Системные модули
        self.build_sys = BuildSystem(self)
        self.lib_mgr = LibraryManager(self.log_to_console)
        self.err_pattern = re.compile(r"^(.*):(\d+):(\d+): (error|warning|note): (.*)$")

        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)

        # Боковая панель
        self.side = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.side.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.side, text="NEW ENGINE", font=("Arial", 22, "bold")).pack(pady=30)
        
        ctk.CTkLabel(self.side, text="Режим сборки:", font=("Arial", 11)).pack()
        self.prof_var = ctk.StringVar(value="Отладка (Debug)")
        ctk.CTkOptionMenu(self.side, values=["Отладка (Debug)", "Релиз (Release)"], variable=self.prof_var).pack(pady=10)

        self.btn_build = ctk.CTkButton(self.side, text="🔨 Собрать", command=lambda: self.build_sys.build(self.prof_var.get()))
        self.btn_build.pack(pady=5, padx=20)
        
        self.btn_run = ctk.CTkButton(self.side, text="▶ Запустить игру", fg_color="#2d8a2d", command=self.build_sys.run_game)
        self.btn_run.pack(pady=5, padx=20)

        self.btn_br = ctk.CTkButton(self.side, text="🚀 Собрать и Запустить", command=lambda: self.build_sys.build(self.prof_var.get(), True))
        self.btn_br.pack(pady=5, padx=20)

        self.sw_auto = ctk.CTkSwitch(self.side, text="⚡ Авто-сборка", command=self.toggle_watcher)
        self.sw_auto.pack(pady=20)

        # Вкладки
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        
        self.setup_logs(self.tabs.add("Консоль и Ошибки"))
        self.setup_libs(self.tabs.add("Библиотеки"))
        self.setup_assets(self.tabs.add("Ассеты"))
        self.setup_system(self.tabs.add("Система"))

        self.log_to_console("NewEngine Studio готова к работе.\n", "success")

    def setup_logs(self, tab):
        tab.grid_columnconfigure(0, weight=1); tab.grid_rowconfigure((0, 1), weight=1)
        
        # Темная таблица ошибок
        st = ttk.Style()
        st.theme_use("clam")
        st.configure("Treeview", background="#1d1d1d", foreground="white", fieldbackground="#1d1d1d", borderwidth=0)
        st.configure("Treeview.Heading", background="#333333", foreground="white", borderwidth=0)
        
        self.issues_tree = ttk.Treeview(tab, columns=("F", "L", "T", "M"), show='headings')
        self.issues_tree.heading("F", text="Файл"); self.issues_tree.heading("L", text="Стр"); self.issues_tree.heading("T", text="Тип"); self.issues_tree.heading("M", text="Сообщение")
        self.issues_tree.column("F", width=150); self.issues_tree.column("L", width=50); self.issues_tree.column("T", width=80); self.issues_tree.column("M", width=500)
        self.issues_tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.console = LogPanel(tab)
        self.console.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def setup_libs(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Менеджер внешних библиотек (C)", font=("Arial", 18, "bold")).pack(pady=15)
        
        for name, url in Config.REMOTE_LIBS.items():
            f = ctk.CTkFrame(tab); f.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(f, text=name, font=("Arial", 13, "bold")).pack(side="left", padx=15)
            ctk.CTkButton(f, text="Установить", width=120, command=lambda n=name, u=url: self.install_lib(n, u)).pack(side="right", padx=10, pady=10)

    def setup_assets(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Конвертер OBJ моделей в C-код", font=("Arial", 18, "bold")).pack(pady=20)
        self.btn_sel = ctk.CTkButton(tab, text="Выбрать .obj файл", command=self.select_obj).pack(pady=10)
        self.lbl_asset = ctk.CTkLabel(tab, text="Файл не выбран"); self.lbl_asset.pack()
        self.btn_convert = ctk.CTkButton(tab, text="Начать конвертацию", state="disabled", command=self.convert_obj)
        self.btn_convert.pack(pady=20)

    def setup_system(self, tab):
        tab.grid_columnconfigure((0,1), weight=1)
        # Диагностика
        f1 = ctk.CTkFrame(tab); f1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(f1, text="Диагностика системы", font=("Arial", 14, "bold")).pack(pady=10)
        self.diag_txt = ctk.CTkTextbox(f1, height=200); self.diag_txt.pack(fill="x", padx=10)
        ctk.CTkButton(f1, text="Запустить проверку", command=self.run_diag).pack(pady=10)
        
        # Обновление
        f2 = ctk.CTkFrame(tab); f2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(f2, text="Обновление с GitHub", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkButton(f2, text="Обновить Студию", command=self.update_studio_self).pack(pady=5)
        ctk.CTkButton(f2, text="Обновить Движок", fg_color="orange", command=self.update_engine_self).pack(pady=5)

    # --- ЛОГИКА ---
    def parse_gcc_output(self, text):
        for line in text.splitlines():
            m = self.err_pattern.match(line)
            if m:
                f, ln, c, s, msg = m.groups()
                self.after(0, lambda f=f, ln=ln, s=s, msg=msg: self.issues_tree.insert("", "end", values=(f, ln, s, msg)))
                self.log_to_console(line + "\n", "error" if s == "error" else "warning")
            else: self.log_to_console(line + "\n")

    def install_lib(self, n, u):
        threading.Thread(target=lambda: self.lib_mgr.install(n, u), daemon=True).start()

    def select_obj(self):
        p = ctk.filedialog.askopenfilename(filetypes=[("3D Модель", "*.obj")])
        if p:
            self.obj_path = Path(p)
            self.lbl_asset.configure(text=f"Выбран: {self.obj_path.name}")
            self.btn_convert.configure(state="normal")

    def convert_obj(self):
        Config.ASSETS_DIR.mkdir(exist_ok=True)
        # Вызов статической логики конвертации
        res = AssetConverter.convert_obj_to_h(self.obj_path)
        (Config.ASSETS_DIR / (self.obj_path.stem + ".h")).write_text(res)
        messagebox.showinfo("Готово", f"Файл {self.obj_path.stem}.h создан в папке assets/")

    def run_diag(self):
        self.diag_txt.delete("1.0", "end")
        try:
            gcc_v = subprocess.run([Config.COMPILER, "--version"], capture_output=True, text=True).stdout.split('\n')[0]
            self.diag_txt.insert("end", f"Компилятор: ✅ {gcc_v}\n")
        except: self.diag_txt.insert("end", "Компилятор: ❌ НЕ НАЙДЕН\n")
        
        for name, path in [("Движок", Config.ENGINE_DIR), ("Игра", Config.GAME_DIR), ("Заголовки", Config.INCLUDE_DIR)]:
            status = "✅" if path.exists() else "❌"
            self.diag_txt.insert("end", f"Папка {name}: {status}\n")

    def update_studio_self(self):
        threading.Thread(target=lambda: self._upd_task(Config.URL_STUDIO_RAW, "studio.py"), daemon=True).start()

    def update_engine_self(self):
        threading.Thread(target=self._upd_engine_task, daemon=True).start()

    def _upd_task(self, url, filename):
        self.log_to_console(f"Обновление {filename}...\n", "info")
        try:
            with urllib.request.urlopen(url) as r:
                data = r.read()
                with open(filename + ".tmp", "wb") as f: f.write(data)
            os.replace(filename + ".tmp", filename)
            self.log_to_console("Обновление завершено! Перезапустите студию.\n", "success")
        except Exception as e: self.log_to_console(f"Ошибка обновления: {e}\n", "error")

    def _upd_engine_task(self):
        self.log_to_console("Обновление движка...\n", "info")
        try:
            with urllib.request.urlopen(Config.URL_ENGINE_ZIP) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
                root = z.namelist()[0].split('/')[0]
                for f in z.namelist():
                    if 'engine/' in f or 'include/' in f:
                        rel = f[len(root)+1:]
                        if rel:
                            dest = Config.ROOT_DIR / rel
                            if f.endswith('/'): dest.mkdir(parents=True, exist_ok=True)
                            else: dest.write_bytes(z.read(f))
            self.log_to_console("Ядро движка успешно обновлено.\n", "success")
        except Exception as e: self.log_to_console(f"Ошибка обновления движка: {e}\n", "error")

    def toggle_watcher(self):
        self.watcher_active = self.sw_auto.get()
        if self.watcher_active: threading.Thread(target=self._watcher_loop, daemon=True).start()

    def _watcher_loop(self):
        file_times = {}
        while self.watcher_active:
            changed = False
            for d in [Config.ENGINE_DIR, Config.GAME_DIR]:
                if d.exists():
                    for f in d.rglob("*.c"):
                        mt = os.path.getmtime(f)
                        if str(f) not in file_times or mt > file_times[str(f)]:
                            file_times[str(f)] = mt; changed = True
            if changed: self.after(0, lambda: self.build_sys.build(self.prof_var.get(), True))
            time.sleep(1)

    def log_to_console(self, t, tag=None): self.after(0, lambda: self.console.write(t, tag))
    def clear_console(self): self.after(0, lambda: self.console.clear())
    def add_issue(self, f, l, s, m): self.after(0, lambda: self.issues_tree.insert("", "end", values=(f, l, s, m)))
    def clear_issues(self): self.after(0, lambda: [self.issues_tree.delete(i) for i in self.issues_tree.get_children()])
    
    def set_ui_busy(self, b):
        s = "disabled" if b else "normal"
        self.btn_build.configure(state=s)
        self.btn_run.configure(state=s)
        self.btn_br.configure(state=s)

# Вспомогательный класс для конвертации (чтобы всё было в одном месте)
class AssetConverter:
    @staticmethod
    def convert_obj_to_h(obj_path: Path) -> str:
        name = obj_path.stem.lower().replace(" ", "_")
        vertices, faces = [], []
        try:
            with open(obj_path, 'r') as f:
                for line in f:
                    if line.startswith('v '):
                        p = line.split()
                        vertices.append(f"    {{{p[1]}, {p[2]}, {p[3]}}}")
                    elif line.startswith('f '):
                        p = line.split()
                        idx = [str(int(part.split('/')[0]) - 1) for part in p[1:]]
                        if len(idx) == 3: faces.append(f"    {{{idx[0]}, {idx[1]}, {idx[2]}}}")
                        elif len(idx) == 4:
                            faces.append(f"    {{{idx[0]}, {idx[1]}, {idx[2]}}}")
                            faces.append(f"    {{{idx[0]}, {idx[2]}, {idx[3]}}}")
            content = f"#pragma once\n\n// Сгенерировано NewEngine Studio\n\n"
            content += f"static const NE_Vertex {name}_v[] = {{\n" + ",\n".join(vertices) + "\n}};\n\n"
            content += f"static const NE_Color {name}_c[] = {{\n" + ",\n".join(["    {1.0, 1.0, 1.0, 1.0}"] * len(vertices)) + "\n}};\n\n"
            content += f"static const NE_Face {name}_f[] = {{\n" + ",\n".join(faces) + "\n}};\n\n"
            content += f"static const NE_Model {name}_model = {{\n    {name}_v,\n    {name}_c,\n    {name}_f,\n    {len(faces)}\n}};\n"
            return content
        except Exception as e: return f"ОШИБКА: {str(e)}"

if __name__ == "__main__":
    app = StudioApp(); app.mainloop()