from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .args import ArgValue
    from .icon import Icon
    from .mods import Mod


class ItemType(StrEnum):
    """
    Alfred Script Filter item `type`.

    DEFAULT: Standard result row.
    FILE: Treat result as a file (Alfred checks existence).
    FILE_SKIPCHECK: Treat as file but skip existence check.
    """

    DEFAULT = "default"
    FILE = "file"
    FILE_SKIPCHECK = "file:skipcheck"


@dataclass(slots=True)
class ResultItem:
    """
    One result row in Alfred's Script Filter `items` array.

    Required:
        title

    Recommended:
        arg, autocomplete

    Notes:
        - If `uid` is set, Alfred may reorder results based on usage.
        - `valid=False` prevents actioning while still displaying.
        - `mods` allows modifier overrides.
        - `variables` are item-scoped session variables.
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
        if not self.title.strip():
            raise ValueError("ResultItem.title must be a non-empty string.")

    def to_alfred(self) -> dict[str, Any]:
        """Serialize to Alfred item JSON."""
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
            icon_obj = self.icon.to_alfred()
            if icon_obj is not None:
                data["icon"] = icon_obj

        if self.mods:
            data["mods"] = {mod.key: mod.payload() for mod in self.mods}

        if self.action is not None:
            data["action"] = self.action

        if self.text is not None:
            data["text"] = dict(self.text)

        if self.quicklookurl is not None:
            data["quicklookurl"] = self.quicklookurl

        if self.variables is not None:
            data["variables"] = dict(self.variables)

        return data
