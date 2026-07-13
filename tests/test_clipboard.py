import llmfix_linux as m


def test_check_clipboard_backend_true_when_paste_and_copy_work(monkeypatch):
    # Given a working pyperclip backend
    monkeypatch.setattr(m.pyperclip, "paste", lambda: "current")
    monkeypatch.setattr(m.pyperclip, "copy", lambda v: None)

    # When we probe the clipboard backend
    ok = m.check_clipboard_backend()

    # Then it reports available
    assert ok is True


def test_check_clipboard_backend_false_when_backend_missing(monkeypatch):
    # Given a pyperclip whose copy raises the backend-missing error
    monkeypatch.setattr(m.pyperclip, "paste", lambda: "current")
    def _boom(v): raise m.pyperclip.PyperclipException("no backend")
    monkeypatch.setattr(m.pyperclip, "copy", _boom)

    # When we probe the clipboard backend
    ok = m.check_clipboard_backend()

    # Then it reports unavailable rather than crashing
    assert ok is False


def test_copy_selection_taps_ctrl_c():
    # Given the mocked keyboard from the autouse fixture

    # When we copy the current selection
    m.copy_selection()

    # Then Ctrl+C is issued via a 'c' tap
    m.kb.tap.assert_any_call("c")


def test_paste_clipboard_taps_ctrl_v():
    # Given the mocked keyboard from the autouse fixture

    # When we paste the clipboard
    m.paste_clipboard()

    # Then Ctrl+V is issued via a 'v' tap
    m.kb.tap.assert_any_call("v")
