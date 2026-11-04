"""Local entry point; the isolated environment is created with uv sync --locked."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from deploy_workflow.model_testing.run import main

if __name__ == "__main__":
    raise SystemExit(main())
