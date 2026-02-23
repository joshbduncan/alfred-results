from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class IconResourceType(StrEnum):
    """
    Alfred icon resource type.

    Determines how Alfred resolves the `path` value in an item's `icon` object.

    Members:
        FILEICON: Treat `path` as a filesystem path and display that file or
            folder’s native macOS icon.
        FILETYPE: Treat `path` as a Uniform Type Identifier (UTI) and display
            the system icon for that file type.
    """

    FILEICON = "fileicon"
    FILETYPE = "filetype"


@dataclass(slots=True)
class Icon:
    """
    Alfred Script Filter `icon` payload.

    Represents the optional `icon` object attached to a Script Filter result
    item. If `path` is not provided, the icon is considered unset and should be
    omitted from the final JSON entirely.

    Alfred spec examples:

        {"icon": {"path": "./custom_icon.png"}}
        {"icon": {"type": "fileicon", "path": "~/Desktop"}}
        {"icon": {"type": "filetype", "path": "com.apple.rtfd"}}

    Attributes:
        path: Path or identifier describing the icon resource.
            • Relative path from the workflow root when `resource_type` is None.
            • Filesystem path when `resource_type` is FILEICON.
            • UTI string when `resource_type` is FILETYPE.
        resource_type: Optional modifier that changes how Alfred interprets
            `path`. Must not be set without `path`.
    """

    path: str | None = None
    resource_type: IconResourceType | None = None

    def to_alfred(self) -> dict[str, Any] | None:
        """
        Serialize this icon to Alfred's `icon` object shape.

        Returns:
            A dict suitable for assigning to an item's `"icon"` key, or None if
            no icon is defined.

        Raises:
            ValueError: If `resource_type` is set but `path` is None.

        Serialization rules:
            • path only → {"path": path}
            • path + resource_type → {"type": "...", "path": path}
            • no path → None (caller should omit `"icon"`)

        Notes:
            The enum is converted to its string value to match Alfred's JSON
            schema exactly.
        """
        if self.path is None:
            if self.resource_type is not None:
                raise ValueError("Icon.resource_type requires Icon.path.")
            return None

        if self.resource_type is None:
            return {"path": self.path}

        return {"type": str(self.resource_type), "path": self.path}
