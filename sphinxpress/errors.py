"""Custom exceptions for sphinxpress."""

from __future__ import annotations


class SphinxpressError(Exception):
    """Base exception for all user-facing sphinxpress errors."""


class ConfigError(SphinxpressError):
    """Raised when configuration is missing or invalid."""


class ValidationError(SphinxpressError):
    """Raised when validation fails."""


class SelectionError(SphinxpressError):
    """Raised when project selection flags are invalid."""


class SphinxBuildError(SphinxpressError):
    """Raised when a sphinx-build command fails."""


class PathTraversalError(SphinxpressError):
    """Raised when a generated path escapes an allowed root."""


class ReleaseResolutionError(SphinxpressError):
    """Raised when release metadata cannot be resolved."""
