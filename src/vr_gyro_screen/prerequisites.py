"""Checks that the programs this app depends on are present, and says where to get them.

Nothing is installed from here. Each missing item points to the site of whoever makes it.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

VIGEMBUS_URL = "https://github.com/nefarius/ViGEmBus/releases/latest"
VIRTUAL_DESKTOP_URL = "https://www.vrdesktop.net/"
OPENXR_KEY = r"SOFTWARE\Khronos\OpenXR\1"
VIGEMBUS_KEY = r"SYSTEM\CurrentControlSet\Services\ViGEmBus"

# Reads one text value under HKEY_LOCAL_MACHINE; None when the key or the value is missing.
RegistryReader = Callable[[str, str], str | None]


@dataclass(frozen=True)
class Check:
    key: str  # stable name, used by the window to pick the translated title
    ok: bool
    detail: str
    url: str


def _read_registry(key: str, value: str) -> str | None:
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as handle:
            data, _kind = winreg.QueryValueEx(handle, value)
    except OSError:
        return None
    return str(data)


def check_all(read: RegistryReader = _read_registry) -> list[Check]:
    """The gamepad driver and the headset runtime, in the order a person would fix them."""
    driver = read(VIGEMBUS_KEY, "ImagePath")
    runtime = read(OPENXR_KEY, "ActiveRuntime")
    runtime_name = Path(runtime).stem if runtime else ""
    from_virtual_desktop = "virtualdesktop" in runtime_name.lower().replace("-", "").replace("_", "")
    return [
        Check("gamepad_driver", driver is not None, "ViGEmBus" if driver else "", VIGEMBUS_URL),
        Check("openxr_runtime", runtime is not None, runtime_name, VIRTUAL_DESKTOP_URL),
        Check("virtual_desktop_runtime", from_virtual_desktop, runtime_name, VIRTUAL_DESKTOP_URL),
    ]
