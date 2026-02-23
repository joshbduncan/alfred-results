import argparse
import sys
from collections.abc import Sequence
from contextlib import nullcontext
from importlib.metadata import version
from json import dumps
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .result_item import Icon, IconResourceType, ItemType, Mod, ResultItem


def parse_input(val: str) -> list[str]:
    cm = nullcontext(sys.stdin) if val == "-" else open(val)  # noqa: SIM115

    with cm as f:
        return [ln.strip() for ln in f if ln.strip()]


def parse_session_vars(val: list[list[str]]) -> dict[str, str]:
    return dict(val)


def get_path_attribute(p: Path, key: str) -> Any:
    attr = getattr(p, key)
    return attr() if callable(attr) else attr


def parse_result_vars(p: Path, val: list[list[str]]) -> dict[str, str]:
    d = {}
    for k, v in val:
        d[k] = str(get_path_attribute(p, v))
    return d


def parse_mods(val: list[list[str]]) -> list[Mod]:
    return [
        Mod(key=key, valid=True, arg=arg, subtitle=subtitle)
        for key, arg, subtitle in val
    ]


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""

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
        help="alfred result item variable from from pathlib Path object (ex. --item-var path as_posix)",  # noqa: E501
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('alfred-path-results')}",
    )

    return parser


def path_to_uuid(path: str) -> str:
    return str(uuid5(NAMESPACE_URL, path))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Parses command line arguments and dispatches to the appropriate subcommand handler.
    If no arguments are provided, displays help message.

    Args:
        argv: Command line arguments. If None, uses sys.argv. Defaults to None.

    Returns:
        Exit status code.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # process stdin (or --input path)
    if args.input == "-" and sys.stdin.isatty():
        parser.error("no stdin provided")

    try:
        paths: list[str] = parse_input(args.input)
    except OSError as e:
        parser.error(f"can't open '{args.input}': {e.strerror}")

    if not paths:
        parser.error("no paths found")

    # process session variables
    session_vars = parse_session_vars(args.session_var)

    # process modifiers
    try:
        mods: list[Mod] = parse_mods(args.mod) if args.mod is not None else []
    except ValueError as e:
        parser.error(str(e))

    # build alfred result dict
    items: list[ResultItem] = []
    for i in paths:
        p = Path(i)
        icon = Icon(path=str(p), resource_type=IconResourceType.FILEICON)

        if args.result_var is not None:
            try:
                result_variables = parse_result_vars(p, args.result_var)
            except AttributeError as e:
                parser.error(str(e))
        else:
            result_variables = {"_path": p.as_posix()}

        item = ResultItem(
            uid=path_to_uuid(str(p.expanduser().resolve())),
            title=p.name,
            subtitle=p.as_posix(),
            arg=p.as_posix(),
            icon=icon,
            type=ItemType.FILE if p.is_file() else ItemType.DEFAULT,
            mods=mods,
            variables=result_variables,
        )
        items.append(item)

    # output alfred json
    print(
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
