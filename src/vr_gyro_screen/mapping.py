"""From headset controller state to gamepad buttons, sticks and the app's own shortcuts.

Default rule: each controller button becomes the gamepad button at the same position on a
standard gamepad with lettered buttons (A at the bottom, B on the right, X on the left, Y at
the top, grips as bumpers, triggers as triggers). With lettered button prompts turned on in a
game, the letter on screen is the letter printed on the controller.

A pair of headset controllers has fewer buttons than a gamepad, so one button can be set as
a combination key:

  combo + left stick   directional pad
  combo + other button the button listed in "combo.with"
  combo + right stick  moves the screen inside the headset (never reaches the game)
  combo alone          its own button (a short tap, or held after a short delay)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .quaternion import Quat, Vec3

PAD_BUTTONS = frozenset(
    {
        "CROSS",
        "CIRCLE",
        "SQUARE",
        "TRIANGLE",
        "SHOULDER_LEFT",
        "SHOULDER_RIGHT",
        "THUMB_LEFT",
        "THUMB_RIGHT",
        "OPTIONS",
        "SHARE",
        "PS",
        "TOUCHPAD",
    }
)
DIGITAL_INPUTS = ("a", "b", "x", "y", "menu", "left_stick_click", "right_stick_click")
ANALOG_INPUTS = ("left_trigger", "right_trigger", "left_squeeze", "right_squeeze")
INPUTS = frozenset(DIGITAL_INPUTS + ANALOG_INPUTS)

PRESS_THRESHOLD = 0.5  # an analog input counts as a button press above this
TRIGGER_CLICK = 0.3  # the gamepad's digital trigger bit turns on above this
DPAD_THRESHOLD = 0.6
SCREEN_ADJUST_THRESHOLD = 0.2
TAP_SECONDS = 0.08


@dataclass
class ControllerState:
    """One reading of both headset controllers and the head."""

    digital: dict[str, bool] = field(default_factory=dict)
    analog: dict[str, float] = field(default_factory=dict)
    left_stick: tuple[float, float] = (0.0, 0.0)
    right_stick: tuple[float, float] = (0.0, 0.0)
    left_aim: Quat | None = None
    right_aim: Quat | None = None
    head: tuple[Quat, Vec3] | None = None

    def pressed(self, name: str) -> bool:
        if name in self.digital:
            return self.digital[name]
        return self.analog.get(name, 0.0) > PRESS_THRESHOLD


@dataclass(frozen=True)
class Mapping:
    buttons: dict[str, str] = field(
        default_factory=lambda: {
            "a": "CROSS",
            "b": "CIRCLE",
            "x": "SQUARE",
            "left_squeeze": "SHOULDER_LEFT",
            "right_squeeze": "SHOULDER_RIGHT",
            "left_stick_click": "THUMB_LEFT",
            "right_stick_click": "THUMB_RIGHT",
            "menu": "OPTIONS",
        }
    )
    trigger_left: str = "left_trigger"
    trigger_right: str = "right_trigger"
    combo_key: str | None = "y"
    combo_solo: str | None = "TRIANGLE"
    combo_solo_delay_s: float = 0.25
    combo_with: dict[str, str] = field(default_factory=lambda: {"x": "SHARE"})
    combo_dpad: bool = True
    combo_screen_adjust: bool = True
    recenter_hold_s: float = 1.0

    def problems(self) -> list[str]:
        """Human readable list of what is wrong with this mapping; empty when it is fine."""
        found: list[str] = []
        for group, table in (("buttons", self.buttons), ("combo.with", self.combo_with)):
            for source, target in table.items():
                if source not in INPUTS:
                    found.append(f'{group}: "{source}" is not a controller input')
                if target not in PAD_BUTTONS:
                    found.append(f'{group}: "{target}" is not a gamepad button')
        for name, value in (("triggers.left", self.trigger_left), ("triggers.right", self.trigger_right)):
            if value not in ANALOG_INPUTS:
                found.append(f'{name}: "{value}" is not an analog controller input')
        if self.combo_key is not None and self.combo_key not in INPUTS:
            found.append(f'combo.key: "{self.combo_key}" is not a controller input')
        for group, table in (("buttons", self.buttons), ("combo.with", self.combo_with)):
            if self.combo_key is not None and self.combo_key in table:
                found.append(f'combo.key: "{self.combo_key}" is also used in [{group}]; remove it there')
        if self.combo_solo is not None and self.combo_solo not in PAD_BUTTONS:
            found.append(f'combo.solo: "{self.combo_solo}" is not a gamepad button')
        if self.combo_solo_delay_s < 0:
            found.append("combo.solo_delay_s must not be negative")
        if self.recenter_hold_s <= 0:
            found.append("recenter.hold_s must be greater than zero")
        return found


@dataclass
class PadFrame:
    """What the virtual gamepad should report, plus requests for the app itself."""

    buttons: set[str] = field(default_factory=set)
    dpad: str | None = None  # "N", "E", "S", "W"
    left_stick: tuple[float, float] = (0.0, 0.0)
    right_stick: tuple[float, float] = (0.0, 0.0)
    left_trigger: float = 0.0
    right_trigger: float = 0.0
    screen_adjust: tuple[float, float] = (0.0, 0.0)  # (up or down, near or far)
    recenter: bool = False


def _dpad_direction(x: float, y: float) -> str:
    angle = math.degrees(math.atan2(y, x)) % 360
    if angle < 45 or angle >= 315:
        return "E"
    if angle < 135:
        return "N"
    if angle < 225:
        return "W"
    return "S"


class ButtonMapper:
    """Applies a Mapping reading after reading; keeps the timing state of the shortcuts."""

    def __init__(self, mapping: Mapping) -> None:
        self.mapping = mapping
        self.reset()

    def reset(self) -> None:
        """Forget shortcuts in progress (the app lost the controllers for a while)."""
        self._combo_since: float | None = None
        self._combo_used = False
        self._tap_until = 0.0
        self._recenter_since: float | None = None
        self._recenter_fired = False

    def update(self, state: ControllerState, now: float) -> PadFrame:
        mapping = self.mapping
        frame = PadFrame(left_stick=state.left_stick, right_stick=state.right_stick)
        for source, target in mapping.buttons.items():
            if state.pressed(source):
                frame.buttons.add(target)

        key = mapping.combo_key
        if key is not None and state.pressed(key):
            if self._combo_since is None:
                self._combo_since, self._combo_used = now, False
            for source, target in mapping.combo_with.items():
                if state.pressed(source):
                    own = mapping.buttons.get(source)
                    # The button's own meaning is dropped, unless another pressed button
                    # (not part of a combination itself) asks for the same thing.
                    shared = any(
                        other != source and wanted == own and other not in mapping.combo_with and state.pressed(other)
                        for other, wanted in mapping.buttons.items()
                    )
                    if own is not None and not shared:
                        frame.buttons.discard(own)
                    frame.buttons.add(target)
                    self._combo_used = True
            if mapping.combo_dpad and math.hypot(*state.left_stick) > DPAD_THRESHOLD:
                frame.dpad = _dpad_direction(*state.left_stick)
                frame.left_stick = (0.0, 0.0)
                self._combo_used = True
            if mapping.combo_screen_adjust and math.hypot(*state.right_stick) > SCREEN_ADJUST_THRESHOLD:
                frame.screen_adjust = (state.right_stick[1], state.right_stick[0])
                frame.right_stick = (0.0, 0.0)
                self._combo_used = True
            held = now - self._combo_since
            if mapping.combo_solo and not self._combo_used and held >= mapping.combo_solo_delay_s:
                frame.buttons.add(mapping.combo_solo)
        else:
            if (
                self._combo_since is not None
                and not self._combo_used
                and now - self._combo_since < mapping.combo_solo_delay_s
            ):
                self._tap_until = now + TAP_SECONDS  # a quick press still reaches the game as a tap
            self._combo_since = None
        if mapping.combo_solo and self._tap_until > now:
            frame.buttons.add(mapping.combo_solo)

        frame.left_trigger = state.analog.get(mapping.trigger_left, 0.0)
        frame.right_trigger = state.analog.get(mapping.trigger_right, 0.0)

        both_clicks = state.pressed("left_stick_click") and state.pressed("right_stick_click")
        if not both_clicks:
            self._recenter_since, self._recenter_fired = None, False
        elif self._recenter_since is None:
            self._recenter_since = now
        elif not self._recenter_fired and now - self._recenter_since >= mapping.recenter_hold_s:
            self._recenter_fired = True
            frame.recenter = True
        return frame
