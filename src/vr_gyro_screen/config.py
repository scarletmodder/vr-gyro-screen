"""Configuration: built-in defaults, an optional TOML file and command line overrides.

A profile sets the options that trade smoothness of the screen for processor and
graphics card time. Anything set explicitly in the file or on the command line wins over
the profile.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .mapping import Mapping

APP_NAME = "vr-gyro-screen"
BACKENDS = ("auto", "gpu", "direct", "dxcam")
BACKGROUNDS = ("auto", "passthrough", "black")
HANDS = ("left", "right")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Profile:
    """The switches that cost or save machine time."""

    mipmaps: bool
    max_fps: int  # 0 = follow the headset; otherwise new images are taken at most this often


PROFILES: dict[str, Profile] = {
    # The default: every new image the monitor produces, so the screen is not held below what the game
    # and the headset can show; a little more processor time.
    "smooth": Profile(mipmaps=False, max_fps=0),
    # Lightest: new images at most 60 times per second, which leaves the most for the game.
    "performance": Profile(mipmaps=False, max_fps=60),
    # Mipmaps are in no profile: measured on a headset session, building them for every image cost the
    # graphics card bursts longer than a frame, felt as stutters in the game. `capture.mipmaps` turns them on.
}


@dataclass(frozen=True)
class ScreenConfig:
    monitor: str = "auto"
    distance_m: float = 2.0
    width_m: float = 2.6
    background: str = "auto"


@dataclass(frozen=True)
class CaptureConfig:
    backend: str = "auto"
    mipmaps: bool = False  # the default profile, "smooth"
    max_fps: int = 0


DISTANCE_RANGE_M = (0.8, 6.0)
WIDTH_RANGE_M = (0.3, 20.0)


@dataclass(frozen=True)
class GyroConfig:
    hand: str = "right"
    scale: float = 1.0
    deadzone_dps: float = 1.5
    keepalive: bool = True


@dataclass(frozen=True)
class Config:
    profile: str = "smooth"
    screen: ScreenConfig = field(default_factory=ScreenConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    gyro: GyroConfig = field(default_factory=GyroConfig)
    mapping: Mapping = field(default_factory=Mapping)


def data_dir() -> Path:
    """Where the app keeps its own files (configuration, saved screen position)."""
    return Path(os.environ.get("APPDATA") or Path.home()) / APP_NAME


def default_config_path() -> Path:
    return data_dir() / "config.toml"


def _table(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a table")
    return value


def _known(table: dict[str, Any], name: str, allowed: tuple[str, ...]) -> None:
    extra = sorted(set(table) - set(allowed))
    if extra:
        raise ConfigError(f"[{name}] has unknown keys: {', '.join(extra)}")


def _number(table: dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    value = table.get(key.rpartition(".")[2], default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigError(f"{key} must be a number")
    if not low <= value <= high:
        raise ConfigError(f"{key} must be between {low} and {high}")
    return float(value)


def _whole(value: float, key: str) -> int:
    if value != int(value):
        raise ConfigError(f"{key} must be a whole number")
    return int(value)


def _choice(table: dict[str, Any], key: str, default: str, allowed: tuple[str, ...]) -> str:
    value = table.get(key.rpartition(".")[2], default)
    if value not in allowed:
        raise ConfigError(f"{key} must be one of: {', '.join(allowed)}")
    return str(value)


def _flag(table: dict[str, Any], key: str, default: bool) -> bool:
    value = table.get(key.rpartition(".")[2], default)
    if not isinstance(value, bool):
        raise ConfigError(f"{key} must be true or false")
    return value


def _button_table(value: Any, name: str) -> dict[str, str]:
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value.values()):
        raise ConfigError(f"[{name}] must map controller inputs to gamepad button names")
    return {str(source): str(target).upper() for source, target in value.items()}


def _optional_name(table: dict[str, Any], key: str, default: str | None, upper: bool) -> str | None:
    """A name, or "none" (any case) or an empty string to turn the feature off."""
    value = table.get(key.rpartition(".")[2], default)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"{key} must be text")
    if value.strip().lower() in ("", "none"):
        return None
    return value.upper() if upper else value


def _mapping(data: dict[str, Any]) -> Mapping:
    base = Mapping()
    combo = _table(data, "combo")
    triggers = _table(data, "triggers")
    recenter = _table(data, "recenter")
    _known(combo, "combo", ("key", "solo", "solo_delay_s", "with", "dpad", "screen_adjust"))
    _known(triggers, "triggers", ("left", "right"))
    _known(recenter, "recenter", ("hold_s",))
    mapping = Mapping(
        buttons=_button_table(data["buttons"], "buttons") if "buttons" in data else base.buttons,
        trigger_left=str(triggers.get("left", base.trigger_left)),
        trigger_right=str(triggers.get("right", base.trigger_right)),
        combo_key=_optional_name(combo, "combo.key", base.combo_key, upper=False),
        combo_solo=_optional_name(combo, "combo.solo", base.combo_solo, upper=True),
        combo_solo_delay_s=_number(combo, "combo.solo_delay_s", base.combo_solo_delay_s, 0.0, 5.0),
        combo_with=_button_table(combo["with"], "combo.with") if "with" in combo else base.combo_with,
        combo_dpad=_flag(combo, "combo.dpad", base.combo_dpad),
        combo_screen_adjust=_flag(combo, "combo.screen_adjust", base.combo_screen_adjust),
        recenter_hold_s=_number(recenter, "recenter.hold_s", base.recenter_hold_s, 0.2, 10.0),
    )
    problems = mapping.problems()
    if problems:
        raise ConfigError("; ".join(problems))
    return mapping


def parse_config(data: dict[str, Any]) -> Config:
    """Validate a parsed TOML document and fill in defaults and the profile."""
    _known(data, "top level", ("profile", "screen", "capture", "gyro", "buttons", "triggers", "combo", "recenter"))
    profile_name = _choice(data, "profile", "smooth", tuple(PROFILES))
    profile = PROFILES[profile_name]
    screen = _table(data, "screen")
    capture = _table(data, "capture")
    gyro = _table(data, "gyro")
    _known(screen, "screen", ("monitor", "distance_m", "width_m", "background"))
    _known(capture, "capture", ("backend", "mipmaps", "max_fps"))
    _known(gyro, "gyro", ("hand", "scale", "deadzone_dps", "keepalive"))
    monitor = screen.get("monitor", "auto")
    if isinstance(monitor, bool) or not isinstance(monitor, str | int):
        raise ConfigError("screen.monitor must be text or a number")
    return Config(
        profile=profile_name,
        screen=ScreenConfig(
            monitor=str(monitor),
            distance_m=_number(screen, "screen.distance_m", 2.0, *DISTANCE_RANGE_M),
            width_m=_number(screen, "screen.width_m", 2.6, *WIDTH_RANGE_M),
            background=_choice(screen, "screen.background", "auto", BACKGROUNDS),
        ),
        capture=CaptureConfig(
            backend=_choice(capture, "capture.backend", "auto", BACKENDS),
            mipmaps=_flag(capture, "capture.mipmaps", profile.mipmaps),
            max_fps=_whole(_number(capture, "capture.max_fps", profile.max_fps, 0, 1000), "capture.max_fps"),
        ),
        gyro=GyroConfig(
            hand=_choice(gyro, "gyro.hand", "right", HANDS),
            scale=_number(gyro, "gyro.scale", 1.0, 0.0, 20.0),
            deadzone_dps=_number(gyro, "gyro.deadzone_dps", 1.5, 0.0, 90.0),
            keepalive=_flag(gyro, "gyro.keepalive", True),
        ),
        mapping=_mapping(data),
    )


def load_config(path: Path | None = None) -> Config:
    """Read the configuration file. A missing default file means built-in defaults."""
    explicit = path is not None
    target = path if path is not None else default_config_path()
    if not target.is_file():
        if explicit:
            raise ConfigError(f"configuration file not found: {target}")
        return Config()
    try:
        with target.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{target} is not valid TOML: {error}") from error
    return parse_config(data)


def with_profile(config: Config, name: str) -> Config:
    """Apply a profile chosen on the command line over an already loaded configuration."""
    if name not in PROFILES:
        raise ConfigError(f"profile must be one of: {', '.join(PROFILES)}")
    profile = PROFILES[name]
    capture = replace(config.capture, mipmaps=profile.mipmaps, max_fps=profile.max_fps)
    return replace(config, profile=name, capture=capture)
