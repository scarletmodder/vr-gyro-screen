"""Send a window to the monitor shown in the headset and make it fill that monitor.

Most games go full screen on whatever monitor their window is on. This helper moves the
window first and then presses the game's full screen key until the window really covers
the monitor, because games often miss the key right after their window moves.
"""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

from .monitors import Monitor

FULLSCREEN_KEYS: dict[str, tuple[int, ...]] = {
    "f11": (0x7A,),
    "alt+enter": (0x12, 0x0D),
    "none": (),
}

_SW_RESTORE = 9
_SW_MAXIMIZE = 3
_SWP_NOZORDER = 0x4
_SWP_SHOWWINDOW = 0x40
_KEYEVENTF_KEYUP = 0x2
_VK_ALT = 0x12
_PER_MONITOR_AWARE_V2 = -4
_MONITOR_NEAREST = 2
_ATTEMPTS = 5

Rect = tuple[int, int, int, int]

_EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


class _MonitorInfo(ctypes.Structure):
    _fields_ = (
        ("size", wintypes.DWORD),
        ("monitor", wintypes.RECT),
        ("work", wintypes.RECT),
        ("flags", wintypes.DWORD),
    )


def _user32() -> ctypes.WinDLL:
    user32 = ctypes.WinDLL("user32")
    # Declared types keep window and monitor handles whole on 64 bit Windows.
    signatures: dict[str, tuple[object, tuple[object, ...]]] = {
        "SetProcessDpiAwarenessContext": (wintypes.BOOL, (ctypes.c_void_p,)),
        "EnumWindows": (wintypes.BOOL, (_EnumWindowsProc, wintypes.LPARAM)),
        "IsWindowVisible": (wintypes.BOOL, (wintypes.HWND,)),
        "GetWindowTextW": (ctypes.c_int, (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)),
        "GetWindowRect": (wintypes.BOOL, (wintypes.HWND, ctypes.POINTER(wintypes.RECT))),
        "GetForegroundWindow": (wintypes.HWND, ()),
        "SetForegroundWindow": (wintypes.BOOL, (wintypes.HWND,)),
        "ShowWindow": (wintypes.BOOL, (wintypes.HWND, ctypes.c_int)),
        "SetWindowPos": (
            wintypes.BOOL,
            (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT),
        ),
        "MonitorFromWindow": (wintypes.HMONITOR, (wintypes.HWND, wintypes.DWORD)),
        "GetMonitorInfoW": (wintypes.BOOL, (wintypes.HMONITOR, ctypes.POINTER(_MonitorInfo))),
        "keybd_event": (None, (wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t)),
    }
    for name, (restype, argtypes) in signatures.items():
        function = getattr(user32, name)
        function.restype = restype
        function.argtypes = argtypes
    # Real pixel coordinates, whatever scaling each monitor uses.
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(_PER_MONITOR_AWARE_V2))
    return user32


def _own_console() -> int:
    """The console window this command runs in, which must never be the window that is moved."""
    get_console = ctypes.WinDLL("kernel32").GetConsoleWindow
    get_console.restype = wintypes.HWND
    return int(get_console() or 0)


def find_window(user32: ctypes.WinDLL, title_part: str) -> int | None:
    """First visible top level window whose title contains the text (case ignored).

    The classic console that runs this command is skipped: its title often shows the
    command line, which contains the very text being searched for. Newer terminal programs
    own their window themselves and cannot be told apart here.
    """
    wanted = title_part.lower()
    skip = _own_console()
    found: list[int] = []

    def visit(handle: int, _: int) -> bool:
        if handle != skip and user32.IsWindowVisible(handle):
            buffer = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(handle, buffer, 512)
            if wanted in buffer.value.lower():
                found.append(handle)
        return True

    user32.EnumWindows(_EnumWindowsProc(visit), 0)
    return found[0] if found else None


def _rect(user32: ctypes.WinDLL, handle: int) -> Rect:
    rect = wintypes.RECT()
    user32.GetWindowRect(handle, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def _press(user32: ctypes.WinDLL, keys: tuple[int, ...]) -> None:
    for key in keys:
        user32.keybd_event(key, 0, 0, 0)
    time.sleep(0.05)
    for key in reversed(keys):
        user32.keybd_event(key, 0, _KEYEVENTF_KEYUP, 0)


def _focus(user32: ctypes.WinDLL, handle: int) -> bool:
    """Bring the window forward. True when it really has the keyboard afterwards."""
    # Windows only lets a background program bring a window forward while a key is down.
    user32.keybd_event(_VK_ALT, 0, 0, 0)
    user32.SetForegroundWindow(handle)
    user32.keybd_event(_VK_ALT, 0, _KEYEVENTF_KEYUP, 0)
    time.sleep(0.3)
    return int(user32.GetForegroundWindow() or 0) == handle


def _press_in(user32: ctypes.WinDLL, handle: int, keys: tuple[int, ...]) -> bool:
    """Press the keys only if the window has the keyboard; otherwise they would go elsewhere."""
    if not _focus(user32, handle):
        return False
    _press(user32, keys)
    return True


def send_to_monitor(title_part: str, monitor: Monitor, fullscreen_key: str, wait_s: float) -> int:
    """Exit code 0 when the window covers the monitor, 1 otherwise.

    With no full screen key the window is only moved and maximized, which is reported as 0
    without measuring: a maximized window leaves the taskbar visible.
    """
    user32 = _user32()
    keys = FULLSCREEN_KEYS[fullscreen_key]
    target: Rect = (monitor.left, monitor.top, monitor.left + monitor.width, monitor.top + monitor.height)
    deadline = time.monotonic() + wait_s
    handle = find_window(user32, title_part)
    while handle is None and time.monotonic() < deadline:
        time.sleep(0.5)
        handle = find_window(user32, title_part)
    if handle is None:
        print(f'no visible window has "{title_part}" in its title', flush=True)
        return 1
    if _rect(user32, handle) == target:
        print("the window already fills the monitor", flush=True)
        return 0

    def place_windowed() -> None:
        user32.ShowWindow(handle, _SW_RESTORE)
        user32.SetWindowPos(
            handle,
            None,
            monitor.left + 100,
            monitor.top + 100,
            monitor.width // 2,
            monitor.height // 2,
            _SWP_NOZORDER | _SWP_SHOWWINDOW,
        )

    before = _rect(user32, handle)
    width, height = before[2] - before[0], before[3] - before[1]
    covers_other_monitor = (width, height) != (0, 0) and before != target and _looks_fullscreen(user32, handle)
    if covers_other_monitor and keys:
        for _ in range(_ATTEMPTS):  # leave full screen on the wrong monitor first
            _press_in(user32, handle, keys)
            time.sleep(1.5)
            if _rect(user32, handle) != before:
                break
    place_windowed()
    if not keys:
        user32.ShowWindow(handle, _SW_MAXIMIZE)
        print("window moved and maximized (no full screen key was given)", flush=True)
        return 0
    refused = 0
    for _ in range(_ATTEMPTS):
        time.sleep(1.5)
        if not _press_in(user32, handle, keys):
            refused += 1
            continue
        time.sleep(1.5)
        if _rect(user32, handle) == target:
            print("the window now fills the monitor", flush=True)
            return 0
        if _looks_fullscreen(user32, handle):
            _press_in(user32, handle, keys)  # full screen on the wrong monitor: back to a window, try again
            time.sleep(1.0)
            place_windowed()
    if refused == _ATTEMPTS:
        print("Windows did not let the window come to the front, so no key was pressed; click it once", flush=True)
    print(f"the window did not fill the monitor; it is at {_rect(user32, handle)}", flush=True)
    return 1


def _looks_fullscreen(user32: ctypes.WinDLL, handle: int) -> bool:
    """True when the window covers the whole monitor it is on."""
    info = _MonitorInfo()
    info.size = ctypes.sizeof(info)
    monitor = user32.MonitorFromWindow(handle, _MONITOR_NEAREST)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return False
    area = info.monitor
    return _rect(user32, handle) == (area.left, area.top, area.right, area.bottom)
