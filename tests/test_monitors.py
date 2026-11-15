"""Which monitor goes to the headset."""

from __future__ import annotations

import pytest

from vr_gyro_screen.monitors import Monitor, MonitorNotFoundError, choose_monitor, same_monitor


def monitor(index: int, description: str, primary: bool = False) -> Monitor:
    return Monitor(index, f"DISPLAY{index + 1}", description, index * 1920, 0, 1920, 1080, 60, primary)


PHYSICAL = monitor(0, "Graphics Card, Generic Monitor", primary=True)
SECOND = monitor(1, "Graphics Card, Other Monitor")
VIRTUAL = monitor(2, "Virtual Desktop Monitor, Generic Monitor")


def test_auto_prefers_the_virtual_monitor() -> None:
    assert choose_monitor([PHYSICAL, SECOND, VIRTUAL]) is VIRTUAL


def test_auto_falls_back_to_a_secondary_monitor_then_to_the_primary() -> None:
    assert choose_monitor([PHYSICAL, SECOND]) is SECOND
    assert choose_monitor([PHYSICAL]) is PHYSICAL


def test_a_number_is_a_position_and_text_is_matched_by_name() -> None:
    monitors = [PHYSICAL, SECOND, VIRTUAL]
    assert choose_monitor(monitors, "1") is SECOND
    assert choose_monitor(monitors, "other") is SECOND
    assert choose_monitor(monitors, "display3") is VIRTUAL


def test_no_match_lists_what_exists() -> None:
    with pytest.raises(MonitorNotFoundError, match="DISPLAY1"):
        choose_monitor([PHYSICAL], "projector")
    with pytest.raises(MonitorNotFoundError):
        choose_monitor([PHYSICAL], "4")
    with pytest.raises(MonitorNotFoundError):
        choose_monitor([])


def test_after_a_loss_a_virtual_monitor_is_recognised_under_its_new_name() -> None:
    renamed = Monitor(5, "DISPLAY21", VIRTUAL.description, 0, 0, 2560, 1440, 90, False)
    assert same_monitor([PHYSICAL, SECOND, renamed], VIRTUAL) is renamed
    assert same_monitor([PHYSICAL, SECOND], VIRTUAL) is None


def test_after_a_loss_an_identical_twin_is_not_taken_for_the_lost_monitor() -> None:
    left = Monitor(0, "DISPLAY1", "Graphics Card, Twin", 0, 0, 1920, 1080, 60, True)
    right = Monitor(1, "DISPLAY2", "Graphics Card, Twin", 1920, 0, 1920, 1080, 60, False)
    assert same_monitor([left, right], right) is right
    moved = Monitor(1, "DISPLAY7", "Graphics Card, Twin", 1920, 0, 1920, 1080, 60, False)
    assert same_monitor([left, moved], right) is moved
    stranger = Monitor(1, "DISPLAY7", "Graphics Card, Twin", 3840, 0, 1920, 1080, 60, False)
    other = Monitor(2, "DISPLAY8", "Graphics Card, Twin", 5760, 0, 1920, 1080, 60, False)
    assert same_monitor([stranger, other], right) is None
