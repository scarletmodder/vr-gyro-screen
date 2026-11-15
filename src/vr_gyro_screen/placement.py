"""Where the screen floats in front of the person, and the file that remembers it."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .quaternion import Quat, Vec3, from_axis_angle, heading_and_pitch, multiply, rotate

MAX_SCREEN_PITCH = 1.2  # radians, up or down
MIN_DISTANCE_M, MAX_DISTANCE_M = 0.8, 6.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _saved_number(saved: dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    """A number from the saved file, or the default when it is missing or unusable."""
    value = saved.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        return default
    return _clamp(float(value), low, high)


class ScreenPlacement:
    """An arc around the point where the head was at the last recenter.

    The saved file wins over the configured distance, because it holds what the person last
    adjusted by hand; ``keep_saved_distance=False`` is for a distance given explicitly.
    """

    def __init__(self, distance_m: float, state_file: Path | None, keep_saved_distance: bool = True) -> None:
        self._state_file = state_file
        saved = self._load()
        configured = _clamp(distance_m, MIN_DISTANCE_M, MAX_DISTANCE_M)
        self.pitch = _saved_number(saved, "pitch", 0.0, -MAX_SCREEN_PITCH, MAX_SCREEN_PITCH)
        self.distance = configured
        if keep_saved_distance:
            self.distance = _saved_number(saved, "distance", configured, MIN_DISTANCE_M, MAX_DISTANCE_M)
        self._anchor: tuple[float, Vec3] | None = None
        self._dirty = False

    def _load(self) -> dict[str, Any]:
        if self._state_file is None:
            return {}
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self) -> None:
        self._dirty = False
        if self._state_file is None:
            return
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._state_file.with_suffix(".tmp")
            temporary.write_text(json.dumps({"pitch": self.pitch, "distance": self.distance}), encoding="utf-8")
            temporary.replace(self._state_file)
        except OSError as error:
            print(f"could not save the screen position: {error}", flush=True)

    def save_if_changed(self) -> None:
        if self._dirty:
            self.save()

    @property
    def placed(self) -> bool:
        return self._anchor is not None

    def place(self, head: tuple[Quat, Vec3], use_head_pitch: bool) -> None:
        """Put the screen where the head is facing. Keeps the saved height unless asked otherwise."""
        heading, pitch = heading_and_pitch(head[0])
        if use_head_pitch:
            self.pitch = _clamp(pitch, -MAX_SCREEN_PITCH, MAX_SCREEN_PITCH)
        self._anchor = (heading, head[1])
        self.save()

    def adjust(self, pitch_delta: float, distance_delta: float) -> None:
        if self._anchor is None:
            return
        self.pitch = _clamp(self.pitch + pitch_delta, -MAX_SCREEN_PITCH, MAX_SCREEN_PITCH)
        self.distance = _clamp(self.distance + distance_delta, MIN_DISTANCE_M, MAX_DISTANCE_M)
        self._dirty = True

    def pose(self) -> tuple[Quat, Vec3] | None:
        if self._anchor is None:
            return None
        heading, origin = self._anchor
        orientation = multiply(from_axis_angle((0.0, 1.0, 0.0), heading), from_axis_angle((1.0, 0.0, 0.0), self.pitch))
        offset = rotate(orientation, (0.0, 0.0, -self.distance))
        return orientation, (origin[0] + offset[0], origin[1] + offset[1], origin[2] + offset[2])
