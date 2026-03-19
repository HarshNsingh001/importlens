from __future__ import annotations

import importlib
from typing import Final

DEFAULT_BACKEND: Final[str] = "pkg.backends.default_backend"


def load_backend(name: str = DEFAULT_BACKEND) -> object:
    return importlib.import_module(name)

