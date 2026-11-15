"""Entry of the installed window program (no console): opens the settings window."""

import sys
import traceback

from vr_gyro_screen.cli import main

if __name__ == "__main__":
    try:
        code = main(["settings"])
    except Exception:  # a windowed program has nowhere to print: show the problem instead
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, traceback.format_exc(), "VR Gyro Screen", 0x10)
        code = 1
    sys.exit(code)
