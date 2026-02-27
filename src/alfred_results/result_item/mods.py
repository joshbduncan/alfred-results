"""
mods
----
Alfred Script Filter modifier-key override types.

Defines :data:`VALID_MODIFIER_KEYS`, the :func:`valid_modifiers` helper, and
the :class:`Mod` dataclass that represents one entry inside a result item's
`"mods"` dict.

Alfred modifier JSON example::

    {
        "mods": {
            "cmd": {"valid": true, "arg": "/tmp/foo", "subtitle": "Open in Terminal"},
            "alt+shift": {"valid": false, "subtitle": "Not available"}
        }
    }
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .args import ArgValue
    from .icon import Icon


VALID_MODIFIER_KEYS: Final[tuple[str, ...]] = ("cmd", "alt", "ctrl", "shift", "fn")
"""The individual modifier key names recognized by Alfred.

Used as the base vocabulary for generating all valid single-key and
multi-key combo strings via :func:`valid_modifiers`.
"""


def valid_modifiers(modifier_keys: list[str] | None = None) -> set[str]:
    """Return the complete set of allowed modifier combo strings.

    Alfred accepts the five base modifier keys and any ordered combination of
    up to three of them joined with `"+"`.  Both orderings of a two-key
    combo are considered distinct valid strings (e.g. `"cmd+alt"` and
    `"alt+cmd"` are each valid).

    Args:
        modifier_keys: Keys to use as the base vocabulary.  Defaults to
            :data:`VALID_MODIFIER_KEYS` when `None` or empty.

    Returns:
        A set of all valid combo strings for the given keys, including all
        1-, 2-, and 3-element ordered permutations joined by `"+"`.

    Example::

        valid_modifiers()
        # {"cmd", "alt", ..., "cmd+alt", "alt+cmd", ..., "cmd+alt+shift", ...}

        valid_modifiers(["cmd", "alt"])
        # {"cmd", "alt", "cmd+alt", "alt+cmd"}
    """
    keys = modifier_keys or list(VALID_MODIFIER_KEYS)
    return {"+".join(p) for r in (1, 2, 3) for p in permutations(keys, r)}


# Precomputed once at import time to avoid rebuilding the permutation set on
# every Mod instantiation.
_VALID_MOD_COMBOS: Final[set[str]] = valid_modifiers()


@dataclass(slots=True)
class Mod:
    """An Alfred modifier-key override entry inside a result item's `mods` dict.

    Each :class:`Mod` represents the behavior change that occurs when the
    user holds a specific modifier key (or combination) while the result row
    is highlighted.  Alfred uses :attr:`key` as the JSON dict key and the
    output of :meth:`to_dict` as its value.

    Attributes:
        key: The modifier combo string used as the JSON key in `"mods"`.
            Must be one of the valid single- or multi-key combos accepted by
            Alfred (e.g. `"cmd"`, `"alt"`, `"cmd+shift"`).  Valid
            combos are any 1–3-element ordered permutation of
            `("cmd", "alt", "ctrl", "shift", "fn")` joined with `"+"`.
        valid: Overrides the parent item's actionability for this modifier.
            `True` allows actioning; `False` makes the item non-actionable
            when the modifier is held.
        arg: The argument passed downstream when the user actions the item
            while holding this modifier.  Overrides the parent item's
            :attr:`~ResultItem.arg`.
        subtitle: Subtitle text shown instead of the parent item's subtitle
            while this modifier is held.
        icon: Icon shown instead of the parent item's icon while this
            modifier is held.
        variables: Item-scoped session variables merged into Alfred's
            environment when the item is actioned with this modifier held.

    Raises:
        ValueError: On construction if :attr:`key` is not a valid modifier
            combo string.

    Example::

        mod = Mod(key="cmd", valid=True, arg="/tmp/out", subtitle="Open in Terminal")
        mod.to_dict()
        # {"valid": True, "arg": "/tmp/out", "subtitle": "Open in Terminal"}
    """

    key: str
    valid: bool | None = None
    arg: ArgValue | None = None
    subtitle: str | None = None
    icon: Icon | None = None
    variables: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        """Validate that :attr:`key` is an allowed modifier combo.

        Raises:
            ValueError: If :attr:`key` is not in the precomputed set of valid
                modifier combo strings.
        """
        if self.key not in _VALID_MOD_COMBOS:
            raise ValueError(f"Invalid modifier key combo: {self.key!r}.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the Alfred mod dict (the value under the mod key).

        Builds the dict that Alfred assigns to :attr:`key` inside a result
        item's `"mods"` object.  Only non-`None` fields are included.

        Returns:
            A JSON-serializable dict with any subset of `"valid"`, `"arg"`,
            `"subtitle"`, `"icon"`, and `"variables"` that are set on
            this instance.  Returns an empty dict `{}` when no fields are set.

        Example::

            Mod(key="alt", subtitle="Preview only", valid=False).to_dict()
            # {"subtitle": "Preview only", "valid": False}
        """
        data: dict[str, Any] = {}
        if self.valid is not None:
            data["valid"] = self.valid
        if self.arg is not None:
            data["arg"] = self.arg
        if self.subtitle is not None:
            data["subtitle"] = self.subtitle
        if self.icon is not None:
            icon_obj = self.icon.to_dict()
            if icon_obj is not None:
                data["icon"] = icon_obj
        if self.variables is not None:
            data["variables"] = dict(self.variables)
        return data
