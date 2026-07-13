import pytest

import llmfix_linux as m

DEFAULTS = {"//C": "// correct", "//SS": ""}


def test_load_commands_returns_defaults_when_file_missing(tmp_path):
    # Given a path where no commands file exists
    path = tmp_path / "commands.toml"

    # When we load commands
    result = m.load_commands(path, DEFAULTS)

    # Then the built-in defaults are returned unchanged
    assert result == DEFAULTS


def test_load_commands_overrides_default_when_toml_redefines_key(tmp_path):
    # Given a commands file that redefines an existing key
    path = tmp_path / "commands.toml"
    path.write_text('[commands]\n"//C" = "// changed"\n')

    # When we load commands
    result = m.load_commands(path, DEFAULTS)

    # Then the file value wins for that key
    assert result["//C"] == "// changed"


def test_load_commands_adds_new_key_when_toml_extends(tmp_path):
    # Given a commands file that introduces a brand-new command
    path = tmp_path / "commands.toml"
    path.write_text('[commands]\n"//NEW" = "// do a new thing"\n')

    # When we load commands
    result = m.load_commands(path, DEFAULTS)

    # Then the new command joins the defaults
    assert result["//NEW"] == "// do a new thing"
    assert result["//C"] == "// correct"


def test_load_commands_falls_back_to_defaults_when_toml_malformed(tmp_path, caplog):
    # Given a commands file that is not valid TOML
    path = tmp_path / "commands.toml"
    path.write_text("this is : not = valid = toml [[[")

    # When we load commands
    result = m.load_commands(path, DEFAULTS)

    # Then defaults are returned and a warning is logged
    assert result == DEFAULTS
    assert any("Could not read" in r.message for r in caplog.records)


def test_commands_path_points_next_to_the_script():
    # Given the running module

    # When we ask for the commands path
    path = m.commands_path()

    # Then it is a sibling file named commands.toml
    assert path.name == "commands.toml"
    assert path.parent == m.Path(m.__file__).resolve().parent


def test_shipped_commands_toml_loads_and_keeps_screenshot_sentinel():
    # Given the commands.toml shipped alongside the script

    # When we load it over the built-in defaults
    result = m.load_commands(m.commands_path(), m.DEFAULT_CODES)

    # Then it parses and //SS remains the empty screenshot sentinel
    assert result["//SS"] == ""
    assert result["//CC"].startswith("// edit to be clear and concise")  # prefix, not exact: the wording is user-editable


def test_print_codes_prints_a_row_per_command_stripping_prefix(capsys):
    # Given a small command map with a normal command and the screenshot sentinel
    codes = {"//CC": "// edit to be clear and concise", "//SS": ""}

    # When we print the table
    m.print_codes(codes)

    # Then the header, the stripped description, and the screenshot help all appear
    out = capsys.readouterr().out
    assert "Available // commands:" in out
    assert "//CC" in out and "edit to be clear and concise" in out
    assert "// edit to be clear and concise" not in out  # leading "// " stripped for display
    assert "screenshot of the monitor under the mouse" in out


def test_print_codes_prints_only_header_when_no_commands(capsys):
    # Given an empty command map
    codes: dict[str, str] = {}

    # When we print the table
    m.print_codes(codes)

    # Then only the header is printed and nothing crashes on the empty width
    out = capsys.readouterr().out
    assert out.strip() == "Available // commands:"
