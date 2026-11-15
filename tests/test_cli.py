"""Command line parsing and low level layouts; nothing here touches the headset or the gamepad driver."""

from __future__ import annotations

import ctypes
import math
from pathlib import Path

import pytest

from vr_gyro_screen import cli
from vr_gyro_screen.capture import dxgi
from vr_gyro_screen.quaternion import from_axis_angle, heading_and_pitch, multiply, rotate


def test_options_without_a_command_mean_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "missing.toml"
    assert cli.main(["--config", str(missing)]) == cli.EXIT_USAGE
    assert "not found" in capsys.readouterr().err


def test_command_line_overrides_the_file(tmp_path: Path) -> None:
    file = tmp_path / "c.toml"
    file.write_text('[screen]\nmonitor = "2"\nwidth_m = 3.0\n[capture]\nbackend = "direct"\n', encoding="utf-8")
    args = cli._parser().parse_args(
        ["run", "--config", str(file), "--profile", "performance", "--monitor", "tv", "--backend", "gpu"]
    )
    config = cli._run_config(args)
    assert (config.screen.monitor, config.screen.width_m) == ("tv", 3.0)
    assert (config.capture.backend, config.capture.mipmaps, config.capture.max_fps) == ("gpu", False, 60)


def test_structures_match_the_windows_layouts() -> None:
    assert ctypes.sizeof(dxgi.GUID) == 16
    assert ctypes.sizeof(dxgi._FrameInfo) == 48
    assert ctypes.sizeof(dxgi._Texture2DDesc) == 44
    assert ctypes.sizeof(dxgi._OutduplDesc) == 36


def test_rotation_about_the_vertical_turns_forward_to_the_left() -> None:
    quarter_left = from_axis_angle((0.0, 1.0, 0.0), math.pi / 2)
    assert rotate(quarter_left, (0.0, 0.0, -1.0)) == pytest.approx((-1.0, 0.0, 0.0), abs=1e-9)


def test_heading_and_pitch_ignore_roll() -> None:
    turn = from_axis_angle((0.0, 1.0, 0.0), math.radians(40))
    tilt = from_axis_angle((1.0, 0.0, 0.0), math.radians(-15))
    roll = from_axis_angle((0.0, 0.0, -1.0), math.radians(70))
    heading, pitch = heading_and_pitch(multiply(multiply(turn, tilt), roll))
    assert math.degrees(heading) == pytest.approx(40)
    assert math.degrees(pitch) == pytest.approx(-15)


@pytest.mark.parametrize(
    "options",
    [["--distance", "0"], ["--distance", "-1"], ["--distance", "nan"], ["--width", "0"], ["--width", "-3"]],
)
def test_screen_options_obey_the_same_limits_as_the_file(
    options: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert cli.main(options) == cli.EXIT_USAGE
    assert "must be between" in capsys.readouterr().err


def test_screen_and_background_options_reach_the_configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    args = cli._parser().parse_args(["run", "--distance", "1.5", "--width", "4", "--background", "black"])
    screen = cli._run_config(args).screen
    assert (screen.distance_m, screen.width_m, screen.background) == (1.5, 4.0, "black")


def test_bench_refuses_a_rate_of_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["bench", "--rate", "0"]) == cli.EXIT_USAGE
    assert "greater than zero" in capsys.readouterr().err
