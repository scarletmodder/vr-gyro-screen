# Third-party notices

The Windows installer of VR Gyro Screen carries the libraries below, unmodified, each in its own file inside the installation folder. Each one belongs to its authors and is used under its own license. The full license texts are at the links.

| Library | What it is used for | License | Where it comes from |
|---|---|---|---|
| Python | Runs the program | PSF License Agreement | <https://www.python.org/> |
| Qt for Python (PySide6) and Qt | The settings window | LGPL-3.0 | <https://doc.qt.io/qtforpython-6/licenses.html> |
| pyopenxr | Talks to the headset | Apache-2.0 | <https://github.com/cmbruns/pyopenxr> |
| OpenXR loader | Finds the active OpenXR runtime | Apache-2.0 | <https://github.com/KhronosGroup/OpenXR-SDK> |
| PyOpenGL | Draws the screen | BSD-3-Clause | <https://github.com/mcfletch/pyopengl> |
| pyGLFW | Creates the drawing context | MIT | <https://github.com/FlorianRhiem/pyGLFW> |
| GLFW | Creates the drawing context | zlib/libpng | <https://www.glfw.org/license.html> |
| vgamepad | Creates the virtual gamepad | MIT | <https://github.com/yannbouteiller/vgamepad> |
| ViGEmClient | Talks to the virtual gamepad driver | MIT | <https://github.com/nefarius/ViGEmClient> |
| NumPy | Numeric arrays used by pyopenxr | BSD-3-Clause | <https://numpy.org/doc/stable/license.html> |

Qt is used as a set of separate library files (DLLs) that the program loads when it starts. You may replace them with your own build of the same Qt version, as the LGPL allows.

The installer does not carry and does not install the programs VR Gyro Screen works with: the ViGEmBus driver and Virtual Desktop are downloaded by you from their own sites.
