"""Turns the pose of a hand controller into the gyroscope and accelerometer of a gamepad.

Games that support motion aiming usually fuse both sensors: the gyroscope moves the aim and
the accelerometer (gravity) slowly corrects drift. If the two disagree, the game pulls the
aim back or ignores part of the movement. Two simpler models were tried and failed that way:

- gravity fixed as "pad lying flat": the aim crept back whenever the hand was raised;
- a virtual orientation integrated from the gyroscope sent: it drifted and killed sideways aim.

The model here builds a "player frame" from the real heading and pitch of the hand, with
roll forced to zero. The gyroscope is the time derivative of the very angles that produce
the gravity vector, so both sensors always tell the same story.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .quaternion import FORWARD, Quat, rotate

GYRO_UNITS_PER_DPS = 16.0  # DualShock 4 raw gyroscope units per degree per second
ACCEL_UNITS_PER_G = 8192.0  # DualShock 4 raw accelerometer units per g
RAW_LIMIT = 32767

MAX_PITCH = math.radians(80)  # beyond this the heading of a nearly vertical hand is noise
MIN_HORIZONTAL = 0.17  # length of the forward vector on the floor plane below which heading is ignored
SPIKE = math.radians(1500)  # faster than this is a tracking jump, not a hand
SMOOTHING = 0.5  # blend with the previous sample to hide pose prediction jitter


@dataclass(frozen=True)
class MotionSample:
    """Raw values ready for a DualShock 4 report."""

    gyro: tuple[int, int, int]
    accel: tuple[int, int, int]


def _raw(value: float) -> int:
    return max(-RAW_LIMIT, min(RAW_LIMIT, int(value)))


class MotionModel:
    def __init__(self, scale: float = 1.0, deadzone_dps: float = 1.5, keepalive: bool = True) -> None:
        self.scale = scale
        self.deadzone = math.radians(deadzone_dps)
        self.keepalive = keepalive
        self._gyro = (0.0, 0.0, 0.0)
        self._gravity = (0.0, 1.0, 0.0)
        self._previous: tuple[float, float, float] | None = None
        self._jitter = 1

    def reset(self) -> None:
        """Forget the last pose, so the next one does not produce a jump."""
        self._previous = None
        self._gyro = (0.0, 0.0, 0.0)

    def update(self, orientation: Quat | None, time_s: float) -> MotionSample:
        """Feed the hand orientation at a given time; None when tracking is lost."""
        if orientation is None:
            self.reset()
            return self._sample()
        forward = rotate(orientation, FORWARD)
        pitch = max(-MAX_PITCH, min(MAX_PITCH, math.asin(max(-1.0, min(1.0, forward[1])))))
        heading = math.atan2(-forward[0], -forward[2])
        previous = self._previous
        if previous is not None and time_s == previous[2]:
            # Same time stamp: no rate can be measured. Keeping the earlier pose means the
            # movement is not lost, it is measured on the next reading.
            return self._sample()
        if previous is not None and time_s < previous[2]:
            # The clock went back: start measuring again from this pose.
            self._previous = (pitch, heading, time_s)
            return self._sample()
        if previous is not None:
            dt = time_s - previous[2]
            pitch_rate = (pitch - previous[0]) / dt
            turn = (heading - previous[1] + math.pi) % (2 * math.pi) - math.pi
            heading_rate = turn / dt if math.hypot(forward[0], forward[2]) > MIN_HORIZONTAL else 0.0
            if abs(pitch_rate) > SPIKE or abs(heading_rate) > SPIKE:
                pitch_rate = heading_rate = 0.0
            rates = (pitch_rate, heading_rate * math.cos(pitch), -heading_rate * math.sin(pitch))
            self._gyro = (
                SMOOTHING * self._gyro[0] + (1 - SMOOTHING) * rates[0],
                SMOOTHING * self._gyro[1] + (1 - SMOOTHING) * rates[1],
                SMOOTHING * self._gyro[2] + (1 - SMOOTHING) * rates[2],
            )
        self._previous = (pitch, heading, time_s)
        self._gravity = (0.0, math.cos(pitch), -math.sin(pitch))
        return self._sample()

    def rest(self) -> MotionSample:
        """A report for when nothing should move (headset menu open, app not focused)."""
        self.reset()
        return self._sample()

    def _sample(self) -> MotionSample:
        gyro = self._gyro
        # Dead zone: prediction jitter of a still hand must not push the aim.
        if math.sqrt(sum(rate * rate for rate in gyro)) < self.deadzone:
            gyro = (0.0, 0.0, 0.0)
        factor = math.degrees(1.0) * GYRO_UNITS_PER_DPS * self.scale
        x, y, z = (_raw(rate * factor) for rate in gyro)
        if self.keepalive:
            # Some games restart their motion sensor when the gyroscope repeats the exact same
            # value for a while. One raw unit (1/16 degree per second), alternating sign, has
            # zero mean and keeps the sensor alive without moving the aim.
            self._jitter = -self._jitter
            z = _raw(z + self._jitter)
        gravity = self._gravity
        accel = (
            _raw(gravity[0] * ACCEL_UNITS_PER_G),
            _raw(gravity[1] * ACCEL_UNITS_PER_G),
            _raw(gravity[2] * ACCEL_UNITS_PER_G),
        )
        return MotionSample((x, y, z), accel)
