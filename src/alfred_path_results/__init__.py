"""
alfred-path-results
-------------------
Helper package for converting filesystem paths into Alfred Script Filter
JSON result items.

The public API is exposed through :mod:`alfred_path_results.result_item` and
re-exported here for convenience:

    from alfred_path_results.result_item import ResultItem, Icon, Mod

Version information is retrieved lazily from the installed package metadata
so that this file never needs to be updated manually when the version bumps.

:copyright: (c) 2026 Josh Duncan.
:license: MIT, see LICENSE for more details.
"""

from __future__ import annotations


def __getattr__(name: str) -> str:
    """Lazy module-level attribute lookup.

    Supports dynamic access to ``__version__`` without importing
    ``importlib.metadata`` at module load time.

    Args:
        name: The attribute name being accessed on this module.

    Returns:
        The installed package version string when *name* is ``"__version__"``.

    Raises:
        AttributeError: For any attribute other than ``"__version__"``.
    """
    if name == "__version__":
        from importlib.metadata import version

        return version("alfred-path-results")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
