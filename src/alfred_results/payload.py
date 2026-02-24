"""
payload
-------
Alfred Script Filter JSON payload.

Defines :class:`ItemType` (how Alfred treats a result row) and
:class:`ResultItem` (a single entry in Alfred's ``"items"`` array).

Minimal Script Filter JSON example::

    {
        "cache": {
            "seconds": 3600
        }
        "rerun": 1,
        "skipknowledge": true,
        "variables": {
            "fruit": "banana",
            "vegetable": "carrot"
        },
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
from json import dumps
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from alfred_results.result_item import ResultItem

AlfredSessionVariables = dict[str, Any]


class ScriptFilterCache(TypedDict):
    seconds: int  # between 5 and 84600 (24 hours)
    loosereload: bool  # try to show any cached data first


@dataclass(slots=True)
class ScriptFilterPayload:
    cache: ScriptFilterCache | None = None
    rerun: float | None = None
    skipknowledge: bool | None = None
    variables: AlfredSessionVariables | None = None
    items: list[ResultItem] | None = None

    def to_alfred(self) -> str:
        data: dict[str, Any] = {}

        if self.cache is not None:
            data["cache"] = self.cache
        if self.rerun is not None:
            data["rerun"] = self.rerun
        if self.skipknowledge is not None:
            data["skipknowledge"] = self.skipknowledge
        if self.variables is not None:
            data["variables"] = self.variables
        if self.items is not None:
            data["items"] = [item.to_alfred() for item in self.items]

        return dumps(data)
