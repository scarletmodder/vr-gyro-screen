"""The settings window's parts that need no headset: saving, requirements, texts, engine command."""

from __future__ import annotations

import queue
import string
import sys
import time
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

from vr_gyro_screen import engine, gui_text
from vr_gyro_screen.config import (
    PROFILES,
    CaptureConfig,
    Config,
    GyroConfig,
    ScreenConfig,
    load_config,
    parse_config,
)
from vr_gyro_screen.mapping import ANALOG_INPUTS, DIGITAL_INPUTS, Mapping
from vr_gyro_screen.monitors import Monitor
from vr_gyro_screen.prerequisites import OPENXR_KEY, VIGEMBUS_KEY, check_all
from vr_gyro_screen.settings_file import dump_toml, save_config, to_document

CHANGED = Config(
    profile="performance",
    screen=ScreenConfig(monitor='Odd "name" \\ here', distance_m=3.5, width_m=4.0, background="black"),
    capture=CaptureConfig(backend="direct", mipmaps=True, max_fps=72),
    gyro=GyroConfig(hand="left", scale=1.75, deadzone_dps=0.0, keepalive=False),
    mapping=Mapping(
        buttons={"a": "CIRCLE", "right_trigger": "PS"},
        trigger_left="left_squeeze",
        trigger_right="right_squeeze",
        combo_key=None,
        combo_solo=None,
        combo_solo_delay_s=0.5,
        combo_with={"b": "TOUCHPAD"},
        combo_dpad=False,
        combo_screen_adjust=False,
        recenter_hold_s=2.0,
    ),
)


def _round_trip(config: Config) -> Config:
    return parse_config(tomllib.loads(dump_toml(to_document(config))))


@pytest.mark.parametrize("config", [Config(), CHANGED, *(replace(Config(), profile=name) for name in PROFILES)])
def test_saved_document_loads_back_as_the_same_configuration(config: Config) -> None:
    profile = PROFILES[config.profile]
    if config is not CHANGED:
        config = replace(config, capture=CaptureConfig(mipmaps=profile.mipmaps, max_fps=profile.max_fps))
    assert _round_trip(config) == config


def test_defaults_write_an_empty_document() -> None:
    assert to_document(Config()) == {}
    assert dump_toml({}) == ""


def test_empty_mapping_tables_survive() -> None:
    config = replace(Config(), mapping=replace(Config().mapping, buttons={}, combo_with={}))
    assert _round_trip(config) == config


def test_control_characters_are_refused() -> None:
    with pytest.raises(ValueError, match="control characters"):
        dump_toml({"screen": {"monitor": "a\nb"}})


def test_save_keeps_the_file_written_by_hand(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "config.toml"
    backup = target.parent / "config.toml.bak"
    by_hand = '# my notes\nprofile = "smooth"\n'
    target.parent.mkdir()
    target.write_text(by_hand, encoding="utf-8")
    save_config(Config(), target)
    assert backup.read_text(encoding="utf-8") == by_hand
    save_config(CHANGED, target)  # replacing a file the window wrote must not replace the hand-written copy
    assert load_config(target) == CHANGED
    assert backup.read_text(encoding="utf-8") == by_hand
    assert not (target.parent / "config.toml.new").exists()


def test_monitor_position_is_not_matched_as_a_name() -> None:
    pytest.importorskip("PySide6")
    from vr_gyro_screen.gui import monitor_options

    monitors = [_monitor(0, "Main"), _monitor(1, "Virtual One")]
    options = monitor_options(monitors, "1", gui_text.EN)
    assert options[2] == ("1", monitors[1].label) and len(options) == 3
    assert monitor_options(monitors, "7", gui_text.EN)[-1][0] == "7"


def test_engine_command_carries_the_distance(tmp_path: Path) -> None:
    command = engine.engine_command(tmp_path / "stop", 2.5)
    assert command[-2:] == ["--distance", "2.5"]


def _deaf_engine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> engine.Engine:
    """An engine whose process never looks at the stop file, like one waiting for the headset."""
    sleeper = [sys.executable, "-c", "import time; print('up', flush=True); time.sleep(60)"]
    monkeypatch.setattr(engine, "engine_command", lambda stop_file, distance_m=None: sleeper)
    return engine.Engine(tmp_path / "stop")


def _wait_for_end(lines: queue.Queue[str | None]) -> None:
    while lines.get(timeout=10) is not None:
        pass


def test_stop_ends_only_the_engine_that_was_asked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runner = _deaf_engine(monkeypatch, tmp_path)
    runner.start()
    first = runner._process
    assert first is not None
    runner.request_stop(patience_s=0.5)
    first.kill()  # it ends before the patience runs out, and a new one starts right away
    _wait_for_end(runner.lines)
    runner.start()
    try:
        assert not runner.stop_requested
        time.sleep(1.0)  # the patience of the first request is over by now
        assert runner.running
    finally:
        runner.request_stop(patience_s=0.2)
        _wait_for_end(runner.lines)
    assert runner.stop_requested and not runner.running
    assert not (tmp_path / "stop").exists()


def _registry(values: dict[tuple[str, str], str]):  # type: ignore[no-untyped-def]
    return lambda key, value: values.get((key, value))


def test_requirements_all_present() -> None:
    read = _registry(
        {
            (VIGEMBUS_KEY, "ImagePath"): "driver.sys",
            (OPENXR_KEY, "ActiveRuntime"): r"C:\Somewhere\OpenXR\virtualdesktop-openxr.json",
        }
    )
    assert [check.ok for check in check_all(read)] == [True, True, True]


def test_requirements_other_runtime_and_no_driver() -> None:
    checks = check_all(_registry({(OPENXR_KEY, "ActiveRuntime"): r"C:\Other\other_runtime.json"}))
    assert [(check.key, check.ok) for check in checks] == [
        ("gamepad_driver", False),
        ("openxr_runtime", True),
        ("virtual_desktop_runtime", False),
    ]
    assert checks[2].detail == "other_runtime"
    assert all(check.url.startswith("https://") for check in checks)


def test_requirements_nothing_installed() -> None:
    assert [check.ok for check in check_all(_registry({}))] == [False, False, False]


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_both_languages_have_the_same_texts() -> None:
    assert set(gui_text.EN) == set(gui_text.PT)
    for key, english in gui_text.EN.items():
        assert _placeholders(english) == _placeholders(gui_text.PT[key]), key


def test_texts_cover_every_option() -> None:
    for name in DIGITAL_INPUTS + ANALOG_INPUTS:
        assert f"input_{name}" in gui_text.EN
    for name in PROFILES:
        assert f"profile_{name}" in gui_text.EN
    from vr_gyro_screen.mapping import PAD_BUTTONS

    for name in PAD_BUTTONS:
        assert f"pad_{name}" in gui_text.EN


def test_every_help_opens_with_a_short_sentence() -> None:
    for texts in (gui_text.EN, gui_text.PT):
        for key, value in texts.items():
            if key.startswith("help_"):
                assert len(gui_text.summary(value)) <= 130, key
                assert gui_text.details(value), key


def test_language_can_be_forced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(gui_text.LANGUAGE_VARIABLE, "pt")
    assert gui_text.pick_language() is gui_text.PT
    monkeypatch.setenv(gui_text.LANGUAGE_VARIABLE, "en")
    assert gui_text.pick_language() is gui_text.EN


def test_engine_command_from_source_and_installed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stop = tmp_path / "stop"
    command = engine.engine_command(stop)
    assert command[:4] == [sys.executable, "-u", "-m", "vr_gyro_screen"]
    assert command[-4:] == ["run", "--quiet", "--stop-file", str(stop)]
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "vr-gyro-screen.exe"))
    assert engine.engine_command(stop)[0] == str(tmp_path / engine.CONSOLE_PROGRAM)


def _monitor(index: int, description: str) -> Monitor:
    return Monitor(index, rf"\\.\DISPLAY{index + 1}", description, 0, 0, 1920, 1080, 60, index == 0)


def test_monitor_options() -> None:
    pytest.importorskip("PySide6")
    from vr_gyro_screen.gui import monitor_options

    text = gui_text.EN
    monitors = [_monitor(0, "Same"), _monitor(1, "Same"), _monitor(2, "Virtual One")]
    values = [value for value, _ in monitor_options(monitors, "auto", text)]
    assert values == ["auto", monitors[0].device_name, monitors[1].device_name, "Virtual One"]
    values = [value for value, _ in monitor_options(monitors, "virtual", text)]
    assert values[3] == "virtual" and len(values) == 4
    gone = monitor_options(monitors, "Unplugged", text)
    assert gone[-1][0] == "Unplugged" and "Unplugged" in gone[-1][1]


def test_window_reads_back_what_it_shows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from PySide6.QtWidgets import QApplication

    from vr_gyro_screen import gui

    monkeypatch.setattr(gui, "list_monitors", lambda: [_monitor(0, "Main"), _monitor(1, "Virtual One")])
    app = QApplication.instance() or QApplication([])
    window = gui.SettingsWindow(tmp_path / "config.toml")
    try:
        assert window.read() == Config()
        window.show_config(CHANGED)
        assert window.read() == CHANGED
        assert window.save()
        assert load_config(tmp_path / "config.toml") == CHANGED
        gui._select(window.profile, "smooth")
        assert window.read().capture == CaptureConfig(backend="direct", mipmaps=False, max_fps=0)
        assert "vr-gyro-screen" in window.diagnostics()
        assert not window.engine.running
        # the two column explanations of a controller card share one place: opening one closes the other
        from PySide6.QtWidgets import QToolButton

        window.menu.setCurrentRow(3)
        buttons_page = window.pages.currentWidget()
        assert buttons_page is not None
        alone, combo = buttons_page.findChildren(QToolButton)[:2]
        alone.setChecked(True)
        combo.setChecked(True)
        assert combo.isChecked() and not alone.isChecked()
        alone.setChecked(True)
        assert alone.isChecked() and not combo.isChecked()
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()
