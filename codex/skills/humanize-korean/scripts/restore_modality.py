#!/usr/bin/env python3
"""Development/symlink-install launcher for the shared runtime script."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[4] / "scripts" / Path(__file__).name), run_name="__main__")
