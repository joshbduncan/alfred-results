"""
alfred-results
--------------
Helper package for converting filesystem paths into Alfred Script Filter
JSON result items.

The public API is exposed through :mod:`alfred_results.result_item`,
:mod:`alfred_results.payload`, and :mod:`alfred_results.utils`,
re-exported here for convenience:

    from alfred_results import ScriptFilterCache, ScriptFilterPayload, path_to_uuid
    from alfred_results.result_item import ResultItem, Icon, Mod

Version information is retrieved lazily from the installed package metadata
so that this file never needs to be updated manually when the version bumps.
When the package is not installed (e.g. running from source via PYTHONPATH),
:func:`_get_version` returns `"unknown"` rather than raising.

:copyright: (c) 2026 Josh Duncan.
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations

from .payload import ScriptFilterCache, ScriptFilterPayload
from .utils import path_to_uuid

__all__ = ["ScriptFilterCache", "ScriptFilterPayload", "path_to_uuid"]


def _get_version() -> str:
    """Return the installed package version string.

    Looks up the version from the package metadata installed by the build
    backend.  Falls back to `"unknown"` when the package has not been
    installed (e.g. when running directly from source via `PYTHONPATH`).

    Returns:
        The version string from package metadata (e.g. `"1.2.3"`), or
        `"unknown"` if the package metadata cannot be found.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("alfred-results")
    except PackageNotFoundError:
        return "unknown"


def __getattr__(name: str) -> str:
    """Lazy module-level attribute lookup.

    Supports dynamic access to `__version__` without importing
    `importlib.metadata` at module load time.

    Args:
        name: The attribute name being accessed on this module.

    Returns:
        The installed package version string when *name* is `"__version__"`,
        or `"unknown"` if the package is not installed.

    Raises:
        AttributeError: For any attribute other than `"__version__"`.
    """
    if name == "__version__":
        return _get_version()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
