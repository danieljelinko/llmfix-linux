import logging
import sys
from unittest.mock import MagicMock

import llmfix_linux as m


def test_setup_logging_sets_requested_level():
    # Given a request for DEBUG logging
    m.setup_logging("DEBUG")

    # Then the module logger is at DEBUG
    assert m.log.level == logging.DEBUG


def test_main_lists_commands_and_exits_without_starting_app(monkeypatch, capsys):
    # Given --list on the command line and a stubbed app class
    monkeypatch.setattr(sys, "argv", ["llmfix_linux.py", "--list"])
    app_cls = MagicMock()
    monkeypatch.setattr(m, "ToolbarApp", app_cls)

    # When main runs
    m.main()

    # Then the command table is printed and the app is never constructed
    out = capsys.readouterr().out
    assert "Available // commands:" in out
    app_cls.assert_not_called()


def test_main_starts_app_with_flags_from_args(monkeypatch):
    # Given --no-tray and a healthy clipboard, with the app class stubbed
    monkeypatch.setattr(sys, "argv", ["llmfix_linux.py", "--no-tray"])
    monkeypatch.setattr(m, "check_clipboard_backend", lambda: True)
    app_cls = MagicMock()
    monkeypatch.setattr(m, "ToolbarApp", app_cls)

    # When main runs
    m.main()

    # Then the app is built tray-less with Caps+A enabled and then run
    app_cls.assert_called_once_with(use_tray=False, enable_caps_a=True)
    app_cls.return_value.run.assert_called_once()


def test_main_disables_caps_a_when_flag_present(monkeypatch):
    # Given --no-tray --disable-caps-a and a healthy clipboard
    monkeypatch.setattr(sys, "argv", ["llmfix_linux.py", "--no-tray", "--disable-caps-a"])
    monkeypatch.setattr(m, "check_clipboard_backend", lambda: True)
    app_cls = MagicMock()
    monkeypatch.setattr(m, "ToolbarApp", app_cls)

    # When main runs
    m.main()

    # Then the Caps+A trigger is disabled on the app
    app_cls.assert_called_once_with(use_tray=False, enable_caps_a=False)
