"""The motion model: gyroscope and gravity must always agree with the real hand."""

from __future__ import annotations

import math

import pytest

from vr_gyro_screen.motion import ACCEL_UNITS_PER_G, GYRO_UNITS_PER_DPS, MotionModel, MotionSample
from vr_gyro_screen.quaternion import Quat, from_axis_angle, multiply

RATE = 90  # samples per second, like a headset


def hand(heading_deg: float, pitch_deg: float, roll_deg: float = 0.0) -> Quat:
    turn = from_axis_angle((0.0, 1.0, 0.0), math.radians(heading_deg))
    tilt = from_axis_angle((1.0, 0.0, 0.0), math.radians(pitch_deg))
    roll = from_axis_angle((0.0, 0.0, -1.0), math.radians(roll_deg))
    return multiply(multiply(turn, tilt), roll)


def settle(
    model: MotionModel, heading_dps: float, pitch_dps: float, pitch0: float = 0.0, seconds: float = 0.5
) -> MotionSample:
    sample = model.update(hand(0.0, pitch0), 0.0)
    for step in range(1, int(seconds * RATE) + 1):
        t = step / RATE
        sample = model.update(hand(heading_dps * t, pitch0 + pitch_dps * t), t)
    return sample


def test_still_hand_reports_no_rotation_and_gravity_straight_down() -> None:
    sample = settle(MotionModel(keepalive=False), 0.0, 0.0)
    assert sample.gyro == (0, 0, 0)
    assert sample.accel == (0, int(ACCEL_UNITS_PER_G), 0)


def test_turning_sideways_is_yaw_only() -> None:
    sample = settle(MotionModel(keepalive=False), 90.0, 0.0)
    assert sample.gyro[1] == pytest.approx(90 * GYRO_UNITS_PER_DPS, rel=0.02)
    assert abs(sample.gyro[0]) <= 2
    assert abs(sample.gyro[2]) <= 2


def test_raising_the_hand_is_pitch_only() -> None:
    sample = settle(MotionModel(keepalive=False), 0.0, 45.0)
    assert sample.gyro[0] == pytest.approx(45 * GYRO_UNITS_PER_DPS, rel=0.02)
    assert abs(sample.gyro[1]) <= 2


def test_gravity_follows_the_real_pitch_so_the_aim_is_not_pulled_back() -> None:
    sample = settle(MotionModel(keepalive=False), 0.0, 0.0, pitch0=30.0)
    assert sample.gyro == (0, 0, 0)
    assert sample.accel[0] == 0
    assert sample.accel[1] == pytest.approx(math.cos(math.radians(30)) * ACCEL_UNITS_PER_G, abs=2)
    assert sample.accel[2] == pytest.approx(-math.sin(math.radians(30)) * ACCEL_UNITS_PER_G, abs=2)


def test_turning_with_the_hand_raised_splits_between_two_axes() -> None:
    sample = settle(MotionModel(keepalive=False), 90.0, 0.0, pitch0=30.0)
    expected = 90 * GYRO_UNITS_PER_DPS
    assert sample.gyro[1] == pytest.approx(expected * math.cos(math.radians(30)), rel=0.02)
    assert sample.gyro[2] == pytest.approx(-expected * math.sin(math.radians(30)), rel=0.02)


def test_rolling_the_wrist_moves_nothing() -> None:
    model = MotionModel(keepalive=False)
    sample = model.update(hand(0.0, 0.0, 0.0), 0.0)
    for step in range(1, 30):
        sample = model.update(hand(0.0, 0.0, step * 2.0), step / RATE)
    assert sample.gyro == (0, 0, 0)
    assert sample.accel == (0, int(ACCEL_UNITS_PER_G), 0)


def test_slow_drift_is_inside_the_dead_zone() -> None:
    assert settle(MotionModel(deadzone_dps=1.5, keepalive=False), 1.0, 0.0).gyro == (0, 0, 0)
    assert settle(MotionModel(deadzone_dps=0.0, keepalive=False), 1.0, 0.0).gyro[1] > 0


def test_tracking_jump_is_discarded() -> None:
    model = MotionModel(keepalive=False)
    model.update(hand(0.0, 0.0), 0.0)
    assert model.update(hand(120.0, 0.0), 1 / RATE).gyro == (0, 0, 0)


def test_crossing_the_back_does_not_spin_the_other_way() -> None:
    model = MotionModel(keepalive=False)
    model.update(hand(179.0, 0.0), 0.0)
    sample = model.update(hand(181.0, 0.0), 1 / RATE)
    assert sample.gyro[1] > 0


def test_lost_tracking_resets_and_keeps_the_last_gravity() -> None:
    model = MotionModel(keepalive=False)
    settle(model, 90.0, 0.0, pitch0=20.0)
    lost = model.update(None, 1.0)
    assert lost.gyro == (0, 0, 0)
    assert lost.accel[2] < 0
    assert model.update(hand(50.0, 20.0), 1.0 + 1 / RATE).gyro == (0, 0, 0)


def test_keepalive_never_repeats_the_same_gyroscope_value() -> None:
    model = MotionModel(keepalive=True)
    values = [model.rest().gyro[2] for _ in range(6)]
    assert values == [-1, 1, -1, 1, -1, 1]


def test_scale_multiplies_the_gyroscope_only() -> None:
    single = settle(MotionModel(scale=1.0, keepalive=False), 60.0, 0.0)
    double = settle(MotionModel(scale=2.0, keepalive=False), 60.0, 0.0)
    assert double.gyro[1] == pytest.approx(2 * single.gyro[1], abs=2)
    assert double.accel == single.accel


def test_repeated_time_stamp_does_not_lose_the_movement() -> None:
    model = MotionModel(keepalive=False)
    model.update(hand(0.0, 0.0), 0.0)
    model.update(hand(1.0, 0.0), 0.0)  # same time stamp: nothing can be measured yet
    late = model.update(hand(1.0, 0.0), 1 / RATE)
    reference = MotionModel(keepalive=False)
    reference.update(hand(0.0, 0.0), 0.0)
    assert late == reference.update(hand(1.0, 0.0), 1 / RATE)
    assert late.gyro[1] != 0


def test_clock_going_back_starts_measuring_again() -> None:
    model = MotionModel(keepalive=False)
    model.update(hand(0.0, 0.0), 10.0)
    model.update(hand(0.0, 0.0), 1.0)  # the clock restarted
    moving = model.update(hand(1.0, 0.0), 1.0 + 1 / RATE)
    assert moving.gyro[1] != 0
