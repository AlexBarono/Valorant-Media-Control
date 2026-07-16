import ctypes
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import uuid
import webbrowser
import zipfile
from tkinter import ttk
from ctypes import wintypes


APP_NAME = "Game Media Control"
APP_VERSION = "1.3.6"
APP_DIR_NAME = "Game Media Control"


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def is_frozen_app():
    return bool(getattr(sys, "frozen", False))


def get_resource_dir():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return get_app_dir()


def get_user_data_dir():
    base_dir = os.environ.get("LOCALAPPDATA")
    if not base_dir:
        base_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.abspath(os.path.join(base_dir, APP_DIR_NAME))


def ensure_directory(path):
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False


APP_DIR = get_app_dir()
RESOURCE_DIR = get_resource_dir()
USER_DATA_DIR = get_user_data_dir()
LOG_DIR = os.path.join(USER_DATA_DIR, "Logs")


def resource_path(file_name):
    external_path = os.path.join(APP_DIR, file_name)
    if os.path.exists(external_path):
        return external_path
    return os.path.join(RESOURCE_DIR, file_name)


CONFIG_PATH = os.path.join(USER_DATA_DIR, "config.json")
LEGACY_CONFIG_PATHS = (
    os.path.join(APP_DIR, "config.json"),
    os.path.join(os.getcwd(), "config.json"),
)
README_PATH = resource_path("README.md")
FALLBACK_BACKGROUND_PATH = resource_path("Gangcord.gif")
LOGO_PATH = resource_path("logo der app.png")
MAX_BACKGROUND_FRAMES = 1
GITHUB_REPO = "AlexBarono/Valorant-Media-Control"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_REPO}"
GITHUB_RELEASE_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_COMMIT_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/commits/HEAD"
GITHUB_RAW_APP_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/valorant_media_guard.py"
GITHUB_RAW_EXE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/dist/Game%20Media%20Control.exe"
GITHUB_DOWNLOAD_URL = f"{GITHUB_REPO_URL}/archive/refs/heads/main.zip"
UPDATE_FILES = (
    "valorant_media_guard.py",
    "start_valorant_media_guard.bat",
    "README.md",
    "Gangcord.gif",
    "logo der app.png",
)

SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
VALORANT_TARGET_HEX = "#ff4655"
VALORANT_TARGET_RGB = (255, 70, 85)
VALORANT_COLOR_TOLERANCE = 0
VALORANT_AUTO_RED_MIN_VALUE = 120
VALORANT_AUTO_RED_MIN_GAP = 35

WM_APPCOMMAND = 0x0319
HWND_BROADCAST = ctypes.c_void_p(0xFFFF)
ERROR_ALREADY_EXISTS = 183
APP_MUTEX_NAME = "Local\\GameMediaControl_Main_Instance"
APPCOMMAND_MEDIA_PLAY = 46
APPCOMMAND_MEDIA_PAUSE = 47
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
ole32 = ctypes.WinDLL("ole32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

HANDLE = ctypes.c_void_p
HWND = ctypes.c_void_p
HDC = ctypes.c_void_p
HBITMAP = ctypes.c_void_p
HGDIOBJ = ctypes.c_void_p
HRESULT = ctypes.c_long


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    def __init__(self, guid_string=None):
        super().__init__()
        if not guid_string:
            return
        value = uuid.UUID(guid_string.strip("{}"))
        self.Data1 = value.time_low
        self.Data2 = value.time_mid
        self.Data3 = value.time_hi_version
        node_bytes = value.node.to_bytes(6, "big")
        self.Data4 = (ctypes.c_ubyte * 8)(value.clock_seq_hi_variant, value.clock_seq_low, *node_bytes)


user32.GetDC.argtypes = [HWND]
user32.GetDC.restype = HDC
user32.ReleaseDC.argtypes = [HWND, HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = HWND
user32.GetWindowTextLengthW.argtypes = [HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.SendMessageW.argtypes = [HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = wintypes.LPARAM
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, wintypes.WPARAM]
user32.keybd_event.restype = None

gdi32.CreateCompatibleDC.argtypes = [HDC]
gdi32.CreateCompatibleDC.restype = HDC
gdi32.CreateCompatibleBitmap.argtypes = [HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = HBITMAP
gdi32.SelectObject.argtypes = [HDC, HGDIOBJ]
gdi32.SelectObject.restype = HGDIOBJ
gdi32.BitBlt.argtypes = [HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
gdi32.BitBlt.restype = wintypes.BOOL
gdi32.GetDIBits.argtypes = [HDC, HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wintypes.UINT]
gdi32.GetDIBits.restype = ctypes.c_int
gdi32.DeleteObject.argtypes = [HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
ole32.CoInitializeEx.restype = HRESULT
ole32.CoUninitialize.argtypes = []
ole32.CoUninitialize.restype = None
ole32.CoCreateInstance.argtypes = [
    ctypes.POINTER(GUID),
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(GUID),
    ctypes.POINTER(ctypes.c_void_p),
]
ole32.CoCreateInstance.restype = HRESULT
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
ole32.CoTaskMemFree.restype = None

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = HANDLE


CLSCTX_ALL = 0x17
COINIT_APARTMENTTHREADED = 0x2
RPC_E_CHANGED_MODE = ctypes.c_long(0x80010106).value
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
E_RENDER = 0
E_MULTIMEDIA = 1

AUTO_LAUNCH_LABELS = {
    "none": "Nein",
    "valorant": "Nur bei Valorant",
    "lol": "Nur bei League of Legends",
    "both": "Bei Valorant und League of Legends",
}
AUTO_LAUNCH_VALUES = {label: value for value, label in AUTO_LAUNCH_LABELS.items()}
WATCHER_EXE_NAME = "Game Media Watcher.exe"
WATCHER_RUN_NAME = "Game Media Control Watcher"

CLSID_MMDEVICE_ENUMERATOR = GUID("BCDE0395-E52F-467C-8E3D-C4579291692E")
IID_IMMDEVICE_ENUMERATOR = GUID("A95664D2-9614-4F35-A746-DE8DB63617E6")
IID_IAUDIO_SESSION_MANAGER2 = GUID("77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F")
IID_IAUDIO_SESSION_CONTROL2 = GUID("BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D")
IID_ISIMPLE_AUDIO_VOLUME = GUID("87CE5498-68D6-44E5-9215-6DA47EF883D8")


DEFAULT_CONFIG = {
    "region": None,
    "interval_ms": 450,
    "red_pixel_percent": 1.0,
    "red_min_value": 140,
    "red_difference": 45,
    "valorant_target_rgb": list(VALORANT_TARGET_RGB),
    "valorant_color_tolerance": VALORANT_COLOR_TOLERANCE,
    "stable_reads": 2,
    "require_valorant_foreground": True,
    "command_mode": "direct",
    "action_mode": "media",
    "target_process": "",
    "target_label": "",
    "dead_volume": 100,
    "alive_volume": 25,
    "lol_region": None,
    "lol_interval_ms": 450,
    "lol_bright_pixel_percent": 0.25,
    "lol_bright_min_value": 150,
    "lol_min_digit_height": 8,
    "lol_min_digit_area": 12,
    "lol_min_digit_components": 1,
    "lol_stable_reads": 2,
    "require_lol_foreground": True,
    "lol_command_mode": "direct",
    "lol_action_mode": "media",
    "lol_target_process": "",
    "lol_target_label": "",
    "lol_dead_volume": 100,
    "lol_alive_volume": 25,
    "theme_mode": "system",
    "auto_launch_mode": "none",
}

LAST_CONFIG_ERROR = ""

THEME_LABELS = {
    "system": "System",
    "light": "Hell",
    "dark": "Dunkel",
}
THEME_VALUES = {label: value for value, label in THEME_LABELS.items()}

FLUENT_PALETTES = {
    "light": {
        "window": "#f3f3f3",
        "surface": "#ffffff",
        "surface_alt": "#fafafa",
        "surface_hover": "#f8f8f8",
        "border": "#d6d6d6",
        "border_focus": "#0067c0",
        "text": "#1a1a1a",
        "muted": "#5f6368",
        "disabled": "#8a8a8a",
        "accent": "#0067c0",
        "accent_hover": "#0a75d9",
        "accent_pressed": "#005a9e",
        "accent_text": "#ffffff",
        "danger": "#c42b1c",
        "danger_hover": "#d13438",
        "success": "#107c10",
        "warning": "#9d5d00",
        "shadow": "#d0d0d0",
        "hero_overlay": "#000000",
        "input": "#ffffff",
        "selection": "#cfe8ff",
    },
    "dark": {
        "window": "#202020",
        "surface": "#2b2b2b",
        "surface_alt": "#252525",
        "surface_hover": "#333333",
        "border": "#454545",
        "border_focus": "#60cdff",
        "text": "#f3f3f3",
        "muted": "#c8c8c8",
        "disabled": "#8a8a8a",
        "accent": "#60cdff",
        "accent_hover": "#7bd7ff",
        "accent_pressed": "#4cc2ff",
        "accent_text": "#001b2e",
        "danger": "#ff6b6b",
        "danger_hover": "#ff7a7a",
        "success": "#6ccb5f",
        "warning": "#f9c23c",
        "shadow": "#121212",
        "hero_overlay": "#000000",
        "input": "#1f1f1f",
        "selection": "#004b73",
    },
}


def set_dpi_awareness():
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def win_error(message):
    error = ctypes.get_last_error()
    if error:
        raise ctypes.WinError(error)
    raise OSError(message)


def check_hresult(hr, message):
    if ctypes.c_long(hr).value < 0:
        raise OSError(f"{message} (HRESULT 0x{hr & 0xFFFFFFFF:08X})")


def com_initialize():
    hr = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    if hr == RPC_E_CHANGED_MODE:
        return False
    check_hresult(hr, "Konnte Windows-Audio-COM nicht starten.")
    return True


def com_method(interface, index, restype, *argtypes):
    vtable = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    prototype = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return prototype(vtable[index])


def com_release(interface):
    if interface:
        com_method(interface, 2, wintypes.ULONG)(interface)


def query_interface(interface, iid):
    result = ctypes.c_void_p()
    hr = com_method(interface, 0, HRESULT, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))(
        interface,
        ctypes.byref(iid),
        ctypes.byref(result),
    )
    check_hresult(hr, "Konnte Audio-Interface nicht oeffnen.")
    return result


def get_process_name(pid):
    if not pid:
        return "System Sounds"

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return f"PID {pid}"

    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return os.path.basename(buffer.value)
    finally:
        kernel32.CloseHandle(handle)

    return f"PID {pid}"


def get_default_audio_session_manager():
    device_enumerator = ctypes.c_void_p()
    device = ctypes.c_void_p()
    manager = ctypes.c_void_p()

    try:
        hr = ole32.CoCreateInstance(
            ctypes.byref(CLSID_MMDEVICE_ENUMERATOR),
            None,
            CLSCTX_ALL,
            ctypes.byref(IID_IMMDEVICE_ENUMERATOR),
            ctypes.byref(device_enumerator),
        )
        check_hresult(hr, "Konnte Audio-Geraete nicht oeffnen.")

        hr = com_method(
            device_enumerator,
            4,
            HRESULT,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p),
        )(device_enumerator, E_RENDER, E_MULTIMEDIA, ctypes.byref(device))
        check_hresult(hr, "Konnte Standard-Wiedergabegeraet nicht finden.")

        hr = com_method(
            device,
            3,
            HRESULT,
            ctypes.POINTER(GUID),
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        )(device, ctypes.byref(IID_IAUDIO_SESSION_MANAGER2), CLSCTX_ALL, None, ctypes.byref(manager))
        check_hresult(hr, "Konnte Audio-Sitzungsmanager nicht oeffnen.")
        return manager
    finally:
        com_release(device)
        com_release(device_enumerator)


def get_session_display_name(control):
    name_pointer = ctypes.c_void_p()
    try:
        hr = com_method(control, 4, HRESULT, ctypes.POINTER(ctypes.c_void_p))(control, ctypes.byref(name_pointer))
        if ctypes.c_long(hr).value < 0 or not name_pointer.value:
            return ""
        return ctypes.wstring_at(name_pointer)
    finally:
        if name_pointer.value:
            ole32.CoTaskMemFree(name_pointer)


def get_session_volume(volume_interface):
    volume = ctypes.c_float()
    hr = com_method(volume_interface, 4, HRESULT, ctypes.POINTER(ctypes.c_float))(volume_interface, ctypes.byref(volume))
    if ctypes.c_long(hr).value < 0:
        return None
    return max(0.0, min(100.0, float(volume.value) * 100.0))


def enumerate_audio_sessions():
    initialized = com_initialize()
    manager = ctypes.c_void_p()
    enumerator = ctypes.c_void_p()
    sessions = []

    try:
        manager = get_default_audio_session_manager()
        hr = com_method(manager, 5, HRESULT, ctypes.POINTER(ctypes.c_void_p))(manager, ctypes.byref(enumerator))
        check_hresult(hr, "Konnte Audio-Sitzungen nicht auflisten.")

        count = ctypes.c_int()
        hr = com_method(enumerator, 3, HRESULT, ctypes.POINTER(ctypes.c_int))(enumerator, ctypes.byref(count))
        check_hresult(hr, "Konnte Audio-Sitzungen nicht zaehlen.")

        for index in range(count.value):
            control = ctypes.c_void_p()
            control2 = ctypes.c_void_p()
            volume_interface = ctypes.c_void_p()
            try:
                hr = com_method(enumerator, 4, HRESULT, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))(
                    enumerator,
                    index,
                    ctypes.byref(control),
                )
                if ctypes.c_long(hr).value < 0 or not control:
                    continue

                control2 = query_interface(control, IID_IAUDIO_SESSION_CONTROL2)
                volume_interface = query_interface(control, IID_ISIMPLE_AUDIO_VOLUME)

                pid = wintypes.DWORD()
                hr = com_method(control2, 14, HRESULT, ctypes.POINTER(wintypes.DWORD))(control2, ctypes.byref(pid))
                if ctypes.c_long(hr).value < 0:
                    continue

                process_name = get_process_name(pid.value)
                display_name = get_session_display_name(control2)
                volume = get_session_volume(volume_interface)
                if process_name.startswith("PID "):
                    label_name = process_name
                elif display_name:
                    label_name = f"{process_name} - {display_name}"
                else:
                    label_name = process_name

                sessions.append(
                    {
                        "pid": int(pid.value),
                        "process_name": process_name,
                        "display_name": display_name,
                        "volume": volume,
                        "label": f"{label_name} ({pid.value})"
                        if volume is None
                        else f"{label_name} ({pid.value}) - {volume:.0f}%",
                    }
                )
            finally:
                com_release(volume_interface)
                com_release(control2)
                com_release(control)

        return sorted(sessions, key=lambda item: item["label"].lower())
    finally:
        com_release(enumerator)
        com_release(manager)
        if initialized:
            ole32.CoUninitialize()


def set_audio_session_volume(process_name, volume_percent):
    target = os.path.basename(process_name or "").lower()
    if not target:
        raise ValueError("Waehle zuerst eine Medienwiedergabe aus.")

    volume_value = max(0.0, min(100.0, float(volume_percent))) / 100.0
    initialized = com_initialize()
    manager = ctypes.c_void_p()
    enumerator = ctypes.c_void_p()
    changed = 0

    try:
        manager = get_default_audio_session_manager()
        hr = com_method(manager, 5, HRESULT, ctypes.POINTER(ctypes.c_void_p))(manager, ctypes.byref(enumerator))
        check_hresult(hr, "Konnte Audio-Sitzungen nicht auflisten.")

        count = ctypes.c_int()
        hr = com_method(enumerator, 3, HRESULT, ctypes.POINTER(ctypes.c_int))(enumerator, ctypes.byref(count))
        check_hresult(hr, "Konnte Audio-Sitzungen nicht zaehlen.")

        for index in range(count.value):
            control = ctypes.c_void_p()
            control2 = ctypes.c_void_p()
            volume_interface = ctypes.c_void_p()
            try:
                hr = com_method(enumerator, 4, HRESULT, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))(
                    enumerator,
                    index,
                    ctypes.byref(control),
                )
                if ctypes.c_long(hr).value < 0 or not control:
                    continue

                control2 = query_interface(control, IID_IAUDIO_SESSION_CONTROL2)
                pid = wintypes.DWORD()
                hr = com_method(control2, 14, HRESULT, ctypes.POINTER(wintypes.DWORD))(control2, ctypes.byref(pid))
                if ctypes.c_long(hr).value < 0:
                    continue

                current_process = os.path.basename(get_process_name(pid.value)).lower()
                if current_process != target:
                    continue

                volume_interface = query_interface(control, IID_ISIMPLE_AUDIO_VOLUME)
                hr = com_method(volume_interface, 3, HRESULT, ctypes.c_float, ctypes.c_void_p)(
                    volume_interface,
                    ctypes.c_float(volume_value),
                    None,
                )
                check_hresult(hr, "Konnte Lautstaerke nicht setzen.")
                changed += 1
            finally:
                com_release(volume_interface)
                com_release(control2)
                com_release(control)

        return changed
    finally:
        com_release(enumerator)
        com_release(manager)
        if initialized:
            ole32.CoUninitialize()


def load_config():
    global LAST_CONFIG_ERROR
    data = dict(DEFAULT_CONFIG)
    checked_paths = [CONFIG_PATH]
    for path in LEGACY_CONFIG_PATHS:
        if path not in checked_paths:
            checked_paths.append(path)

    for path in checked_paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                data.update(loaded)
                LAST_CONFIG_ERROR = ""
                return data
        except Exception as exc:
            LAST_CONFIG_ERROR = f"Einstellungen konnten nicht gelesen werden: {exc}"
            continue
    if LAST_CONFIG_ERROR:
        return data
    return data


def migrate_legacy_config_if_needed():
    if os.path.exists(CONFIG_PATH):
        return
    for legacy_path in LEGACY_CONFIG_PATHS:
        if not os.path.exists(legacy_path):
            continue
        try:
            ensure_directory(USER_DATA_DIR)
            shutil.copy2(legacy_path, CONFIG_PATH)
            return
        except Exception:
            continue


def save_config(data):
    global LAST_CONFIG_ERROR
    temp_path = ""
    try:
        if not ensure_directory(USER_DATA_DIR):
            raise OSError(f"Ordner konnte nicht erstellt werden: {USER_DATA_DIR}")
        fd, temp_path = tempfile.mkstemp(prefix="config_", suffix=".tmp", dir=USER_DATA_DIR)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, CONFIG_PATH)
        LAST_CONFIG_ERROR = ""
        return True
    except Exception as exc:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        LAST_CONFIG_ERROR = f"Einstellungen konnten nicht gespeichert werden: {exc}"
        return False


def detect_windows_theme():
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            apps_use_light_theme = winreg.QueryValueEx(key, "AppsUseLightTheme")[0]
        return "light" if apps_use_light_theme else "dark"
    except Exception:
        return "light"


def normalize_theme_mode(value):
    text = str(value or "system").strip().lower()
    if text in ("hell", "light"):
        return "light"
    if text in ("dunkel", "dark"):
        return "dark"
    return "system"


def resolved_theme(mode):
    normalized = normalize_theme_mode(mode)
    if normalized == "system":
        return detect_windows_theme()
    return normalized


def normalize_auto_launch_mode(value):
    text = str(value or "none").strip().lower()
    aliases = {
        "nein": "none",
        "no": "none",
        "off": "none",
        "valorant": "valorant",
        "lol": "lol",
        "league": "lol",
        "league of legends": "lol",
        "both": "both",
        "beide": "both",
    }
    return aliases.get(text, text if text in AUTO_LAUNCH_LABELS else "none")


def get_watcher_path():
    return os.path.join(APP_DIR, WATCHER_EXE_NAME)


def stop_watcher_process():
    try:
        subprocess.run(
            ["taskkill", "/IM", WATCHER_EXE_NAME, "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=8,
        )
    except Exception:
        pass


def start_watcher_process():
    watcher_path = get_watcher_path()
    if not os.path.exists(watcher_path):
        return False, f"Watcher nicht gefunden: {watcher_path}"
    try:
        subprocess.Popen(
            [watcher_path],
            cwd=APP_DIR,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True, ""
    except Exception as exc:
        return False, f"Watcher konnte nicht gestartet werden: {exc}"


def configure_watcher_autostart(mode):
    mode = normalize_auto_launch_mode(mode)
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if mode == "none":
                try:
                    winreg.DeleteValue(key, WATCHER_RUN_NAME)
                except FileNotFoundError:
                    pass
                stop_watcher_process()
                return True, "Automatische Spielerkennung deaktiviert."

            watcher_path = get_watcher_path()
            if not os.path.exists(watcher_path):
                return False, f"Watcher nicht gefunden: {watcher_path}"

            command = f'"{watcher_path}"'
            winreg.SetValueEx(key, WATCHER_RUN_NAME, 0, winreg.REG_SZ, command)
            started, start_message = start_watcher_process()
            if not started:
                return False, start_message
            return True, "Automatische Spielerkennung wird beim Windows-Start geladen."
    except Exception as exc:
        return False, f"Autostart konnte nicht geaendert werden: {exc}"


def create_single_instance_mutex():
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, False, APP_MUTEX_NAME)
    already_running = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
    return handle, already_running


def rounded_canvas_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    radius = max(0, min(radius, int((x2 - x1) / 2), int((y2 - y1) / 2)))
    points = [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def is_replacement_header_image(file_name):
    lower_name = file_name.lower()
    return lower_name.endswith(".png") and "gif" in lower_name and "logo" not in lower_name


def find_header_background_path():
    candidates = []
    for directory in (APP_DIR, RESOURCE_DIR):
        try:
            for file_name in os.listdir(directory):
                if is_replacement_header_image(file_name):
                    path = os.path.join(directory, file_name)
                    candidates.append((os.path.getmtime(path), path))
        except OSError:
            pass

    if candidates:
        return max(candidates)[1]
    return FALLBACK_BACKGROUND_PATH


def update_file_names_from_source(source_root):
    file_names = list(UPDATE_FILES)
    try:
        for file_name in os.listdir(source_root):
            if is_replacement_header_image(file_name) and file_name not in file_names:
                file_names.append(file_name)
    except OSError:
        pass
    return file_names


def run_git_command(*args, timeout=12):
    return subprocess.check_output(
        ["git", *args],
        cwd=APP_DIR,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    ).strip()


def get_current_commit(short=False):
    try:
        if short:
            return run_git_command("rev-parse", "--short", "HEAD")
        return run_git_command("rev-parse", "HEAD")
    except Exception:
        return ""


def get_current_version_text():
    commit = get_current_commit(short=True)
    if commit:
        return f"v{APP_VERSION} ({commit})"
    return f"v{APP_VERSION}"


def normalize_version(value):
    return str(value or "").strip().lower().lstrip("v")


def version_parts(value):
    parts = []
    current = ""
    for char in normalize_version(value):
        if char.isdigit():
            current += char
        elif current:
            parts.append(int(current))
            current = ""
    if current:
        parts.append(int(current))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_version_newer(remote_version, local_version):
    return version_parts(remote_version) > version_parts(local_version)


def extract_app_version(source_text):
    marker = 'APP_VERSION = "'
    start = source_text.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    end = source_text.find('"', start)
    if end < 0:
        return ""
    return source_text[start:end]


def is_git_available():
    try:
        run_git_command("--version", timeout=5)
        return True
    except Exception:
        return False


def powershell_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def find_release_exe_download_url(release_data):
    assets = release_data.get("assets")
    if not isinstance(assets, list):
        return ""

    app_key = APP_NAME.lower().replace(" ", "")
    exe_assets = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        download_url = str(asset.get("browser_download_url") or "")
        if name.lower().endswith(".exe") and download_url:
            exe_assets.append((name, download_url))

    for name, download_url in exe_assets:
        if app_key in name.lower().replace(" ", ""):
            return download_url
    if exe_assets:
        return exe_assets[0][1]
    return ""


def read_url_text(url, timeout=8):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            return response.read().decode("utf-8", errors="replace")
    except Exception:
        command = (
            "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; "
            f"(Invoke-WebRequest -UseBasicParsing -Uri {powershell_quote(url)} -TimeoutSec {int(timeout) + 5}).Content"
        )
        try:
            return subprocess.check_output(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                text=True,
                stderr=subprocess.STDOUT,
                timeout=timeout + 10,
            )
        except Exception:
            return None


def download_url_to_file(url, target_path, timeout=45):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            with open(target_path, "wb") as handle:
                shutil.copyfileobj(response, handle)
        return
    except Exception:
        command = (
            "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; "
            f"Invoke-WebRequest -UseBasicParsing -Uri {powershell_quote(url)} "
            f"-OutFile {powershell_quote(target_path)} -TimeoutSec {int(timeout)}"
        )
        subprocess.check_call(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            timeout=timeout + 15,
        )


def fetch_latest_release_info():
    response_text = read_url_text(GITHUB_RELEASE_API_URL, timeout=8)
    if not response_text:
        return None
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return None

    tag_name = data.get("tag_name")
    if not tag_name:
        return None
    exe_download_url = find_release_exe_download_url(data)
    if is_frozen_app():
        download_url = exe_download_url or GITHUB_RAW_EXE_URL
    else:
        download_url = GITHUB_DOWNLOAD_URL
    return {
        "kind": "release",
        "latest": tag_name,
        "url": data.get("html_url", GITHUB_REPO_URL),
        "download_url": download_url,
        "available": is_version_newer(tag_name, APP_VERSION),
        "manual_update": False,
    }


def fetch_latest_raw_version_info():
    source_text = read_url_text(GITHUB_RAW_APP_URL, timeout=8)
    if not source_text:
        return None

    remote_version = extract_app_version(source_text)
    if not remote_version:
        return None

    available = is_version_newer(remote_version, APP_VERSION)
    if available:
        status = "Neue Version auf GitHub gefunden."
    elif version_parts(remote_version) == version_parts(APP_VERSION):
        status = "Du hast die neueste Version."
    else:
        status = "Lokale Version ist neuer als GitHub."

    return {
        "kind": "raw_version",
        "latest": f"v{remote_version}",
        "url": GITHUB_REPO_URL,
        "download_url": GITHUB_RAW_EXE_URL if is_frozen_app() else GITHUB_DOWNLOAD_URL,
        "available": available,
        "manual_update": False,
        "status": status,
    }


def fetch_latest_api_head_info():
    response_text = read_url_text(GITHUB_COMMIT_API_URL, timeout=8)
    if not response_text:
        return None
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return None

    remote_commit = data.get("sha", "")
    if not remote_commit:
        return None

    current_commit = get_current_commit(short=False)
    if current_commit:
        available = current_commit != remote_commit
        status = "Neue GitHub-Version gefunden." if available else "Du hast die neueste Version."
    else:
        available = False
        status = "GitHub erreichbar. Updates werden per ZIP geladen."

    return {
        "kind": "api_commit",
        "latest": f"GitHub {remote_commit[:7]}",
        "remote_commit": remote_commit,
        "url": GITHUB_REPO_URL,
        "download_url": GITHUB_RAW_EXE_URL if is_frozen_app() else GITHUB_DOWNLOAD_URL,
        "available": available,
        "manual_update": False,
        "status": status,
    }


def fetch_latest_remote_head_info():
    output = run_git_command("ls-remote", "origin", "HEAD", timeout=15)
    remote_commit = output.split()[0] if output else ""
    current_commit = get_current_commit(short=False)
    if not remote_commit:
        raise RuntimeError("GitHub-HEAD konnte nicht gelesen werden.")

    return {
        "kind": "commit",
        "latest": f"GitHub {remote_commit[:7]}",
        "remote_commit": remote_commit,
        "url": GITHUB_REPO_URL,
        "available": bool(current_commit and current_commit != remote_commit),
    }


def fetch_latest_version_info():
    try:
        release_info = fetch_latest_release_info()
    except Exception:
        release_info = None

    raw_version_info = fetch_latest_raw_version_info()
    if release_info and (release_info.get("available") or not raw_version_info):
        return release_info
    if raw_version_info:
        return raw_version_info
    if release_info:
        return release_info

    api_info = fetch_latest_api_head_info()
    if api_info:
        return api_info

    if is_git_available():
        return fetch_latest_remote_head_info()

    return {
        "kind": "manual",
        "latest": "Git nicht gefunden",
        "url": GITHUB_REPO_URL,
        "download_url": GITHUB_DOWNLOAD_URL,
        "available": False,
        "manual_update": True,
        "status": "GitHub kann im Browser geoeffnet werden.",
    }


def pull_latest_version():
    try:
        return run_git_command("pull", "--ff-only", timeout=60)
    except subprocess.CalledProcessError:
        return run_git_command("pull", "--ff-only", "origin", "HEAD", timeout=60)


def download_and_apply_zip_update():
    with tempfile.TemporaryDirectory(prefix="game_media_guard_update_") as temp_dir:
        zip_path = os.path.join(temp_dir, "update.zip")
        download_url_to_file(GITHUB_DOWNLOAD_URL, zip_path, timeout=45)

        extract_dir = os.path.join(temp_dir, "extract")
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)

        roots = [
            os.path.join(extract_dir, name)
            for name in os.listdir(extract_dir)
            if os.path.isdir(os.path.join(extract_dir, name))
        ]
        if not roots:
            raise RuntimeError("Update-ZIP enthaelt keinen Projektordner.")
        source_root = roots[0]

        updated = []
        for file_name in update_file_names_from_source(source_root):
            source_path = os.path.join(source_root, file_name)
            target_path = os.path.join(APP_DIR, file_name)
            if os.path.exists(source_path):
                shutil.copy2(source_path, target_path)
                updated.append(file_name)

        if not updated:
            raise RuntimeError("Update-ZIP enthaelt keine bekannten Programmdateien.")

        return "Aktualisiert: " + ", ".join(updated)


def validate_downloaded_exe(exe_path):
    if not os.path.exists(exe_path):
        raise RuntimeError("Die neue EXE wurde nicht heruntergeladen.")
    if os.path.getsize(exe_path) < 1024 * 1024:
        raise RuntimeError("Die heruntergeladene EXE ist zu klein oder unvollstaendig.")
    with open(exe_path, "rb") as handle:
        if handle.read(2) != b"MZ":
            raise RuntimeError("Die heruntergeladene Datei ist keine gueltige Windows-EXE.")


def write_exe_update_script(script_path, current_exe_path, new_exe_path, current_pid):
    script = f"""@echo off
setlocal
set "OLD_EXE={current_exe_path}"
set "NEW_EXE={new_exe_path}"
set "APP_PID={current_pid}"
set "SCRIPT_DIR=%~dp0"

:wait_for_app
tasklist /FI "PID eq %APP_PID%" 2>NUL | findstr /C:"%APP_PID%" >NUL
if not errorlevel 1 (
    timeout /T 1 /NOBREAK >NUL
    goto wait_for_app
)

set /A TRY_COUNT=0
:replace_exe
set /A TRY_COUNT+=1
move /Y "%NEW_EXE%" "%OLD_EXE%" >NUL
if exist "%NEW_EXE%" (
    if %TRY_COUNT% LSS 20 (
        timeout /T 1 /NOBREAK >NUL
        goto replace_exe
    )
    exit /B 1
)

start "" "%OLD_EXE%"
cd /d "%TEMP%"
del "%~f0"
rmdir "%SCRIPT_DIR%" 2>NUL
"""
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(script)


def prepare_exe_update(download_url=None):
    if not is_frozen_app():
        return {
            "mode": "files",
            "message": download_and_apply_zip_update(),
        }

    update_dir = tempfile.mkdtemp(prefix="game_media_control_update_")

    current_exe_path = os.path.abspath(sys.executable)
    new_exe_path = os.path.join(update_dir, f"{APP_NAME}.new.exe")
    script_path = os.path.join(update_dir, "finish_update.bat")

    download_url_to_file(download_url or GITHUB_RAW_EXE_URL, new_exe_path, timeout=90)
    validate_downloaded_exe(new_exe_path)
    write_exe_update_script(script_path, current_exe_path, new_exe_path, os.getpid())

    return {
        "mode": "exe",
        "message": "Neue EXE wurde heruntergeladen. Die App wird gleich geschlossen, ersetzt und neu gestartet.",
        "script_path": script_path,
    }


def start_hidden_update_script(script_path):
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        ["cmd.exe", "/c", script_path],
        cwd=os.path.dirname(script_path),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def get_virtual_screen():
    x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return x, y, width, height


def get_foreground_title():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def is_valorant_foreground():
    return "VALORANT" in get_foreground_title().upper()


def is_lol_foreground():
    title = get_foreground_title().upper()
    return "LEAGUE OF LEGENDS" in title or "LOL" in title


def send_appcommand(command):
    user32.SendMessageW(HWND_BROADCAST, WM_APPCOMMAND, 0, command << 16)


def send_media_play():
    send_appcommand(APPCOMMAND_MEDIA_PLAY)


def send_media_pause():
    send_appcommand(APPCOMMAND_MEDIA_PAUSE)


def send_media_toggle():
    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
    user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)


def capture_region(left, top, width, height):
    if width <= 0 or height <= 0:
        raise ValueError("Der Aufnahmebereich ist leer.")

    screen_dc = user32.GetDC(None)
    if not screen_dc:
        win_error("Konnte den Bildschirm nicht lesen.")

    mem_dc = gdi32.CreateCompatibleDC(screen_dc)
    if not mem_dc:
        user32.ReleaseDC(None, screen_dc)
        win_error("Konnte keinen Speicher-DC erstellen.")

    bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
    if not bitmap:
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(None, screen_dc)
        win_error("Konnte kein Bildschirm-Bitmap erstellen.")

    old_object = gdi32.SelectObject(mem_dc, bitmap)
    try:
        ok = gdi32.BitBlt(mem_dc, 0, 0, width, height, screen_dc, left, top, SRCCOPY)
        if not ok:
            win_error("BitBlt ist fehlgeschlagen.")

        bitmap_info = BITMAPINFO()
        bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bitmap_info.bmiHeader.biWidth = width
        bitmap_info.bmiHeader.biHeight = -height
        bitmap_info.bmiHeader.biPlanes = 1
        bitmap_info.bmiHeader.biBitCount = 32
        bitmap_info.bmiHeader.biCompression = 0

        buffer_size = width * height * 4
        buffer = ctypes.create_string_buffer(buffer_size)
        rows = gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer, ctypes.byref(bitmap_info), DIB_RGB_COLORS)
        if rows != height:
            win_error("Konnte die Bildschirmdaten nicht kopieren.")
        return buffer.raw
    finally:
        if old_object:
            gdi32.SelectObject(mem_dc, old_object)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(None, screen_dc)


def normalize_rgb(value, fallback=VALORANT_TARGET_RGB):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return fallback

    try:
        red, green, blue = (int(channel) for channel in value)
    except (TypeError, ValueError):
        return fallback

    return (
        max(0, min(255, red)),
        max(0, min(255, green)),
        max(0, min(255, blue)),
    )


def rgb_to_hex(rgb):
    red, green, blue = normalize_rgb(rgb)
    return f"#{red:02x}{green:02x}{blue:02x}"


def parse_rgb_input(value):
    text = str(value or "").strip().lower()
    compact = text.replace(" ", "")
    if not compact:
        raise ValueError("Gib eine Farbe ein, z.B. #ff4655 oder 255,70,85.")

    if compact.startswith("#"):
        compact = compact[1:]
    if compact.startswith("0x"):
        compact = compact[2:]

    if re.fullmatch(r"[0-9a-f]{3}", compact):
        compact = "".join(char * 2 for char in compact)
    if re.fullmatch(r"[0-9a-f]{6}", compact):
        return (
            int(compact[0:2], 16),
            int(compact[2:4], 16),
            int(compact[4:6], 16),
        )

    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    if len(numbers) >= 3:
        channels = tuple(int(float(number)) for number in numbers[:3])
        if all(0 <= channel <= 255 for channel in channels):
            return channels
        raise ValueError("RGB-Werte muessen zwischen 0 und 255 liegen.")

    raise ValueError("Farbe nicht erkannt. Nutze z.B. #ff4655 oder 255,70,85.")


def format_rgb(rgb):
    normalized = normalize_rgb(rgb)
    return f"{rgb_to_hex(normalized)} RGB{normalized}"


def get_valorant_target_rgb(config_data):
    return normalize_rgb(config_data.get("valorant_target_rgb"), VALORANT_TARGET_RGB)


def find_dominant_red_color(raw_bgra, width, height):
    total = width * height
    color_counts = {}

    for index in range(0, len(raw_bgra), 4):
        blue = raw_bgra[index]
        green = raw_bgra[index + 1]
        red = raw_bgra[index + 2]

        if red < VALORANT_AUTO_RED_MIN_VALUE:
            continue
        if red - green < VALORANT_AUTO_RED_MIN_GAP or red - blue < VALORANT_AUTO_RED_MIN_GAP:
            continue

        rgb = (red, green, blue)
        color_counts[rgb] = color_counts.get(rgb, 0) + 1

    if not color_counts:
        return None, 0, total

    def sort_key(item):
        rgb, count = item
        red, green, blue = rgb
        dominance = red - max(green, blue)
        default_distance = sum(abs(channel - target) for channel, target in zip(rgb, VALORANT_TARGET_RGB))
        return count, dominance, red, -default_distance

    color, count = max(color_counts.items(), key=sort_key)
    return color, count, total


def capture_color_sample_at_point(screen_x, screen_y, sample_size=15):
    virtual_x, virtual_y, virtual_w, virtual_h = get_virtual_screen()
    half_size = max(1, sample_size // 2)
    left = max(virtual_x, int(screen_x) - half_size)
    top = max(virtual_y, int(screen_y) - half_size)
    right = min(virtual_x + virtual_w, int(screen_x) + half_size + 1)
    bottom = min(virtual_y + virtual_h, int(screen_y) + half_size + 1)
    width = max(1, right - left)
    height = max(1, bottom - top)

    raw = capture_region(left, top, width, height)
    target_rgb, target_pixels, total_pixels = find_dominant_red_color(raw, width, height)
    return target_rgb, target_pixels, total_pixels


def get_valorant_color_percent(raw_bgra, width, height, color_tolerance, target_rgb=None):
    total = width * height
    if total <= 0:
        return 0.0, 0, 0

    target_red, target_green, target_blue = normalize_rgb(target_rgb)
    matched_pixels = 0
    for index in range(0, len(raw_bgra), 4):
        blue = raw_bgra[index]
        green = raw_bgra[index + 1]
        red = raw_bgra[index + 2]

        if (
            abs(red - target_red) <= color_tolerance
            and abs(green - target_green) <= color_tolerance
            and abs(blue - target_blue) <= color_tolerance
        ):
            matched_pixels += 1

    return matched_pixels * 100.0 / total, matched_pixels, total


def detect_state_from_red(raw_bgra, width, height, red_pixel_percent, color_tolerance, target_rgb=None):
    percent, red_pixels, total = get_valorant_color_percent(raw_bgra, width, height, color_tolerance, target_rgb)
    state = "red" if percent >= red_pixel_percent else "no_red"
    return state, percent, red_pixels, total


def build_bright_mask(raw_bgra, width, height, bright_min_value):
    total = width * height
    mask = bytearray(total)
    bright_pixels = 0

    pixel_index = 0
    for index in range(0, len(raw_bgra), 4):
        blue = raw_bgra[index]
        green = raw_bgra[index + 1]
        red = raw_bgra[index + 2]

        if max(red, green, blue) >= bright_min_value:
            mask[pixel_index] = 1
            bright_pixels += 1
        pixel_index += 1

    return mask, bright_pixels, total


def count_digit_like_components(mask, width, height, min_digit_height, min_digit_area):
    total = width * height
    visited = bytearray(total)
    components = 0

    for start in range(total):
        if not mask[start] or visited[start]:
            continue

        stack = [start]
        visited[start] = 1
        area = 0
        min_x = width
        max_x = -1
        min_y = height
        max_y = -1

        while stack:
            index = stack.pop()
            area += 1
            x = index % width
            y = index // width
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y

            if x > 0:
                neighbour = index - 1
                if mask[neighbour] and not visited[neighbour]:
                    visited[neighbour] = 1
                    stack.append(neighbour)
            if x < width - 1:
                neighbour = index + 1
                if mask[neighbour] and not visited[neighbour]:
                    visited[neighbour] = 1
                    stack.append(neighbour)
            if y > 0:
                neighbour = index - width
                if mask[neighbour] and not visited[neighbour]:
                    visited[neighbour] = 1
                    stack.append(neighbour)
            if y < height - 1:
                neighbour = index + width
                if mask[neighbour] and not visited[neighbour]:
                    visited[neighbour] = 1
                    stack.append(neighbour)
            if x > 0 and y > 0:
                neighbour = index - width - 1
                if mask[neighbour] and not visited[neighbour]:
                    visited[neighbour] = 1
                    stack.append(neighbour)
            if x < width - 1 and y > 0:
                neighbour = index - width + 1
                if mask[neighbour] and not visited[neighbour]:
                    visited[neighbour] = 1
                    stack.append(neighbour)
            if x > 0 and y < height - 1:
                neighbour = index + width - 1
                if mask[neighbour] and not visited[neighbour]:
                    visited[neighbour] = 1
                    stack.append(neighbour)
            if x < width - 1 and y < height - 1:
                neighbour = index + width + 1
                if mask[neighbour] and not visited[neighbour]:
                    visited[neighbour] = 1
                    stack.append(neighbour)

        box_width = max_x - min_x + 1
        box_height = max_y - min_y + 1
        box_area = box_width * box_height
        if box_area <= 0:
            continue

        aspect = box_width / float(box_height)
        fill = area / float(box_area)

        if (
            area >= min_digit_area
            and box_height >= min_digit_height
            and 0.05 <= aspect <= 1.7
            and 0.05 <= fill <= 1.0
            and (fill <= 0.9 or aspect <= 0.35)
        ):
            components += 1

    return components


def detect_state_from_number(
    raw_bgra,
    width,
    height,
    bright_pixel_percent,
    bright_min_value,
    min_digit_height,
    min_digit_area,
    min_digit_components,
):
    mask, bright_pixels, total = build_bright_mask(raw_bgra, width, height, bright_min_value)
    percent = bright_pixels * 100.0 / total if total else 0.0
    components = 0
    if percent >= bright_pixel_percent:
        components = count_digit_like_components(mask, width, height, min_digit_height, min_digit_area)
    state = "number" if percent >= bright_pixel_percent and components >= min_digit_components else "no_number"
    return state, percent, bright_pixels, total, components


def region_to_text(region):
    if not region:
        return "nicht gewaehlt"
    return f"x={region['left']} y={region['top']} w={region['width']} h={region['height']}"


class RegionSelector(tk.Toplevel):
    def __init__(self, master, callback, prompt, accent="#ff4655"):
        super().__init__(master)
        self.callback = callback
        self.prompt = prompt
        self.accent = accent
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.virtual_x, self.virtual_y, self.virtual_w, self.virtual_h = get_virtual_screen()

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.32)
        self.configure(bg="black")
        self.geometry(f"{self.virtual_w}x{self.virtual_h}+{self.virtual_x}+{self.virtual_y}")

        self.canvas = tk.Canvas(self, bg="black", cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(
            24,
            24,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 16, "bold"),
            text=self.prompt,
        )
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda _event: self.cancel())
        self.focus_force()

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline=self.accent, width=3)

    def on_drag(self, event):
        if self.rect_id is not None:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if self.start_x is None or self.start_y is None:
            self.cancel()
            return

        left = min(self.start_x, event.x) + self.virtual_x
        top = min(self.start_y, event.y) + self.virtual_y
        right = max(self.start_x, event.x) + self.virtual_x
        bottom = max(self.start_y, event.y) + self.virtual_y
        width = right - left
        height = bottom - top

        self.destroy()
        if width < 20 or height < 20:
            self.callback(None)
            return

        self.callback({"left": int(left), "top": int(top), "width": int(width), "height": int(height)})

    def cancel(self):
        self.destroy()
        self.callback(None)


class ColorSelector(tk.Toplevel):
    def __init__(self, master, callback, prompt, accent="#ff4655"):
        super().__init__(master)
        self.callback = callback
        self.prompt = prompt
        self.accent = accent
        self.virtual_x, self.virtual_y, self.virtual_w, self.virtual_h = get_virtual_screen()

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.28)
        self.configure(bg="black")
        self.geometry(f"{self.virtual_w}x{self.virtual_h}+{self.virtual_x}+{self.virtual_y}")

        self.canvas = tk.Canvas(self, bg="black", cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(
            24,
            24,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 16, "bold"),
            text=self.prompt,
        )
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda _event: self.cancel())
        self.focus_force()

    def on_release(self, event):
        point = {"x": int(event.x + self.virtual_x), "y": int(event.y + self.virtual_y)}
        self.destroy()
        self.callback(point)

    def cancel(self):
        self.destroy()
        self.callback(None)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.minsize(1000, 720)
        start_width = min(1280, self.winfo_screenwidth() - 80)
        start_height = min(860, self.winfo_screenheight() - 80)
        self.geometry(f"{start_width}x{start_height}")

        migrate_legacy_config_if_needed()
        self.config_data = load_config()
        self.theme_mode = normalize_theme_mode(self.config_data.get("theme_mode", "system"))
        self.active_theme = resolved_theme(self.theme_mode)
        self.palette = FLUENT_PALETTES[self.active_theme]
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.monitor_thread = None
        self.active_monitor = None
        self.audio_choice_map = {}
        self.audio_session_labels = []
        self.background_frames = []
        self.background_index = 0
        self.background_label = None
        self.logo_image = None
        self.logo_header_image = None
        self.banner_image = None
        self.hero_cover_image = None
        self.hero_cover_zoom = None
        self.hero_canvas = None
        self.hero_update_window = None
        self.last_hero_height = None
        self.root_frame = None
        self.notebook = None
        self.scroll_pages = []
        self.update_available = False
        self.update_check_running = False
        self.manual_update_url = None
        self.update_download_url = None
        self.update_status_var = tk.StringVar(value="Update noch nicht geprueft.")
        self.current_version_var = tk.StringVar(value=get_current_version_text())
        self.latest_version_var = tk.StringVar(value="-")
        self.update_button_text_var = tk.StringVar(value="Update pruefen")
        self.update_button = None
        self.theme_choice_var = tk.StringVar(value=THEME_LABELS.get(self.theme_mode, "System"))
        self.theme_combo = None
        self.auto_launch_choice_var = tk.StringVar(
            value=AUTO_LAUNCH_LABELS.get(normalize_auto_launch_mode(self.config_data.get("auto_launch_mode")), "Nein")
        )
        for variable in (self.update_status_var, self.current_version_var, self.latest_version_var):
            variable.trace_add("write", lambda *_args: self.draw_hero())

        self.region_var = tk.StringVar()
        self.red_settings_var = tk.StringVar()
        self.valorant_color_var = tk.StringVar()
        self.valorant_color_entry_var = tk.StringVar(value=rgb_to_hex(get_valorant_target_rgb(self.config_data)))
        self.valorant_color_swatch = None
        self.monitor_var = tk.StringVar(value="gestoppt")
        self.detected_var = tk.StringVar(value="-")
        self.log_var = tk.StringVar(value="Bereit.")
        self.interval_var = tk.StringVar(value=str(self.config_data.get("interval_ms", 450)))
        self.red_percent_var = tk.StringVar(value=str(self.config_data.get("red_pixel_percent", 1.0)))
        self.red_min_var = tk.StringVar(value=str(self.config_data.get("red_min_value", 140)))
        self.red_difference_var = tk.StringVar(value=str(self.config_data.get("valorant_color_tolerance", VALORANT_COLOR_TOLERANCE)))
        self.stable_var = tk.StringVar(value=str(self.config_data.get("stable_reads", 2)))
        self.require_valorant_var = tk.BooleanVar(value=bool(self.config_data.get("require_valorant_foreground", True)))
        self.command_mode_var = tk.StringVar(value=self.config_data.get("command_mode", "direct"))
        self.action_mode_var = tk.StringVar(value=self.config_data.get("action_mode", "media"))
        self.target_session_var = tk.StringVar(value=self.config_data.get("target_label", ""))
        self.dead_volume_var = tk.StringVar(value=str(self.config_data.get("dead_volume", 100)))
        self.alive_volume_var = tk.StringVar(value=str(self.config_data.get("alive_volume", 25)))

        self.lol_region_var = tk.StringVar()
        self.lol_number_settings_var = tk.StringVar()
        self.lol_monitor_var = tk.StringVar(value="gestoppt")
        self.lol_detected_var = tk.StringVar(value="-")
        self.lol_log_var = tk.StringVar(value="Bereit.")
        self.lol_interval_var = tk.StringVar(value=str(self.config_data.get("lol_interval_ms", 450)))
        self.lol_bright_percent_var = tk.StringVar(value=str(self.config_data.get("lol_bright_pixel_percent", 0.25)))
        self.lol_bright_min_var = tk.StringVar(value=str(self.config_data.get("lol_bright_min_value", 150)))
        self.lol_digit_height_var = tk.StringVar(value=str(self.config_data.get("lol_min_digit_height", 8)))
        self.lol_digit_area_var = tk.StringVar(value=str(self.config_data.get("lol_min_digit_area", 12)))
        self.lol_digit_components_var = tk.StringVar(value=str(self.config_data.get("lol_min_digit_components", 1)))
        self.lol_stable_var = tk.StringVar(value=str(self.config_data.get("lol_stable_reads", 2)))
        self.require_lol_var = tk.BooleanVar(value=bool(self.config_data.get("require_lol_foreground", True)))
        self.lol_command_mode_var = tk.StringVar(value=self.config_data.get("lol_command_mode", "direct"))
        self.lol_action_mode_var = tk.StringVar(value=self.config_data.get("lol_action_mode", "media"))
        self.lol_target_session_var = tk.StringVar(value=self.config_data.get("lol_target_label", ""))
        self.lol_dead_volume_var = tk.StringVar(value=str(self.config_data.get("lol_dead_volume", 100)))
        self.lol_alive_volume_var = tk.StringVar(value=str(self.config_data.get("lol_alive_volume", 25)))

        self.load_app_assets()
        self.apply_theme()
        self.create_background()
        self.build_ui()
        self.refresh_labels()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(400, self.refresh_audio_sessions)
        self.after(900, self.check_for_updates)
        self.after(200, self.drain_events)

    def apply_theme(self):
        self.theme_mode = normalize_theme_mode(getattr(self, "theme_mode", self.config_data.get("theme_mode", "system")))
        self.active_theme = resolved_theme(self.theme_mode)
        self.palette = FLUENT_PALETTES[self.active_theme]
        palette = self.palette

        try:
            style = ttk.Style(self)
            if style.theme_use() != "clam":
                style.theme_use("clam")
        except tk.TclError:
            style = ttk.Style(self)
        self.style = style

        self.configure(bg=palette["window"])
        default_font = ("Segoe UI", 10)
        heading_font = ("Segoe UI", 11, "bold")
        title_font = ("Segoe UI", 17, "bold")

        style.configure(".", font=default_font, background=palette["window"], foreground=palette["text"])
        style.configure("TFrame", background=palette["window"])
        style.configure("Root.TFrame", background=palette["window"])
        style.configure("Toolbar.TFrame", background=palette["surface"], borderwidth=1, relief="solid")
        style.configure("Card.TFrame", background=palette["surface"], borderwidth=1, relief="solid")
        style.configure("InnerCard.TFrame", background=palette["surface"])
        style.configure("TLabel", background=palette["surface"], foreground=palette["text"])
        style.configure("PageTitle.TLabel", background=palette["window"], foreground=palette["text"], font=heading_font)
        style.configure("Card.TLabel", background=palette["surface"], foreground=palette["text"])
        style.configure("SectionTitle.TLabel", background=palette["surface"], foreground=palette["text"], font=heading_font)
        style.configure("Muted.TLabel", background=palette["surface"], foreground=palette["muted"])
        style.configure("Value.TLabel", background=palette["surface"], foreground=palette["text"])
        style.configure("Log.TLabel", background=palette["surface_alt"], foreground=palette["muted"], padding=(12, 9))
        style.configure("HeroTitle.TLabel", font=title_font)

        style.configure(
            "TButton",
            background=palette["surface_alt"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["surface_alt"],
            darkcolor=palette["surface_alt"],
            focusthickness=2,
            focuscolor=palette["border_focus"],
            padding=(14, 8),
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("pressed", palette["surface_hover"]), ("active", palette["surface_hover"])],
            foreground=[("disabled", palette["disabled"])],
            bordercolor=[("focus", palette["border_focus"]), ("active", palette["border_focus"])],
        )
        style.configure(
            "Accent.TButton",
            background=palette["accent"],
            foreground=palette["accent_text"],
            bordercolor=palette["accent"],
            lightcolor=palette["accent"],
            darkcolor=palette["accent"],
        )
        style.map(
            "Accent.TButton",
            background=[("pressed", palette["accent_pressed"]), ("active", palette["accent_hover"])],
            foreground=[("disabled", palette["disabled"]), ("!disabled", palette["accent_text"])],
        )
        style.configure(
            "Danger.TButton",
            background=palette["danger"],
            foreground="#ffffff",
            bordercolor=palette["danger"],
            lightcolor=palette["danger"],
            darkcolor=palette["danger"],
        )
        style.map("Danger.TButton", background=[("pressed", palette["danger"]), ("active", palette["danger_hover"])])

        for widget_style in ("TEntry", "TCombobox"):
            style.configure(
                widget_style,
                fieldbackground=palette["input"],
                background=palette["input"],
                foreground=palette["text"],
                bordercolor=palette["border"],
                lightcolor=palette["input"],
                darkcolor=palette["input"],
                insertcolor=palette["text"],
                padding=(8, 7),
            )
            style.map(
                widget_style,
                fieldbackground=[("readonly", palette["input"]), ("focus", palette["input"])],
                bordercolor=[("focus", palette["border_focus"]), ("active", palette["border_focus"])],
                foreground=[("disabled", palette["disabled"]), ("!disabled", palette["text"])],
            )

        style.configure("TCheckbutton", background=palette["surface"], foreground=palette["text"], padding=(2, 6))
        style.configure("TRadiobutton", background=palette["surface"], foreground=palette["text"], padding=(2, 6))
        style.map(
            "TCheckbutton",
            background=[("active", palette["surface"])],
            foreground=[("disabled", palette["disabled"]), ("!disabled", palette["text"])],
        )
        style.map(
            "TRadiobutton",
            background=[("active", palette["surface"])],
            foreground=[("disabled", palette["disabled"]), ("!disabled", palette["text"])],
        )

        style.configure(
            "TNotebook",
            background=palette["window"],
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "TNotebook.Tab",
            background=palette["surface_alt"],
            foreground=palette["muted"],
            padding=(18, 10),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", palette["surface"]), ("active", palette["surface_hover"])],
            foreground=[("selected", palette["text"]), ("active", palette["text"])],
        )
        style.configure("Vertical.TScrollbar", background=palette["surface_alt"], troughcolor=palette["surface"])

        self.apply_widget_theme()

    def apply_widget_theme(self):
        palette = self.palette
        if self.background_label:
            self.background_label.configure(bg=palette["window"])
        if self.hero_canvas:
            self.hero_canvas.configure(bg=palette["window"])
            self.draw_hero()
        for page in getattr(self, "scroll_pages", []):
            page["canvas"].configure(bg=palette["window"])
        if hasattr(self, "readme_text"):
            self.readme_text.configure(
                bg=palette["surface"],
                fg=palette["text"],
                insertbackground=palette["text"],
                selectbackground=palette["selection"],
                relief="flat",
                borderwidth=0,
            )
        if self.valorant_color_swatch:
            self.valorant_color_swatch.configure(highlightbackground=palette["border"], highlightcolor=palette["border"])
        self.refresh_labels_if_ready()

    def refresh_labels_if_ready(self):
        if hasattr(self, "region_var"):
            try:
                self.refresh_labels()
            except Exception:
                pass

    def on_theme_selected(self, _event=None):
        selected = self.theme_choice_var.get()
        self.theme_mode = THEME_VALUES.get(selected, "system")
        self.config_data["theme_mode"] = self.theme_mode
        save_config(self.config_data)
        self.apply_theme()

    def on_auto_launch_selected(self, _event=None):
        selected = self.auto_launch_choice_var.get()
        mode = AUTO_LAUNCH_VALUES.get(selected, "none")
        self.config_data["auto_launch_mode"] = mode
        save_config(self.config_data)
        ok, message = configure_watcher_autostart(mode)
        if ok:
            self.set_game_status("valorant", log=message)
            self.set_game_status("lol", log=message)
        else:
            self.show_warning("Autostart", message)

    def load_app_assets(self):
        if os.path.exists(LOGO_PATH):
            try:
                self.logo_image = tk.PhotoImage(file=LOGO_PATH)
                self.logo_header_image = self.logo_image.subsample(8, 8)
                self.iconphoto(True, self.logo_image)
            except tk.TclError:
                self.logo_image = None
                self.logo_header_image = None

        background_path = find_header_background_path()
        if os.path.exists(background_path):
            is_gif = background_path.lower().endswith(".gif")
            index = 0
            while index < MAX_BACKGROUND_FRAMES:
                try:
                    if is_gif:
                        frame = tk.PhotoImage(file=background_path, format=f"gif -index {index}")
                    else:
                        frame = tk.PhotoImage(file=background_path)
                except tk.TclError:
                    break
                self.background_frames.append(frame)
                index += 1
                if not is_gif:
                    break
            if self.background_frames:
                self.banner_image = self.background_frames[0]

    def create_background(self):
        self.configure(bg=self.palette["window"])
        self.background_label = tk.Label(self, bg=self.palette["window"], bd=0)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.background_label.lower()
        if self.background_frames:
            self.background_label.configure(image=self.background_frames[0])
            if len(self.background_frames) > 1:
                self.animate_background()

    def animate_background(self):
        if not self.background_frames or not self.background_label:
            return
        frame = self.background_frames[self.background_index]
        self.background_label.configure(image=frame)
        self.background_index = (self.background_index + 1) % len(self.background_frames)
        self.after(90, self.animate_background)

    def build_ui(self):
        root = ttk.Frame(self, padding=(20, 18, 20, 20), style="Root.TFrame")
        self.root_frame = root
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        self.build_hero(root)
        self.build_toolbar(root)

        notebook = ttk.Notebook(root)
        self.notebook = notebook
        notebook.grid(row=2, column=0, sticky="nsew", pady=(12, 0))

        valorant_tab = self.create_scrollable_tab(notebook, "Valorant")
        lol_tab = self.create_scrollable_tab(notebook, "LoL")
        readme_tab = self.create_scrollable_tab(notebook, "README")

        self.build_valorant_tab(valorant_tab)
        self.build_lol_tab(lol_tab)
        self.build_readme_tab(readme_tab)
        self.bind_all("<FocusIn>", self.scroll_focused_widget_into_view, add="+")
        self.bind_all("<MouseWheel>", self.on_global_mousewheel, add="+")
        self.after_idle(self.resize_hero)

    def create_scrollable_tab(self, notebook, title):
        outer = ttk.Frame(notebook, style="Root.TFrame")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)
        notebook.add(outer, text=title)

        canvas = tk.Canvas(outer, highlightthickness=0, bd=0, bg=self.palette["window"])
        vertical = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        horizontal = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        content = ttk.Frame(canvas, padding=16, style="Root.TFrame")
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        content.columnconfigure(0, weight=1)

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(window_id, width=max(canvas.winfo_width(), content.winfo_reqwidth()))

        def resize_content(event):
            canvas.itemconfigure(window_id, width=max(event.width, content.winfo_reqwidth()))
            canvas.configure(scrollregion=canvas.bbox("all"))

        content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", resize_content)
        canvas.bind("<MouseWheel>", lambda event, c=canvas: self.on_canvas_mousewheel(event, c))
        content.bind("<MouseWheel>", lambda event, c=canvas: self.on_canvas_mousewheel(event, c))

        self.scroll_pages.append({"canvas": canvas, "content": content})
        return content

    def on_canvas_mousewheel(self, event, canvas):
        if event.state & 0x0001:
            canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def on_global_mousewheel(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        if widget is None:
            return
        for page in self.scroll_pages:
            if self.is_descendant(widget, page["content"]) or widget == page["canvas"]:
                return self.on_canvas_mousewheel(event, page["canvas"])
        return None

    def is_descendant(self, widget, ancestor):
        current = widget
        while current is not None:
            if current == ancestor:
                return True
            current = getattr(current, "master", None)
        return False

    def scroll_focused_widget_into_view(self, event):
        widget = event.widget
        for page in self.scroll_pages:
            content = page["content"]
            canvas = page["canvas"]
            if not self.is_descendant(widget, content):
                continue
            self.after_idle(lambda c=canvas, w=widget: self.scroll_widget_into_view(c, w))
            break

    def scroll_widget_into_view(self, canvas, widget):
        try:
            canvas.update_idletasks()
            widget_y = widget.winfo_rooty() - canvas.winfo_rooty()
            widget_bottom = widget_y + widget.winfo_height()
            canvas_height = canvas.winfo_height()
            first, last = canvas.yview()
            if widget_y < 12:
                canvas.yview_moveto(max(0.0, first - (12 - widget_y) / max(canvas.bbox("all")[3], 1)))
            elif widget_bottom > canvas_height - 12:
                canvas.yview_moveto(min(1.0, first + (widget_bottom - canvas_height + 12) / max(canvas.bbox("all")[3], 1)))
        except Exception:
            pass

    def build_toolbar(self, parent):
        toolbar = ttk.Frame(parent, padding=(14, 10), style="Toolbar.TFrame")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        toolbar.columnconfigure(0, weight=1)
        toolbar.columnconfigure(2, weight=0)
        toolbar.columnconfigure(4, weight=0)

        config_text = f"Einstellungen: {CONFIG_PATH}"
        ttk.Label(toolbar, text=config_text, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(toolbar, text="Autostart", style="Muted.TLabel").grid(row=0, column=1, sticky="e", padx=(12, 8))
        self.auto_launch_combo = ttk.Combobox(
            toolbar,
            textvariable=self.auto_launch_choice_var,
            values=list(AUTO_LAUNCH_VALUES.keys()),
            width=26,
            state="readonly",
        )
        self.auto_launch_combo.grid(row=0, column=2, sticky="e")
        self.auto_launch_combo.bind("<<ComboboxSelected>>", self.on_auto_launch_selected)

        ttk.Label(toolbar, text="Design", style="Muted.TLabel").grid(row=0, column=3, sticky="e", padx=(12, 8))
        self.theme_combo = ttk.Combobox(
            toolbar,
            textvariable=self.theme_choice_var,
            values=list(THEME_VALUES.keys()),
            width=10,
            state="readonly",
        )
        self.theme_combo.grid(row=0, column=4, sticky="e")
        self.theme_combo.bind("<<ComboboxSelected>>", self.on_theme_selected)

    def build_hero(self, parent):
        self.hero_canvas = tk.Canvas(parent, height=190, highlightthickness=0, bd=0, bg=self.palette["window"])
        self.hero_canvas.grid(row=0, column=0, sticky="ew")
        self.update_button = ttk.Button(
            self.hero_canvas,
            textvariable=self.update_button_text_var,
            command=self.update_button_clicked,
            style="Accent.TButton",
        )
        self.hero_canvas.bind("<Configure>", lambda _event: self.draw_hero())
        self.bind("<Configure>", lambda _event: self.resize_hero())
        self.resize_hero()
        self.draw_hero()

    def resize_hero(self):
        if not self.hero_canvas:
            return
        window_height = max(self.winfo_height(), 1)
        target_height = max(150, min(230, int(window_height * 0.23)))
        if target_height != self.last_hero_height:
            self.last_hero_height = target_height
            self.hero_canvas.configure(height=target_height)

    def draw_hero(self):
        if not self.hero_canvas:
            return

        canvas = self.hero_canvas
        palette = self.palette
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)
        canvas.delete("all")

        shadow_offset = 4
        rounded_canvas_rect(
            canvas,
            4,
            shadow_offset,
            width - 4,
            height - 2,
            22,
            fill=palette["shadow"],
            outline="",
        )
        rounded_canvas_rect(
            canvas,
            0,
            0,
            width - 8,
            height - 6,
            22,
            fill=palette["surface"],
            outline=palette["border"],
        )
        canvas.save_region = None

        if self.banner_image:
            image_width = self.banner_image.width()
            image_height = self.banner_image.height()
            zoom = max(
                1,
                (width + image_width - 1) // image_width,
                (height + image_height - 1) // image_height,
            )
            if self.hero_cover_zoom != zoom:
                self.hero_cover_image = self.banner_image.zoom(zoom, zoom)
                self.hero_cover_zoom = zoom
            image = self.hero_cover_image
            image_y = int((height - image.height()) * 0.46)
            canvas.create_image(
                (width - image.width()) // 2,
                image_y,
                image=image,
                anchor="nw",
            )
        else:
            rounded_canvas_rect(canvas, 0, 0, width - 8, height - 6, 22, fill=palette["surface_alt"], outline="")

        rounded_canvas_rect(canvas, 0, 0, width - 8, height - 6, 22, fill=palette["hero_overlay"], stipple="gray50", outline="")

        left = 34
        if self.logo_header_image:
            canvas.create_image(left, 32, image=self.logo_header_image, anchor="nw")
            text_left = left + self.logo_header_image.width() + 16
        else:
            text_left = left

        canvas.create_text(
            text_left,
            34,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 18, "bold"),
            text=APP_NAME,
        )
        canvas.create_text(
            left,
            82,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 10),
            width=min(620, max(320, width - 470)),
            text=(
                "Automatische Mediensteuerung fuer Valorant und League of Legends: "
                "Bereich markieren, Zustand erkennen und Musik per Play/Pause oder Lautstaerke regeln."
            ),
        )

        version_x = max(width - 355, left)
        canvas.create_text(
            version_x,
            34,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 10),
            text=f"Aktuell: {self.current_version_var.get()}",
        )
        canvas.create_text(
            version_x,
            56,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 10),
            text=f"Neueste: {self.latest_version_var.get()}",
        )
        canvas.create_text(
            version_x,
            96,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 10),
            width=270,
            text=self.update_status_var.get(),
        )
        self.hero_update_window = canvas.create_window(
            max(version_x + 180, width - 152),
            32,
            anchor="nw",
            window=self.update_button,
        )

    def create_card(self, parent, row, title, pady=(0, 12)):
        shadow = ttk.Frame(parent, style="Root.TFrame")
        shadow.grid(row=row, column=0, sticky="ew", pady=pady)
        shadow.columnconfigure(0, weight=1)

        card = ttk.Frame(shadow, padding=16, style="Card.TFrame")
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text=title, style="SectionTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 12))
        body = ttk.Frame(card, style="InnerCard.TFrame")
        body.grid(row=1, column=0, sticky="ew")
        body.columnconfigure(0, weight=1)
        return body

    def build_readme_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        tools = ttk.Frame(parent, style="Root.TFrame")
        tools.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tools.columnconfigure(0, weight=1)
        ttk.Label(tools, text="README.md", style="PageTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(tools, text="Neu laden", command=self.load_readme_text).grid(row=0, column=1, sticky="e")

        body = ttk.Frame(parent, padding=14, style="Card.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.readme_text = tk.Text(body, wrap="word", height=18, borderwidth=0, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.readme_text.yview)
        self.readme_text.configure(yscrollcommand=scrollbar.set)
        self.readme_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.load_readme_text()

    def load_readme_text(self):
        if not hasattr(self, "readme_text"):
            return
        try:
            with open(README_PATH, "r", encoding="utf-8") as handle:
                text = handle.read()
        except Exception as exc:
            text = f"README konnte nicht geladen werden: {exc}"

        self.readme_text.configure(state="normal")
        self.readme_text.delete("1.0", "end")
        self.readme_text.insert("1.0", text)
        self.readme_text.configure(state="disabled")

    def show_dialog(self, title, message, kind="info"):
        palette = self.palette
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.configure(bg=palette["window"])
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        shell = tk.Frame(dialog, bg=palette["shadow"], padx=1, pady=1)
        shell.pack(fill="both", expand=True, padx=18, pady=18)
        body = tk.Frame(shell, bg=palette["surface"], padx=22, pady=20)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        accent = {
            "error": palette["danger"],
            "warning": palette["warning"],
            "success": palette["success"],
            "info": palette["accent"],
        }.get(kind, palette["accent"])
        symbol = {
            "error": "!",
            "warning": "!",
            "success": "",
            "info": "i",
        }.get(kind, "i")

        icon = tk.Canvas(body, width=34, height=34, bg=palette["surface"], highlightthickness=0)
        icon.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 14))
        icon.create_oval(2, 2, 32, 32, fill=accent, outline=accent)
        if symbol:
            icon.create_text(17, 17, text=symbol, fill=palette["accent_text"] if kind != "warning" else "#ffffff", font=("Segoe UI", 14, "bold"))
        else:
            icon.create_line(10, 18, 15, 23, 25, 11, fill="#ffffff", width=3, capstyle="round", joinstyle="round")

        tk.Label(
            body,
            text=title,
            bg=palette["surface"],
            fg=palette["text"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")
        tk.Label(
            body,
            text=message,
            bg=palette["surface"],
            fg=palette["muted"],
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=430,
        ).grid(row=1, column=1, sticky="ew", pady=(8, 18))

        button_row = ttk.Frame(body, style="InnerCard.TFrame")
        button_row.grid(row=2, column=0, columnspan=2, sticky="e")
        ttk.Button(button_row, text="OK", command=dialog.destroy, style="Accent.TButton").grid(row=0, column=0)

        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.winfo_rootx() + max(0, int((self.winfo_width() - width) / 2))
        y = self.winfo_rooty() + max(0, int((self.winfo_height() - height) / 2))
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()
        dialog.focus_force()
        self.wait_window(dialog)

    def show_info(self, title, message):
        self.show_dialog(title, message, "info")

    def show_warning(self, title, message):
        self.show_dialog(title, message, "warning")

    def show_error(self, title, message):
        self.show_dialog(title, message, "error")

    def update_button_clicked(self):
        if self.manual_update_url:
            webbrowser.open(self.manual_update_url)
            self.update_status_var.set("GitHub wurde im Browser geoeffnet.")
        elif self.update_available:
            self.install_update()
        else:
            self.check_for_updates()

    def check_for_updates(self):
        if self.update_check_running:
            return
        self.update_check_running = True
        self.update_available = False
        self.manual_update_url = None
        self.update_download_url = None
        self.update_button_text_var.set("Prueft...")
        self.update_status_var.set("Suche auf GitHub nach neuer Version...")
        if self.update_button:
            self.update_button.configure(state="disabled")
        threading.Thread(target=self.update_check_worker, daemon=True).start()

    def update_check_worker(self):
        try:
            info = fetch_latest_version_info()
            self.events.put(("update_check", info, None))
        except Exception as exc:
            self.events.put(("update_check", None, str(exc)))

    def apply_update_check_result(self, info, error):
        self.update_check_running = False
        self.current_version_var.set(get_current_version_text())
        if self.update_button:
            self.update_button.configure(state="normal")

        if error:
            self.latest_version_var.set("-")
            self.update_button_text_var.set("Update pruefen")
            self.update_status_var.set(f"Update-Pruefung fehlgeschlagen: {error}")
            return

        latest = info.get("latest", "-")
        self.latest_version_var.set(latest)
        self.update_available = bool(info.get("available"))
        self.manual_update_url = None
        self.update_download_url = info.get("download_url")

        manual_update = bool(info.get("manual_update"))

        if manual_update:
            self.manual_update_url = info.get("download_url") or info.get("url") or GITHUB_REPO_URL
            self.update_button_text_var.set("GitHub oeffnen")
            self.update_status_var.set(info.get("status", "GitHub kann im Browser geoeffnet werden."))
        elif self.update_available:
            self.update_button_text_var.set("Jetzt aktualisieren")
            self.update_status_var.set(info.get("status", "Neue Version auf GitHub gefunden."))
        else:
            self.update_button_text_var.set("Erneut pruefen")
            self.update_status_var.set(info.get("status", "Du hast die neueste Version."))

    def install_update(self):
        if self.update_check_running:
            return
        self.update_check_running = True
        self.update_button_text_var.set("Aktualisiert...")
        if is_frozen_app():
            self.update_status_var.set("Update-EXE wird von GitHub geladen...")
        else:
            self.update_status_var.set("Update-ZIP wird von GitHub geladen...")
        if self.update_button:
            self.update_button.configure(state="disabled")
        threading.Thread(target=self.install_update_worker, daemon=True).start()

    def install_update_worker(self):
        try:
            output = prepare_exe_update(self.update_download_url)
            self.events.put(("update_install", True, output or {"message": "Update abgeschlossen."}))
        except subprocess.CalledProcessError as exc:
            message = exc.output.strip() if exc.output else str(exc)
            self.events.put(("update_install", False, message))
        except Exception as exc:
            self.events.put(("update_install", False, str(exc)))

    def apply_update_install_result(self, success, message):
        self.update_check_running = False
        if self.update_button:
            self.update_button.configure(state="normal")
        if success:
            result = message if isinstance(message, dict) else {"mode": "files", "message": str(message)}
            self.update_available = False
            self.current_version_var.set(get_current_version_text())
            if result.get("mode") == "exe" and result.get("script_path"):
                self.update_button_text_var.set("Update startet...")
                self.update_status_var.set("Update geladen. App wird neu gestartet...")
                self.show_info("Update", result.get("message", "Update wurde geladen. Die App wird jetzt neu gestartet."))
                start_hidden_update_script(result["script_path"])
                self.after(250, self.destroy)
            else:
                self.update_button_text_var.set("Erneut pruefen")
                self.update_status_var.set("Update fertig. App bitte neu starten.")
                self.show_info("Update", "Update wurde geladen. Starte die App neu, damit die neue Version aktiv ist.")
        else:
            self.update_button_text_var.set("Jetzt aktualisieren" if self.update_available else "Update pruefen")
            self.update_status_var.set("Update fehlgeschlagen.")
            self.show_error("Update fehlgeschlagen", message)

    def build_valorant_tab(self, parent):
        parent.columnconfigure(0, weight=1)

        status = self.create_card(parent, 0, "Status")
        status.columnconfigure(1, weight=1)
        self.add_status_row(status, 0, "Bereich", self.region_var)
        self.add_status_row(status, 1, "Rot-Regel", self.red_settings_var)
        self.add_status_row(status, 2, "Monitoring", self.monitor_var)
        self.add_status_row(status, 3, "Erkannt", self.detected_var)

        controls = self.create_card(parent, 1, "Einrichten")
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        ttk.Button(controls, text="Bereich waehlen", command=self.select_valorant_region).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(controls, text="Farbe waehlen", command=self.select_valorant_color).grid(row=0, column=1, sticky="ew")

        self.build_media_section(parent, 2, "valorant")

        settings = self.create_card(parent, 3, "Optionen")
        for column in range(6):
            settings.columnconfigure(column, weight=1)

        ttk.Label(settings, text="Intervall ms").grid(row=0, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.interval_var, width=8).grid(row=0, column=1, sticky="ew", padx=(4, 12))
        ttk.Label(settings, text="Rot %").grid(row=0, column=2, sticky="w")
        ttk.Entry(settings, textvariable=self.red_percent_var, width=8).grid(row=0, column=3, sticky="ew", padx=(4, 12))
        ttk.Label(settings, text="Stabil").grid(row=0, column=4, sticky="w")
        ttk.Entry(settings, textvariable=self.stable_var, width=8).grid(row=0, column=5, sticky="ew", padx=(4, 0))

        ttk.Label(settings, text="Farbe").grid(row=1, column=0, sticky="w", pady=(10, 0))
        color_controls = ttk.Frame(settings, style="InnerCard.TFrame")
        color_controls.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(4, 12), pady=(10, 0))
        color_controls.columnconfigure(1, weight=1)
        self.valorant_color_swatch = tk.Label(color_controls, width=4, relief="solid", borderwidth=1)
        self.valorant_color_swatch.grid(row=0, column=0, sticky="ns", padx=(0, 6))
        ttk.Entry(color_controls, textvariable=self.valorant_color_entry_var, width=14).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(color_controls, text="Speichern", command=self.save_manual_valorant_color).grid(row=0, column=2, sticky="e")
        ttk.Label(settings, text="Toleranz").grid(row=1, column=4, sticky="w", pady=(10, 0))
        ttk.Entry(settings, textvariable=self.red_difference_var, width=8).grid(row=1, column=5, sticky="ew", padx=(4, 0), pady=(10, 0))

        ttk.Checkbutton(settings, text="Nur reagieren, wenn Valorant im Vordergrund ist", variable=self.require_valorant_var).grid(
            row=2, column=0, columnspan=6, sticky="w", pady=(10, 4)
        )
        ttk.Radiobutton(settings, text="Direkte Play/Pause-Befehle", variable=self.command_mode_var, value="direct").grid(
            row=3, column=0, columnspan=3, sticky="w"
        )
        ttk.Radiobutton(settings, text="Fallback: Medien-Toggle bei jedem Wechsel", variable=self.command_mode_var, value="toggle").grid(
            row=3, column=3, columnspan=3, sticky="w"
        )

        run = ttk.Frame(parent, style="Root.TFrame")
        run.grid(row=4, column=0, sticky="ew")
        for column in range(4):
            run.columnconfigure(column, weight=1)

        ttk.Button(run, text="Start", command=self.start_valorant_monitoring, style="Accent.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(run, text="Stop", command=lambda: self.stop_monitoring("valorant"), style="Danger.TButton").grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(run, text="Test Play", command=send_media_play).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(run, text="Test Pause", command=send_media_pause).grid(row=0, column=3, sticky="ew", padx=(8, 0))

        log = ttk.Label(parent, textvariable=self.log_var, wraplength=680, style="Log.TLabel")
        log.grid(row=5, column=0, sticky="ew", pady=(14, 0))

    def build_lol_tab(self, parent):
        parent.columnconfigure(0, weight=1)

        status = self.create_card(parent, 0, "Status")
        status.columnconfigure(1, weight=1)
        self.add_status_row(status, 0, "Bereich", self.lol_region_var)
        self.add_status_row(status, 1, "Zahl-Regel", self.lol_number_settings_var)
        self.add_status_row(status, 2, "Monitoring", self.lol_monitor_var)
        self.add_status_row(status, 3, "Erkannt", self.lol_detected_var)

        controls = self.create_card(parent, 1, "Einrichten")
        controls.columnconfigure(0, weight=1)
        ttk.Button(controls, text="Bereich waehlen", command=self.select_lol_region).grid(row=0, column=0, sticky="ew")

        self.build_media_section(parent, 2, "lol")

        settings = self.create_card(parent, 3, "Optionen")
        for column in range(6):
            settings.columnconfigure(column, weight=1)

        ttk.Label(settings, text="Intervall ms").grid(row=0, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.lol_interval_var, width=8).grid(row=0, column=1, sticky="ew", padx=(4, 12))
        ttk.Label(settings, text="Hell %").grid(row=0, column=2, sticky="w")
        ttk.Entry(settings, textvariable=self.lol_bright_percent_var, width=8).grid(row=0, column=3, sticky="ew", padx=(4, 12))
        ttk.Label(settings, text="Stabil").grid(row=0, column=4, sticky="w")
        ttk.Entry(settings, textvariable=self.lol_stable_var, width=8).grid(row=0, column=5, sticky="ew", padx=(4, 0))

        ttk.Label(settings, text="Hell min").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(settings, textvariable=self.lol_bright_min_var, width=8).grid(row=1, column=1, sticky="ew", padx=(4, 12), pady=(10, 0))
        ttk.Label(settings, text="Ziffer Hoehe").grid(row=1, column=2, sticky="w", pady=(10, 0))
        ttk.Entry(settings, textvariable=self.lol_digit_height_var, width=8).grid(row=1, column=3, sticky="ew", padx=(4, 12), pady=(10, 0))
        ttk.Label(settings, text="Ziffer Flaeche").grid(row=1, column=4, sticky="w", pady=(10, 0))
        ttk.Entry(settings, textvariable=self.lol_digit_area_var, width=8).grid(row=1, column=5, sticky="ew", padx=(4, 0), pady=(10, 0))

        ttk.Label(settings, text="Komponenten").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(settings, textvariable=self.lol_digit_components_var, width=8).grid(row=2, column=1, sticky="ew", padx=(4, 12), pady=(10, 0))

        ttk.Checkbutton(settings, text="Nur reagieren, wenn League of Legends im Vordergrund ist", variable=self.require_lol_var).grid(
            row=3, column=0, columnspan=6, sticky="w", pady=(10, 4)
        )
        ttk.Radiobutton(settings, text="Direkte Play/Pause-Befehle", variable=self.lol_command_mode_var, value="direct").grid(
            row=4, column=0, columnspan=3, sticky="w"
        )
        ttk.Radiobutton(settings, text="Fallback: Medien-Toggle bei jedem Wechsel", variable=self.lol_command_mode_var, value="toggle").grid(
            row=4, column=3, columnspan=3, sticky="w"
        )

        run = ttk.Frame(parent, style="Root.TFrame")
        run.grid(row=4, column=0, sticky="ew")
        for column in range(4):
            run.columnconfigure(column, weight=1)

        ttk.Button(run, text="Start", command=self.start_lol_monitoring, style="Accent.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(run, text="Stop", command=lambda: self.stop_monitoring("lol"), style="Danger.TButton").grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(run, text="Test Play", command=send_media_play).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(run, text="Test Pause", command=send_media_pause).grid(row=0, column=3, sticky="ew", padx=(8, 0))

        log = ttk.Label(parent, textvariable=self.lol_log_var, wraplength=680, style="Log.TLabel")
        log.grid(row=5, column=0, sticky="ew", pady=(14, 0))

    def build_media_section(self, parent, row, game):
        is_lol = game == "lol"
        target_var = self.lol_target_session_var if is_lol else self.target_session_var
        action_var = self.lol_action_mode_var if is_lol else self.action_mode_var
        dead_volume_var = self.lol_dead_volume_var if is_lol else self.dead_volume_var
        alive_volume_var = self.lol_alive_volume_var if is_lol else self.alive_volume_var

        media = self.create_card(parent, row, "Medienwiedergabe")
        for column in range(6):
            media.columnconfigure(column, weight=1)

        ttk.Label(media, text="Ziel").grid(row=0, column=0, sticky="w")
        combo = ttk.Combobox(media, textvariable=target_var, values=self.audio_session_labels, state="readonly")
        combo.grid(row=0, column=1, columnspan=4, sticky="ew", padx=(4, 8))
        combo.bind("<<ComboboxSelected>>", lambda _event, selected_game=game: self.audio_target_selected(selected_game))
        ttk.Button(media, text="Aktualisieren", command=self.refresh_audio_sessions).grid(row=0, column=5, sticky="ew")
        if is_lol:
            self.lol_target_session_combo = combo
        else:
            self.target_session_combo = combo

        ttk.Radiobutton(media, text="Play/Pause steuern", variable=action_var, value="media").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )
        ttk.Radiobutton(media, text="Nur Lautstaerke anpassen", variable=action_var, value="volume").grid(
            row=1, column=3, columnspan=3, sticky="w", pady=(10, 0)
        )

        ttk.Label(media, text="Tot %").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(media, textvariable=dead_volume_var, width=8).grid(row=2, column=1, sticky="ew", padx=(4, 12), pady=(10, 0))
        ttk.Label(media, text="Nicht tot %").grid(row=2, column=2, sticky="w", pady=(10, 0))
        ttk.Entry(media, textvariable=alive_volume_var, width=8).grid(row=2, column=3, sticky="ew", padx=(4, 12), pady=(10, 0))
        ttk.Button(media, text="Test Tot", command=lambda selected_game=game: self.test_volume(selected_game, True)).grid(
            row=2, column=4, sticky="ew", padx=(0, 4), pady=(10, 0)
        )
        ttk.Button(media, text="Test Nicht tot", command=lambda selected_game=game: self.test_volume(selected_game, False)).grid(
            row=2, column=5, sticky="ew", pady=(10, 0)
        )

    def add_status_row(self, parent, row, label, variable):
        ttk.Label(parent, text=label + ":", style="Muted.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 14), pady=4)
        ttk.Label(parent, textvariable=variable, wraplength=680, style="Value.TLabel").grid(row=row, column=1, sticky="w", pady=4)

    def audio_keys_for_game(self, game):
        if game == "lol":
            return {
                "action_mode": "lol_action_mode",
                "target_process": "lol_target_process",
                "target_label": "lol_target_label",
                "dead_volume": "lol_dead_volume",
                "alive_volume": "lol_alive_volume",
            }
        return {
            "action_mode": "action_mode",
            "target_process": "target_process",
            "target_label": "target_label",
            "dead_volume": "dead_volume",
            "alive_volume": "alive_volume",
        }

    def audio_vars_for_game(self, game):
        if game == "lol":
            return {
                "action_mode": self.lol_action_mode_var,
                "target": self.lol_target_session_var,
                "dead_volume": self.lol_dead_volume_var,
                "alive_volume": self.lol_alive_volume_var,
            }
        return {
            "action_mode": self.action_mode_var,
            "target": self.target_session_var,
            "dead_volume": self.dead_volume_var,
            "alive_volume": self.alive_volume_var,
        }

    def parse_volume_percent(self, value, label):
        try:
            volume = float(value)
        except ValueError:
            raise ValueError(f"{label} muss eine Zahl sein.")
        if volume < 0 or volume > 100:
            raise ValueError(f"{label} muss zwischen 0 und 100 liegen.")
        return volume

    def refresh_audio_sessions(self):
        try:
            sessions = enumerate_audio_sessions()
        except Exception as exc:
            message = f"Konnte Medienwiedergaben nicht lesen: {exc}"
            self.set_game_status("valorant", log=message)
            self.set_game_status("lol", log=message)
            return

        self.audio_choice_map = {session["label"]: session for session in sessions}
        self.audio_session_labels = list(self.audio_choice_map)
        for combo_name in ("target_session_combo", "lol_target_session_combo"):
            combo = getattr(self, combo_name, None)
            if combo:
                combo.configure(values=self.audio_session_labels)

        self.restore_audio_target("valorant")
        self.restore_audio_target("lol")
        message = (
            f"{len(self.audio_session_labels)} Medienwiedergabe(n) gefunden."
            if self.audio_session_labels
            else "Keine laufende Medienwiedergabe gefunden."
        )
        self.set_game_status("valorant", log=message)
        self.set_game_status("lol", log=message)

    def restore_audio_target(self, game):
        keys = self.audio_keys_for_game(game)
        vars_for_game = self.audio_vars_for_game(game)
        selected_label = vars_for_game["target"].get()
        if selected_label in self.audio_choice_map:
            self.audio_target_selected(game)
            return

        saved_process = os.path.basename(self.config_data.get(keys["target_process"], "")).lower()
        if not saved_process:
            return

        for label, session in self.audio_choice_map.items():
            if os.path.basename(session["process_name"]).lower() == saved_process:
                vars_for_game["target"].set(label)
                self.config_data[keys["target_label"]] = label
                self.config_data[keys["target_process"]] = session["process_name"]
                return

    def audio_target_selected(self, game):
        keys = self.audio_keys_for_game(game)
        vars_for_game = self.audio_vars_for_game(game)
        selected_label = vars_for_game["target"].get()
        session = self.audio_choice_map.get(selected_label)
        if not session:
            return
        self.config_data[keys["target_label"]] = selected_label
        self.config_data[keys["target_process"]] = session["process_name"]
        save_config(self.config_data)
        self.set_game_status(game, log=f"Medienziel gespeichert: {session['process_name']}")

    def sync_audio_settings(self, game):
        keys = self.audio_keys_for_game(game)
        vars_for_game = self.audio_vars_for_game(game)
        action_mode = vars_for_game["action_mode"].get()
        if action_mode not in ("media", "volume"):
            action_mode = "media"
            vars_for_game["action_mode"].set(action_mode)

        dead_volume = self.parse_volume_percent(vars_for_game["dead_volume"].get(), "Tot %")
        alive_volume = self.parse_volume_percent(vars_for_game["alive_volume"].get(), "Nicht tot %")
        selected_label = vars_for_game["target"].get()
        session = self.audio_choice_map.get(selected_label)
        target_process = self.config_data.get(keys["target_process"], "")

        if session:
            target_process = session["process_name"]
            self.config_data[keys["target_label"]] = selected_label
            self.config_data[keys["target_process"]] = target_process
        elif action_mode == "volume" and not target_process:
            raise ValueError("Waehle zuerst eine Medienwiedergabe aus oder klicke auf Aktualisieren.")

        self.config_data[keys["action_mode"]] = action_mode
        self.config_data[keys["dead_volume"]] = dead_volume
        self.config_data[keys["alive_volume"]] = alive_volume
        save_config(self.config_data)

        return {
            "action_mode": action_mode,
            "target_process": target_process,
            "dead_volume": dead_volume,
            "alive_volume": alive_volume,
        }

    def saved_audio_settings(self, game):
        keys = self.audio_keys_for_game(game)
        return {
            "action_mode": self.config_data.get(keys["action_mode"], "media"),
            "target_process": self.config_data.get(keys["target_process"], ""),
            "dead_volume": float(self.config_data.get(keys["dead_volume"], 100)),
            "alive_volume": float(self.config_data.get(keys["alive_volume"], 25)),
        }

    def test_volume(self, game, is_dead):
        try:
            audio_settings = self.sync_audio_settings(game)
            volume = audio_settings["dead_volume"] if is_dead else audio_settings["alive_volume"]
            changed = set_audio_session_volume(audio_settings["target_process"], volume)
        except Exception as exc:
            self.show_error("Lautstaerke pruefen", str(exc))
            return

        state_text = "tot" if is_dead else "nicht tot"
        if changed:
            self.set_game_status(game, log=f"Test: {volume:g}% fuer {audio_settings['target_process']} gesetzt ({state_text}).")
        else:
            self.set_game_status(game, log=f"Keine laufende Audio-Sitzung fuer {audio_settings['target_process']} gefunden.")

    def apply_state_action(self, game, state, command_mode, audio_settings):
        is_dead = state in ("red", "number")
        state_text = "tot" if is_dead else "nicht tot"

        if audio_settings["action_mode"] == "volume":
            volume = audio_settings["dead_volume"] if is_dead else audio_settings["alive_volume"]
            changed = set_audio_session_volume(audio_settings["target_process"], volume)
            if changed:
                return f"Lautstaerke {volume:g}% fuer {audio_settings['target_process']} gesetzt, weil Zustand jetzt {state_text} ist."
            return f"Keine laufende Audio-Sitzung fuer {audio_settings['target_process']} gefunden."

        if command_mode == "toggle":
            send_media_toggle()
            return f"Medien-Toggle gesendet, weil Zustand jetzt {state_text} ist."
        if is_dead:
            send_media_play()
            return f"Play gesendet, weil Zustand jetzt {state_text} ist."

        send_media_pause()
        return f"Pause gesendet, weil Zustand jetzt {state_text} ist."

    def refresh_labels(self):
        target_rgb = get_valorant_target_rgb(self.config_data)
        target_hex = rgb_to_hex(target_rgb)
        self.region_var.set(region_to_text(self.config_data.get("region")))
        self.valorant_color_var.set(format_rgb(target_rgb))
        self.valorant_color_entry_var.set(target_hex)
        if self.valorant_color_swatch:
            self.valorant_color_swatch.configure(bg=target_hex)
        self.red_settings_var.set(
            f"Tot ab {self.config_data.get('red_pixel_percent', 1.0)}% Pixeln mit {format_rgb(target_rgb)} "
            f"(Toleranz {self.config_data.get('valorant_color_tolerance', VALORANT_COLOR_TOLERANCE)})"
        )
        self.lol_region_var.set(region_to_text(self.config_data.get("lol_region")))
        self.lol_number_settings_var.set(
            f"Tot ab {self.config_data.get('lol_bright_pixel_percent', 0.25)}% hellen Pixeln "
            f"und {self.config_data.get('lol_min_digit_components', 1)} Ziffer-Komponente(n) "
            f"(Hell min {self.config_data.get('lol_bright_min_value', 150)})"
        )

    def select_valorant_region(self):
        self.show_info(
            "Bereich waehlen",
            "Nach OK hast du 3 Sekunden, um Valorant sichtbar zu machen. Ziehe dann den Bereich, "
            "der ueberwacht werden soll.",
        )
        self.withdraw()
        self.after(3000, lambda: self.open_region_selector("valorant"))

    def select_valorant_color(self):
        self.show_info(
            "Farbe waehlen",
            "Nach OK hast du 3 Sekunden, um Valorant sichtbar zu machen. Klicke dann direkt auf die rote Farbe, "
            "die als tot erkannt werden soll.",
        )
        self.withdraw()
        self.after(3000, self.open_valorant_color_selector)

    def select_lol_region(self):
        self.show_info(
            "LoL-Bereich waehlen",
            "Nach OK hast du 3 Sekunden, um League of Legends sichtbar zu machen. Ziehe dann den Bereich, "
            "in dem die Zahl oder der Countdown erscheint.",
        )
        self.withdraw()
        self.after(3000, lambda: self.open_region_selector("lol"))

    def open_region_selector(self, game):
        if game == "lol":
            prompt = "Bereich ziehen, in dem die LoL-Zahl erkannt werden soll. Esc bricht ab."
            RegionSelector(self, lambda region: self.region_selected("lol", region), prompt, "#2fb7d6")
        else:
            prompt = "Bereich ziehen, der fuer Valorant ueberwacht werden soll. Esc bricht ab."
            RegionSelector(self, lambda region: self.region_selected("valorant", region), prompt, "#ff4655")

    def open_valorant_color_selector(self):
        prompt = "Auf die rote Valorant-Farbe klicken. Esc bricht ab."
        ColorSelector(self, self.valorant_color_selected, prompt, "#ff4655")

    def region_selected(self, game, region):
        self.deiconify()
        self.lift()
        if not region:
            self.set_game_status(game, log="Bereichsauswahl abgebrochen oder zu klein.")
            return

        if game == "lol":
            self.config_data["lol_region"] = region
            self.set_game_status("lol", log="Bereich gespeichert. Start druecken, dann wird eine Zahl in diesem Bereich erkannt.")
        else:
            self.config_data["region"] = region
            self.set_game_status("valorant", log="Bereich gespeichert. Farbe separat waehlen oder Start druecken.")

        save_config(self.config_data)
        self.refresh_labels()

    def valorant_color_selected(self, point):
        if not point:
            self.deiconify()
            self.lift()
            self.set_game_status("valorant", log="Farbauswahl abgebrochen.")
            return

        self.after(140, lambda selected_point=point: self.apply_valorant_color_selection(selected_point))

    def apply_valorant_color_selection(self, point):
        try:
            target_rgb, target_pixels, total_pixels = capture_color_sample_at_point(point["x"], point["y"])
            if not target_rgb:
                message = (
                    f"Keine rote Farbe am Klickpunkt gefunden. Farbe bleibt "
                    f"{format_rgb(get_valorant_target_rgb(self.config_data))}."
                )
            else:
                self.config_data["valorant_target_rgb"] = list(target_rgb)
                self.config_data["valorant_color_tolerance"] = 0
                self.config_data["red_difference"] = 0
                self.red_difference_var.set("0")
                save_config(self.config_data)
                message = (
                    f"Farbe {format_rgb(target_rgb)} gespeichert "
                    f"({target_pixels}/{total_pixels} Pixel, Toleranz 0)."
                )
        except Exception as exc:
            message = f"Farbe konnte nicht gelesen werden: {exc}"

        self.deiconify()
        self.lift()
        self.set_game_status("valorant", log=message)
        self.refresh_labels()

    def save_manual_valorant_color(self):
        try:
            target_rgb = parse_rgb_input(self.valorant_color_entry_var.get())
        except ValueError as exc:
            self.show_error("Farbe speichern", str(exc))
            return

        self.config_data["valorant_target_rgb"] = list(target_rgb)
        self.config_data["valorant_color_tolerance"] = 0
        self.config_data["red_difference"] = 0
        self.red_difference_var.set("0")
        save_config(self.config_data)
        self.refresh_labels()
        self.set_game_status("valorant", log=f"Farbe {format_rgb(target_rgb)} manuell gespeichert (Toleranz 0).")

    def sync_valorant_settings(self):
        try:
            interval_ms = int(float(self.interval_var.get()))
            red_pixel_percent = float(self.red_percent_var.get())
            color_tolerance = int(float(self.red_difference_var.get()))
            stable_reads = int(float(self.stable_var.get()))
        except ValueError:
            raise ValueError("Intervall, Rot %, Toleranz und Stabil muessen Zahlen sein.")

        if interval_ms < 100:
            raise ValueError("Intervall muss mindestens 100 ms sein.")
        if red_pixel_percent < 0 or red_pixel_percent > 100:
            raise ValueError("Rot % muss zwischen 0 und 100 liegen.")
        if color_tolerance < 0 or color_tolerance > 80:
            raise ValueError("Toleranz muss zwischen 0 und 80 liegen.")
        if stable_reads < 1:
            raise ValueError("Stabil muss mindestens 1 sein.")
        if self.command_mode_var.get() not in ("direct", "toggle"):
            self.command_mode_var.set("direct")

        self.config_data["interval_ms"] = interval_ms
        self.config_data["red_pixel_percent"] = red_pixel_percent
        self.config_data["valorant_color_tolerance"] = color_tolerance
        self.config_data["red_difference"] = color_tolerance
        self.config_data["stable_reads"] = stable_reads
        self.config_data["require_valorant_foreground"] = bool(self.require_valorant_var.get())
        self.config_data["command_mode"] = self.command_mode_var.get()
        self.sync_audio_settings("valorant")
        save_config(self.config_data)
        self.refresh_labels()

    def sync_lol_settings(self):
        try:
            interval_ms = int(float(self.lol_interval_var.get()))
            bright_pixel_percent = float(self.lol_bright_percent_var.get())
            bright_min_value = int(float(self.lol_bright_min_var.get()))
            min_digit_height = int(float(self.lol_digit_height_var.get()))
            min_digit_area = int(float(self.lol_digit_area_var.get()))
            min_digit_components = int(float(self.lol_digit_components_var.get()))
            stable_reads = int(float(self.lol_stable_var.get()))
        except ValueError:
            raise ValueError("Intervall, Hell %, Hell min, Ziffer-Werte und Stabil muessen Zahlen sein.")

        if interval_ms < 100:
            raise ValueError("Intervall muss mindestens 100 ms sein.")
        if bright_pixel_percent < 0 or bright_pixel_percent > 100:
            raise ValueError("Hell % muss zwischen 0 und 100 liegen.")
        if bright_min_value < 0 or bright_min_value > 255:
            raise ValueError("Hell min muss zwischen 0 und 255 liegen.")
        if min_digit_height < 1:
            raise ValueError("Ziffer Hoehe muss mindestens 1 sein.")
        if min_digit_area < 1:
            raise ValueError("Ziffer Flaeche muss mindestens 1 sein.")
        if min_digit_components < 1:
            raise ValueError("Komponenten muss mindestens 1 sein.")
        if stable_reads < 1:
            raise ValueError("Stabil muss mindestens 1 sein.")
        if self.lol_command_mode_var.get() not in ("direct", "toggle"):
            self.lol_command_mode_var.set("direct")

        self.config_data["lol_interval_ms"] = interval_ms
        self.config_data["lol_bright_pixel_percent"] = bright_pixel_percent
        self.config_data["lol_bright_min_value"] = bright_min_value
        self.config_data["lol_min_digit_height"] = min_digit_height
        self.config_data["lol_min_digit_area"] = min_digit_area
        self.config_data["lol_min_digit_components"] = min_digit_components
        self.config_data["lol_stable_reads"] = stable_reads
        self.config_data["require_lol_foreground"] = bool(self.require_lol_var.get())
        self.config_data["lol_command_mode"] = self.lol_command_mode_var.get()
        self.sync_audio_settings("lol")
        save_config(self.config_data)
        self.refresh_labels()

    def monitor_is_running(self):
        return self.monitor_thread and self.monitor_thread.is_alive()

    def active_monitor_name(self):
        if self.active_monitor == "lol":
            return "LoL"
        if self.active_monitor == "valorant":
            return "Valorant"
        return "ein anderes Monitoring"

    def start_valorant_monitoring(self):
        if self.monitor_is_running():
            self.show_info("Laeuft schon", f"{self.active_monitor_name()} laeuft bereits. Stoppe es zuerst.")
            return
        if not self.config_data.get("region"):
            self.show_warning("Fehlt", "Waehle zuerst einen Valorant-Bereich.")
            return
        try:
            self.sync_valorant_settings()
        except Exception as exc:
            self.show_error("Optionen pruefen", str(exc))
            return

        self.start_monitor_thread("valorant", self.monitor_loop_valorant)

    def start_lol_monitoring(self):
        if self.monitor_is_running():
            self.show_info("Laeuft schon", f"{self.active_monitor_name()} laeuft bereits. Stoppe es zuerst.")
            return
        if not self.config_data.get("lol_region"):
            self.show_warning("Fehlt", "Waehle zuerst einen LoL-Bereich.")
            return
        try:
            self.sync_lol_settings()
        except Exception as exc:
            self.show_error("Optionen pruefen", str(exc))
            return

        self.start_monitor_thread("lol", self.monitor_loop_lol)

    def start_monitor_thread(self, game, target):
        self.stop_event.clear()
        self.active_monitor = game
        self.monitor_thread = threading.Thread(target=target, daemon=True)
        self.monitor_thread.start()
        self.set_game_status(
            game,
            monitor="laeuft",
            log="Monitoring gestartet. Das Fenster wird minimiert; du kannst es ueber die Taskleiste wieder oeffnen.",
        )
        self.after(1200, self.iconify)

    def stop_monitoring(self, game=None):
        if not self.active_monitor:
            self.set_game_status(game or "valorant", log="Kein Monitoring aktiv.")
            return

        active = self.active_monitor
        self.stop_event.set()
        self.set_game_status(active, monitor="stoppt...", log="Monitoring wird gestoppt.")

    def set_game_status(self, game, monitor=None, detected=None, log=None):
        if game == "lol":
            monitor_var = self.lol_monitor_var
            detected_var = self.lol_detected_var
            log_var = self.lol_log_var
        else:
            monitor_var = self.monitor_var
            detected_var = self.detected_var
            log_var = self.log_var

        if monitor is not None:
            monitor_var.set(monitor)
        if detected is not None:
            detected_var.set(detected)
        if log:
            log_var.set(log)

    def monitor_loop_valorant(self):
        region = dict(self.config_data["region"])
        interval = self.config_data["interval_ms"] / 1000.0
        red_pixel_percent = float(self.config_data["red_pixel_percent"])
        color_tolerance = int(self.config_data.get("valorant_color_tolerance", VALORANT_COLOR_TOLERANCE))
        target_rgb = get_valorant_target_rgb(self.config_data)
        stable_reads = int(self.config_data["stable_reads"])
        require_valorant = bool(self.config_data["require_valorant_foreground"])
        command_mode = self.config_data.get("command_mode", "direct")
        audio_settings = self.saved_audio_settings("valorant")

        candidate = None
        candidate_count = 0
        last_action_state = None

        while not self.stop_event.is_set():
            try:
                if require_valorant and not is_valorant_foreground():
                    self.events.put(("status", "valorant", "wartet auf Valorant", "-", "Valorant ist nicht im Vordergrund."))
                    candidate = None
                    candidate_count = 0
                    time.sleep(interval)
                    continue

                raw = capture_region(region["left"], region["top"], region["width"], region["height"])
                state, percent, red_pixels, total = detect_state_from_red(
                    raw,
                    region["width"],
                    region["height"],
                    red_pixel_percent,
                    color_tolerance,
                    target_rgb,
                )

                readable = {
                    "red": "tot (rot)",
                    "no_red": "nicht tot (kein Rot)",
                }[state]

                detail = f"{readable}  |  {format_rgb(target_rgb)} {percent:.2f}% ({red_pixels}/{total})"
                self.events.put(("status", "valorant", "laeuft", detail, ""))

                if candidate == state:
                    candidate_count += 1
                else:
                    candidate = state
                    candidate_count = 1

                if candidate_count >= stable_reads and state != last_action_state:
                    last_action_state = state
                    action_message = self.apply_state_action("valorant", state, command_mode, audio_settings)
                    self.events.put(("log", "valorant", action_message))

                time.sleep(interval)
            except Exception as exc:
                self.events.put(("status", "valorant", "Fehler", "-", str(exc)))
                time.sleep(max(interval, 1.0))

        self.events.put(("stopped", "valorant"))

    def monitor_loop_lol(self):
        region = dict(self.config_data["lol_region"])
        interval = self.config_data["lol_interval_ms"] / 1000.0
        bright_pixel_percent = float(self.config_data["lol_bright_pixel_percent"])
        bright_min_value = int(self.config_data["lol_bright_min_value"])
        min_digit_height = int(self.config_data["lol_min_digit_height"])
        min_digit_area = int(self.config_data["lol_min_digit_area"])
        min_digit_components = int(self.config_data["lol_min_digit_components"])
        stable_reads = int(self.config_data["lol_stable_reads"])
        require_lol = bool(self.config_data["require_lol_foreground"])
        command_mode = self.config_data.get("lol_command_mode", "direct")
        audio_settings = self.saved_audio_settings("lol")

        candidate = None
        candidate_count = 0
        last_action_state = None

        while not self.stop_event.is_set():
            try:
                if require_lol and not is_lol_foreground():
                    self.events.put(("status", "lol", "wartet auf LoL", "-", "League of Legends ist nicht im Vordergrund."))
                    candidate = None
                    candidate_count = 0
                    time.sleep(interval)
                    continue

                raw = capture_region(region["left"], region["top"], region["width"], region["height"])
                state, percent, bright_pixels, total, components = detect_state_from_number(
                    raw,
                    region["width"],
                    region["height"],
                    bright_pixel_percent,
                    bright_min_value,
                    min_digit_height,
                    min_digit_area,
                    min_digit_components,
                )

                readable = {
                    "number": "tot (Zahl)",
                    "no_number": "nicht tot (keine Zahl)",
                }[state]

                detail = f"{readable}  |  Hell {percent:.2f}% ({bright_pixels}/{total}), Formen {components}"
                self.events.put(("status", "lol", "laeuft", detail, ""))

                if candidate == state:
                    candidate_count += 1
                else:
                    candidate = state
                    candidate_count = 1

                if candidate_count >= stable_reads and state != last_action_state:
                    last_action_state = state
                    action_message = self.apply_state_action("lol", state, command_mode, audio_settings)
                    self.events.put(("log", "lol", action_message))

                time.sleep(interval)
            except Exception as exc:
                self.events.put(("status", "lol", "Fehler", "-", str(exc)))
                time.sleep(max(interval, 1.0))

        self.events.put(("stopped", "lol"))

    def drain_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "status":
                    self.set_game_status(event[1], monitor=event[2], detected=event[3], log=event[4])
                elif event[0] == "log":
                    self.set_game_status(event[1], log=event[2])
                elif event[0] == "stopped":
                    self.set_game_status(event[1], monitor="gestoppt", detected="-", log="Monitoring gestoppt.")
                    if self.active_monitor == event[1]:
                        self.active_monitor = None
                elif event[0] == "update_check":
                    self.apply_update_check_result(event[1], event[2])
                elif event[0] == "update_install":
                    self.apply_update_install_result(event[1], event[2])
        except queue.Empty:
            pass
        self.after(200, self.drain_events)

    def on_close(self):
        self.stop_event.set()
        self.destroy()


if __name__ == "__main__":
    set_dpi_awareness()
    mutex_handle, is_running = create_single_instance_mutex()
    if is_running:
        sys.exit(0)
    app = App()
    try:
        app.mainloop()
    finally:
        if mutex_handle:
            kernel32.CloseHandle(mutex_handle)
