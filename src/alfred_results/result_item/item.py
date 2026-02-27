"""
item
----
Alfred Script Filter result item types.

Defines :class:`ItemType` (how Alfred treats a result row) and
:class:`ResultItem` (a single entry in Alfred's `"items"` array).

Minimal Script Filter JSON example::

    {
        "items": [
            {
                "title": "My Result",
                "subtitle": "A description",
                "arg": "/path/to/file",
                "uid": "some-stable-uid"
            }
        ]
    }
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .args import ArgValue
    from .icon import Icon
    from .mods import Mod


class ItemType(StrEnum):
    """How Alfred treats a result row.

    Attributes:
        DEFAULT: A standard, non-file result row.  Alfred performs no
            filesystem existence check.
        FILE: Alfred treats the result as a file path.  Alfred verifies
            that the path exists before displaying the item; items pointing
            to non-existent paths are hidden.
        FILE_SKIPCHECK: Same as :attr:`FILE` but Alfred skips the existence
            check.  Useful for items that represent virtual or remote paths.
    """

    DEFAULT = "default"
    FILE = "file"
    FILE_SKIPCHECK = "file:skipcheck"


@dataclass(slots=True)
class ResultItem:
    """A single row in Alfred's Script Filter `items` array.

    Only :attr:`title` is required by Alfred's schema.  All other fields are
    optional; unset fields (`None`) are omitted from the serialized JSON
    produced by :meth:`to_dict`.

    Attributes:
        title: The primary text shown in the Alfred result row.  Must be a
            non-empty, non-whitespace string.
        subtitle: Secondary text shown below the title in the result row.
        uid: A stable, unique identifier for this result.  When set, Alfred
            learns from the user's selection history and may reorder results
            accordingly.  Should be consistent across invocations for the
            same logical item (e.g. a UUID derived from the file path).
        arg: The argument passed to the next action in Alfred's workflow when
            this item is actioned.  Accepts either a single string or a list
            of strings (see :data:`~alfred_results.result_item.ArgValue`).
        valid: Controls whether the item can be actioned.  `True` (default
            when omitted) allows actioning; `False` turns the item into a
            non-actionable label row (useful for section headers or error
            messages).
        autocomplete: The string inserted into Alfred's search field when the
            user presses Tab on this item.  Useful for building hierarchical
            navigation.
        match: A custom string used for Alfred's filtering when the Script
            Filter is configured with Alfred's built-in matching.  Defaults to
            the title when not set.
        type: Controls how Alfred categorizes this result; see
            :class:`ItemType`.  Omit to use Alfred's default behavior.
        icon: The icon displayed next to the result row; see
            :class:`~alfred_results.result_item.Icon`.
        mods: A list of :class:`~alfred_results.result_item.Mod`
            instances that override the item's behavior when the user holds a
            modifier key (cmd, alt, ctrl, shift, fn, or combinations).  Each
            :attr:`~Mod.key` in the list must be unique; duplicate keys raise
            :exc:`ValueError` on construction because :meth:`to_dict` converts
            the list to a dict keyed by :attr:`~Mod.key` and duplicate entries
            would silently overwrite each other.
        action: The Universal Action payload passed to Alfred when the item is
            actioned via Universal Actions.  Can be a string, a list of
            strings, or a typed mapping (`{"file": [...], "url": [...]}`)
            following Alfred's Universal Actions schema.
        text: Copy/paste and Large Type overrides.  Expected keys are
            `"copy"` (text placed on the clipboard) and `"largetype"`
            (text displayed in Large Type mode).
        quicklookurl: URL or file path opened when the user invokes Quick Look
            on this result (Shift or Cmd+Y).
        variables: Item-scoped Alfred session variables.  These are merged
            into Alfred's environment when this item is actioned and are
            available to downstream workflow objects.

    Example::

        item = ResultItem(
            uid="3d4c1e2a-...",
            title="Downloads",
            subtitle="/Users/me/Downloads",
            arg="/Users/me/Downloads",
            type=ItemType.FILE,
            icon=Icon(
                path="/Users/me/Downloads",
                resource_type=IconResourceType.FILEICON,
            ),
        )
        payload = item.to_dict()
    """

    title: str

    subtitle: str | None = None
    uid: str | None = None

    arg: ArgValue | None = None
    valid: bool | None = None
    autocomplete: str | None = None
    match: str | None = None

    type: ItemType | None = None
    icon: Icon | None = None

    mods: list[Mod] | None = None
    action: str | Sequence[str] | Mapping[str, Any] | None = None
    text: Mapping[str, str] | None = None
    quicklookurl: str | None = None
    variables: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        """Validate field constraints after dataclass initialization.

        Raises:
            ValueError: If :attr:`title` is empty or contains only whitespace.
            ValueError: If :attr:`mods` contains duplicate :attr:`~Mod.key`
                values.
        """
        if not self.title.strip():
            raise ValueError("ResultItem.title must be a non-empty string.")
        if self.mods is not None:
            seen: set[str] = set()
            for mod in self.mods:
                if mod.key in seen:
                    raise ValueError(
                        f"ResultItem.mods contains duplicate modifier key {mod.key!r}."
                    )
                seen.add(mod.key)

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        mods: list[Mod] | None = None,
        variables: Mapping[str, str] | None = None,
    ) -> ResultItem:
        """Construct a :class:`ResultItem` from a filesystem path.

        Handles the boilerplate of building a fully-populated result item from
        a path: expanding `~`, resolving symlinks, deriving a stable UUID
        `uid`, setting `title`, `subtitle`, `arg`, `icon`, and
        `type` automatically.

        The default `variables` dict always contains `"_path"` (the POSIX
        representation of the input path) and `"_parent"` (the POSIX path of
        the parent directory).  Pass an explicit `variables` mapping to merge
        additional keys or override the defaults; user-supplied values win on
        collision.

        Args:
            path: The filesystem path to convert.  May be a :class:`~pathlib.Path`
                object or a string (including `~`-prefixed paths).
            mods: Optional list of :class:`~alfred_results.result_item.Mod`
                modifier-key overrides to attach to the item.
            variables: Optional item-scoped Alfred session variables merged over
                the defaults (`{"_path": ..., "_parent": ...}`) when provided.
                Defaults to the built-in `_path` and `_parent` keys when
                `None`.

        Returns:
            A fully-populated :class:`ResultItem` ready for serialization via
            :meth:`to_dict`.

        Example::

            item = ResultItem.from_path("/Users/me/Downloads")
            item.to_dict()
            # {
            #   "title": "Downloads",
            #   "uid": "...",
            #   "subtitle": "/Users/me/Downloads",
            #   "arg": "/Users/me/Downloads",
            #   "type": "default",
            #   "icon": {"type": "fileicon", "path": "/Users/me/Downloads"},
            #   "variables": {"_path": "/Users/me/Downloads", "_parent": "/Users/me"}
            # }
        """
        from ..utils import path_to_uuid
        from .icon import Icon, IconResourceType

        p = Path(path)
        p_resolved = p.expanduser().resolve()
        posix = p.as_posix()

        # Merge caller-supplied variables over built-in defaults; caller wins.
        default_variables = {
            "_path": posix,
            "_parent": p.parent.as_posix(),
        }
        user_variables: dict[str, str] = (
            dict(variables.items()) if variables is not None else {}
        )

        return cls(
            uid=path_to_uuid(str(p_resolved)),
            title=p.name or posix,
            subtitle=posix,
            arg=posix,
            icon=Icon(path=str(p_resolved), resource_type=IconResourceType.FILEICON),
            type=ItemType.FILE if p.is_file() else ItemType.DEFAULT,
            mods=mods,
            variables=default_variables | user_variables,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this item to Alfred's Script Filter JSON shape.

        Builds the dict that represents one entry in Alfred's `"items"`
        array.  Only fields that have been explicitly set (i.e. are not
        `None`) are included; this keeps the JSON output minimal and avoids
        sending unexpected keys to Alfred.

        The `mods` list is converted to a dict keyed by modifier combo
        string (e.g. `{"cmd": {...}, "alt+shift": {...}}`), matching
        Alfred's expected schema.

        Returns:
            A JSON-serializable dict conforming to the Alfred Script Filter
            result item schema.

        Example::

            item = ResultItem(title="foo", arg="bar", uid="abc-123")
            item.to_dict()
            # {"title": "foo", "arg": "bar", "uid": "abc-123"}
        """
        data: dict[str, Any] = {"title": self.title}

        if self.uid is not None:
            data["uid"] = self.uid
        if self.subtitle is not None:
            data["subtitle"] = self.subtitle
        if self.match is not None:
            data["match"] = self.match
        if self.autocomplete is not None:
            data["autocomplete"] = self.autocomplete

        if self.arg is not None:
            data["arg"] = self.arg
        if self.valid is not None:
            data["valid"] = self.valid

        if self.type is not None:
            data["type"] = str(self.type)

        if self.icon is not None:
            icon_obj = self.icon.to_dict()
            if icon_obj is not None:
                data["icon"] = icon_obj

        if self.mods:
            data["mods"] = {mod.key: mod.to_dict() for mod in self.mods}

        if self.action is not None:
            data["action"] = self.action

        if self.text is not None:
            data["text"] = dict(self.text)

        if self.quicklookurl is not None:
            data["quicklookurl"] = self.quicklookurl

        if self.variables is not None:
            data["variables"] = dict(self.variables)

        return data
