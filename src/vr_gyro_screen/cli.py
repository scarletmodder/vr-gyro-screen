"""Command line: run the app, list monitors, send a window to the headset monitor, benchmark."""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from .config import (
    BACKENDS,
    BACKGROUNDS,
    DISTANCE_RANGE_M,
    PROFILES,
    WIDTH_RANGE_M,
    Config,
    ConfigError,
    load_config,
    with_profile,
)

EXIT_OK, EXIT_PROBLEM, EXIT_USAGE = 0, 1, 2
# What the gamepad library says, when it loads, on a computer that does not have its driver.
DRIVER_MISSING_MARK = "VIGEM_ERROR_BUS_NOT_FOUND"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vr-gyro-screen",
        description="Play flat PC games on a big screen inside a VR headset, "
        "with the headset controllers acting as a gamepad with motion sensors.",
    )
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("settings", help="open the settings window")
    commands.add_parser("check", help="check what the app needs and that its own libraries load")

    run = commands.add_parser("run", help="show the monitor in the headset and create the gamepad (default)")
    run.add_argument("--config", type=Path, help="configuration file (default: the one in the app data folder)")
    run.add_argument("--profile", choices=tuple(PROFILES), help="how often the screen takes a new image")
    run.add_argument("--monitor", help='"auto", a position from "monitors", or part of a monitor name')
    run.add_argument("--backend", choices=BACKENDS, help="how the monitor image is captured")
    run.add_argument("--background", choices=BACKGROUNDS, help="what surrounds the screen")
    run.add_argument(
        "--distance",
        type=float,
        metavar="M",
        help="distance to the screen, in metres (replaces the distance saved from the last session)",
    )
    run.add_argument("--width", type=float, metavar="M", help="width of the screen, in metres")
    run.add_argument("--quiet", action="store_true", help="do not print the periodic timing line")
    run.add_argument("--stop-file", type=Path, metavar="FILE", help="close cleanly as soon as this file exists")

    monitors = commands.add_parser("monitors", help="list the monitors and show which one would be used")
    monitors.add_argument("--config", type=Path, help="configuration file (default: the one in the app data folder)")
    monitors.add_argument("--monitor", help="selector to try, instead of the configured one")

    window = commands.add_parser("window", help="send a window to the headset monitor and make it fill it")
    window.add_argument("title", help="part of the window title")
    window.add_argument("--monitor", default="auto")
    window.add_argument(
        "--fullscreen-key",
        choices=("f11", "alt+enter", "none"),
        default="f11",
        help="key that toggles full screen in that program (default: f11)",
    )
    window.add_argument("--wait", type=float, default=60.0, metavar="S", help="seconds to wait for the window")

    bench = commands.add_parser("bench", help="measure the processor cost of each capture backend")
    bench.add_argument("--monitor", default="auto")
    bench.add_argument("--backend", choices=BACKENDS[1:], action="append", help="repeat to compare several")
    bench.add_argument("--seconds", type=float, default=8.0)
    bench.add_argument("--rate", type=int, default=90, metavar="HZ", help="cycles per second, like the headset")
    bench.add_argument("--no-mipmaps", action="store_true")
    return parser


def _checked(option: str, value: float, limits: tuple[float, float]) -> float:
    """The same limits as the configuration file, so the command line cannot go around them."""
    low, high = limits
    if not math.isfinite(value) or not low <= value <= high:
        raise ConfigError(f"{option} must be between {low} and {high}")
    return value


def _run_config(args: argparse.Namespace) -> Config:
    config = load_config(args.config)
    if args.profile:
        config = with_profile(config, args.profile)
    screen = config.screen
    if args.monitor:
        screen = replace(screen, monitor=args.monitor)
    if args.background:
        screen = replace(screen, background=args.background)
    if args.distance is not None:
        screen = replace(screen, distance_m=_checked("--distance", args.distance, DISTANCE_RANGE_M))
    if args.width is not None:
        screen = replace(screen, width_m=_checked("--width", args.width, WIDTH_RANGE_M))
    capture = replace(config.capture, backend=args.backend) if args.backend else config.capture
    return replace(config, screen=screen, capture=capture)


def _run(args: argparse.Namespace) -> int:
    config = _run_config(args)
    import xr

    from .app import StartupError, run
    from .capture.dxgi import CaptureLostError
    from .capture.sources import CaptureUnavailableError

    try:
        return run(config, quiet=args.quiet, keep_saved_distance=args.distance is None, stop_file=args.stop_file)
    except (CaptureLostError, CaptureUnavailableError) as error:
        print(f"could not capture the monitor: {error}", file=sys.stderr)
    except StartupError as error:
        print(str(error), file=sys.stderr)
    except xr.exception.XrException as error:
        print(
            f"the headset session failed ({type(error).__name__}: {error}). "
            "Check that the headset is connected and that an OpenXR runtime is active.",
            file=sys.stderr,
        )
    return EXIT_PROBLEM


def _check() -> int:
    """Requirements on this computer, then the libraries that come with the app."""
    import importlib

    from .prerequisites import check_all

    failed = False
    for check in check_all():
        print(f"{check.key}: {'ok' if check.ok else 'missing, see ' + check.url} {check.detail}".rstrip())
    for name in ("xr", "glfw", "OpenGL.GL", "vgamepad"):
        try:
            importlib.import_module(name)
        except Exception as error:  # any failure here is the answer the person needs
            if DRIVER_MISSING_MARK in str(error):
                # The gamepad library loaded and asked for its driver, which is reported above.
                print(f"library {name}: ok (its driver is missing)")
                continue
            failed = True
            print(f"library {name}: failed ({type(error).__name__}: {error})")
        else:
            print(f"library {name}: ok")
    return EXIT_PROBLEM if failed else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    known = {"run", "settings", "check", "monitors", "window", "bench", "-h", "--help"}
    if not arguments or arguments[0] not in known:
        arguments.insert(0, "run")  # plain "vr-gyro-screen [options]" means run
    args = _parser().parse_args(arguments)

    if sys.platform != "win32":
        print("vr-gyro-screen only runs on Windows", file=sys.stderr)
        return EXIT_PROBLEM

    if args.command == "settings":
        from .gui import open_window

        return open_window()

    if args.command == "check":
        return _check()

    from .monitors import MonitorNotFoundError, choose_monitor, list_monitors

    try:
        if args.command == "monitors":
            selector = args.monitor or load_config(args.config).screen.monitor
            monitors = list_monitors()
            chosen = choose_monitor(monitors, selector)
            for monitor in monitors:
                marks = [mark for mark, on in (("primary", monitor.primary), ("selected", monitor == chosen)) if on]
                print(f"{monitor.index}: {monitor.label}{'  [' + ', '.join(marks) + ']' if marks else ''}")
            return EXIT_OK
        if args.command == "window":
            from .window import send_to_monitor

            monitor = choose_monitor(list_monitors(), args.monitor)
            print(f"target monitor: {monitor.label}", flush=True)
            return send_to_monitor(args.title, monitor, args.fullscreen_key, args.wait)
        if args.command == "bench":
            if args.rate <= 0 or not args.seconds > 0:
                raise ConfigError("--rate and --seconds must be greater than zero")
            from .bench import bench_all

            monitor = choose_monitor(list_monitors(), args.monitor)
            print(f"monitor: {monitor.label}", flush=True)
            backends = args.backend or ["gpu", "direct", "dxcam"]
            return bench_all(monitor, backends, args.seconds, args.rate, not args.no_mipmaps)
        return _run(args)
    except ConfigError as error:
        print(f"configuration problem: {error}", file=sys.stderr)
        return EXIT_USAGE
    except MonitorNotFoundError as error:
        print(str(error), file=sys.stderr)
        return EXIT_PROBLEM


if __name__ == "__main__":
    raise SystemExit(main())
