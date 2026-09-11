#!/usr/bin/env python3
"""
Build Survey Planner into a folder that runs without Python.

    python build.py            one folder in dist\\, the fast-starting form
    python build.py --onefile  a single .exe, slower to start

--onedir is the default on purpose. A one-file build unpacks itself into a
temporary directory on every launch, and with numpy and matplotlib inside that
is several seconds of nothing happening before the window appears. The folder
form starts immediately and zips just as well for a release.

shapely and scikit-image are large and are both required: shapely does the
polygon work and scikit-image the least-cost routing that keeps a transit on
the water. Neither can be excluded.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "SurveyPlanner"
ENTRY = "survey_planner.py"

# Imported through a string or a plugin system, so PyInstaller cannot see them
# by following the source.
HIDDEN = [
    "matplotlib.backends.backend_tkagg",
    "PIL._tkinter_finder",
    "skimage.graph",
    "skimage.graph._mcp",
    "scipy.spatial.transform._rotation_groups",
]

# Never reached from this program. Each one is tens of megabytes.
EXCLUDE = [
    "pandas", "rasterio", "pingverter", "pingmapper", "IPython", "pytest",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "notebook", "sphinx",
    "tkinter.test", "test",
]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    onefile = "--onefile" in argv

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed. Run:")
        print("    python -m pip install pyinstaller")
        return 1

    for stale in ("build", "dist", NAME + ".spec"):
        path = os.path.join(HERE, stale)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", NAME,
        "--onefile" if onefile else "--onedir",
        # No console window behind the GUI. The command line still works:
        # RecordingFixer.exe --report <recording> prints to a pipe.
        "--windowed",
        "--icon", os.path.join(HERE, "icon.png"),
        # Read by appicon.py, which looks in sys._MEIPASS when frozen.
        "--add-data", "%s%s." % (os.path.join(HERE, "icon.png"), os.pathsep),
    ]
    for name in HIDDEN:
        cmd += ["--hidden-import", name]
    for name in EXCLUDE:
        cmd += ["--exclude-module", name]
    cmd.append(os.path.join(HERE, ENTRY))

    print("Building %s ..." % NAME)
    print(" ".join(cmd))
    print()
    result = subprocess.run(cmd, cwd=HERE)
    if result.returncode != 0:
        return result.returncode

    out = os.path.join(HERE, "dist", NAME + (".exe" if onefile else ""))
    print()
    if os.path.isdir(out):
        total = sum(os.path.getsize(os.path.join(base, f))
                    for base, _d, files in os.walk(out) for f in files)
        print("Built %s\n  %.0f MB in the folder" % (out, total / 1e6))
        print("  Run: %s" % os.path.join(out, NAME + ".exe"))
    elif os.path.isfile(out):
        print("Built %s\n  %.0f MB" % (out, os.path.getsize(out) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
