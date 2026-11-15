"""Buttons, the combination key and the recenter shortcut."""

from __future__ import annotations

from vr_gyro_screen.mapping import ButtonMapper, ControllerState, Mapping

Stick = tuple[float, float]
CENTER: Stick = (0.0, 0.0)


def state(*pressed: str, left: Stick = CENTER, right: Stick = CENTER, **analog: float) -> ControllerState:
    names = ("a", "b", "x", "y", "menu", "left_stick_click", "right_stick_click")
    levels = {"left_trigger": 0.0, "right_trigger": 0.0, "left_squeeze": 0.0, "right_squeeze": 0.0}
    levels.update(analog)
    return ControllerState(
        digital={name: name in pressed for name in names}, analog=levels, left_stick=left, right_stick=right
    )


def test_buttons_follow_the_letter_positions() -> None:
    frame = ButtonMapper(Mapping()).update(state("a", "b", "x", "menu", left_squeeze=1.0), 0.0)
    assert frame.buttons == {"CROSS", "CIRCLE", "SQUARE", "OPTIONS", "SHOULDER_LEFT"}
    assert frame.dpad is None


def test_triggers_and_sticks_pass_through() -> None:
    frame = ButtonMapper(Mapping()).update(state(left=(0.5, -0.5), right=(1.0, 0.0), right_trigger=0.7), 0.0)
    assert frame.left_stick == (0.5, -0.5)
    assert frame.right_stick == (1.0, 0.0)
    assert (frame.left_trigger, frame.right_trigger) == (0.0, 0.7)


def test_combo_with_left_stick_is_the_directional_pad() -> None:
    mapper = ButtonMapper(Mapping())
    for stick, direction in (((0.0, 1.0), "N"), ((1.0, 0.0), "E"), ((0.0, -1.0), "S"), ((-1.0, 0.0), "W")):
        frame = mapper.update(state("y", left=stick), 0.0)
        assert frame.dpad == direction
        assert frame.left_stick == (0.0, 0.0)
        assert "TRIANGLE" not in frame.buttons


def test_combo_with_another_button_replaces_it() -> None:
    frame = ButtonMapper(Mapping()).update(state("y", "x"), 0.0)
    assert frame.buttons == {"SHARE"}


def test_combo_with_right_stick_moves_the_screen_and_hides_the_stick_from_the_game() -> None:
    frame = ButtonMapper(Mapping()).update(state("y", right=(0.3, 0.8)), 0.0)
    assert frame.screen_adjust == (0.8, 0.3)
    assert frame.right_stick == (0.0, 0.0)


def test_right_stick_reaches_the_game_without_the_combo_key() -> None:
    frame = ButtonMapper(Mapping()).update(state(right=(0.3, 0.8)), 0.0)
    assert frame.right_stick == (0.3, 0.8)
    assert frame.screen_adjust == (0.0, 0.0)


def test_quick_press_of_the_combo_key_is_a_tap_of_its_own_button() -> None:
    mapper = ButtonMapper(Mapping())
    assert "TRIANGLE" not in mapper.update(state("y"), 0.00).buttons
    assert "TRIANGLE" in mapper.update(state(), 0.10).buttons
    assert "TRIANGLE" not in mapper.update(state(), 0.30).buttons


def test_holding_the_combo_key_alone_holds_its_own_button() -> None:
    mapper = ButtonMapper(Mapping())
    mapper.update(state("y"), 0.0)
    assert "TRIANGLE" in mapper.update(state("y"), 0.3).buttons


def test_a_used_combo_does_not_tap_on_release() -> None:
    mapper = ButtonMapper(Mapping())
    mapper.update(state("y", left=(0.0, 1.0)), 0.0)
    assert "TRIANGLE" not in mapper.update(state(), 0.05).buttons


def test_without_a_combo_key_every_button_is_plain() -> None:
    mapping = Mapping(buttons={**Mapping().buttons, "y": "TRIANGLE"}, combo_key=None)
    frame = ButtonMapper(mapping).update(state("y", left=(0.0, 1.0)), 0.0)
    assert frame.buttons == {"TRIANGLE"}
    assert frame.dpad is None
    assert frame.left_stick == (0.0, 1.0)


def test_recenter_fires_once_after_holding_both_stick_clicks() -> None:
    mapper = ButtonMapper(Mapping())
    both = state("left_stick_click", "right_stick_click")
    assert not mapper.update(both, 0.0).recenter
    assert not mapper.update(both, 0.9).recenter
    assert mapper.update(both, 1.0).recenter
    assert not mapper.update(both, 1.5).recenter
    mapper.update(state(), 2.0)
    mapper.update(both, 3.0)
    assert mapper.update(both, 4.1).recenter


def test_mapping_problems_are_reported_in_words() -> None:
    assert Mapping().problems() == []
    broken = Mapping(buttons={"q": "CROSS", "a": "JUMP"}, trigger_left="a", combo_key="z")
    text = " ".join(broken.problems())
    for fragment in ('"q"', '"JUMP"', "triggers.left", "combo.key"):
        assert fragment in text


def test_combination_keeps_a_button_that_another_pressed_input_also_asks_for() -> None:
    mapping = Mapping(buttons={"a": "CROSS", "b": "CROSS"}, combo_with={"b": "SHARE"})
    frame = ButtonMapper(mapping).update(state("a", "b", "y"), 0.0)
    assert frame.buttons == {"CROSS", "SHARE"}
    assert ButtonMapper(mapping).update(state("b", "y"), 0.0).buttons == {"SHARE"}


def test_combination_key_cannot_also_be_a_plain_button() -> None:
    assert Mapping().problems() == []
    assert any("combo.key" in problem for problem in Mapping(combo_key="a").problems())
    assert any("combo.key" in problem for problem in Mapping(combo_key="x").problems())


def test_reset_forgets_a_combination_key_held_before_the_app_lost_the_controllers() -> None:
    mapper = ButtonMapper(Mapping())
    mapper.update(state("y"), 0.0)
    mapper.reset()
    assert "TRIANGLE" not in mapper.update(state("y"), 5.0).buttons
    assert "TRIANGLE" in mapper.update(state("y"), 5.3).buttons


def test_reset_restarts_the_recenter_hold() -> None:
    mapper = ButtonMapper(Mapping())
    mapper.update(state("left_stick_click", "right_stick_click"), 0.0)
    mapper.reset()
    assert not mapper.update(state("left_stick_click", "right_stick_click"), 2.0).recenter
    assert mapper.update(state("left_stick_click", "right_stick_click"), 3.1).recenter
