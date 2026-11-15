"""Capture benchmark: processor cost of each backend, without a headset.

It opens a small window on the chosen monitor that changes colour every cycle, so the
desktop produces a new image each refresh, and runs the same work the headset loop does
(bring the image into a texture, copy it flipped, build mipmaps).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import glfw
from OpenGL import GL

from .capture.sources import GL_SRGB8_ALPHA8, CaptureUnavailableError, FrameSource, open_source
from .monitors import Monitor


@dataclass(frozen=True)
class BenchResult:
    backend: str
    seconds: float
    cycles: int
    new_frames: int
    cpu_seconds: float
    sample: tuple[int, int, int]

    @property
    def cpu_percent_of_one_core(self) -> float:
        return 100.0 * self.cpu_seconds / self.seconds if self.seconds else 0.0


def run_bench(monitor: Monitor, backend: str, seconds: float, rate_hz: int, mipmaps: bool) -> BenchResult:
    if not glfw.init():
        raise RuntimeError("could not start GLFW")
    glfw.window_hint(glfw.DECORATED, glfw.FALSE)
    glfw.window_hint(glfw.FLOATING, glfw.TRUE)
    window = glfw.create_window(160, 90, "vr-gyro-screen bench", None, None)
    source: FrameSource | None = None
    try:
        glfw.set_window_pos(window, monitor.left + 40, monitor.top + 40)
        glfw.make_context_current(window)
        glfw.swap_interval(0)
        source = open_source(backend, monitor.device_name, GL_SRGB8_ALPHA8, rate_hz)
        width, height = source.width, source.height
        levels = max(width, height).bit_length() if mipmaps else 1
        target = int(GL.glGenTextures(1))
        GL.glBindTexture(GL.GL_TEXTURE_2D, target)
        GL.glTexStorage2D(GL.GL_TEXTURE_2D, levels, GL_SRGB8_ALPHA8, width, height)
        read_fbo, draw_fbo = (int(name) for name in GL.glGenFramebuffers(2))
        GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, draw_fbo)
        GL.glFramebufferTexture2D(GL.GL_DRAW_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, target, 0)
        GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, 0)

        period = 1.0 / rate_hz
        cycles = new_frames = 0
        started = time.perf_counter()
        cpu_started = time.process_time()
        deadline = started
        while time.perf_counter() - started < seconds:
            shade = (cycles % 64) / 64.0
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
            GL.glClearColor(shade, 1.0 - shade, 0.5, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            glfw.swap_buffers(window)
            glfw.poll_events()
            if source.poll():
                new_frames += 1
                GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, read_fbo)
                GL.glFramebufferTexture2D(
                    GL.GL_READ_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, source.texture, 0
                )
                GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, draw_fbo)
                GL.glBlitFramebuffer(0, 0, width, height, 0, height, width, 0, GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)
                GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, 0)
                GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, 0)
                if mipmaps:
                    GL.glBindTexture(GL.GL_TEXTURE_2D, target)
                    GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
                    GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
            cycles += 1
            deadline += period
            pause = deadline - time.perf_counter()
            if pause > 0:
                time.sleep(pause)
        GL.glFinish()
        cpu = time.process_time() - cpu_started
        elapsed = time.perf_counter() - started
        # One pixel from the middle of the copied image, to confirm real content arrived.
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, draw_fbo)
        pixel = GL.glReadPixels(width // 2, height // 2, 1, 1, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, 0)
        raw = bytes(pixel)
        return BenchResult(source.name, elapsed, cycles, new_frames, cpu, (raw[0], raw[1], raw[2]))
    finally:
        if source is not None:
            source.close()
        glfw.destroy_window(window)
        glfw.terminate()


def describe(result: BenchResult) -> str:
    return (
        f"{result.backend}: {result.new_frames} new images in {result.seconds:.1f} s "
        f"({result.new_frames / result.seconds:.0f} per second), processor "
        f"{result.cpu_percent_of_one_core:.0f}% of one core, middle pixel {result.sample}"
    )


def bench_all(monitor: Monitor, backends: list[str], seconds: float, rate_hz: int, mipmaps: bool) -> int:
    failures = 0
    for backend in backends:
        try:
            print(describe(run_bench(monitor, backend, seconds, rate_hz, mipmaps)), flush=True)
        except CaptureUnavailableError as error:
            print(f"{backend}: not available here ({error})", flush=True)
        except Exception as error:
            failures += 1
            print(f"{backend}: failed ({error})", flush=True)
    return 1 if failures else 0
