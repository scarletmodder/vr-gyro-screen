"""The OpenXR side: reading the controllers and showing the monitor image on a floating screen."""

from __future__ import annotations

import ctypes
import time
from typing import Any

import xr
from OpenGL import GL

from .capture.sources import GL_SRGB8_ALPHA8
from .mapping import ControllerState
from .quaternion import Quat, Vec3

GL_RGBA8 = 0x8058

RECENTER_SETTLE_S = 0.3  # let the headset's own recenter take effect before placing the screen

_CONTROLLER_PATHS: dict[str, tuple[str, str]] = {
    "left_stick": ("vec2", "/user/hand/left/input/thumbstick"),
    "right_stick": ("vec2", "/user/hand/right/input/thumbstick"),
    "left_stick_click": ("bool", "/user/hand/left/input/thumbstick/click"),
    "right_stick_click": ("bool", "/user/hand/right/input/thumbstick/click"),
    "a": ("bool", "/user/hand/right/input/a/click"),
    "b": ("bool", "/user/hand/right/input/b/click"),
    "x": ("bool", "/user/hand/left/input/x/click"),
    "y": ("bool", "/user/hand/left/input/y/click"),
    "menu": ("bool", "/user/hand/left/input/menu/click"),
    "left_trigger": ("float", "/user/hand/left/input/trigger/value"),
    "right_trigger": ("float", "/user/hand/right/input/trigger/value"),
    "left_squeeze": ("float", "/user/hand/left/input/squeeze/value"),
    "right_squeeze": ("float", "/user/hand/right/input/squeeze/value"),
    "left_aim": ("pose", "/user/hand/left/input/aim/pose"),
    "right_aim": ("pose", "/user/hand/right/input/aim/pose"),
}
_ACTION_TYPES = {
    "vec2": xr.ActionType.VECTOR2F_INPUT,
    "bool": xr.ActionType.BOOLEAN_INPUT,
    "float": xr.ActionType.FLOAT_INPUT,
    "pose": xr.ActionType.POSE_INPUT,
}


class RecenterWatch:
    """Notices when the headset's own recenter runs (holding the system button).

    The runtime then moves the origin of the tracking space, and a screen anchored to the
    old origin ends up off to the side. The helper loop of the OpenXR binding drops that
    event, so the event poll is wrapped here to catch it.
    """

    def __init__(self) -> None:
        self._due: float | None = None
        original = self._original = xr.poll_event

        def watch(instance: Any) -> Any:
            event = original(instance)
            pending = xr.StructureType.EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING
            if xr.StructureType(event.type) == pending:
                self._due = time.perf_counter() + RECENTER_SETTLE_S
            return event

        xr.poll_event = watch

    def close(self) -> None:
        """Put the binding's own event poll back."""
        xr.poll_event = self._original

    def take(self, now: float) -> bool:
        """True once, shortly after a recenter happened."""
        if self._due is not None and now >= self._due:
            self._due = None
            return True
        return False


class ControllerReader:
    """Reads both controllers and the head pose once per frame.

    Only the "is active" flag of each input is trusted. Checking which interaction profile
    is bound was tried, to mute hand tracking pinches, and it silenced real controllers on
    some runtimes; turning hand tracking off in the headset is the reliable fix.
    """

    def __init__(self, context: Any) -> None:
        self._context = context
        instance = context.instance
        self._action_set = context.default_action_set
        self._actions: dict[str, tuple[str, Any]] = {}
        bindings = []
        for name, (kind, path) in _CONTROLLER_PATHS.items():
            action = xr.create_action(
                self._action_set,
                xr.ActionCreateInfo(
                    action_type=_ACTION_TYPES[kind],
                    action_name=name.replace("_", "-"),
                    localized_action_name=name,
                ),
            )
            self._actions[name] = (kind, action)
            bindings.append(xr.ActionSuggestedBinding(action, xr.string_to_path(instance, path)))
        xr.suggest_interaction_profile_bindings(
            instance,
            xr.InteractionProfileSuggestedBinding(
                interaction_profile=xr.string_to_path(instance, "/interaction_profiles/oculus/touch_controller"),
                count_suggested_bindings=len(bindings),
                suggested_bindings=(xr.ActionSuggestedBinding * len(bindings))(*bindings),
            ),
        )
        self._spaces = {
            name: xr.create_action_space(context.session, xr.ActionSpaceCreateInfo(action=action))
            for name, (kind, action) in self._actions.items()
            if kind == "pose"
        }
        self._view_space = xr.create_reference_space(
            context.session, xr.ReferenceSpaceCreateInfo(reference_space_type=xr.ReferenceSpaceType.VIEW)
        )

    def read(self, display_time: Any) -> ControllerState:
        session = self._context.session
        xr.sync_actions(
            session,
            xr.ActionsSyncInfo(active_action_sets=[xr.ActiveActionSet(self._action_set, xr.NULL_PATH)]),
        )
        state = ControllerState()
        poses: dict[str, Quat | None] = {}
        for name, (kind, action) in self._actions.items():
            info = xr.ActionStateGetInfo(action=action)
            if kind == "bool":
                value = xr.get_action_state_boolean(session, info)
                state.digital[name] = bool(value.current_state) and bool(value.is_active)
            elif kind == "float":
                value = xr.get_action_state_float(session, info)
                state.analog[name] = float(value.current_state) if value.is_active else 0.0
            elif kind == "vec2":
                value = xr.get_action_state_vector2f(session, info)
                stick = (float(value.current_state.x), float(value.current_state.y)) if value.is_active else (0.0, 0.0)
                if name == "left_stick":
                    state.left_stick = stick
                else:
                    state.right_stick = stick
            else:
                location = xr.locate_space(self._spaces[name], self._context.space, display_time)
                valid = int(location.location_flags) & int(xr.SPACE_LOCATION_ORIENTATION_VALID_BIT)
                o = location.pose.orientation
                poses[name] = (o.x, o.y, o.z, o.w) if valid else None
        state.left_aim, state.right_aim = poses.get("left_aim"), poses.get("right_aim")
        location = xr.locate_space(self._view_space, self._context.space, display_time)
        if int(location.location_flags) & 3 == 3:  # orientation and position valid
            o, p = location.pose.orientation, location.pose.position
            state.head = ((o.x, o.y, o.z, o.w), (p.x, p.y, p.z))
        return state


class ScreenLayer:
    """The headset swapchain that receives the monitor image, shown as a quad layer.

    A quad layer is drawn by the headset compositor at the display's own resolution, so text
    stays sharp and nothing is rendered per eye by this app.
    """

    def __init__(self, context: Any, width_m: float, mipmaps: bool) -> None:
        self._context = context
        self._width_m = width_m
        self._want_mipmaps = mipmaps
        formats = list(xr.enumerate_swapchain_formats(context.session))
        self.format = GL_SRGB8_ALPHA8 if GL_SRGB8_ALPHA8 in formats else GL_RGBA8
        self._swapchain: Any = None
        self._images: Any = None
        self._layer: Any = None
        self.width = self.height = 0
        self._levels = 1
        self._has_image = False
        self._read_fbo, self._draw_fbo = (int(name) for name in GL.glGenFramebuffers(2))

    def resize(self, width: int, height: int) -> None:
        """(Re)create the swapchain for a monitor of this size."""
        if (width, height) == (self.width, self.height) and self._swapchain is not None:
            return
        # Until the new swapchain has an image there is nothing valid to show.
        self._has_image = False
        # Mipmaps: the monitor image covers far fewer headset pixels than it has. Without the
        # reduced copies the compositor skips pixels and fine detail (grass, text) shimmers.
        levels = max(width, height).bit_length() if self._want_mipmaps else 1
        usage = (
            xr.SwapchainUsageFlags.SAMPLED_BIT
            | xr.SwapchainUsageFlags.COLOR_ATTACHMENT_BIT
            | xr.SwapchainUsageFlags.TRANSFER_DST_BIT
        )

        def create(mip_count: int) -> Any:
            return xr.create_swapchain(
                self._context.session,
                xr.SwapchainCreateInfo(
                    usage_flags=usage,
                    format=self.format,
                    sample_count=1,
                    width=width,
                    height=height,
                    face_count=1,
                    array_size=1,
                    mip_count=mip_count,
                ),
            )

        try:
            swapchain = create(levels)
        except xr.exception.XrException as error:
            if levels == 1:
                raise
            print(f"the runtime refused {levels} mipmap levels ({error}); continuing without", flush=True)
            levels = 1
            swapchain = create(1)
        # The old swapchain goes away only after the new one exists: a failed creation
        # leaves this object consistent and the caller can simply try again.
        try:
            images = xr.enumerate_swapchain_images(swapchain, xr.SwapchainImageOpenGLKHR)
        except xr.exception.XrException:
            xr.destroy_swapchain(swapchain)
            raise
        if self._swapchain is not None:
            xr.destroy_swapchain(self._swapchain)
        self._swapchain, self._images, self._levels = swapchain, images, levels
        self.width, self.height = width, height
        kind = "sRGB" if self.format == GL_SRGB8_ALPHA8 else "RGBA8"
        print(f"screen: {width}x{height}, {kind}, {levels} mipmap level(s)", flush=True)

    def present(self, source_texture: int) -> None:
        """Copy the newest monitor image (stored top row first) into the headset swapchain."""
        index = xr.acquire_swapchain_image(self._swapchain, xr.SwapchainImageAcquireInfo())
        xr.wait_swapchain_image(self._swapchain, xr.SwapchainImageWaitInfo(timeout=xr.INFINITE_DURATION))
        try:
            self._copy(source_texture, self._images[index].image)
        finally:
            # Always handed back: an image left acquired would make every later copy fail.
            xr.release_swapchain_image(self._swapchain, xr.SwapchainImageReleaseInfo())
        self._has_image = True

    def _copy(self, source_texture: int, target: int) -> None:
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self._read_fbo)
        GL.glFramebufferTexture2D(GL.GL_READ_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, source_texture, 0)
        GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, self._draw_fbo)
        GL.glFramebufferTexture2D(GL.GL_DRAW_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, target, 0)
        # Swapped destination rows flip the image on the graphics card, at no processor cost.
        GL.glBlitFramebuffer(
            0, 0, self.width, self.height, 0, self.height, self.width, 0, GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST
        )
        GL.glFramebufferTexture2D(GL.GL_READ_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, 0, 0)
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, 0)
        GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, 0)
        if self._levels > 1:
            GL.glBindTexture(GL.GL_TEXTURE_2D, target)
            GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    def layer(self, pose: tuple[Quat, Vec3] | None) -> Any:
        """The composition layer for this frame, or None while there is nothing to show."""
        if not self._has_image or pose is None:
            return None
        orientation, position = pose
        self._layer = xr.CompositionLayerQuad(
            space=self._context.space,
            eye_visibility=xr.EyeVisibility.BOTH,
            sub_image=xr.SwapchainSubImage(
                swapchain=self._swapchain,
                image_rect=xr.Rect2Di(offset=xr.Offset2Di(0, 0), extent=xr.Extent2Di(self.width, self.height)),
            ),
            pose=xr.Posef(orientation=xr.Quaternionf(*orientation), position=xr.Vector3f(*position)),
            size=xr.Extent2Df(self._width_m, self._width_m * self.height / self.width),
        )
        return ctypes.byref(self._layer)
