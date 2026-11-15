"""The settings window: what is needed, start and stop, and every option of the configuration file.

Drawn with Qt in the system's own style, so it follows the light or dark theme of Windows.
Options sit in cards: the name, one sentence that says what the option is for, the control,
and an information button that opens the rest of the explanation right under it.
"""

from __future__ import annotations

import contextlib
import html
import importlib.util
import json
import platform
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt, QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont, QGuiApplication, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .config import (
    BACKENDS,
    BACKGROUNDS,
    DISTANCE_RANGE_M,
    HANDS,
    PROFILES,
    WIDTH_RANGE_M,
    CaptureConfig,
    Config,
    ConfigError,
    GyroConfig,
    ScreenConfig,
    data_dir,
    default_config_path,
    load_config,
    parse_config,
)
from .engine import STOP_FILE_NAME, Engine
from .gui_text import LANGUAGE_CHOICES, details, language_choice, pick_language, save_language_choice, summary
from .mapping import ANALOG_INPUTS, DIGITAL_INPUTS, PAD_BUTTONS, Mapping
from .monitors import Monitor, list_monitors
from .prerequisites import Check, check_all
from .settings_file import save_config, to_document

NOTHING = ""
ALL_INPUTS = DIGITAL_INPUTS + ANALOG_INPUTS
# The buttons page shows one card per controller, in the order the fingers find them.
LEFT_INPUTS = ("x", "y", "menu", "left_stick_click", "left_trigger", "left_squeeze")
RIGHT_INPUTS = ("a", "b", "right_stick_click", "right_trigger", "right_squeeze")
# The order a person expects: face buttons, shoulders, stick clicks, then the system buttons.
PAD_ORDER = (
    "CROSS",
    "CIRCLE",
    "SQUARE",
    "TRIANGLE",
    "SHOULDER_LEFT",
    "SHOULDER_RIGHT",
    "THUMB_LEFT",
    "THUMB_RIGHT",
    "OPTIONS",
    "SHARE",
    "PS",
    "TOUCHPAD",
)
POLL_MS = 100
LOG_LINES = 400
LOG_FILE_NAME = "last-run.log"  # what the engine said the last time it ran
BASE_POINT_SIZE = 10.5  # the system's 9 points read too small next to other programs
DESIGN_POINT_SIZE = 9.0  # the font size the pixel measures in this file were drawn for
WINDOW_MUTEX = "VRGyroScreenWindow"  # the installer looks for it to know the window is open
Option = tuple[str, str]  # (value kept in the file, text shown)

if set(PAD_ORDER) != set(PAD_BUTTONS):  # a new gamepad button must get a place in the list
    raise RuntimeError("PAD_ORDER and mapping.PAD_BUTTONS list different buttons")
if set(LEFT_INPUTS + RIGHT_INPUTS) != set(ALL_INPUTS):  # and a new controller input, a card
    raise RuntimeError("LEFT_INPUTS and RIGHT_INPUTS do not cover the controller inputs")

STYLE = """
QFrame#card { background: rgba(127, 127, 127, 0.08); border: 1px solid rgba(127, 127, 127, 0.24);
    border-radius: 8px; }
QFrame#line { background: rgba(127, 127, 127, 0.24); border: none; max-height: 1px; min-height: 1px; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QListWidget#menu { border: none; background: transparent; outline: 0; }
QListWidget#menu::item { padding: 10px 12px; margin: 2px 0; border-radius: 6px;
    border-left: 3px solid transparent; }
QListWidget#menu::item:hover { background: rgba(127, 127, 127, 0.10); }
QListWidget#menu::item:selected { background: rgba(127, 127, 127, 0.18); color: palette(window-text);
    border-left: 3px solid palette(highlight); }
QPushButton#primary { background: palette(highlight); color: palette(highlighted-text); border: none;
    border-radius: 6px; padding: 9px 22px; font-weight: 600; }
QPushButton#primary:disabled { background: rgba(127, 127, 127, 0.35); }
QToolButton#info { border: 1px solid rgba(127, 127, 127, 0.55); border-radius: INFO_RADIUSpx;
    font-weight: 600; min-width: INFOpx; max-width: INFOpx; min-height: INFOpx; max-height: INFOpx; }
QToolButton#info:hover, QToolButton#info:checked { background: palette(highlight);
    color: palette(highlighted-text); border-color: palette(highlight); }
QLabel#badge { background: rgba(127, 127, 127, 0.22); border-radius: BADGE_RADIUSpx; font-weight: 600;
    min-width: BADGEpx; max-width: BADGEpx; min-height: BADGEpx; max-height: BADGEpx; }
"""


def text_scale() -> float:
    """The text size chosen in the Windows accessibility settings (1.0 to 2.25)."""
    if sys.platform != "win32":
        return 1.0
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Accessibility") as key:
            percent = int(winreg.QueryValueEx(key, "TextScaleFactor")[0])
    except (OSError, ValueError, TypeError):
        return 1.0
    return min(max(percent, 100), 225) / 100


def use_readable_font(app: QCoreApplication) -> None:
    """A base size in line with other programs, grown by the text size the person set in Windows."""
    if not isinstance(app, QApplication):
        return
    font = app.font()
    font.setPointSizeF(BASE_POINT_SIZE * text_scale())
    app.setFont(font)


def _px(pixels: float) -> int:
    """A measure drawn for the design font size, grown with the font in use."""
    return round(pixels * max(QApplication.font().pointSizeF(), DESIGN_POINT_SIZE) / DESIGN_POINT_SIZE)


def _style() -> str:
    sizes = {"INFO_RADIUS": _px(22) // 2, "INFO": _px(22) // 2 * 2 - 2, "BADGE_RADIUS": _px(26) // 2}
    sizes["BADGE"] = sizes["BADGE_RADIUS"] * 2
    style = STYLE
    for name in ("INFO_RADIUS", "BADGE_RADIUS", "INFO", "BADGE"):
        style = style.replace(name + "px", f"{sizes[name]}px")
    return style


def monitor_options(monitors: Sequence[Monitor], saved: str, text: dict[str, str]) -> list[Option]:
    """Choices for the monitor list. A monitor is saved by its description when no other
    monitor shares it (it survives Windows renumbering the displays), else by device name."""
    options: list[Option] = [("auto", text["monitor_auto"])]
    descriptions = [monitor.description for monitor in monitors]
    for monitor in monitors:
        unique = monitor.description and descriptions.count(monitor.description) == 1
        options.append((monitor.description if unique else monitor.device_name, monitor.label))
    wanted = saved.strip().lower()
    if wanted in ("", "auto"):
        return options
    if wanted.isdigit():  # a position in the list, as the command line accepts
        if int(wanted) < len(monitors):
            options[int(wanted) + 1] = (saved, monitors[int(wanted)].label)
            return options
        wanted = ""  # no such position: shown below as saved and not connected
    for index, monitor in enumerate(monitors, start=1):
        if wanted and (wanted in monitor.device_name.lower() or wanted in monitor.description.lower()):
            options[index] = (saved, monitor.label)  # keep the saved text: it already selects this one
            return options
    options.append((saved, text["monitor_saved"].format(name=saved)))
    return options


def _combo(options: Sequence[Option], width: int = 250) -> QComboBox:
    combo = QComboBox()
    combo.setFixedWidth(_px(width))  # a steady width keeps the option names from being squeezed
    _fill(combo, options)
    return combo


def _fill(combo: QComboBox, options: Sequence[Option]) -> None:
    combo.clear()
    for value, shown in options:
        combo.addItem(shown, value)


def _select(combo: QComboBox, value: str) -> None:
    combo.setCurrentIndex(max(combo.findData(value), 0))


def _value(combo: QComboBox) -> str:
    return str(combo.currentData())


def _number(low: float, high: float, step: float, decimals: int = 2) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(low, high)
    box.setSingleStep(step)
    box.setDecimals(decimals)
    box.setMinimumWidth(_px(110))
    return box


def _secondary(text: str) -> QLabel:
    """Help text, in the quieter colour the system uses for hints."""
    label = QLabel(text)
    label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
    label.setWordWrap(True)
    return label


def _scaled(label: QLabel, factor: float, weight: QFont.Weight = QFont.Weight.Normal) -> QLabel:
    font = QFont(label.font())
    font.setPointSizeF(font.pointSizeF() * factor)
    font.setWeight(weight)
    label.setFont(font)
    return label


def _status_color(widget: QWidget, ok: bool) -> str:
    """Green or orange that stay readable on a light or a dark window."""
    dark = widget.palette().color(QPalette.ColorRole.Window).lightness() < 128
    if ok:
        return "#4CC38A" if dark else "#1E7F46"
    return "#FF8A5B" if dark else "#C2410C"


def _line() -> QFrame:
    line = QFrame()
    line.setObjectName("line")
    return line


def _card(*rows: QWidget) -> QFrame:
    """A rounded box of rows, with a hairline between one row and the next."""
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    for index, row in enumerate(rows):
        if index:
            layout.addWidget(_line())
        layout.addWidget(row)
    return card


def _one_open_at_a_time(buttons: Sequence[QToolButton]) -> None:
    """Opening one of these explanations closes the others: they are shown in the same place."""

    def close_others(opened: QToolButton, checked: bool) -> None:
        if checked:
            for other in buttons:
                if other is not opened:
                    other.setChecked(False)

    for button in buttons:
        button.toggled.connect(lambda checked, opened=button: close_others(opened, checked))


def _padded(*widgets: QWidget) -> tuple[QWidget, QVBoxLayout]:
    """A row of a card, with the card's inner margins."""
    row = QWidget()
    layout = QVBoxLayout(row)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(8)
    for widget in widgets:
        layout.addWidget(widget)
    return row, layout


class SettingsWindow(QWidget):
    def __init__(self, config_path: Path | None = None, on_language: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.text = pick_language()
        self.config_path = config_path or default_config_path()
        self.engine = Engine(data_dir() / STOP_FILE_NAME)
        self.loaded = Config()
        self._closing = False
        self._active = False  # from Start until the engine's end was seen by _poll
        self._on_language = on_language

        self.setWindowTitle(self.text["title"])
        self.setStyleSheet(_style())
        self.setMinimumSize(_px(860), _px(600))
        self._restart = False  # True while the engine closes only to start again with new settings
        icon = Path(__file__).parent / "assets" / "icon.png"
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 16)
        outer.setSpacing(14)
        outer.addLayout(self._build_header(icon))

        self.menu = QListWidget()
        self.menu.setObjectName("menu")
        self.menu.setFixedWidth(_px(200))
        self.pages = QStackedWidget()
        for key, build in (
            ("tab_start", self._build_start),
            ("tab_screen", self._build_screen),
            ("tab_controller", self._build_motion),
            ("tab_buttons", self._build_buttons),
        ):
            self.menu.addItem(self.text[key])
            self.pages.addWidget(build())
        self.menu.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.menu.setCurrentRow(0)
        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(self.menu)
        body.addWidget(self.pages, 1)
        outer.addLayout(body, 1)
        outer.addWidget(_line())
        outer.addLayout(self._build_footer())

        self._load()
        self.refresh_checks()
        self._show_state("state_stopped")
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(POLL_MS)

    # ---------------------------------------------------------------- small parts

    def _info(self, key: str) -> tuple[QToolButton, QLabel]:
        """The information button and the explanation it opens (also shown on hover)."""
        explanation = details(self.text[key])
        detail = _secondary(explanation)
        detail.setVisible(False)
        button = QToolButton()
        button.setObjectName("info")
        button.setText("i")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(f"<p>{html.escape(explanation)}</p>")  # rich text, so the tooltip wraps its lines
        button.setAccessibleName(self.text["more_info"])
        button.setAccessibleDescription(explanation)
        button.toggled.connect(detail.setVisible)
        return button, detail

    def _option(self, key: str, *controls: QWidget, help_key: str = "") -> QWidget:
        """One option: its name, what it is for in one sentence, the control and the information button."""
        help_key = help_key or "help_" + key
        title = QLabel(self.text[key])
        title.setWordWrap(True)
        names = QVBoxLayout()
        names.setSpacing(2)
        names.addWidget(title)
        names.addWidget(_secondary(summary(self.text[help_key])))
        button, detail = self._info(help_key)
        top = QHBoxLayout()
        top.setSpacing(12)
        top.addLayout(names, 1)
        for control in controls:
            control.setAccessibleName(self.text[key])
            top.addWidget(control)
        top.addWidget(button)
        row, layout = _padded()
        layout.addLayout(top)
        layout.addWidget(detail)
        return row

    def _page(self) -> tuple[QScrollArea, QVBoxLayout]:
        """A page of the window: it scrolls when the window is short."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(2, 0, 12, 8)
        layout.setSpacing(10)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidget(content)
        return area, layout

    def _section(self, layout: QVBoxLayout, title_key: str, *rows: QWidget, intro_key: str = "") -> None:
        if layout.count():
            layout.addSpacing(8)
        layout.addWidget(_scaled(QLabel(self.text[title_key]), 1.1, QFont.Weight.DemiBold))
        if intro_key:
            layout.addWidget(_secondary(self.text[intro_key]))
        layout.addWidget(_card(*rows))

    # ---------------------------------------------------------------- building

    def _build_header(self, icon: Path) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(14)
        if icon.is_file():
            picture = QLabel()
            picture.setPixmap(QIcon(str(icon)).pixmap(_px(52), _px(52)))
            header.addWidget(picture)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(_scaled(QLabel(self.text["title"]), 1.9, QFont.Weight.DemiBold))
        titles.addWidget(_secondary(self.text["byline"]))
        header.addLayout(titles, 1)
        self.start_button = QPushButton(self.text["start"])
        self.start_button.setObjectName("primary")
        self.start_button.setMinimumWidth(_px(140))
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.clicked.connect(self.toggle_engine)
        header.addWidget(self.start_button)
        return header

    def _build_footer(self) -> QHBoxLayout:
        t = self.text
        footer = QHBoxLayout()
        footer.addWidget(QLabel(t["language"] + ":"))
        self.language = _combo([(choice, t[f"language_{choice}"]) for choice in LANGUAGE_CHOICES], 170)
        _select(self.language, language_choice())
        self.language.activated.connect(self._language_picked)
        footer.addWidget(self.language)
        footer.addSpacing(12)
        footer.addWidget(_secondary(t["version"].format(version=__version__)))
        self.save_note = QLabel("")
        self.save_note.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.save_note.setWordWrap(True)
        footer.addWidget(self.save_note, 1)
        self.apply_button = QPushButton(t["apply_now"])
        self.apply_button.setVisible(False)
        self.apply_button.clicked.connect(self.apply_now)
        footer.addWidget(self.apply_button)
        defaults = QPushButton(t["defaults"])
        defaults.clicked.connect(lambda: self.show_config(Config()))
        save = QPushButton(t["save"])
        save.setMinimumWidth(_px(110))
        save.clicked.connect(self.save)
        footer.addWidget(defaults)
        footer.addWidget(save)
        return footer

    def _step(self, number: int, key: str) -> tuple[QWidget, QVBoxLayout]:
        """A numbered step of the start page; what belongs to the step goes in the returned layout."""
        badge = QLabel(str(number))
        badge.setObjectName("badge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sentence = QLabel(self.text[key])
        sentence.setWordWrap(True)
        content = QVBoxLayout()
        content.setSpacing(10)
        content.addWidget(sentence)
        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        top.addLayout(content, 1)
        row, layout = _padded()
        layout.addLayout(top)
        return row, content

    def _build_start(self) -> QWidget:
        t = self.text
        page, layout = self._page()

        self.state_dot = _scaled(QLabel("●"), 1.4)
        self.state_label = _scaled(QLabel(""), 1.25, QFont.Weight.DemiBold)
        self.state_label.setWordWrap(True)
        banner = QHBoxLayout()
        banner.setSpacing(12)
        banner.addWidget(self.state_dot)
        banner.addWidget(self.state_label, 1)
        state, state_layout = _padded()
        state_layout.setContentsMargins(18, 18, 18, 18)
        state_layout.addLayout(banner)
        layout.addWidget(_card(state))

        first, needs = self._step(1, "step_1")
        self.checks_grid = QGridLayout()
        self.checks_grid.setColumnStretch(1, 1)
        self.checks_grid.setVerticalSpacing(6)
        self.checks_grid.setHorizontalSpacing(10)
        needs.addLayout(self.checks_grid)
        bottom = QHBoxLayout()
        bottom.addWidget(_secondary(t["requirements_note"]), 1)
        again = QPushButton(t["check_again"])
        again.clicked.connect(self.refresh_checks)
        bottom.addWidget(again)
        needs.addLayout(bottom)
        second, _ = self._step(2, "step_2")
        third, _ = self._step(3, "step_3")
        self._section(layout, "steps_title", first, second, third)

        tips = []
        for line in t["how_to"].split("\n"):
            tip = QLabel(line)
            tip.setWordWrap(True)
            tips.append(_padded(tip)[0])
        self._section(layout, "how_to_title", *tips)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(LOG_LINES)
        self.log.setMinimumHeight(_px(130))
        self.copy_note = _secondary("")
        copy = QPushButton(t["copy_diagnostics"])
        copy.clicked.connect(self.copy_diagnostics)
        button, detail = self._info("help_messages")
        row = QHBoxLayout()
        row.addWidget(_secondary(summary(t["help_messages"])), 1)
        row.addWidget(self.copy_note)
        row.addWidget(copy)
        row.addWidget(button)
        messages, messages_layout = _padded()
        messages_layout.addLayout(row)
        messages_layout.addWidget(detail)
        messages_layout.addWidget(self.log)
        self._section(layout, "messages", messages)
        layout.addStretch(1)
        return page

    def _build_screen(self) -> QWidget:
        t = self.text
        page, layout = self._page()
        self.monitor = _combo([("auto", t["monitor_auto"])], 360)
        refresh = QPushButton(t["refresh"])
        refresh.clicked.connect(lambda: self.refresh_monitors())
        self.profile = _combo([(name, t[f"profile_{name}"]) for name in PROFILES], 360)
        self.background = _combo([(name, t[f"background_{name}"]) for name in BACKGROUNDS], 360)
        self.distance = _number(*DISTANCE_RANGE_M, 0.1)
        self.screen_width = _number(*WIDTH_RANGE_M, 0.1)
        self.recenter = _number(0.2, 10.0, 0.1)
        offered = [name for name in BACKENDS if name != "dxcam" or importlib.util.find_spec("dxcam")]
        self.backend = _combo([(name, t[f"backend_{name}"]) for name in offered], 360)

        self._section(
            layout,
            "section_image",
            self._option("monitor", self.monitor, refresh),
            self._option("profile", self.profile),
            self._option("background", self.background),
        )
        self._section(
            layout,
            "section_place",
            self._option("distance", self.distance),
            self._option("width", self.screen_width),
            self._option("recenter", self.recenter),
        )
        self._section(layout, "advanced", self._option("backend", self.backend))
        layout.addStretch(1)
        return page

    def _build_motion(self) -> QWidget:
        t = self.text
        page, layout = self._page()
        inputs = [(name, t[f"input_{name}"]) for name in LEFT_INPUTS + RIGHT_INPUTS]
        self.hand = _combo([(name, t[f"hand_{name}"]) for name in HANDS], 160)
        self.scale = _number(0.0, 20.0, 0.1)
        self.deadzone = _number(0.0, 90.0, 0.5)
        self.keepalive = QCheckBox()
        self.combo_key = _combo([(NOTHING, t["nothing"]), *inputs])
        self.combo_solo = _combo(self._pad_options())
        self.combo_delay = _number(0.0, 5.0, 0.05)
        self.combo_dpad = QCheckBox()
        self.combo_screen = QCheckBox()

        self._section(
            layout,
            "motion",
            self._option("hand", self.hand),
            self._option("scale", self.scale),
            self._option("deadzone", self.deadzone),
            self._option("keepalive", self.keepalive),
        )
        self._section(
            layout,
            "combo",
            self._option("combo_key", self.combo_key),
            self._option("combo_solo", self.combo_solo),
            self._option("combo_delay", self.combo_delay),
            self._option("combo_dpad", self.combo_dpad),
            self._option("combo_screen", self.combo_screen),
            intro_key="combo_intro",
        )
        layout.addStretch(1)
        return page

    def _pad_options(self) -> list[Option]:
        return [(NOTHING, self.text["nothing"])] + [(name, self.text[f"pad_{name}"]) for name in PAD_ORDER]

    def _controller_card(self, names: Sequence[str]) -> QWidget:
        """The buttons of one controller: what each sends alone and with the combination button."""
        t = self.text
        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(14)
        grid.setColumnStretch(0, 1)
        grid.addWidget(_secondary(t["column_input"]), 0, 0)
        heads: list[QToolButton] = []
        for column, key in ((1, "column_alone"), (2, "column_combo")):
            button, detail = self._info("help_" + key)
            heads.append(button)
            head = QHBoxLayout()
            head.setSpacing(6)
            head.addWidget(_secondary(t[key]))
            head.addWidget(button)
            head.addStretch(1)
            grid.addLayout(head, 0, column)
            grid.addWidget(detail, 1, 0, 1, 3)
        _one_open_at_a_time(heads)  # both explanations open in the same place
        for row, name in enumerate(names, start=2):
            self.input_labels[name] = QLabel(t[f"input_{name}"])
            grid.addWidget(self.input_labels[name], row, 0)
            self.alone[name] = _combo(self._pad_options(), 240)
            self.with_combo[name] = _combo(self._pad_options(), 240)
            grid.addWidget(self.alone[name], row, 1)
            grid.addWidget(self.with_combo[name], row, 2)
        card, layout = _padded()
        layout.addLayout(grid)
        return card

    def _build_buttons(self) -> QWidget:
        t = self.text
        page, layout = self._page()
        self.alone: dict[str, QComboBox] = {}
        self.with_combo: dict[str, QComboBox] = {}
        self.input_labels: dict[str, QLabel] = {}
        layout.addWidget(_secondary(t["buttons_intro"]))
        self._section(layout, "left_controller", self._controller_card(LEFT_INPUTS))
        self._section(layout, "right_controller", self._controller_card(RIGHT_INPUTS))
        analog = [(name, t[f"input_{name}"]) for name in ANALOG_INPUTS]
        self.trigger_left = _combo(analog)
        self.trigger_right = _combo(analog)
        self._section(
            layout,
            "triggers",
            self._option("trigger_left", self.trigger_left, help_key="help_triggers"),
            self._option("trigger_right", self.trigger_right, help_key="help_triggers"),
        )
        layout.addStretch(1)
        self.combo_key.currentIndexChanged.connect(self._mark_combo_key)
        return page

    def _mark_combo_key(self) -> None:
        """On the buttons page, say which row is the combination button."""
        chosen = _value(self.combo_key)
        for name, label in self.input_labels.items():
            shown = self.text[f"input_{name}"]
            label.setText(f"{shown} ({self.text['is_combo']})" if name == chosen else shown)

    # ---------------------------------------------------------------- settings

    def _load(self) -> None:
        try:
            config = load_config(self.config_path) if self.config_path.is_file() else Config()
        except ConfigError as error:
            config = Config()
            QMessageBox.warning(self, self.text["load_problem_title"], self.text["load_problem"].format(error=error))
        self.show_config(config)
        self._show_headset_distance()

    def _show_headset_distance(self) -> None:
        """Show the distance last adjusted inside the headset, so the field says what will be used."""
        try:
            saved = json.loads((data_dir() / "screen.json").read_text(encoding="utf-8"))
            distance = float(saved["distance"])
        except (OSError, ValueError, KeyError, TypeError):
            return
        if DISTANCE_RANGE_M[0] <= distance <= DISTANCE_RANGE_M[1]:
            self.distance.setValue(distance)

    def refresh_monitors(self, saved: str | None = None) -> None:
        current = _value(self.monitor) if saved is None else saved
        try:
            monitors = list_monitors()
        except OSError:
            monitors = []
        _fill(self.monitor, monitor_options(monitors, current, self.text))
        _select(self.monitor, current)

    def show_config(self, config: Config) -> None:
        """Fill every field from a configuration."""
        self.loaded = config
        self.refresh_monitors(config.screen.monitor)
        _select(self.profile, config.profile)
        _select(self.background, config.screen.background)
        if self.backend.findData(config.capture.backend) < 0:  # saved by hand, not offered on this computer
            self.backend.addItem(self.text[f"backend_{config.capture.backend}"], config.capture.backend)
        _select(self.backend, config.capture.backend)
        _select(self.hand, config.gyro.hand)
        self.keepalive.setChecked(config.gyro.keepalive)
        self.distance.setValue(config.screen.distance_m)
        self.screen_width.setValue(config.screen.width_m)
        self.scale.setValue(config.gyro.scale)
        self.deadzone.setValue(config.gyro.deadzone_dps)
        mapping = config.mapping
        for name in ALL_INPUTS:
            _select(self.alone[name], mapping.buttons.get(name, NOTHING))
            _select(self.with_combo[name], mapping.combo_with.get(name, NOTHING))
        _select(self.combo_key, mapping.combo_key or NOTHING)
        _select(self.combo_solo, mapping.combo_solo or NOTHING)
        self.combo_dpad.setChecked(mapping.combo_dpad)
        self.combo_screen.setChecked(mapping.combo_screen_adjust)
        self.combo_delay.setValue(mapping.combo_solo_delay_s)
        self.recenter.setValue(mapping.recenter_hold_s)
        _select(self.trigger_left, mapping.trigger_left)
        _select(self.trigger_right, mapping.trigger_right)
        self._mark_combo_key()

    def read(self) -> Config:
        """The configuration the fields describe. Raises ConfigError when it is not valid."""
        profile = _value(self.profile)
        if profile == self.loaded.profile:
            mipmaps, max_fps = self.loaded.capture.mipmaps, self.loaded.capture.max_fps  # keep hand-made overrides
        else:
            mipmaps, max_fps = PROFILES[profile].mipmaps, PROFILES[profile].max_fps
        chosen = {name: _value(self.alone[name]) for name in ALL_INPUTS}
        combined = {name: _value(self.with_combo[name]) for name in ALL_INPUTS}
        config = Config(
            profile=profile,
            screen=ScreenConfig(
                monitor=_value(self.monitor),
                distance_m=round(self.distance.value(), 2),
                width_m=round(self.screen_width.value(), 2),
                background=_value(self.background),
            ),
            capture=CaptureConfig(backend=_value(self.backend), mipmaps=mipmaps, max_fps=max_fps),
            gyro=GyroConfig(
                hand=_value(self.hand),
                scale=round(self.scale.value(), 2),
                deadzone_dps=round(self.deadzone.value(), 2),
                keepalive=self.keepalive.isChecked(),
            ),
            mapping=Mapping(
                buttons={name: target for name, target in chosen.items() if target},
                trigger_left=_value(self.trigger_left),
                trigger_right=_value(self.trigger_right),
                combo_key=_value(self.combo_key) or None,
                combo_solo=_value(self.combo_solo) or None,
                combo_solo_delay_s=round(self.combo_delay.value(), 2),
                combo_with={name: target for name, target in combined.items() if target},
                combo_dpad=self.combo_dpad.isChecked(),
                combo_screen_adjust=self.combo_screen.isChecked(),
                recenter_hold_s=round(self.recenter.value(), 2),
            ),
        )
        return parse_config(to_document(config))  # the same checks the file gets when it is read

    def save(self) -> bool:
        try:
            config = self.read()
            save_config(config, self.config_path)
        except (ConfigError, OSError, ValueError) as error:
            QMessageBox.critical(self, self.text["invalid_title"], str(error))
            return False
        self.loaded = config
        self.save_note.setText(self.text["saved_running" if self._active else "saved"])
        self.apply_button.setVisible(self._active)
        return True

    def apply_now(self) -> None:
        """Close the engine and start it again, so what was just saved is used."""
        self.apply_button.setVisible(False)
        if not self._active:
            return
        self._restart = True
        self.engine.request_stop()
        self.start_button.setEnabled(False)
        self._show_state("state_restarting")

    def _save_if_changed(self) -> bool:
        """Save before starting, unless the file already says what the fields say."""
        try:
            if self.config_path.is_file() and self.read() == self.loaded:
                return True
        except ConfigError:
            pass  # save() shows the problem
        return self.save()

    def _language_picked(self) -> None:
        choice = _value(self.language)
        if choice == language_choice():
            return
        save_language_choice(choice)
        if self._on_language is not None:
            self._on_language()

    # ---------------------------------------------------------------- requirements

    def refresh_checks(self) -> list[Check]:
        t = self.text
        while self.checks_grid.count():
            item = self.checks_grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        checks = check_all()
        for index, check in enumerate(checks):
            row = index * 2
            state = t["found"] if check.ok else t["missing"]
            if check.key != "gamepad_driver" and check.detail:
                state += f" ({t['active_runtime'].format(name=check.detail)})"
            mark = QLabel("✓" if check.ok else "✗")
            mark.setStyleSheet(f"color: {_status_color(self, check.ok)}; font-weight: 600;")
            name = QLabel(f"{t['check_' + check.key]}: {state}")
            name.setWordWrap(True)
            button, detail = self._info("help_check_" + check.key)
            detail.setText(t["help_check_" + check.key])  # here the first sentence is not shown elsewhere
            self.checks_grid.addWidget(mark, row, 0)
            self.checks_grid.addWidget(name, row, 1)
            if not check.ok:
                site = QPushButton(t["open_site"])
                site.clicked.connect(lambda _=False, url=check.url: QDesktopServices.openUrl(QUrl(url)))
                self.checks_grid.addWidget(site, row, 2)
            self.checks_grid.addWidget(button, row, 3)
            self.checks_grid.addWidget(detail, row + 1, 1, 1, 3)
        return checks

    # ---------------------------------------------------------------- engine

    def _show_state(self, key: str) -> None:
        self.state_label.setText(self.text[key])
        colors = {"state_running": _status_color(self, True), "state_failed": _status_color(self, False)}
        self.state_dot.setStyleSheet(f"color: {colors.get(key, 'rgba(127, 127, 127, 0.7)')};")

    def toggle_engine(self) -> None:
        t = self.text
        if self._active:
            self.engine.request_stop()
            self.start_button.setEnabled(False)
            self.apply_button.setVisible(False)
            self._show_state("state_stopping")
            return
        if not self._save_if_changed():
            return
        missing = [t["check_" + check.key] for check in self.refresh_checks() if not check.ok]
        if missing:
            answer = QMessageBox.question(
                self, t["missing_title"], t["missing_question"].format(items="\n".join(missing))
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.engine.start(self.distance.value())  # the field wins over the distance kept from last time
        except OSError as error:
            self.log.appendPlainText(str(error))
            self._show_state("state_failed")
            return
        self._active = True
        self._write_log("", fresh=True)
        self.save_note.setText(t["running_note"])
        self.start_button.setText(t["stop"])
        self.language.setEnabled(False)  # changing it rebuilds the window, which would drop the session
        self.menu.setCurrentRow(0)  # the status and the messages are on the first page
        self._show_state("state_running")

    def _write_log(self, text: str, fresh: bool = False) -> None:
        """Keep what the engine says in a file too, so a problem can be read after the window closes."""
        with (
            contextlib.suppress(OSError),
            (data_dir() / LOG_FILE_NAME).open("w" if fresh else "a", encoding="utf-8") as file,
        ):
            file.write(text)

    def _poll(self) -> None:
        ended = False
        said = []
        while not self.engine.lines.empty():
            line = self.engine.lines.get_nowait()
            if line is None:
                ended = True
            else:
                said.append(line)
                self.log.appendPlainText(line)
        if said:
            self._write_log("\n".join(said) + "\n")
        if not ended:
            return
        self._active = False
        if self._closing:
            self.close()
            return
        self.start_button.setText(self.text["start"])
        self.start_button.setEnabled(True)
        self.language.setEnabled(True)
        self.apply_button.setVisible(False)
        self.save_note.setText("")
        if self._restart:
            self._restart = False
            self.toggle_engine()
            return
        self._show_headset_distance()  # it may have been changed with the controllers
        # An engine that had to be ended after a stop request still stopped because it was asked to.
        asked = self.engine.exit_code == 0 or self.engine.stop_requested
        self._show_state("state_stopped" if asked else "state_failed")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Closing the window also closes the engine, cleanly when it answers in time."""
        if not self._active:
            event.accept()
            return
        event.ignore()
        self._closing = True
        self.engine.request_stop()
        self.start_button.setEnabled(False)
        self._show_state("state_stopping")

    # ---------------------------------------------------------------- diagnostics

    def diagnostics(self) -> str:
        lines = [
            f"vr-gyro-screen {__version__}",
            f"Windows {platform.version()}, Python {platform.python_version()}",
            f"settings file: {'present' if self.config_path.is_file() else 'not created yet'}",
        ]
        lines += [f"{check.key}: {'ok' if check.ok else 'MISSING'} {check.detail}".rstrip() for check in check_all()]
        try:
            lines += [f"monitor {monitor.index}: {monitor.label}" for monitor in list_monitors()]
        except OSError as error:
            lines.append(f"monitors: {error}")
        lines += ["", self.log.toPlainText().strip()]
        return "\n".join(lines)

    def copy_diagnostics(self) -> None:
        QGuiApplication.clipboard().setText(self.diagnostics())
        self.copy_note.setText(self.text["copied"])


class _Host:
    """Keeps the one open window, and opens it again in the other language when asked."""

    def __init__(self, config_path: Path | None) -> None:
        self.config_path = config_path
        self.window = SettingsWindow(config_path, self.reopen)
        self.window.resize(_px(1080), _px(780))
        self.window.show()

    def reopen(self) -> None:
        old = self.window
        new = SettingsWindow(self.config_path, self.reopen)
        try:
            unsaved = old.read()
        except ConfigError:
            unsaved = None
        if unsaved is not None:  # what was typed and not saved yet comes along
            new.show_config(unsaved)
            new.loaded = old.loaded
        new.menu.setCurrentRow(old.menu.currentRow())
        new.setGeometry(old.geometry())
        new.show()
        self.window = new
        old.close()
        old.deleteLater()


def _already_open(title: str) -> bool:
    """True when another copy of the window is open; that copy is brought to the front."""
    if sys.platform != "win32":
        return False
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32")
    # The handle is kept for the life of the process on purpose: that is what marks it as open.
    kernel32.CreateMutexW(None, False, WINDOW_MUTEX)
    if ctypes.get_last_error() != 183:  # ERROR_ALREADY_EXISTS
        return False
    other = user32.FindWindowW(None, title)
    if other:
        user32.ShowWindow(other, 9)  # SW_RESTORE
        user32.SetForegroundWindow(other)
    return True


def open_window(config_path: Path | None = None) -> int:
    if _already_open(pick_language()["title"]):
        return 0
    app = QApplication.instance() or QApplication(sys.argv[:1])
    use_readable_font(app)
    host = _Host(config_path)
    code = int(app.exec())
    del host
    return code
