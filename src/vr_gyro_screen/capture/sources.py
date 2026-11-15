"""Frame sources: each one keeps an OpenGL texture with the newest image of a monitor.

All of them must be created and polled on the thread that owns the OpenGL context.
The texture is stored top row first, which OpenGL reads as upside down; the renderer
flips it on the graphics card when it copies the image to the headset.

- GpuSource: the image stays on the graphics card (shared Direct3D texture). No copy
  through the processor. Needs the WGL_NV_DX_interop2 driver extension.
- DirectSource: one copy through system memory per new frame, no helper threads.
- DxcamSource: the original path, through the dxcam library and a background thread.
  Several copies per frame; kept as a fallback and for comparison.
"""

from __future__ import annotations

import ctypes
import threading
import time
from abc import ABC, abstractmethod
from typing import Any

from OpenGL import GL

from .dxgi import CaptureLostError, Duplicator, list_outputs

GL_SRGB8_ALPHA8 = 0x8C43
FIRST_FRAME_MS = 500  # how long to wait for the first image when opening
WGL_ACCESS_READ_ONLY_NV = 0x0000


class CaptureUnavailableError(RuntimeError):
    """This backend cannot run on this machine; another one should be tried."""


class FrameSource(ABC):
    """A monitor image kept in an OpenGL texture."""

    name: str
    width: int
    height: int
    texture: int

    @abstractmethod
    def poll(self) -> bool:
        """Bring the texture up to date. True when the image changed."""

    @abstractmethod
    def close(self) -> None:
        """Free everything. Safe to call more than once."""


def _new_texture(internal_format: int, width: int, height: int) -> int:
    texture = int(GL.glGenTextures(1))
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
    GL.glTexStorage2D(GL.GL_TEXTURE_2D, 1, internal_format, width, height)
    GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
    return texture


class DirectSource(FrameSource):
    name = "direct"

    def __init__(self, device_name: str, internal_format: int) -> None:
        self.texture = 0
        self._duplicator = Duplicator(device_name, cpu_readable=True)
        self.width, self.height = self._duplicator.width, self._duplicator.height
        try:
            self.texture = _new_texture(internal_format, self.width, self.height)
            # A desktop that is not changing may give no first image in time; the texture
            # then fills in on the first change, and nothing unread is uploaded.
            if self._duplicator.acquire(timeout_ms=FIRST_FRAME_MS):
                self._upload()
        except Exception:
            self.close()
            raise

    def _upload(self) -> None:
        address, pitch = self._duplicator.map()
        try:
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)
            GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 4)
            # Rows in the mapped image may be padded; tell OpenGL the real row length.
            GL.glPixelStorei(GL.GL_UNPACK_ROW_LENGTH, pitch // 4)
            GL.glTexSubImage2D(
                GL.GL_TEXTURE_2D,
                0,
                0,
                0,
                self.width,
                self.height,
                GL.GL_BGRA,
                GL.GL_UNSIGNED_BYTE,
                ctypes.c_void_p(address),
            )
            GL.glPixelStorei(GL.GL_UNPACK_ROW_LENGTH, 0)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        finally:
            self._duplicator.unmap()

    def poll(self) -> bool:
        if not self._duplicator.acquire():
            return False
        self._upload()
        return True

    def close(self) -> None:
        self._duplicator.close()
        if self.texture:
            GL.glDeleteTextures([self.texture])
            self.texture = 0


class GpuSource(FrameSource):
    name = "gpu"

    def __init__(self, device_name: str) -> None:
        try:
            from OpenGL.raw.WGL import _types as wgl_types
            from OpenGL.WGL.NV import DX_interop as interop
        except ImportError as error:  # pragma: no cover - depends on the OpenGL package build
            raise CaptureUnavailableError(f"texture sharing is not available ({error})") from error
        self._interop: Any = interop
        self._device_handle: Any = None
        self._object_handle: Any = None
        self._handles: Any = None
        self._locked = False
        self.texture = 0
        if not bool(interop.wglDXOpenDeviceNV):
            raise CaptureUnavailableError("the graphics driver does not offer WGL_NV_DX_interop2")
        # The shared texture stays in the plain (non sRGB) format: the driver then hands the
        # stored values over untouched, exactly like the processor path. With the sRGB format
        # the copy came out darker (measured: 117 became 45).
        self._duplicator = Duplicator(device_name, cpu_readable=False)
        self.width, self.height = self._duplicator.width, self._duplicator.height
        try:
            self._device_handle = interop.wglDXOpenDeviceNV(ctypes.c_void_p(self._duplicator.device.pointer))
            if not self._device_handle:
                raise CaptureUnavailableError("the graphics driver refused to share the Direct3D device")
            self.texture = int(GL.glGenTextures(1))
            self._object_handle = interop.wglDXRegisterObjectNV(
                self._device_handle,
                ctypes.c_void_p(self._duplicator.texture.pointer),
                self.texture,
                GL.GL_TEXTURE_2D,
                WGL_ACCESS_READ_ONLY_NV,
            )
            if not self._object_handle:
                raise CaptureUnavailableError("the graphics driver refused to share the texture")
            self._handles = (wgl_types.HANDLE * 1)(self._object_handle)
            self._duplicator.acquire(timeout_ms=FIRST_FRAME_MS)
            self._lock()
        except Exception:
            self.close()
            raise

    def _lock(self) -> None:
        if not self._locked:
            if not self._interop.wglDXLockObjectsNV(self._device_handle, 1, self._handles):
                raise CaptureLostError("could not lock the shared texture")
            self._locked = True

    def _unlock(self) -> None:
        if self._locked:
            self._interop.wglDXUnlockObjectsNV(self._device_handle, 1, self._handles)
            self._locked = False

    def poll(self) -> bool:
        # Direct3D may only write to the texture while OpenGL is not holding it.
        return self._duplicator.acquire(before_copy=self._unlock, after_copy=self._lock)

    def close(self) -> None:
        if self._device_handle:
            if self._object_handle:
                self._unlock()
                self._interop.wglDXUnregisterObjectNV(self._device_handle, self._object_handle)
                self._object_handle = None
            self._interop.wglDXCloseDeviceNV(self._device_handle)
            self._device_handle = None
        if self.texture:
            GL.glDeleteTextures([self.texture])
            self.texture = 0
        self._duplicator.close()


class DxcamSource(FrameSource):
    name = "dxcam"

    STALE_SECONDS = 3.0

    def __init__(self, adapter_index: int, output_index: int, internal_format: int, fps: int) -> None:
        self.texture = 0
        self._alive = False
        self._camera: Any = None
        try:
            import dxcam
        except ImportError as error:
            raise CaptureUnavailableError(
                'the dxcam backend needs the optional package: pip install "vr-gyro-screen[dxcam]"'
            ) from error
        try:
            self._camera = dxcam.create(device_idx=adapter_index, output_idx=output_index, output_color="BGRA")
            if self._camera is None:
                raise CaptureLostError("dxcam did not open the monitor")
            self._camera.start(target_fps=fps, video_mode=True)
            first = self._camera.get_latest_frame()
            if first is None:
                raise CaptureLostError("dxcam gave no image")
            self.height, self.width = (int(side) for side in first.shape[:2])
            self.texture = _new_texture(internal_format, self.width, self.height)
        except CaptureLostError:
            self.close()
            raise
        except Exception as error:
            # dxcam keeps one camera per monitor: left running, the next attempt would get
            # the same broken one back.
            self.close()
            raise CaptureLostError(f"dxcam could not open the monitor ({error})") from error
        self._lock = threading.Lock()
        self._frame: Any = first
        self._frame_id = 1
        self._shown_id = 0
        self._last_new = time.perf_counter()
        self._alive = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while self._alive:
            try:
                frame = self._camera.get_latest_frame()
            except Exception:
                return  # poll() notices the stale image and reports the loss
            if frame is None or frame.shape[:2] != (self.height, self.width):
                continue
            with self._lock:
                self._frame = frame
                self._frame_id += 1
                self._last_new = time.perf_counter()

    def poll(self) -> bool:
        with self._lock:
            frame_id, frame, last_new = self._frame_id, self._frame, self._last_new
        if time.perf_counter() - last_new > self.STALE_SECONDS:
            raise CaptureLostError("the monitor image stopped")
        if frame_id == self._shown_id:
            return False
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 4)
        GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, self.width, self.height, GL.GL_BGRA, GL.GL_UNSIGNED_BYTE, frame)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        self._shown_id = frame_id
        return True

    def close(self) -> None:
        self._alive = False
        try:
            if self._camera is not None:
                self._camera.stop()
                self._camera.release()
        except Exception:  # noqa: S110 - the device may already be gone, nothing left to free
            pass
        if self.texture:
            GL.glDeleteTextures([self.texture])
            self.texture = 0


def open_source(backend: str, device_name: str, internal_format: int, fps: int) -> FrameSource:
    """Open the requested backend; "auto" tries the cheapest first."""
    if backend == "dxcam":
        for output in list_outputs():
            if output.device_name.lower() == device_name.lower():
                return DxcamSource(output.adapter_index, output.output_index, internal_format, fps)
        raise CaptureLostError(f"{device_name} is not available to the capture")
    if backend == "direct":
        return DirectSource(device_name, internal_format)
    if backend == "gpu":
        return GpuSource(device_name)
    try:
        return GpuSource(device_name)
    except CaptureUnavailableError as error:
        print(f"capture: staying on the processor path ({error})", flush=True)
        return DirectSource(device_name, internal_format)
