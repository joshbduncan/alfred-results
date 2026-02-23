# alfred-path-results

Convert filesystem paths into fully-featured [Alfred Script Filter](https://www.alfredapp.com/help/workflows/inputs/script-filter/) JSON result items.

Usable as a **CLI tool** (pipe paths in, get Alfred JSON out) or as a **Python library** (build result items programmatically). No runtime dependencies; requires Python ≥ 3.12.

---

## Installation

```bash
pip install alfred-path-results
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add alfred-path-results
```

### CLI only (no project required)

If you only need the CLI and don't want to add it as a project dependency, install it as a [uv tool](https://docs.astral.sh/uv/concepts/tools/). This makes the `alfred-path-results` command available globally without affecting any project environment:

```bash
uv tool install alfred-path-results
```

### Bundling with a workflow (no install required)

Copy the `alfred_path_results/` package directory into your workflow bundle and add a `run.py` entry point at the workflow root:

```python
#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from alfred_path_results.cli import main

sys.exit(main())
```

Then call it from Alfred's Run Script object:

```bash
python3 run.py
```

---

## CLI usage

The CLI reads newline-delimited paths from **stdin** or a **file** and writes Alfred Script Filter JSON to stdout.

### Read from stdin

```bash
find ~/Projects -maxdepth 1 -type d | alfred-path-results
```

### Read from a file

```bash
alfred-path-results --input paths.txt
```

### Example output

```json
{
  "variables": {},
  "items": [
    {
      "title": "my-project",
      "uid": "a1b2c3d4-...",
      "subtitle": "/Users/me/Projects/my-project",
      "arg": "/Users/me/Projects/my-project",
      "type": "default",
      "icon": {"type": "fileicon", "path": "/Users/me/Projects/my-project"},
      "variables": {"_path": "/Users/me/Projects/my-project"}
    }
  ]
}
```

### Modifier key overrides (`--mod`)

Add actions for modifier keys. Each `--mod` takes three arguments: the key combo, the arg, and the subtitle.

```bash
find ~/Projects -maxdepth 1 -type d \
  | alfred-path-results \
    --mod cmd /tmp/out "Open in Terminal" \
    --mod alt /tmp/out "Copy path"
```

Valid modifier keys: `cmd`, `alt`, `ctrl`, `shift`, `fn` and combinations up to three keys joined with `+` (e.g. `cmd+shift`, `alt+ctrl+fn`).

### Session variables (`--session-var`)

Set Alfred session-level variables included in the top-level `variables` object:

```bash
echo "/tmp/foo" | alfred-path-results \
  --session-var source "file-browser" \
  --session-var ts "2026-01-01"
```

```json
{
  "variables": {"source": "file-browser", "ts": "2026-01-01"},
  "items": [...]
}
```

### Per-result variables (`--result-var`)

Map item-scoped variables to [`pathlib.Path`](https://docs.python.org/3/library/pathlib.html) attributes or methods. The second argument must be a valid `Path` attribute name.

```bash
echo "/Users/me/report.pdf" | alfred-path-results \
  --result-var posix_path as_posix \
  --result-var extension suffix \
  --result-var parent parent
```

This produces `variables` like:

```json
{
  "posix_path": "/Users/me/report.pdf",
  "extension": ".pdf",
  "parent": "/Users/me"
}
```

### All options

```
usage: alfred-path-results [-h] [-i FILE] [-m MOD ARG SUBTITLE]
                           [--session-var KEY VALUE] [--result-var KEY VALUE]
                           [--version]

  -i, --input FILE          input file or '-' for stdin (default: stdin)
  -m, --mod MOD ARG SUB     modifier key override (repeatable)
  --session-var KEY VALUE   Alfred session variable (repeatable)
  --result-var KEY VALUE    per-result variable from pathlib Path (repeatable)
  --version                 show version and exit
```

---

## Python API

### Building result items

```python
from json import dumps
from alfred_path_results.result_item import (
    Icon,
    IconResourceType,
    ItemType,
    Mod,
    ResultItem,
)
from alfred_path_results import path_to_uuid

path = "/Users/me/Downloads"

item = ResultItem(
    uid=path_to_uuid(path),
    title="Downloads",
    subtitle=path,
    arg=path,
    type=ItemType.FILE,
    icon=Icon(path=path, resource_type=IconResourceType.FILEICON),
)

print(dumps({"items": [item.to_alfred()]}))
```

Output:

```json
{
  "items": [
    {
      "title": "Downloads",
      "uid": "...",
      "subtitle": "/Users/me/Downloads",
      "arg": "/Users/me/Downloads",
      "type": "file",
      "icon": {"type": "fileicon", "path": "/Users/me/Downloads"}
    }
  ]
}
```

### Modifier key overrides

```python
item = ResultItem(
    title="report.pdf",
    arg="/Users/me/report.pdf",
    mods=[
        Mod(key="cmd", valid=True, arg="/Users/me/report.pdf", subtitle="Open in Preview"),
        Mod(key="alt", valid=True, arg="/Users/me/report.pdf", subtitle="Reveal in Finder"),
        Mod(key="cmd+shift", valid=False, subtitle="Not available"),
    ],
)
```

### Icons

```python
# Use the file's native Finder icon
Icon(path="/Users/me/report.pdf", resource_type=IconResourceType.FILEICON)

# Use the system icon for a file type (UTI)
Icon(path="com.adobe.pdf", resource_type=IconResourceType.FILETYPE)

# Use a custom image bundled with the workflow
Icon(path="./icons/pdf.png")

# No icon (key omitted from JSON entirely)
Icon()
```

### Stable UIDs with `path_to_uuid`

`path_to_uuid` derives a stable UUID v5 from a canonical path string. Alfred uses the `uid` field to learn from selection history and reorder results. Always pass an expanded, resolved path for consistency:

```python
from pathlib import Path
from alfred_path_results import path_to_uuid

uid = path_to_uuid(str(Path("~/Downloads").expanduser().resolve()))
```

---

## Reference

### `ResultItem` fields

| Field | Type | Description |
|---|---|---|
| `title` | `str` | **Required.** Primary text shown in the result row. |
| `subtitle` | `str` | Secondary text shown below the title. |
| `uid` | `str` | Stable identifier; Alfred learns ordering from this. |
| `arg` | `str \| Sequence[str]` | Argument passed to the next workflow action. |
| `valid` | `bool` | `False` makes the item non-actionable. |
| `autocomplete` | `str` | Text inserted into Alfred's search field on Tab. |
| `match` | `str` | Custom string used for Alfred's built-in filtering. |
| `type` | `ItemType` | `DEFAULT`, `FILE`, or `FILE_SKIPCHECK`. |
| `icon` | `Icon` | Icon displayed beside the result row. |
| `mods` | `list[Mod]` | Modifier key overrides. |
| `action` | `str \| list \| dict` | Universal Actions payload. |
| `text` | `Mapping[str, str]` | `"copy"` and `"largetype"` overrides. |
| `quicklookurl` | `str` | URL or path for Quick Look (Shift / Cmd+Y). |
| `variables` | `Mapping[str, str]` | Item-scoped Alfred session variables. |

### `ItemType` values

| Value | Description |
|---|---|
| `ItemType.DEFAULT` | Standard result row; no filesystem check. |
| `ItemType.FILE` | Alfred checks the path exists before showing the item. |
| `ItemType.FILE_SKIPCHECK` | Treated as a file but existence check is skipped. |

### `IconResourceType` values

| Value | Description |
|---|---|
| `IconResourceType.FILEICON` | Display the native Finder icon of the file at `path`. |
| `IconResourceType.FILETYPE` | Display the system icon for the UTI given in `path`. |

---

## Apple Uniform Type Identifiers (UTI)

When using `IconResourceType.FILETYPE`, the `path` field should be a UTI string. Useful references:

- [Official system-declared UTIs](https://developer.apple.com/documentation/uniformtypeidentifiers/system-declared-uniform-type-identifiers)
- [Alternate community reference](https://gist.github.com/RhetTbull/7221ef3cfd9d746f34b2550d4419a8c2)

---

## License

MIT — see [LICENSE](LICENSE) for details.
