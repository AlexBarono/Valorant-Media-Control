import ctypes
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import ttk


APP_NAME = "Game Media Control"
APP_VERSION = "1.3.6"
PUBLISHER = "GallA"
APP_EXE_NAME = "Game Media Control.exe"
WATCHER_EXE_NAME = "Game Media Watcher.exe"
UNINSTALLER_EXE_NAME = "Game Media Control Uninstaller.exe"
SETUP_TITLE = f"{APP_NAME} Setup"
RUN_VALUE_NAME = "Game Media Control Watcher"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Game Media Control"
PAYLOAD_DIR = "payload"

AUTO_LABELS = {
    "none": "Nein",
    "valorant": "Nur bei Valorant",
    "lol": "Nur bei League of Legends",
    "both": "Bei Valorant und League of Legends",
}
AUTO_VALUES = {label: value for value, label in AUTO_LABELS.items()}


def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def app_payload_path(file_name):
    bundled = resource_path(PAYLOAD_DIR, file_name)
    if os.path.exists(bundled):
        return bundled
    fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", file_name)
    if os.path.exists(fallback):
        return fallback
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)


def detect_exe_arch(exe_path):
    try:
        with open(exe_path, "rb") as handle:
            if handle.read(2) != b"MZ":
                return 64
            handle.seek(0x3C)
            pe_offset = struct.unpack("<I", handle.read(4))[0]
            handle.seek(pe_offset + 4)
            machine = struct.unpack("<H", handle.read(2))[0]
        if machine in (0x014C, 0x01C4):
            return 32
        return 64
    except Exception:
        return 64


def default_install_dir(scope):
    arch = detect_exe_arch(app_payload_path(APP_EXE_NAME))
    if scope == "all":
        if arch == 32:
            base = os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles") or r"C:\Program Files (x86)"
        else:
            base = os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles") or r"C:\Program Files"
        return os.path.join(base, APP_NAME)
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base, "Programs", APP_NAME)


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


def run_hidden(command):
    return subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def create_shortcut(shortcut_path, target_path, working_dir, icon_path):
    os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
    script = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut({ps_quote(shortcut_path)}); "
        f"$shortcut.TargetPath = {ps_quote(target_path)}; "
        f"$shortcut.WorkingDirectory = {ps_quote(working_dir)}; "
        f"$shortcut.IconLocation = {ps_quote(icon_path)}; "
        "$shortcut.Save()"
    )
    run_hidden(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])


def remove_file(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def stop_running_app():
    for image in (APP_EXE_NAME, WATCHER_EXE_NAME):
        run_hidden(["taskkill", "/IM", image, "/T", "/F"])


def copy_payload(install_dir):
    os.makedirs(install_dir, exist_ok=True)
    copied = []
    for file_name in (APP_EXE_NAME, WATCHER_EXE_NAME, UNINSTALLER_EXE_NAME, "README.md", "LICENSE.txt"):
        source = app_payload_path(file_name)
        if os.path.exists(source):
            target = os.path.join(install_dir, file_name)
            shutil.copy2(source, target)
            copied.append(target)
    if not os.path.exists(os.path.join(install_dir, APP_EXE_NAME)):
        raise RuntimeError("App-EXE fehlt im Setup-Paket.")
    if not os.path.exists(os.path.join(install_dir, WATCHER_EXE_NAME)):
        raise RuntimeError("Watcher-EXE fehlt im Setup-Paket.")
    if not os.path.exists(os.path.join(install_dir, UNINSTALLER_EXE_NAME)):
        raise RuntimeError("Deinstaller-EXE fehlt im Setup-Paket.")
    return copied


def write_user_config(auto_mode):
    data_dir = local_app_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    config_path = os.path.join(data_dir, "config.json")
    data = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}
    data["auto_launch_mode"] = auto_mode
    fd, temp_path = tempfile.mkstemp(prefix="config_", suffix=".tmp", dir=data_dir)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(temp_path, config_path)


def configure_watcher_run(install_dir, auto_mode):
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if auto_mode == "none":
                try:
                    winreg.DeleteValue(key, RUN_VALUE_NAME)
                except FileNotFoundError:
                    pass
            else:
                watcher_path = os.path.join(install_dir, WATCHER_EXE_NAME)
                winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, f'"{watcher_path}"')
    except Exception:
        pass


def register_uninstall(scope, install_dir):
    import winreg

    root = winreg.HKEY_LOCAL_MACHINE if scope == "all" else winreg.HKEY_CURRENT_USER
    uninstall_path = os.path.join(install_dir, UNINSTALLER_EXE_NAME)
    uninstall_command = f'"{uninstall_path}" --scope {scope}'
    access = winreg.KEY_SET_VALUE
    if scope == "all":
        access |= winreg.KEY_WOW64_64KEY
    with winreg.CreateKeyEx(root, UNINSTALL_KEY, 0, access) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, os.path.join(install_dir, APP_EXE_NAME))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_command)
        winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, uninstall_command)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, 28000)


def install_application(scope, install_dir, create_desktop, auto_mode):
    stop_running_app()
    copy_payload(install_dir)

    app_path = os.path.join(install_dir, APP_EXE_NAME)
    icon_path = app_path
    start_menu = common_start_menu_dir() if scope == "all" else user_start_menu_dir()
    create_shortcut(os.path.join(start_menu, f"{APP_NAME}.lnk"), app_path, install_dir, icon_path)
    create_shortcut(os.path.join(start_menu, "Deinstallieren.lnk"), os.path.join(install_dir, UNINSTALLER_EXE_NAME), install_dir, icon_path)
    if create_desktop:
        shortcut_path = public_desktop_shortcut() if scope == "all" else user_desktop_shortcut()
        create_shortcut(shortcut_path, app_path, install_dir, icon_path)

    write_user_config(auto_mode)
    configure_watcher_run(install_dir, auto_mode)
    register_uninstall(scope, install_dir)


def relaunch_as_admin(args):
    params = " ".join(f'"{arg}"' for arg in args)
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    return result > 32


class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(SETUP_TITLE)
        self.geometry("760x560")
        self.minsize(720, 520)
        self.configure(bg="#f3f3f3")

        self.scope_var = tk.StringVar(value="user")
        self.install_dir_var = tk.StringVar(value=default_install_dir("user"))
        self.desktop_var = tk.BooleanVar(value=True)
        self.auto_var = tk.StringVar(value=AUTO_LABELS["none"])
        self.launch_var = tk.BooleanVar(value=True)
        self.accept_var = tk.BooleanVar(value=False)
        self.page_index = 0
        self.pages = []
        self.build_ui()

    def build_ui(self):
        self.header = tk.Frame(self, bg="#ffffff", height=82)
        self.header.pack(fill="x")
        tk.Label(self.header, text=APP_NAME, bg="#ffffff", fg="#1a1a1a", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=28, pady=(18, 0))
        tk.Label(self.header, text=f"Setup {APP_VERSION}  |  {PUBLISHER}", bg="#ffffff", fg="#5f6368", font=("Segoe UI", 10)).pack(anchor="w", padx=28)

        self.body = ttk.Frame(self, padding=24)
        self.body.pack(fill="both", expand=True)
        self.footer = ttk.Frame(self, padding=(24, 14))
        self.footer.pack(fill="x")

        self.back_button = ttk.Button(self.footer, text="Zurueck", command=self.back)
        self.next_button = ttk.Button(self.footer, text="Weiter", command=self.next)
        self.cancel_button = ttk.Button(self.footer, text="Abbrechen", command=self.destroy)
        self.cancel_button.pack(side="right")
        self.next_button.pack(side="right", padx=(0, 8))
        self.back_button.pack(side="right", padx=(0, 8))

        self.pages = [
            self.page_welcome,
            self.page_scope,
            self.page_license,
            self.page_options,
            self.page_summary,
            self.page_install,
        ]
        self.show_page()

    def clear_body(self):
        for child in self.body.winfo_children():
            child.destroy()

    def title_label(self, text):
        ttk.Label(self.body, text=text, font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 12))

    def body_text(self, text):
        ttk.Label(self.body, text=text, wraplength=670).pack(anchor="w", fill="x", pady=(0, 14))

    def page_welcome(self):
        self.title_label("Willkommen")
        self.body_text("Dieses Setup installiert Game Media Control und richtet Startmenue, optional Desktopverknuepfung, Autostart-Waechter und Deinstaller ein.")
        self.body_text("Die Anwendung liest nur laufende Windows-Prozesse und Bildschirmbereiche. Es wird nicht in Spiele eingegriffen.")

    def page_scope(self):
        self.title_label("Installationsart")
        ttk.Radiobutton(self.body, text="Nur fuer mich installieren", variable=self.scope_var, value="user", command=self.scope_changed).pack(anchor="w", pady=6)
        ttk.Radiobutton(self.body, text="Fuer alle Benutzer dieses Computers installieren", variable=self.scope_var, value="all", command=self.scope_changed).pack(anchor="w", pady=6)
        ttk.Label(self.body, text="Installationspfad").pack(anchor="w", pady=(22, 4))
        ttk.Entry(self.body, textvariable=self.install_dir_var).pack(fill="x")
        self.body_text("\nBenutzerinstallation benoetigt keine Administratorrechte. Systeminstallation wird per UAC erhoeht.")

    def page_license(self):
        self.title_label("Lizenzvereinbarung")
        license_path = app_payload_path("LICENSE.txt")
        try:
            with open(license_path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except Exception:
            text = "LICENSE.txt konnte nicht geladen werden."
        text_frame = ttk.Frame(self.body)
        text_frame.pack(fill="both", expand=True)
        text_box = tk.Text(text_frame, wrap="word", height=14, borderwidth=1, relief="solid")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_box.yview)
        text_box.configure(yscrollcommand=scrollbar.set)
        text_box.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        text_box.insert("1.0", text)
        text_box.configure(state="disabled")
        ttk.Checkbutton(self.body, text="Ich akzeptiere die Lizenzvereinbarung", variable=self.accept_var).pack(anchor="w", pady=(12, 0))

    def page_options(self):
        self.title_label("Optionen")
        ttk.Checkbutton(self.body, text="Desktopverknuepfung erstellen", variable=self.desktop_var).pack(anchor="w", pady=(0, 16))
        ttk.Label(self.body, text="Automatisch starten, wenn ein Spiel geoeffnet wird").pack(anchor="w")
        combo = ttk.Combobox(self.body, textvariable=self.auto_var, values=list(AUTO_VALUES.keys()), state="readonly")
        combo.pack(fill="x", pady=(4, 16))
        ttk.Checkbutton(self.body, text="Game Media Control nach Abschluss starten", variable=self.launch_var).pack(anchor="w")

    def page_summary(self):
        self.title_label("Zusammenfassung")
        auto_mode = AUTO_VALUES.get(self.auto_var.get(), "none")
        lines = [
            f"App: {APP_NAME} {APP_VERSION}",
            f"Herausgeber: {PUBLISHER}",
            f"Installation: {'fuer alle Benutzer' if self.scope_var.get() == 'all' else 'nur fuer mich'}",
            f"Zielordner: {self.install_dir_var.get()}",
            f"Einstellungen: {local_app_data_dir()}",
            f"Desktopverknuepfung: {'ja' if self.desktop_var.get() else 'nein'}",
            f"Spielerkennung: {AUTO_LABELS.get(auto_mode, 'Nein')}",
        ]
        self.body_text("\n".join(lines))

    def page_install(self):
        self.title_label("Installation")
        self.progress = ttk.Progressbar(self.body, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 14))
        self.status_label = ttk.Label(self.body, text="Bereit.")
        self.status_label.pack(anchor="w")
        self.back_button.configure(state="disabled")
        self.next_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.after(200, self.perform_install)

    def show_page(self):
        self.clear_body()
        self.pages[self.page_index]()
        self.back_button.configure(state="normal" if self.page_index > 0 else "disabled")
        self.next_button.configure(text="Installieren" if self.page_index == len(self.pages) - 2 else "Weiter")
        if self.page_index == len(self.pages) - 1:
            self.back_button.configure(state="disabled")

    def scope_changed(self):
        self.install_dir_var.set(default_install_dir(self.scope_var.get()))

    def back(self):
        if self.page_index > 0:
            self.page_index -= 1
            self.show_page()

    def next(self):
        if self.page_index == 2 and not self.accept_var.get():
            ctypes.windll.user32.MessageBoxW(self.winfo_id(), "Bitte akzeptiere die Lizenzvereinbarung.", "Lizenz", 0x30)
            return
        if self.page_index == len(self.pages) - 2:
            self.page_index += 1
            self.show_page()
            return
        if self.page_index < len(self.pages) - 1:
            self.page_index += 1
            self.show_page()

    def perform_install(self):
        scope = self.scope_var.get()
        install_dir = self.install_dir_var.get()
        auto_mode = AUTO_VALUES.get(self.auto_var.get(), "none")
        if scope == "all" and not is_admin():
            args = [
                "--install",
                "--scope",
                scope,
                "--dir",
                install_dir,
                "--desktop",
                "1" if self.desktop_var.get() else "0",
                "--auto",
                auto_mode,
                "--launch",
                "1" if self.launch_var.get() else "0",
            ]
            if relaunch_as_admin(args):
                self.destroy()
            else:
                self.status_label.configure(text="Administratorrechte wurden nicht erteilt.")
                self.cancel_button.configure(state="normal")
            return

        try:
            self.progress.start(12)
            self.status_label.configure(text="Installiere Dateien und Verknuepfungen...")
            self.update_idletasks()
            install_application(scope, install_dir, self.desktop_var.get(), auto_mode)
            self.progress.stop()
            self.status_label.configure(text="Installation abgeschlossen.")
            self.next_button.configure(text="Fertig", state="normal", command=self.finish)
            self.cancel_button.configure(state="normal", text="Schliessen", command=self.finish)
        except Exception as exc:
            self.progress.stop()
            self.status_label.configure(text=f"Installation fehlgeschlagen: {exc}")
            self.cancel_button.configure(state="normal")

    def finish(self):
        if self.launch_var.get():
            app_path = os.path.join(self.install_dir_var.get(), APP_EXE_NAME)
            if os.path.exists(app_path):
                subprocess.Popen([app_path], cwd=self.install_dir_var.get())
        self.destroy()


def parse_arg(name, default=""):
    if name in sys.argv:
        index = sys.argv.index(name)
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return default


def command_line_install():
    scope = parse_arg("--scope", "user")
    install_dir = parse_arg("--dir", default_install_dir(scope))
    desktop = parse_arg("--desktop", "1") == "1"
    auto_mode = parse_arg("--auto", "none")
    launch = parse_arg("--launch", "1") == "1"
    if scope == "all" and not is_admin():
        relaunch_as_admin(sys.argv[1:])
        return 0
    try:
        install_application(scope, install_dir, desktop, auto_mode)
        if launch:
            subprocess.Popen([os.path.join(install_dir, APP_EXE_NAME)], cwd=install_dir)
        ctypes.windll.user32.MessageBoxW(None, "Installation abgeschlossen.", SETUP_TITLE, 0x40)
        return 0
    except Exception as exc:
        ctypes.windll.user32.MessageBoxW(None, f"Installation fehlgeschlagen:\n{exc}", SETUP_TITLE, 0x10)
        return 1


def main():
    if "--install" in sys.argv:
        return command_line_install()
    app = SetupWizard()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
