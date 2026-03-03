"""
cli
---
Command-line interface for alfred-results.

Reads input from stdin or a file in one of four formats (`path`, `csv`,
`json`, or `string`) and writes the complete Script Filter JSON payload to
stdout via :class:`~alfred_results.payload.ScriptFilterPayload`.

Alfred Script Filters are workflow nodes that run a script and read its stdout
as a JSON payload describing a list of result items to display in Alfred's UI.
This CLI acts as a bridge between shell pipelines (e.g. `find`, `mdfind`,
`ls`) and that JSON format, so Alfred workflows can be built without writing
Python.

Arguments
---------
FILE
    Path to an input file whose format is controlled by `--input-format`,
    or `-` to read from stdin (the default when no file is given).
--input-format FORMAT
    Controls how the input is parsed.  One of:

    `path` (default)
        One filesystem path per line.  Each path is expanded, resolved, and
        converted to a :class:`~alfred_results.result_item.ResultItem` via
        :meth:`~alfred_results.result_item.ResultItem.from_path`.
    `csv`
        A CSV file with a header row.  The `title` column is required;
        `subtitle`, `uid`, `arg`, `type`, and `icon` are optional.
        Additional columns are ignored.
    `json`
        A JSON array of objects.  Each object must have a `"title"` key;
        `"subtitle"`, `"uid"`, `"arg"`, `"type"`, and `"icon"` are
        optional.  Additional keys are ignored.  Useful for piping output
        from tools like `jq`, `gh`, or `brew info --json`.
    `string`
        One arbitrary string per line.  Each line becomes the `title` of a
        plain :class:`~alfred_results.result_item.ResultItem` with no path
        metadata.
--mod MOD ARG SUBTITLE
    Add a modifier-key override to every result item.  `MOD` must be a valid
    Alfred modifier combo (e.g. `cmd`, `alt`, `cmd+shift`).  `ARG` is
    resolved per item: for `path` format it is tried as a
    :class:`~pathlib.Path` attribute first; for `csv` and `json` formats
    it is looked up as a column/key in the current row first.  In both cases
    the raw string is used when no match is found.  May be repeated.
--result-var KEY VALUE
    Add an Alfred result-item variable to every item.  For `path` format,
    `VALUE` is first resolved as a :class:`~pathlib.Path` attribute name
    (e.g. `name`, `suffix`, `as_posix`); if no such attribute exists
    the raw string is used instead.  For `csv` and `json` formats,
    `VALUE` is first looked up as a column/key name in the current row;
    if not found the raw string is used instead.  For `string` format the
    raw string is always used.  May be repeated.
--session-var KEY VALUE
    Add a top-level Alfred session variable to the payload.  Session variables
    are available to all downstream workflow objects regardless of which item
    the user selects.  May be repeated.
--version
    Print the installed package version and exit.

Usage::

    # Pipe paths from another command
    find ~/Downloads -maxdepth 1 | alfred-results

    # Pass a newline-delimited file of paths (default format)
    alfred-results paths.txt

    # Add a modifier override and a session variable
    alfred-results --mod cmd /tmp/out "Open in Terminal" \\
        --session-var ts 2026-01-01

    # Attach per-item variables using Path attribute names
    alfred-results paths.txt --result-var ext suffix --result-var base stem

    # Read a CSV file (title column required)
    alfred-results --input-format csv data.csv

    # Read a JSON array of objects (title key required)
    alfred-results --input-format json data.json

    # Pipe JSON from another tool
    gh repo list --json name,url | alfred-results --input-format json

    # Read plain strings, one per line
    alfred-results --input-format string labels.txt

Entry point: :func:`main`.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence
    from typing import TextIO

from . import _get_version
from .payload import ScriptFilterPayload
from .result_item import Icon, ItemType, Mod, ResultItem


@contextmanager
def _open_input(val: str) -> Generator[TextIO, None, None]:
    """Return an open text-file context manager for *val*.

    Yields `sys.stdin` directly when *val* is `"-"`; otherwise opens the
    file at *val* with UTF-8 encoding.  The file is closed automatically on
    exit; stdin is left open.

    Args:
        val: A filesystem path, or `"-"` for stdin.

    Yields:
        A readable text-mode file object (`sys.stdin` or an opened file).

    Raises:
        OSError: If *val* is a path that cannot be opened.
    """
    if val == "-":
        yield sys.stdin
    else:
        with open(val, encoding="utf-8") as f:
            yield f


def parse_input_lines(val: str) -> list[str]:
    """Read newline-delimited lines from stdin or a file path.

    Opens `val` as a file path with UTF-8 encoding, or reads from stdin
    when `val` is `"-"`.  Blank lines and lines that are entirely
    whitespace are discarded.  Used by both the `path` and `string`
    input formats.

    Args:
        val: A filesystem path to a text file, or `"-"` to read from stdin.

    Returns:
        A list of non-empty, stripped lines in the order they appear
        in the input.

    Raises:
        OSError: If `val` is a file path that cannot be opened (e.g. does
            not exist or permission denied).
    """
    with _open_input(val) as f:
        return [ln.strip() for ln in f if ln.strip()]


def parse_input_csv(val: str, *, delimiter: str = ",") -> list[dict[str, str]]:
    """Read a CSV file from stdin or a file path into a list of row dicts.

    The first row is treated as the header and its values become the keys of
    each row dict.  Blank rows are returned as empty dicts by the underlying
    :class:`csv.DictReader` and are included in the output; callers are
    responsible for any row-level validation.

    Args:
        val: A filesystem path to a CSV file, or `"-"` to read from stdin.
        delimiter: The field delimiter character.  Defaults to `","`
            (standard CSV).  Pass `"\\t"` for TSV input.

    Returns:
        A list of :class:`dict` objects mapping column header names to cell
        values, one dict per data row.

    Raises:
        OSError: If `val` is a file path that cannot be opened (e.g. does
            not exist or permission denied).

    Example::

        # Given a file with:
        # title,arg,subtitle
        # Downloads,/Users/me/Downloads,My downloads folder
        parse_input_csv("data.csv")
        # [{"title": "Downloads", "arg": "/Users/me/Downloads", ...}]
    """
    with _open_input(val) as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return list(reader)


def parse_input_json(val: str) -> list[dict[str, str]]:
    """Read a JSON array of objects from stdin or a file path into a list of dicts.

    The input must be a JSON array where every element is an object (dict).
    Each object is returned as-is; callers are responsible for field-level
    validation.  The `title` key is required by the `json` format handler
    in :func:`main` and an error is raised there if it is absent.

    Args:
        val: A filesystem path to a JSON file, or `"-"` to read from stdin.

    Returns:
        A list of :class:`dict` objects, one per element in the JSON array.

    Raises:
        OSError: If `val` is a file path that cannot be opened (e.g. does
            not exist or permission denied).
        ValueError: If the input is not valid JSON, or the top-level value is
            not an array, or any element is not a JSON object.

    Example::

        # Given a file containing:
        # [{"title": "Downloads", "arg": "/Users/me/Downloads", "subtitle": "Home"}]
        parse_input_json("data.json")
        # [{"title": "Downloads", "arg": "/Users/me/Downloads", "subtitle": "Home"}]
    """
    with _open_input(val) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(
            f"json input must be a JSON array, got {type(data).__name__!r}"
        )

    result: list[dict[str, str]] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"json input element {i} must be an object, got {type(item).__name__!r}"
            )
        result.append({str(k): str(v) for k, v in item.items()})

    return result


def parse_session_vars(val: list[list[str]] | None) -> dict[str, str]:
    """Convert argparse `--session-var` pairs into a flat dict.

    Each element of *val* is a two-element list `[KEY, VALUE]` produced by
    `argparse` when `nargs=2, action="append"` is used.

    Args:
        val: A list of `[key, value]` pairs, or `None` when the option
            was not provided.

    Returns:
        A `{key: value}` dict, or an empty dict when *val* is `None`.
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
        key: The attribute name to look up on *p* (e.g. `"name"`,
             `"as_posix"`, `"suffix"`).

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

    Each element of *val* is a two-element list `[VAR_NAME, PATH_ATTR]`
    where `PATH_ATTR` names a :class:`~pathlib.Path` attribute or
    zero-argument method.  The resolved value is coerced to `str`.

    Args:
        p: The :class:`~pathlib.Path` for the current result item.
        val: A list of `[variable_name, path_attribute]` pairs supplied via
            `--result-var` on the command line, or `None` when the option
            was not provided.

    Returns:
        A `{variable_name: resolved_str_value}` dict, or `None` when
        *val* is `None`.  When a `path_attribute` name is not a valid
        :class:`~pathlib.Path` attribute the raw `VALUE` string is used
        as-is rather than raising.  For `csv` and `json` formats see
        :func:`parse_result_vars_from_row`.
    """
    if val is None:
        return None
    d: dict[str, str] = {}
    for k, v in val:
        try:
            d[k] = str(get_path_attribute(p, v))
        except AttributeError:
            d[k] = v
    return d


def parse_result_vars_from_row(
    row: dict[str, str], val: list[list[str]] | None
) -> dict[str, str] | None:
    """Build per-result variables by looking up keys in a parsed row dict.

    Each element of *val* is a two-element list `[VAR_NAME, ROW_KEY]`.
    For each pair, *ROW_KEY* is looked up in *row*; if the key is present
    its value is used.  If *ROW_KEY* is not present in *row*, the raw
    *ROW_KEY* string is used as-is.  This mirrors the fallback behaviour of
    :func:`parse_result_vars` for the `path` format.

    Args:
        row: The parsed row dict from a `csv` or `json` input item.
        val: A list of `[variable_name, row_key]` pairs supplied via
            `--result-var` on the command line, or `None` when the
            option was not provided.

    Returns:
        A `{variable_name: value}` dict, or `None` when *val* is
        `None`.  A `None` return value signals callers to omit the
        `variables` key from the result item entirely.
    """
    if val is None:
        return None
    return {k: row.get(v, v) for k, v in val}


def parse_mods(val: list[list[str]] | None) -> list[Mod]:
    """Convert argparse `--mod` triples into :class:`~result_item.Mod` instances.

    Used for upfront validation of modifier key combos before any rows are
    processed.  The `arg` field is taken as a raw string here; for
    per-row `arg` resolution against row keys or :class:`~pathlib.Path`
    attributes use :func:`build_mods_for_row` instead.

    Args:
        val: A list of `[mod_key, arg, subtitle]` triples supplied via
            `--mod` on the command line, or `None` when the option was
            not provided.

    Returns:
        A list of :class:`~alfred_results.result_item.Mod` objects with
        `valid=True`, or an empty list when *val* is `None`.

    Raises:
        ValueError: If any *mod_key* is not a recognized Alfred modifier combo
            (propagated from
            :class:`~alfred_results.result_item.Mod.__post_init__`).
    """
    if val is None:
        return []
    return [
        Mod(key=key, valid=True, arg=arg, subtitle=subtitle)
        for key, arg, subtitle in val
    ]


def resolve_mod_arg(
    arg: str,
    *,
    row: dict[str, str] | None = None,
    path: Path | None = None,
) -> str:
    """Resolve a mod `arg` value against a row dict or a Path object.

    Applies the same lookup-then-fallback strategy used by
    :func:`parse_result_vars` and :func:`parse_result_vars_from_row`:

    * If *row* is provided: look up *arg* as a key in *row*; use the raw
      string if the key is absent.
    * If *path* is provided: try to resolve *arg* as a
      :class:`~pathlib.Path` attribute via :func:`get_path_attribute`; use
      the raw string if the attribute does not exist.
    * If neither is provided: return *arg* as-is (used for the `string`
      format where no structured data is available).

    Only one of *row* or *path* should be supplied per call.

    Args:
        arg: The raw `arg` string from a `--mod` triple.
        row: A parsed row dict from a `csv` or `json` input item.
        path: The :class:`~pathlib.Path` for the current `path`-format item.

    Returns:
        The resolved argument string.
    """
    if row is not None:
        return row.get(arg, arg)
    if path is not None:
        try:
            return str(get_path_attribute(path, arg))
        except AttributeError:
            return arg
    return arg


def build_mods_for_row(
    val: list[list[str]] | None,
    *,
    row: dict[str, str] | None = None,
    path: Path | None = None,
) -> list[Mod]:
    """Build per-row :class:`~result_item.Mod` instances with resolved `arg` values.

    Iterates the `--mod` triples and resolves each `arg` value via
    :func:`resolve_mod_arg` before constructing the :class:`~result_item.Mod`.
    This allows the `arg` to reference a row column/key (for `csv` and
    `json` formats) or a :class:`~pathlib.Path` attribute (for the `path`
    format), falling back to the raw string in both cases.

    Args:
        val: A list of `[mod_key, arg, subtitle]` triples supplied via
            `--mod` on the command line, or `None` when the option was
            not provided.
        row: A parsed row dict from a `csv` or `json` input item.
        path: The :class:`~pathlib.Path` for the current `path`-format item.

    Returns:
        A list of :class:`~result_item.Mod` objects with `valid=True`, or
        an empty list when *val* is `None`.

    Raises:
        ValueError: If any *mod_key* is not a recognized Alfred modifier combo
            (propagated from :class:`~result_item.Mod.__post_init__`).
    """
    if val is None:
        return []
    return [
        Mod(
            key=key,
            valid=True,
            arg=resolve_mod_arg(arg, row=row, path=path),
            subtitle=subtitle,
        )
        for key, arg, subtitle in val
    ]


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        A fully configured :class:`argparse.ArgumentParser` instance ready
        for `parse_args()`.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Builds Alfred Script Filter JSON from paths, CSV rows, JSON objects,"
            " or plain strings. Drop it into any Alfred workflow to turn shell"
            " output into a list of results Alfred can show and act on."
        )
    )

    parser.add_argument(
        "file",
        nargs="?",
        default="-",
        metavar="FILE",
        help="input file or '-' for stdin (default: stdin)",
    )

    parser.add_argument(
        "-f",
        "--input-format",
        choices=["path", "csv", "json", "string"],
        default="path",
        dest="input_format",
        metavar="FORMAT",
        help="input data format: path (default), csv, json, or string",
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
        "--result-var",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help=(
            "add an item-scoped variable; VALUE is resolved as a Path attribute"
            " (path format) or row key (csv/json format), falling back to the"
            " raw string (ex. --result-var ext suffix)"
        ),
    )

    parser.add_argument(
        "--session-var",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="alfred session variable (ex. --session-var ts 2026-02-20T11:31:59Z)",
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
    2. Read input from stdin or a positional `FILE` argument according to
       `--input-format` (`path`, `csv`, `json`, or `string`).
    3. Optionally parse `--session-var` pairs into top-level variables.
    4. Validate `--mod` key combos upfront via :func:`parse_mods`.
    5. For each input row: construct a :class:`~result_item.ResultItem`
       (via :meth:`~result_item.ResultItem.from_path` for `path` format,
       or directly for `csv`, `json`, and `string` formats) and collect it.
       For `path`, `csv`, and `json`, `--result-var` values and
       `--mod` `ARG` values are resolved per item against Path attributes
       or row keys respectively, falling back to the raw string.
    6. Serialize to JSON and print to stdout.

    Args:
        argv: Command-line argument list.  Defaults to `sys.argv[1:]` when
            `None`.

    Returns:
        `0` on success.  Non-zero exit codes are produced via
        :func:`argparse.ArgumentParser.error` (which calls `sys.exit(2)`).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # process stdin or positional FILE argument
    if args.file == "-" and sys.stdin.isatty():
        parser.error("no stdin provided")

    # process session variables
    session_vars = parse_session_vars(args.session_var)

    # process modifiers
    mods: list[Mod] = []
    try:
        mods = parse_mods(args.mod)
    except ValueError as e:
        parser.error(str(e))

    items: list[ResultItem] = []
    try:
        match args.input_format:
            case "path":
                data = parse_input_lines(args.file)
                for line in data:
                    fp = Path(line)
                    result_variables = parse_result_vars(fp, args.result_var)
                    item_mods = build_mods_for_row(args.mod, path=fp)
                    item = ResultItem.from_path(
                        fp, mods=item_mods, variables=result_variables
                    )
                    items.append(item)
            case "csv":
                rows = parse_input_csv(args.file)

                for row in rows:
                    title = row.get("title")
                    if title is None:
                        parser.error("csv input requires a 'title' column in every row")
                    assert title is not None

                    uid = row.get("uid")
                    subtitle = row.get("subtitle")
                    arg = row.get("arg")

                    item_type: ItemType | None = None
                    type_str = row.get("type")
                    if type_str is not None:
                        try:
                            item_type = ItemType(type_str)
                        except ValueError:
                            valid = ", ".join(f"'{t}'" for t in ItemType)
                            parser.error(
                                f"invalid 'type' value {type_str!r} in csv"
                                f" — must be one of {valid}"
                            )

                    icon_path = row.get("icon")
                    icon = Icon(path=icon_path) if icon_path else None

                    item_vars = parse_result_vars_from_row(row, args.result_var)
                    item_mods = build_mods_for_row(args.mod, row=row)
                    item = ResultItem(
                        title=title,
                        subtitle=subtitle,
                        uid=uid,
                        arg=arg,
                        type=item_type,
                        icon=icon,
                        mods=item_mods,
                        variables=item_vars,
                    )
                    items.append(item)
            case "json":
                rows = parse_input_json(args.file)

                for row in rows:
                    title = row.get("title")
                    if title is None:
                        parser.error(
                            "json input requires a 'title' key in every object"
                        )
                    assert title is not None

                    uid = row.get("uid")
                    subtitle = row.get("subtitle")
                    arg = row.get("arg")

                    item_type: ItemType | None = None
                    type_str = row.get("type")
                    if type_str is not None:
                        try:
                            item_type = ItemType(type_str)
                        except ValueError:
                            valid = ", ".join(f"'{t}'" for t in ItemType)
                            parser.error(
                                f"invalid 'type' value {type_str!r} in json"
                                f" — must be one of {valid}"
                            )

                    icon_path = row.get("icon")
                    icon = Icon(path=icon_path) if icon_path else None

                    item_vars = parse_result_vars_from_row(row, args.result_var)
                    item_mods = build_mods_for_row(args.mod, row=row)
                    item = ResultItem(
                        title=title,
                        subtitle=subtitle,
                        uid=uid,
                        arg=arg,
                        type=item_type,
                        icon=icon,
                        mods=item_mods,
                        variables=item_vars,
                    )
                    items.append(item)
            case "string":
                data = parse_input_lines(args.file)
                item_vars: dict[str, str] | None = (
                    dict(args.result_var) if args.result_var is not None else None
                )

                for line in data:
                    item = ResultItem(title=line, mods=mods, variables=item_vars)
                    items.append(item)
            case _:
                parser.error(f"invalid --input-format: {args.input_format}")

    except OSError as e:
        parser.error(f"can't open '{args.file}': {e.strerror}")
    except ValueError as e:
        parser.error(str(e))

    if not items:
        parser.error("no input data found")

    # build alfred script filter json payload
    payload = ScriptFilterPayload(variables=session_vars, items=items)

    # output alfred json
    sys.stdout.write(payload.to_json())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
