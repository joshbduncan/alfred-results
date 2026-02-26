"""Tests for the CLI (cli.py / main())."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from alfred_results.cli import (
    create_parser,
    get_path_attribute,
    main,
    parse_input_csv,
    parse_input_json,
    parse_input_lines,
    parse_mods,
    parse_result_vars,
    parse_result_vars_from_row,
    parse_session_vars,
)

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> dict:
    """Call main() and return the parsed JSON written to stdout."""
    rc = main(argv)
    assert rc == 0
    out = capsys.readouterr().out
    return json.loads(out)


# ---------------------------------------------------------------------------
# parse_input_lines
# ---------------------------------------------------------------------------


class TestParseInputLines:
    def test_reads_lines_from_file(self, tmp_path: Path) -> None:
        f = tmp_path / "lines.txt"
        f.write_text("/a/b\n/c/d\n")
        assert parse_input_lines(str(f)) == ["/a/b", "/c/d"]

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        f = tmp_path / "lines.txt"
        f.write_text("  /a/b  \n  /c/d  \n")
        assert parse_input_lines(str(f)) == ["/a/b", "/c/d"]

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "lines.txt"
        f.write_text("/a/b\n\n\n/c/d\n")
        assert parse_input_lines(str(f)) == ["/a/b", "/c/d"]

    def test_missing_file_raises_oserror(self) -> None:
        with pytest.raises(OSError):
            parse_input_lines("/no/such/file.txt")


# ---------------------------------------------------------------------------
# parse_input_csv
# ---------------------------------------------------------------------------


class TestParseInputCsv:
    def test_basic_csv(self, tmp_path: Path) -> None:
        f = tmp_path / "data.csv"
        f.write_text("title,arg\nDownloads,/Users/me/Downloads\n")
        rows = parse_input_csv(str(f))
        assert rows == [{"title": "Downloads", "arg": "/Users/me/Downloads"}]

    def test_custom_delimiter(self, tmp_path: Path) -> None:
        f = tmp_path / "data.tsv"
        f.write_text("title\targ\nDownloads\t/Users/me/Downloads\n")
        rows = parse_input_csv(str(f), delimiter="\t")
        assert rows[0]["title"] == "Downloads"

    def test_missing_file_raises_oserror(self) -> None:
        with pytest.raises(OSError):
            parse_input_csv("/no/such/file.csv")


# ---------------------------------------------------------------------------
# parse_input_json
# ---------------------------------------------------------------------------


class TestParseInputJson:
    def test_basic_json(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('[{"title": "foo", "arg": "bar"}]')
        rows = parse_input_json(str(f))
        assert rows == [{"title": "foo", "arg": "bar"}]

    def test_values_coerced_to_str(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('[{"title": "foo", "count": 42}]')
        rows = parse_input_json(str(f))
        assert rows[0]["count"] == "42"

    def test_invalid_json_raises_value_error(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text("not json")
        with pytest.raises(ValueError, match="invalid JSON"):
            parse_input_json(str(f))

    def test_non_array_raises_value_error(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"title": "foo"}')
        with pytest.raises(ValueError, match="must be a JSON array"):
            parse_input_json(str(f))

    def test_non_object_element_raises_value_error(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('["not an object"]')
        with pytest.raises(ValueError, match="must be an object"):
            parse_input_json(str(f))

    def test_missing_file_raises_oserror(self) -> None:
        with pytest.raises(OSError):
            parse_input_json("/no/such/file.json")


# ---------------------------------------------------------------------------
# parse_session_vars
# ---------------------------------------------------------------------------


class TestParseSessionVars:
    def test_none_returns_empty_dict(self) -> None:
        assert parse_session_vars(None) == {}

    def test_pairs_become_dict(self) -> None:
        assert parse_session_vars([["mode", "search"], ["ts", "2026"]]) == {
            "mode": "search",
            "ts": "2026",
        }


# ---------------------------------------------------------------------------
# parse_mods
# ---------------------------------------------------------------------------


class TestParseMods:
    def test_none_returns_empty_list(self) -> None:
        assert parse_mods(None) == []

    def test_single_mod(self) -> None:
        mods = parse_mods([["cmd", "/tmp/foo", "Open in Terminal"]])
        assert len(mods) == 1
        assert mods[0].key == "cmd"
        assert mods[0].arg == "/tmp/foo"
        assert mods[0].subtitle == "Open in Terminal"
        assert mods[0].valid is True

    def test_invalid_mod_key_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid modifier key combo"):
            parse_mods([["super", "/tmp/foo", "subtitle"]])


# ---------------------------------------------------------------------------
# get_path_attribute
# ---------------------------------------------------------------------------


class TestGetPathAttribute:
    def test_name_attribute(self, tmp_path: Path) -> None:
        p = tmp_path / "report.pdf"
        assert get_path_attribute(p, "name") == "report.pdf"

    def test_stem_attribute(self, tmp_path: Path) -> None:
        p = tmp_path / "report.pdf"
        assert get_path_attribute(p, "stem") == "report"

    def test_suffix_attribute(self, tmp_path: Path) -> None:
        p = tmp_path / "report.pdf"
        assert get_path_attribute(p, "suffix") == ".pdf"

    def test_callable_attribute(self, tmp_path: Path) -> None:
        p = tmp_path / "report.pdf"
        assert get_path_attribute(p, "as_posix") == p.as_posix()

    def test_invalid_attribute_raises(self, tmp_path: Path) -> None:
        with pytest.raises(AttributeError):
            get_path_attribute(tmp_path / "f.txt", "nonexistent_attr")


# ---------------------------------------------------------------------------
# parse_result_vars
# ---------------------------------------------------------------------------


class TestParseResultVars:
    def test_none_returns_none(self, tmp_path: Path) -> None:
        assert parse_result_vars(tmp_path, None) is None

    def test_resolves_path_attribute(self, tmp_path: Path) -> None:
        p = tmp_path / "report.pdf"
        result = parse_result_vars(p, [["ext", "suffix"]])
        assert result == {"ext": ".pdf"}

    def test_falls_back_to_raw_string(self, tmp_path: Path) -> None:
        p = tmp_path / "report.pdf"
        result = parse_result_vars(p, [["custom", "not_a_path_attr"]])
        assert result == {"custom": "not_a_path_attr"}


# ---------------------------------------------------------------------------
# parse_result_vars_from_row
# ---------------------------------------------------------------------------


class TestParseResultVarsFromRow:
    def test_none_returns_none(self) -> None:
        assert parse_result_vars_from_row({"title": "foo"}, None) is None

    def test_key_found_in_row(self) -> None:
        row = {"title": "foo", "url": "https://example.com"}
        result = parse_result_vars_from_row(row, [["link", "url"]])
        assert result == {"link": "https://example.com"}

    def test_key_not_in_row_falls_back_to_raw_string(self) -> None:
        row = {"title": "foo"}
        result = parse_result_vars_from_row(row, [["src", "missing_key"]])
        assert result == {"src": "missing_key"}

    def test_multiple_pairs_mixed_hit_and_miss(self) -> None:
        row = {"title": "foo", "url": "https://example.com"}
        result = parse_result_vars_from_row(
            row, [["link", "url"], ["src", "missing_key"]]
        )
        assert result == {"link": "https://example.com", "src": "missing_key"}

    def test_empty_val_returns_empty_dict(self) -> None:
        assert parse_result_vars_from_row({"title": "foo"}, []) == {}


# ---------------------------------------------------------------------------
# main() — path format
# ---------------------------------------------------------------------------


class TestMainPathFormat:
    def test_single_path(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        f = tmp_path / "input.txt"
        f.write_text(str(p))
        payload = run([str(f)], capsys)
        assert len(payload["items"]) == 1
        assert payload["items"][0]["title"] == "myfile.txt"

    def test_multiple_paths(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        files = [tmp_path / f"file{i}.txt" for i in range(3)]
        for fp in files:
            fp.touch()
        f = tmp_path / "input.txt"
        f.write_text("\n".join(str(fp) for fp in files))
        payload = run([str(f)], capsys)
        assert len(payload["items"]) == 3

    def test_default_vars_present(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        f = tmp_path / "input.txt"
        f.write_text(str(p))
        payload = run([str(f)], capsys)
        variables = payload["items"][0]["variables"]
        assert "_path" in variables
        assert "_parent" in variables

    def test_result_var_path_attribute(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        p = tmp_path / "report.pdf"
        p.touch()
        f = tmp_path / "input.txt"
        f.write_text(str(p))
        payload = run([str(f), "--result-var", "ext", "suffix"], capsys)
        assert payload["items"][0]["variables"]["ext"] == ".pdf"

    def test_session_var_in_payload(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        f = tmp_path / "input.txt"
        f.write_text(str(p))
        payload = run([str(f), "--session-var", "mode", "search"], capsys)
        assert payload["variables"]["mode"] == "search"

    def test_mod_attached_to_items(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        p = tmp_path / "myfile.txt"
        p.touch()
        f = tmp_path / "input.txt"
        f.write_text(str(p))
        payload = run([str(f), "--mod", "cmd", "/tmp/out", "Open in Terminal"], capsys)
        assert "cmd" in payload["items"][0]["mods"]


# ---------------------------------------------------------------------------
# main() — csv format
# ---------------------------------------------------------------------------


class TestMainCsvFormat:
    def test_basic_csv(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.csv"
        f.write_text("title,arg,subtitle\nDownloads,/Users/me/Downloads,Home\n")
        payload = run(["-f", "csv", str(f)], capsys)
        item = payload["items"][0]
        assert item["title"] == "Downloads"
        assert item["arg"] == "/Users/me/Downloads"
        assert item["subtitle"] == "Home"

    def test_missing_title_exits(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.csv"
        f.write_text("arg\n/Users/me/Downloads\n")
        with pytest.raises(SystemExit):
            main(["-f", "csv", str(f)])

    def test_invalid_type_exits(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.csv"
        f.write_text("title,type\nfoo,badtype\n")
        with pytest.raises(SystemExit):
            main(["-f", "csv", str(f)])

    def test_result_var_column_lookup(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.csv"
        f.write_text("title,url\nGitHub,https://github.com\n")
        payload = run(["-f", "csv", str(f), "--result-var", "link", "url"], capsys)
        assert payload["items"][0]["variables"]["link"] == "https://github.com"

    def test_result_var_fallback_to_raw_string(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.csv"
        f.write_text("title\nfoo\n")
        payload = run(["-f", "csv", str(f), "--result-var", "src", "myval"], capsys)
        assert payload["items"][0]["variables"]["src"] == "myval"

    def test_result_var_no_vars_when_not_provided(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.csv"
        f.write_text("title\nfoo\n")
        payload = run(["-f", "csv", str(f)], capsys)
        assert "variables" not in payload["items"][0]

    def test_result_var_per_row_lookup(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.csv"
        f.write_text("title,url\nGitHub,https://github.com\nPyPI,https://pypi.org\n")
        payload = run(["-f", "csv", str(f), "--result-var", "link", "url"], capsys)
        assert payload["items"][0]["variables"]["link"] == "https://github.com"
        assert payload["items"][1]["variables"]["link"] == "https://pypi.org"


# ---------------------------------------------------------------------------
# main() — json format
# ---------------------------------------------------------------------------


class TestMainJsonFormat:
    def test_basic_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.json"
        f.write_text('[{"title": "foo", "arg": "bar", "subtitle": "baz"}]')
        payload = run(["-f", "json", str(f)], capsys)
        item = payload["items"][0]
        assert item["title"] == "foo"
        assert item["arg"] == "bar"
        assert item["subtitle"] == "baz"

    def test_missing_title_exits(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('[{"arg": "bar"}]')
        with pytest.raises(SystemExit):
            main(["-f", "json", str(f)])

    def test_invalid_json_exits(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text("not json")
        with pytest.raises(SystemExit):
            main(["-f", "json", str(f)])

    def test_non_array_exits(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"title": "foo"}')
        with pytest.raises(SystemExit):
            main(["-f", "json", str(f)])

    def test_result_var_key_lookup(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.json"
        f.write_text('[{"title": "GitHub", "url": "https://github.com"}]')
        payload = run(["-f", "json", str(f), "--result-var", "link", "url"], capsys)
        assert payload["items"][0]["variables"]["link"] == "https://github.com"

    def test_result_var_fallback_to_raw_string(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.json"
        f.write_text('[{"title": "foo"}]')
        payload = run(["-f", "json", str(f), "--result-var", "src", "myval"], capsys)
        assert payload["items"][0]["variables"]["src"] == "myval"

    def test_result_var_no_vars_when_not_provided(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.json"
        f.write_text('[{"title": "foo"}]')
        payload = run(["-f", "json", str(f)], capsys)
        assert "variables" not in payload["items"][0]

    def test_result_var_per_row_lookup(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "data.json"
        f.write_text(
            '[{"title": "GitHub", "url": "https://github.com"},'
            ' {"title": "PyPI", "url": "https://pypi.org"}]'
        )
        payload = run(["-f", "json", str(f), "--result-var", "link", "url"], capsys)
        assert payload["items"][0]["variables"]["link"] == "https://github.com"
        assert payload["items"][1]["variables"]["link"] == "https://pypi.org"


# ---------------------------------------------------------------------------
# main() — string format
# ---------------------------------------------------------------------------


class TestMainStringFormat:
    def test_basic_strings(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "labels.txt"
        f.write_text("Open Safari\nOpen Terminal\n")
        payload = run(["-f", "string", str(f)], capsys)
        titles = [item["title"] for item in payload["items"]]
        assert titles == ["Open Safari", "Open Terminal"]

    def test_no_path_metadata(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "labels.txt"
        f.write_text("Hello\n")
        payload = run(["-f", "string", str(f)], capsys)
        item = payload["items"][0]
        assert "subtitle" not in item
        assert "uid" not in item

    def test_result_var_raw_string(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "labels.txt"
        f.write_text("Hello\n")
        payload = run(
            ["-f", "string", str(f), "--result-var", "source", "labels"], capsys
        )
        assert payload["items"][0]["variables"]["source"] == "labels"


# ---------------------------------------------------------------------------
# main() — error paths
# ---------------------------------------------------------------------------


class TestMainErrors:
    def test_missing_file_exits(self) -> None:
        with pytest.raises(SystemExit):
            main(["/no/such/file.txt"])

    def test_empty_input_exits(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        f.write_text("")
        with pytest.raises(SystemExit):
            main([str(f)])

    def test_blank_lines_only_exits(self, tmp_path: Path) -> None:
        f = tmp_path / "blank.txt"
        f.write_text("\n\n\n")
        with pytest.raises(SystemExit):
            main([str(f)])

    def test_invalid_mod_key_exits(self, tmp_path: Path) -> None:
        f = tmp_path / "input.txt"
        p = tmp_path / "a.txt"
        p.touch()
        f.write_text(str(p))
        with pytest.raises(SystemExit):
            main([str(f), "--mod", "superkey", "/tmp/out", "subtitle"])


# ---------------------------------------------------------------------------
# create_parser
# ---------------------------------------------------------------------------


class TestCreateParser:
    def test_default_format_is_path(self) -> None:
        parser = create_parser()
        args = parser.parse_args([])
        assert args.input_format == "path"

    def test_short_flag_f(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["-f", "csv"])
        assert args.input_format == "csv"

    def test_long_flag_input_format(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["--input-format", "json"])
        assert args.input_format == "json"

    def test_file_defaults_to_stdin(self) -> None:
        parser = create_parser()
        args = parser.parse_args([])
        assert args.file == "-"

    def test_mod_accumulates(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["--mod", "cmd", "a", "b", "--mod", "alt", "c", "d"])
        assert args.mod == [["cmd", "a", "b"], ["alt", "c", "d"]]

    def test_session_var_accumulates(self) -> None:
        parser = create_parser()
        args = parser.parse_args(
            ["--session-var", "k1", "v1", "--session-var", "k2", "v2"]
        )
        assert args.session_var == [["k1", "v1"], ["k2", "v2"]]
