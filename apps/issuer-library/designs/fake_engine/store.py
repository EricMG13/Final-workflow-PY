"""Offline check only: the real store, loaded from its own folder and served in process."""

import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "real_store", os.environ["CHECK_ROOT"] + "/apps/issuer-library/engine/store.py"
)
real = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real)
workspace_store = real.workspace_store
