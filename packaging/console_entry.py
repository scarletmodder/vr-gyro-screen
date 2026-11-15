"""Entry of the installed console program: the same command line as `python -m vr_gyro_screen`."""

import sys

from vr_gyro_screen.cli import main

if __name__ == "__main__":
    sys.exit(main())
