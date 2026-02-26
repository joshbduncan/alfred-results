"""Tests for ScriptFilterPayload and ScriptFilterCache."""

from __future__ import annotations

import json

import pytest

from alfred_results.payload import ScriptFilterCache, ScriptFilterPayload
from alfred_results.result_item import ResultItem


class TestScriptFilterCache:
    def test_seconds_only(self) -> None:
        assert ScriptFilterCache(seconds=60).to_dict() == {"seconds": 60}

    def test_loosereload_included_when_set(self) -> None:
        assert ScriptFilterCache(seconds=60, loosereload=True).to_dict() == {
            "seconds": 60,
            "loosereload": True,
        }

    def test_loosereload_omitted_when_none(self) -> None:
        assert "loosereload" not in ScriptFilterCache(seconds=60).to_dict()

    def test_seconds_too_low_raises(self) -> None:
        with pytest.raises(ValueError, match="ScriptFilterCache.seconds"):
            ScriptFilterCache(seconds=4)

    def test_seconds_too_high_raises(self) -> None:
        with pytest.raises(ValueError, match="ScriptFilterCache.seconds"):
            ScriptFilterCache(seconds=86401)

    def test_seconds_at_minimum(self) -> None:
        assert ScriptFilterCache(seconds=5).seconds == 5

    def test_seconds_at_maximum(self) -> None:
        assert ScriptFilterCache(seconds=86400).seconds == 86400


class TestScriptFilterPayload:
    def test_empty_payload_has_variables(self) -> None:
        result = ScriptFilterPayload().to_dict()
        assert "variables" in result
        assert "script" in result["variables"]
        assert "version" in result["variables"]

    def test_items_serialized(self) -> None:
        items = [ResultItem(title="foo"), ResultItem(title="bar")]
        result = ScriptFilterPayload(items=items).to_dict()
        assert len(result["items"]) == 2
        assert result["items"][0]["title"] == "foo"
        assert result["items"][1]["title"] == "bar"

    def test_items_omitted_when_none(self) -> None:
        assert "items" not in ScriptFilterPayload().to_dict()

    def test_user_variables_merged(self) -> None:
        result = ScriptFilterPayload(variables={"mode": "search"}).to_dict()
        assert result["variables"]["mode"] == "search"
        assert "script" in result["variables"]

    def test_user_variable_wins_on_collision(self) -> None:
        result = ScriptFilterPayload(variables={"script": "custom"}).to_dict()
        assert result["variables"]["script"] == "custom"

    def test_rerun_included(self) -> None:
        assert ScriptFilterPayload(rerun=1.5).to_dict()["rerun"] == 1.5

    def test_rerun_too_low_raises(self) -> None:
        with pytest.raises(ValueError, match="ScriptFilterPayload.rerun"):
            ScriptFilterPayload(rerun=0.05)

    def test_rerun_too_high_raises(self) -> None:
        with pytest.raises(ValueError, match="ScriptFilterPayload.rerun"):
            ScriptFilterPayload(rerun=5.1)

    def test_rerun_at_boundaries(self) -> None:
        assert ScriptFilterPayload(rerun=0.1).rerun == 0.1
        assert ScriptFilterPayload(rerun=5.0).rerun == 5.0

    def test_skipknowledge_included(self) -> None:
        assert (
            ScriptFilterPayload(skipknowledge=True).to_dict()["skipknowledge"] is True
        )

    def test_cache_serialized(self) -> None:
        cache = ScriptFilterCache(seconds=30, loosereload=True)
        result = ScriptFilterPayload(cache=cache).to_dict()
        assert result["cache"] == {"seconds": 30, "loosereload": True}

    def test_to_json_returns_string(self) -> None:
        payload = ScriptFilterPayload(items=[ResultItem(title="foo")])
        assert isinstance(payload.to_json(), str)

    def test_to_json_is_valid_json(self) -> None:
        payload = ScriptFilterPayload(items=[ResultItem(title="foo")])
        parsed = json.loads(payload.to_json())
        assert parsed["items"][0]["title"] == "foo"

    def test_to_json_kwargs_forwarded(self) -> None:
        payload = ScriptFilterPayload(items=[ResultItem(title="foo")])
        compact = payload.to_json(separators=(",", ":"))
        assert " " not in compact
