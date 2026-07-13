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


def test_load_command_specs_preserves_table_shape_when_toml_uses_table(tmp_path):
    # Given a commands file whose value is an inline table
    path = tmp_path / "commands.toml"
    path.write_text('[commands]\n"//X" = { instruction = "// do X", model = "claude-haiku" }\n')

    # When we load the raw specs
    result = m.load_command_specs(path, DEFAULTS)

    # Then the table value is kept intact (not yet reduced to its instruction)
    assert result["//X"] == {"instruction": "// do X", "model": "claude-haiku"}


def test_load_commands_reduces_table_spec_to_instruction_when_toml_uses_table(tmp_path):
    # Given a commands file whose value is an inline table pinning a model
    path = tmp_path / "commands.toml"
    path.write_text('[commands]\n"//X" = { instruction = "// do X", model = "claude-haiku" }\n')

    # When we load the back-compat instruction map
    result = m.load_commands(path, DEFAULTS)

    # Then the table is normalized down to its instruction string
    assert result["//X"] == "// do X"


def test_load_models_maps_command_to_pinned_model_when_table(tmp_path):
    # Given a commands file with a pinned table command and a bare-string command
    path = tmp_path / "commands.toml"
    path.write_text('[commands]\n"//X" = { instruction = "// do X", model = "claude-haiku" }\n"//Y" = "// do Y"\n')

    # When we load the model map
    result = m.load_models(path, DEFAULTS)

    # Then only the pinned command appears, mapped to its model
    assert result["//X"] == "claude-haiku"
    assert "//Y" not in result


def test_model_for_uses_longest_matched_commands_pin():
    # Given text carrying a pinned command
    codes  = {"//C": "// correct", "//DOH": "// fix typos"}
    models = {"//DOH": "claude-haiku"}

    # When we resolve the model for text using that command
    result = m.model_for("some typo //DOH", codes, models, "claude-sonnet")

    # Then the pinned model of the matched command is chosen
    assert result == "claude-haiku"


def test_model_for_falls_back_to_default_when_longest_unpinned():
    # Given //C pinned to haiku but the longer //CC (which contains //C) unpinned
    codes  = {"//C": "// correct", "//CC": "// clear and concise"}
    models = {"//C": "claude-haiku"}

    # When we resolve the model for a //CC request (both //C and //CC match)
    result = m.model_for("make this //CC", codes, models, "claude-sonnet")

    # Then the longest match (//CC) wins, and being unpinned it yields the default
    assert result == "claude-sonnet"


def test_model_for_default_when_no_command():
    # Given text with no command token
    codes  = {"//C": "// correct"}
    models = {"//C": "claude-haiku"}

    # When we resolve the model
    result = m.model_for("plain text", codes, models, "claude-sonnet")

    # Then the default model is used
    assert result == "claude-sonnet"


def test_command_instruction_returns_string_as_is():
    # Given a bare-string command spec
    value = "// correct the spelling"

    # When we read its instruction
    result = m.command_instruction(value)

    # Then the string is returned unchanged
    assert result == "// correct the spelling"


def test_command_instruction_reads_field_when_table():
    # Given a table command spec pinning a model
    value = {"instruction": "// fix typos", "model": "claude-haiku"}

    # When we read its instruction
    result = m.command_instruction(value)

    # Then the instruction field is returned
    assert result == "// fix typos"


def test_command_model_none_when_string():
    # Given a bare-string command spec (no pinned model)
    value = "// correct the spelling"

    # When we read its pinned model
    result = m.command_model(value)

    # Then there is none
    assert result is None


def test_command_model_reads_field_when_table():
    # Given a table command spec pinning a model
    value = {"instruction": "// fix typos", "model": "claude-haiku"}

    # When we read its pinned model
    result = m.command_model(value)

    # Then the model field is returned
    assert result == "claude-haiku"


def test_print_codes_prints_only_header_when_no_commands(capsys):
    # Given an empty command map
    codes: dict[str, str] = {}

    # When we print the table
    m.print_codes(codes)

    # Then only the header is printed and nothing crashes on the empty width
    out = capsys.readouterr().out
    assert out.strip() == "Available // commands:"
