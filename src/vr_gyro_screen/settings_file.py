"""Writes a configuration back to a TOML file.

The standard library reads TOML but does not write it. The configuration only uses text,
numbers, true or false and tables of those, so a small writer is enough. Only what differs
from the built-in defaults is written, so a saved file stays short and keeps following the
defaults of later versions.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .config import PROFILES, Config

Document = dict[str, Any]


def to_document(config: Config) -> Document:
    """The TOML document that loads back as this configuration."""
    base = Config()
    document: Document = {}
    if config.profile != base.profile:
        document["profile"] = config.profile

    screen = {
        key: getattr(config.screen, key)
        for key in ("monitor", "distance_m", "width_m", "background")
        if getattr(config.screen, key) != getattr(base.screen, key)
    }
    profile = PROFILES[config.profile]
    capture: Document = {}
    if config.capture.backend != base.capture.backend:
        capture["backend"] = config.capture.backend
    if config.capture.mipmaps != profile.mipmaps:
        capture["mipmaps"] = config.capture.mipmaps
    if config.capture.max_fps != profile.max_fps:
        capture["max_fps"] = config.capture.max_fps
    gyro = {
        key: getattr(config.gyro, key)
        for key in ("hand", "scale", "deadzone_dps", "keepalive")
        if getattr(config.gyro, key) != getattr(base.gyro, key)
    }

    mapping, default = config.mapping, base.mapping
    triggers: Document = {}
    if mapping.trigger_left != default.trigger_left:
        triggers["left"] = mapping.trigger_left
    if mapping.trigger_right != default.trigger_right:
        triggers["right"] = mapping.trigger_right
    combo: Document = {}
    if mapping.combo_key != default.combo_key:
        combo["key"] = mapping.combo_key or "none"
    if mapping.combo_solo != default.combo_solo:
        combo["solo"] = mapping.combo_solo or "none"
    if mapping.combo_solo_delay_s != default.combo_solo_delay_s:
        combo["solo_delay_s"] = mapping.combo_solo_delay_s
    if mapping.combo_dpad != default.combo_dpad:
        combo["dpad"] = mapping.combo_dpad
    if mapping.combo_screen_adjust != default.combo_screen_adjust:
        combo["screen_adjust"] = mapping.combo_screen_adjust
    if mapping.combo_with != default.combo_with:
        combo["with"] = dict(mapping.combo_with)

    for name, table in (("screen", screen), ("capture", capture), ("gyro", gyro)):
        if table:
            document[name] = table
    if mapping.buttons != default.buttons:
        document["buttons"] = dict(mapping.buttons)
    if triggers:
        document["triggers"] = triggers
    if combo:
        document["combo"] = combo
    if mapping.recenter_hold_s != default.recenter_hold_s:
        document["recenter"] = {"hold_s": mapping.recenter_hold_s}
    return document


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    if any(ord(character) < 32 or ord(character) == 127 for character in text):
        raise ValueError("text values cannot contain control characters")
    return f'"{text}"'


def _key(name: str) -> str:
    plain = name.replace("_", "").replace("-", "")
    return name if plain.isascii() and plain.isalnum() else _value(name)


def dump_toml(document: Document) -> str:
    """Text of a document made of values and tables of values (tables may nest)."""
    lines: list[str] = []

    def table(path: str, content: Document) -> None:
        values = {key: value for key, value in content.items() if not isinstance(value, dict)}
        tables = {key: value for key, value in content.items() if isinstance(value, dict)}
        if path and (values or not tables):
            if lines:
                lines.append("")
            lines.append(f"[{path}]")
        lines.extend(f"{_key(key)} = {_value(value)}" for key, value in values.items())
        for key, value in tables.items():
            table(f"{path}.{_key(key)}" if path else _key(key), value)

    table("", document)
    return "\n".join(lines) + "\n" if lines else ""


HEADER = "# Written by the vr-gyro-screen settings window. Only what differs from the defaults is listed.\n"


def _written_by_hand(path: Path) -> bool:
    try:
        return not path.read_text(encoding="utf-8").startswith(HEADER)
    except (OSError, ValueError):
        return True


def save_config(config: Config, path: Path) -> None:
    """Write the configuration. A file written by hand (comments and all) is kept as `<name>.bak`;
    a file this function wrote before is just replaced, so the hand-written copy is not lost."""
    text = HEADER + dump_toml(to_document(config))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and _written_by_hand(path):
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)
