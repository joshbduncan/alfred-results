"""
icon
----
Alfred Script Filter icon types.

Defines :class:`IconResourceType` (how Alfred resolves the icon path) and
:class:`Icon` (the `"icon"` sub-object in a Script Filter result item or
modifier payload).

Alfred icon JSON examples::

    {"icon": {"path": "./custom_icon.png"}}
    {"icon": {"type": "fileicon", "path": "~/Desktop"}}
    {"icon": {"type": "filetype", "path": "com.apple.rtfd"}}
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class IconResourceType(StrEnum):
    """How Alfred resolves the `path` field of an :class:`Icon`.

    When omitted, Alfred treats the path as a relative path from the workflow
    bundle root pointing to an image file (PNG, ICNS, etc.).

    Attributes:
        FILEICON: Display the native macOS icon of the file or folder at
            `path`.  Useful for showing a folder's Finder icon or an
            application's dock icon.
        FILETYPE: Display the system icon for the Uniform Type Identifier
            (UTI) given in `path` (e.g. `"com.apple.rtfd"` for an
            RTFD document).
    """

    FILEICON = "fileicon"
    FILETYPE = "filetype"


@dataclass(slots=True)
class Icon:
    """Alfred Script Filter `icon` payload.

    Represents the optional `"icon"` object attached to a Script Filter
    result item or modifier entry.  When `path` is `None` the icon is
    considered unset and :meth:`to_dict` returns `None`, signalling the
    caller to omit the key entirely.

    Attributes:
        path: The icon resource path or identifier.

            * `None` — no icon; :meth:`to_dict` returns `None`.
            * Relative filesystem path (from the workflow bundle root) when
              `resource_type` is `None`.
            * Absolute or `~`-prefixed filesystem path when
              `resource_type` is :attr:`IconResourceType.FILEICON`.
            * UTI string (e.g. `"com.apple.rtfd"`) when `resource_type`
              is :attr:`IconResourceType.FILETYPE`.

        resource_type: Optional modifier that changes how Alfred interprets
            `path`.  Must be `None` when `path` is `None`; setting it
            without a path raises :exc:`ValueError` on construction.

    Raises:
        ValueError: If `resource_type` is set but `path` is `None`.

    Example::

        # Use the Finder icon of the matched file
        icon = Icon(path="/Users/me/Documents", resource_type=IconResourceType.FILEICON)

        # Custom PNG bundled with the workflow
        icon = Icon(path="./icons/custom.png")

        # No icon (omitted from JSON)
        icon = Icon()
    """

    path: str | None = None
    resource_type: IconResourceType | None = None

    def __post_init__(self) -> None:
        """Validate field constraints after dataclass initialization.

        Raises:
            ValueError: If `resource_type` is set but `path` is `None`.
        """
        if self.path is None and self.resource_type is not None:
            raise ValueError("Icon.resource_type requires Icon.path.")

    def to_dict(self) -> dict[str, Any] | None:
        """Serialize to Alfred's `icon` object shape.

        Produces the dict that is assigned to the `"icon"` key of a result
        item or modifier entry.  Returns `None` when no icon is defined so
        callers can gate inclusion with a simple truthiness check.

        Returns:
            `{"path": path}` when only `path` is set.
            `{"type": "<resource_type>", "path": path}` when both fields
            are set.
            `None` when `path` is `None` (icon should be omitted).

        Example::

            icon = Icon(path="~/Desktop", resource_type=IconResourceType.FILEICON)
            icon.to_dict()
            # {"type": "fileicon", "path": "~/Desktop"}
        """
        if self.path is None:
            return None

        if self.resource_type is None:
            return {"path": self.path}

        return {"type": str(self.resource_type), "path": self.path}
