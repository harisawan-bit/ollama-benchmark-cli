"""Ensure the project root is importable when running pytest.

The project ships flat modules (main.py, cli.py, benchmarks.py) rather than a
package. This puts the repository root first on sys.path so ``import cli`` and
``import benchmarks`` resolve to this project even if another ``cli`` module
happens to be on the interpreter path.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
