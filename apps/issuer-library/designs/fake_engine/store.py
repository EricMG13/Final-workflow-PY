"""Offline check only: run the real store from its own folder."""

import os
import runpy

runpy.run_path(
    os.environ["CHECK_ROOT"] + "/apps/issuer-library/engine/store.py", run_name="__main__"
)
