"""Tests for Icon and IconResourceType."""

from __future__ import annotations

import pytest

from alfred_results.result_item import Icon, IconResourceType


class TestIconToDict:
    def test_no_path_returns_none(self) -> None:
        assert Icon().to_dict() is None

    def test_path_only(self, custom_icon: Icon) -> None:
        assert custom_icon.to_dict() == {"path": "./icons/star.png"}

    def test_fileicon(self, fileicon: Icon) -> None:
        assert fileicon.to_dict() == {
            "type": "fileicon",
            "path": "/Users/me/Downloads",
        }

    def test_filetype(self, filetype_icon: Icon) -> None:
        assert filetype_icon.to_dict() == {
            "type": "filetype",
            "path": "com.adobe.pdf",
        }


class TestIconValidation:
    def test_resource_type_without_path_raises(self) -> None:
        with pytest.raises(ValueError, match="Icon.resource_type requires Icon.path"):
            Icon(resource_type=IconResourceType.FILEICON)

    def test_path_none_resource_type_none_is_valid(self) -> None:
        icon = Icon()
        assert icon.path is None
        assert icon.resource_type is None


class TestIconResourceType:
    def test_fileicon_value(self) -> None:
        assert IconResourceType.FILEICON == "fileicon"

    def test_filetype_value(self) -> None:
        assert IconResourceType.FILETYPE == "filetype"
