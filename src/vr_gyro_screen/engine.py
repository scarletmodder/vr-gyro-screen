"""Runs the part that talks to the headset as a separate process, for the settings window.

A separate process keeps the window responsive and lets a crash in the headset session be
shown as a message instead of closing the window. Stopping is asked through a file, because
on Windows a process ended from outside gets no chance to release the gamepad buttons.
"""

from __future__ import annotations

import contextlib
import locale
import queue
import subprocess
import sys
import threading
from pathlib import Path

CONSOLE_PROGRAM = "vr-gyro-screen-cli.exe"  # sits next to the window program when installed
STOP_FILE_NAME = "stop-request"
STOP_PATIENCE_S = 5.0  # how long a stop request may take before the engine is ended from outside


def engine_command(stop_file: Path, distance_m: float | None = None) -> list[str]:
    """The command that starts the engine, for an installed copy or for a source checkout."""
    arguments = ["run", "--quiet", "--stop-file", str(stop_file)]
    if distance_m is not None:
        arguments += ["--distance", f"{distance_m:g}"]
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).with_name(CONSOLE_PROGRAM)), *arguments]
    return [sys.executable, "-u", "-m", "vr_gyro_screen", *arguments]


def _job_that_ends_with_this_process() -> int | None:
    """A Windows job whose processes are ended when this process goes away, however it goes.

    Without it, a window that crashed or was ended from the Task Manager would leave the engine
    running: holding the gamepad and the headset session, with nothing on screen to stop it.
    """
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = (
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        )

    class ExtendedLimits(ctypes.Structure):
        _fields_ = (
            ("BasicLimitInformation", BasicLimits),
            ("IoInfo", ctypes.c_uint64 * 6),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        )

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    limits = ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    extended_limit_information = 9
    if not kernel32.SetInformationJobObject(
        job, extended_limit_information, ctypes.byref(limits), ctypes.sizeof(limits)
    ):
        return None
    return int(job)  # never closed on purpose: Windows closes it when this process ends


def _add_to_job(job: int, process_id: int) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    set_quota_and_terminate = 0x0100 | 0x0001
    handle = kernel32.OpenProcess(set_quota_and_terminate, False, process_id)
    if handle:
        kernel32.AssignProcessToJobObject(job, handle)
        kernel32.CloseHandle(handle)


class Engine:
    """One engine process at a time. Output lines arrive in `lines`; None marks the end."""

    def __init__(self, stop_file: Path) -> None:
        self.stop_file = stop_file
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.stop_requested = False  # True when the engine that ran last was asked to stop
        self._process: subprocess.Popen[bytes] | None = None
        self._job = _job_that_ends_with_this_process()

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def exit_code(self) -> int | None:
        return None if self._process is None else self._process.poll()

    def start(self, distance_m: float | None = None) -> None:
        if self.running:
            return
        self.stop_requested = False
        self.stop_file.parent.mkdir(parents=True, exist_ok=True)
        self.stop_file.unlink(missing_ok=True)
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        # The command is this program itself (see engine_command), never text typed by someone.
        process = subprocess.Popen(  # noqa: S603
            engine_command(self.stop_file, distance_m),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
        self._process = process
        if self._job is not None:
            _add_to_job(self._job, process.pid)
        threading.Thread(target=self._read, args=(process,), daemon=True).start()

    def _read(self, process: subprocess.Popen[bytes]) -> None:
        try:
            encoding = locale.getpreferredencoding(False)
            if process.stdout is not None:
                for raw in process.stdout:
                    self.lines.put(raw.decode(encoding, errors="replace").rstrip())
            process.wait()
            with contextlib.suppress(OSError):  # another program may be holding the file for a moment
                self.stop_file.unlink(missing_ok=True)
        finally:
            self.lines.put(None)  # whatever happened above, the window must learn that it ended

    def request_stop(self, patience_s: float = STOP_PATIENCE_S) -> None:
        """Ask the engine to close by itself (it releases the gamepad and saves the screen).

        An engine that does not answer in time is ended from outside. The wait is tied to the
        process that was asked, so an engine started right after is never the one that is ended.
        """
        process = self._process
        if process is None or process.poll() is not None or self.stop_requested:
            return
        self.stop_requested = True
        with contextlib.suppress(OSError):
            self.stop_file.write_text("stop\n", encoding="utf-8")
        threading.Thread(target=self._end_after, args=(process, patience_s), daemon=True).start()

    @staticmethod
    def _end_after(process: subprocess.Popen[bytes], patience_s: float) -> None:
        try:
            process.wait(patience_s)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(OSError):
                process.kill()
