from unittest.mock import MagicMock

import llmfix_linux as m


def test_notify_invokes_notify_send_with_title(monkeypatch):
    # Given a mocked notify-send subprocess boundary
    run = MagicMock()
    monkeypatch.setattr(m.subprocess, "run", run)

    # When we post a notification with a title
    m.notify("Processing…")

    # Then notify-send is invoked with the app name and the title in the payload
    run.assert_called_once()
    cmd = run.call_args[0][0]
    assert cmd[0] == "notify-send"
    assert "LLMFix" in cmd
    assert "Processing…" in cmd[-1]


def test_notify_silent_adds_suppress_sound_hint(monkeypatch):
    # Given a mocked notify-send subprocess boundary
    run = MagicMock()
    monkeypatch.setattr(m.subprocess, "run", run)

    # When we post a silent notification
    m.notify("Done", "body", silent=True)

    # Then the suppress-sound hint is included in the command
    cmd = run.call_args[0][0]
    assert "--hint=boolean:suppress-sound:true" in cmd


def test_notify_swallows_missing_binary(monkeypatch):
    # Given a system where notify-send is absent (subprocess raises FileNotFoundError)
    def raise_missing(*a, **k): raise FileNotFoundError("notify-send")
    monkeypatch.setattr(m.subprocess, "run", raise_missing)

    # When we post a notification
    # Then it is a silent no-op, no exception escapes
    m.notify("anything")
