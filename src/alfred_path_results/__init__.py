"""
Alfred Helper
-------------
Helper package for working with Alfred app workflows.
-------------
:copyright: (c) 2026 Josh Duncan.
:license: MIT, see LICENSE for more details.
"""


def __getattr__(name: str) -> str:
    """Lazy module-level attribute lookup for ``__version__``."""

    if name == "__version__":
        from importlib.metadata import version

        return version("word_search_generator")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
