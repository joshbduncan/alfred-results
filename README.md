# alfred-results 🎩

Turn paths, CSV rows, JSON objects, or plain strings into [Alfred Script Filter](https://www.alfredapp.com/help/workflows/inputs/script-filter/) JSON, without writing a single line of boilerplate.

Use it as a **CLI tool** (pipe data in, get Alfred JSON out) or as a **Python library** (build result items programmatically and compose them however you like). No runtime dependencies. Python ≥ 3.12.

---

## Installation

```bash
pip install alfred-results
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add alfred-results
```

### 🛠️ CLI only (no project required)

If you just want the `alfred-results` command globally without adding it as a project dependency:

```bash
uv tool install alfred-results
```

### 📦 Bundling with a workflow (no install required)

Copy the `alfred_results/` package directory into your workflow bundle and add a `run.py` entry point at the workflow root:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from alfred_results.cli import main

sys.exit(main())
```

Then call it from Alfred's Run Script object:

```bash
python3 run.py
```

---

## CLI usage 🖥️

The CLI reads input from **stdin** or a **file** and writes Alfred Script Filter JSON to stdout. Drop it into any Alfred workflow Run Script object.

```
usage: alfred-results [-h] [-f FORMAT] [-m MOD ARG SUBTITLE]
                      [--result-var KEY VALUE] [--session-var KEY VALUE]
                      [--version]
                      [FILE]
```

### Input formats (`-f` / `--input-format`)

| Format | Input shape | Use case |
|---|---|---|
| `path` *(default)* | One filesystem path per line | `find`, `mdfind`, `ls` pipelines |
| `csv` | CSV with a header row (`title` required) | Spreadsheets, exported data |
| `json` | JSON array of objects (`title` required) | `jq`, `gh`, `brew info --json` |
| `string` | One arbitrary string per line | Labels, commands, bookmarks |

---

### 📁 `path` format (default)

One path per line, piped in or from a file. Each path is expanded, resolved, and converted into a fully-populated result item automatically.

```bash
# Pipe from find
find ~/Projects -maxdepth 1 -type d | alfred-results

# Pass a file
alfred-results paths.txt

# mdfind is a great source too
mdfind -onlyin ~ "kind:pdf" | alfred-results
```

**Example output:**

```json
{
  "variables": {
    "script": "alfred-results",
    "version": "0.1.0"
  },
  "items": [
    {
      "title": "my-project",
      "uid": "a1b2c3d4-...",
      "subtitle": "/Users/me/Projects/my-project",
      "arg": "/Users/me/Projects/my-project",
      "type": "default",
      "icon": {"type": "fileicon", "path": "/Users/me/Projects/my-project"},
      "variables": {
        "_path": "/Users/me/Projects/my-project",
        "_parent": "/Users/me/Projects"
      }
    }
  ]
}
```

> 💡 `_path` and `_parent` are always injected as item-scoped variables so downstream workflow objects can reference them without extra wiring.

---

### 📊 `csv` format

Pass a CSV file with a header row. `title` is the only required column. Everything else is optional and unknown columns are ignored.

```
title,subtitle,arg,type,icon,uid
Downloads,Your downloads folder,/Users/me/Downloads,default,,
report.pdf,Q4 financials,/Users/me/report.pdf,file,,
```

```bash
alfred-results --input-format csv data.csv
```

**Supported columns:**

| Column | Required | Description |
|---|---|---|
| `title` | ✅ | Primary text shown in Alfred |
| `subtitle` | — | Secondary text below the title |
| `arg` | — | Argument passed to the next workflow action |
| `uid` | — | Stable identifier for Alfred's ordering learning |
| `type` | — | `default`, `file`, or `file:skipcheck` |
| `icon` | — | Path to an icon file |

---

### 🔧 `json` format

Pass a JSON array of objects, perfect for piping output from tools that already speak JSON.

```bash
# From a file
alfred-results --input-format json data.json

# Pipe from jq
curl -s https://api.example.com/items | jq '[.[] | {title: .name, arg: .url}]' \
  | alfred-results --input-format json

# List GitHub repos with alfred-results
gh repo list --json name,url --jq '[.[] | {title: .name, subtitle: .url, arg: .url}]' \
  | alfred-results --input-format json

# Installed Homebrew formulae
brew info --json=v2 --installed \
  | jq '[.formulae[] | {title: .name, subtitle: .desc, arg: .name}]' \
  | alfred-results --input-format json
```

**Supported keys:** same as CSV: `title` (required), `subtitle`, `arg`, `uid`, `type`, `icon`. Additional keys are silently ignored.

---

### 🔤 `string` format

One string per line becomes the `title` of a plain result item with no path metadata. Great for lists of commands, bookmarks, or anything title-only.

```bash
printf "Open Safari\nOpen Terminal\nOpen Finder" | alfred-results --input-format string

alfred-results --input-format string bookmarks.txt
```

---

### 🎛️ Modifier key overrides (`--mod`)

Add actions for when the user holds a modifier key while highlighting a result. Each `--mod` takes three arguments: the key combo, the arg, and the subtitle. Repeat it for multiple modifiers.

```bash
find ~/Projects -maxdepth 1 -type d \
  | alfred-results \
    --mod cmd  "{query}" "Open in Terminal" \
    --mod alt  "{query}" "Reveal in Finder" \
    --mod shift "{query}" "Copy path to clipboard"
```

Valid modifier keys: `cmd`, `alt`, `ctrl`, `shift`, `fn`, and any combination of up to three joined with `+` (e.g. `cmd+shift`, `alt+ctrl+fn`).

---

### 🌐 Session variables (`--session-var`)

Set top-level Alfred session variables included in the payload's `variables` object. These are available to all downstream workflow objects regardless of which item the user picks.

```bash
echo "/tmp/foo" | alfred-results \
  --session-var source "file-browser" \
  --session-var mode "open"
```

```json
{
  "variables": {
    "script": "alfred-results",
    "version": "0.1.0",
    "source": "file-browser",
    "mode": "open"
  },
  "items": [...]
}
```

---

### 📌 Per-result variables (`--result-var`)

Attach item-scoped variables to every result.

- **`path`**: `_path` and `_parent` are always injected automatically; `--result-var` adds to them. The value is first resolved as a [`pathlib.Path`](https://docs.python.org/3/library/pathlib.html) attribute name (e.g. `suffix`, `stem`, `parent`); if no such attribute exists the raw string is used.
- **`csv` / `json`**: the value is first looked up as a column or key name in the current row; if not found the raw string is used.
- **`string`**: the raw string is always used.

```bash
echo "/Users/me/report.pdf" | alfred-results \
  --result-var file_ext  suffix \
  --result-var file_stem stem \
  --result-var file_dir  parent
```

Produces `variables` on each item:

```json
{
  "file_ext": ".pdf",
  "file_stem": "report",
  "file_dir": "/Users/me"
}
```

---

## Python API 🐍

### Quick start

```python
from alfred_results.payload import ScriptFilterPayload
from alfred_results.result_item import ResultItem

items = [
    ResultItem.from_path("/Users/me/Downloads"),
    ResultItem.from_path("/Users/me/Documents"),
]

payload = ScriptFilterPayload(items=items)
print(payload.to_json())
```

That's it. `to_json()` produces the complete Alfred Script Filter JSON string, ready to print to stdout.

---

### `ResultItem.from_path()` ✨

The fastest way to build a result item from a filesystem path. Automatically:
- Expands `~` and resolves symlinks
- Derives a stable UUID `uid` so Alfred can learn your preferences
- Sets `title` (filename), `subtitle` (full path), `arg` (full path), `icon` (native Finder icon), and `type`
- Injects `_path` and `_parent` as item-scoped variables

```python
from alfred_results.result_item import ResultItem

item = ResultItem.from_path("/Users/me/Downloads")
print(item.to_dict())
```

```json
{
  "title": "Downloads",
  "uid": "a696dbaa-...",
  "subtitle": "/Users/me/Downloads",
  "arg": "/Users/me/Downloads",
  "type": "default",
  "icon": {"type": "fileicon", "path": "/Users/me/Downloads"},
  "variables": {
    "_path": "/Users/me/Downloads",
    "_parent": "/Users/me"
  }
}
```

Pass `mods` and `variables` to extend it:

```python
from alfred_results.result_item import Mod, ResultItem

item = ResultItem.from_path(
    "/Users/me/report.pdf",
    mods=[
        Mod(key="cmd", valid=True, arg="/Users/me/report.pdf", subtitle="Open in Preview"),
        Mod(key="alt", valid=True, subtitle="Reveal in Finder"),
    ],
    variables={"category": "reports"},
)
```

---

### Building items manually 🔩

For full control over every field, construct `ResultItem` directly:

```python
from alfred_results.result_item import Icon, IconResourceType, ItemType, ResultItem
from alfred_results import path_to_uuid

path = "/Users/me/Downloads"

item = ResultItem(
    uid=path_to_uuid(path),
    title="Downloads",
    subtitle="Your downloads folder",
    arg=path,
    type=ItemType.FILE,
    icon=Icon(path=path, resource_type=IconResourceType.FILEICON),
    valid=True,
    autocomplete="Downloads",
    quicklookurl=path,
    variables={"folder": "downloads"},
)
```

Only `title` is required, every other field is optional and omitted from the JSON if not set.

---

### Icons 🖼️

```python
from alfred_results.result_item import Icon, IconResourceType

# Native Finder icon of the file or folder at this path
Icon(path="/Users/me/Downloads", resource_type=IconResourceType.FILEICON)
# → {"type": "fileicon", "path": "/Users/me/Downloads"}

# System icon for a Uniform Type Identifier (UTI)
Icon(path="com.adobe.pdf", resource_type=IconResourceType.FILETYPE)
# → {"type": "filetype", "path": "com.adobe.pdf"}

# Custom image bundled with the workflow (relative to the workflow root)
Icon(path="./icons/star.png")
# → {"path": "./icons/star.png"}

# No icon at all, the key is omitted from the JSON entirely
Icon()
# → None (omitted)
```

> 🍎 See [Apple's UTI reference](https://developer.apple.com/documentation/uniformtypeidentifiers/system-declared-uniform-type-identifiers) or this [community UTI list](https://gist.github.com/RhetTbull/7221ef3cfd9d746f34b2550d4419a8c2) for common type identifiers.

---

### Modifier key overrides 🎹

```python
from alfred_results.result_item import Mod, ResultItem

item = ResultItem(
    title="report.pdf",
    arg="/Users/me/report.pdf",
    mods=[
        # cmd → open in Preview
        Mod(key="cmd", valid=True, arg="/Users/me/report.pdf", subtitle="Open in Preview"),
        # alt → reveal in Finder
        Mod(key="alt", valid=True, arg="/Users/me/report.pdf", subtitle="Reveal in Finder"),
        # cmd+shift → disabled with a message
        Mod(key="cmd+shift", valid=False, subtitle="Not available right now"),
    ],
)
```

```json
{
  "title": "report.pdf",
  "arg": "/Users/me/report.pdf",
  "mods": {
    "cmd":       {"valid": true,  "arg": "/Users/me/report.pdf", "subtitle": "Open in Preview"},
    "alt":       {"valid": true,  "arg": "/Users/me/report.pdf", "subtitle": "Reveal in Finder"},
    "cmd+shift": {"valid": false, "subtitle": "Not available right now"}
  }
}
```

Valid modifier keys: `cmd`, `alt`, `ctrl`, `shift`, `fn`, any 1–3 key ordered combination joined with `+`.

---

### The full payload 📦

`ScriptFilterPayload` wraps your items into the complete top-level Alfred Script Filter response:

```python
from alfred_results.payload import ScriptFilterCache, ScriptFilterPayload
from alfred_results.result_item import ResultItem

payload = ScriptFilterPayload(
    items=[
        ResultItem.from_path("/Users/me/Downloads"),
        ResultItem.from_path("/Users/me/Documents"),
    ],
    variables={"workflow": "file-browser"},
    rerun=1.0,                                      # re-run every second
    skipknowledge=True,                             # don't reorder by usage
    cache=ScriptFilterCache(seconds=30, loosereload=True),
)

# Print compact JSON for Alfred
print(payload.to_json())

# Pretty-print for debugging
print(payload.to_json(indent=2))

# Get a plain Python dict if you need to inspect or extend it
data = payload.to_dict()
```

```json
{
  "cache": {"seconds": 30, "loosereload": true},
  "rerun": 1.0,
  "skipknowledge": true,
  "variables": {
    "script": "alfred-results",
    "version": "0.1.0",
    "workflow": "file-browser"
  },
  "items": [...]
}
```

> 💡 `script` and `version` are always injected into `variables` automatically so downstream workflow objects always know what generated the payload. User-supplied variables win on collision.

---

### Caching ⚡

`ScriptFilterCache` controls how Alfred caches results between script invocations:

```python
from alfred_results.payload import ScriptFilterCache

# Cache for 5 minutes, show stale results immediately while reloading
ScriptFilterCache(seconds=300, loosereload=True)

# Cache for 1 hour, wait for fresh results before showing anything
ScriptFilterCache(seconds=3600)
```

`seconds` must be between `5` and `86400` (24 hours).  `loosereload=True` tells Alfred to show the cached results immediately while re-running the script in the background, which is great for slow data sources.

---

### Stable UIDs with `path_to_uuid` 🔑

Alfred uses the `uid` field to learn from your selection history and reorder results over time. `path_to_uuid` derives a deterministic UUID v5 from a resolved path so the same path always produces the same `uid`, no database required.

```python
from pathlib import Path
from alfred_results import path_to_uuid

uid = path_to_uuid(str(Path("~/Downloads").expanduser().resolve()))
# → "a696dbaa-739b-5781-8e08-7e38648f678a"  (stable across runs)
```

`ResultItem.from_path()` calls this automatically. You only need it when building items manually.

---

### Validating modifier keys 🛡️

Check whether a key combo is valid before constructing a `Mod`:

```python
from alfred_results.result_item import VALID_MODIFIER_KEYS, valid_modifiers

# The five base keys
print(VALID_MODIFIER_KEYS)
# ("cmd", "alt", "ctrl", "shift", "fn")

# All valid single, double, and triple combos
combos = valid_modifiers()
print("cmd+alt" in combos)   # True
print("cmd+cmd" in combos)   # False
```

---

## Reference 📖

### `ResultItem` fields

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `str` | ✅ | Primary text shown in the result row |
| `subtitle` | `str` | — | Secondary text below the title |
| `uid` | `str` | — | Stable identifier (Alfred learns ordering from this) |
| `arg` | `str \| Sequence[str]` | — | Argument passed to the next workflow action |
| `valid` | `bool` | — | `False` makes the item non-actionable |
| `autocomplete` | `str` | — | Text inserted into Alfred's search field on Tab |
| `match` | `str` | — | Custom string for Alfred's built-in filtering |
| `type` | `ItemType` | — | `DEFAULT`, `FILE`, or `FILE_SKIPCHECK` |
| `icon` | `Icon` | — | Icon displayed beside the result row |
| `mods` | `list[Mod]` | — | Modifier key overrides (unique keys required) |
| `action` | `str \| list \| dict` | — | Universal Actions payload |
| `text` | `Mapping[str, str]` | — | `"copy"` and `"largetype"` overrides |
| `quicklookurl` | `str` | — | URL or path for Quick Look (Shift / Cmd+Y) |
| `variables` | `Mapping[str, str]` | — | Item-scoped Alfred session variables |

### `ScriptFilterPayload` fields

| Field | Type | Required | Description |
|---|---|---|---|
| `items` | `list[ResultItem]` | — | Result items to display in Alfred |
| `variables` | `Mapping[str, str]` | — | Top-level session variables |
| `rerun` | `float` | — | Re-run interval in seconds (0.1–5.0) |
| `skipknowledge` | `bool` | — | Skip Alfred's learned ordering for this response |
| `cache` | `ScriptFilterCache` | — | Caching configuration |

### `ItemType` values

| Value | Alfred JSON | Description |
|---|---|---|
| `ItemType.DEFAULT` | `"default"` | Standard result (no filesystem check) |
| `ItemType.FILE` | `"file"` | Alfred checks the path exists before showing |
| `ItemType.FILE_SKIPCHECK` | `"file:skipcheck"` | Treated as file but existence check skipped |

### `IconResourceType` values

| Value | Alfred JSON | Description |
|---|---|---|
| `IconResourceType.FILEICON` | `"fileicon"` | Native Finder icon of the file at `path` |
| `IconResourceType.FILETYPE` | `"filetype"` | System icon for the UTI given in `path` |

---

## License

MIT. See [LICENSE](LICENSE) for details.
