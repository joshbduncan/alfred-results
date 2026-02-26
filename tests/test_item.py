"""Tests for ResultItem and ItemType."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from alfred_results.result_item import Icon, IconResourceType, ItemType, Mod, ResultItem

if TYPE_CHECKING:
    from pathlib import Path


class TestResultItemValidation:
    def test_empty_title_raises(self) -> None:
        with pytest.raises(
            ValueError, match="ResultItem.title must be a non-empty string"
        ):
            ResultItem(title="")

    def test_whitespace_title_raises(self) -> None:
        with pytest.raises(
            ValueError, match="ResultItem.title must be a non-empty string"
        ):
            ResultItem(title="   ")

    def test_duplicate_mod_keys_raises(self) -> None:
        with pytest.raises(ValueError, match="duplicate modifier key"):
            ResultItem(
                title="test",
                mods=[
                    Mod(key="cmd", valid=True),
                    Mod(key="cmd", valid=False),
                ],
            )

    def test_valid_title(self) -> None:
        item = ResultItem(title="Hello")
        assert item.title == "Hello"


class TestResultItemToDict:
    def test_title_only(self, simple_item: ResultItem) -> None:
        assert simple_item.to_dict() == {"title": "My Result"}

    def test_optional_fields_omitted_when_none(self, simple_item: ResultItem) -> None:
        result = simple_item.to_dict()
        for key in ("subtitle", "uid", "arg", "valid", "type", "icon", "mods"):
            assert key not in result

    def test_full_item_keys(self, full_item: ResultItem) -> None:
        result = full_item.to_dict()
        assert result["title"] == "report.pdf"
        assert result["subtitle"] == "/Users/me/report.pdf"
        assert result["uid"] == "abc-123"
        assert result["arg"] == "/Users/me/report.pdf"
        assert result["valid"] is True
        assert result["autocomplete"] == "report"
        assert result["match"] == "report pdf"
        assert result["type"] == "file"
        assert result["quicklookurl"] == "/Users/me/report.pdf"
        assert result["variables"] == {"category": "reports"}

    def test_mods_serialized_as_dict(self, full_item: ResultItem) -> None:
        result = full_item.to_dict()
        assert "mods" in result
        assert "cmd" in result["mods"]
        assert "alt" in result["mods"]

    def test_icon_serialized(self, full_item: ResultItem) -> None:
        result = full_item.to_dict()
        assert result["icon"] == {"type": "fileicon", "path": "/Users/me/report.pdf"}

    def test_none_icon_omitted(self) -> None:
        # Icon() has no path, so to_dict() returns None and the key is omitted.
        assert "icon" not in ResultItem(title="test", icon=Icon()).to_dict()
        # No icon set at all — also omitted.
        assert "icon" not in ResultItem(title="test").to_dict()

    def test_item_type_serialized_as_string(self) -> None:
        item = ResultItem(title="test", type=ItemType.FILE_SKIPCHECK)
        assert item.to_dict()["type"] == "file:skipcheck"

    def test_text_field(self) -> None:
        item = ResultItem(title="test", text={"copy": "foo", "largetype": "FOO"})
        assert item.to_dict()["text"] == {"copy": "foo", "largetype": "FOO"}

    def test_list_arg(self) -> None:
        item = ResultItem(title="test", arg=["/a", "/b"])
        assert item.to_dict()["arg"] == ["/a", "/b"]


class TestResultItemFromPath:
    def test_title_is_filename(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        item = ResultItem.from_path(str(p))
        assert item.title == "myfile.txt"

    def test_subtitle_is_path(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        item = ResultItem.from_path(str(p))
        assert item.subtitle == str(p)

    def test_arg_is_path(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        item = ResultItem.from_path(str(p))
        assert item.arg == str(p)

    def test_uid_is_set(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        item = ResultItem.from_path(str(p))
        assert item.uid is not None
        assert len(item.uid) == 36  # standard UUID format

    def test_uid_is_stable(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        assert ResultItem.from_path(str(p)).uid == ResultItem.from_path(str(p)).uid

    def test_default_variables_injected(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        item = ResultItem.from_path(str(p))
        assert item.variables is not None
        assert "_path" in item.variables
        assert "_parent" in item.variables

    def test_user_variables_merged(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        item = ResultItem.from_path(str(p), variables={"custom": "val"})
        assert item.variables is not None
        assert item.variables["custom"] == "val"
        assert "_path" in item.variables

    def test_user_variable_wins_on_collision(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        item = ResultItem.from_path(str(p), variables={"_path": "override"})
        assert item.variables is not None
        assert item.variables["_path"] == "override"

    def test_file_type_for_file(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        item = ResultItem.from_path(str(p))
        assert item.type == ItemType.FILE

    def test_default_type_for_directory(self, tmp_path: Path) -> None:
        item = ResultItem.from_path(str(tmp_path))
        assert item.type == ItemType.DEFAULT

    def test_icon_is_fileicon(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        item = ResultItem.from_path(str(p))
        assert item.icon is not None
        assert item.icon.resource_type == IconResourceType.FILEICON

    def test_mods_passed_through(self, tmp_path: Path) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        mods = [Mod(key="cmd", valid=True, subtitle="Open")]
        item = ResultItem.from_path(str(p), mods=mods)
        assert item.mods == mods


class TestItemType:
    def test_default_value(self) -> None:
        assert ItemType.DEFAULT == "default"

    def test_file_value(self) -> None:
        assert ItemType.FILE == "file"

    def test_file_skipcheck_value(self) -> None:
        assert ItemType.FILE_SKIPCHECK == "file:skipcheck"
