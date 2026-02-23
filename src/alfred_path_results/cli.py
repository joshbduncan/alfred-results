"""
cli
---
Command-line interface for alfred-path-results.

Reads a list of filesystem paths (from stdin or a file), converts each path
into an Alfred Script Filter result item, and writes the resulting JSON payload
to stdout.

Usage::

    # Pipe paths from another command
    find ~/Downloads -maxdepth 1 | alfred-path-results

    # Pass a newline-delimited file
    alfred-path-results --input paths.txt

    # Add a modifier override and session variable
    alfred-path-results --mod cmd /tmp/out "Open in Terminal" \\
        --session-var ts 2026-01-01

Entry point: :func:`main`.
"""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from json import dumps
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

from . import _get_version
from .result_item import Icon, IconResourceType, ItemType, Mod, ResultItem
from .utils import path_to_uuid


@contextmanager
def _open_input(val: str) -> Generator[Any, None, None]:
    """Return an open text-file context manager for *val*.

    Yields ``sys.stdin`` directly when *val* is ``"-"``; otherwise opens the
    file at *val* with UTF-8 encoding.  The file is closed automatically on
    exit; stdin is left open.

    Args:
        val: A filesystem path, or ``"-"`` for stdin.

    Yields:
        A readable text-file object.

    Raises:
        OSError: If *val* is a path that cannot be opened.
    """
    if val == "-":
        yield sys.stdin
    else:
        with open(val, encoding="utf-8") as f:
            yield f


def parse_input(val: str) -> list[str]:
    """Read newline-delimited paths from stdin or a file path.

    Opens ``val`` as a file path with UTF-8 encoding, or reads from stdin
    when ``val`` is ``"-"``.  Blank lines and lines that are entirely
    whitespace are discarded.

    Args:
        val: A filesystem path to a text file, or ``"-"`` to read from stdin.

    Returns:
        A list of non-empty, stripped path strings in the order they appear
        in the input.

    Raises:
        OSError: If ``val`` is a file path that cannot be opened (e.g. does
            not exist or permission denied).
    """
    with _open_input(val) as f:
        return [ln.strip() for ln in f if ln.strip()]


def parse_session_vars(val: list[list[str]] | None) -> dict[str, str]:
    """Convert argparse ``--session-var`` pairs into a flat dict.

    Each element of *val* is a two-element list ``[KEY, VALUE]`` produced by
    ``argparse`` when ``nargs=2, action="append"`` is used.

    Args:
        val: A list of ``[key, value]`` pairs, or ``None`` when the option
            was not provided.

    Returns:
        A ``{key: value}`` dict, or an empty dict when *val* is ``None``.
    """
    if val is None:
        return {}
    return dict(val)


def get_path_attribute(p: Path, key: str) -> Any:
    """Retrieve a named attribute or method result from a :class:`~pathlib.Path`.

    If the attribute is callable (e.g. :meth:`~pathlib.Path.as_posix`), it is
    called with no arguments and its return value is returned.  Non-callable
    attributes (e.g. :attr:`~pathlib.Path.name`, :attr:`~pathlib.Path.stem`)
    are returned directly.

    Args:
        p: The :class:`~pathlib.Path` instance to inspect.
        key: The attribute name to look up on *p* (e.g. ``"name"``,
             ``"as_posix"``, ``"suffix"``).

    Returns:
        The attribute value, or the return value of the attribute if it is
        callable.

    Raises:
        AttributeError: If *key* is not a valid attribute of
            :class:`~pathlib.Path`.
    """
    attr = getattr(p, key)
    return attr() if callable(attr) else attr


def parse_result_vars(p: Path, val: list[list[str]] | None) -> dict[str, str] | None:
    """Build per-result variables by resolving Path attributes.

    Each element of *val* is a two-element list ``[VAR_NAME, PATH_ATTR]``
    where ``PATH_ATTR`` names a :class:`~pathlib.Path` attribute or
    zero-argument method.  The resolved value is coerced to ``str``.

    Args:
        p: The :class:`~pathlib.Path` for the current result item.
        val: A list of ``[variable_name, path_attribute]`` pairs supplied via
            ``--result-var`` on the command line, or ``None`` when the option
            was not provided.

    Returns:
        A ``{variable_name: resolved_str_value}`` dict, or ``None`` when
        *val* is ``None``.

    Raises:
        AttributeError: If any ``path_attribute`` name is not valid on
            :class:`~pathlib.Path`.
    """
    if val is None:
        return None
    d: dict[str, str] = {}
    for k, v in val:
        d[k] = str(get_path_attribute(p, v))
    return d


def parse_mods(val: list[list[str]] | None) -> list[Mod]:
    """Convert argparse ``--mod`` triples into :class:`~result_item.Mod` instances.

    Each element of *val* is a three-element list ``[MOD_KEY, ARG, SUBTITLE]``
    produced by ``argparse`` when ``nargs=3, action="append"`` is used.

    Args:
        val: A list of ``[mod_key, arg, subtitle]`` triples supplied via
            ``--mod`` on the command line, or ``None`` when the option was
            not provided.

    Returns:
        A list of :class:`~result_item.Mod` objects with ``valid=True``, or
        an empty list when *val* is ``None``.

    Raises:
        ValueError: If any *mod_key* is not a recognised Alfred modifier combo
            (propagated from :class:`~result_item.Mod.__post_init__`).
    """
    if val is None:
        return []
    return [
        Mod(key=key, valid=True, arg=arg, subtitle=subtitle)
        for key, arg, subtitle in val
    ]


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        A fully configured :class:`argparse.ArgumentParser` instance ready
        for ``parse_args()``.
    """
    parser = argparse.ArgumentParser(
        description="Helper package for working with Alfred app workflows."
    )

    parser.add_argument(
        "-i",
        "--input",
        metavar="FILE",
        default="-",
        help="input file or '-' for stdin (default: stdin)",
    )

    parser.add_argument(
        "-m",
        "--mod",
        nargs=3,
        action="append",
        metavar=("MOD", "ARG", "SUBTITLE"),
        help="control modifier key/key-combo action (ex. --mod cmd+shift foo bar)",
    )

    parser.add_argument(
        "--session-var",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="alfred session variable (ex. --session-var ts 2026-02-20T11:31:59Z)",
    )

    parser.add_argument(
        "--result-var",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help=(
            "alfred result item variable from pathlib Path object"
            " (ex. --result-var path as_posix)"
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Reads one or more filesystem paths, converts each into an Alfred Script
    Filter result item, and writes the full Script Filter JSON payload to
    stdout.

    Processing steps:

    1. Parse command-line arguments.
    2. Read paths from stdin or ``--input`` file via :func:`parse_input`.
    3. Optionally parse ``--session-var`` pairs into top-level variables.
    4. Optionally parse ``--mod`` triples into modifier overrides.
    5. For each path: build an :class:`~result_item.Icon`, resolve any
       ``--result-var`` pairs, construct a :class:`~result_item.ResultItem`,
       and collect it.
    6. Serialise to JSON and print to stdout.

    Args:
        argv: Command-line argument list.  Defaults to ``sys.argv[1:]`` when
            ``None``.

    Returns:
        ``0`` on success.  Non-zero exit codes are produced via
        :func:`argparse.ArgumentParser.error` (which calls ``sys.exit(2)``).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # process stdin (or --input path)
    if args.input == "-" and sys.stdin.isatty():
        parser.error("no stdin provided")

    paths: list[str] = []
    try:
        paths = parse_input(args.input)
    except OSError as e:
        parser.error(f"can't open '{args.input}': {e.strerror}")

    if not paths:
        parser.error("no paths found")

    # process session variables
    session_vars = parse_session_vars(args.session_var)

    # process modifiers
    mods: list[Mod] = []
    try:
        mods = parse_mods(args.mod)
    except ValueError as e:
        parser.error(str(e))

    # build alfred result dict
    items: list[ResultItem] = []
    for i in paths:
        p = Path(i)
        p_resolved = p.expanduser().resolve()
        icon = Icon(path=str(p_resolved), resource_type=IconResourceType.FILEICON)

        result_variables: dict[str, str] = {"_path": p.as_posix()}
        try:
            result_variables = parse_result_vars(p, args.result_var) or result_variables
        except AttributeError as e:
            parser.error(str(e))

        item = ResultItem(
            uid=path_to_uuid(str(p_resolved)),
            title=p.name or p.as_posix(),
            subtitle=p.as_posix(),
            arg=p.as_posix(),
            icon=icon,
            type=ItemType.FILE if p.is_file() else ItemType.DEFAULT,
            mods=mods,
            variables=result_variables,
        )
        items.append(item)

    # output alfred json
    sys.stdout.write(
        dumps(
            {
                "variables": session_vars,
                "items": [item.to_alfred() for item in items],
            },
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
