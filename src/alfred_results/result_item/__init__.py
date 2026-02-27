"""
result_item
-----------
Public API for Alfred Script Filter result item types.

Exports
-------
ResultItem
    A single row in Alfred's `items` array.
ItemType
    Enum controlling how Alfred treats a result (file vs default).
Icon
    The `icon` sub-object attached to a result item or modifier.
IconResourceType
    Enum controlling how Alfred resolves an icon path (fileicon / filetype).
ArgValue
    Type alias for a scalar or list argument value (`str | Sequence[str]`).
Mod
    A modifier-key override entry inside a result item's `mods` dict.
VALID_MODIFIER_KEYS
    Tuple of the five base Alfred modifier key names accepted by :class:`Mod`.
valid_modifiers
    Return the full set of valid single- and multi-key modifier combo strings.
"""

from .args import ArgValue
from .icon import Icon, IconResourceType
from .item import ItemType, ResultItem
from .mods import VALID_MODIFIER_KEYS, Mod, valid_modifiers

__all__ = [
    "ResultItem",
    "ItemType",
    "Icon",
    "IconResourceType",
    "ArgValue",
    "Mod",
    "VALID_MODIFIER_KEYS",
    "valid_modifiers",
]
