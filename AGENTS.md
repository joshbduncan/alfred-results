# AGENTS.md — alfred-path-results

A Python helper library that converts filesystem paths into Alfred Script Filter
JSON result items. No runtime dependencies; targets Python ≥ 3.12.

---

## Environment Setup

**Package manager:** [`uv`](https://docs.astral.sh/uv/)

```bash
uv sync          # Install all dependencies (including dev: ruff, ty)
```

Python version is pinned to **3.12** via `.python-version`.

---

## Build / Package

```bash
uv build         # Produces dist/ with sdist + wheel
```

---

## Lint & Format

[`ruff`](https://docs.astral.sh/ruff/) handles both linting and formatting.

```bash
uv run ruff check .            # Lint
uv run ruff check --fix .      # Lint and auto-fix
uv run ruff format .           # Format
uv run ruff format --check .   # Verify formatting without changing files
```

Run both together before committing:

```bash
uv run ruff check --fix . && uv run ruff format .
```

---

## Type Checking

[`ty`](https://github.com/astral-sh/ty) (Astral's type checker) is used instead
of mypy or pyright.

```bash
uv run ty check
```

The package is PEP 561 compliant (`py.typed` marker present).

---

## Tests

**No test suite currently exists.** When tests are added, `pytest` is the expected
framework. Standard commands once tests exist:

```bash
uv run pytest                                        # Run all tests
uv run pytest tests/test_foo.py                      # Run a single file
uv run pytest tests/test_foo.py::test_my_function    # Run a single test
uv run pytest -v                                     # Verbose output
```

---

## CLI

```bash
uv run alfred-path-results --help
```

---

## Code Style

### Formatting (ruff.toml)

| Setting              | Value             |
|----------------------|-------------------|
| Line length          | 88 (Black-compat) |
| Indent               | 4 spaces          |
| Quotes               | Double            |
| Magic trailing comma | Respected         |
| Target Python        | py312+            |

### Enabled Lint Rules

- `E` — pycodestyle errors
- `F` — Pyflakes
- `UP` — pyupgrade (enforce modern syntax)
- `B` — flake8-bugbear
- `SIM` — flake8-simplify
- `I` — isort (import ordering)
- `C4` — flake8-comprehensions
- `TCH` — flake8-type-checking (enforce `TYPE_CHECKING` guards)

---

## Naming Conventions

| Construct              | Style                        | Example                              |
|------------------------|------------------------------|--------------------------------------|
| Packages / modules     | `snake_case`                 | `result_item`, `alfred_path_results` |
| Classes                | `PascalCase`                 | `ResultItem`, `IconResourceType`     |
| Functions / variables  | `snake_case`                 | `parse_input`, `result_variables`    |
| Public constants       | `UPPER_SNAKE_CASE` + `Final` | `VALID_MODIFIER_KEYS`                |
| Private module-level   | `_UPPER_SNAKE_CASE`          | `_VALID_MOD_COMBOS`                  |
| Enum values            | `UPPER_SNAKE_CASE`           | `ItemType.DEFAULT`                   |

---

## Imports

- Always include `from __future__ import annotations` at the top of every module
  (enables deferred annotation evaluation and forward references).
- Use `TYPE_CHECKING` guards for type-only imports to avoid runtime overhead:
  ```python
  from __future__ import annotations

  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from collections.abc import Mapping, Sequence
      from .args import ArgValue
  ```
- Use `collections.abc` types (`Mapping`, `Sequence`) rather than `typing`
  equivalents.
- Use relative imports within the package (`from .result_item import Icon`).
- Define `__all__` in `__init__.py` files to explicitly control the public API.
- Import order enforced by ruff/isort: stdlib → third-party → local, each group
  separated by a blank line.
- Defer imports inside methods (e.g. classmethods) when needed to avoid circular
  imports — this is preferable to restructuring the module graph.

---

## Type Annotations

- Fully annotate all function signatures, including return types.
- Use `X | Y` union syntax (not `Union[X, Y]`); enabled by `from __future__ import annotations`.
- Use `X | None` (not `Optional[X]`).
- Prefer `collections.abc` abstract types for parameters (`Sequence`, `Mapping`).
- Use `Final` for constants: `VALID_MODIFIER_KEYS: Final[tuple[str, ...]] = (...)`.
- The package is typed (PEP 561); keep `py.typed` present.

---

## Data Classes

- Use `@dataclass(slots=True)` for all model classes (reduces memory, enforces
  explicit attribute declaration).
- Validate in `__post_init__`; raise `ValueError` with a descriptive message.
- Default optional fields to `None` rather than a sentinel.
- Use `@classmethod` factory methods (e.g. `from_path`) to encapsulate common
  construction patterns and spare callers from boilerplate.

  ```python
  @dataclass(slots=True)
  class ResultItem:
      title: str
      subtitle: str | None = None

      def __post_init__(self) -> None:
          if not self.title.strip():
              raise ValueError("ResultItem.title must be a non-empty string.")
  ```

---

## Enums

- Use `StrEnum` for all enumerations so values can be used directly as strings
  without calling `.value`.

  ```python
  from enum import StrEnum

  class ItemType(StrEnum):
      DEFAULT = "default"
      FILE = "file"
  ```

---

## Serialization (`to_alfred()` / `payload()` methods)

- Return `dict[str, Any]`; never use `dataclasses.asdict()` (it recurses too
  eagerly and loses control).
- Gate every optional field with `if field is not None:` before adding it to the
  dict — omit falsy/unset keys from output.
- Return `None` from `to_alfred()` when the whole object should be omitted from
  the parent payload (e.g. `Icon.to_alfred()` returns `None` when no path is set).

  ```python
  def to_alfred(self) -> dict[str, Any]:
      out: dict[str, Any] = {"title": self.title}
      if self.subtitle is not None:
          out["subtitle"] = self.subtitle
      return out
  ```

---

## Error Handling

- Raise `ValueError` with descriptive messages for invalid input; use `!r` repr
  formatting for the bad value:
  ```python
  raise ValueError(f"Invalid modifier key combo: {self.key!r}.")
  ```
- In the CLI (`cli.py`), route all errors through `parser.error(...)` for
  consistent argparse-style output to stderr.
- Catch `OSError` when performing file I/O and surface `e.strerror` to the user.
- Catch `AttributeError` and `ValueError` in `main()` and forward to
  `parser.error()`.
- Initialise variables before `try/except` blocks so they are always bound from
  the type checker's perspective, even though `parser.error()` exits unconditionally.

---

## Project Layout

```
src/
└── alfred_path_results/
    ├── __init__.py          # Package init; lazy __version__ + _get_version()
    ├── __main__.py          # python -m alfred_path_results entry point
    ├── cli.py               # argparse CLI entry point
    ├── py.typed             # PEP 561 marker
    ├── utils.py             # Shared utilities (path_to_uuid, _PATH_UUID_NAMESPACE)
    └── result_item/
        ├── __init__.py      # Public re-exports + __all__
        ├── args.py          # ArgValue type alias
        ├── icon.py          # Icon dataclass, IconResourceType StrEnum
        ├── item.py          # ResultItem dataclass, ItemType StrEnum
        └── mods.py          # Mod dataclass, valid_modifiers helper
```

New public types belong in `src/alfred_path_results/result_item/` with a
corresponding re-export in `result_item/__init__.py` and `__all__`.

Shared utilities with no CLI or Alfred-type dependencies belong in `utils.py`.
