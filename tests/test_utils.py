"""Tests for path_to_uuid."""

from __future__ import annotations

from alfred_results.utils import path_to_uuid


class TestPathToUuid:
    def test_returns_string(self) -> None:
        assert isinstance(path_to_uuid("/Users/me/Downloads"), str)

    def test_standard_uuid_format(self) -> None:
        uid = path_to_uuid("/Users/me/Downloads")
        parts = uid.split("-")
        assert len(parts) == 5
        assert [len(p) for p in parts] == [8, 4, 4, 4, 12]

    def test_same_path_same_uid(self) -> None:
        assert path_to_uuid("/Users/me/Downloads") == path_to_uuid(
            "/Users/me/Downloads"
        )

    def test_different_paths_different_uids(self) -> None:
        assert path_to_uuid("/Users/me/Downloads") != path_to_uuid(
            "/Users/me/Documents"
        )

    def test_known_stable_value(self) -> None:
        # Regression guard: this value must never change across releases.
        uid = path_to_uuid("/Users/me/Downloads")
        assert uid == "e01a7ef8-32c2-5ace-88bc-107ed71edaa1"
