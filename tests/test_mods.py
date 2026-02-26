"""Tests for Mod, VALID_MODIFIER_KEYS, and valid_modifiers."""

from __future__ import annotations

import pytest

from alfred_results.result_item import VALID_MODIFIER_KEYS, Mod, valid_modifiers


class TestModToDict:
    def test_empty_mod(self) -> None:
        assert Mod(key="cmd").to_dict() == {}

    def test_valid_flag(self) -> None:
        assert Mod(key="cmd", valid=True).to_dict() == {"valid": True}

    def test_valid_false(self) -> None:
        assert Mod(key="cmd", valid=False).to_dict() == {"valid": False}

    def test_arg(self) -> None:
        assert Mod(key="alt", arg="/tmp/foo").to_dict() == {"arg": "/tmp/foo"}

    def test_subtitle(self) -> None:
        assert Mod(key="ctrl", subtitle="Open in Terminal").to_dict() == {
            "subtitle": "Open in Terminal"
        }

    def test_all_fields(self) -> None:
        mod = Mod(
            key="cmd",
            valid=True,
            arg="/tmp/foo",
            subtitle="Open in Terminal",
            variables={"source": "mod"},
        )
        assert mod.to_dict() == {
            "valid": True,
            "arg": "/tmp/foo",
            "subtitle": "Open in Terminal",
            "variables": {"source": "mod"},
        }

    def test_combo_key(self) -> None:
        mod = Mod(key="cmd+shift", valid=False, subtitle="Not available")
        assert mod.to_dict() == {"valid": False, "subtitle": "Not available"}


class TestModValidation:
    def test_invalid_key_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid modifier key combo"):
            Mod(key="super")

    def test_repeated_key_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid modifier key combo"):
            Mod(key="cmd+cmd")

    def test_all_base_keys_valid(self) -> None:
        for key in VALID_MODIFIER_KEYS:
            assert Mod(key=key).key == key

    def test_two_key_combo_valid(self) -> None:
        assert Mod(key="cmd+alt").key == "cmd+alt"

    def test_three_key_combo_valid(self) -> None:
        assert Mod(key="cmd+alt+shift").key == "cmd+alt+shift"

    def test_four_key_combo_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid modifier key combo"):
            Mod(key="cmd+alt+shift+ctrl")


class TestValidModifiers:
    def test_returns_set(self) -> None:
        assert isinstance(valid_modifiers(), set)

    def test_base_keys_included(self) -> None:
        combos = valid_modifiers()
        for key in VALID_MODIFIER_KEYS:
            assert key in combos

    def test_two_key_combos_included(self) -> None:
        combos = valid_modifiers()
        assert "cmd+alt" in combos
        assert "alt+cmd" in combos

    def test_three_key_combos_included(self) -> None:
        assert "cmd+alt+shift" in valid_modifiers()

    def test_custom_keys(self) -> None:
        combos = valid_modifiers(["cmd", "alt"])
        assert combos == {"cmd", "alt", "cmd+alt", "alt+cmd"}

    def test_valid_modifier_keys_constant(self) -> None:
        assert VALID_MODIFIER_KEYS == ("cmd", "alt", "ctrl", "shift", "fn")
