from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .args import ArgValue
    from .icon import Icon


VALID_MODIFIER_KEYS: Final[tuple[str, ...]] = ("cmd", "alt", "ctrl", "shift", "fn")


def valid_modifiers(modifier_keys: list[str] | None = None) -> set[str]:
    """
    Return the set of allowed modifier combo strings.

    Alfred accepts: cmd, alt, ctrl, shift, fn, and combinations using "+".
    This generates order-sensitive combos (both "cmd+shift" and "shift+cmd"),
    and limits to 1, 2, or 3-part combos.

    Args:
        modifier_keys: Keys to include. Defaults to VALID_MODIFIER_KEYS.

    Returns:
        A set of valid combo strings (e.g., {"cmd", "cmd+alt", "alt+cmd", ...}).
    """
    keys = modifier_keys or list(VALID_MODIFIER_KEYS)
    return {"+".join(p) for r in (1, 2, 3) for p in permutations(keys, r)}


# Precompute once; avoids rebuilding the set for every Mod instance.
_VALID_MOD_COMBOS: Final[set[str]] = valid_modifiers()


@dataclass(slots=True)
class Mod:
    """
    Alfred modifier entry.

    `key` is the modifier combination string used as the JSON key in `mods`.
    Examples: "cmd", "alt", "cmd+alt", "ctrl+shift", "fn".

    This model supports only:
        - valid
        - arg
        - subtitle
    """

    key: str
    valid: bool | None = None
    arg: ArgValue | None = None
    subtitle: str | None = None
    icon: Icon | None = None
    variables: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        """
        Validate `key` is an allowed modifier key or combination.

        Raises:
            ValueError: If `key` is not a valid combo.
        """
        if self.key not in _VALID_MOD_COMBOS:
            raise ValueError(f"Invalid modifier key combo: {self.key!r}.")

    def payload(self) -> dict[str, object]:
        """Return the Alfred mod payload (the value under the `mods` key)."""
        data: dict[str, object] = {}
        if self.valid is not None:
            data["valid"] = self.valid
        if self.arg is not None:
            data["arg"] = self.arg
        if self.subtitle is not None:
            data["subtitle"] = self.subtitle
        if self.icon is not None:
            icon_obj = self.icon.to_alfred()
            if icon_obj is not None:
                data["icon"] = icon_obj
        if self.variables is not None:
            data["variables"] = dict(self.variables)
        return data
