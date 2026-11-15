"""The main loop: monitor image to the headset, controllers to the virtual gamepad."""

from __future__ import annotations

import contextlib
import math
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import xr
from OpenGL import GL
from xr.utils.gl import ContextObject
from xr.utils.gl.glfw_util import GLFWOffscreenContextProvider

from .capture.dxgi import CaptureLostError
from .capture.sources import CaptureUnavailableError, FrameSource, open_source
from .config import APP_NAME, Config, data_dir
from .headset import ControllerReader, RecenterWatch, ScreenLayer
from .mapping import ButtonMapper, PadFrame
from .monitors import Monitor, MonitorNotFoundError, choose_monitor, list_monitors, same_monitor
from .motion import MotionModel
from .pad import VirtualPad
from .placement import ScreenPlacement

RETRY_SECONDS = 1.0
REPORT_SECONDS = 10.0
STOP_CHECK_SECONDS = 0.25
SCREEN_PITCH_SPEED = 0.6  # radians per second at full stick
SCREEN_DISTANCE_SPEED = 1.5  # metres per second at full stick
LATE_FACTOR = 1.5  # a frame counts as late when it took this many display periods

_WAITING = (CaptureLostError, CaptureUnavailableError, MonitorNotFoundError)


class StartupError(RuntimeError):
    """The app could not start; the message tells the person what to check."""


class Capture:
    """Keeps a frame source open, reopening it when the monitor goes away and comes back.

    Virtual Desktop removes its virtual monitor when the headset disconnects and creates a
    new one (with a new Windows name) when it reconnects or the refresh rate changes.
    """

    def __init__(self, config: Config, screen: ScreenLayer) -> None:
        self._config = config
        self._screen = screen
        self._source: FrameSource | None = None
        self._monitor: Monitor | None = None
        self._retry_at = 0.0
        self._last_new = 0.0
        self._last_problem = ""
        self._min_gap = 1.0 / config.capture.max_fps if config.capture.max_fps > 0 else 0.0

    def _pick(self) -> Monitor:
        monitors = list_monitors()
        if self._monitor is None:
            return choose_monitor(monitors, self._config.screen.monitor)
        # After a loss, only the same monitor is accepted: falling back to another one would
        # put a different desktop in the headset without anyone asking.
        monitor = same_monitor(monitors, self._monitor)
        if monitor is None:
            raise MonitorNotFoundError("the monitor has not come back yet")
        return monitor

    def _open(self) -> None:
        monitor = self._pick()
        source = open_source(
            self._config.capture.backend, monitor.device_name, self._screen.format, max(monitor.refresh_hz, 60)
        )
        try:
            self._screen.resize(source.width, source.height)
            self._screen.present(source.texture)
        except Exception:
            source.close()
            raise
        self._source = source
        self._monitor = monitor
        print(f"capture: {monitor.label}, backend {source.name}", flush=True)

    def open_first(self) -> None:
        """Open at start-up; problems here are fatal and explained to the person."""
        self._open()

    def _lose(self, now: float, reason: object) -> None:
        print(f"capture: lost the monitor ({reason}); waiting for it to come back", flush=True)
        self.close()
        self._retry_at = now + RETRY_SECONDS

    def poll(self, now: float) -> None:
        """Bring the newest image to the headset, or try to get the monitor back."""
        if self._source is None:
            if now < self._retry_at:
                return
            self._retry_at = now + RETRY_SECONDS
            try:
                self._open()
            except _WAITING:
                return
            except (GL.GLError, OSError, xr.exception.XrException) as error:
                # Not a reason to end the session: the controllers keep working meanwhile.
                problem = f"{type(error).__name__}: {error}"
                if problem != self._last_problem:
                    print(f"capture: could not reopen the monitor ({problem}); still trying", flush=True)
                    self._last_problem = problem
                return
            self._last_problem = ""
            print("capture: the monitor is back", flush=True)
            return
        if self._min_gap and now - self._last_new < self._min_gap:
            return
        try:
            if self._source.poll():
                self._last_new = now
                self._screen.present(self._source.texture)
        except (CaptureLostError, GL.GLError, OSError) as error:
            self._lose(now, error)

    def close(self) -> None:
        if self._source is not None:
            try:
                self._source.close()
            except Exception as error:
                print(f"capture: error while closing ({error})", flush=True)
            self._source = None


def _choose_background(config: Config, context: Any) -> bool:
    """True when the room (passthrough) is shown around the screen."""
    modes = list(
        xr.enumerate_environment_blend_modes(
            context.instance, context.system_id, xr.ViewConfigurationType.PRIMARY_STEREO
        )
    )
    available = xr.EnvironmentBlendMode.ALPHA_BLEND in modes
    wanted = config.screen.background
    if wanted == "passthrough" and not available:
        print("background: this runtime does not offer passthrough to apps; using black", flush=True)
    passthrough = wanted != "black" and available
    if passthrough:
        context.environment_blend_mode = xr.EnvironmentBlendMode.ALPHA_BLEND
    print(f"background: {'passthrough' if passthrough else 'black'}", flush=True)
    return passthrough


def _create_pad() -> VirtualPad:
    try:
        return VirtualPad()
    except Exception as error:
        raise StartupError(
            f"could not create the virtual gamepad ({error}). Check that the ViGEmBus driver is installed."
        ) from error


@contextlib.contextmanager
def _graphics() -> Iterator[GLFWOffscreenContextProvider]:
    """The hidden OpenGL context, closed exactly once.

    The headset context closes it on its own way out, and closing it a second time fails
    inside GLFW: the app would end with an error after having done everything right.
    """
    provider = GLFWOffscreenContextProvider()
    try:
        yield provider
    finally:
        if getattr(provider, "_window", None) is not None:  # still open: the headset context never took it
            provider.destroy()


def run(config: Config, quiet: bool = False, keep_saved_distance: bool = True, stop_file: Path | None = None) -> int:
    """Run until the headset session ends, Ctrl+C is pressed or `stop_file` appears.

    The stop file is how another program (the settings window) asks for a clean exit: on
    Windows a process ended from outside gets no chance to release the gamepad buttons.
    """
    pad = _create_pad()
    print("virtual gamepad created (DualShock 4 with motion sensors)", flush=True)
    motion = MotionModel(config.gyro.scale, config.gyro.deadzone_dps, config.gyro.keepalive)
    mapper = ButtonMapper(config.mapping)
    recenter_watch = RecenterWatch()
    try:
        with (
            _graphics() as provider,
            ContextObject(
                context_provider=provider,
                instance_create_info=xr.InstanceCreateInfo(
                    application_info=xr.ApplicationInfo(application_name=APP_NAME, engine_name="none"),
                    enabled_extension_names=[xr.KHR_OPENGL_ENABLE_EXTENSION_NAME],
                ),
                reference_space_create_info=xr.ReferenceSpaceCreateInfo(
                    reference_space_type=xr.ReferenceSpaceType.LOCAL
                ),
            ) as context,
        ):
            passthrough = _choose_background(config, context)
            reader = ControllerReader(context)
            screen = ScreenLayer(context, config.screen.width_m, config.capture.mipmaps)
            placement = ScreenPlacement(config.screen.distance_m, data_dir() / "screen.json", keep_saved_distance)
            capture = Capture(config, screen)

            report_at = time.perf_counter() + REPORT_SECONDS
            frames = late = 0
            worst_gap = capture_seconds = 0.0
            previous: float | None = None
            stop_check_at = 0.0
            try:
                capture.open_first()
                for frame_state in context.frame_loop():
                    now = time.perf_counter()
                    elapsed = 0.0
                    if previous is not None:
                        gap = now - previous
                        worst_gap = max(worst_gap, gap)
                        late += gap > LATE_FACTOR * frame_state.predicted_display_period / 1e9
                        elapsed = min(0.1, gap)
                    previous = now
                    if stop_file is not None and now >= stop_check_at:
                        stop_check_at = now + STOP_CHECK_SECONDS
                        if stop_file.exists():
                            break

                    state = None
                    if context.session_state == xr.SessionState.FOCUSED:
                        try:
                            state = reader.read(frame_state.predicted_display_time)
                        except xr.exception.SessionNotFocused:
                            state = None  # focus lost in the middle of the frame (headset menu opened)
                    if state is None:
                        # Without focus the last report must not stay stuck: release everything,
                        # and forget half finished shortcuts so they do not fire on the way back.
                        mapper.reset()
                        pad.send(PadFrame(), motion.rest())
                    else:
                        if state.head is not None and (not placement.placed or recenter_watch.take(now)):
                            placement.place(state.head, use_head_pitch=False)
                        frame = mapper.update(state, now)
                        hand = state.right_aim if config.gyro.hand == "right" else state.left_aim
                        pad.send(frame, motion.update(hand, frame_state.predicted_display_time / 1e9))
                        if frame.recenter and state.head is not None:
                            placement.place(state.head, use_head_pitch=True)
                            print(f"screen recentered (tilt {math.degrees(placement.pitch):.0f} degrees)", flush=True)
                        up_down, near_far = frame.screen_adjust
                        if up_down or near_far:
                            placement.adjust(
                                up_down * SCREEN_PITCH_SPEED * elapsed, -near_far * SCREEN_DISTANCE_SPEED * elapsed
                            )
                        else:
                            placement.save_if_changed()

                    capture_started = time.perf_counter()
                    capture.poll(now)
                    capture_seconds += time.perf_counter() - capture_started

                    if passthrough:
                        # Passthrough needs a projection layer with transparent pixels behind the screen.
                        for _ in context.view_loop(frame_state):
                            GL.glClearColor(0.0, 0.0, 0.0, 0.0)
                            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
                    layer = screen.layer(placement.pose())
                    if layer is not None:
                        context.render_layers.append(layer)

                    frames += 1
                    if now >= report_at:
                        if not quiet:
                            span = REPORT_SECONDS + (now - report_at)
                            print(
                                f"{frames / span:.0f} frames/s, worst gap {worst_gap * 1000:.0f} ms, {late} late, "
                                f"capture {capture_seconds / max(frames, 1) * 1000:.2f} ms per frame, "
                                f"session {context.session_state.name}",
                                flush=True,
                            )
                        report_at = now + REPORT_SECONDS
                        frames = late = 0
                        worst_gap = capture_seconds = 0.0
            except KeyboardInterrupt:
                pass
            finally:
                capture.close()
                placement.save_if_changed()
    finally:
        recenter_watch.close()
        try:
            pad.send(PadFrame(), motion.rest())  # no button stays held in the game after the app leaves
        except Exception as error:
            print(f"could not release the gamepad ({error})", flush=True)
    print("closed", flush=True)
    return 0
