"""Configuration file parsing, profiles and error messages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from vr_gyro_screen.config import PROFILES, Config, ConfigError, load_config, parse_config, with_profile


def test_defaults_are_the_smooth_profile() -> None:
    config = parse_config({})
    assert config == Config()
    assert config.profile == "smooth"
    assert (config.capture.mipmaps, config.capture.max_fps) == (False, 0)


def test_profile_sets_capture_options_and_explicit_values_win() -> None:
    assert parse_config({"profile": "performance"}).capture.mipmaps is False
    assert parse_config({"profile": "performance"}).capture.max_fps == 60
    mixed = parse_config({"profile": "performance", "capture": {"mipmaps": True}})
    assert (mixed.capture.mipmaps, mixed.capture.max_fps) == (True, 60)


def test_command_line_profile_replaces_capture_options() -> None:
    config = with_profile(parse_config({"capture": {"max_fps": 30}}), "smooth")
    assert config.profile == "smooth"
    assert config.capture.max_fps == PROFILES["smooth"].max_fps == 0


def test_no_profile_builds_mipmaps() -> None:
    # Measured on a headset session: mipmaps for every image stutter the game. They stay an explicit option.
    assert not any(profile.mipmaps for profile in PROFILES.values())
    assert parse_config({"capture": {"mipmaps": True}}).capture.mipmaps is True


def test_mapping_tables_are_read_and_button_names_are_case_insensitive() -> None:
    config = parse_config(
        {
            "buttons": {"a": "circle", "b": "cross"},
            "combo": {"key": "x", "solo": "square", "with": {"a": "ps"}, "dpad": False},
            "triggers": {"left": "left_squeeze", "right": "right_squeeze"},
            "recenter": {"hold_s": 2},
            "gyro": {"hand": "left", "scale": 1.5},
            "screen": {"monitor": 1},
        }
    )
    assert config.mapping.buttons == {"a": "CIRCLE", "b": "CROSS"}
    assert (config.mapping.combo_key, config.mapping.combo_solo) == ("x", "SQUARE")
    assert config.mapping.combo_with == {"a": "PS"}
    assert config.mapping.combo_dpad is False
    assert config.mapping.trigger_left == "left_squeeze"
    assert config.mapping.recenter_hold_s == 2.0
    assert (config.gyro.hand, config.gyro.scale) == ("left", 1.5)
    assert config.screen.monitor == "1"


def test_combo_key_can_be_turned_off() -> None:
    assert parse_config({"combo": {"key": "none"}}).mapping.combo_key is None


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        ({"profile": "ultra"}, "profile"),
        ({"speed": 1}, "unknown keys: speed"),
        ({"screen": {"distance_m": 50}}, "distance_m"),
        ({"screen": {"size": 3}}, "unknown keys: size"),
        ({"capture": {"backend": "magic"}}, "backend"),
        ({"capture": {"mipmaps": "yes"}}, "mipmaps"),
        ({"gyro": {"hand": "both"}}, "hand"),
        ({"buttons": {"a": "JUMP"}}, "JUMP"),
        ({"buttons": "a"}, "buttons"),
        ({"triggers": {"left": "a"}}, "triggers.left"),
        ({"screen": {"width_m": 0}}, "screen.width_m must be between"),
        ({"gyro": {"scale": "fast"}}, "gyro.scale must be a number"),
        ({"capture": {"max_fps": 59.7}}, "capture.max_fps must be a whole number"),
        ({"combo": {"key": "a"}}, "combo.key"),
        ({"recenter": {"hold_s": 0}}, "recenter.hold_s"),
    ],
)
def test_mistakes_are_named(data: dict[str, Any], fragment: str) -> None:
    with pytest.raises(ConfigError, match=fragment):
        parse_config(data)


def test_missing_default_file_means_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert load_config() == Config()


def test_explicit_file_must_exist_and_be_valid(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.toml")
    bad = tmp_path / "bad.toml"
    bad.write_text("profile = ", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid TOML"):
        load_config(bad)
    good = tmp_path / "good.toml"
    good.write_text('profile = "smooth"\n[gyro]\nscale = 2\n', encoding="utf-8")
    assert load_config(good).gyro.scale == 2.0


def test_the_example_file_in_the_repository_matches_the_defaults() -> None:
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    assert load_config(example) == Config()
