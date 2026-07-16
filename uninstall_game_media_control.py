import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import ttk


APP_NAME = "Game Media Control"
APP_VERSION = "1.3.6"
APP_EXE_NAME = "Game Media Control.exe"
WATCHER_EXE_NAME = "Game Media Watcher.exe"
UNINSTALLER_EXE_NAME = "Game Media Control Uninstaller.exe"
PUBLISHER = "GallA"
RUN_VALUE_NAME = "Game Media Control Watcher"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Game Media Control"


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def local_app_data_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base, APP_NAME)


def user_start_menu_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    return os.path.join(base, "Microsoft", "Windows", "Start Menu", "Programs", APP_NAME)


def common_start_menu_dir():
    base = os.environ.get("PROGRAMDATA") or r"C:\ProgramData"
    return os.path.join(base, "Microsoft", "Windows", "Start Menu", "Programs", APP_NAME)


def user_desktop_shortcut():
    return os.path.join(os.path.expanduser("~"), "Desktop", f"{APP_NAME}.lnk")


def public_desktop_shortcut():
    public = os.environ.get("PUBLIC") or r"C:\Users\Public"
    return os.path.join(public, "Desktop", f"{APP_NAME}.lnk")


def remove_file(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def remove_tree(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass


def remove_registry_value(root, path, name):
    try:
        import winreg

        with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
    except Exception:
        pass


def remove_registry_key(root, path, view_flag=0):
    try:
        import winreg

        access = winreg.KEY_ALL_ACCESS | view_flag
        winreg.DeleteKeyEx(root, path, access, 0)
    except Exception:
        try:
            import winreg

            winreg.DeleteKey(root, path)
        except Exception:
            pass


def stop_processes():
    for image_name in (APP_EXE_NAME, WATCHER_EXE_NAME):
        subprocess.run(
            ["taskkill", "/IM", image_name, "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


def schedule_self_delete(install_dir):
    script_path = os.path.join(tempfile.gettempdir(), "game_media_control_remove.bat")
    script = f"""@echo off
set "INSTALL_DIR={install_dir}"
timeout /T 2 /NOBREAK >NUL
rmdir /S /Q "%INSTALL_DIR%"
del "%~f0"
"""
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(script)
    subprocess.Popen(
        ["cmd.exe", "/c", script_path],
        cwd=tempfile.gettempdir(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def run_uninstall(scope, delete_user_data):
    install_dir = app_dir()
    stop_processes()

    remove_registry_value(
        __import__("winreg").HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        RUN_VALUE_NAME,
    )

    if scope == "all":
        remove_tree(common_start_menu_dir())
        remove_file(public_desktop_shortcut())
        remove_registry_key(__import__("winreg").HKEY_LOCAL_MACHINE, UNINSTALL_KEY, __import__("winreg").KEY_WOW64_64KEY)
        remove_registry_key(__import__("winreg").HKEY_LOCAL_MACHINE, UNINSTALL_KEY, __import__("winreg").KEY_WOW64_32KEY)
    else:
        remove_tree(user_start_menu_dir())
        remove_file(user_desktop_shortcut())
        remove_registry_key(__import__("winreg").HKEY_CURRENT_USER, UNINSTALL_KEY)

    if delete_user_data:
        remove_tree(local_app_data_dir())

    for name in (APP_EXE_NAME, WATCHER_EXE_NAME):
        remove_file(os.path.join(install_dir, name))
    schedule_self_delete(install_dir)


class Uninstaller(tk.Tk):
    def __init__(self, scope):
        super().__init__()
        self.scope = scope
        self.title(f"{APP_NAME} deinstallieren")
        self.geometry("560x360")
        self.minsize(520, 320)
        self.configure(bg="#f3f3f3")
        self.delete_data_var = tk.BooleanVar(value=False)
        self.build_ui()

    def build_ui(self):
        frame = ttk.Frame(self, padding=24)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text=f"{APP_NAME} deinstallieren", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            frame,
            text=(
                "Der Deinstaller entfernt Programmdateien, Startmenueeintraege, Desktopverknuepfungen, "
                "Autostart-Eintraege und den Eintrag unter Installierte Apps."
            ),
            wraplength=500,
        ).grid(row=1, column=0, sticky="ew", pady=(14, 20))

        ttk.Checkbutton(
            frame,
            text="Auch alle Einstellungen, Logs und persoenlichen Anwendungsdaten loeschen",
            variable=self.delete_data_var,
        ).grid(row=2, column=0, sticky="w", pady=(0, 24))

        ttk.Label(
            frame,
            text=f"Installationsordner: {app_dir()}",
            wraplength=500,
            foreground="#5f6368",
        ).grid(row=3, column=0, sticky="ew")

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, sticky="e", pady=(30, 0))
        ttk.Button(buttons, text="Abbrechen", command=self.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Deinstallieren", command=self.uninstall).grid(row=0, column=1)

    def uninstall(self):
        run_uninstall(self.scope, self.delete_data_var.get())
        self.destroy()


def main():
    scope = "user"
    if "--scope" in sys.argv:
        index = sys.argv.index("--scope")
        if index + 1 < len(sys.argv):
            scope = sys.argv[index + 1]

    if scope == "all" and not is_admin():
        params = " ".join(f'"{arg}"' for arg in sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        return 0

    app = Uninstaller(scope)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
