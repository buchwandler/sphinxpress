"""sphinxpress package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sphinxpress")
except PackageNotFoundError:  # pragma: no cover - local source tree fallback
    __version__ = "0.0.0"

__all__ = ["__version__"]

