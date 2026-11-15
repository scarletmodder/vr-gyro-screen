"""Small quaternion helpers. Quaternions are (x, y, z, w), the order OpenXR uses."""

from __future__ import annotations

import math

Quat = tuple[float, float, float, float]
Vec3 = tuple[float, float, float]

FORWARD: Vec3 = (0.0, 0.0, -1.0)


def multiply(a: Quat, b: Quat) -> Quat:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def conjugate(q: Quat) -> Quat:
    return (-q[0], -q[1], -q[2], q[3])


def rotate(q: Quat, v: Vec3) -> Vec3:
    x, y, z, _ = multiply(multiply(q, (v[0], v[1], v[2], 0.0)), conjugate(q))
    return (x, y, z)


def from_axis_angle(axis: Vec3, angle: float) -> Quat:
    s = math.sin(angle / 2)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(angle / 2))


def heading_and_pitch(q: Quat) -> tuple[float, float]:
    """Where an orientation points: heading (positive to the left) and pitch (positive up).

    Roll is ignored on purpose: tilting the head or the hand sideways must not move anything.
    """
    forward = rotate(q, FORWARD)
    heading = math.atan2(-forward[0], -forward[2])
    pitch = math.asin(max(-1.0, min(1.0, forward[1])))
    return heading, pitch
