import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes


APP_NAME = "Game Media Control"
APP_EXE_NAME = "Game Media Control.exe"
APP_MUTEX_NAME = "Local\\GameMediaControl_Main_Instance"
WATCHER_MUTEX_NAME = "Local\\GameMediaControl_Watcher_Instance"
CONFIG_FILE_NAME = "config.json"
LOG_FILE_NAME = "watcher.log"

VALORANT_PROCESSES = {
    "valorant-win64-shipping.exe",
    "riotclientservices.exe",
}
LOL_PROCESSES = {
    "leagueclient.exe",
    "leagueclientux.exe",
    "league of legends.exe",
}

ERROR_ALREADY_EXISTS = 183
TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
SYNCHRONIZE = 0x00100000
CREATE_NO_WINDOW = 0x08000000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.OpenMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_user_data_dir():
    base_dir = os.environ.get("LOCALAPPDATA")
    if not base_dir:
        base_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.abspath(os.path.join(base_dir, APP_NAME))


APP_DIR = get_app_dir()
USER_DATA_DIR = get_user_data_dir()
CONFIG_PATH = os.path.join(USER_DATA_DIR, CONFIG_FILE_NAME)
LOG_DIR = os.path.join(USER_DATA_DIR, "Logs")
LOG_PATH = os.path.join(LOG_DIR, LOG_FILE_NAME)


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)


def log(message):
    try:
        ensure_directory(LOG_DIR)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def create_single_instance_mutex():
    handle = kernel32.CreateMutexW(None, False, WATCHER_MUTEX_NAME)
    already_running = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
    return handle, already_running


def app_is_running():
    handle = kernel32.OpenMutexW(SYNCHRONIZE, False, APP_MUTEX_NAME)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return False


def normalize_mode(value):
    text = str(value or "none").strip().lower()
    if text in ("valorant", "lol", "both"):
        return text
    return "none"


def load_mode():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return normalize_mode(data.get("auto_launch_mode"))
    except FileNotFoundError:
        return "none"
    except Exception as exc:
        log(f"Config konnte nicht gelesen werden: {exc}")
    return "none"


def running_process_names():
    names = set()
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        log("Prozessliste konnte nicht gelesen werden.")
        return names

    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    try:
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return names
        while True:
            if entry.szExeFile:
                names.add(entry.szExeFile.lower())
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return names


def should_launch(mode, process_names):
    valorant_running = bool(process_names & VALORANT_PROCESSES)
    lol_running = bool(process_names & LOL_PROCESSES)
    if mode == "valorant":
        return valorant_running
    if mode == "lol":
        return lol_running
    if mode == "both":
        return valorant_running or lol_running
    return False


def launch_app():
    app_path = os.path.join(APP_DIR, APP_EXE_NAME)
    if not os.path.exists(app_path):
        log(f"App nicht gefunden: {app_path}")
        return
    if app_is_running():
        return
    try:
        subprocess.Popen(
            [app_path],
            cwd=APP_DIR,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        log("App wurde gestartet.")
    except Exception as exc:
        log(f"App konnte nicht gestartet werden: {exc}")


def main():
    mutex_handle, already_running = create_single_instance_mutex()
    if already_running:
        return 0

    log("Watcher gestartet.")
    last_launch_state = False
    try:
        while True:
            mode = load_mode()
            if mode == "none":
                last_launch_state = False
                time.sleep(20)
                continue

            process_names = running_process_names()
            launch_now = should_launch(mode, process_names)
            if launch_now and not last_launch_state:
                launch_app()
            last_launch_state = launch_now
            time.sleep(8)
    finally:
        if mutex_handle:
            kernel32.CloseHandle(mutex_handle)


if __name__ == "__main__":
    raise SystemExit(main())
