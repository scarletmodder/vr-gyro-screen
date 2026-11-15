"""Desktop Duplication (DXGI) and Direct3D 11 through plain ctypes.

Only the handful of COM methods the capture needs are called, by vtable index, so the
package needs no COM helper library. Index comments name the method being called.
"""

from __future__ import annotations

import ctypes
import uuid
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any

DXGI_ERROR_WAIT_TIMEOUT = 0x887A0027
DXGI_ERROR_NOT_FOUND = 0x887A0002

DXGI_FORMAT_B8G8R8A8_UNORM = 87
DXGI_FORMAT_B8G8R8A8_UNORM_SRGB = 91
D3D11_SDK_VERSION = 7
D3D11_CREATE_DEVICE_BGRA_SUPPORT = 0x20
D3D11_USAGE_DEFAULT = 0
D3D11_USAGE_STAGING = 3
D3D11_BIND_SHADER_RESOURCE = 0x8
D3D11_BIND_RENDER_TARGET = 0x20
D3D11_CPU_ACCESS_READ = 0x20000
D3D11_MAP_READ = 1


class CaptureLostError(RuntimeError):
    """The monitor or the graphics device went away; the capture must be reopened."""


class GUID(ctypes.Structure):
    _fields_ = (
        ("data1", ctypes.c_uint32),
        ("data2", ctypes.c_uint16),
        ("data3", ctypes.c_uint16),
        ("data4", ctypes.c_ubyte * 8),
    )


def _guid(text: str) -> GUID:
    return GUID.from_buffer_copy(uuid.UUID(text).bytes_le)


IID_IDXGIFactory1 = _guid("770aae78-f26f-4dba-a829-253c83d1b387")
IID_IDXGIOutput1 = _guid("00cddea8-939b-4b83-a340-a685226666cc")
IID_ID3D11Texture2D = _guid("6f15aaf2-d208-4e89-9ab4-489535d34f9c")


class _OutputDesc(ctypes.Structure):
    _fields_ = (
        ("device_name", ctypes.c_wchar * 32),
        ("desktop_coordinates", wintypes.RECT),
        ("attached_to_desktop", wintypes.BOOL),
        ("rotation", ctypes.c_uint),
        ("monitor", wintypes.HMONITOR),
    )


class _Rational(ctypes.Structure):
    _fields_ = (("numerator", ctypes.c_uint), ("denominator", ctypes.c_uint))


class _ModeDesc(ctypes.Structure):
    _fields_ = (
        ("width", ctypes.c_uint),
        ("height", ctypes.c_uint),
        ("refresh_rate", _Rational),
        ("format", ctypes.c_uint),
        ("scanline_ordering", ctypes.c_uint),
        ("scaling", ctypes.c_uint),
    )


_ROTATION_UNSPECIFIED, _ROTATION_IDENTITY = 0, 1


class _OutduplDesc(ctypes.Structure):
    _fields_ = (
        ("mode_desc", _ModeDesc),
        ("rotation", ctypes.c_uint),
        ("desktop_image_in_system_memory", wintypes.BOOL),
    )


class _PointerPosition(ctypes.Structure):
    _fields_ = (("position", wintypes.POINT), ("visible", wintypes.BOOL))


class _FrameInfo(ctypes.Structure):
    _fields_ = (
        ("last_present_time", ctypes.c_int64),
        ("last_mouse_update_time", ctypes.c_int64),
        ("accumulated_frames", ctypes.c_uint),
        ("rects_coalesced", wintypes.BOOL),
        ("protected_content_masked_out", wintypes.BOOL),
        ("pointer_position", _PointerPosition),
        ("total_metadata_buffer_size", ctypes.c_uint),
        ("pointer_shape_buffer_size", ctypes.c_uint),
    )


class _SampleDesc(ctypes.Structure):
    _fields_ = (("count", ctypes.c_uint), ("quality", ctypes.c_uint))


class _Texture2DDesc(ctypes.Structure):
    _fields_ = (
        ("width", ctypes.c_uint),
        ("height", ctypes.c_uint),
        ("mip_levels", ctypes.c_uint),
        ("array_size", ctypes.c_uint),
        ("format", ctypes.c_uint),
        ("sample_desc", _SampleDesc),
        ("usage", ctypes.c_uint),
        ("bind_flags", ctypes.c_uint),
        ("cpu_access_flags", ctypes.c_uint),
        ("misc_flags", ctypes.c_uint),
    )


class _MappedSubresource(ctypes.Structure):
    _fields_ = (
        ("data", ctypes.c_void_p),
        ("row_pitch", ctypes.c_uint),
        ("depth_pitch", ctypes.c_uint),
    )


def _failed(hr: int) -> bool:
    return hr < 0


def _check(hr: int, what: str) -> None:
    if _failed(hr):
        raise CaptureLostError(f"{what} failed (HRESULT 0x{hr & 0xFFFFFFFF:08X})")


class ComPtr:
    """Owning pointer to a COM object, with calls by vtable index."""

    def __init__(self, pointer: int) -> None:
        self.pointer = pointer

    def __bool__(self) -> bool:
        return bool(self.pointer)

    def method(self, index: int, *argtypes: Any, restype: Any = ctypes.c_long) -> Callable[..., Any]:
        vtable = ctypes.cast(self.pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
        function = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtable[index])
        pointer = self.pointer

        def call(*args: Any) -> Any:
            return function(pointer, *args)

        return call

    def query(self, iid: GUID) -> ComPtr:
        out = ctypes.c_void_p()
        hr = self.method(0, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))(  # QueryInterface
            ctypes.byref(iid), ctypes.byref(out)
        )
        _check(hr, "QueryInterface")
        return ComPtr(out.value or 0)

    def release(self) -> None:
        if self.pointer:
            self.method(2, restype=ctypes.c_ulong)()  # Release
            self.pointer = 0


@dataclass(frozen=True)
class OutputInfo:
    """One monitor as DXGI sees it."""

    device_name: str
    adapter_index: int
    output_index: int


def _factory() -> ComPtr:
    out = ctypes.c_void_p()
    create = ctypes.WinDLL("dxgi").CreateDXGIFactory1
    create.restype = ctypes.c_long
    create.argtypes = (ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))
    _check(create(ctypes.byref(IID_IDXGIFactory1), ctypes.byref(out)), "CreateDXGIFactory1")
    return ComPtr(out.value or 0)


def _enumerate(factory: ComPtr) -> list[tuple[OutputInfo, ComPtr, ComPtr]]:
    """Every (info, adapter, output); the caller releases the pointers it does not keep."""
    found: list[tuple[OutputInfo, ComPtr, ComPtr]] = []
    enum_adapters = factory.method(12, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p))  # EnumAdapters1
    adapter_index = 0
    while True:
        raw_adapter = ctypes.c_void_p()
        if _failed(enum_adapters(adapter_index, ctypes.byref(raw_adapter))):
            break
        adapter = ComPtr(raw_adapter.value or 0)
        enum_outputs = adapter.method(7, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p))  # EnumOutputs
        output_index = 0
        while True:
            raw_output = ctypes.c_void_p()
            if _failed(enum_outputs(output_index, ctypes.byref(raw_output))):
                break
            output = ComPtr(raw_output.value or 0)
            desc = _OutputDesc()
            output.method(7, ctypes.POINTER(_OutputDesc))(ctypes.byref(desc))  # GetDesc
            adapter.method(1, restype=ctypes.c_ulong)()  # AddRef: each entry owns its adapter reference
            info = OutputInfo(desc.device_name, adapter_index, output_index)
            found.append((info, ComPtr(adapter.pointer), output))
            output_index += 1
        adapter.release()
        adapter_index += 1
    return found


def list_outputs() -> list[OutputInfo]:
    factory = _factory()
    try:
        entries = _enumerate(factory)
        for _, adapter, output in entries:
            output.release()
            adapter.release()
        return [info for info, _, _ in entries]
    finally:
        factory.release()


class Duplicator:
    """Duplicates one monitor into a texture this object owns.

    cpu_readable=True keeps a staging texture that can be mapped (one copy to system memory).
    cpu_readable=False keeps a regular texture meant to be shared with the renderer, so the
    image never leaves the graphics card.
    """

    def __init__(self, device_name: str, *, cpu_readable: bool, srgb: bool = False) -> None:
        self.device = ComPtr(0)
        self.context = ComPtr(0)
        self.duplication = ComPtr(0)
        self.texture = ComPtr(0)
        self._mapped = False
        factory = _factory()
        try:
            adapter, output = self._find(factory, device_name)
        finally:
            factory.release()
        try:
            self._create_device(adapter)
            output1 = output.query(IID_IDXGIOutput1)
            try:
                raw = ctypes.c_void_p()
                hr = output1.method(22, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))(  # DuplicateOutput
                    self.device.pointer, ctypes.byref(raw)
                )
                _check(hr, "DuplicateOutput")
                self.duplication = ComPtr(raw.value or 0)
            finally:
                output1.release()
            desc = _OutduplDesc()
            self.duplication.method(7, ctypes.POINTER(_OutduplDesc), restype=None)(ctypes.byref(desc))  # GetDesc
            if desc.rotation not in (_ROTATION_UNSPECIFIED, _ROTATION_IDENTITY):
                raise CaptureLostError("rotated monitors are not supported")
            self.width = int(desc.mode_desc.width)
            self.height = int(desc.mode_desc.height)
            rate = desc.mode_desc.refresh_rate
            self.refresh_hz = rate.numerator / rate.denominator if rate.denominator else 0.0
            self._create_texture(cpu_readable, srgb)
        except Exception:
            self.close()
            raise
        finally:
            output.release()
            adapter.release()
        self._acquire = self.duplication.method(  # AcquireNextFrame
            8, ctypes.c_uint, ctypes.POINTER(_FrameInfo), ctypes.POINTER(ctypes.c_void_p)
        )
        self._release_frame = self.duplication.method(14)  # ReleaseFrame
        self._copy = self.context.method(47, ctypes.c_void_p, ctypes.c_void_p, restype=None)  # CopyResource
        self._map = self.context.method(  # Map
            14, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(_MappedSubresource)
        )
        self._unmap = self.context.method(15, ctypes.c_void_p, ctypes.c_uint, restype=None)  # Unmap
        self._info = _FrameInfo()

    @staticmethod
    def _find(factory: ComPtr, device_name: str) -> tuple[ComPtr, ComPtr]:
        chosen: tuple[ComPtr, ComPtr] | None = None
        for info, adapter, output in _enumerate(factory):
            if chosen is None and info.device_name.lower() == device_name.lower():
                chosen = (adapter, output)
            else:
                output.release()
                adapter.release()
        if chosen is None:
            raise CaptureLostError(f"monitor {device_name} is not available to the graphics card")
        return chosen

    def _create_device(self, adapter: ComPtr) -> None:
        create = ctypes.WinDLL("d3d11").D3D11CreateDevice
        create.restype = ctypes.c_long
        create.argtypes = (
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_void_p),
        )
        device = ctypes.c_void_p()
        context = ctypes.c_void_p()
        level = ctypes.c_uint()
        # Driver type 0 (unknown) is mandatory when an explicit adapter is given.
        hr = create(
            adapter.pointer,
            0,
            None,
            D3D11_CREATE_DEVICE_BGRA_SUPPORT,
            None,
            0,
            D3D11_SDK_VERSION,
            ctypes.byref(device),
            ctypes.byref(level),
            ctypes.byref(context),
        )
        _check(hr, "D3D11CreateDevice")
        self.device = ComPtr(device.value or 0)
        self.context = ComPtr(context.value or 0)

    def _create_texture(self, cpu_readable: bool, srgb: bool) -> None:
        desc = _Texture2DDesc()
        desc.width, desc.height = self.width, self.height
        desc.mip_levels = desc.array_size = 1
        desc.format = DXGI_FORMAT_B8G8R8A8_UNORM_SRGB if srgb else DXGI_FORMAT_B8G8R8A8_UNORM
        desc.sample_desc.count = 1
        if cpu_readable:
            desc.usage = D3D11_USAGE_STAGING
            desc.cpu_access_flags = D3D11_CPU_ACCESS_READ
        else:
            desc.usage = D3D11_USAGE_DEFAULT
            desc.bind_flags = D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_RENDER_TARGET
        raw = ctypes.c_void_p()
        hr = self.device.method(  # CreateTexture2D
            5, ctypes.POINTER(_Texture2DDesc), ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
        )(ctypes.byref(desc), None, ctypes.byref(raw))
        _check(hr, "CreateTexture2D")
        self.texture = ComPtr(raw.value or 0)

    def acquire(
        self,
        timeout_ms: int = 0,
        before_copy: Callable[[], None] | None = None,
        after_copy: Callable[[], None] | None = None,
    ) -> bool:
        """Copy the newest desktop image into the owned texture. False when nothing changed."""
        if not self.duplication:
            raise CaptureLostError("the capture is closed")
        resource = ctypes.c_void_p()
        hr = self._acquire(timeout_ms, ctypes.byref(self._info), ctypes.byref(resource))
        if hr & 0xFFFFFFFF == DXGI_ERROR_WAIT_TIMEOUT:
            return False
        _check(hr, "AcquireNextFrame")
        frame = ComPtr(resource.value or 0)
        try:
            if self._info.last_present_time == 0:
                return False  # only the mouse pointer moved; the image is the same
            texture = frame.query(IID_ID3D11Texture2D)
            try:
                if before_copy is not None:
                    before_copy()
                try:
                    self._copy(self.texture.pointer, texture.pointer)
                finally:
                    if after_copy is not None:
                        after_copy()
            finally:
                texture.release()
            return True
        finally:
            frame.release()
            self._release_frame()

    def map(self) -> tuple[int, int]:
        """Address and row pitch of the image in system memory (cpu_readable only)."""
        mapped = _MappedSubresource()
        _check(self._map(self.texture.pointer, 0, D3D11_MAP_READ, 0, ctypes.byref(mapped)), "Map")
        self._mapped = True
        return int(mapped.data or 0), int(mapped.row_pitch)

    def unmap(self) -> None:
        if self._mapped:
            self._unmap(self.texture.pointer, 0)
            self._mapped = False

    def close(self) -> None:
        if self.texture:
            self.unmap()
        for pointer in (self.texture, self.duplication, self.context, self.device):
            pointer.release()
