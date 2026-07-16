import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes


APP_NAME = "Gangcord"
APP_VERSION = "2.0.1"
APP_EXE_NAME = "Gangcord.exe"
WATCHER_EXE_NAME = "GangcordWatcher.exe"
APP_MUTEX_NAME = "Local\\Gangcord_Main_Instance"
WATCHER_MUTEX_NAME = "Local\\Gangcord_Watcher_Instance"
WATCHER_STOP_EVENT_NAME = "Local\\Gangcord_Watcher_Stop"
RUN_VALUE_NAME = "Gangcord Watcher"
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
EVENT_MODIFY_STATE = 0x0002
CREATE_NO_WINDOW = 0x08000000
WAIT_OBJECT_0 = 0x00000000

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
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.OpenEventW.restype = wintypes.HANDLE
kernel32.SetEvent.argtypes = [wintypes.HANDLE]
kernel32.SetEvent.restype = wintypes.BOOL
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
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


def watcher_is_running():
    handle = kernel32.OpenMutexW(SYNCHRONIZE, False, WATCHER_MUTEX_NAME)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return False


def signal_watcher_stop():
    handle = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, WATCHER_STOP_EVENT_NAME)
    if not handle:
        return
    try:
        kernel32.SetEvent(handle)
    finally:
        kernel32.CloseHandle(handle)


def wait_for_watcher_exit(timeout_seconds=6):
    deadline = time.monotonic() + timeout_seconds
    while watcher_is_running() and time.monotonic() < deadline:
        time.sleep(0.1)


def normalize_mode(value):
    text = str(value or "none").strip().lower()
    if text in ("valorant", "lol", "both"):
        return text
    return "none"


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        log(f"Settings could not be read: {exc}")
        return {}


def save_mode(mode):
    data = load_config()
    data["auto_launch_mode"] = normalize_mode(mode)
    ensure_directory(USER_DATA_DIR)
    temp_path = ""
    try:
        descriptor, temp_path = tempfile.mkstemp(prefix="config-", suffix=".tmp", dir=USER_DATA_DIR)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, CONFIG_PATH)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def load_mode():
    return normalize_mode(load_config().get("auto_launch_mode"))


def configure_windows_startup(mode):
    import winreg

    normalized_mode = normalize_mode(mode)
    save_mode(normalized_mode)
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if normalized_mode == "none":
            try:
                winreg.DeleteValue(key, RUN_VALUE_NAME)
            except FileNotFoundError:
                pass
            return
        watcher_path = os.path.join(APP_DIR, WATCHER_EXE_NAME)
        winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, f'"{watcher_path}"')


def launch_watcher_instance():
    if getattr(sys, "frozen", False):
        command = [sys.executable]
    else:
        command = [sys.executable, os.path.abspath(__file__)]
    subprocess.Popen(
        command,
        cwd=APP_DIR,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def running_process_names():
    names = set()
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        log("The process list could not be read.")
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
        log(f"Application not found: {app_path}")
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
        log("Gangcord was started.")
    except Exception as exc:
        log(f"Gangcord could not be started: {exc}")


def run_monitor():
    mutex_handle, already_running = create_single_instance_mutex()
    if already_running:
        return 0
    stop_event = kernel32.CreateEventW(None, True, False, WATCHER_STOP_EVENT_NAME)

    log(f"Watcher {APP_VERSION} started.")
    last_launch_state = False
    try:
        while True:
            mode = load_mode()
            if mode == "none":
                log("Automatic game detection is disabled; watcher is exiting.")
                return 0

            process_names = running_process_names()
            launch_now = should_launch(mode, process_names)
            if launch_now and not last_launch_state:
                launch_app()
            last_launch_state = launch_now
            if stop_event and kernel32.WaitForSingleObject(stop_event, 10000) == WAIT_OBJECT_0:
                log("Watcher stop signal received.")
                return 0
    finally:
        if stop_event:
            kernel32.CloseHandle(stop_event)
        if mutex_handle:
            kernel32.CloseHandle(mutex_handle)


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) == 2 and arguments[0] == "--configure":
        mode = normalize_mode(arguments[1])
        configure_windows_startup(mode)
        if mode == "none":
            signal_watcher_stop()
            wait_for_watcher_exit()
        else:
            launch_watcher_instance()
        return 0
    return run_monitor()


if __name__ == "__main__":
    raise SystemExit(main())
