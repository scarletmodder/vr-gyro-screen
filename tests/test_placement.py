"""Where the screen floats, and what happens with a damaged saved file."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from vr_gyro_screen.placement import MAX_DISTANCE_M, MAX_SCREEN_PITCH, MIN_DISTANCE_M, ScreenPlacement
from vr_gyro_screen.quaternion import from_axis_angle

LEVEL_HEAD = (from_axis_angle((0.0, 1.0, 0.0), 0.0), (0.0, 1.6, 0.0))


def saved(tmp_path: Path, content: str) -> Path:
    file = tmp_path / "screen.json"
    file.write_text(content, encoding="utf-8")
    return file


def test_screen_appears_straight_ahead_at_the_configured_distance() -> None:
    placement = ScreenPlacement(2.0, None)
    assert placement.pose() is None
    placement.place(LEVEL_HEAD, use_head_pitch=False)
    pose = placement.pose()
    assert pose is not None
    assert pose[1] == pytest.approx((0.0, 1.6, -2.0), abs=1e-9)


def test_position_is_saved_and_read_back(tmp_path: Path) -> None:
    file = tmp_path / "screen.json"
    first = ScreenPlacement(2.0, file)
    first.place(LEVEL_HEAD, use_head_pitch=False)
    first.adjust(0.25, 1.0)
    first.save_if_changed()
    again = ScreenPlacement(2.0, file)
    assert (again.pitch, again.distance) == pytest.approx((0.25, 3.0))


def test_explicit_distance_replaces_the_saved_one_but_keeps_the_height(tmp_path: Path) -> None:
    file = saved(tmp_path, json.dumps({"pitch": 0.3, "distance": 4.0}))
    placement = ScreenPlacement(1.5, file, keep_saved_distance=False)
    assert (placement.pitch, placement.distance) == pytest.approx((0.3, 1.5))


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[1, 2]",
        '{"pitch": null, "distance": "x"}',
        '{"pitch": NaN, "distance": Infinity}',
        '{"pitch": true, "distance": false}',
    ],
)
def test_damaged_saved_file_falls_back_to_the_configuration(tmp_path: Path, content: str) -> None:
    placement = ScreenPlacement(2.0, saved(tmp_path, content))
    assert (placement.pitch, placement.distance) == (0.0, 2.0)


def test_saved_values_out_of_range_are_brought_back_in(tmp_path: Path) -> None:
    placement = ScreenPlacement(2.0, saved(tmp_path, '{"pitch": 9, "distance": 0}'))
    assert (placement.pitch, placement.distance) == (MAX_SCREEN_PITCH, MIN_DISTANCE_M)
    placement.place(LEVEL_HEAD, use_head_pitch=False)
    placement.adjust(0.0, 100.0)
    assert placement.distance == MAX_DISTANCE_M
    pose = placement.pose()
    assert pose is not None and all(math.isfinite(value) for value in pose[1])
