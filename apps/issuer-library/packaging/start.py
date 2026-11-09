"""Start Credit OS from a release folder under the company Python (run with -I; stdlib only)."""

import os
import sys

RELEASE = os.path.dirname(os.path.abspath(__file__))  # as launched: a UNC or drive path
sys.path[:0] = [os.path.join(RELEASE, "lib"), os.path.join(RELEASE, "engine", "src")]

from issuer_library.version import app_version

if sys.argv[1:] == ["--version"]:
    print(app_version())
    sys.exit(0)

from issuer_library.__main__ import main

PACKAGE_ROOT = os.path.dirname(os.path.dirname(RELEASE))
sys.argv = [
    sys.argv[0],
    "--defaults",
    os.path.join(PACKAGE_ROOT, "default-workspace.json"),
    *sys.argv[1:],
]
sys.exit(main())
