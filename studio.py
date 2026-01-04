active_studio_name = \
"NewEngine Studio v0.10.0"
"""
An interactive development environment for the Kolya142's engine "NewEngine".

License: MIT

Mainteiners:
crinbrodev - vibecoded this studio in Russian
Kolya142 - made it useable, deleted code&text trash and translated it to English
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

# TODOO: Add JSON parser or something like this.




THEME_DARK = 0
THEME_LIGHT = 1
# TODO: Add these themes
#  THEME_PAPER = 2
#  THEME_CONTRAST = 3

class Config:
    """
    Class that centerilizes configuration of the IDE.
    """
    APP_NAME = active_studio_name
    THEME = THEME_LIGHT
    ACCENT_COLOR = "blue"

    ROOT_DIR = Path(os.getcwd())

    BIN_DIR = ROOT_DIR / "bin"
    OBJ_DIR = BIN_DIR / "obj"

    INCLUDE_DIR = ROOT_DIR / "include"
    THIRDPARTY_DIR = INCLUDE_DIR / "thirdparty"
    ASSETS_DIR = ROOT_DIR / "assets"
    GAME_DIR = ROOT_DIR / "game"
    ENGINE_DIR = ROOT_DIR / "engine"

    COMPILER = "gcc"

    # TODO: MacOS uses they own executeable format, not ELF.
    OUTPUT_WIN64_BINARY = "game.exe"
    OUTPUT_UNIXS_BINARY = "game"

    if platform.system() == "Windows":
        OUTPUT_BINARY = OUTPUT_WIN64_BINARY
    else:
        OUTPUT_BINARY = OUTPUT_UNIXS_BINARY

    URL_STUDIO_SOURCE = "https://raw.githubusercontent.com/Kolya142/newengine/main/studio.py"
    URL_ENGINE_MASTER = "https://github.com/Kolya142/newengine/archive/refs/heads/main.zip"

if Config.THEME == THEME_DARK:
    CS = [
        "#ff5555",  # 0
        "#ffb86c",  # 1
        "#50fa7b",  # 2
        "#8be9fd",  # 3
        "#6272a4",  # 4

        "#1d1d1d",  # 5
        "#ffffff",  # 6
        "#1d1d1d",  # 7
        "#333333",  # 8
        "#ffffff",  # 9
        "#1f538d",  # 10

        "#2d8a2d",  # 11

        "#d68a00",  # 12
    ]
elif Config.THEME == THEME_LIGHT:
    CS = [
        "#ffaaaa",  # 0
        "#ffb86c",  # 1
        "#50fa7b",  # 2
        "#8be9fd",  # 3
        "#6272a4",  # 4

        "#eaeaea",  # 5
        "#000000",  # 6
        "#eaeaea",  # 7
        "#dddddd",  # 8
        "#000000",  # 9
        "#7fb3ed",  # 10

        "#8dea8d",  # 11

        "#d68a00",  # 12
    ]




class LogWidget(ctk.CTkTextbox):
    """
    Loging console widget.
    Used to output logs with color indication.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(state="disabled", font=("FreeMono", 11))

        self.tag_config("error", foreground=CS[0])
        self.tag_config("warning", foreground=CS[1])
        self.tag_config("success", foreground=CS[2])
        self.tag_config("info", foreground=CS[3])
        self.tag_config("dim", foreground=CS[4])
        self.do_scroll = True

    def log(self, text: str, tag: Optional[str] = None):
        self.configure(state="normal")
        self.insert("end", text, tag)
        if self.do_scroll:
            self.see("end")
        self.configure(state="disabled")

    def clear_content(self):
        """Полная очистка консоли."""
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")

class CompilerIssuesTable(ctk.CTkFrame):
    """
    It's just like LogWidget but for the compiler.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # TODOO: Some users may want to use light theme.
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=CS[5],
            foreground=CS[6],
            fieldbackground=CS[7],
            borderwidth=0,
            rowheight=25,
            font=("FreeMono", 10)
        )
        style.configure(
            "Treeview.Heading",
            background=CS[8],
            foreground=CS[9],
            borderwidth=1,
            font=("FreeMono", 10, "bold")
        )
        style.map("Treeview", background=[('selected', CS[10])])

        columns = ("File", "Line", "Severity", "Message")
        self.tree = ttk.Treeview(self, columns=columns, show='headings')

        self.tree.heading("File", text="File")
        self.tree.heading("Line", text="Line")
        self.tree.heading("Severity", text="Type")
        self.tree.heading("Message", text="Text")

        self.tree.column("File", width=140, anchor="w")
        self.tree.column("Line", width=50, anchor="center")
        self.tree.column("Severity", width=90, anchor="center")
        self.tree.column("Message", width=450, anchor="w")

        # Scrollbar
        self.v_scroll = ctk.CTkScrollbar(self, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.v_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        self.v_scroll.pack(side="right", fill="y")

    def add_issue(self, file: str, line: str, severity: str, message: str):
        icon = "ERROR" if severity.lower() == "error" else "WARING"
        self.tree.insert("", "end", values=(file, line, f"{icon} {severity}", message))

    def clear_issues(self):
        for row in self.tree.get_children():
            self.tree.delete(row)




class DependencyManager:
    """Analysis include (#include) system."""

    def extract_includes(self, file_path: Path) -> List[str]:
        """Extracts all includes by a file name."""
        if not file_path.exists():
            return []

        includes_found = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # #include "file.h"<file.h>
                pattern = r'#include\s+["<]([^">]+)[">]'
                matches = re.findall(pattern, content)
                for m in matches:
                    includes_found.append(m)
        except Exception as e:
            print(f"[DependencyManager] Error when reading {file_path.name}: {e}")

        return includes_found

    def check_rebuild_needed(self, source_c: Path, object_o: Path) -> bool:
        """Checks is rebuild needed using recursive dependency analyser."""

        if not object_o.exists():  # When there is no target build, because THERE IS NO TARGET BUILD.
            return True

        target_time = os.path.getmtime(object_o)

        if os.path.getmtime(__file__) > target_time:
            return True

        if os.path.getmtime(source_c) > target_time:
            return True

        visited = set()
        stack = self.extract_includes(source_c)

        while stack:
            header_name = stack.pop()
            if header_name in visited:
                continue
            visited.add(header_name)

            for folder in [Config.INCLUDE_DIR, Config.ASSETS_DIR, source_c.parent]:
                h_path = folder / header_name
                if h_path.exists():
                    if os.path.getmtime(h_path) > target_time:
                        return True
                    stack.extend(self.extract_includes(h_path))
                    break
        return False

class GitEngine:
    """Abstration layer for the Git."""

    @staticmethod
    def is_installed() -> bool:
        """Checks is there `git' installed."""
        try:
            subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    def run_command(args: List[str]) -> Tuple[bool, str]:
        """Executes Git command."""
        if not GitEngine.is_installed():
            return False, "Install Git first."

        process = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=Config.ROOT_DIR,
            encoding='utf-8',
            errors='replace'
        )
        if process.returncode == 0:
            output = process.stdout if process.stdout else "Command completed successfully."
            return True, output
        else:
            return False, process.stderr if process.stderr else (process.stdout if process.stdout else "Unknown Git error.")  # Git shall log error, but ...

    @staticmethod
    def get_repo_status() -> str:
        git_dir = Config.ROOT_DIR / ".git"
        if not git_dir.exists():
            return "The folder does not contain git repo."

        ok, out = GitEngine.run_command(["status", "--short"])
        if ok:
            return out if out.strip() else "No Changes."
        return f"Git error: {out}"

# I removed SnapshotManager because Git already has own snapshot system called `commits'

def parse_engine_api() -> Dict[str, List[str]]:
    results: Dict[str, List[str]] = {}
    if not Config.INCLUDE_DIR.exists():
        return results

    # Regexp for parsing C function definitions.
    # TODOO: crimbrodev forgot about extern/const/unsigned
    regex = re.compile(r'^([A-Za-z0-9_]+\s+\*?[A-Za-z0-9_]+)\s*\(([^)]*)\);', re.MULTILINE)

    forbidden_words = {'return', 'if', 'else', 'while', 'for', 'switch', 'typedef', 'static'}
    valid_prefixes = (
        'N',  # NewEngine.
        'void', 'char', 'short', 'int', 'long', 'float', 'double',  # C types
        'u8', 's8', 'u16', 's16', 'u32', 's32', 'u64', 's64', 'f32', 'f64'  # Simplified types.
    )

    for header_file in Config.INCLUDE_DIR.rglob("*.h"):
        try:
            raw_code = header_file.read_text(encoding='utf-8', errors='ignore')

            raw_code = re.sub(r'//.*', '', raw_code)
            raw_code = re.sub(r'/\*.*?\*/', '', raw_code, flags=re.DOTALL)

            matches = regex.findall(raw_code)
            if matches:
                rel_path = str(header_file.relative_to(Config.INCLUDE_DIR))
                file_functions = []

                for match in matches:
                    func_head = match[0].strip()
                    func_args = match[1].strip()

                    head_words = func_head.split()
                    first_word = head_words[0] if head_words else ""

                    if first_word in forbidden_words:
                        continue
                    if "__" in func_head:
                        continue
                    if not any(func_head.startswith(p) for p in valid_prefixes):
                        continue
                    file_functions.append(f"{func_head}({func_args});")

                if file_functions:
                    results[rel_path] = file_functions
        except Exception:
            continue
    return results

# TODO: I want to do it in engine it self, so this is kinda useless

def convert_obj_to_c(input_path: Path) -> str:
    """Converts .obj to .c."""
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
                    idxs = [str(int(p.split('/')[0]) - 1) for p in parts[1:]]

                    if len(idxs) == 3:
                        faces_list.append(f"    {{{idxs[0]}, {idxs[1]}, {idxs[2]}}}")
                    else:
                        # Splitting polygons to triangles.
                        assert (len(idxs)-3)%2 != 0, f"Invalid polygon in .obj file \"{input_path}\"."
                        for i in range(0, len(idnx), 2):
                            faces_list.append(f"    {{{idxs[i]}, {idxs[i+1]}, {idxs[(i+2)%idnx]}}}")

        code = f"#pragma once\n\n"
        code += f"// Generated by NewEngine Studio\n"
        code += f"// Source: {input_path.name}\n\n"

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
        return f"Error when parsing .obj file \"{input_file}\": {str(e)}"





class BuildCore:
    """Parallel Compilation System."""
    def __init__(self, app):
        self.app = app
        self.dep_manager = DependencyManager()
        self.thread_pool = ThreadPoolExecutor(max_workers=os.cpu_count())
        self.active_game_process: Optional[subprocess.Popen] = None
        self.is_compiling = False
        self.gcc_regex = re.compile(r"^(.*):(\d+):(\d+): (error|warning|note): (.*)$")

    def request_build(self, profile: str, /, auto_run: bool = False, force: bool = False):
        """Requests threaded build."""
        if self.is_compiling:
            return
        worker = threading.Thread(
            target=self._compilation_thread_logic,
            args=(profile, auto_run, force),
            daemon=True
        )
        worker.start()

    def _compile_unit(self, src: Path, flags: List[str], force: bool) -> Optional[str]:
        rel_path = src.relative_to(Config.ROOT_DIR)
        obj_name = str(rel_path).replace(os.sep, "_").replace(".c", ".o")
        obj_full_path = Config.OBJ_DIR / obj_name

        if not force:
            if not self.dep_manager.check_rebuild_needed(src, obj_full_path):
                return str(obj_full_path)

        self.app.log_to_console(f"Compiling: {rel_path}\n", "dim")

        # TODOOO: Some compilers (eg. MSVC) requests different arguments
        cmd = [Config.COMPILER, "-c", str(src), "-o", str(obj_full_path)] + flags

        process_res = subprocess.run(cmd, capture_output=True, text=True, cwd=Config.ROOT_DIR)

        if process_res.stderr:
            self.app.on_compiler_message(process_res.stderr)

        if process_res.returncode == 0:
            return str(obj_full_path)
        return None

    def _compilation_thread_logic(self, profile: str, run_after: bool, force: bool):
        self.is_compiling = True
        self.app.set_ui_busy_state(True)
        self.app.clear_console()
        self.app.clear_issues()

        start_time = time.time()
        self.app.log_to_console(f"--- STARTING BUILD USING PROFILE [{profile}] ---\n", "info")

        Config.OBJ_DIR.mkdir(parents=True, exist_ok=True)
        Config.BIN_DIR.mkdir(parents=True, exist_ok=True)

        with open(Config.BIN_DIR / ".gitignore", 'w') as f:
            f.write("# NO BINARIES IN MY REPO\n*")

        source_files = []
        for d in [Config.ENGINE_DIR, Config.GAME_DIR]:
            if d.exists():
                source_files.extend(list(d.rglob("*.c")))

        is_debug = "Debug" in profile
        # O3 is too agressive optimization
        opt_flags = []
        match profile:
            case "Debug":
                opt_flags = ["-g", "-O0"]
            case "Release":
                opt_flags = ["-s", "-O3"]
            case "Not stripped Release":
                opt_flags = ["-O3"]
            case "Low-optimization Release":
                opt_flags = ["-s"]
        common_flags = [f"-I{Config.INCLUDE_DIR}", f"-I{Config.ASSETS_DIR}", "-Wall"] + opt_flags

        self.app.log_to_console(f"--- Using {os.cpu_count()} CPU Cores ---\n", "dim")
        object_units = list(self.thread_pool.map(lambda s: self._compile_unit(s, common_flags, force), source_files))

        if None in object_units:
            self.app.log_to_console("\nCompilation errors.\n", "error")
        else:
            self.app.log_to_console("\n--- LINKING ---\n", "info")
            output_exe = Config.BIN_DIR / Config.OUTPUT_BINARY

            linker_libs = ["-lopengl32", "-lgdi32"]
            if platform.system() == "Linux":
                linker_libs = ["-lGL", "-lm", "-lX11", "-lXrandr"]
            if not is_debug and platform.system() == "Windows":
                linker_libs.append("-mwindows")

            link_cmd = [Config.COMPILER] + object_units + ["-o", str(output_exe)] + common_flags + linker_libs

            res_link = subprocess.run(link_cmd, capture_output=True, text=True, cwd=Config.ROOT_DIR)

            if res_link.returncode == 0:
                elapsed = time.time() - start_time
                self.app.log_to_console(f"Built successfully for {elapsed:.2f}s.\n", "success")
                if run_after:
                    self.execute_game()
            else:
                self.app.on_compiler_message(res_link.stderr)
                self.app.log_to_console("Linking error\n", "error")

        self.is_compiling = False
        self.app.set_ui_busy_state(False)

    def execute_game(self):
        binary = Config.BIN_DIR / Config.OUTPUT_BINARY
        if not binary.exists():
            self.request_build("Release")
            return

        if self.active_game_process and self.active_game_process.poll() is None:
            self.active_game_process.terminate()

        try:
            self.active_game_process = subprocess.Popen([str(binary)], cwd=Config.ROOT_DIR)
            self.app.log_to_console("Game executed successfully.\n", "success")
        except Exception as e:
            self.app.log_to_console(f"Failed to execute the game: {e}\n", "error")





class StudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{Config.APP_NAME}")
        self.geometry("1200x850")
        ctk.set_appearance_mode("Dark" if Config.THEME == THEME_DARK else "White")

        self.build_sys = BuildCore(self)
        self.prof_var = ctk.StringVar(value="Debug")
        self.hot_reload_active = False
        self.mtime_store = {}
        self.current_obj_path: Optional[Path] = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._setup_sidebar()
        self._setup_main_tabs()

        self.log_to_console("Core initialized.\n", "info")

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="New Engine", font=("Arial", 22, "bold")).pack(pady=30)

        ctk.CTkLabel(self.sidebar, text="Build type:", font=("Arial", 11)).pack(pady=(10, 0))
        ctk.CTkOptionMenu(self.sidebar, values=["Debug", "Release", "Not stripped Release", "Low-optimization Release"], variable=self.prof_var).pack(pady=10, padx=20)

        self.btn_compile = ctk.CTkButton(self.sidebar, text="Build", command=lambda: self.build_sys.request_build(self.prof_var.get()))
        self.btn_compile.pack(pady=5, padx=20)

        self.btn_fcompile = ctk.CTkButton(self.sidebar, text="Force Build", command=lambda: self.build_sys.request_build(self.prof_var.get(), force=True))
        self.btn_fcompile.pack(pady=5, padx=20)

        self.btn_launch = ctk.CTkButton(self.sidebar, text="Run", fg_color=CS[11], command=self.build_sys.execute_game)
        self.btn_launch.pack(pady=5, padx=20)

        self.btn_br = ctk.CTkButton(self.sidebar, text="Build & Run", command=lambda: self.build_sys.request_build(self.prof_var.get(), auto_run=True))
        self.btn_br.pack(pady=5, padx=20)

        self.btn_fbr = ctk.CTkButton(self.sidebar, text="Force Build & Run", command=lambda: self.build_sys.request_build(self.prof_var.get(), auto_run=True, force=True))
        self.btn_fbr.pack(pady=5, padx=20)

        self.sw_auto = ctk.CTkSwitch(self.sidebar, text="Hot build (doesn't work yet :(", command=self.on_toggle_hot_reload)
        self.sw_auto.pack(pady=30)

    def _setup_main_tabs(self):
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")

        self._init_tab_console(self.tabs.add("Console"))
        self._init_tab_git(self.tabs.add("Git"))
        self._init_tab_api(self.tabs.add("API Viewer"))
        self._init_tab_system(self.tabs.add("System"))
        self._init_tab_assets(self.tabs.add("Assets"))

    def _init_tab_console(self, tab):
        tab.grid_columnconfigure(0, weight=1); tab.grid_rowconfigure((0, 1), weight=1)
        self.issues_view = CompilerIssuesTable(tab); self.issues_view.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.console_view = LogWidget(tab); self.console_view.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def _init_tab_git(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Git Status", font=("Arial", 16, "bold")).pack(pady=10)
        self.ui_git_log = ctk.CTkTextbox(tab, height=300, font=("FreeMono", 11)); self.ui_git_log.pack(fill="x", padx=20, pady=10)

        f = ctk.CTkFrame(tab); f.pack(pady=10)
        ctk.CTkButton(f, text="Update", width=100, command=self.on_git_refresh_ui).pack(side="left", padx=5)
        ctk.CTkButton(f, text="Commit", width=100, command=self.on_git_commit_ui).pack(side="left", padx=5)
        ctk.CTkButton(f, text="Push", width=100, command=lambda: self.on_git_action_async(["push"])).pack(side="left", padx=5)
        self.on_git_refresh_ui()

    def _init_tab_api(self, tab):
        tab.grid_columnconfigure(0, weight=1); tab.grid_rowconfigure(1, weight=1)
        ctk.CTkButton(tab, text="Scan API", command=self.on_api_scan_ui).pack(pady=10)
        self.ui_api_box = ctk.CTkTextbox(tab, font=("FreeMono", 11)); self.ui_api_box.pack(fill="both", expand=True, padx=20, pady=10)

    def _init_tab_system(self, tab):
        tab.grid_columnconfigure((0, 1), weight=1)

        f2 = ctk.CTkFrame(tab); f2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkButton(f2, text="Update studio.py", command=self.on_update_studio_ui).pack(pady=5)
        ctk.CTkButton(f2, text="Update Engine Core", fg_color=CS[12], command=self.on_update_engine_ui).pack(pady=5)

    def _init_tab_assets(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Convert .obj to .c", font=("Arial", 18, "bold")).pack(pady=20)
        ctk.CTkButton(tab, text="Choose .obj", command=self.on_asset_select_ui).pack(pady=10)
        self.ui_asset_lbl = ctk.CTkLabel(tab, text="Nothing is choosed", text_color="gray"); self.ui_asset_lbl.pack()
        self.ui_asset_btn = ctk.CTkButton(tab, text="Convert", state="disabled", command=self.on_asset_convert_ui)
        self.ui_asset_btn.pack(pady=20)

    def log_to_console(self, m, t=None): self.after(0, lambda: self.console_view.log(m, t))
    def clear_console(self): self.after(0, self.console_view.clear_content)
    def clear_issues(self): self.after(0, self.issues_view.clear_issues)
    def on_compiler_message(self, output):
        for line in output.splitlines():
            m = self.build_sys.gcc_regex.match(line)
            if m:
                f, ln, col, sev, msg = m.groups()
                self.after(0, lambda f=f, l=ln, s=sev, msg=msg: self.issues_view.add_issue(f, l, s, msg))
                self.log_to_console(line + "\n", "error" if sev == "error" else "warning")
            else: self.log_to_console(line + "\n")

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
        self.ui_git_log.insert("end", GitEngine.get_repo_status())

    def on_git_commit_ui(self):
        m = simpledialog.askstring("Git Commit", "Commit name")
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
        api_map = parse_engine_api()
        if not api_map:
            self.ui_api_box.insert("end", "Failed to scan API.")
            return
        for file, funcs in api_map.items():
            self.ui_api_box.insert("end", f"[{file}]\n", "info")
            for f in funcs: self.ui_api_box.insert("end", f"  • {f}\n")
            self.ui_api_box.insert("end", "\n")

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
        messagebox.showinfo("OK", "Done.")
        self.log_to_console(f"Asset {self.current_obj_path.name} converted successfully.\n", "success")

    def on_update_studio_ui(self):
        def run():
            self.log_to_console("Updating studio.py...\n", "info")
            try:
                with urllib.request.urlopen(Config.URL_STUDIO_SOURCE) as r:
                    with open("studio.py", "wb") as f: f.write(r.read())
                self.log_to_console("Success. Restart the studio.\n", "success")
            except Exception as e: self.log_to_console(f"Error: {e}\n", "error")
        threading.Thread(target=run, daemon=True).start()

    def on_update_engine_ui(self):
        def run():
            self.log_to_console("Updating the engine core...\n", "info")
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
                self.log_to_console("Engine updated successfully.\n", "success")
            except Exception as e: self.log_to_console(f"Error: {e}\n", "error")
        threading.Thread(target=run, daemon=True).start()

    def set_ui_busy_state(self, b):
        st = "disabled" if b else "normal"
        self.btn_compile.configure(state=st)
        self.btn_br.configure(state=st)





if __name__ == "__main__":
    try:
        app = StudioApp()
        app.mainloop()
    except Exception as e:
        print(f"FATAL: {e}")
