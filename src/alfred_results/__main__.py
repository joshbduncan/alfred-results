"""
__main__
--------
Entry point for running alfred-results as a module.

Allows the package to be invoked directly via the Python interpreter::

    python -m alfred_results [ARGS...]

This is equivalent to running the `alfred-results` console script.
All command-line arguments are forwarded to :func:`~alfred_results.cli.main`,
which handles parsing and exits with the appropriate status code.
"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
