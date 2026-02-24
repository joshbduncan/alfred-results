"""
result_item
-----------
Public API for Alfred Script Filter result item types.

Exports
-------
ResultItem
    A single row in Alfred's ``items`` array.
ItemType
    Enum controlling how Alfred treats a result (file vs default).
Icon
    The ``icon`` sub-object attached to a result item or modifier.
IconResourceType
    Enum controlling how Alfred resolves an icon path (fileicon / filetype).
ArgValue
    Type alias for a scalar or list argument value (``str | Sequence[str]``).
Mod
    A modifier-key override entry inside a result item's ``mods`` dict.
"""

from .args import ArgValue
from .icon import Icon, IconResourceType
from .item import ItemType, ResultItem
from .mods import Mod

__all__ = [
    "ResultItem",
    "ItemType",
    "Icon",
    "IconResourceType",
    "ArgValue",
    "Mod",
]
