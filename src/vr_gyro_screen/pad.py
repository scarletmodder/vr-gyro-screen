"""The virtual DualShock 4 (through the ViGEmBus driver) and how a frame is written to it."""

from __future__ import annotations

import time
from typing import Any

from .mapping import TRIGGER_CLICK, PadFrame
from .motion import MotionSample

_SPECIAL = {"PS": 0x01, "TOUCHPAD": 0x02}
_DPAD = {"N": "NORTH", "E": "EAST", "S": "SOUTH", "W": "WEST"}
_TIMESTAMP_HZ = 187500  # the DualShock 4 motion timestamp counts in units of 5.33 microseconds


def _stick(value: float) -> int:
    return max(0, min(255, round(128 + value * 127)))


class VirtualPad:
    def __init__(self) -> None:
        import vgamepad

        self._vg: Any = vgamepad
        self._pad: Any = vgamepad.VDS4Gamepad()

    def send(self, frame: PadFrame, motion: MotionSample) -> None:
        vg = self._vg
        buttons = 0
        special = 0
        for name in frame.buttons:
            if name in _SPECIAL:
                special |= _SPECIAL[name]
            else:
                buttons |= int(getattr(vg.DS4_BUTTONS, "DS4_BUTTON_" + name))
        if frame.left_trigger > TRIGGER_CLICK:
            buttons |= int(vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT)
        if frame.right_trigger > TRIGGER_CLICK:
            buttons |= int(vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT)
        direction = "NONE" if frame.dpad is None else _DPAD[frame.dpad]
        dpad = int(getattr(vg.DS4_DPAD_DIRECTIONS, "DS4_BUTTON_DPAD_" + direction))

        extended = self._pad.get_default_extended_report()
        report = extended.Report
        report.bThumbLX, report.bThumbLY = _stick(frame.left_stick[0]), _stick(-frame.left_stick[1])
        report.bThumbRX, report.bThumbRY = _stick(frame.right_stick[0]), _stick(-frame.right_stick[1])
        report.wButtons = (buttons & ~0xF) | dpad  # the low four bits hold the directional pad
        report.bSpecial = special
        report.bTriggerL = max(0, min(255, int(frame.left_trigger * 255)))
        report.bTriggerR = max(0, min(255, int(frame.right_trigger * 255)))
        report.wGyroX, report.wGyroY, report.wGyroZ = motion.gyro
        report.wAccelX, report.wAccelY, report.wAccelZ = motion.accel
        report.wTimestamp = int(time.perf_counter() * _TIMESTAMP_HZ) & 0xFFFF
        self._pad.update_extended_report(extended)
