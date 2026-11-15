"""Monitors as Windows lists them, and the choice of which one goes to the headset."""

from __future__ import annotations

import ctypes
from collections.abc import Sequence
from ctypes import wintypes
from dataclasses import dataclass

# Name fragment of the monitor Virtual Desktop creates when "virtual monitors" are in use.
VIRTUAL_MONITOR_HINT = "virtual desktop"

_ATTACHED_TO_DESKTOP = 0x1
_PRIMARY_DEVICE = 0x4
_ENUM_CURRENT_SETTINGS = -1


@dataclass(frozen=True)
class Monitor:
    index: int
    device_name: str
    description: str
    left: int
    top: int
    width: int
    height: int
    refresh_hz: int
    primary: bool

    @property
    def label(self) -> str:
        return f"{self.device_name} ({self.description}) {self.width}x{self.height} @ {self.refresh_hz} Hz"


class MonitorNotFoundError(LookupError):
    pass


class _DisplayDevice(ctypes.Structure):
    _fields_ = (
        ("cb", wintypes.DWORD),
        ("device_name", ctypes.c_wchar * 32),
        ("device_string", ctypes.c_wchar * 128),
        ("state_flags", wintypes.DWORD),
        ("device_id", ctypes.c_wchar * 128),
        ("device_key", ctypes.c_wchar * 128),
    )


class _DevMode(ctypes.Structure):
    _fields_ = (
        ("device_name", ctypes.c_wchar * 32),
        ("spec_version", wintypes.WORD),
        ("driver_version", wintypes.WORD),
        ("size", wintypes.WORD),
        ("driver_extra", wintypes.WORD),
        ("fields", wintypes.DWORD),
        ("position_x", ctypes.c_long),
        ("position_y", ctypes.c_long),
        ("display_orientation", wintypes.DWORD),
        ("display_fixed_output", wintypes.DWORD),
        ("color", ctypes.c_short),
        ("duplex", ctypes.c_short),
        ("y_resolution", ctypes.c_short),
        ("tt_option", ctypes.c_short),
        ("collate", ctypes.c_short),
        ("form_name", ctypes.c_wchar * 32),
        ("log_pixels", wintypes.WORD),
        ("bits_per_pel", wintypes.DWORD),
        ("pels_width", wintypes.DWORD),
        ("pels_height", wintypes.DWORD),
        ("display_flags", wintypes.DWORD),
        ("display_frequency", wintypes.DWORD),
        ("reserved", ctypes.c_byte * 32),  # colour management and panning fields, unused here
    )


def list_monitors() -> list[Monitor]:
    """Every monitor attached to the desktop, in Windows order."""
    user32 = ctypes.WinDLL("user32")
    monitors: list[Monitor] = []
    adapter_index = 0
    while True:
        adapter = _DisplayDevice()
        adapter.cb = ctypes.sizeof(adapter)
        if not user32.EnumDisplayDevicesW(None, adapter_index, ctypes.byref(adapter), 0):
            break
        adapter_index += 1
        if not adapter.state_flags & _ATTACHED_TO_DESKTOP:
            continue
        mode = _DevMode()
        mode.size = ctypes.sizeof(mode)
        if not user32.EnumDisplaySettingsW(adapter.device_name, _ENUM_CURRENT_SETTINGS, ctypes.byref(mode)):
            continue
        screen = _DisplayDevice()
        screen.cb = ctypes.sizeof(screen)
        has_screen = user32.EnumDisplayDevicesW(adapter.device_name, 0, ctypes.byref(screen), 0)
        description = adapter.device_string
        if has_screen and screen.device_string:
            description = f"{adapter.device_string}, {screen.device_string}"
        monitors.append(
            Monitor(
                index=len(monitors),
                device_name=adapter.device_name,
                description=description,
                left=int(mode.position_x),
                top=int(mode.position_y),
                width=int(mode.pels_width),
                height=int(mode.pels_height),
                refresh_hz=int(mode.display_frequency),
                primary=bool(adapter.state_flags & _PRIMARY_DEVICE),
            )
        )
    return monitors


def choose_monitor(monitors: Sequence[Monitor], selector: str = "auto") -> Monitor:
    """Pick the monitor to show in the headset.

    "auto" prefers the Virtual Desktop virtual monitor, then any monitor that is not the
    primary one, then the primary. A number is a position in the list; any other text is
    matched against the device name and description.
    """
    if not monitors:
        raise MonitorNotFoundError("Windows reports no monitor attached to the desktop")
    wanted = selector.strip().lower()
    if wanted in ("", "auto"):
        for monitor in monitors:
            if VIRTUAL_MONITOR_HINT in monitor.description.lower():
                return monitor
        for monitor in monitors:
            if not monitor.primary:
                return monitor
        return monitors[0]
    if wanted.isdigit():
        position = int(wanted)
        if position >= len(monitors):
            raise MonitorNotFoundError(f"there is no monitor {position}; {len(monitors)} found")
        return monitors[position]
    for monitor in monitors:
        if wanted in monitor.device_name.lower() or wanted in monitor.description.lower():
            return monitor
    names = "; ".join(monitor.label for monitor in monitors)
    raise MonitorNotFoundError(f'no monitor matches "{selector}"; found: {names}')


def same_monitor(monitors: list[Monitor], previous: Monitor) -> Monitor | None:
    """The monitor that was in use before, if it is among these.

    A virtual monitor comes back under a new Windows name, so the description decides.
    When several monitors share that description (two identical screens), only the one
    with the same name or the same place on the desktop is accepted.
    """
    alike = [monitor for monitor in monitors if monitor.description == previous.description]
    if len(alike) <= 1:
        return alike[0] if alike else None
    for monitor in alike:
        if monitor.device_name == previous.device_name:
            return monitor
    for monitor in alike:
        if (monitor.left, monitor.top) == (previous.left, previous.top):
            return monitor
    return None
