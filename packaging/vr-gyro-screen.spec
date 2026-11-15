# PyInstaller recipe: one folder with two programs that share the same files.
#   vr-gyro-screen.exe      the settings window (no console)
#   vr-gyro-screen-cli.exe  the engine and the command line (console)
# Only the libraries the programs load are collected. The gamepad driver installer that
# comes inside the gamepad package is left out on purpose: drivers are installed by the
# person, from the site of whoever makes them.
import importlib.util
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent
SOURCE = ROOT / "src"


def package_dir(name):
    return Path(importlib.util.find_spec(name).origin).parent


xr_library = package_dir("xr") / "library"
datas = [
    (str(SOURCE / "vr_gyro_screen" / "assets" / "icon.ico"), "vr_gyro_screen/assets"),
    (str(SOURCE / "vr_gyro_screen" / "assets" / "icon.png"), "vr_gyro_screen/assets"),
]
binaries = [
    (str(package_dir("vgamepad") / "win" / "vigem" / "client" / "x64" / "ViGEmClient.dll"), "vgamepad/win/vigem/client/x64"),
    (str(xr_library / "openxr_loader.dll"), "xr/library"),
    (str(xr_library / "windows_x86_64" / "openxr_loader.dll"), "xr/library/windows_x86_64"),
    (
        str(package_dir("xr") / "api_layer" / "windows_x86_64" / "XrApiLayer_python.dll"),
        "xr/api_layer/windows_x86_64",
    ),
    (str(package_dir("glfw") / "glfw3.dll"), "glfw"),
]
excludes = ["dxcam", "PIL", "tkinter", "pytest", "mypy", "ruff", "IPython", "matplotlib", "OpenGL_accelerate"]
icon = str(SOURCE / "vr_gyro_screen" / "assets" / "icon.ico")


def analysis(script):
    return Analysis(
        [str(ROOT / "packaging" / script)],
        pathex=[str(SOURCE)],
        binaries=binaries,
        datas=datas,
        hiddenimports=[
            "OpenGL.platform.win32",
            "OpenGL.arrays.ctypesarrays",
            "OpenGL.arrays.ctypesparameters",
            *collect_submodules("xr"),  # the headset library picks its parts by name at run time
        ],
        excludes=excludes,
        noarchive=False,
    )


window = analysis("window_entry.py")
console = analysis("console_entry.py")
window_exe = EXE(
    PYZ(window.pure),
    window.scripts,
    exclude_binaries=True,
    name="vr-gyro-screen",
    console=False,
    upx=False,
    icon=icon,
)
console_exe = EXE(
    PYZ(console.pure),
    console.scripts,
    exclude_binaries=True,
    name="vr-gyro-screen-cli",
    console=True,
    upx=False,
    icon=icon,
)
COLLECT(
    window_exe,
    console_exe,
    window.binaries,
    window.datas,
    console.binaries,
    console.datas,
    upx=False,
    name="vr-gyro-screen",
)
